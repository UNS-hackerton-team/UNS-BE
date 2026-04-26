from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=2, max_length=300)
    team_type: str = Field(min_length=2, max_length=50)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: str
    team_type: str
    owner_id: int
    invite_code: str
    invite_code_active: bool
    invite_code_expires_at: Optional[str] = None
    invite_code_max_uses: Optional[int] = None
    invite_code_used_count: int
    member_count: int
    created_at: str


class InviteInfoResponse(BaseModel):
    workspace_id: int
    workspace_name: str
    invite_code: str
    invite_url: str
    invite_code_active: bool
    invite_code_expires_at: Optional[str] = None
    invite_code_max_uses: Optional[int] = None
    invite_code_used_count: int
    member_count: int


class InviteRegenerateRequest(BaseModel):
    expires_at: Optional[str] = None
    max_uses: Optional[int] = Field(default=None, ge=1)


class InviteValidationResponse(BaseModel):
    valid: bool
    workspace_id: int
    workspace_name: str
    message: str
    invite_code_active: bool


class InviteJoinResponse(BaseModel):
    workspace_id: int
    workspace_name: str
    joined: bool
    workspace_role: str
