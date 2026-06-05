import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash

password_hash_obj = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/token")


def hash_password(password: str) -> str:
    """Function hashes password and returns its hash

    Args:
        password (str): User Password

    Returns:
        str: Hash of password
    """
    return password_hash_obj.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Function verify User provided password with DB hash

    Args:
        password (str): User password
        password_hash (str): DB hash

    Returns:
        bool: True if password == password_hash otherwise False
    """
    return password_hash_obj.verify(password, password_hash)
