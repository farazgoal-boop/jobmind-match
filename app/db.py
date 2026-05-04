from pathlib import Path

from sqlalchemy import inspect
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


def _ensure_candidate_profile_columns() -> None:
    column_names = {column["name"] for column in inspect(engine).get_columns("candidateprofile")}
    missing_columns = []

    if "resume_url" not in column_names:
        missing_columns.append("resume_url")
    if "portfolio_url" not in column_names:
        missing_columns.append("portfolio_url")

    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name in missing_columns:
            connection.exec_driver_sql(
                f"ALTER TABLE candidateprofile ADD COLUMN {column_name} VARCHAR NOT NULL DEFAULT ''"
            )


engine = _build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_candidate_profile_columns()


def get_session():
    with Session(engine) as session:
        yield session
