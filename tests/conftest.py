"""Test-wide setup. The app's DB engine is a module-level singleton built
from DATABASE_URL at import time, so the env var must be set before
`app.config`/`app.db` are imported anywhere — done here, in conftest,
which pytest always imports before collecting test modules."""
import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="jobmind_test_")
DB_PATH = Path(_TMP_DIR) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["APP_ENV"] = "test"

from sqlmodel import Session, create_engine  # noqa: E402

from app.db import engine, init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_database():
    init_db()
    yield


@pytest.fixture()
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture()
def fresh_engine():
    """A brand-new engine/connection pointed at the same sqlite file as the
    app's own engine, but sharing no Python objects with it — the closest a
    same-process test can get to simulating 'the app was killed and a new
    process reopened the same database file'."""
    new_engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}", connect_args={"check_same_thread": False})
    try:
        yield new_engine
    finally:
        new_engine.dispose()
