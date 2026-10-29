from __future__ import annotations

from sqlalchemy import Engine, create_engine

from ad_automation.config import Settings
from ad_automation.models import Base


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        f"sqlite:///{settings.database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
