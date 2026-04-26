from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.invites import router as invite_router
from app.api.v1.projects import router as project_router
from app.api.v1.workspaces import router as workspace_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(workspace_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(invite_router, prefix="/invites", tags=["invites"])
api_router.include_router(project_router, tags=["projects"])
api_router.include_router(ai_router, tags=["ai"])
api_router.include_router(chat_router, tags=["chat"])
