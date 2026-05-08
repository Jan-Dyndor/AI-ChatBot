from src.backend.database.db import session_factory


def get_db():
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
