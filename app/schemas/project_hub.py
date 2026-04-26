from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.project import (
    BacklogResponse,
    DashboardResponse,
    ProjectResponse,
    TeamMemberSummary,
)
from app.schemas.work_tracking import DashboardArea, ProgressSummary, WorkItem


class ProjectSettingsResponse(BaseModel):
    id: int
    project_id: int
    ai_prompt: str
    tech_stack_notes: str
    summary_cache: str
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ProjectSettingsUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, min_length=5)
    goal: Optional[str] = Field(default=None, min_length=5)
    tech_stack: Optional[list[str]] = None
    priority: Optional[str] = None
    mvp_scope: Optional[str] = Field(default=None, min_length=5)
    ai_prompt: Optional[str] = None
    tech_stack_notes: Optional[str] = None


class ProjectPermissionResponse(BaseModel):
    current_user_id: int
    pm_user_id: int
    is_pm: bool


class ProjectPmTransferRequest(BaseModel):
    new_pm_user_id: int


class ProjectDomainCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=50)
    color: str = Field(default="#0F172A", min_length=4, max_length=20)


class ProjectDomainUpdateRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    color: Optional[str] = Field(default=None, min_length=4, max_length=20)
    is_active: Optional[bool] = None


class ProjectDomainResponse(BaseModel):
    id: int
    project_id: int
    code: str
    name: str
    color: str
    is_active: bool
    created_at: datetime


class ProjectDomainMappingRequest(BaseModel):
    domain_id: int
    source: Literal["any", "jira", "linear", "internal"] = "any"
    match_field: Literal[
        "label",
        "project",
        "team",
        "title",
        "required_role",
        "tech_stack",
        "scope",
        "assignee",
    ]
    match_value: str = Field(min_length=1, max_length=255)


class ProjectDomainMappingResponse(BaseModel):
    id: int
    project_id: int
    domain_id: int
    source: str
    match_field: str
    match_value: str
    created_at: datetime


class WorkspaceIntegrationResponse(BaseModel):
    id: int
    workspace_id: int
    provider: str
    external_workspace_id: str
    external_workspace_name: str
    external_workspace_url: Optional[str] = None
    scope: Optional[str] = None
    status: str
    connected_by: Optional[int] = None
    token_expires_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IntegrationConnectUrlResponse(BaseModel):
    provider: str
    configured: bool
    authorization_url: Optional[str] = None
    message: Optional[str] = None


class IntegrationCatalogItemResponse(BaseModel):
    id: str
    name: str
    key: Optional[str] = None
    url: Optional[str] = None


class IntegrationCatalogResponse(BaseModel):
    provider: str
    items: list[IntegrationCatalogItemResponse] = Field(default_factory=list)


class ProjectIntegrationBindingRequest(BaseModel):
    workspace_integration_id: int
    scope_type: str = Field(min_length=2, max_length=30)
    scope_id: str = Field(min_length=1, max_length=255)
    scope_name: str = Field(min_length=1, max_length=255)
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectIntegrationResponse(BaseModel):
    id: int
    project_id: int
    workspace_integration_id: int
    provider: str
    scope_type: str
    scope_id: str
    scope_name: str
    settings: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime


class ProjectMemoryEntryRequest(BaseModel):
    memory_type: Literal["MEETING", "DECISION", "SUMMARY", "CHAT_NOTE", "PROMPT_NOTE"]
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2)


class MeetingIngestRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    transcript: str = Field(min_length=2)
    source: Literal["MANUAL", "GEMINI"] = "MANUAL"
    participants: list[str] = Field(default_factory=list)


class ProjectMemoryEntryResponse(BaseModel):
    id: int
    project_id: int
    memory_type: str
    title: str
    content: str
    status: str
    created_by: Optional[int] = None
    created_at: datetime


class DomainProgressResponse(BaseModel):
    domain_id: int
    code: str
    name: str
    color: str
    summary: ProgressSummary
    sources: list[str] = Field(default_factory=list)


class ProjectDeliveryDashboardResponse(BaseModel):
    summary: ProgressSummary
    sources: list[DashboardArea] = Field(default_factory=list)
    domains: list[DomainProgressResponse] = Field(default_factory=list)
    active_items: list[WorkItem] = Field(default_factory=list)
    unmapped_items: int = 0
    integration_warnings: list[str] = Field(default_factory=list)


class PersonalRecommendationResponse(BaseModel):
    summary: str
    current_assignments: list[dict[str, Any]] = Field(default_factory=list)
    recommended_backlog: list[dict[str, Any]] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    excluded_titles: list[str] = Field(default_factory=list)


class ProjectHubResponse(BaseModel):
    project: ProjectResponse
    settings: ProjectSettingsResponse
    permissions: ProjectPermissionResponse
    members: list[TeamMemberSummary] = Field(default_factory=list)
    backlog: list[BacklogResponse] = Field(default_factory=list)
    internal_dashboard: DashboardResponse
    delivery_dashboard: ProjectDeliveryDashboardResponse
    domains: list[ProjectDomainResponse] = Field(default_factory=list)
    domain_mappings: list[ProjectDomainMappingResponse] = Field(default_factory=list)
    workspace_integrations: list[WorkspaceIntegrationResponse] = Field(default_factory=list)
    project_integrations: list[ProjectIntegrationResponse] = Field(default_factory=list)
    memories: list[ProjectMemoryEntryResponse] = Field(default_factory=list)
    personal_recommendation: PersonalRecommendationResponse
