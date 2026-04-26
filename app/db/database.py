import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from app.core.config import get_settings


def _database_path() -> Path:
    settings = get_settings()
    return Path(settings.app_database_path).expanduser()


def serialize_list(values: Optional[list[str]]) -> str:
    return json.dumps(values or [])


def deserialize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


def _ensure_parent_dir() -> None:
    database_path = _database_path()
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    _ensure_parent_dir()

    with sqlite3.connect(_database_path()) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                team_type TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                invite_code_active INTEGER NOT NULL DEFAULT 1,
                invite_code_expires_at TEXT,
                invite_code_max_uses INTEGER,
                invite_code_used_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS workspace_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                workspace_role TEXT NOT NULL DEFAULT 'MEMBER',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (workspace_id, user_id),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                goal TEXT NOT NULL,
                tech_stack TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                pm_id INTEGER NOT NULL,
                priority TEXT NOT NULL,
                mvp_scope TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY (pm_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS project_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                project_role TEXT NOT NULL,
                tech_stack TEXT NOT NULL,
                strong_tasks TEXT NOT NULL,
                disliked_tasks TEXT NOT NULL,
                available_hours_per_day INTEGER NOT NULL,
                experience_level TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                goal TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PLANNED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS backlog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                required_role TEXT,
                required_tech_stack TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                estimated_hours INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                linked_issue_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                sprint_id INTEGER,
                backlog_item_id INTEGER,
                assignee_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'TODO',
                priority TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                estimated_hours INTEGER NOT NULL,
                required_role TEXT,
                required_tech_stack TEXT NOT NULL,
                assignment_reason TEXT,
                due_date TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE SET NULL,
                FOREIGN KEY (backlog_item_id) REFERENCES backlog_items(id) ON DELETE SET NULL,
                FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS chat_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (project_id, type, user_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_room_id INTEGER NOT NULL,
                sender_id INTEGER,
                sender_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        connection.commit()


def get_connection() -> sqlite3.Connection:
    init_db()
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(query, tuple(params)).fetchone()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(query, tuple(params)).fetchall()


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with get_connection() as connection:
        cursor = connection.execute(query, tuple(params))
        connection.commit()
        return cursor.lastrowid
