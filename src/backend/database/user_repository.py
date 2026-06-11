from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Users
from backend.exceptions.exc import DataBaseError, UserAlreadyExists

# from backend.authentication.auth import password_hash_obj


class UserRepository:
    """Class responisble for connection with DB. Consist of methods to work with AUTH, login, registry of users"""

    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_user(self, email, password) -> str:
        """Function will create user

        Args:
            email (str)
            password (str): password_hash

        Returns:
            str: User email
        """
        try:
            user = self.db.query(Users).where(Users.email == email).first()
        except SQLAlchemyError as err:
            raise DataBaseError() from err

        if user is not None:
            raise UserAlreadyExists()

        new_user = Users(email=email, password_hash=password)

        try:
            self.db.add(new_user)
            self.db.commit()
            logger.debug(f"Created user with ID {new_user.id}")
            return new_user.email

        except SQLAlchemyError as err:
            raise DataBaseError() from err

    def get_user_by_email(self, user_email):
        """Function check weather User with particular email exists in DB

        Args:
            user_email (str): user email

        Raises:
            DataBaseError: If SQL error happens

        Returns:
            _type_: SQLAlchemy Users table object, later converted into Pydantic Model or None if User not found
        """
        try:
            user = self.db.query(Users).where(Users.email == user_email).first()
        except SQLAlchemyError as err:
            raise DataBaseError from err

        if not user:
            logger.warning(f"User with email {user_email} does not exists in DB")
            return None
        return user
