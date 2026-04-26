from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    user_message_id: int
    ai_message_id: int
    room_type: str
    answer: dict
