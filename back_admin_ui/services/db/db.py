from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from config import SQLALCHEMY_DATABASE_URL as ENV_DATABASE_URL
from services.db.model import Base

DEFAULT_SQLITE_URL = "sqlite:///./build_ai_2025.db"

database_url = ENV_DATABASE_URL or DEFAULT_SQLITE_URL

engine_kwargs = {}

try:
    backend_name = make_url(database_url).get_backend_name()
except Exception:
    backend_name = ""

if backend_name == "sqlite":
    engine_kwargs["connect_args"] = {"check_same_thread": False}

database_url = DEFAULT_SQLITE_URL
engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы успешно!")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
