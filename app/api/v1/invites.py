from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.workspace import InviteJoinResponse, InviteValidationResponse
from app.services.workspace import join_workspace_by_invite, validate_invite_code


router = APIRouter()


@router.get("/{invite_code}", response_model=InviteValidationResponse)
async def validate_invite_endpoint(invite_code: str) -> InviteValidationResponse:
    return InviteValidationResponse(**validate_invite_code(invite_code))


@router.post("/{invite_code}/join", response_model=InviteJoinResponse)
async def join_invite_endpoint(
    invite_code: str,
    current_user: dict = Depends(get_current_user),
) -> InviteJoinResponse:
    return InviteJoinResponse(**join_workspace_by_invite(invite_code, current_user["id"]))
