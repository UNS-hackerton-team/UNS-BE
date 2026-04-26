from fastapi.testclient import TestClient

from app.main import app
from app.schemas.work_tracking import (
    DashboardResponse,
    ProgressSummary,
    WorkItem,
    WorkScopeSnapshot,
    WorkSnapshotResponse,
)
from app.services.work_tracking import build_dashboard_areas


def _summary(
    *,
    total_items: int,
    effective_items: int,
    backlog_items: int,
    in_progress_items: int,
    done_items: int,
    canceled_items: int,
    completion_rate: float,
) -> ProgressSummary:
    return ProgressSummary(
        total_items=total_items,
        effective_items=effective_items,
        backlog_items=backlog_items,
        in_progress_items=in_progress_items,
        done_items=done_items,
        canceled_items=canceled_items,
        total_estimate=None,
        completed_estimate=None,
        completion_rate=completion_rate,
        weighted_completion_rate=None,
    )


def test_build_dashboard_areas_groups_by_project() -> None:
    items = [
        WorkItem(
            source="jira",
            scope_id="10",
            scope_name="Platform Board",
            external_id="JIRA-1",
            title="Implement auth",
            project_name="Platform",
            team_name="Platform Board",
            assignee_name="Alice",
            status_name="Done",
            status_category="done",
            labels=["backend"],
            estimate=3,
            is_current_iteration=True,
        ),
        WorkItem(
            source="linear",
            scope_id="team-1",
            scope_name="Growth",
            external_id="ENG-42",
            title="Improve funnel",
            project_name="Growth",
            team_name="Growth",
            assignee_name="Bob",
            status_name="In Progress",
            status_category="in_progress",
            labels=["frontend"],
            estimate=5,
            is_current_iteration=True,
        ),
        WorkItem(
            source="linear",
            scope_id="team-1",
            scope_name="Growth",
            external_id="ENG-43",
            title="Triage request",
            project_name=None,
            team_name="Growth",
            assignee_name=None,
            status_name="Backlog",
            status_category="backlog",
            labels=[],
            estimate=None,
            is_backlog=True,
        ),
    ]

    areas = build_dashboard_areas(items, group_by="project")

    assert [area.label for area in areas] == ["Growth", "No project", "Platform"]
    growth_area = next(area for area in areas if area.label == "Growth")
    assert growth_area.summary.in_progress_items == 1
    no_project_area = next(area for area in areas if area.label == "No project")
    assert no_project_area.summary.backlog_items == 1


def test_jira_snapshot_endpoint_returns_mocked_data(monkeypatch) -> None:
    async def fake_fetch_jira_snapshot(_: object) -> WorkSnapshotResponse:
        return WorkSnapshotResponse(
            scopes=[
                WorkScopeSnapshot(
                    source="jira",
                    scope_id="10",
                    scope_name="Platform Board",
                    iterations=[],
                    summary=_summary(
                        total_items=1,
                        effective_items=1,
                        backlog_items=0,
                        in_progress_items=1,
                        done_items=0,
                        canceled_items=0,
                        completion_rate=0.0,
                    ),
                    items=[
                        WorkItem(
                            source="jira",
                            scope_id="10",
                            scope_name="Platform Board",
                            external_id="JIRA-1",
                            title="Implement auth",
                            status_name="In Progress",
                            status_category="in_progress",
                        )
                    ],
                )
            ],
            summary=_summary(
                total_items=1,
                effective_items=1,
                backlog_items=0,
                in_progress_items=1,
                done_items=0,
                canceled_items=0,
                completion_rate=0.0,
            ),
        )

    monkeypatch.setattr(
        "app.api.v1.work_tracking.fetch_jira_snapshot",
        fake_fetch_jira_snapshot,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/work-tracking/jira/snapshot", json={"boards": []})

    assert response.status_code == 200
    assert response.json()["summary"]["in_progress_items"] == 1


def test_linear_snapshot_endpoint_returns_mocked_data(monkeypatch) -> None:
    async def fake_fetch_linear_snapshot(_: object) -> WorkSnapshotResponse:
        return WorkSnapshotResponse(
            scopes=[
                WorkScopeSnapshot(
                    source="linear",
                    scope_id="team-1",
                    scope_name="Growth",
                    iterations=[],
                    summary=_summary(
                        total_items=2,
                        effective_items=2,
                        backlog_items=1,
                        in_progress_items=1,
                        done_items=0,
                        canceled_items=0,
                        completion_rate=0.0,
                    ),
                    items=[],
                )
            ],
            summary=_summary(
                total_items=2,
                effective_items=2,
                backlog_items=1,
                in_progress_items=1,
                done_items=0,
                canceled_items=0,
                completion_rate=0.0,
            ),
        )

    monkeypatch.setattr(
        "app.api.v1.work_tracking.fetch_linear_snapshot",
        fake_fetch_linear_snapshot,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/work-tracking/linear/snapshot",
            json={"teams": [{"team_id": "team-1"}]},
        )

    assert response.status_code == 200
    assert response.json()["summary"]["backlog_items"] == 1


def test_dashboard_endpoint_returns_mocked_data(monkeypatch) -> None:
    async def fake_fetch_dashboard(_: object) -> DashboardResponse:
        return DashboardResponse(
            summary=_summary(
                total_items=3,
                effective_items=3,
                backlog_items=1,
                in_progress_items=1,
                done_items=1,
                canceled_items=0,
                completion_rate=0.3333,
            ),
            areas=[],
            sources=[],
            scopes=[],
            items=[],
        )

    monkeypatch.setattr(
        "app.api.v1.work_tracking.fetch_dashboard",
        fake_fetch_dashboard,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/work-tracking/dashboard",
            json={"group_by": "project", "jira": {"boards": []}},
        )

    assert response.status_code == 200
    assert response.json()["summary"]["completion_rate"] == 0.3333
