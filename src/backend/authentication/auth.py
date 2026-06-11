from datetime import datetime, timedelta, timezone

import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from loguru import logger

from backend.api.schemas.pydantic_schemas import UserDB
from backend.authentication.passwords import DUMMY_HASH, verify_password
from backend.configuration.settings import get_settings
from backend.database.user_repository import UserRepository
from backend.exceptions.exc import InvalidCredentials

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/token")


class AuthService:

    def __init__(self, user_repository: UserRepository) -> None:
        self.db = user_repository

    def get_user(self, user_email: str) -> UserDB | None:
        """Function call UserRepository to check if User with email exists in DB

        Args:
            user_email (str):

        Returns:
            UserDB | None: If user exists UesrDB object is returned or None if user does not exist
        """
        user = self.db.get_user_by_email(user_email)
        if not user:
            return None
        return UserDB.model_validate(user)

    def authenticate_user(self, user_email: str, password: str) -> UserDB:
        """Function check if user exists and if password maches

        Args:
            user_email (str):
            password (str):

        Returns:
            bool | UserDB: If User does not exist or password does not mach return False. If OK return UserDB model
        """
        user = self.get_user(user_email)

        if not user:
            verify_password(password, DUMMY_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.password_hash):
            logger.debug("Wrong User Password")
            raise InvalidCredentials()
        return user

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        """Function creates JWT

        Args:
            data (dict): user payload with sub = user_email
            expires_delta (timedelta | None, optional): TTL of JWT in minutes. Defaults to None.

        Returns:
            str: JWT
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(tz=timezone.utc) + expires_delta
        else:
            expire = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})

        encode_jwt = jwt.encode(
            to_encode, settings.secret_key_jwt, settings.algorythm_jwt
        )

        return encode_jwt

    def get_current_user_data(self, token: str) -> UserDB:
        """Function decodes JWT and returs UserDB model if JWT is valid

        Args:
            token (str, optional): Token. Defaults to Depends(oauth2_scheme).

        Returns:
            UserDB: Pydantic Model (email, password_hash,id)
        """
        try:
            payload = jwt.decode(
                token, settings.secret_key_jwt, algorithms=[settings.algorythm_jwt]
            )  #! tutaj chyba co jak toke jest expired czy cos weic tu tez w try cathc trzeba zebrac
        except InvalidTokenError as err:
            raise InvalidCredentials() from err  # ! zmien error jaki wychodzi tutaj!
        user_email = payload.get("sub", None)
        if not user_email:
            raise InvalidTokenError()
        user = self.get_user(user_email)
        if not user:
            raise InvalidCredentials()

        return user
