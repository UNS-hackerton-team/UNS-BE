import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.deps import get_current_user
from app.core.security import decode_token
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.auth import get_user_by_id
from app.services.chat import (
    connection_manager,
    get_personal_history,
    get_team_history,
    room_key,
    send_personal_message,
    send_team_message,
)
from app.services.project import require_project_member


router = APIRouter()


@router.post("/projects/{project_id}/chat/team/messages", response_model=ChatMessageResponse)
async def send_team_message_endpoint(
    project_id: int,
    payload: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatMessageResponse:
    return ChatMessageResponse(**await send_team_message(project_id, current_user, payload.content))


@router.post("/projects/{project_id}/chat/personal/messages", response_model=ChatMessageResponse)
async def send_personal_message_endpoint(
    project_id: int,
    payload: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatMessageResponse:
    return ChatMessageResponse(**await send_personal_message(project_id, current_user, payload.content))


@router.get("/projects/{project_id}/chat/team/history", response_model=ChatHistoryResponse)
async def get_team_history_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ChatHistoryResponse:
    return ChatHistoryResponse(**get_team_history(project_id, current_user["id"]))


@router.get("/projects/{project_id}/chat/personal/history", response_model=ChatHistoryResponse)
async def get_personal_history_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ChatHistoryResponse:
    return ChatHistoryResponse(**get_personal_history(project_id, current_user["id"]))


@router.websocket("/projects/{project_id}/ws/chat/team")
async def team_chat_socket(websocket: WebSocket, project_id: int) -> None:
    user = _authenticate_websocket(websocket)
    require_project_member(project_id, user["id"])
    key = room_key(project_id, "TEAM_AI", None)
    await connection_manager.connect(key, websocket)
    await websocket.send_json(
        {
            "type": "history",
            "room_type": "TEAM_AI",
            "messages": get_team_history(project_id, user["id"])["messages"],
        }
    )
    try:
        while True:
            payload = await websocket.receive_json()
            content = str(payload.get("content", "")).strip()
            if not content:
                continue
            response = await send_team_message(project_id, user, content)
            await connection_manager.broadcast(
                key,
                {
                    "type": "message",
                    "room_type": "TEAM_AI",
                    "user_message": {
                        "sender_type": "USER",
                        "sender_id": user["id"],
                        "content": content,
                    },
                    "ai_message": {
                        "sender_type": "AI",
                        "content": response["answer"].get("summary") or json.dumps(response["answer"]),
                        "payload": response["answer"],
                    },
                },
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(key, websocket)


@router.websocket("/projects/{project_id}/ws/chat/personal")
async def personal_chat_socket(websocket: WebSocket, project_id: int) -> None:
    user = _authenticate_websocket(websocket)
    require_project_member(project_id, user["id"])
    key = room_key(project_id, "PERSONAL_AI", user["id"])
    await connection_manager.connect(key, websocket)
    await websocket.send_json(
        {
            "type": "history",
            "room_type": "PERSONAL_AI",
            "messages": get_personal_history(project_id, user["id"])["messages"],
        }
    )
    try:
        while True:
            payload = await websocket.receive_json()
            content = str(payload.get("content", "")).strip()
            if not content:
                continue
            response = await send_personal_message(project_id, user, content)
            await connection_manager.broadcast(
                key,
                {
                    "type": "message",
                    "room_type": "PERSONAL_AI",
                    "user_message": {
                        "sender_type": "USER",
                        "sender_id": user["id"],
                        "content": content,
                    },
                    "ai_message": {
                        "sender_type": "AI",
                        "content": response["answer"].get("summary") or json.dumps(response["answer"]),
                        "payload": response["answer"],
                    },
                },
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(key, websocket)


def _authenticate_websocket(websocket: WebSocket) -> dict:
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketDisconnect(code=4401)
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise WebSocketDisconnect(code=4401)
    user = get_user_by_id(int(user_id))
    if user is None:
        raise WebSocketDisconnect(code=4404)
    return user
