from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.config import settings


if settings.database_url.strip().lower().startswith("sqlite:///:memory:"):
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
