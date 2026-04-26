import os

from fastapi.testclient import TestClient


os.environ["APP_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.pop("APP_DATABASE_PATH", None)

from app.core.config import get_settings
from app.db.database import reset_db_state
from app.main import app


get_settings.cache_clear()


def _reset_database() -> None:
    reset_db_state()


def _signup(client: TestClient, name: str, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/signup",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_full_mvp_flow() -> None:
    _reset_database()

    with TestClient(app) as client:
        owner_token = _signup(client, "Owner", "owner@example.com", "password123")
        member_token = _signup(client, "Member", "member@example.com", "password123")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        member_headers = {"Authorization": f"Bearer {member_token}"}

        workspace_response = client.post(
            "/api/v1/workspaces",
            json={
                "name": "CMUX Hack Team",
                "description": "AI PM Workspace hackathon team",
                "team_type": "Hackathon Team",
            },
            headers=owner_headers,
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()
        workspace_id = workspace["id"]

        second_workspace_response = client.post(
            "/api/v1/workspaces",
            json={
                "name": "Another Org",
                "description": "Second workspace for the same owner",
                "team_type": "Company",
            },
            headers=owner_headers,
        )
        assert second_workspace_response.status_code == 200

        invite_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/invite",
            headers=owner_headers,
        )
        assert invite_response.status_code == 200
        invite_code = invite_response.json()["invite_code"]

        validate_response = client.get(f"/api/v1/invites/{invite_code}")
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        join_response = client.post(
            f"/api/v1/invites/{invite_code}/join",
            headers=member_headers,
        )
        assert join_response.status_code == 200
        assert join_response.json()["joined"] is True

        owner_workspace_list_response = client.get(
            "/api/v1/workspaces",
            headers=owner_headers,
        )
        assert owner_workspace_list_response.status_code == 200
        owner_workspaces = owner_workspace_list_response.json()
        assert len(owner_workspaces) == 2
        assert owner_workspaces[0]["workspace_role"] == "OWNER"

        member_workspace_list_response = client.get(
            "/api/v1/workspaces",
            headers=member_headers,
        )
        assert member_workspace_list_response.status_code == 200
        member_workspaces = member_workspace_list_response.json()
        assert len(member_workspaces) == 1
        assert member_workspaces[0]["id"] == workspace_id
        assert member_workspaces[0]["workspace_role"] == "MEMBER"

        project_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            json={
                "name": "AI PM Workspace",
                "description": "AI PM workspace for hackathon teams",
                "goal": "Generate and assign tasks quickly",
                "tech_stack": ["FastAPI", "SQLite", "React"],
                "priority": "HIGH",
                "mvp_scope": "Workspace invite, project setup, AI tasks",
            },
            headers=owner_headers,
        )
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]

        owner_profile_response = client.post(
            f"/api/v1/projects/{project_id}/members/profile",
            json={
                "project_role": "BACKEND",
                "tech_stack": ["FastAPI", "SQLite", "JWT"],
                "strong_tasks": ["API", "database", "auth"],
                "disliked_tasks": ["design"],
                "available_hours_per_day": 6,
                "experience_level": "ADVANCED",
            },
            headers=owner_headers,
        )
        assert owner_profile_response.status_code == 200

        member_profile_response = client.post(
            f"/api/v1/projects/{project_id}/members/profile",
            json={
                "project_role": "FRONTEND",
                "tech_stack": ["React", "TypeScript"],
                "strong_tasks": ["UI", "screen", "frontend"],
                "disliked_tasks": ["database"],
                "available_hours_per_day": 5,
                "experience_level": "INTERMEDIATE",
            },
            headers=member_headers,
        )
        assert member_profile_response.status_code == 200

        members_response = client.get(
            f"/api/v1/projects/{project_id}/members",
            headers=owner_headers,
        )
        assert members_response.status_code == 200
        assert len(members_response.json()) == 2

        tasks_response = client.post(
            f"/api/v1/projects/{project_id}/ai/tasks",
            json={"create_backlog": True},
            headers=owner_headers,
        )
        assert tasks_response.status_code == 200
        created_backlog_items = tasks_response.json()["created_backlog_items"]
        assert len(created_backlog_items) >= 3

        assignments_response = client.post(
            f"/api/v1/projects/{project_id}/ai/assignments",
            json={"backlog_item_ids": created_backlog_items[:2]},
            headers=owner_headers,
        )
        assert assignments_response.status_code == 200
        assignments = assignments_response.json()["assignments"]
        assert len(assignments) == 2

        confirm_payload = {
            "assignments": [
                {
                    "backlog_item_id": item["backlog_item_id"],
                    "assignee_id": item["recommended_assignee_id"],
                    "assignment_reason": item["recommendation_reason"],
                }
                for item in assignments
            ]
        }
        confirm_response = client.post(
            f"/api/v1/projects/{project_id}/ai/assignments/confirm",
            json=confirm_payload,
            headers=owner_headers,
        )
        assert confirm_response.status_code == 200
        issue_ids = confirm_response.json()["created_issue_ids"]
        assert len(issue_ids) == 2

        sprint_response = client.post(
            f"/api/v1/projects/{project_id}/sprints",
            json={
                "name": "Sprint 1",
                "goal": "Complete core MVP flow",
                "start_date": "2026-04-26",
                "end_date": "2026-04-27",
            },
            headers=owner_headers,
        )
        assert sprint_response.status_code == 200
        sprint_id = sprint_response.json()["id"]

        attach_response = client.post(
            f"/api/v1/sprints/{sprint_id}/issues",
            json={"issue_ids": issue_ids},
            headers=owner_headers,
        )
        assert attach_response.status_code == 200

        update_status_response = client.patch(
            f"/api/v1/issues/{issue_ids[0]}/status",
            json={"status": "IN_PROGRESS"},
            headers=owner_headers,
        )
        assert update_status_response.status_code == 200
        assert update_status_response.json()["status"] == "IN_PROGRESS"

        dashboard_response = client.get(
            f"/api/v1/projects/{project_id}/dashboard",
            headers=owner_headers,
        )
        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["total_issues"] >= 2

        team_chat_response = client.post(
            f"/api/v1/projects/{project_id}/chat/team/messages",
            json={"content": "지금 가장 먼저 해야 할 일이 뭐야?"},
            headers=owner_headers,
        )
        assert team_chat_response.status_code == 200
        assert "next_action" in team_chat_response.json()["answer"]

        personal_chat_response = client.post(
            f"/api/v1/projects/{project_id}/chat/personal/messages",
            json={"content": "내가 지금 뭘 해야 해?"},
            headers=owner_headers,
        )
        assert personal_chat_response.status_code == 200
        assert "recommended_order" in personal_chat_response.json()["answer"]
