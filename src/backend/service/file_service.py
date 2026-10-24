from pathlib import Path

from fastapi import UploadFile

from backend.database.file_repository import FileRepository
from backend.exceptions.exc import FileToLarge


class FileService:
    def __init__(self, file_repository: FileRepository) -> None:
        self.db = file_repository

    def save_file(self, file: UploadFile, file_name: str, user_id: int) -> Path:
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
        return self.db.save_file(file, file_name, user_id)

    def save_file_metadata(
        self,
        file_name: str,
        user_id: int,
        file_path: Path,
    ) -> None:
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
        self.db.save_file_metadata(
            file_name=file_name, user_id=user_id, file_path=file_path
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
