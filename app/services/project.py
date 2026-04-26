from typing import Optional

from fastapi import HTTPException

from app.db.database import (
    deserialize_list,
    execute,
    fetch_all,
    fetch_one,
    serialize_list,
)
from app.services.workspace import require_workspace_member


def create_project(
    workspace_id: int,
    current_user_id: int,
    name: str,
    description: str,
    goal: str,
    tech_stack: list[str],
    start_date: Optional[str],
    end_date: Optional[str],
    pm_id: int,
    priority: str,
    mvp_scope: str,
) -> dict:
    require_workspace_member(workspace_id, current_user_id)
    project_id = execute(
        """
        INSERT INTO projects (
            workspace_id, name, description, goal, tech_stack,
            start_date, end_date, pm_id, priority, mvp_scope
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            name,
            description,
            goal,
            serialize_list(tech_stack),
            start_date,
            end_date,
            pm_id,
            priority,
            mvp_scope,
        ),
    )
    existing_room = fetch_one(
        """
        SELECT id
        FROM chat_rooms
        WHERE project_id = ? AND type = ? AND user_id IS NULL
        """,
        (project_id, "TEAM_AI"),
    )
    if existing_room is None:
        execute(
            """
            INSERT INTO chat_rooms (project_id, type, user_id)
            VALUES (?, 'TEAM_AI', NULL)
            """,
            (project_id,),
        )
    return get_project(project_id, current_user_id)


def get_project(project_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT p.*
        FROM projects p
        JOIN workspace_members wm
            ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE p.id = ?
        """,
        (user_id, project_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project = dict(row)
    project["tech_stack"] = deserialize_list(project["tech_stack"])
    return project


def list_projects(workspace_id: int, user_id: int) -> list[dict]:
    require_workspace_member(workspace_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM projects
        WHERE workspace_id = ?
        ORDER BY id DESC
        """,
        (workspace_id,),
    )
    projects = []
    for row in rows:
        project = dict(row)
        project["tech_stack"] = deserialize_list(project["tech_stack"])
        projects.append(project)
    return projects


def require_project_member(project_id: int, user_id: int) -> None:
    project = get_project(project_id, user_id)
    require_workspace_member(project["workspace_id"], user_id)


def require_project_pm(project_id: int, user_id: int) -> None:
    project = get_project(project_id, user_id)
    if project["pm_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project PM access required")


def upsert_project_profile(project_id: int, user: dict, payload: dict) -> dict:
    require_project_member(project_id, user["id"])
    existing = fetch_one(
        """
        SELECT id FROM project_members
        WHERE project_id = ? AND user_id = ?
        """,
        (project_id, user["id"]),
    )
    params = (
        project_id,
        user["id"],
        payload["project_role"],
        serialize_list(payload["tech_stack"]),
        serialize_list(payload["strong_tasks"]),
        serialize_list(payload["disliked_tasks"]),
        payload["available_hours_per_day"],
        payload["experience_level"],
    )
    if existing is None:
        execute(
            """
            INSERT INTO project_members (
                project_id, user_id, project_role, tech_stack,
                strong_tasks, disliked_tasks, available_hours_per_day, experience_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )
    else:
        execute(
            """
            UPDATE project_members
            SET project_role = ?, tech_stack = ?, strong_tasks = ?, disliked_tasks = ?,
                available_hours_per_day = ?, experience_level = ?
            WHERE project_id = ? AND user_id = ?
            """,
            (
                payload["project_role"],
                serialize_list(payload["tech_stack"]),
                serialize_list(payload["strong_tasks"]),
                serialize_list(payload["disliked_tasks"]),
                payload["available_hours_per_day"],
                payload["experience_level"],
                project_id,
                user["id"],
            ),
        )
    return get_project_member_profile(project_id, user["id"])


def get_project_member_profile(project_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT
            pm.*,
            u.name AS user_name,
            u.email AS user_email
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id = ? AND pm.user_id = ?
        """,
        (project_id, user_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project profile not found")
    return _serialize_project_member(dict(row))


def list_project_members(project_id: int, user_id: int) -> list[dict]:
    project = get_project(project_id, user_id)
    rows = fetch_all(
        """
        SELECT
            u.id AS user_id,
            u.name AS user_name,
            u.email AS user_email,
            wm.workspace_role,
            wm.joined_at,
            pm.id AS profile_id,
            pm.project_role,
            pm.tech_stack,
            pm.strong_tasks,
            pm.disliked_tasks,
            pm.available_hours_per_day,
            pm.experience_level,
            pm.joined_at AS profile_joined_at
        FROM workspace_members wm
        JOIN users u ON u.id = wm.user_id
        LEFT JOIN project_members pm
            ON pm.project_id = ? AND pm.user_id = u.id
        WHERE wm.workspace_id = ?
        ORDER BY u.id ASC
        """,
        (project_id, project["workspace_id"]),
    )
    members = []
    for row in rows:
        member = {
            "user_id": row["user_id"],
            "user_name": row["user_name"],
            "user_email": row["user_email"],
            "workspace_role": row["workspace_role"],
            "joined_at": row["joined_at"],
            "project_profile": None,
        }
        if row["profile_id"] is not None:
            member["project_profile"] = {
                "id": row["profile_id"],
                "project_id": project_id,
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "user_email": row["user_email"],
                "project_role": row["project_role"],
                "tech_stack": deserialize_list(row["tech_stack"]),
                "strong_tasks": deserialize_list(row["strong_tasks"]),
                "disliked_tasks": deserialize_list(row["disliked_tasks"]),
                "available_hours_per_day": row["available_hours_per_day"],
                "experience_level": row["experience_level"],
                "joined_at": row["profile_joined_at"],
            }
        members.append(member)
    return members


def create_backlog_item(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    backlog_id = execute(
        """
        INSERT INTO backlog_items (
            project_id, title, description, priority, required_role,
            required_tech_stack, difficulty, estimated_hours
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            payload["title"],
            payload["description"],
            payload["priority"],
            payload.get("required_role"),
            serialize_list(payload["required_tech_stack"]),
            payload["difficulty"],
            payload["estimated_hours"],
        ),
    )
    return get_backlog_item(backlog_id, user_id)


def get_backlog_item(backlog_item_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT b.*
        FROM backlog_items b
        JOIN projects p ON p.id = b.project_id
        JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE b.id = ?
        """,
        (user_id, backlog_item_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Backlog item not found")
    item = dict(row)
    item["required_tech_stack"] = deserialize_list(item["required_tech_stack"])
    return item


def list_backlog(project_id: int, user_id: int) -> list[dict]:
    require_project_member(project_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM backlog_items
        WHERE project_id = ?
        ORDER BY id ASC
        """,
        (project_id,),
    )
    items = []
    for row in rows:
        item = dict(row)
        item["required_tech_stack"] = deserialize_list(item["required_tech_stack"])
        items.append(item)
    return items


def update_backlog_item(backlog_item_id: int, user_id: int, payload: dict) -> dict:
    item = get_backlog_item(backlog_item_id, user_id)
    require_project_pm(item["project_id"], user_id)
    next_item = {**item, **payload}
    required_tech_stack = payload.get("required_tech_stack", item["required_tech_stack"])
    execute(
        """
        UPDATE backlog_items
        SET title = ?, description = ?, priority = ?, required_role = ?,
            required_tech_stack = ?, difficulty = ?, estimated_hours = ?, status = ?
        WHERE id = ?
        """,
        (
            next_item["title"],
            next_item["description"],
            next_item["priority"],
            next_item.get("required_role"),
            serialize_list(required_tech_stack),
            next_item["difficulty"],
            next_item["estimated_hours"],
            next_item["status"],
            backlog_item_id,
        ),
    )
    return get_backlog_item(backlog_item_id, user_id)


def delete_backlog_item(backlog_item_id: int, user_id: int) -> None:
    item = get_backlog_item(backlog_item_id, user_id)
    require_project_pm(item["project_id"], user_id)
    execute("DELETE FROM backlog_items WHERE id = ?", (backlog_item_id,))


def create_sprint(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    sprint_id = execute(
        """
        INSERT INTO sprints (project_id, name, goal, start_date, end_date, status)
        VALUES (?, ?, ?, ?, ?, 'PLANNED')
        """,
        (
            project_id,
            payload["name"],
            payload["goal"],
            payload["start_date"],
            payload["end_date"],
        ),
    )
    return get_sprint(sprint_id, user_id)


def get_sprint(sprint_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT s.*
        FROM sprints s
        JOIN projects p ON p.id = s.project_id
        JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE s.id = ?
        """,
        (user_id, sprint_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return dict(row)


def list_sprints(project_id: int, user_id: int) -> list[dict]:
    require_project_member(project_id, user_id)
    rows = fetch_all(
        "SELECT * FROM sprints WHERE project_id = ? ORDER BY id DESC",
        (project_id,),
    )
    return [dict(row) for row in rows]


def add_issues_to_sprint(sprint_id: int, issue_ids: list[int], user_id: int) -> dict:
    sprint = get_sprint(sprint_id, user_id)
    require_project_pm(sprint["project_id"], user_id)
    for issue_id in issue_ids:
        execute(
            "UPDATE issues SET sprint_id = ? WHERE id = ? AND project_id = ?",
            (sprint_id, issue_id, sprint["project_id"]),
        )
    execute(
        "UPDATE sprints SET status = 'ACTIVE' WHERE id = ?",
        (sprint_id,),
    )
    return get_sprint(sprint_id, user_id)


def create_issue(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_member(project_id, user_id)
    issue_id = execute(
        """
        INSERT INTO issues (
            project_id, sprint_id, assignee_id, title, description, priority,
            difficulty, estimated_hours, required_role, required_tech_stack,
            due_date, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            payload.get("sprint_id"),
            payload.get("assignee_id"),
            payload["title"],
            payload["description"],
            payload["priority"],
            payload["difficulty"],
            payload["estimated_hours"],
            payload.get("required_role"),
            serialize_list(payload["required_tech_stack"]),
            payload.get("due_date"),
            user_id,
        ),
    )
    return get_issue(issue_id, user_id)


def get_issue(issue_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT i.*
        FROM issues i
        JOIN projects p ON p.id = i.project_id
        JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE i.id = ?
        """,
        (user_id, issue_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue = dict(row)
    issue["required_tech_stack"] = deserialize_list(issue["required_tech_stack"])
    return issue


def update_issue_status(issue_id: int, user_id: int, status_value: str) -> dict:
    issue = get_issue(issue_id, user_id)
    if issue["assignee_id"] not in (None, user_id):
        require_project_pm(issue["project_id"], user_id)
    execute(
        "UPDATE issues SET status = ? WHERE id = ?",
        (status_value, issue_id),
    )
    return get_issue(issue_id, user_id)


def update_issue_assignee(
    issue_id: int,
    user_id: int,
    assignee_id: Optional[int],
    assignment_reason: Optional[str],
) -> dict:
    issue = get_issue(issue_id, user_id)
    require_project_pm(issue["project_id"], user_id)
    execute(
        """
        UPDATE issues
        SET assignee_id = ?, assignment_reason = ?
        WHERE id = ?
        """,
        (assignee_id, assignment_reason, issue_id),
    )
    return get_issue(issue_id, user_id)


def get_dashboard(project_id: int, user_id: int) -> dict:
    require_project_member(project_id, user_id)
    counts = fetch_one(
        """
        SELECT
            COUNT(*) AS total_issues,
            SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) AS completed_issues,
            SUM(CASE WHEN status IN ('IN_PROGRESS', 'REVIEW') THEN 1 ELSE 0 END) AS in_progress_issues,
            SUM(CASE WHEN status != 'DONE' THEN 1 ELSE 0 END) AS remaining_issues
        FROM issues
        WHERE project_id = ?
        """,
        (project_id,),
    )
    sprint_counts = fetch_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) AS done_count
        FROM issues
        WHERE project_id = ? AND sprint_id IS NOT NULL
        """,
        (project_id,),
    )
    workload_rows = fetch_all(
        """
        SELECT
            u.id AS user_id,
            u.name AS user_name,
            COUNT(i.id) AS issue_count
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        LEFT JOIN issues i
            ON i.assignee_id = pm.user_id
           AND i.project_id = pm.project_id
           AND i.status != 'DONE'
        WHERE pm.project_id = ?
        GROUP BY u.id, u.name
        ORDER BY issue_count DESC, u.id ASC
        """,
        (project_id,),
    )
    risk_rows = fetch_all(
        """
        SELECT id, title, priority, status
        FROM issues
        WHERE project_id = ? AND priority = 'HIGH' AND status != 'DONE'
        ORDER BY id ASC
        LIMIT 5
        """,
        (project_id,),
    )
    next_issue = fetch_one(
        """
        SELECT id, title, priority, status
        FROM issues
        WHERE project_id = ? AND status = 'TODO'
        ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id ASC
        LIMIT 1
        """,
        (project_id,),
    )
    remaining_backend = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM issues
        WHERE project_id = ? AND status != 'DONE' AND required_role = 'BACKEND'
        """,
        (project_id,),
    )["count"]
    remaining_frontend = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM issues
        WHERE project_id = ? AND status != 'DONE' AND required_role = 'FRONTEND'
        """,
        (project_id,),
    )["count"]
    if remaining_backend > remaining_frontend:
        bottleneck = "Backend issues are heavier than frontend issues. Clear API and data tasks first."
    elif remaining_frontend > remaining_backend:
        bottleneck = "Frontend tasks are dominating the queue. Review screen scope and unblock UI implementation."
    else:
        bottleneck = "Workload is balanced. Focus on the highest-priority open issue."

    total = sprint_counts["total"] or 0
    done = sprint_counts["done_count"] or 0
    sprint_progress = int(done * 100 / total) if total else 0
    return {
        "total_issues": counts["total_issues"] or 0,
        "completed_issues": counts["completed_issues"] or 0,
        "in_progress_issues": counts["in_progress_issues"] or 0,
        "remaining_issues": counts["remaining_issues"] or 0,
        "sprint_progress": sprint_progress,
        "team_workload": [dict(row) for row in workload_rows],
        "risk_issues": [dict(row) for row in risk_rows],
        "bottleneck_summary": bottleneck,
        "recommended_next_issue": dict(next_issue) if next_issue is not None else None,
    }


def _serialize_project_member(row: dict) -> dict:
    row["tech_stack"] = deserialize_list(row["tech_stack"])
    row["strong_tasks"] = deserialize_list(row["strong_tasks"])
    row["disliked_tasks"] = deserialize_list(row["disliked_tasks"])
    return row
