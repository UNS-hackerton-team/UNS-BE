from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from typing import Literal, Optional

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
    team_id: Optional[str] = None
    team_key: Optional[str] = None
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
    jira: Optional[JiraSnapshotRequest] = None
    linear: Optional[LinearSnapshotRequest] = None
    group_by: DashboardGroupBy = "project"
    include_items: bool = False
    exclude_canceled_from_progress: bool = True


class WorkIteration(BaseModel):
    source: Literal["jira", "linear"]
    external_id: str
    name: str
    state: Optional[str] = None
    scope_id: str
    scope_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: Optional[str] = None
    progress: Optional[float] = None


class WorkItem(BaseModel):
    source: Literal["jira", "linear"]
    scope_id: str
    scope_name: str
    external_id: str
    title: str
    url: Optional[str] = None
    project_name: Optional[str] = None
    team_name: Optional[str] = None
    assignee_name: Optional[str] = None
    status_name: str
    status_category: WorkStatusCategory
    labels: list[str] = Field(default_factory=list)
    estimate: Optional[float] = None
    priority: Optional[str] = None
    is_backlog: bool = False
    is_current_iteration: bool = False
    iteration_id: Optional[str] = None
    iteration_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ProgressSummary(BaseModel):
    total_items: int
    effective_items: int
    backlog_items: int
    in_progress_items: int
    done_items: int
    canceled_items: int
    total_estimate: Optional[float] = None
    completed_estimate: Optional[float] = None
    completion_rate: float
    weighted_completion_rate: Optional[float] = None


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
