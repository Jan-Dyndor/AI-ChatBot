from pwdlib import PasswordHash

password_hash_obj = PasswordHash.recommended()
DUMMY_HASH: str = password_hash_obj.hash(
    "DUMMY HASH TO MAKE SURE AUTH PROCESS TAKES ON AVG SAME AMOUNT OF TIME"
)


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
