from typing import Optional

from pydantic import BaseModel


class TaskGenerationRequest(BaseModel):
    create_backlog: bool = True


class TaskSuggestion(BaseModel):
    title: str
    description: str
    required_role: str
    required_tech_stack: list[str]
    difficulty: str
    estimated_hours: int
    priority: str


class TaskGenerationResponse(BaseModel):
    project_summary: str
    tasks: list[TaskSuggestion]
    created_backlog_items: list[int]


class AssignmentRequest(BaseModel):
    backlog_item_ids: list[int]


class CandidateScore(BaseModel):
    user_id: int
    user_name: str
    score: int
    stars: str
    reasons: list[str]


class AssignmentSuggestion(BaseModel):
    backlog_item_id: int
    title: str
    recommended_assignee_id: Optional[int] = None
    recommended_assignee_name: Optional[str] = None
    recommendation_reason: str
    candidates: list[CandidateScore]


class AssignmentResponse(BaseModel):
    assignments: list[AssignmentSuggestion]


class AssignmentConfirmItem(BaseModel):
    backlog_item_id: int
    assignee_id: int
    assignment_reason: str
    sprint_id: Optional[int] = None


class AssignmentConfirmRequest(BaseModel):
    assignments: list[AssignmentConfirmItem]


class AssignmentConfirmResponse(BaseModel):
    created_issue_ids: list[int]
