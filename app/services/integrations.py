from __future__ import annotations

import asyncio
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.db.database import execute, fetch_all, fetch_one
from app.schemas.project_hub import IntegrationCatalogItemResponse
from app.schemas.work_tracking import JiraBoardScopeRequest, LinearTeamScopeRequest, WorkScopeSnapshot
from app.services.project import get_project, require_project_pm
from app.services.work_tracking import JiraClient, LinearClient
from app.services.workspace import require_workspace_member


def list_workspace_integrations(workspace_id: int, user_id: int) -> list[dict]:
    require_workspace_member(workspace_id, user_id)
    rows = fetch_all(
        """
        SELECT *
        FROM workspace_integrations
        WHERE workspace_id = ?
        ORDER BY provider ASC, external_workspace_name ASC, id ASC
        """,
        (workspace_id,),
    )
    return [dict(row) for row in rows]


def list_project_integrations(project_id: int, user_id: int) -> list[dict]:
    project = get_project(project_id, user_id)
    rows = fetch_all(
        """
        SELECT pi.*
        FROM project_integrations pi
        JOIN workspace_integrations wi ON wi.id = pi.workspace_integration_id
        WHERE pi.project_id = ? AND wi.workspace_id = ?
        ORDER BY pi.provider ASC, pi.scope_name ASC, pi.id ASC
        """,
        (project_id, project["workspace_id"]),
    )
    return [_serialize_project_integration(dict(row)) for row in rows]


def build_connect_url(
    workspace_id: int,
    user: dict,
    provider: str,
    *,
    redirect_to: str | None = None,
) -> dict:
    require_workspace_member(workspace_id, user["id"])
    settings = get_settings()
    normalized_provider = provider.lower()
    state = secrets.token_urlsafe(32)

    if normalized_provider == "jira":
        if not settings.jira_oauth_client_id or not settings.jira_oauth_client_secret:
            return {
                "provider": "jira",
                "configured": False,
                "message": "Jira OAuth client credentials are not configured",
            }
        params = {
            "audience": "api.atlassian.com",
            "client_id": settings.jira_oauth_client_id,
            "scope": settings.jira_oauth_scopes,
            "redirect_uri": settings.jira_oauth_redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        authorization_url = f"https://auth.atlassian.com/authorize?{urlencode(params)}"
    elif normalized_provider == "linear":
        if not settings.linear_oauth_client_id or not settings.linear_oauth_client_secret:
            return {
                "provider": "linear",
                "configured": False,
                "message": "Linear OAuth client credentials are not configured",
            }
        params = {
            "client_id": settings.linear_oauth_client_id,
            "redirect_uri": settings.linear_oauth_redirect_uri,
            "response_type": "code",
            "scope": settings.linear_oauth_scopes,
            "state": state,
            "prompt": "consent",
        }
        authorization_url = f"https://linear.app/oauth/authorize?{urlencode(params)}"
    else:
        raise HTTPException(status_code=404, detail="Unsupported integration provider")

    execute(
        """
        INSERT INTO oauth_states (workspace_id, provider, state, created_by, redirect_to)
        VALUES (?, ?, ?, ?, ?)
        """,
        (workspace_id, normalized_provider, state, user["id"], _sanitize_redirect_target(redirect_to)),
    )
    return {
        "provider": normalized_provider,
        "configured": True,
        "authorization_url": authorization_url,
        "message": None,
    }


async def handle_oauth_callback(provider: str, code: str, state: str) -> str:
    state_row = fetch_one(
        """
        SELECT *
        FROM oauth_states
        WHERE state = ? AND provider = ?
        """,
        (state, provider.lower()),
    )
    if state_row is None:
        raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")

    settings = get_settings()
    redirect_to = state_row["redirect_to"] or f"{settings.normalized_frontend_url}/dashboard"

    try:
        if provider.lower() == "jira":
            connected_count = await _connect_jira(state_row, code)
        elif provider.lower() == "linear":
            connected_count = await _connect_linear(state_row, code)
        else:
            raise HTTPException(status_code=404, detail="Unsupported integration provider")
    finally:
        execute("DELETE FROM oauth_states WHERE id = ?", (state_row["id"],))

    separator = "&" if "?" in redirect_to else "?"
    return (
        f"{redirect_to}{separator}"
        f"integration={provider.lower()}&status=connected&count={connected_count}"
    )


async def list_integration_catalog(integration_id: int, user_id: int) -> dict:
    integration = _get_workspace_integration(integration_id, user_id)
    if integration["provider"] == "jira":
        token = await _get_access_token(integration)
        async with JiraClient(
            get_settings(),
            oauth_access_token=token,
            oauth_cloud_id=integration["external_workspace_id"],
            browse_base_url=integration.get("external_workspace_url"),
        ) as client:
            boards = await client.fetch_board_catalog()
        return {
            "provider": "jira",
            "items": [
                IntegrationCatalogItemResponse(
                    id=str(board["id"]),
                    name=board.get("name") or f"Board {board['id']}",
                    key=board.get("type"),
                    url=integration.get("external_workspace_url"),
                ).model_dump()
                for board in boards
            ],
        }

    if integration["provider"] == "linear":
        token = await _get_access_token(integration)
        async with LinearClient(get_settings(), access_token=token) as client:
            teams = await client.fetch_team_catalog()
        return {
            "provider": "linear",
            "items": [
                IntegrationCatalogItemResponse(
                    id=str(team["id"]),
                    name=team.get("name") or str(team["id"]),
                    key=team.get("key"),
                    url=integration.get("external_workspace_url"),
                ).model_dump()
                for team in teams
            ],
        }

    raise HTTPException(status_code=404, detail="Unsupported integration provider")


def attach_project_integration(project_id: int, user_id: int, payload: dict) -> dict:
    require_project_pm(project_id, user_id)
    project = get_project(project_id, user_id)
    workspace_integration = fetch_one(
        """
        SELECT *
        FROM workspace_integrations
        WHERE id = ? AND workspace_id = ?
        """,
        (payload["workspace_integration_id"], project["workspace_id"]),
    )
    if workspace_integration is None:
        raise HTTPException(status_code=404, detail="Workspace integration not found")

    existing = fetch_one(
        """
        SELECT id
        FROM project_integrations
        WHERE project_id = ? AND provider = ? AND scope_id = ?
        """,
        (project_id, workspace_integration["provider"], payload["scope_id"]),
    )
    settings_json = json.dumps(payload.get("settings") or {})
    if existing is None:
        binding_id = execute(
            """
            INSERT INTO project_integrations (
                project_id, workspace_integration_id, provider, scope_type,
                scope_id, scope_name, settings
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                workspace_integration["id"],
                workspace_integration["provider"],
                payload["scope_type"],
                payload["scope_id"],
                payload["scope_name"],
                settings_json,
            ),
        )
    else:
        binding_id = existing["id"]
        execute(
            """
            UPDATE project_integrations
            SET workspace_integration_id = ?, scope_type = ?, scope_name = ?, settings = ?, is_active = TRUE
            WHERE id = ?
            """,
            (
                workspace_integration["id"],
                payload["scope_type"],
                payload["scope_name"],
                settings_json,
                binding_id,
            ),
        )

    row = fetch_one("SELECT * FROM project_integrations WHERE id = ?", (binding_id,))
    return _serialize_project_integration(dict(row))


def remove_project_integration(binding_id: int, user_id: int) -> None:
    row = fetch_one(
        """
        SELECT pi.*, p.workspace_id
        FROM project_integrations pi
        JOIN projects p ON p.id = pi.project_id
        JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = ?
        WHERE pi.id = ?
        """,
        (user_id, binding_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Project integration not found")
    require_project_pm(row["project_id"], user_id)
    execute("DELETE FROM project_integrations WHERE id = ?", (binding_id,))


async def fetch_project_delivery_scopes(project_id: int, user_id: int) -> tuple[list[WorkScopeSnapshot], list[str]]:
    get_project(project_id, user_id)
    rows = fetch_all(
        """
        SELECT pi.*, wi.external_workspace_id, wi.external_workspace_url, wi.access_token,
               wi.refresh_token, wi.token_expires_at, wi.scope, wi.status
        FROM project_integrations pi
        JOIN workspace_integrations wi ON wi.id = pi.workspace_integration_id
        WHERE pi.project_id = ? AND pi.is_active = TRUE
        ORDER BY pi.id ASC
        """,
        (project_id,),
    )
    if not rows:
        return [], []

    scopes: list[WorkScopeSnapshot] = []
    warnings: list[str] = []
    for row in rows:
        binding = _serialize_project_integration(dict(row))
        try:
            scope = await _fetch_scope_from_binding(binding, row)
            scopes.append(scope)
        except HTTPException as exc:
            warnings.append(f"{binding['provider']} {binding['scope_name']}: {exc.detail}")
        except Exception as exc:
            warnings.append(f"{binding['provider']} {binding['scope_name']}: {exc}")
    return scopes, warnings


async def _fetch_scope_from_binding(binding: dict, raw_row: dict) -> WorkScopeSnapshot:
    settings = get_settings()
    binding_settings = binding["settings"]
    if binding["provider"] == "jira":
        token = await _get_access_token(dict(raw_row))
        board_request = JiraBoardScopeRequest(
            board_id=int(binding["scope_id"]),
            sprint_state=binding_settings.get("sprint_state", "active"),
            sprint_limit=int(binding_settings.get("sprint_limit", 1)),
            sprint_issue_limit=int(binding_settings.get("sprint_issue_limit", 100)),
            backlog_limit=int(binding_settings.get("backlog_limit", 100)),
            include_sprints=bool(binding_settings.get("include_sprints", True)),
            include_backlog=bool(binding_settings.get("include_backlog", True)),
        )
        async with JiraClient(
            settings,
            oauth_access_token=token,
            oauth_cloud_id=raw_row["external_workspace_id"],
            browse_base_url=raw_row.get("external_workspace_url"),
        ) as client:
            return await client.fetch_board_snapshot(board_request)

    if binding["provider"] == "linear":
        token = await _get_access_token(dict(raw_row))
        if binding["scope_type"].lower() == "team_key":
            request = LinearTeamScopeRequest(
                team_key=binding["scope_id"],
                issue_limit=int(binding_settings.get("issue_limit", 250)),
                cycle_limit=int(binding_settings.get("cycle_limit", 6)),
                include_current_cycle=bool(binding_settings.get("include_current_cycle", True)),
                include_backlog=bool(binding_settings.get("include_backlog", True)),
            )
        else:
            request = LinearTeamScopeRequest(
                team_id=binding["scope_id"],
                issue_limit=int(binding_settings.get("issue_limit", 250)),
                cycle_limit=int(binding_settings.get("cycle_limit", 6)),
                include_current_cycle=bool(binding_settings.get("include_current_cycle", True)),
                include_backlog=bool(binding_settings.get("include_backlog", True)),
            )
        async with LinearClient(settings, access_token=token) as client:
            return await client.fetch_team_snapshot(request)

    raise HTTPException(status_code=404, detail="Unsupported integration provider")


async def _connect_jira(state_row: dict, code: str) -> int:
    settings = get_settings()
    token_payload = await _exchange_jira_code(code)
    access_token = token_payload["access_token"]
    refresh_token = token_payload.get("refresh_token")
    expires_at = _expires_at(token_payload.get("expires_in"))
    scope = token_payload.get("scope")

    async with httpx.AsyncClient(timeout=settings.jira_timeout_seconds) as client:
        response = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira accessible resources failed: {response.text}",
        )

    resources = response.json()
    if not resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jira returned no accessible resources for this authorization",
        )

    connected_count = 0
    for resource in resources:
        external_id = str(resource.get("id") or "")
        if not external_id:
            continue
        _upsert_workspace_integration(
            workspace_id=state_row["workspace_id"],
            provider="jira",
            external_workspace_id=external_id,
            external_workspace_name=resource.get("name") or external_id,
            external_workspace_url=resource.get("url"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            scope=scope,
            connected_by=state_row.get("created_by"),
        )
        connected_count += 1
    return connected_count


async def _connect_linear(state_row: dict, code: str) -> int:
    token_payload = await _exchange_linear_code(code)
    access_token = token_payload["access_token"]
    refresh_token = token_payload.get("refresh_token")
    expires_at = _expires_at(token_payload.get("expires_in"))
    scope = token_payload.get("scope")

    async with LinearClient(get_settings(), access_token=access_token) as client:
        workspace = await client.fetch_viewer_workspace()

    external_workspace_id = str(workspace.get("id") or "viewer")
    external_workspace_name = workspace.get("name") or "Linear workspace"
    url_key = workspace.get("urlKey")
    external_workspace_url = f"https://linear.app/{url_key}" if url_key else "https://linear.app"
    _upsert_workspace_integration(
        workspace_id=state_row["workspace_id"],
        provider="linear",
        external_workspace_id=external_workspace_id,
        external_workspace_name=external_workspace_name,
        external_workspace_url=external_workspace_url,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=expires_at,
        scope=scope,
        connected_by=state_row.get("created_by"),
    )
    return 1


async def _exchange_jira_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.jira_oauth_client_id or not settings.jira_oauth_client_secret:
        raise HTTPException(status_code=400, detail="Jira OAuth is not configured")

    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.jira_oauth_client_id,
        "client_secret": settings.jira_oauth_client_secret,
        "code": code,
        "redirect_uri": settings.jira_oauth_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=settings.jira_timeout_seconds) as client:
        response = await client.post(
            "https://auth.atlassian.com/oauth/token",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira token exchange failed: {response.text}",
        )
    return response.json()


async def _exchange_linear_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.linear_oauth_client_id or not settings.linear_oauth_client_secret:
        raise HTTPException(status_code=400, detail="Linear OAuth is not configured")

    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.linear_oauth_client_id,
        "client_secret": settings.linear_oauth_client_secret,
        "code": code,
        "redirect_uri": settings.linear_oauth_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=settings.linear_timeout_seconds) as client:
        response = await client.post(
            "https://api.linear.app/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Linear token exchange failed: {response.text}",
        )
    return response.json()


async def _get_access_token(integration: dict) -> str:
    expires_at = integration.get("token_expires_at")
    access_token = integration.get("access_token")
    if access_token and not _is_expired(expires_at):
        return access_token

    refresh_token = integration.get("refresh_token")
    if not refresh_token:
        if access_token:
            return access_token
        raise HTTPException(status_code=400, detail="Integration token is missing")

    if integration["provider"] == "jira":
        refreshed = await _refresh_jira_token(refresh_token)
    elif integration["provider"] == "linear":
        refreshed = await _refresh_linear_token(refresh_token)
    else:
        raise HTTPException(status_code=404, detail="Unsupported integration provider")

    access_token = refreshed["access_token"]
    next_refresh_token = refreshed.get("refresh_token", refresh_token)
    next_expires_at = _expires_at(refreshed.get("expires_in"))
    execute(
        """
        UPDATE workspace_integrations
        SET access_token = ?, refresh_token = ?, token_expires_at = ?, scope = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            access_token,
            next_refresh_token,
            next_expires_at,
            refreshed.get("scope"),
            integration["id"],
        ),
    )
    return access_token


async def _refresh_jira_token(refresh_token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.jira_oauth_client_id or not settings.jira_oauth_client_secret:
        raise HTTPException(status_code=400, detail="Jira OAuth is not configured")

    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.jira_oauth_client_id,
        "client_secret": settings.jira_oauth_client_secret,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=settings.jira_timeout_seconds) as client:
        response = await client.post(
            "https://auth.atlassian.com/oauth/token",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira token refresh failed: {response.text}",
        )
    return response.json()


async def _refresh_linear_token(refresh_token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.linear_oauth_client_id or not settings.linear_oauth_client_secret:
        raise HTTPException(status_code=400, detail="Linear OAuth is not configured")

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.linear_oauth_client_id,
        "client_secret": settings.linear_oauth_client_secret,
    }
    async with httpx.AsyncClient(timeout=settings.linear_timeout_seconds) as client:
        response = await client.post(
            "https://api.linear.app/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Linear token refresh failed: {response.text}",
        )
    return response.json()


def _get_workspace_integration(integration_id: int, user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT wi.*
        FROM workspace_integrations wi
        JOIN workspace_members wm ON wm.workspace_id = wi.workspace_id AND wm.user_id = ?
        WHERE wi.id = ?
        """,
        (user_id, integration_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace integration not found")
    return dict(row)


def _upsert_workspace_integration(
    *,
    workspace_id: int,
    provider: str,
    external_workspace_id: str,
    external_workspace_name: str,
    external_workspace_url: str | None,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: str | None,
    scope: str | None,
    connected_by: int | None,
) -> None:
    existing = fetch_one(
        """
        SELECT id
        FROM workspace_integrations
        WHERE workspace_id = ? AND provider = ? AND external_workspace_id = ?
        """,
        (workspace_id, provider, external_workspace_id),
    )
    if existing is None:
        execute(
            """
            INSERT INTO workspace_integrations (
                workspace_id, provider, external_workspace_id, external_workspace_name,
                external_workspace_url, access_token, refresh_token, token_expires_at,
                scope, status, connected_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONNECTED', ?)
            """,
            (
                workspace_id,
                provider,
                external_workspace_id,
                external_workspace_name,
                external_workspace_url,
                access_token,
                refresh_token,
                token_expires_at,
                scope,
                connected_by,
            ),
        )
        return

    execute(
        """
        UPDATE workspace_integrations
        SET external_workspace_name = ?, external_workspace_url = ?, access_token = ?,
            refresh_token = ?, token_expires_at = ?, scope = ?, status = 'CONNECTED',
            connected_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            external_workspace_name,
            external_workspace_url,
            access_token,
            refresh_token,
            token_expires_at,
            scope,
            connected_by,
            existing["id"],
        ),
    )


def _serialize_project_integration(row: dict) -> dict:
    row["settings"] = _json_loads(row.get("settings"))
    return row


def _json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    return json.loads(value)


def _sanitize_redirect_target(redirect_to: str | None) -> str:
    settings = get_settings()
    if not redirect_to:
        return f"{settings.normalized_frontend_url}/dashboard"

    parsed = urlparse(redirect_to)
    if parsed.scheme and parsed.netloc:
        frontend_origin = urlparse(settings.normalized_frontend_url)
        if parsed.scheme != frontend_origin.scheme or parsed.netloc != frontend_origin.netloc:
            return f"{settings.normalized_frontend_url}/dashboard"
        return redirect_to

    if not redirect_to.startswith("/"):
        return f"{settings.normalized_frontend_url}/dashboard"
    return f"{settings.normalized_frontend_url}{redirect_to}"


def _expires_at(expires_in: Any) -> str | None:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _is_expired(value: str | None) -> bool:
    if not value:
        return False
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return False
    return expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2)
