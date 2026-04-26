from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence

from fastapi import HTTPException

from app.db.database import deserialize_list, execute, fetch_all, fetch_one, serialize_list
from app.services.integrations import (
    fetch_project_delivery_scopes,
    list_project_integrations,
    list_workspace_integrations,
)
from app.services.project import (
    get_backlog_item,
    get_dashboard,
    get_project,
    list_backlog,
    list_project_members,
    require_project_member,
    require_project_pm,
)
from app.services.work_tracking import build_dashboard_areas, summarize_items


def get_project_settings(project_id: int, user_id: int) -> dict:
    row = get_project_settings_runtime(project_id, user_id)
    return row


def get_project_settings_runtime(project_id: int, user_id: int) -> dict:
    require_project_member(project_id, user_id)
    row = fetch_one(
        """
        SELECT *
        FROM project_settings
        WHERE project_id = ?
        """,
        (project_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project settings not found")
    return dict(row)


def update_project_settings(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    project = get_project(project_id, user_id)
    next_project = {**project}
    for key in ("name", "description", "goal", "priority", "mvp_scope"):
        if key in payload:
            next_project[key] = payload[key]
    next_tech_stack = payload.get("tech_stack", project["tech_stack"])
    execute(
        """
        UPDATE projects
        SET name = ?, description = ?, goal = ?, tech_stack = ?, priority = ?, mvp_scope = ?
        WHERE id = ?
        """,
        (
            next_project["name"],
            next_project["description"],
            next_project["goal"],
            serialize_list(next_tech_stack),
            next_project["priority"],
            next_project["mvp_scope"],
            project_id,
        ),
    )

    settings = get_project_settings(project_id, user_id)
    ai_prompt = payload.get("ai_prompt", settings["ai_prompt"])
    tech_stack_notes = payload.get("tech_stack_notes", settings["tech_stack_notes"])
    execute(
        """
        UPDATE project_settings
        SET ai_prompt = ?, tech_stack_notes = ?, summary_cache = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE project_id = ?
        """,
        (
            ai_prompt,
            tech_stack_notes,
            _build_summary_cache(project_id, ai_prompt, tech_stack_notes),
            user_id,
            project_id,
        ),
    )
    return get_project_settings(project_id, user_id)


def transfer_project_pm(project_id: int, user_id: int, new_pm_user_id: int) -> dict:
    require_project_pm(project_id, user_id)
    project = get_project(project_id, user_id)
    member_rows = list_project_members(project_id, user_id)
    if not any(member["user_id"] == new_pm_user_id for member in member_rows):
        raise HTTPException(status_code=400, detail="New PM must be a project member")

    execute("UPDATE projects SET pm_id = ? WHERE id = ?", (new_pm_user_id, project_id))
    execute(
        """
        INSERT INTO project_memory_entries (project_id, memory_type, title, content, created_by)
        VALUES (?, 'DECISION', ?, ?, ?)
        """,
        (
            project_id,
            "PM transfer",
            f"Project PM changed from user #{project['pm_id']} to user #{new_pm_user_id}.",
            user_id,
        ),
    )
    return get_project(project_id, user_id)


def list_domains(project_id: int, user_id: int) -> list[dict]:
    require_project_member(project_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM project_domains
        WHERE project_id = ?
        ORDER BY is_active DESC, code ASC, id ASC
        """,
        (project_id,),
    )
    return [dict(row) for row in rows]


def create_domain(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    domain_id = execute(
        """
        INSERT INTO project_domains (project_id, code, name, color)
        VALUES (?, ?, ?, ?)
        """,
        (
            project_id,
            payload["code"].strip().upper(),
            payload["name"].strip(),
            payload["color"].strip(),
        ),
    )
    row = fetch_one("SELECT * FROM project_domains WHERE id = ?", (domain_id,))
    return dict(row)


def update_domain(domain_id: int, user_id: int, payload: dict) -> dict:
    row = _get_domain(domain_id, user_id)
    require_project_pm(row["project_id"], user_id)
    next_row = {**row}
    for key in ("code", "name", "color", "is_active"):
        if key in payload:
            next_row[key] = payload[key]
    execute(
        """
        UPDATE project_domains
        SET code = ?, name = ?, color = ?, is_active = ?
        WHERE id = ?
        """,
        (
            str(next_row["code"]).upper(),
            next_row["name"],
            next_row["color"],
            bool(next_row["is_active"]),
            domain_id,
        ),
    )
    return _get_domain(domain_id, user_id)


def delete_domain(domain_id: int, user_id: int) -> None:
    row = _get_domain(domain_id, user_id)
    require_project_pm(row["project_id"], user_id)
    execute("DELETE FROM project_domain_mappings WHERE domain_id = ?", (domain_id,))
    execute("DELETE FROM project_domains WHERE id = ?", (domain_id,))


def list_domain_mappings(project_id: int, user_id: int) -> list[dict]:
    require_project_member(project_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM project_domain_mappings
        WHERE project_id = ?
        ORDER BY source ASC, match_field ASC, match_value ASC, id ASC
        """,
        (project_id,),
    )
    return [dict(row) for row in rows]


def create_domain_mapping(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    domain = _get_domain(payload["domain_id"], user_id)
    if domain["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="Domain does not belong to this project")
    mapping_id = execute(
        """
        INSERT INTO project_domain_mappings (project_id, domain_id, source, match_field, match_value)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            project_id,
            payload["domain_id"],
            payload["source"],
            payload["match_field"],
            payload["match_value"].strip(),
        ),
    )
    row = fetch_one("SELECT * FROM project_domain_mappings WHERE id = ?", (mapping_id,))
    return dict(row)


def delete_domain_mapping(mapping_id: int, user_id: int) -> None:
    row = fetch_one(
        """
        SELECT *
        FROM project_domain_mappings
        WHERE id = ?
        """,
        (mapping_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Domain mapping not found")
    require_project_pm(row["project_id"], user_id)
    execute("DELETE FROM project_domain_mappings WHERE id = ?", (mapping_id,))


def list_memories(project_id: int, user_id: int) -> list[dict]:
    require_project_member(project_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM project_memory_entries
        WHERE project_id = ? AND status = 'ACTIVE'
        ORDER BY created_at DESC, id DESC
        LIMIT 20
        """,
        (project_id,),
    )
    return [dict(row) for row in rows]


def create_memory_entry(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_member(project_id, user_id)
    memory_id = execute(
        """
        INSERT INTO project_memory_entries (project_id, memory_type, title, content, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            project_id,
            payload["memory_type"],
            payload["title"].strip(),
            payload["content"].strip(),
            user_id,
        ),
    )
    _refresh_project_summary(project_id, user_id)
    row = fetch_one("SELECT * FROM project_memory_entries WHERE id = ?", (memory_id,))
    return dict(row)


def ingest_meeting_note(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_member(project_id, user_id)
    meeting_content = payload["transcript"].strip()
    participants = payload.get("participants") or []
    header = f"Source: {payload['source']}"
    if participants:
        header = f"{header}\nParticipants: {', '.join(participants)}"
    return create_memory_entry(
        project_id,
        user_id,
        {
            "memory_type": "MEETING",
            "title": payload["title"],
            "content": f"{header}\n\n{meeting_content}",
        },
    )


async def build_delivery_dashboard(project_id: int, user_id: int) -> dict:
    scopes, warnings = await fetch_project_delivery_scopes(project_id, user_id)
    return _build_delivery_dashboard_from_scopes(project_id, user_id, scopes, warnings)


async def get_project_hub(project_id: int, user_id: int) -> dict:
    project = get_project(project_id, user_id)
    settings = get_project_settings(project_id, user_id)
    members = list_project_members(project_id, user_id)
    backlog = list_backlog(project_id, user_id)
    internal_dashboard = get_dashboard(project_id, user_id)
    domains = list_domains(project_id, user_id)
    domain_mappings = list_domain_mappings(project_id, user_id)
    workspace_integrations = list_workspace_integrations(project["workspace_id"], user_id)
    project_integrations = list_project_integrations(project_id, user_id)
    memories = list_memories(project_id, user_id)
    scopes, warnings = await fetch_project_delivery_scopes(project_id, user_id)
    delivery_dashboard = _build_delivery_dashboard_from_scopes(project_id, user_id, scopes, warnings)
    personal_recommendation = build_personal_recommendation(
        project_id,
        user_id,
        external_items=[item for scope in scopes for item in scope.items],
    )
    return {
        "project": project,
        "settings": settings,
        "permissions": {
            "current_user_id": user_id,
            "pm_user_id": project["pm_id"],
            "is_pm": project["pm_id"] == user_id,
        },
        "members": members,
        "backlog": backlog,
        "internal_dashboard": internal_dashboard,
        "delivery_dashboard": delivery_dashboard,
        "domains": domains,
        "domain_mappings": domain_mappings,
        "workspace_integrations": workspace_integrations,
        "project_integrations": project_integrations,
        "memories": memories,
        "personal_recommendation": personal_recommendation,
    }


def build_personal_recommendation(
    project_id: int,
    user_id: int,
    *,
    external_items: Sequence[Any] | None = None,
) -> dict:
    require_project_member(project_id, user_id)
    assigned_rows = fetch_all(
        """
        SELECT id, title, status, priority
        FROM issues
        WHERE project_id = ? AND assignee_id = ? AND status != 'DONE'
        ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id ASC
        """,
        (project_id, user_id),
    )
    current_assignments = [dict(row) for row in assigned_rows]
    project = get_project(project_id, user_id)
    settings = get_project_settings(project_id, user_id)
    memories = list_memories(project_id, user_id)
    context_notes = []
    if settings["ai_prompt"]:
        context_notes.append(settings["ai_prompt"])
    for memory in memories[:3]:
        context_notes.append(f"{memory['memory_type']}: {memory['title']}")

    normalized_excluded_titles = set(_collect_excluded_titles(project_id))
    recommended_items: list[dict] = []

    profiles = {
        member["user_id"]: member["project_profile"]
        for member in list_project_members(project_id, user_id)
        if member["project_profile"] is not None
    }
    profile = profiles.get(user_id)

    for backlog_item in list_backlog(project_id, user_id):
        if backlog_item["status"] not in {"OPEN", "READY"}:
            continue
        normalized_title = _normalize_title(backlog_item["title"])
        if normalized_title in normalized_excluded_titles:
            continue
        score = _score_candidate(backlog_item, profile)
        recommended_items.append(
            {
                "source": "internal_backlog",
                "id": backlog_item["id"],
                "title": backlog_item["title"],
                "priority": backlog_item["priority"],
                "score": score,
                "why": _candidate_reason(backlog_item, profile),
            }
        )

    for item in external_items or []:
        assignee_name = getattr(item, "assignee_name", None)
        status_category = getattr(item, "status_category", None)
        if status_category != "backlog":
            continue
        if assignee_name and assignee_name != project.get("name") and assignee_name != profiles.get(user_id, {}).get("user_name"):
            if assignee_name != fetch_one("SELECT name FROM users WHERE id = ?", (user_id,))["name"]:
                continue
        normalized_title = _normalize_title(getattr(item, "title", ""))
        if normalized_title in normalized_excluded_titles:
            continue
        score = _score_external_item(item, profile)
        recommended_items.append(
            {
                "source": getattr(item, "source", "external"),
                "id": getattr(item, "external_id", ""),
                "title": getattr(item, "title", ""),
                "priority": getattr(item, "priority", None),
                "score": score,
                "why": _external_candidate_reason(item, profile),
            }
        )

    recommended_items.sort(key=lambda item: (-item["score"], item["title"].lower()))
    if current_assignments:
        summary = "Keep moving your current assignments first before pulling new work."
    elif recommended_items:
        summary = "These are the best next pieces of work that are not already active or completed."
    else:
        summary = "No clear unclaimed work is available right now. Review new backlog or add more mappings."

    return {
        "summary": summary,
        "current_assignments": current_assignments,
        "recommended_backlog": recommended_items[:5],
        "context_notes": context_notes,
        "excluded_titles": sorted(normalized_excluded_titles),
    }


def _build_delivery_dashboard_from_scopes(
    project_id: int,
    user_id: int,
    scopes: Sequence[Any],
    warnings: Sequence[str],
) -> dict:
    require_project_member(project_id, user_id)
    all_items = [item for scope in scopes for item in scope.items]
    domains = [domain for domain in list_domains(project_id, user_id) if domain["is_active"]]
    mappings = list_domain_mappings(project_id, user_id)
    grouped_items: dict[int, list[Any]] = defaultdict(list)
    unmapped_count = 0
    for item in all_items:
        matched_ids = _match_domain_ids(item, domains, mappings)
        if not matched_ids:
            unmapped_count += 1
            continue
        for domain_id in matched_ids:
            grouped_items[domain_id].append(item)

    domain_summaries = []
    for domain in domains:
        items = grouped_items.get(domain["id"], [])
        if not items:
            continue
        summary = summarize_items(items)
        domain_summaries.append(
            {
                "domain_id": domain["id"],
                "code": domain["code"],
                "name": domain["name"],
                "color": domain["color"],
                "summary": summary,
                "sources": sorted({item.source for item in items}),
            }
        )

    domain_summaries.sort(
        key=lambda item: (-item["summary"].total_items, item["code"]),
    )
    summary = summarize_items(all_items)
    sources = build_dashboard_areas(all_items, group_by="source")
    active_items = [
        item
        for item in all_items
        if item.status_category in {"backlog", "in_progress"}
    ]
    active_items.sort(
        key=lambda item: (
            0 if item.status_category == "in_progress" else 1,
            (item.priority or "ZZZ"),
            item.title.lower(),
        )
    )
    return {
        "summary": summary,
        "sources": sources,
        "domains": domain_summaries,
        "active_items": active_items[:20],
        "unmapped_items": unmapped_count,
        "integration_warnings": list(warnings),
    }


def _refresh_project_summary(project_id: int, user_id: int) -> None:
    settings = get_project_settings(project_id, user_id)
    execute(
        """
        UPDATE project_settings
        SET summary_cache = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE project_id = ?
        """,
        (
            _build_summary_cache(project_id, settings["ai_prompt"], settings["tech_stack_notes"]),
            user_id,
            project_id,
        ),
    )


def _build_summary_cache(project_id: int, ai_prompt: str, tech_stack_notes: str) -> str:
    memory_rows = fetch_all(
        """
        SELECT memory_type, title
        FROM project_memory_entries
        WHERE project_id = ? AND status = 'ACTIVE'
        ORDER BY created_at DESC, id DESC
        LIMIT 5
        """,
        (project_id,),
    )
    parts = []
    if ai_prompt.strip():
        parts.append(ai_prompt.strip())
    if tech_stack_notes.strip():
        parts.append(tech_stack_notes.strip())
    if memory_rows:
        parts.append(
            "Recent memory: "
            + "; ".join(f"{row['memory_type']} - {row['title']}" for row in memory_rows)
        )
    return " | ".join(parts)


def _get_domain(domain_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT d.*
        FROM project_domains d
        JOIN projects p ON p.id = d.project_id
        JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE d.id = ?
        """,
        (user_id, domain_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project domain not found")
    return dict(row)


def _match_domain_ids(item: Any, domains: Sequence[dict], mappings: Sequence[dict]) -> list[int]:
    matched_ids = []
    for mapping in mappings:
        if _matches_mapping(item, mapping):
            matched_ids.append(mapping["domain_id"])

    if matched_ids:
        return sorted(set(matched_ids))

    for domain in domains:
        if _matches_domain_heuristic(item, domain):
            matched_ids.append(domain["id"])
    return sorted(set(matched_ids))


def _matches_mapping(item: Any, mapping: dict) -> bool:
    if mapping["source"] not in {"any", getattr(item, "source", "internal")}:
        return False

    field = mapping["match_field"]
    match_value = mapping["match_value"].strip().lower()
    candidates: list[str] = []
    if field == "label":
        candidates = [value.lower() for value in getattr(item, "labels", [])]
    elif field == "project":
        candidates = [str(getattr(item, "project_name", "")).lower()]
    elif field == "team":
        candidates = [str(getattr(item, "team_name", "")).lower()]
    elif field == "title":
        candidates = [str(getattr(item, "title", "")).lower()]
    elif field == "scope":
        candidates = [str(getattr(item, "scope_name", "")).lower()]
    elif field == "assignee":
        candidates = [str(getattr(item, "assignee_name", "")).lower()]
    elif field == "required_role":
        required_role = item.get("required_role") if isinstance(item, dict) else None
        candidates = [str(required_role or "").lower()]
    elif field == "tech_stack":
        values = item.get("required_tech_stack", []) if isinstance(item, dict) else []
        candidates = [str(value).lower() for value in values]
    return any(match_value in candidate for candidate in candidates if candidate)


def _matches_domain_heuristic(item: Any, domain: dict) -> bool:
    text_bits = [
        str(getattr(item, "title", "")),
        str(getattr(item, "project_name", "")),
        str(getattr(item, "team_name", "")),
        str(getattr(item, "scope_name", "")),
    ]
    text_bits.extend(getattr(item, "labels", []))
    haystack = " ".join(text_bits).lower()
    code = domain["code"].lower()
    name = domain["name"].lower()
    synonyms = {
        "be": ["backend", "api", "server"],
        "fe": ["frontend", "ui", "web", "client"],
        "de": ["data", "etl", "pipeline", "warehouse", "ml"],
    }
    values = [code, name]
    values.extend(synonyms.get(code, []))
    return any(value and value in haystack for value in values)


def _collect_excluded_titles(project_id: int) -> set[str]:
    rows = fetch_all(
        """
        SELECT title
        FROM issues
        WHERE project_id = ? AND status IN ('TODO', 'IN_PROGRESS', 'REVIEW', 'DONE')
        """,
        (project_id,),
    )
    return {_normalize_title(row["title"]) for row in rows if row.get("title")}


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _score_candidate(backlog_item: dict, profile: dict | None) -> int:
    score = 1
    if profile is None:
        return score
    if backlog_item.get("required_role") and _role_matches(backlog_item["required_role"], profile["project_role"]):
        score += 3
    tech_stack = set(backlog_item["required_tech_stack"])
    if tech_stack:
        score += min(2, len(tech_stack & set(profile["tech_stack"])))
    if _keyword_match(backlog_item["title"], backlog_item["description"], profile["strong_tasks"]):
        score += 2
    if _keyword_match(backlog_item["title"], backlog_item["description"], profile["disliked_tasks"]):
        score -= 2
    return score


def _score_external_item(item: Any, profile: dict | None) -> int:
    score = 1
    if profile is None:
        return score
    labels = getattr(item, "labels", [])
    text = f"{getattr(item, 'title', '')} {' '.join(labels)}"
    if _keyword_match(text, "", profile["strong_tasks"]):
        score += 2
    if _keyword_match(text, "", profile["disliked_tasks"]):
        score -= 2
    for tech in profile["tech_stack"]:
        if tech.lower() in text.lower():
            score += 1
    return score


def _candidate_reason(backlog_item: dict, profile: dict | None) -> str:
    if profile is None:
        return "Open backlog work with no existing owner."
    reasons = []
    if backlog_item.get("required_role") and _role_matches(backlog_item["required_role"], profile["project_role"]):
        reasons.append("role fit")
    if _keyword_match(backlog_item["title"], backlog_item["description"], profile["strong_tasks"]):
        reasons.append("matches your strengths")
    if not reasons:
        reasons.append("currently unclaimed")
    return ", ".join(reasons)


def _external_candidate_reason(item: Any, profile: dict | None) -> str:
    if profile is None:
        return "Open work from the connected delivery tool."
    reasons = []
    labels = getattr(item, "labels", [])
    text = f"{getattr(item, 'title', '')} {' '.join(labels)}"
    if _keyword_match(text, "", profile["strong_tasks"]):
        reasons.append("matches your strengths")
    if labels:
        reasons.append(f"labels: {', '.join(labels[:3])}")
    if not reasons:
        reasons.append("open external backlog work")
    return ", ".join(reasons)


def _keyword_match(title: str, description: str, keywords: list[str]) -> bool:
    text = f"{title} {description}".lower()
    return any(keyword.lower() in text for keyword in keywords)


def _role_matches(required_role: str, project_role: str) -> bool:
    normalized_required = required_role.strip().upper()
    normalized_role = project_role.strip().upper()
    mapping = {
        "BACKEND": {"BACKEND", "BE", "FULLSTACK"},
        "FRONTEND": {"FRONTEND", "FE", "FULLSTACK"},
        "DATA": {"DATA", "DE", "FULLSTACK"},
        "BE": {"BACKEND", "BE", "FULLSTACK"},
        "FE": {"FRONTEND", "FE", "FULLSTACK"},
        "DE": {"DATA", "DE", "FULLSTACK"},
    }
    if normalized_required == normalized_role:
        return True
    return normalized_role in mapping.get(normalized_required, set())
