import sqlite3
from pathlib import Path

from app.core.config import get_settings


def _database_path() -> Path:
    settings = get_settings()
    return Path(settings.app_database_path).expanduser()


def init_db() -> None:
    database_path = _database_path()
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def get_connection() -> sqlite3.Connection:
    init_db()
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    return connection

