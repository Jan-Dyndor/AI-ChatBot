from backend.authentication.passwords import hash_password
from backend.database.user_repository import UserRepository


class UserService:
    """Class to orchestrate the User logic involving with DB connection"""

    def __init__(self, UserRepository: UserRepository):
        self.db = UserRepository

    def create_user(self, email, password) -> str:
        """Function will  hash User password and call User Repository to save user to DB

        Args:
            email (str):
            password (str):

        Returns:
            str: user email
        """
        password_hash = hash_password(password)
        return self.db.create_user(email=email, password=password_hash)
