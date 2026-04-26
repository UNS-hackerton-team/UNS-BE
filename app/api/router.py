from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.work_tracking import router as work_tracking_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    work_tracking_router,
    prefix="/work-tracking",
    tags=["work-tracking"],
)

