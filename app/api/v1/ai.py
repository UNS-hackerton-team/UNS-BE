from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.ai import (
    AssignmentConfirmRequest,
    AssignmentConfirmResponse,
    AssignmentRequest,
    AssignmentResponse,
    TaskGenerationRequest,
    TaskGenerationResponse,
)
from app.services.ai import confirm_assignments, generate_project_tasks, recommend_assignments


router = APIRouter()


@router.post("/projects/{project_id}/ai/tasks", response_model=TaskGenerationResponse)
async def generate_tasks_endpoint(
    project_id: int,
    payload: TaskGenerationRequest,
    current_user: dict = Depends(get_current_user),
) -> TaskGenerationResponse:
    return TaskGenerationResponse(
        **generate_project_tasks(project_id, current_user["id"], payload.create_backlog)
    )


@router.post("/projects/{project_id}/ai/assignments", response_model=AssignmentResponse)
async def recommend_assignments_endpoint(
    project_id: int,
    payload: AssignmentRequest,
    current_user: dict = Depends(get_current_user),
) -> AssignmentResponse:
    return AssignmentResponse(
        **recommend_assignments(project_id, current_user["id"], payload.backlog_item_ids)
    )


@router.post("/projects/{project_id}/ai/assignments/confirm", response_model=AssignmentConfirmResponse)
async def confirm_assignments_endpoint(
    project_id: int,
    payload: AssignmentConfirmRequest,
    current_user: dict = Depends(get_current_user),
) -> AssignmentConfirmResponse:
    return AssignmentConfirmResponse(
        **confirm_assignments(project_id, current_user["id"], [item.model_dump() for item in payload.assignments])
    )
