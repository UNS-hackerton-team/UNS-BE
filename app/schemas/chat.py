from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    user_message_id: int
    ai_message_id: int
    room_type: str
    answer: dict


class ChatHistoryMessageResponse(BaseModel):
    id: int
    chat_room_id: int
    sender_id: Optional[int] = None
    sender_type: str
    content: str
    metadata: Optional[str] = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    room_type: str
    messages: list[ChatHistoryMessageResponse]
