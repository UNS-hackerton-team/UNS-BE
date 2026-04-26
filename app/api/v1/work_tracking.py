from fastapi import APIRouter

from app.schemas.work_tracking import (
    DashboardRequest,
    DashboardResponse,
    JiraSnapshotRequest,
    LinearSnapshotRequest,
    WorkSnapshotResponse,
)
from app.services.work_tracking import (
    fetch_dashboard,
    fetch_jira_snapshot,
    fetch_linear_snapshot,
)


router = APIRouter()


@router.post("/jira/snapshot", response_model=WorkSnapshotResponse)
async def jira_snapshot(payload: JiraSnapshotRequest) -> WorkSnapshotResponse:
    return await fetch_jira_snapshot(payload)


@router.post("/linear/snapshot", response_model=WorkSnapshotResponse)
async def linear_snapshot(payload: LinearSnapshotRequest) -> WorkSnapshotResponse:
    return await fetch_linear_snapshot(payload)


@router.post("/dashboard", response_model=DashboardResponse)
async def dashboard(payload: DashboardRequest) -> DashboardResponse:
    return await fetch_dashboard(payload)
