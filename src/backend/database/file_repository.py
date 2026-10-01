import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Files
from backend.exceptions.exc import DataBaseFileError, FileNotSaved


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

    def save_file(
        self,
        file: UploadFile,
        file_name: str,
        user_id: int,
    ):
        """Save an uploaded file to local storage and persist its metadata in the database.

        The file is first written to the filesystem. If the file is saved successfully,
        its metadata is stored in the database. If the database operation fails, the
        transaction is rolled back and a best-effort cleanup is performed to remove
        the previously saved file.

        Args:
            file (UploadFile): Uploaded file object received from FastAPI.
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user who uploaded the file.

        Raises:
            FileNotSaved: If the file cannot be written to local storage.
            DataBaseFileError: If the file metadata cannot be persisted in the database.
        """

        file_path: Path = self.create_file_storage_place(user_id, file_name)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except OSError as e:
            raise FileNotSaved(
                file_name=file_name, user_id=user_id, file_path=file_path
            ) from e

        logger.info(
            f"Transferred user's { user_id } file {file_name} to given location in storage"
        )
        try:
            file_to_save = Files(
                user_id=user_id,
                original_file_name=file_name,
                storage_path=str(file_path),
            )

            self.db.add(file_to_save)
            self.db.commit()
            logger.info(f"Saved user's {user_id} file {file_name} metadata in DB")
        except SQLAlchemyError as e:
            self.db.rollback()
            try:
                self.delete_file_from_storage(file_path)

            except OSError:
                logger.exception(
                    f"Failed to cleanup user's {user_id} file {file_name} after database error. File may still be under path {file_path}"
                )

            raise DataBaseFileError(user_id, file_name) from e

    def delete_file_from_storage(self, file_path: Path):
        """Delete File from storage

        Args:
            file_path (Path): path to file
        """
        os.remove(path=file_path)
