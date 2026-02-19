from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Gunakan data dari .env jika ada, atau default ke matel.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./matel.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Enable WAL Mode for SQLite stability (Crucial for background tasks)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
