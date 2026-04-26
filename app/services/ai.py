from __future__ import annotations

from collections import Counter

from fastapi import HTTPException

from app.db.database import execute, fetch_one, serialize_list
from app.services.project import (
    create_backlog_item,
    get_backlog_item,
    get_project,
    list_backlog,
    list_project_members,
    require_project_member,
    require_project_pm,
)


def generate_project_tasks(project_id: int, user_id: int, create_backlog: bool) -> dict:
    require_project_pm(project_id, user_id)
    project = get_project(project_id, user_id)
    members = list_project_members(project_id, user_id)
    roles = [m["project_profile"]["project_role"] for m in members if m["project_profile"]]
    role_counts = Counter(role.upper() for role in roles)

    tasks = [
        {
            "title": "Define MVP scope and acceptance criteria",
            "description": f"Break down the MVP scope for {project['name']} into clear deliverables and acceptance criteria.",
            "required_role": "PM",
            "required_tech_stack": [],
            "difficulty": "MEDIUM",
            "estimated_hours": 2,
            "priority": "HIGH",
        },
        {
            "title": "Set up project foundation",
            "description": f"Initialize repository structure and base architecture for {project['name']}.",
            "required_role": "BACKEND" if role_counts.get("BACKEND", 0) or role_counts.get("BE", 0) else "FULLSTACK",
            "required_tech_stack": project["tech_stack"][:2],
            "difficulty": "MEDIUM",
            "estimated_hours": 3,
            "priority": "HIGH",
        },
        {
            "title": "Implement core user flow",
            "description": f"Build the most critical user flow needed to achieve the goal: {project['goal']}.",
            "required_role": "FULLSTACK" if role_counts.get("FULLSTACK", 0) else "FRONTEND",
            "required_tech_stack": project["tech_stack"][:3],
            "difficulty": "HIGH",
            "estimated_hours": 6,
            "priority": "HIGH",
        },
        {
            "title": "Create API and data contracts",
            "description": "Define the interfaces between client, server, and persistence layers for the MVP.",
            "required_role": "BACKEND",
            "required_tech_stack": project["tech_stack"][:3],
            "difficulty": "MEDIUM",
            "estimated_hours": 4,
            "priority": "HIGH",
        },
        {
            "title": "Run integration test and demo prep",
            "description": "Validate the end-to-end scenario and prepare a clean demo path for the sprint review.",
            "required_role": "PM" if role_counts.get("PM", 0) else "FULLSTACK",
            "required_tech_stack": [],
            "difficulty": "LOW",
            "estimated_hours": 2,
            "priority": "MEDIUM",
        },
    ]

    created_backlog_items = []
    if create_backlog:
        existing_titles = {item["title"] for item in list_backlog(project_id, user_id)}
        for task in tasks:
            if task["title"] in existing_titles:
                continue
            item = create_backlog_item(project_id, user_id, task)
            created_backlog_items.append(item["id"])

    return {
        "project_summary": (
            f"{project['name']} targets {project['goal']}. "
            "The initial plan prioritizes scope definition, foundation work, core flow implementation, "
            "API/data alignment, and demo readiness."
        ),
        "tasks": tasks,
        "created_backlog_items": created_backlog_items,
    }


def recommend_assignments(project_id: int, user_id: int, backlog_item_ids: list[int]) -> dict:
    require_project_member(project_id, user_id)
    members = [
        member["project_profile"]
        for member in list_project_members(project_id, user_id)
        if member["project_profile"] is not None
    ]
    if not members:
        raise HTTPException(status_code=400, detail="No project profiles found")

    assignments = []
    for backlog_item_id in backlog_item_ids:
        backlog_item = get_backlog_item(backlog_item_id, user_id)
        candidates = []
        for member in members:
            score, reasons = _score_member(backlog_item, member, project_id)
            candidates.append(
                {
                    "user_id": member["user_id"],
                    "user_name": member["user_name"],
                    "score": score,
                    "stars": _to_stars(score),
                    "reasons": reasons,
                }
            )
        candidates.sort(key=lambda item: (-item["score"], item["user_id"]))
        best = candidates[0]
        assignments.append(
            {
                "backlog_item_id": backlog_item_id,
                "title": backlog_item["title"],
                "recommended_assignee_id": best["user_id"],
                "recommended_assignee_name": best["user_name"],
                "recommendation_reason": "; ".join(best["reasons"]),
                "candidates": candidates,
            }
        )
    return {"assignments": assignments}


def confirm_assignments(project_id: int, user_id: int, assignments: list[dict]) -> dict:
    require_project_pm(project_id, user_id)
    created_issue_ids = []
    for assignment in assignments:
        backlog_item = get_backlog_item(assignment["backlog_item_id"], user_id)
        issue_id = execute(
            """
            INSERT INTO issues (
                project_id, sprint_id, backlog_item_id, assignee_id, title, description,
                status, priority, difficulty, estimated_hours, required_role,
                required_tech_stack, assignment_reason, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, 'TODO', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                assignment.get("sprint_id"),
                backlog_item["id"],
                assignment["assignee_id"],
                backlog_item["title"],
                backlog_item["description"],
                backlog_item["priority"],
                backlog_item["difficulty"],
                backlog_item["estimated_hours"],
                backlog_item.get("required_role"),
                serialize_list(backlog_item["required_tech_stack"]),
                assignment["assignment_reason"],
                user_id,
            ),
        )
        execute(
            """
            UPDATE backlog_items
            SET status = 'CONVERTED', linked_issue_id = ?
            WHERE id = ?
            """,
            (issue_id, backlog_item["id"]),
        )
        created_issue_ids.append(issue_id)
    return {"created_issue_ids": created_issue_ids}


def _score_member(backlog_item: dict, member: dict, project_id: int) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    if backlog_item.get("required_role") and _role_matches(backlog_item["required_role"], member["project_role"]):
        score += 2
        reasons.append("Project role matches the task role")

    tech_matches = sorted(set(backlog_item["required_tech_stack"]) & set(member["tech_stack"]))
    if tech_matches:
        score += min(2, len(tech_matches))
        reasons.append(f"Matching tech stack: {', '.join(tech_matches)}")

    if _keyword_match(backlog_item["title"], backlog_item["description"], member["strong_tasks"]):
        score += 2
        reasons.append("Task aligns with the member's strong tasks")

    if _keyword_match(backlog_item["title"], backlog_item["description"], member["disliked_tasks"]):
        score -= 2
        reasons.append("Task overlaps with disliked work")

    workload = fetch_one(
        """
        SELECT COUNT(*) AS issue_count
        FROM issues
        WHERE project_id = ? AND assignee_id = ? AND status != 'DONE'
        """,
        (project_id, member["user_id"]),
    )["issue_count"]
    if workload <= 1:
        score += 1
        reasons.append("Current workload is light")

    if member["available_hours_per_day"] >= backlog_item["estimated_hours"] / 2:
        score += 1
        reasons.append("Available hours fit the estimate")

    difficulty_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    experience_map = {"BEGINNER": 1, "INTERMEDIATE": 2, "ADVANCED": 3}
    if experience_map.get(member["experience_level"], 2) >= difficulty_map.get(backlog_item["difficulty"], 2):
        score += 1
        reasons.append("Experience level fits the difficulty")

    if not reasons:
        reasons.append("Assigned as the closest available general contributor")

    return score, reasons


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
        "PM": {"PM"},
    }
    if normalized_required == normalized_role:
        return True
    return normalized_role in mapping.get(normalized_required, set())


def _to_stars(score: int) -> str:
    if score <= 1:
        return "1/5"
    if score == 2:
        return "2/5"
    if score == 3:
        return "3/5"
    if score == 4:
        return "4/5"
    return "5/5"
