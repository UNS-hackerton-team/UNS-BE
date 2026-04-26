from __future__ import annotations

import json
import re
from typing import Any, Sequence

import httpx

from app.core.config import get_settings
from app.services.project import get_dashboard, get_project
from app.services.project_hub import (
    build_delivery_dashboard,
    build_personal_recommendation,
    get_project_settings_runtime,
    list_memories,
)


async def generate_project_agent_reply(
    project_id: int,
    user: dict,
    room_type: str,
    content: str,
    history: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    settings = get_project_settings_runtime(project_id, user["id"])
    app_settings = get_settings()
    api_key = (app_settings.gemini_api_key or "").strip()
    if not api_key:
        return None

    model = app_settings.gemini_model.strip()
    project = get_project(project_id, user["id"])
    internal_dashboard = get_dashboard(project_id, user["id"])
    delivery_dashboard = await build_delivery_dashboard(project_id, user["id"])
    personal_recommendation = build_personal_recommendation(
        project_id,
        user["id"],
        external_items=delivery_dashboard["active_items"],
    )
    memories = list_memories(project_id, user["id"])[:5]

    prompt = _build_prompt(
        room_type=room_type,
        content=content,
        project=project,
        settings=settings,
        internal_dashboard=internal_dashboard,
        delivery_dashboard=delivery_dashboard,
        personal_recommendation=personal_recommendation,
        memories=memories,
        history=history,
        user=user,
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "topP": 0.9,
                },
            },
        )
    if response.status_code >= 400:
        return {
            "summary": f"Gemini request failed ({response.status_code}). Falling back to local planner.",
            "provider": "gemini",
            "error": response.text,
        }

    payload = response.json()
    text = _extract_text(payload)
    if not text:
        return {
            "summary": "Gemini returned an empty answer. Falling back to local planner.",
            "provider": "gemini",
        }
    parsed = _parse_json_answer(text)
    parsed.setdefault("summary", text.strip())
    parsed["provider"] = "gemini"
    return parsed


def _build_prompt(
    *,
    room_type: str,
    content: str,
    project: dict,
    settings: dict,
    internal_dashboard: dict,
    delivery_dashboard: dict,
    personal_recommendation: dict,
    memories: Sequence[dict],
    history: Sequence[dict[str, Any]],
    user: dict,
) -> str:
    role_instruction = (
        "You are the personal project AI for a single contributor."
        if room_type == "PERSONAL_AI"
        else "You are the shared project AI for the whole delivery team."
    )
    history_lines = [
        f"{entry.get('sender_type', entry.get('role', 'USER'))}: {entry.get('content', '')}"
        for entry in history[-8:]
    ]
    memory_lines = [f"{memory['memory_type']}: {memory['title']}" for memory in memories]
    domain_lines = [
        (
            f"{domain['code']} - {domain['summary'].done_items}/"
            f"{domain['summary'].total_items} done"
        )
        for domain in delivery_dashboard.get("domains", [])
    ]
    recommended_titles = [
        item["title"]
        for item in personal_recommendation.get("recommended_backlog", [])[:5]
    ]

    return (
        f"{role_instruction}\n"
        "Use the project context below. Do not recommend work that is already in progress or done.\n"
        "Return valid JSON only with these keys: "
        "summary, next_action, recommended_tasks, risks, current_assignments, recommended_order, context_notes.\n\n"
        f"Project: {project['name']}\n"
        f"Goal: {project['goal']}\n"
        f"Priority: {project['priority']}\n"
        f"Tech stack: {', '.join(project['tech_stack'])}\n"
        f"Project AI prompt: {settings.get('ai_prompt', '')}\n"
        f"Project summary cache: {settings.get('summary_cache', '')}\n"
        f"Current user: {user['name']}\n"
        f"Internal dashboard: {json.dumps(internal_dashboard, ensure_ascii=False)}\n"
        f"Delivery summary: {json.dumps(_summarize_delivery(delivery_dashboard), ensure_ascii=False)}\n"
        f"Domain progress: {', '.join(domain_lines) if domain_lines else 'No mapped domain progress yet'}\n"
        f"Suggested open work: {', '.join(recommended_titles) if recommended_titles else 'No suggested work'}\n"
        f"Recent project memories: {' | '.join(memory_lines) if memory_lines else 'None'}\n"
        f"Recent chat history: {' | '.join(history_lines) if history_lines else 'No previous chat'}\n\n"
        f"User question: {content}"
    )


def _summarize_delivery(delivery_dashboard: dict) -> dict[str, Any]:
    summary = delivery_dashboard.get("summary")
    if summary is None:
        return {}
    return {
        "total_items": summary.total_items,
        "backlog_items": summary.backlog_items,
        "in_progress_items": summary.in_progress_items,
        "done_items": summary.done_items,
        "unmapped_items": delivery_dashboard.get("unmapped_items", 0),
        "warnings": delivery_dashboard.get("integration_warnings", []),
    }


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "\n".join(texts).strip()


def _parse_json_answer(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"summary": text.strip()}
