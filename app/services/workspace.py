import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status

from app.db.database import execute, fetch_all, fetch_one


def _generate_invite_code() -> str:
    return secrets.token_hex(3).upper()


def create_workspace(owner_id: int, name: str, description: str, team_type: str) -> dict:
    invite_code = _generate_invite_code()
    workspace_id = execute(
        """
        INSERT INTO workspaces (
            name, description, team_type, owner_id, invite_code
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (name, description, team_type, owner_id, invite_code),
    )
    execute(
        """
        INSERT INTO workspace_members (workspace_id, user_id, workspace_role)
        VALUES (?, ?, 'OWNER')
        """,
        (workspace_id, owner_id),
    )
    return get_workspace(workspace_id, owner_id)


def list_workspaces(user_id: int) -> list[dict]:
    rows = fetch_all(
        """
        SELECT
            w.id,
            w.name,
            w.description,
            w.team_type,
            w.owner_id,
            membership.workspace_role,
            w.invite_code_active,
            (
                SELECT COUNT(*)
                FROM workspace_members wm
                WHERE wm.workspace_id = w.id
            ) AS member_count,
            w.created_at
        FROM workspaces w
        JOIN workspace_members membership
            ON membership.workspace_id = w.id
        WHERE membership.user_id = ?
        ORDER BY w.created_at DESC, w.id DESC
        """,
        (user_id,),
    )
    return [dict(row) for row in rows]


def get_workspace(workspace_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT
            w.*,
            (SELECT COUNT(*) FROM workspace_members wm WHERE wm.workspace_id = w.id) AS member_count
        FROM workspaces w
        JOIN workspace_members membership
            ON membership.workspace_id = w.id AND membership.user_id = ?
        WHERE w.id = ?
        """,
        (user_id, workspace_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return dict(row)


def get_workspace_role(workspace_id: int, user_id: int) -> Optional[str]:
    row = fetch_one(
        """
        SELECT workspace_role
        FROM workspace_members
        WHERE workspace_id = ? AND user_id = ?
        """,
        (workspace_id, user_id),
    )
    if row is None:
        return None
    return row["workspace_role"]


def require_workspace_member(workspace_id: int, user_id: int) -> None:
    if get_workspace_role(workspace_id, user_id) is None:
        raise HTTPException(status_code=403, detail="Workspace access denied")


def require_workspace_owner(workspace_id: int, user_id: int) -> None:
    role = get_workspace_role(workspace_id, user_id)
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Workspace owner access required")


def get_invite_info(workspace_id: int, user_id: int, base_url: str) -> dict:
    require_workspace_member(workspace_id, user_id)
    workspace = get_workspace(workspace_id, user_id)
    return {
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
        "invite_code": workspace["invite_code"],
        "invite_url": f"{base_url}/invite/{workspace['invite_code']}",
        "invite_code_active": bool(workspace["invite_code_active"]),
        "invite_code_expires_at": workspace["invite_code_expires_at"],
        "invite_code_max_uses": workspace["invite_code_max_uses"],
        "invite_code_used_count": workspace["invite_code_used_count"],
        "member_count": workspace["member_count"],
    }


def regenerate_invite(
    workspace_id: int,
    user_id: int,
    expires_at: Optional[str],
    max_uses: Optional[int],
    base_url: str,
) -> dict:
    require_workspace_owner(workspace_id, user_id)
    execute(
        """
        UPDATE workspaces
        SET invite_code = ?, invite_code_active = 1, invite_code_expires_at = ?, invite_code_max_uses = ?, invite_code_used_count = 0
        WHERE id = ?
        """,
        (_generate_invite_code(), expires_at, max_uses, workspace_id),
    )
    return get_invite_info(workspace_id, user_id, base_url)


def deactivate_invite(workspace_id: int, user_id: int, base_url: str) -> dict:
    require_workspace_owner(workspace_id, user_id)
    execute(
        "UPDATE workspaces SET invite_code_active = 0 WHERE id = ?",
        (workspace_id,),
    )
    return get_invite_info(workspace_id, user_id, base_url)


def _load_workspace_by_invite(invite_code: str) -> dict:
    row = fetch_one(
        """
        SELECT id, name, invite_code_active, invite_code_expires_at,
               invite_code_max_uses, invite_code_used_count
        FROM workspaces
        WHERE invite_code = ?
        """,
        (invite_code,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    return dict(row)


def validate_invite_code(invite_code: str) -> dict:
    workspace = _load_workspace_by_invite(invite_code)
    valid = True
    message = "Invite is valid"

    if not workspace["invite_code_active"]:
        valid = False
        message = "Invite is inactive"
    if valid and workspace["invite_code_expires_at"]:
        expires_at = datetime.fromisoformat(workspace["invite_code_expires_at"])
        if expires_at < datetime.utcnow():
            valid = False
            message = "Invite is expired"
    if valid and workspace["invite_code_max_uses"] is not None:
        if workspace["invite_code_used_count"] >= workspace["invite_code_max_uses"]:
            valid = False
            message = "Invite usage limit reached"

    return {
        "valid": valid,
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
        "message": message,
        "invite_code_active": bool(workspace["invite_code_active"]),
    }


def join_workspace_by_invite(invite_code: str, user_id: int) -> dict:
    invite = validate_invite_code(invite_code)
    if not invite["valid"]:
        raise HTTPException(status_code=400, detail=invite["message"])

    existing = fetch_one(
        """
        SELECT workspace_role
        FROM workspace_members
        WHERE workspace_id = ? AND user_id = ?
        """,
        (invite["workspace_id"], user_id),
    )
    if existing is None:
        execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, workspace_role)
            VALUES (?, ?, 'MEMBER')
            """,
            (invite["workspace_id"], user_id),
        )
        execute(
            """
            UPDATE workspaces
            SET invite_code_used_count = invite_code_used_count + 1
            WHERE id = ?
            """,
            (invite["workspace_id"],),
        )
        return {
            "workspace_id": invite["workspace_id"],
            "workspace_name": invite["workspace_name"],
            "joined": True,
            "workspace_role": "MEMBER",
        }

    return {
        "workspace_id": invite["workspace_id"],
        "workspace_name": invite["workspace_name"],
        "joined": False,
        "workspace_role": existing["workspace_role"],
    }
