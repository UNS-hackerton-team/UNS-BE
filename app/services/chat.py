from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Optional

from fastapi import WebSocket

from app.db.database import execute, fetch_all, fetch_one
from app.services.gemini_agent import generate_project_agent_reply
from app.services.project import get_dashboard, get_project, require_project_member
from app.services.project_hub import build_delivery_dashboard, build_personal_recommendation


class ChatConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, room_key: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[room_key].add(websocket)

    def disconnect(self, room_key: str, websocket: WebSocket) -> None:
        connections = self._connections.get(room_key)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(room_key, None)

    async def broadcast(self, room_key: str, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in self._connections.get(room_key, set()):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(room_key, websocket)


connection_manager = ChatConnectionManager()


async def send_team_message(project_id: int, user: dict, content: str) -> dict:
    require_project_member(project_id, user["id"])
    room_id = _get_or_create_room(project_id, "TEAM_AI", None)
    user_message_id = _store_user_message(room_id, user["id"], content)
    history = _list_room_messages(room_id, limit=12)
    answer = await _build_team_answer(project_id, content, user, history)
    ai_message_id = _store_ai_message(room_id, answer)
    return {
        "user_message_id": user_message_id,
        "ai_message_id": ai_message_id,
        "room_type": "TEAM_AI",
        "answer": answer,
    }


async def send_personal_message(project_id: int, user: dict, content: str) -> dict:
    require_project_member(project_id, user["id"])
    room_id = _get_or_create_room(project_id, "PERSONAL_AI", user["id"])
    user_message_id = _store_user_message(room_id, user["id"], content)
    history = _list_room_messages(room_id, limit=12)
    answer = await _build_personal_answer(project_id, user, content, history)
    ai_message_id = _store_ai_message(room_id, answer)
    return {
        "user_message_id": user_message_id,
        "ai_message_id": ai_message_id,
        "room_type": "PERSONAL_AI",
        "answer": answer,
    }


def get_team_history(project_id: int, user_id: int) -> dict:
    require_project_member(project_id, user_id)
    room_id = _get_or_create_room(project_id, "TEAM_AI", None)
    return {
        "room_type": "TEAM_AI",
        "messages": _list_room_messages(room_id, limit=100),
    }


def get_personal_history(project_id: int, user_id: int) -> dict:
    require_project_member(project_id, user_id)
    room_id = _get_or_create_room(project_id, "PERSONAL_AI", user_id)
    return {
        "room_type": "PERSONAL_AI",
        "messages": _list_room_messages(room_id, limit=100),
    }


def room_key(project_id: int, room_type: str, user_id: Optional[int]) -> str:
    return f"{project_id}:{room_type}:{user_id or 'shared'}"


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


def _store_user_message(room_id: int, user_id: int, content: str) -> int:
    return execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_id, sender_type, content)
        VALUES (?, ?, 'USER', ?)
        """,
        (room_id, user_id, content),
    )


def _store_ai_message(room_id: int, answer: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO chat_messages (chat_room_id, sender_type, content, metadata)
        VALUES (?, 'AI', ?, ?)
        """,
        (room_id, _answer_summary(answer), json.dumps(answer)),
    )


async def _build_team_answer(
    project_id: int,
    content: str,
    user: dict,
    history: list[dict],
) -> dict:
    gemini_answer = await generate_project_agent_reply(
        project_id,
        user,
        "TEAM_AI",
        content,
        history,
    )
    if gemini_answer and "error" not in gemini_answer:
        return gemini_answer

    project = get_project(project_id, user["id"])
    dashboard = get_dashboard(project_id, user["id"])
    delivery_dashboard = await build_delivery_dashboard(project_id, user["id"])
    next_item = delivery_dashboard["active_items"][0] if delivery_dashboard["active_items"] else None
    domain_focus = delivery_dashboard["domains"][0] if delivery_dashboard["domains"] else None
    answer = {
        "summary": f"{project['name']} should keep focus on the smallest unblocked MVP slice.",
        "recommended_tasks": [serialize_work_item(next_item)] if next_item else [],
        "risks": dashboard["risk_issues"],
        "next_action": (
            f"Pull '{next_item.title}' next."
            if next_item
            else "Map external delivery scopes or create the next backlog issue."
        ),
        "priority": project["priority"],
        "reasoning": (
            f"Most active delivery pressure is in {domain_focus['code']}."
            if domain_focus
            else dashboard["bottleneck_summary"]
        ),
        "context_notes": delivery_dashboard["integration_warnings"],
        "question": content,
        "provider": "local",
    }
    if gemini_answer and gemini_answer.get("error"):
        answer["context_notes"] = answer["context_notes"] + [gemini_answer["summary"]]
    return answer


async def _build_personal_answer(
    project_id: int,
    user: dict,
    content: str,
    history: list[dict],
) -> dict:
    gemini_answer = await generate_project_agent_reply(
        project_id,
        user,
        "PERSONAL_AI",
        content,
        history,
    )
    if gemini_answer and "error" not in gemini_answer:
        return gemini_answer

    recommendation = build_personal_recommendation(project_id, user["id"])
    answer = {
        "summary": recommendation["summary"],
        "current_assignments": recommendation["current_assignments"],
        "recommended_tasks": recommendation["recommended_backlog"],
        "recommended_order": [
            "Finish your current assigned work first",
            "Pull the highest-fit unclaimed backlog item",
            "Confirm scope with PM if the task is ambiguous",
            "Move active work to review as soon as the smallest slice is done",
        ],
        "context_notes": recommendation["context_notes"],
        "question": content,
        "provider": "local",
    }
    if gemini_answer and gemini_answer.get("error"):
        answer["context_notes"] = answer["context_notes"] + [gemini_answer["summary"]]
    return answer


def _list_room_messages(room_id: int, *, limit: int) -> list[dict]:
    rows = fetch_all(
        """
        SELECT *
        FROM chat_messages
        WHERE chat_room_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (room_id, limit),
    )
    messages = [dict(row) for row in rows]
    messages.reverse()
    return messages


def _answer_summary(answer: dict[str, Any]) -> str:
    summary = answer.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    next_action = answer.get("next_action")
    if isinstance(next_action, str) and next_action.strip():
        return next_action.strip()
    return json.dumps(answer)


def serialize_work_item(item: Any | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "source": getattr(item, "source", None),
        "external_id": getattr(item, "external_id", None),
        "title": getattr(item, "title", None),
        "status_name": getattr(item, "status_name", None),
        "status_category": getattr(item, "status_category", None),
        "priority": getattr(item, "priority", None),
        "assignee_name": getattr(item, "assignee_name", None),
        "url": getattr(item, "url", None),
    }
