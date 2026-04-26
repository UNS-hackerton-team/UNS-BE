from fastapi import APIRouter, Depends, Request

from app.core.deps import get_current_user
from app.schemas.workspace import (
    InviteInfoResponse,
    InviteRegenerateRequest,
    WorkspaceCreateRequest,
    WorkspaceListItemResponse,
    WorkspaceResponse,
)
from app.services.workspace import (
    create_workspace,
    deactivate_invite,
    get_invite_info,
    get_workspace,
    list_workspaces,
    regenerate_invite,
)


router = APIRouter()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("", response_model=list[WorkspaceListItemResponse])
async def list_workspaces_endpoint(
    current_user: dict = Depends(get_current_user),
) -> list[WorkspaceListItemResponse]:
    workspaces = list_workspaces(current_user["id"])
    return [WorkspaceListItemResponse(**workspace) for workspace in workspaces]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace_endpoint(
    payload: WorkspaceCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> WorkspaceResponse:
    workspace = create_workspace(current_user["id"], payload.name, payload.description, payload.team_type)
    return WorkspaceResponse(**workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_endpoint(
    workspace_id: int,
    current_user: dict = Depends(get_current_user),
) -> WorkspaceResponse:
    return WorkspaceResponse(**get_workspace(workspace_id, current_user["id"]))


@router.get("/{workspace_id}/invite", response_model=InviteInfoResponse)
async def get_workspace_invite_endpoint(
    workspace_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> InviteInfoResponse:
    invite = get_invite_info(workspace_id, current_user["id"], _base_url(request))
    return InviteInfoResponse(**invite)


@router.patch("/{workspace_id}/invite/regenerate", response_model=InviteInfoResponse)
async def regenerate_invite_endpoint(
    workspace_id: int,
    payload: InviteRegenerateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> InviteInfoResponse:
    invite = regenerate_invite(
        workspace_id,
        current_user["id"],
        payload.expires_at,
        payload.max_uses,
        _base_url(request),
    )
    return InviteInfoResponse(**invite)


@router.patch("/{workspace_id}/invite/deactivate", response_model=InviteInfoResponse)
async def deactivate_invite_endpoint(
    workspace_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> InviteInfoResponse:
    invite = deactivate_invite(workspace_id, current_user["id"], _base_url(request))
    return InviteInfoResponse(**invite)
