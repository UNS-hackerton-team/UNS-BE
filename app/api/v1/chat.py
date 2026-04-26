from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.chat import send_personal_message, send_team_message


router = APIRouter()


@router.post("/projects/{project_id}/chat/team/messages", response_model=ChatMessageResponse)
async def send_team_message_endpoint(
    project_id: int,
    payload: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatMessageResponse:
    return ChatMessageResponse(**send_team_message(project_id, current_user, payload.content))


@router.post("/projects/{project_id}/chat/personal/messages", response_model=ChatMessageResponse)
async def send_personal_message_endpoint(
    project_id: int,
    payload: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatMessageResponse:
    return ChatMessageResponse(**send_personal_message(project_id, current_user, payload.content))
