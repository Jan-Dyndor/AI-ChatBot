from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(DB_URL: str):
    """Function creates engine based on enviroment DB URL

    Args:
        DB_URL (str): DB URL

    Returns:
        Engine: engine object
    """
    if DB_URL == "sqlite:///:memory:":
        engine = create_engine(
            url=DB_URL, poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
    else:
        engine = create_engine(url=DB_URL)

    return engine


def session_factory(engine) -> sessionmaker:
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session
