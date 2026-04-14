from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _resolve_database_url(raw_url: str) -> str:
    if not raw_url.startswith("sqlite:///"):
        return raw_url

    db_rel_path = raw_url.replace("sqlite:///", "", 1)
    db_path = Path(db_rel_path)
    if not db_path.is_absolute():
        backend_dir = Path(__file__).resolve().parents[1]
        db_path = (backend_dir / db_rel_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


DATABASE_URL = _resolve_database_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()