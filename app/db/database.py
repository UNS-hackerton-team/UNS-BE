import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings


metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(50), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

workspaces_table = Table(
    "workspaces",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
    Column("description", Text),
    Column("team_type", String(50), nullable=False),
    Column("owner_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("invite_code", String(20), nullable=False, unique=True),
    Column("invite_code_active", Boolean, nullable=False, server_default="true"),
    Column("invite_code_expires_at", String(50)),
    Column("invite_code_max_uses", Integer),
    Column("invite_code_used_count", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

workspace_members_table = Table(
    "workspace_members",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("workspace_role", String(20), nullable=False, server_default="MEMBER"),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
)

projects_table = Table(
    "projects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("description", Text, nullable=False),
    Column("goal", Text, nullable=False),
    Column("tech_stack", Text, nullable=False),
    Column("start_date", String(30)),
    Column("end_date", String(30)),
    Column("pm_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("priority", String(20), nullable=False),
    Column("mvp_scope", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

project_members_table = Table(
    "project_members",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("project_role", String(50), nullable=False),
    Column("tech_stack", Text, nullable=False),
    Column("strong_tasks", Text, nullable=False),
    Column("disliked_tasks", Text, nullable=False),
    Column("available_hours_per_day", Integer, nullable=False),
    Column("experience_level", String(30), nullable=False),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
)

sprints_table = Table(
    "sprints",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("goal", Text, nullable=False),
    Column("start_date", String(30), nullable=False),
    Column("end_date", String(30), nullable=False),
    Column("status", String(20), nullable=False, server_default="PLANNED"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

backlog_items_table = Table(
    "backlog_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=False),
    Column("priority", String(20), nullable=False),
    Column("required_role", String(50)),
    Column("required_tech_stack", Text, nullable=False),
    Column("difficulty", String(20), nullable=False),
    Column("estimated_hours", Integer, nullable=False),
    Column("status", String(20), nullable=False, server_default="OPEN"),
    Column("linked_issue_id", Integer),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

issues_table = Table(
    "issues",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("sprint_id", Integer, ForeignKey("sprints.id", ondelete="SET NULL")),
    Column("backlog_item_id", Integer, ForeignKey("backlog_items.id", ondelete="SET NULL")),
    Column("assignee_id", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=False),
    Column("status", String(20), nullable=False, server_default="TODO"),
    Column("priority", String(20), nullable=False),
    Column("difficulty", String(20), nullable=False),
    Column("estimated_hours", Integer, nullable=False),
    Column("required_role", String(50)),
    Column("required_tech_stack", Text, nullable=False),
    Column("assignment_reason", Text),
    Column("due_date", String(30)),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

chat_rooms_table = Table(
    "chat_rooms",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("type", String(20), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("project_id", "type", "user_id", name="uq_chat_rooms_project_type_user"),
)

chat_messages_table = Table(
    "chat_messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chat_room_id", Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
    Column("sender_id", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("sender_type", String(10), nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

project_settings_table = Table(
    "project_settings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("ai_prompt", Text, nullable=False, server_default=""),
    Column("tech_stack_notes", Text, nullable=False, server_default=""),
    Column("summary_cache", Text, nullable=False, server_default=""),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("updated_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("project_id", name="uq_project_settings_project"),
)

project_domains_table = Table(
    "project_domains",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("code", String(20), nullable=False),
    Column("name", String(50), nullable=False),
    Column("color", String(20), nullable=False, server_default="#0F172A"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("project_id", "code", name="uq_project_domains_project_code"),
)

project_domain_mappings_table = Table(
    "project_domain_mappings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("domain_id", Integer, ForeignKey("project_domains.id", ondelete="CASCADE"), nullable=False),
    Column("source", String(20), nullable=False, server_default="any"),
    Column("match_field", String(30), nullable=False),
    Column("match_value", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

workspace_integrations_table = Table(
    "workspace_integrations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(20), nullable=False),
    Column("external_workspace_id", String(255), nullable=False),
    Column("external_workspace_name", String(255), nullable=False),
    Column("external_workspace_url", String(255)),
    Column("access_token", Text),
    Column("refresh_token", Text),
    Column("token_expires_at", String(50)),
    Column("scope", Text),
    Column("status", String(20), nullable=False, server_default="CONNECTED"),
    Column("connected_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint(
        "workspace_id",
        "provider",
        "external_workspace_id",
        name="uq_workspace_integrations_workspace_provider_external",
    ),
)

oauth_states_table = Table(
    "oauth_states",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(20), nullable=False),
    Column("state", String(120), nullable=False, unique=True),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("redirect_to", String(255)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

project_integrations_table = Table(
    "project_integrations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column(
        "workspace_integration_id",
        Integer,
        ForeignKey("workspace_integrations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("provider", String(20), nullable=False),
    Column("scope_type", String(30), nullable=False),
    Column("scope_id", String(255), nullable=False),
    Column("scope_name", String(255), nullable=False),
    Column("settings", Text, nullable=False, server_default="{}"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint(
        "project_id",
        "provider",
        "scope_id",
        name="uq_project_integrations_project_provider_scope",
    ),
)

project_memory_entries_table = Table(
    "project_memory_entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("memory_type", String(30), nullable=False),
    Column("title", String(255), nullable=False),
    Column("content", Text, nullable=False),
    Column("status", String(20), nullable=False, server_default="ACTIVE"),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def serialize_list(values: Optional[list[str]]) -> str:
    return json.dumps(values or [])


def deserialize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


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
    engine = _get_engine(database_url)
    metadata.create_all(engine)
    _run_bootstrap_migrations(engine)


def reset_db_state() -> None:
    try:
        get_engine().dispose()
    except Exception:
        pass
    _get_engine.cache_clear()
    table_has_column.cache_clear()


def _run_bootstrap_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []
    if "name" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN name VARCHAR(50)")
    if "email" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN email VARCHAR(255)")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        if "username" in columns:
            connection.execute(
                text(
                    """
                    UPDATE users
                    SET name = COALESCE(NULLIF(name, ''), username)
                    WHERE name IS NULL OR name = ''
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE users
                    SET email = COALESCE(NULLIF(email, ''), LOWER(username) || '.' || id || '@local.uns')
                    WHERE email IS NULL OR email = ''
                    """
                )
            )

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email
                ON users (email)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_users_name
                ON users (name)
                """
            )
        )


def _backend_name() -> str:
    return make_url(_database_url()).get_backend_name()


@lru_cache
def table_has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(get_engine())
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _prepare_query(query: str, backend_name: str, is_insert: bool) -> str:
    normalized = query.strip().rstrip(";")
    if backend_name != "sqlite":
        normalized = normalized.replace("?", "%s")
        if is_insert and "RETURNING" not in normalized.upper():
            normalized = f"{normalized} RETURNING id"
    return normalized


def _row_to_dict(cursor: Any, row: Any) -> dict:
    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[dict]:
    connection = get_engine().raw_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(query, _backend_name(), False), tuple(params))
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_dict(cursor, row)
    finally:
        cursor.close()
        connection.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict]:
    connection = get_engine().raw_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(query, _backend_name(), False), tuple(params))
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def execute(query: str, params: Iterable[Any] = ()) -> int:
    backend_name = _backend_name()
    is_insert = query.lstrip().upper().startswith("INSERT INTO")
    connection = get_engine().raw_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(query, backend_name, is_insert), tuple(params))
        if is_insert:
            if backend_name == "sqlite":
                result = cursor.lastrowid
            else:
                result = cursor.fetchone()[0]
        else:
            result = cursor.rowcount
        connection.commit()
        return result
    finally:
        cursor.close()
        connection.close()
