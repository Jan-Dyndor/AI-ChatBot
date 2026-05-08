from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine(url="sqlite:///data/data.db")

session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
