from fastapi import APIRouter, Depends, Response, status

from app.core.deps import get_current_user
from app.schemas.project import (
    BacklogCreateRequest,
    BacklogResponse,
    BacklogUpdateRequest,
    DashboardResponse,
    IssueAssigneeUpdateRequest,
    IssueCreateRequest,
    IssueResponse,
    IssueStatusUpdateRequest,
    ProjectCreateRequest,
    ProjectMemberProfileResponse,
    ProjectProfileRequest,
    ProjectResponse,
    SprintCreateRequest,
    SprintIssueAddRequest,
    SprintResponse,
    TeamMemberSummary,
)
from app.services.project import (
    add_issues_to_sprint,
    create_backlog_item,
    create_issue,
    create_project,
    create_sprint,
    delete_backlog_item,
    get_dashboard,
    get_project,
    list_backlog,
    list_project_members,
    list_projects,
    list_sprints,
    update_backlog_item,
    update_issue_assignee,
    update_issue_status,
    upsert_project_profile,
)


router = APIRouter()


@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectResponse)
async def create_project_endpoint(
    workspace_id: int,
    payload: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectResponse:
    project = create_project(
        workspace_id=workspace_id,
        current_user_id=current_user["id"],
        name=payload.name,
        description=payload.description,
        goal=payload.goal,
        tech_stack=payload.tech_stack,
        start_date=payload.start_date,
        end_date=payload.end_date,
        pm_id=payload.pm_id or current_user["id"],
        priority=payload.priority,
        mvp_scope=payload.mvp_scope,
    )
    return ProjectResponse(**project)


@router.get("/workspaces/{workspace_id}/projects", response_model=list[ProjectResponse])
async def list_projects_endpoint(
    workspace_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[ProjectResponse]:
    return [ProjectResponse(**project) for project in list_projects(workspace_id, current_user["id"])]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ProjectResponse:
    return ProjectResponse(**get_project(project_id, current_user["id"]))


@router.post("/projects/{project_id}/members/profile", response_model=ProjectMemberProfileResponse)
async def create_project_profile_endpoint(
    project_id: int,
    payload: ProjectProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectMemberProfileResponse:
    profile = upsert_project_profile(project_id, current_user, payload.model_dump())
    return ProjectMemberProfileResponse(**profile)


@router.patch("/projects/{project_id}/members/profile", response_model=ProjectMemberProfileResponse)
async def update_project_profile_endpoint(
    project_id: int,
    payload: ProjectProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectMemberProfileResponse:
    profile = upsert_project_profile(project_id, current_user, payload.model_dump())
    return ProjectMemberProfileResponse(**profile)


@router.get("/projects/{project_id}/members", response_model=list[TeamMemberSummary])
async def list_project_members_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[TeamMemberSummary]:
    return [TeamMemberSummary(**member) for member in list_project_members(project_id, current_user["id"])]


@router.get("/projects/{project_id}/backlog", response_model=list[BacklogResponse])
async def list_backlog_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[BacklogResponse]:
    return [BacklogResponse(**item) for item in list_backlog(project_id, current_user["id"])]


@router.post("/projects/{project_id}/backlog", response_model=BacklogResponse)
async def create_backlog_endpoint(
    project_id: int,
    payload: BacklogCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> BacklogResponse:
    return BacklogResponse(**create_backlog_item(project_id, current_user["id"], payload.model_dump()))


@router.patch("/backlog/{backlog_item_id}", response_model=BacklogResponse)
async def update_backlog_endpoint(
    backlog_item_id: int,
    payload: BacklogUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> BacklogResponse:
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    return BacklogResponse(**update_backlog_item(backlog_item_id, current_user["id"], updates))


@router.delete("/backlog/{backlog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backlog_endpoint(
    backlog_item_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    delete_backlog_item(backlog_item_id, current_user["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/sprints", response_model=SprintResponse)
async def create_sprint_endpoint(
    project_id: int,
    payload: SprintCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> SprintResponse:
    return SprintResponse(**create_sprint(project_id, current_user["id"], payload.model_dump()))


@router.get("/projects/{project_id}/sprints", response_model=list[SprintResponse])
async def list_sprints_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[SprintResponse]:
    return [SprintResponse(**sprint) for sprint in list_sprints(project_id, current_user["id"])]


@router.post("/sprints/{sprint_id}/issues", response_model=SprintResponse)
async def add_sprint_issues_endpoint(
    sprint_id: int,
    payload: SprintIssueAddRequest,
    current_user: dict = Depends(get_current_user),
) -> SprintResponse:
    return SprintResponse(**add_issues_to_sprint(sprint_id, payload.issue_ids, current_user["id"]))


@router.post("/projects/{project_id}/issues", response_model=IssueResponse)
async def create_issue_endpoint(
    project_id: int,
    payload: IssueCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> IssueResponse:
    return IssueResponse(**create_issue(project_id, current_user["id"], payload.model_dump()))


@router.patch("/issues/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status_endpoint(
    issue_id: int,
    payload: IssueStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> IssueResponse:
    return IssueResponse(**update_issue_status(issue_id, current_user["id"], payload.status))


@router.patch("/issues/{issue_id}/assignee", response_model=IssueResponse)
async def update_issue_assignee_endpoint(
    issue_id: int,
    payload: IssueAssigneeUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> IssueResponse:
    return IssueResponse(
        **update_issue_assignee(
            issue_id,
            current_user["id"],
            payload.assignee_id,
            payload.assignment_reason,
        )
    )


@router.get("/projects/{project_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> DashboardResponse:
    return DashboardResponse(**get_dashboard(project_id, current_user["id"]))
