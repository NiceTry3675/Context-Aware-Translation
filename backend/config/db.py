
from sqlalchemy.orm import Session, sessionmaker
from backend.config.database import SessionLocal

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_sessionmaker() -> sessionmaker:
    """Get the sessionmaker for creating new sessions in UoW."""
    return SessionLocal
