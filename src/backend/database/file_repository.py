import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DataError, IntegrityError, ProgrammingError, SQLAlchemyError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from backend.database.models import Files, FileStatus, IndexingStatus
from backend.exceptions.exc import (
    DataBaseError,
    DataBaseFileError,
    DatabaseNoRetryError,
    DataBaseResourceNotFound,
    FailedFileCleanUp,
    FileAlreadyExists,
    FileIntegrityError,
    FileNotSaved,
    FileStorageException,
    UploadAfterFailedFileDelation,
)
from backend.retry.retry_logs_logic import (
    _mark_file_to_del_tenacity_callback,
    cleanup_and_log_final_retry_failure,
    log_and_delete_file,
    log_retry,
)


class FileRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def delete_file_from_db(self, file_id: int, user_id: int):
        """Delete a user's file metadata from the database.

        Delete the file record matching the provided file ID and user ID.
        If no matching record exists, return without raising an exception.
        Commit the transaction after successful deletion and roll back
        if a database error occurs.

        Args:
            file_id: ID of the file to delete.
            user_id: ID of the user who owns the file.

        Raises:
            DataBaseError: If a SQLAlchemy database operation fails.
        """

        logger.debug(f"Deleting User's {user_id} file {file_id}from DB ")
        try:
            query = delete(Files).where(Files.id == file_id, Files.user_id == user_id)
            result = self.db.execute(query)
            if not result.rowcount:
                self.db.rollback()
                logger.debug(f"User's {user_id} File {file_id} alredy delted")
                return
            self.db.commit()
            logger.debug(f"Deleted User's {user_id} file {file_id} from DB")
        except SQLAlchemyError as err:
            self.db.rollback()
            raise DataBaseError() from err

    def mark_file_status_to_delte(self, file_id: int, user_id: int) -> bool:
        """Mark a user's file as pending deletion in the database.

        Update the file's status to DELETING for the specified file ID and user ID.
        If no matching record exists, return False without raising an exception.
        Commit the transaction after a successful update and roll back if a
        database error occurs.

        Args:
            file_id: ID of the file to mark for deletion.
            user_id: ID of the user who owns the file.

        Returns:
            bool: True if the file status was updated, False if no matching
                file record was found.

        Raises:
            DataBaseError: If a SQLAlchemy database operation fails.
        """
        logger.debug(
            f"Setting User's {user_id} file {file_id} status as to beeing delete"
        )
        try:
            query = (
                update(Files)
                .where(Files.id == file_id, Files.user_id == user_id)
                .values(file_status=FileStatus.DELETING)
            )

            result = self.db.execute(query)

            if result.rowcount == 0:
                self.db.rollback()
                logger.info(f"File {file_id} not found in DB")
                return False

            self.db.commit()
            return True

        except SQLAlchemyError as err:
            self.db.rollback()
            raise DataBaseError() from err

    def create_file_storage_place(
        self, user_id: int, file_name: str, file_id: int
    ) -> Path:
        """Prepare a unique filesystem path for an uploaded file.

        Create a user-specific storage directory if it does not already exist
        and generate a unique file path by prefixing the original filename
        with a UUID.

        If path preparation fails, attempt to mark the file for deletion and
        remove its metadata from the database. Cleanup errors are logged and
        suppressed to preserve the original storage exception.

        Args:
            user_id: ID of the user uploading the file.
            file_name: Original name of the uploaded file.
            file_id: ID of the associated file record in the database.

        Returns:
            Path: Generated filesystem path where the file should be stored.

        Raises:
            FileStorageException: If storage path preparation fails.
                The original exception is preserved as the cause.
        """
        try:
            root: Path = Path(__file__).resolve().parents[3]
            file_dir: Path = root / Path("storage")

            user_dir = file_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)

            file_path: Path = file_dir / f"{user_id}" / f"{uuid4()}_{file_name}"
            logger.info(
                f"Secured file location for file {file_name} uploaded by user {user_id}"
            )
            return file_path
        except Exception as storage_error:
            try:
                self.mark_file_status_to_delte(file_id=file_id, user_id=user_id)
            except Exception:
                logger.exception(
                    f"Issue occured while marking User's {user_id} file {file_id} to delte. No information if file exists - tring to delte the file anyway."
                )
            try:
                self.delete_file_from_db(file_id=file_id, user_id=user_id)
            except Exception:
                logger.exception(
                    f"Issue occured while deleting User's {user_id} file {file_id} from DB."
                )

            raise FileStorageException(
                user_id,
                file_id,
                file_name,
            ) from storage_error

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(FileNotSaved),
        before_sleep=log_retry,
        retry_error_callback=_mark_file_to_del_tenacity_callback,
    )
    def save_file(
        self,
        file: UploadFile,
        file_name: str,
        user_id: int,
        file_id: int,
        file_path: Path,
    ):
        """Save an uploaded file to local storage with automatic retries.

        Reset the uploaded file stream before each attempt and copy its contents
        to the specified filesystem path.

        If writing fails, attempt to remove the partially saved file. If cleanup
        also fails, mark the file for deletion in the database and raise
        FailedFileCleanUp.

        Retry up to three attempts for FileNotSaved exceptions using exponential
        backoff with jitter. After exhausting retries, invoke the configured
        callback.

        Args:
            file: Uploaded file received from FastAPI.
            file_name: Original name of the uploaded file.
            user_id: ID of the user uploading the file.
            file_id: ID of the associated file record in the database.
            file_path: Destination path where the file should be saved.

        Returns:
            None: On successful completion.

        Raises:
            FileNotSaved: If writing fails and filesystem cleanup succeeds.
            FailedFileCleanUp: If removal of a partially saved file fails.
        """

        try:
            file.file.seek(0)  # move pointer to the beggining of the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(
                f"Transferred user's {user_id} file {file_name} to given location in storage"
            )
        except OSError as file_error:
            try:
                self.delete_file_from_storage(file_path=file_path)
            except FileNotFoundError:
                raise FileNotSaved(
                    file_name=file_name, user_id=user_id, file_path=file_path
                )
            except Exception:
                try:
                    self.mark_file_status_to_delte(file_id=file_id, user_id=user_id)
                except Exception:
                    logger.exception(
                        f"Issue occured while marking User's {user_id} file {file_id} to delte. No information if file exists - tring to delte the file anyway."
                    )
                raise FailedFileCleanUp(
                    file_path=file_path, user_id=user_id, file_id=file_id
                ) from file_error

            raise FileNotSaved(
                file_name=file_name, user_id=user_id, file_path=file_path
            ) from file_error

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(DataBaseFileError),
        retry_error_callback=log_and_delete_file,
    )
    def update_file_metadata(
        self, user_id: int, file_path: Path, file_id: int, file_name: str
    ):
        """Update the storage path of an existing file record in PostgreSQL.

        Locate the file using its file ID and user ID, update its storage path,
        and commit the transaction.

        If no matching record exists, roll back the transaction and raise
        DataBaseResourceNotFound.

        Retry up to three times for DataBaseFileError exceptions using
        exponential backoff with jitter. After exhausting retries, invoke
        the configured cleanup callback.

        For non-retryable database errors, attempt to mark the file for
        deletion and remove its metadata from the database. Cleanup errors
        are logged and suppressed.

        Args:
            user_id: ID of the user who owns the file.
            file_path: Filesystem path where the uploaded file is stored.
            file_id: ID of the existing file record.
            file_name: Original filename used for logging and error reporting.

        Returns:
            None: If the metadata is successfully updated. The retry callback
                may determine the return value when all retries are exhausted.

        Raises:
            DataBaseResourceNotFound: If no matching file record exists.
            DatabaseNoRetryError: If a non-retryable database error occurs.
            DataBaseFileError: If a retryable database operation fails.
                After exhausting retries, the final behavior depends on
                the configured retry_error_callback.
        """
        try:
            file_metadata = (
                update(Files)
                .where(Files.id == file_id, Files.user_id == user_id)
                .values(storage_path=str(file_path))
            )

            result = self.db.execute(file_metadata)
            if result.rowcount == 0:
                logger.warning(
                    f"Can not find User's {user_id} file {file_id} in DB to update metadata"
                )
                self.db.rollback()
                raise DataBaseResourceNotFound()
            self.db.commit()
            logger.info(f"Updated user's {user_id} file {file_name} metadata in DB")

        except (IntegrityError, DataError, ProgrammingError) as e:
            self.db.rollback()
            try:
                self.mark_file_status_to_delte(file_id=file_id, user_id=user_id)
            except Exception:
                logger.exception(
                    f"Issue occured while marking User's {user_id} file {file_id} to delte. No information if file exists - tring to delte the file anyway."
                )
            try:
                self.delete_file_from_db(file_id=file_id, user_id=user_id)
            except Exception:
                logger.exception(
                    f"Issue occured while deleting User's {user_id} file {file_id} from DB."
                )
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
            query = select(
                Files.id, Files.original_file_name, Files.index_status
            ).where(Files.user_id == user_id)
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

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        retry=retry_if_exception_type(DataBaseError),
        before_sleep=log_retry,
        retry_error_callback=cleanup_and_log_final_retry_failure,
    )
    def update_file_idnexing_status(self, user_id: int, file_id: int, new_status: str):
        """Update the indexing status for a user's file.

        Args:
            user_id: ID of the file owner.
            file_id: ID of the file to update.
            new_status: New indexing status to save.

        Raises:
            DataBaseError: If the database update fails.
            DataBaseResourceNotFound: If no file with the given ID belongs to the user.
        """
        try:
            query = (
                update(Files)
                .where(Files.user_id == user_id, Files.id == file_id)
                .values(index_status=new_status)
            )
            logger.info(f"Updating user's {user_id} file {file_id} status")
            result = self.db.execute(query)
            if result.rowcount == 0:
                self.db.rollback()
                raise DataBaseResourceNotFound()

            self.db.commit()
            logger.info(f"Sucessfully updated user's {user_id} file {file_id} status")

        except (IntegrityError, DataError, ProgrammingError) as e:
            self.db.rollback()
            raise DatabaseNoRetryError() from e
        except SQLAlchemyError as err:
            self.db.rollback()
            raise DataBaseError() from err

    def is_sha_present(self, user_id: int, sha: str) -> bool:
        """Check whether a file with the given SHA-256 hash exists for a user.

        Args:
            user_id (int): ID of the user who owns the file.
            sha (str): SHA-256 hash of the file to check.
            file_name (str): Original name of the file.

        Returns:
            bool: True if a matching file exists, False otherwise.

        Raises:
            DataBaseError: If a SQLAlchemy database operation fails.
        """
        query = select(Files.file_sha).where(
            Files.user_id == user_id, Files.file_sha == sha
        )
        try:
            result = self.db.scalar(query)
            if not result:
                return False
            else:
                return True
        except SQLAlchemyError:
            raise DataBaseError()

    def partially_save_file_metadata(
        self, user_id: int, file_name: str, sha: str, task_id: str
    ) -> int:
        """Create an initial file record with partial metadata in PostgreSQL.

        Persist the available file metadata before saving the file to storage.
        Use a placeholder for the storage path and set the indexing status
        to PENDING.

        The database's unique constraint on (user_id, file_sha) prevents
        concurrent uploads of duplicate files by the same user.

        Args:
            user_id: ID of the user uploading the file.
            file_name: Original name of the uploaded file.
            sha: SHA-256 hash of the file content.
            task_id: Unique identifier of the associated Celery task.

        Returns:
            int: ID of the newly created file record.

        Raises:
            FileAlreadyExists: If a database integrity constraint is violated.
            DataBaseError: If another SQLAlchemy database operation fails.
        """
        try:

            file = Files(
                user_id=user_id,
                storage_path="TO BE SET",
                original_file_name=file_name,
                index_status=IndexingStatus.PENDING,
                file_sha=sha,
                task_id=task_id,
            )
            self.db.add(file)
            self.db.commit()
            logger.debug(f"Saved User's {user_id} partial file metadata in DB")
            return file.id
        except IntegrityError as err:
            self.db.rollback()
            is_delete_status: bool | None = self.check_file_status(
                sha=sha, user_id=user_id
            )
            if is_delete_status is None:
                raise FileIntegrityError(user_id=user_id, file_name=file_name) from err
            elif is_delete_status:
                raise UploadAfterFailedFileDelation(
                    file_name=file_name, user_id=user_id
                )
            else:
                raise FileAlreadyExists(file_name=file_name, user_id=user_id) from err

        except SQLAlchemyError as err:
            self.db.rollback()
            raise DataBaseError() from err

    def mark_file_as_ready_best_effort(
        self, user_id: int, file_id: int, file_path: Path
    ):
        """Mark an uploaded file as READY using a best-effort database update.

        Update the file status to READY after successful file storage and
        metadata persistence, before starting the indexing process.

        If the file record cannot be found, attempt to remove the physical
        file from storage to prevent orphaned files. Cleanup errors are
        logged without masking the missing database record error.

        If a SQLAlchemy error occurs, roll back the transaction and log
        the failure without deleting the uploaded file.

        Args:
            user_id: ID of the user who owns the file.
            file_id: ID of the file record to update.
            file_path: Path to the uploaded file, used for cleanup if the
                database record is missing.

        Returns:
            None: The method does not return a value.

        Raises:
            DataBaseResourceNotFound: If no matching file record exists,
                assuming this exception is not a subclass of SQLAlchemyError.
        """
        try:
            query = (
                update(Files)
                .where(Files.id == file_id, Files.user_id == user_id)
                .values(file_status=FileStatus.READY)
            )
            result = self.db.execute(query)

            if result.rowcount == 0:
                self.db.rollback()
                logger.error(
                    f"Can not locate User's {user_id} file {file_id} after whole process of file upload before indexing"
                )
                try:
                    self.delete_file_from_storage(file_path=file_path)
                except FileNotFoundError:
                    logger.exception(
                        f"User's {user_id} file {file_id} does not exists in storage as well."
                    )
                except Exception:
                    logger.exception(
                        f"Cound not clean up User's {user_id} file {file_id} from storage. Need manual cleanup from {file_path}"
                    )
                raise DataBaseResourceNotFound()

            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception(
                f"Exception occured at the end of upload User's {user_id} file {file_id} porcess before indexing the file."
            )

    def check_file_status(self, sha: str, user_id: int) -> bool | None:
        #! DOCS STRING
        """_summary_

        Args:
            sha (str): _description_
            user_id (int): _description_

        Raises:
            DataBaseError: _description_

        Returns:
            bool | None: _description_
        """
        try:
            query = select(Files.file_status).where(
                Files.file_sha == sha, Files.user_id == user_id
            )

            result = self.db.scalar(query)

            self.db.commit()
            if not result:
                return None

            if result == FileStatus.DELETING:
                return True
            else:
                return False
        except SQLAlchemyError as err:
            self.db.rollback()
            raise DataBaseError() from err
