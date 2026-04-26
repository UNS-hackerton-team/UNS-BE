from functools import lru_cache
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings


metadata = MetaData()
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(30), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def _database_url() -> str:
    return get_settings().database_url


def _ensure_sqlite_directory_exists(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return
    if not url.database or url.database == ":memory:":
        return

    database_path = Path(url.database).expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def _get_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        url = make_url(database_url)
        if not url.database or url.database == ":memory:":
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )

    return create_engine(database_url, pool_pre_ping=True)


def get_engine() -> Engine:
    return _get_engine(_database_url())


def init_db() -> None:
    database_url = _database_url()
    _ensure_sqlite_directory_exists(database_url)
    metadata.create_all(_get_engine(database_url))


def reset_db_state() -> None:
    try:
        get_engine().dispose()
    except Exception:
        pass
    _get_engine.cache_clear()

