from pathlib import Path

from fastapi import UploadFile

from backend.database.file_repository import FileRepository
from backend.exceptions.exc import FileToLarge


class FileService:
    def __init__(self, file_repository: FileRepository) -> None:
        self.db = file_repository

    def save_file(self, file: UploadFile, file_name: str, user_id: int) -> Path:
        """Save an uploaded file using the file repository.

        This method represents the service layer entry point for file uploads.
        It delegates file persistence and metadata storage to the repository.

        Args:
            file (UploadFile): Uploaded file object received from FastAPI.
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user who uploaded the file.
        """
        return self.db.save_file(file, file_name, user_id)

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
