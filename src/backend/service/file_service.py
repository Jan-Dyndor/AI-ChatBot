from pathlib import Path

from fastapi import UploadFile
from loguru import logger
from rust_sha256 import calculate_sha  # type: ignore

from backend.api.schemas.pydantic_schemas import FilesResponse
from backend.database.file_repository import FileRepository
from backend.exceptions.exc import (
    FailedFileDelete,
    FileAlreadyExists,
    FileToLarge,
    SHACalcuationError,
)


class FileService:
    def __init__(self, file_repository: FileRepository) -> None:
        self.db = file_repository

    def update_and_save_file_metadata(
        self, file: UploadFile, file_name: str, user_id: int, file_id: int
    ):
        """Save an uploaded file to local storage through the repository.

        Delegates file persistence to the repository, which handles
        automatic retries and cleanup in case of write failures.

        Args:
            file (UploadFile): Uploaded file received from FastAPI.
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user uploading the file.

        Returns:
            Path: Path to the successfully saved file.

        Raises:
            FileNotSaved: If file writing fails after all retry attempts.
            FailedFileCleanUp: If cleanup fails after a write error.
        """
        logger.debug(f"Attempting to save User's {user_id} file {file_id} to storage")

        file_path: Path = self.db.create_file_storage_place(
            user_id=user_id, file_name=file_name, file_id=file_id
        )

        self.db.update_file_metadata(
            user_id=user_id, file_path=file_path, file_id=file_id, file_name=file_name
        )

        self.db.save_file(
            file=file,
            file_name=file_name,
            user_id=user_id,
            file_id=file_id,
            file_path=file_path,
        )

        self.db.mark_file_as_ready_best_effort(
            user_id=user_id, file_id=file_id, file_path=file_path
        )

        return file_path

    def update_file_metadata(
        self, file_name: str, user_id: int, file_path: Path, file_id: int
    ):
        """Persist uploaded file metadata through the repository.

        Delegates the database operation to the repository, which handles
        transaction rollback and automatic retries for selected errors.

        Args:
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user who uploaded the file.
            file_path (Path): Path to the file stored on disk.

        Raises:
            DataBaseFileError: If metadata persistence fails after retries.
            DatabaseNoRetryError: If a non-retryable database error occurs.
        """
        logger.debug(
            f"Attempting to update User's {user_id} file {file_id} metadata in DB"
        )

        return self.db.update_file_metadata(
            file_name=file_name, user_id=user_id, file_path=file_path, file_id=file_id
        )

    def validate_file_size(
        self, size: int, max_size: int, file_name: str, user_id: int
    ) -> None:
        """Validate that the uploaded file does not exceed the maximum allowed size.

        Args:
            size (int): Size of the uploaded file in bytes.
            max_size (int): Maximum allowed file size in bytes.
            file_name (str): Name of the uploaded file.
            user_id (int): ID of the user uploading the file.

        Raises:
            FileToLarge: If the file size exceeds the maximum allowed limit.
        """
        if size > max_size:
            raise FileToLarge(file_name, user_id, max_size)

    def get_all_users_files(self, user_id) -> list[FilesResponse]:
        """Retrieve and validate all files belonging to the specified user.

        Args:
            user_id (int): ID of the user whose files are being retrieved.

        Raises:
            DataBaseResourceNotFound: If the user has no files stored in the database.
            DataBaseError: If a database operation fails.
            ValidationError: If the retrieved data does not match the FilesResponse schema.

        Returns:
            list[FilesResponse]: List of validated file response objects
                containing file IDs and original file names.
        """
        user_files = self.db.get_all_user_files(user_id=user_id)

        return [FilesResponse.model_validate(file) for file in user_files]

    def get_file(self, user_id: int, file_id: int) -> str:
        """Retrieve the storage path of a user's file and verify its availability.

        Args:
            user_id (int): ID of the user who owns the file.
            file_id (int): ID of the requested file.

        Raises:
            DataBaseResourceNotFound: If the file does not exist in the database
                or does not belong to the specified user.
            DataBaseError: If a database operation fails.
            FileNotFoundInStorage: If the file exists in the database but is
                missing from local storage.

        Returns:
            str: Local storage path of the verified file.
        """
        file_path: str = self.db.get_file_path(user_id=user_id, file_id=file_id)

        self.db.check_if_file_in_storage(
            user_id=user_id, file_path=Path(file_path), file_id=file_id
        )

        return file_path

    def update_idnexing_status(self, user_id: int, file_id: int, new_status: str):
        """Update the indexing status of a file owned by a user.

        Args:
            user_id: ID of the file owner.
            file_id: ID of the file to update.
            new_status: Status to assign to the file.
        """
        self.db.update_file_idnexing_status(
            user_id=user_id, file_id=file_id, new_status=new_status
        )

    def validate_if_file_exists(
        self, user_id: int, file_name: str, file_bytes: bytes
    ) -> str:
        """Validate that a file does not already exist for the given user.

        Calculate the file's SHA-256 hash and check whether the same hash
        is already stored in the database for the specified user.

        Args:
            user_id: ID of the user uploading the file.
            file_name: Original name of the uploaded file.
            file_bytes: Binary content of the uploaded file.

        Raises:
            SHACalcuationError: If the SHA-256 hash calculation fails.
            FileAlreadyExists: If a file with the same hash already exists
                for the given user.

        Returns:
            str: SHA-256 hash of the unique file.
        """
        try:
            logger.debug(f"Calculating User's {user_id} file SHA")
            sha = calculate_sha(file_bytes)
        except Exception as e:
            raise SHACalcuationError(user_id=user_id, file_name=file_name) from e

        if self.db.is_sha_present(user_id=user_id, sha=sha):
            raise FileAlreadyExists(user_id=user_id, file_name=file_name)

        logger.debug(f"User {user_id} file {file_name} is unique")
        return sha

    def save_partially_file_metadata(
        self, user_id: int, file_name: str, sha: str, task_id: str
    ) -> int:
        """Save initial file metadata to reserve a unique user-file SHA combination.

        Persist the required metadata before further file processing to prevent
        concurrent uploads of the same file by the same user. Remaining fields
        are populated with placeholder values.

        The database's unique constraint on (user_id, file_sha) ensures that
        duplicate records cannot be inserted concurrently.

        Args:
            user_id: ID of the user uploading the file.
            file_name: Original name of the uploaded file.
            sha: SHA-256 hash of the file content.
            task_id: Unique identifier of the associated Celery task.

        Returns:
            int: ID of the newly created file record.
        """
        logger.debug(
            f"Saving Users' {user_id} partial of file metadata to lock unique constrians of USER ID and SHA of file"
        )
        return self.db.partially_save_file_metadata(
            user_id=user_id, file_name=file_name, sha=sha, task_id=task_id
        )

    def prepare_to_del_file_from_db(self, user_id: int, file_id: int):
        """Mark a user's file for deletion and remove it from local storage.

        First, atomically marks the file as DELETING in the database and
        retrieves its storage path. Then attempts to delete the physical file.

        Args:
            user_id (int): ID of the user who owns the file.
            file_id (int): ID of the file to be deleted.

        Raises:
            FailedFileDelete: If an unexpected error occurs while deleting
                the file from storage.
            Exception: Propagates exceptions raised by the database operation.

        Notes:
            - Missing files in storage are logged but do not raise an exception.
            - The database record is not deleted by this method.
            - Database and filesystem operations are not part of a single
              atomic transaction.
        """
        file_path: str = self.db.mark_file_to_delete_atomic_operation(
            file_id=file_id, user_id=user_id
        )

        try:
            self.db.delete_file_from_storage(file_path=Path(file_path))
        except FileNotFoundError:
            logger.exception(
                f"User's {user_id} file {file_id} does not exist in storage anymore"
            )
        except Exception as err:
            logger.exception(
                f"Exception occured while deleting User's {user_id} file {file_id} from storage"
            )
            raise FailedFileDelete(user_id=user_id, file_id=file_id) from err
        logger.info(
            f"Sucessfully deleted User's {user_id} file {file_id} from sotrage."
        )

    def delete_file_from_db(self, user_id: int, file_id: int):
        """Delete a user's file record from the database.

        Args:
            user_id (int): ID of the user who owns the file.
            file_id (int): ID of the file record to delete.

        Raises:
            Exception: Propagates exceptions raised by the database
                repository during deletion.

        Notes:
            - Deletes only the database record, not the physical file
              or its associated vector embeddings.
            - Database transaction handling is delegated to the repository.
        """
        self.db.delete_file_from_db(file_id=file_id, user_id=user_id)
