from fastapi import UploadFile
from backend.database.file_repository import FileRepository


class FileService:
    def __init__(self, file_repository: FileRepository) -> None:
        self.db = file_repository

    def save_file(self, file: UploadFile, file_name: str, user_id: int):

        self.db.save_file(file, file_name, user_id)
