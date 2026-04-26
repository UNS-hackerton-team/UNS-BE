from typing import Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    password: str


class UserProfile(BaseModel):
    id: int
    name: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
