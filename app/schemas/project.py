from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5)
    goal: str = Field(min_length=5)
    tech_stack: list[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    pm_id: Optional[int] = None
    priority: str = "HIGH"
    mvp_scope: str = Field(min_length=5)
    ai_prompt: str = ""


class ProjectResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str
    goal: str
    tech_stack: list[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    pm_id: int
    priority: str
    mvp_scope: str
    created_at: datetime


class ProjectProfileRequest(BaseModel):
    project_role: str
    tech_stack: list[str]
    strong_tasks: list[str]
    disliked_tasks: list[str]
    available_hours_per_day: int = Field(ge=1, le=24)
    experience_level: str


class ProjectMemberProfileResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    user_name: str
    user_email: Optional[str] = None
    project_role: str
    tech_stack: list[str]
    strong_tasks: list[str]
    disliked_tasks: list[str]
    available_hours_per_day: int
    experience_level: str
    joined_at: datetime


class TeamMemberSummary(BaseModel):
    user_id: int
    user_name: str
    user_email: Optional[str] = None
    workspace_role: str
    joined_at: datetime
    project_profile: Optional[ProjectMemberProfileResponse] = None


class BacklogCreateRequest(BaseModel):
    title: str
    description: str
    priority: str
    required_role: Optional[str] = None
    required_tech_stack: list[str]
    difficulty: str
    estimated_hours: int = Field(ge=1)


class BacklogUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    required_role: Optional[str] = None
    required_tech_stack: Optional[list[str]] = None
    difficulty: Optional[str] = None
    estimated_hours: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = None


class BacklogResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    priority: str
    required_role: Optional[str] = None
    required_tech_stack: list[str]
    difficulty: str
    estimated_hours: int
    status: str
    linked_issue_id: Optional[int] = None
    created_at: datetime


class SprintCreateRequest(BaseModel):
    name: str
    goal: str
    start_date: str
    end_date: str


class SprintResponse(BaseModel):
    id: int
    project_id: int
    name: str
    goal: str
    start_date: str
    end_date: str
    status: str
    created_at: datetime


class SprintIssueAddRequest(BaseModel):
    issue_ids: list[int]


class IssueCreateRequest(BaseModel):
    title: str
    description: str
    priority: str
    difficulty: str
    estimated_hours: int = Field(ge=1)
    required_role: Optional[str] = None
    required_tech_stack: list[str]
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[str] = None


class IssueStatusUpdateRequest(BaseModel):
    status: str


class IssueAssigneeUpdateRequest(BaseModel):
    assignee_id: Optional[int] = None
    assignment_reason: Optional[str] = None


class IssueResponse(BaseModel):
    id: int
    project_id: int
    sprint_id: Optional[int] = None
    backlog_item_id: Optional[int] = None
    assignee_id: Optional[int] = None
    title: str
    description: str
    status: str
    priority: str
    difficulty: str
    estimated_hours: int
    required_role: Optional[str] = None
    required_tech_stack: list[str]
    assignment_reason: Optional[str] = None
    due_date: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime


class DashboardResponse(BaseModel):
    total_issues: int
    completed_issues: int
    in_progress_issues: int
    remaining_issues: int
    sprint_progress: int
    team_workload: list[dict]
    risk_issues: list[dict]
    bottleneck_summary: str
    recommended_next_issue: Optional[dict] = None
