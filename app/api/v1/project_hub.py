from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse, Response

from app.core.deps import get_current_user
from app.schemas.project import ProjectResponse
from app.schemas.project_hub import (
    IntegrationCatalogResponse,
    IntegrationConnectUrlResponse,
    PersonalRecommendationResponse,
    ProjectDeliveryDashboardResponse,
    ProjectDomainCreateRequest,
    ProjectDomainMappingRequest,
    ProjectDomainMappingResponse,
    ProjectDomainResponse,
    ProjectDomainUpdateRequest,
    ProjectHubResponse,
    ProjectIntegrationBindingRequest,
    ProjectIntegrationResponse,
    ProjectMemoryEntryRequest,
    ProjectMemoryEntryResponse,
    ProjectPermissionResponse,
    ProjectPmTransferRequest,
    ProjectSettingsResponse,
    ProjectSettingsUpdateRequest,
    WorkspaceIntegrationResponse,
    MeetingIngestRequest,
)
from app.services.integrations import (
    attach_project_integration,
    build_connect_url,
    handle_oauth_callback,
    list_integration_catalog,
    list_project_integrations,
    list_workspace_integrations,
    remove_project_integration,
)
from app.services.project_hub import (
    build_delivery_dashboard,
    build_personal_recommendation,
    create_domain,
    create_domain_mapping,
    create_memory_entry,
    delete_domain,
    delete_domain_mapping,
    get_project_hub,
    get_project_settings,
    ingest_meeting_note,
    list_domain_mappings,
    list_domains,
    list_memories,
    transfer_project_pm,
    update_domain,
    update_project_settings,
)


router = APIRouter()


@router.get("/projects/{project_id}/hub", response_model=ProjectHubResponse)
async def get_project_hub_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ProjectHubResponse:
    return ProjectHubResponse(**await get_project_hub(project_id, current_user["id"]))


@router.get("/projects/{project_id}/settings", response_model=ProjectSettingsResponse)
async def get_project_settings_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ProjectSettingsResponse:
    return ProjectSettingsResponse(**get_project_settings(project_id, current_user["id"]))


@router.patch("/projects/{project_id}/settings", response_model=ProjectSettingsResponse)
async def update_project_settings_endpoint(
    project_id: int,
    payload: ProjectSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectSettingsResponse:
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    return ProjectSettingsResponse(**update_project_settings(project_id, current_user["id"], updates))


@router.post("/projects/{project_id}/pm/transfer", response_model=ProjectResponse)
async def transfer_project_pm_endpoint(
    project_id: int,
    payload: ProjectPmTransferRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectResponse:
    return ProjectResponse(
        **transfer_project_pm(project_id, current_user["id"], payload.new_pm_user_id)
    )


@router.get("/projects/{project_id}/domains", response_model=list[ProjectDomainResponse])
async def list_domains_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[ProjectDomainResponse]:
    return [ProjectDomainResponse(**domain) for domain in list_domains(project_id, current_user["id"])]


@router.post("/projects/{project_id}/domains", response_model=ProjectDomainResponse)
async def create_domain_endpoint(
    project_id: int,
    payload: ProjectDomainCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectDomainResponse:
    return ProjectDomainResponse(**create_domain(project_id, current_user["id"], payload.model_dump()))


@router.patch("/domains/{domain_id}", response_model=ProjectDomainResponse)
async def update_domain_endpoint(
    domain_id: int,
    payload: ProjectDomainUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectDomainResponse:
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    return ProjectDomainResponse(**update_domain(domain_id, current_user["id"], updates))


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain_endpoint(
    domain_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    delete_domain(domain_id, current_user["id"])
    return Response(status_code=204)


@router.get("/projects/{project_id}/domain-mappings", response_model=list[ProjectDomainMappingResponse])
async def list_domain_mappings_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[ProjectDomainMappingResponse]:
    return [
        ProjectDomainMappingResponse(**mapping)
        for mapping in list_domain_mappings(project_id, current_user["id"])
    ]


@router.post("/projects/{project_id}/domain-mappings", response_model=ProjectDomainMappingResponse)
async def create_domain_mapping_endpoint(
    project_id: int,
    payload: ProjectDomainMappingRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectDomainMappingResponse:
    return ProjectDomainMappingResponse(
        **create_domain_mapping(project_id, current_user["id"], payload.model_dump())
    )


@router.delete("/domain-mappings/{mapping_id}", status_code=204)
async def delete_domain_mapping_endpoint(
    mapping_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    delete_domain_mapping(mapping_id, current_user["id"])
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/integrations", response_model=list[WorkspaceIntegrationResponse])
async def list_workspace_integrations_endpoint(
    workspace_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[WorkspaceIntegrationResponse]:
    return [
        WorkspaceIntegrationResponse(**integration)
        for integration in list_workspace_integrations(workspace_id, current_user["id"])
    ]


@router.get(
    "/workspaces/{workspace_id}/integrations/{provider}/connect",
    response_model=IntegrationConnectUrlResponse,
)
async def connect_integration_endpoint(
    workspace_id: int,
    provider: str,
    redirect_to: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> IntegrationConnectUrlResponse:
    return IntegrationConnectUrlResponse(
        **build_connect_url(
            workspace_id,
            current_user,
            provider,
            redirect_to=redirect_to,
        )
    )


@router.get("/integrations/oauth/{provider}/callback")
async def integration_callback_endpoint(
    provider: str,
    code: str,
    state: str,
) -> RedirectResponse:
    redirect_url = await handle_oauth_callback(provider, code, state)
    return RedirectResponse(redirect_url)


@router.get("/workspace-integrations/{integration_id}/catalog", response_model=IntegrationCatalogResponse)
async def integration_catalog_endpoint(
    integration_id: int,
    current_user: dict = Depends(get_current_user),
) -> IntegrationCatalogResponse:
    return IntegrationCatalogResponse(**await list_integration_catalog(integration_id, current_user["id"]))


@router.get("/projects/{project_id}/integrations", response_model=list[ProjectIntegrationResponse])
async def list_project_integrations_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[ProjectIntegrationResponse]:
    return [
        ProjectIntegrationResponse(**integration)
        for integration in list_project_integrations(project_id, current_user["id"])
    ]


@router.post("/projects/{project_id}/integrations", response_model=ProjectIntegrationResponse)
async def attach_project_integration_endpoint(
    project_id: int,
    payload: ProjectIntegrationBindingRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectIntegrationResponse:
    return ProjectIntegrationResponse(
        **attach_project_integration(project_id, current_user["id"], payload.model_dump())
    )


@router.delete("/project-integrations/{binding_id}", status_code=204)
async def remove_project_integration_endpoint(
    binding_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    remove_project_integration(binding_id, current_user["id"])
    return Response(status_code=204)


@router.get("/projects/{project_id}/delivery-dashboard", response_model=ProjectDeliveryDashboardResponse)
async def build_delivery_dashboard_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> ProjectDeliveryDashboardResponse:
    return ProjectDeliveryDashboardResponse(
        **await build_delivery_dashboard(project_id, current_user["id"])
    )


@router.get("/projects/{project_id}/ai/focus", response_model=PersonalRecommendationResponse)
async def get_personal_focus_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> PersonalRecommendationResponse:
    return PersonalRecommendationResponse(
        **build_personal_recommendation(project_id, current_user["id"])
    )


@router.get("/projects/{project_id}/memories", response_model=list[ProjectMemoryEntryResponse])
async def list_memories_endpoint(
    project_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[ProjectMemoryEntryResponse]:
    return [
        ProjectMemoryEntryResponse(**memory)
        for memory in list_memories(project_id, current_user["id"])
    ]


@router.post("/projects/{project_id}/memories", response_model=ProjectMemoryEntryResponse)
async def create_memory_endpoint(
    project_id: int,
    payload: ProjectMemoryEntryRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectMemoryEntryResponse:
    return ProjectMemoryEntryResponse(
        **create_memory_entry(project_id, current_user["id"], payload.model_dump())
    )


@router.post("/projects/{project_id}/meetings", response_model=ProjectMemoryEntryResponse)
async def ingest_meeting_endpoint(
    project_id: int,
    payload: MeetingIngestRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectMemoryEntryResponse:
    return ProjectMemoryEntryResponse(
        **ingest_meeting_note(project_id, current_user["id"], payload.model_dump())
    )
