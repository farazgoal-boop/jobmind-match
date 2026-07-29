from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models import AppSetting


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
        engine = create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        # WAL lets a read (dashboard render) and a write (a hunt batch
        # committing a contact) happen concurrently without lock contention,
        # and survives a hard crash mid-write better than the default
        # rollback-journal mode.
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        return engine

    return create_engine(database_url, echo=False)


def _ensure_candidate_profile_columns() -> None:
    column_names = {column["name"] for column in inspect(engine).get_columns("candidateprofile")}
    missing_columns = []

    if "resume_url" not in column_names:
        missing_columns.append("resume_url")
    if "portfolio_url" not in column_names:
        missing_columns.append("portfolio_url")
    if "linkedin_url" not in column_names:
        missing_columns.append("linkedin_url")
    if "upwork_url" not in column_names:
        missing_columns.append("upwork_url")
    if "fiverr_url" not in column_names:
        missing_columns.append("fiverr_url")
    if "product_name" not in column_names:
        missing_columns.append("product_name")
    if "product_url" not in column_names:
        missing_columns.append("product_url")
    if "sales_pitch" not in column_names:
        missing_columns.append("sales_pitch")

    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name in missing_columns:
            connection.exec_driver_sql(
                f"ALTER TABLE candidateprofile ADD COLUMN {column_name} VARCHAR NOT NULL DEFAULT ''"
            )


def _ensure_lead_hunter_location_columns() -> None:
    for table_name in ("huntedcontact", "clientlead"):
        column_names = {column["name"] for column in inspect(engine).get_columns(table_name)}
        if "location" not in column_names:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN location VARCHAR NOT NULL DEFAULT ''"
                )


def _ensure_hunt_session_columns() -> None:
    column_names = {column["name"] for column in inspect(engine).get_columns("huntedcontact")}
    if "hunt_session_id" not in column_names:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE huntedcontact ADD COLUMN hunt_session_id INTEGER"
            )


def _load_saved_github_token() -> None:
    # A user-saved token (Settings > GitHub Token) lives in AppSetting, not
    # the GITHUB_TOKEN env var settings.github_token was built from at import
    # time — pull it in now so every GitHub call picks it up from process
    # start, not just after the next in-app save.
    with Session(engine) as session:
        row = session.get(AppSetting, "github_token")
        if row and row.value:
            settings.github_token = row.value


engine = _build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_candidate_profile_columns()
    _ensure_lead_hunter_location_columns()
    _ensure_hunt_session_columns()
    _load_saved_github_token()


def get_session():
    with Session(engine) as session:
        yield session
