from typing import Optional

from app.db.database import execute, fetch_all, fetch_one
from app.services.project import get_dashboard, get_project, require_project_member


def send_team_message(project_id: int, user: dict, content: str) -> dict:
    require_project_member(project_id, user["id"])
    room_id = _get_or_create_room(project_id, "TEAM_AI", None)
    user_message_id = execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_id, sender_type, content)
        VALUES (?, ?, 'USER', ?)
        """,
        (room_id, user["id"], content),
    )
    answer = _build_team_answer(project_id, content, user["id"])
    ai_message_id = execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_type, content, metadata)
        VALUES (?, 'AI', ?, ?)
        """,
        (room_id, answer["summary"], answer["json"]),
    )
    return {
        "user_message_id": user_message_id,
        "ai_message_id": ai_message_id,
        "room_type": "TEAM_AI",
        "answer": answer["payload"],
    }


def send_personal_message(project_id: int, user: dict, content: str) -> dict:
    require_project_member(project_id, user["id"])
    room_id = _get_or_create_room(project_id, "PERSONAL_AI", user["id"])
    user_message_id = execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_id, sender_type, content)
        VALUES (?, ?, 'USER', ?)
        """,
        (room_id, user["id"], content),
    )
    answer = _build_personal_answer(project_id, user["id"], content)
    ai_message_id = execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_type, content, metadata)
        VALUES (?, 'AI', ?, ?)
        """,
        (room_id, answer["summary"], answer["json"]),
    )
    return {
        "user_message_id": user_message_id,
        "ai_message_id": ai_message_id,
        "room_type": "PERSONAL_AI",
        "answer": answer["payload"],
    }


def _get_or_create_room(project_id: int, room_type: str, user_id: Optional[int]) -> int:
    if user_id is None:
        row = fetch_one(
            """
            SELECT id
            FROM chat_rooms
            WHERE project_id = ? AND type = ? AND user_id IS NULL
            """,
            (project_id, room_type),
        )
    else:
        row = fetch_one(
            """
            SELECT id
            FROM chat_rooms
            WHERE project_id = ? AND type = ? AND user_id = ?
            """,
            (project_id, room_type, user_id),
        )
    if row is not None:
        return row["id"]
    return execute(
        """
        INSERT INTO chat_rooms (project_id, type, user_id)
        VALUES (?, ?, ?)
        """,
        (project_id, room_type, user_id),
    )


def _build_team_answer(project_id: int, content: str, user_id: int) -> dict:
    project = get_project(project_id, user_id)
    dashboard = get_dashboard(project_id, user_id)
    next_issue = dashboard.get("recommended_next_issue")
    payload = {
        "summary": f"Project {project['name']} should stay focused on MVP-critical work.",
        "recommended_tasks": [next_issue] if next_issue else [],
        "risks": dashboard["risk_issues"],
        "next_action": (
            f"Start with issue #{next_issue['id']} - {next_issue['title']}"
            if next_issue
            else "Create or assign the next highest-priority issue."
        ),
        "priority": "HIGH",
        "reasoning": dashboard["bottleneck_summary"],
        "question": content,
    }
    import json

    return {
        "summary": payload["summary"],
        "json": json.dumps(payload),
        "payload": payload,
    }


def _build_personal_answer(project_id: int, user_id: int, content: str) -> dict:
    rows = fetch_all(
        """
        SELECT id, title, status, priority
        FROM issues
        WHERE project_id = ? AND assignee_id = ? AND status != 'DONE'
        ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id ASC
        """,
        (project_id, user_id),
    )
    issues = [dict(row) for row in rows]
    top_issue = issues[0] if issues else None
    payload = {
        "summary": "Focus on your highest-priority assigned work first.",
        "current_assignments": issues,
        "recommended_order": [
            "Clarify acceptance criteria",
            "Implement the smallest working slice",
            "Test the result",
            "Move the issue to REVIEW",
        ],
        "top_priority_issue": top_issue,
        "question": content,
    }
    import json

    return {
        "summary": payload["summary"],
        "json": json.dumps(payload),
        "payload": payload,
    }
