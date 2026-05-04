from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.config import settings


def _ensure_sqlite_directory(database_url: str) -> None:
    database_path = database_url[len("sqlite:///") :]
    parent = Path(database_path).expanduser().parent
    parent.mkdir(parents=True, exist_ok=True)


def _build_engine():
    database_url = settings.database_url.strip()
    normalized = database_url.lower()

    if normalized.startswith("sqlite:///:memory:"):
        return create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    if normalized.startswith("sqlite:///"):
        _ensure_sqlite_directory(database_url)
        return create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

    return create_engine(database_url, echo=False)

engine = _build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
