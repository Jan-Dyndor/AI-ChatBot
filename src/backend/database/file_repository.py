import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError, ProgrammingError, SQLAlchemyError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from backend.database.models import Files
from backend.exceptions.exc import (
    DataBaseError,
    DataBaseFileError,
    DatabaseNoRetryError,
    DataBaseResourceNotFound,
    FailedFileCleanUp,
    FileNotSaved,
)
from backend.retry.retry_logs import log_and_delete_file, log_retry


class FileRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_file_storage_place(self, user_id: int, file_name: str) -> Path:
        """Create and return a unique storage path for an uploaded file.

        The method ensures that a user-specific storage directory exists and
        generates a unique file name using a UUID to avoid naming conflicts.

        Args:
            user_id (int): ID of the user who uploaded the file.
            file_name (str): Original name of the uploaded file.

        Returns:
            Path: Full filesystem path where the uploaded file should be stored.
        """

        root: Path = Path(__file__).resolve().parents[3]
        file_dir: Path = root / Path("storage")

        user_dir = file_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path: Path = file_dir / f"{user_id}" / f"{uuid4()}_{file_name}"
        logger.info(
            f"Secured file location for file {file_name} uploaded by user {user_id}"
        )
        return file_path

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(FileNotSaved),
        before_sleep=log_retry,
    )
    def save_file(
        self,
        file: UploadFile,
        file_name: str,
        user_id: int,
    ) -> Path:
        """Save an uploaded file to local storage with automatic retries.

        Generates a unique storage path and copies the uploaded file to disk.
        The source stream is reset before each attempt. If writing fails,
        a best-effort cleanup removes the partially saved file.

        Retries up to three times for FileNotSaved exceptions using
        exponential backoff with jitter.

        Args:
            file (UploadFile): Uploaded file received from FastAPI.
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user uploading the file.

        Returns:
            Path: Path to the successfully saved file.

        Raises:
            FileNotSaved: If writing fails after all retry attempts.
            FailedFileCleanUp: If cleanup of a partially saved file fails.
        """

        file_path: Path = self.create_file_storage_place(user_id, file_name)

        try:
            file.file.seek(0)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(
                f"Transferred user's {user_id} file {file_name} to given location in storage"
            )
            return file_path
        except OSError as e:
            try:
                self.delete_file_from_storage(file_path)
            except OSError as err:
                raise FailedFileCleanUp(file_path=file_path) from err

            raise FileNotSaved(
                file_name=file_name, user_id=user_id, file_path=file_path
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(DataBaseFileError),
        retry_error_callback=log_and_delete_file,
    )
    def save_file_metadata(
        self,
        file_name: str,
        user_id: int,
        file_path: Path,
    ) -> None:
        """Persist uploaded file metadata in PostgreSQL using SQLAlchemy.

        Creates a database record containing the file name, owner ID,
        and storage path. Rolls back the transaction if persistence fails.

        Retries up to three times for DataBaseFileError exceptions using
        exponential backoff with jitter. IntegrityError, DataError,
        and ProgrammingError are treated as non-retryable errors.

        Args:
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user who uploaded the file.
            file_path (Path): Path to the file stored on disk.

        Raises:
            DatabaseNoRetryError: If a non-retryable database error occurs.
            DataBaseFileError: If database persistence fails after retries.
        """
        try:
            file_to_save = Files(
                user_id=user_id,
                original_file_name=file_name,
                storage_path=str(file_path),
            )

            self.db.add(file_to_save)
            self.db.commit()
            logger.info(f"Saved user's {user_id} file {file_name} metadata in DB")
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseNoRetryError() from e
        except DataError as e:
            self.db.rollback()
            raise DatabaseNoRetryError() from e
        except ProgrammingError as e:
            self.db.rollback()
            raise DatabaseNoRetryError() from e

        except SQLAlchemyError as e:
            self.db.rollback()
            raise DataBaseFileError(user_id, file_name) from e

    @staticmethod
    def delete_file_from_storage(file_path: Path):
        """Delete File from storage

        Args:
            file_path (Path): path to file
        """
        os.remove(path=file_path)

    def get_all_user_files(self, user_id: int) -> list:
        """Retrieve the IDs and original names of all files owned by a user.

        Args:
            user_id (int): ID of the user whose files are being retrieved.

        Raises:
            DataBaseResourceNotFound: If the user has no files stored in the database.
            DataBaseError: If a SQLAlchemy database operation fails.

        Returns:
            list[Row]: List of SQLAlchemy Row objects containing file IDs
                and original file names.
        """
        try:
            query = select(Files.id, Files.original_file_name).where(
                Files.user_id == user_id
            )
            user_files = self.db.execute(query).all()

            if not user_files:
                raise DataBaseResourceNotFound()

            return user_files
        except SQLAlchemyError as err:
            raise DataBaseError() from err

    def get_file(self, user_id: int, file_id: int) -> str:
        """Retrieve the storage path of a file owned by the specified user.

        Args:
            user_id (int): ID of the user who owns the file.
            file_id (int): ID of the requested file.

        Raises:
            DataBaseResourceNotFound: If the file does not exist or does not
                belong to the specified user.
            DataBaseError: If a SQLAlchemy database operation fails.

        Returns:
            str: Local storage path of the requested file.
        """
        try:
            query = select(Files).where(Files.user_id == user_id, Files.id == file_id)

            file = self.db.scalar(query)
            if not file:
                raise DataBaseResourceNotFound()

            return file.storage_path

        except SQLAlchemyError as err:
            raise DataBaseError() from err
