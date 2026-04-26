from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


WorkStatusCategory = Literal["backlog", "in_progress", "done", "canceled"]
DashboardGroupBy = Literal[
    "source",
    "scope",
    "project",
    "team",
    "assignee",
    "label",
    "status_category",
]


class JiraBoardScopeRequest(BaseModel):
    board_id: int
    sprint_state: Literal["active", "future", "closed"] = "active"
    sprint_limit: int = Field(default=1, ge=1, le=10)
    sprint_issue_limit: int = Field(default=100, ge=1, le=500)
    backlog_limit: int = Field(default=100, ge=1, le=500)
    include_sprints: bool = True
    include_backlog: bool = True


class JiraSnapshotRequest(BaseModel):
    boards: list[JiraBoardScopeRequest] = Field(default_factory=list)


class LinearTeamScopeRequest(BaseModel):
    team_id: str | None = None
    team_key: str | None = None
    issue_limit: int = Field(default=250, ge=1, le=500)
    cycle_limit: int = Field(default=6, ge=1, le=20)
    include_current_cycle: bool = True
    include_backlog: bool = True

    @model_validator(mode="after")
    def validate_scope(self) -> "LinearTeamScopeRequest":
        if not self.team_id and not self.team_key:
            raise ValueError("Either team_id or team_key is required")
        return self


class LinearSnapshotRequest(BaseModel):
    teams: list[LinearTeamScopeRequest] = Field(default_factory=list)


class DashboardRequest(BaseModel):
    jira: JiraSnapshotRequest | None = None
    linear: LinearSnapshotRequest | None = None
    group_by: DashboardGroupBy = "project"
    include_items: bool = False
    exclude_canceled_from_progress: bool = True


class WorkIteration(BaseModel):
    source: Literal["jira", "linear"]
    external_id: str
    name: str
    state: str | None = None
    scope_id: str
    scope_name: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    goal: str | None = None
    progress: float | None = None


class WorkItem(BaseModel):
    source: Literal["jira", "linear"]
    scope_id: str
    scope_name: str
    external_id: str
    title: str
    url: str | None = None
    project_name: str | None = None
    team_name: str | None = None
    assignee_name: str | None = None
    status_name: str
    status_category: WorkStatusCategory
    labels: list[str] = Field(default_factory=list)
    estimate: float | None = None
    priority: str | None = None
    is_backlog: bool = False
    is_current_iteration: bool = False
    iteration_id: str | None = None
    iteration_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class ProgressSummary(BaseModel):
    total_items: int
    effective_items: int
    backlog_items: int
    in_progress_items: int
    done_items: int
    canceled_items: int
    total_estimate: float | None = None
    completed_estimate: float | None = None
    completion_rate: float
    weighted_completion_rate: float | None = None


class WorkScopeSnapshot(BaseModel):
    source: Literal["jira", "linear"]
    scope_id: str
    scope_name: str
    iterations: list[WorkIteration] = Field(default_factory=list)
    summary: ProgressSummary
    items: list[WorkItem] = Field(default_factory=list)


class WorkSnapshotResponse(BaseModel):
    scopes: list[WorkScopeSnapshot] = Field(default_factory=list)
    summary: ProgressSummary


class DashboardArea(BaseModel):
    key: str
    label: str
    summary: ProgressSummary


class DashboardResponse(BaseModel):
    summary: ProgressSummary
    areas: list[DashboardArea] = Field(default_factory=list)
    sources: list[DashboardArea] = Field(default_factory=list)
    scopes: list[WorkScopeSnapshot] = Field(default_factory=list)
    items: list[WorkItem] = Field(default_factory=list)
