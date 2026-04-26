from typing import Optional

from app.core.config import get_settings
from app.schemas.auth import UserProfile


def authenticate_user(email: str, password: str) -> Optional[UserProfile]:
    settings = get_settings()
    if email != settings.demo_user_email:
        return None
    if password != settings.demo_user_password:
        return None

    return UserProfile(email=email, name="UNS Admin")
