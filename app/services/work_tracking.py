from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.work_tracking import (
    DashboardArea,
    DashboardGroupBy,
    DashboardRequest,
    DashboardResponse,
    JiraBoardScopeRequest,
    JiraSnapshotRequest,
    LinearSnapshotRequest,
    LinearTeamScopeRequest,
    ProgressSummary,
    WorkItem,
    WorkIteration,
    WorkScopeSnapshot,
    WorkSnapshotResponse,
)


JIRA_DEFAULT_FIELDS = [
    "summary",
    "status",
    "assignee",
    "labels",
    "project",
    "priority",
    "created",
    "updated",
    "duedate",
]

LINEAR_TEAM_DIRECTORY_QUERY = """
query TeamDirectory($first: Int!) {
  teams(first: $first) {
    nodes {
      id
      key
      name
    }
  }
}
"""

LINEAR_TEAM_SNAPSHOT_QUERY = """
query TeamSnapshot($teamId: String!, $issueLimit: Int!, $cycleLimit: Int!) {
  team(id: $teamId) {
    id
    key
    name
    cycles(first: $cycleLimit) {
      nodes {
        id
        number
        name
        startsAt
        endsAt
        progress
      }
    }
    issues(first: $issueLimit) {
      nodes {
        id
        identifier
        title
        url
        estimate
        createdAt
        updatedAt
        completedAt
        assignee {
          name
        }
        labels {
          nodes {
            name
          }
        }
        project {
          name
        }
        cycle {
          id
          number
          name
          startsAt
          endsAt
        }
        state {
          name
          type
        }
      }
    }
  }
}
"""


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _work_item_summary(
    items: Sequence[WorkItem],
    *,
    exclude_canceled_from_progress: bool = True,
) -> ProgressSummary:
    total_items = len(items)
    canceled_items = sum(item.status_category == "canceled" for item in items)
    done_items = sum(item.status_category == "done" for item in items)
    backlog_items = sum(item.status_category == "backlog" for item in items)
    in_progress_items = sum(item.status_category == "in_progress" for item in items)
    effective_items = (
        total_items - canceled_items if exclude_canceled_from_progress else total_items
    )

    eligible_items = [
        item
        for item in items
        if not exclude_canceled_from_progress or item.status_category != "canceled"
    ]
    estimated_items = [item for item in eligible_items if item.estimate is not None]
    total_estimate = sum(item.estimate or 0 for item in estimated_items)
    completed_estimate = sum(
        item.estimate or 0
        for item in estimated_items
        if item.status_category == "done"
    )

    completion_rate = round(done_items / effective_items, 4) if effective_items else 0.0
    weighted_completion_rate = (
        round(completed_estimate / total_estimate, 4) if total_estimate else None
    )

    return ProgressSummary(
        total_items=total_items,
        effective_items=effective_items,
        backlog_items=backlog_items,
        in_progress_items=in_progress_items,
        done_items=done_items,
        canceled_items=canceled_items,
        total_estimate=round(total_estimate, 2) if estimated_items else None,
        completed_estimate=round(completed_estimate, 2) if estimated_items else None,
        completion_rate=completion_rate,
        weighted_completion_rate=weighted_completion_rate,
    )


def _group_keys_for_item(item: WorkItem, group_by: DashboardGroupBy) -> list[tuple[str, str]]:
    if group_by == "source":
        return [(item.source, item.source.upper())]
    if group_by == "scope":
        return [(f"{item.source}:{item.scope_id}", item.scope_name)]
    if group_by == "project":
        label = item.project_name or "No project"
        return [(label.lower(), label)]
    if group_by == "team":
        label = item.team_name or item.scope_name or "No team"
        return [(label.lower(), label)]
    if group_by == "assignee":
        label = item.assignee_name or "Unassigned"
        return [(label.lower(), label)]
    if group_by == "status_category":
        label = item.status_category
        return [(label, label)]
    if group_by == "label":
        if item.labels:
            return [(label.lower(), label) for label in item.labels]
        return [("unlabeled", "Unlabeled")]

    return [("unknown", "Unknown")]


def build_dashboard_areas(
    items: Sequence[WorkItem],
    *,
    group_by: DashboardGroupBy,
    exclude_canceled_from_progress: bool = True,
) -> list[DashboardArea]:
    grouped_items: dict[tuple[str, str], list[WorkItem]] = defaultdict(list)
    for item in items:
        for group_key in _group_keys_for_item(item, group_by):
            grouped_items[group_key].append(item)

    areas = [
        DashboardArea(
            key=key,
            label=label,
            summary=_work_item_summary(
                bucket_items,
                exclude_canceled_from_progress=exclude_canceled_from_progress,
            ),
        )
        for (key, label), bucket_items in grouped_items.items()
    ]
    return sorted(
        areas,
        key=lambda area: (-area.summary.total_items, area.label.lower()),
    )


class JiraClient:
    def __init__(self, settings: Settings):
        if not settings.jira_base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JIRA_BASE_URL is not configured",
            )
        if not settings.jira_api_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JIRA_API_TOKEN is not configured",
            )

        headers = {"Accept": "application/json"}
        auth: httpx.BasicAuth | None = None
        if settings.jira_email:
            auth = httpx.BasicAuth(settings.jira_email, settings.jira_api_token)
        else:
            headers["Authorization"] = f"Bearer {settings.jira_api_token}"

        self._settings = settings
        self._base_url = settings.jira_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            auth=auth,
            timeout=settings.jira_timeout_seconds,
        )

    async def __aenter__(self) -> "JiraClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Jira request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Jira API returned {response.status_code}: {response.text}",
            )

        return response.json()

    async def _paginate(
        self,
        path: str,
        *,
        collection_key: str,
        limit: int,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        start_at = 0

        while len(results) < limit:
            page_size = min(50, limit - len(results))
            request_params = dict(params or {})
            request_params["startAt"] = start_at
            request_params["maxResults"] = page_size
            payload = await self._get(path, request_params)

            items = payload.get(collection_key, [])
            if not items:
                break

            results.extend(items)
            if payload.get("isLast") is True:
                break

            returned_count = payload.get("maxResults") or len(items)
            start_at = int(payload.get("startAt", start_at)) + int(returned_count)
            total = payload.get("total")
            if total is not None and start_at >= int(total):
                break

        return results[:limit]

    async def fetch_board_snapshot(
        self,
        board_request: JiraBoardScopeRequest,
    ) -> WorkScopeSnapshot:
        board = await self._get(f"/rest/agile/1.0/board/{board_request.board_id}")
        board_name = board.get("name") or f"Jira Board {board_request.board_id}"
        scope_id = str(board_request.board_id)
        team_name = board_name

        story_points_field = self._settings.jira_story_points_field
        requested_fields = list(JIRA_DEFAULT_FIELDS)
        if story_points_field:
            requested_fields.append(story_points_field)
        fields_param = ",".join(requested_fields)

        iterations: list[WorkIteration] = []
        items: list[WorkItem] = []

        sprint_list: list[dict[str, Any]] = []
        if board_request.include_sprints:
            sprint_list = await self._paginate(
                f"/rest/agile/1.0/board/{board_request.board_id}/sprint",
                collection_key="values",
                limit=board_request.sprint_limit,
                params={"state": board_request.sprint_state},
            )

        for sprint in sprint_list:
            iteration = WorkIteration(
                source="jira",
                external_id=str(sprint["id"]),
                name=sprint.get("name") or f"Sprint {sprint['id']}",
                state=sprint.get("state"),
                scope_id=scope_id,
                scope_name=board_name,
                start_date=_parse_datetime(sprint.get("startDate")),
                end_date=_parse_datetime(sprint.get("endDate")),
                goal=sprint.get("goal"),
            )
            iterations.append(iteration)

            sprint_issues = await self._paginate(
                f"/rest/agile/1.0/sprint/{sprint['id']}/issue",
                collection_key="issues",
                limit=board_request.sprint_issue_limit,
                params={"fields": fields_param},
            )
            items.extend(
                _normalize_jira_issue(
                    issue,
                    base_url=self._base_url,
                    board_name=board_name,
                    team_name=team_name,
                    scope_id=scope_id,
                    story_points_field=story_points_field,
                    iteration=iteration,
                    is_backlog=False,
                )
                for issue in sprint_issues
            )

        if board_request.include_backlog:
            backlog_issues = await self._paginate(
                f"/rest/agile/1.0/board/{board_request.board_id}/backlog",
                collection_key="issues",
                limit=board_request.backlog_limit,
                params={"fields": fields_param},
            )
            items.extend(
                _normalize_jira_issue(
                    issue,
                    base_url=self._base_url,
                    board_name=board_name,
                    team_name=team_name,
                    scope_id=scope_id,
                    story_points_field=story_points_field,
                    iteration=None,
                    is_backlog=True,
                )
                for issue in backlog_issues
            )

        deduped_items = list({item.external_id: item for item in items}.values())
        return WorkScopeSnapshot(
            source="jira",
            scope_id=scope_id,
            scope_name=board_name,
            iterations=iterations,
            summary=_work_item_summary(deduped_items),
            items=deduped_items,
        )


class LinearClient:
    def __init__(self, settings: Settings):
        if not settings.linear_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LINEAR_API_KEY is not configured",
            )

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": settings.linear_api_key,
                "Content-Type": "application/json",
            },
            timeout=settings.linear_timeout_seconds,
        )
        self._settings = settings

    async def __aenter__(self) -> "LinearClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def _query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.post(
                self._settings.linear_api_url,
                json={"query": query, "variables": variables or {}},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Linear request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Linear API returned {response.status_code}: {response.text}",
            )

        payload = response.json()
        if payload.get("errors"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Linear API error: {payload['errors']}",
            )

        return payload.get("data", {})

    async def _resolve_team_id(self, request: LinearTeamScopeRequest) -> str:
        if request.team_id:
            return request.team_id

        payload = await self._query(
            LINEAR_TEAM_DIRECTORY_QUERY,
            {"first": 100},
        )
        teams = payload.get("teams", {}).get("nodes", [])
        normalized_key = (request.team_key or "").strip().lower()
        for team in teams:
            if str(team.get("key", "")).strip().lower() == normalized_key:
                return str(team["id"])

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Linear team '{request.team_key}' was not found",
        )

    async def fetch_team_snapshot(
        self,
        team_request: LinearTeamScopeRequest,
    ) -> WorkScopeSnapshot:
        team_id = await self._resolve_team_id(team_request)
        payload = await self._query(
            LINEAR_TEAM_SNAPSHOT_QUERY,
            {
                "teamId": team_id,
                "issueLimit": team_request.issue_limit,
                "cycleLimit": team_request.cycle_limit,
            },
        )
        team = payload.get("team")
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Linear team '{team_id}' was not found",
            )

        scope_id = str(team["id"])
        scope_name = team.get("name") or team.get("key") or scope_id
        cycles = team.get("cycles", {}).get("nodes", [])
        current_cycle = _find_current_cycle(cycles)

        iterations: list[WorkIteration] = []
        if current_cycle and team_request.include_current_cycle:
            iterations.append(
                WorkIteration(
                    source="linear",
                    external_id=str(current_cycle["id"]),
                    name=current_cycle.get("name")
                    or f"Cycle {current_cycle.get('number', '')}".strip(),
                    state="current",
                    scope_id=scope_id,
                    scope_name=scope_name,
                    start_date=_parse_datetime(current_cycle.get("startsAt")),
                    end_date=_parse_datetime(current_cycle.get("endsAt")),
                    progress=_to_float(current_cycle.get("progress")),
                )
            )

        items: list[WorkItem] = []
        for issue in team.get("issues", {}).get("nodes", []):
            cycle = issue.get("cycle")
            status_category = _map_linear_status(issue)
            is_current_iteration = bool(
                current_cycle and cycle and str(cycle.get("id")) == str(current_cycle["id"])
            )
            is_backlog = cycle is None and status_category not in {"done", "canceled"}

            should_include = False
            if is_current_iteration and team_request.include_current_cycle:
                should_include = True
            if is_backlog and team_request.include_backlog:
                should_include = True

            if not should_include:
                continue

            items.append(
                _normalize_linear_issue(
                    issue,
                    scope_id=scope_id,
                    scope_name=scope_name,
                    current_cycle=current_cycle,
                    is_backlog=is_backlog,
                )
            )

        deduped_items = list({item.external_id: item for item in items}.values())
        return WorkScopeSnapshot(
            source="linear",
            scope_id=scope_id,
            scope_name=scope_name,
            iterations=iterations,
            summary=_work_item_summary(deduped_items),
            items=deduped_items,
        )


def _find_current_cycle(cycles: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    active_cycles: list[tuple[datetime, dict[str, Any]]] = []
    for cycle in cycles:
        start_date = _parse_datetime(cycle.get("startsAt"))
        end_date = _parse_datetime(cycle.get("endsAt"))
        if start_date and end_date and start_date <= now <= end_date:
            active_cycles.append((start_date, cycle))

    if not active_cycles:
        return None

    active_cycles.sort(key=lambda value: value[0], reverse=True)
    return active_cycles[0][1]


def _map_jira_status(status: dict[str, Any], *, is_backlog: bool) -> str:
    category_key = (
        (status.get("statusCategory") or {}).get("key", "")
        or (status.get("statusCategory") or {}).get("name", "")
    ).lower()
    name = str(status.get("name", "")).lower()
    if category_key == "done":
        return "done"
    if "cancel" in name:
        return "canceled"
    if is_backlog or category_key == "new":
        return "backlog"
    return "in_progress"


def _map_linear_status(issue: dict[str, Any]) -> str:
    state_type = str((issue.get("state") or {}).get("type", "")).lower()
    if state_type == "completed":
        return "done"
    if state_type == "canceled":
        return "canceled"
    if state_type in {"backlog", "unstarted", "triage"}:
        return "backlog"
    return "in_progress"


def _normalize_jira_issue(
    issue: dict[str, Any],
    *,
    base_url: str,
    board_name: str,
    team_name: str,
    scope_id: str,
    story_points_field: str | None,
    iteration: WorkIteration | None,
    is_backlog: bool,
) -> WorkItem:
    fields = issue.get("fields", {})
    status = fields.get("status") or {}
    assignee = fields.get("assignee") or {}
    project = fields.get("project") or {}
    priority = fields.get("priority") or {}
    estimate = _to_float(fields.get(story_points_field)) if story_points_field else None

    return WorkItem(
        source="jira",
        scope_id=scope_id,
        scope_name=board_name,
        external_id=issue.get("key") or str(issue.get("id")),
        title=fields.get("summary") or issue.get("key") or "Untitled issue",
        url=f"{base_url}/browse/{issue.get('key')}" if issue.get("key") else None,
        project_name=project.get("name"),
        team_name=team_name,
        assignee_name=assignee.get("displayName") or assignee.get("name"),
        status_name=status.get("name") or "Unknown",
        status_category=_map_jira_status(status, is_backlog=is_backlog),
        labels=list(fields.get("labels") or []),
        estimate=estimate,
        priority=priority.get("name"),
        is_backlog=is_backlog,
        is_current_iteration=iteration is not None,
        iteration_id=iteration.external_id if iteration else None,
        iteration_name=iteration.name if iteration else None,
        created_at=_parse_datetime(fields.get("created")),
        updated_at=_parse_datetime(fields.get("updated")),
        completed_at=None,
    )


def _normalize_linear_issue(
    issue: dict[str, Any],
    *,
    scope_id: str,
    scope_name: str,
    current_cycle: dict[str, Any] | None,
    is_backlog: bool,
) -> WorkItem:
    cycle = issue.get("cycle") or {}
    assignee = issue.get("assignee") or {}
    project = issue.get("project") or {}
    labels = [label.get("name") for label in (issue.get("labels") or {}).get("nodes", [])]
    labels = [label for label in labels if label]
    current_cycle_id = str(current_cycle["id"]) if current_cycle else None
    cycle_id = str(cycle.get("id")) if cycle.get("id") else None

    return WorkItem(
        source="linear",
        scope_id=scope_id,
        scope_name=scope_name,
        external_id=issue.get("identifier") or str(issue.get("id")),
        title=issue.get("title") or "Untitled issue",
        url=issue.get("url"),
        project_name=project.get("name"),
        team_name=scope_name,
        assignee_name=assignee.get("name"),
        status_name=(issue.get("state") or {}).get("name") or "Unknown",
        status_category=_map_linear_status(issue),
        labels=labels,
        estimate=_to_float(issue.get("estimate")),
        is_backlog=is_backlog,
        is_current_iteration=bool(current_cycle_id and current_cycle_id == cycle_id),
        iteration_id=cycle_id,
        iteration_name=cycle.get("name"),
        created_at=_parse_datetime(issue.get("createdAt")),
        updated_at=_parse_datetime(issue.get("updatedAt")),
        completed_at=_parse_datetime(issue.get("completedAt")),
    )


def _resolve_jira_request(payload: JiraSnapshotRequest | None) -> JiraSnapshotRequest:
    settings = get_settings()
    if payload and payload.boards:
        return payload

    default_boards = [
        JiraBoardScopeRequest(board_id=board_id)
        for board_id in settings.jira_default_board_id_list
    ]
    if not default_boards:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Jira boards were provided and JIRA_DEFAULT_BOARD_IDS is empty",
        )
    return JiraSnapshotRequest(boards=default_boards)


def _resolve_linear_request(payload: LinearSnapshotRequest | None) -> LinearSnapshotRequest:
    settings = get_settings()
    if payload and payload.teams:
        return payload

    default_teams = [
        LinearTeamScopeRequest(team_id=team_id)
        for team_id in settings.linear_default_team_id_list
    ]
    if not default_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Linear teams were provided and LINEAR_DEFAULT_TEAM_IDS is empty",
        )
    return LinearSnapshotRequest(teams=default_teams)


async def fetch_jira_snapshot(payload: JiraSnapshotRequest | None) -> WorkSnapshotResponse:
    request = _resolve_jira_request(payload)
    settings = get_settings()

    async with JiraClient(settings) as client:
        scopes = await asyncio.gather(
            *(client.fetch_board_snapshot(board) for board in request.boards)
        )

    all_items = [item for scope in scopes for item in scope.items]
    return WorkSnapshotResponse(
        scopes=list(scopes),
        summary=_work_item_summary(all_items),
    )


async def fetch_linear_snapshot(
    payload: LinearSnapshotRequest | None,
) -> WorkSnapshotResponse:
    request = _resolve_linear_request(payload)
    settings = get_settings()

    async with LinearClient(settings) as client:
        scopes = await asyncio.gather(
            *(client.fetch_team_snapshot(team) for team in request.teams)
        )

    all_items = [item for scope in scopes for item in scope.items]
    return WorkSnapshotResponse(
        scopes=list(scopes),
        summary=_work_item_summary(all_items),
    )


async def fetch_dashboard(payload: DashboardRequest) -> DashboardResponse:
    snapshot_tasks = []
    if payload.jira is not None:
        snapshot_tasks.append(fetch_jira_snapshot(payload.jira))
    if payload.linear is not None:
        snapshot_tasks.append(fetch_linear_snapshot(payload.linear))

    if not snapshot_tasks:
        settings = get_settings()
        if settings.jira_default_board_id_list:
            snapshot_tasks.append(fetch_jira_snapshot(None))
        if settings.linear_default_team_id_list:
            snapshot_tasks.append(fetch_linear_snapshot(None))

    if not snapshot_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Jira or Linear scope was provided for dashboard aggregation",
        )

    snapshots = await asyncio.gather(*snapshot_tasks)
    scopes = [scope for snapshot in snapshots for scope in snapshot.scopes]
    items = [item for scope in scopes for item in scope.items]
    return DashboardResponse(
        summary=_work_item_summary(
            items,
            exclude_canceled_from_progress=payload.exclude_canceled_from_progress,
        ),
        areas=build_dashboard_areas(
            items,
            group_by=payload.group_by,
            exclude_canceled_from_progress=payload.exclude_canceled_from_progress,
        ),
        sources=build_dashboard_areas(
            items,
            group_by="source",
            exclude_canceled_from_progress=payload.exclude_canceled_from_progress,
        ),
        scopes=scopes,
        items=list(items) if payload.include_items else [],
    )
