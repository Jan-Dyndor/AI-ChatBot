from fastapi import UploadFile

from backend.database.file_repository import FileRepository


class FileService:
    def __init__(self, file_repository: FileRepository) -> None:
        self.db = file_repository

    def save_file(self, file: UploadFile, file_name: str, user_id: int):
        """Save an uploaded file using the file repository.

        This method represents the service layer entry point for file uploads.
        It delegates file persistence and metadata storage to the repository.

        Args:
            file (UploadFile): Uploaded file object received from FastAPI.
            file_name (str): Original name of the uploaded file.
            user_id (int): ID of the user who uploaded the file.
        """
        self.db.save_file(file, file_name, user_id)
