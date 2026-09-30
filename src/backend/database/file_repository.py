import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Files
from backend.exceptions.exc import DataBaseError, FileNotSaved


class FileRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_file_storage_place(self, user_id: int, file_name: str) -> Path:

        root: Path = Path(__file__).resolve().parents[3]
        file_dir: Path = root / Path("storage")

        try:
            os.mkdir(file_dir / f"{user_id}")
        except FileExistsError:
            pass

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

        file_path: Path = self.create_file_storage_place(user_id, file_name)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except OSError as e:
            raise FileNotSaved(
                file_name=file_name, user_id=user_id, file_path=file_path
            ) from e

        logger.info(
            f"Transferred user's { user_id } file {file_name} to given location"
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
            raise DataBaseError() from e
