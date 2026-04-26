# UNS-BE

FastAPI backend for the UNS workspace dashboard. The current build includes:

- workspace and project bootstrap
- PM ownership transfer
- project AI prompt and memory storage
- Jira / Linear OAuth connection scaffolding
- project-level BE / FE / DE domain mapping
- delivery dashboard aggregation
- team and personal AI chat over WebSocket
- optional Gemini-backed AI replies via environment variables

## Local development

1. Copy [`.env.example`](/C:/git/UNS-BE/.env.example) to `.env`
2. Fill in any optional keys you want to use
3. Start the stack

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:55432`

## Key environment variables

Core:

- `APP_DATABASE_URL`
- `APP_PUBLIC_BASE_URL`
- `APP_FRONTEND_URL`
- `APP_CORS_ORIGINS`

Gemini:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`

Jira OAuth:

- `JIRA_OAUTH_CLIENT_ID`
- `JIRA_OAUTH_CLIENT_SECRET`
- `JIRA_OAUTH_SCOPES`

Linear OAuth:

- `LINEAR_OAUTH_CLIENT_ID`
- `LINEAR_OAUTH_CLIENT_SECRET`
- `LINEAR_OAUTH_SCOPES`

Legacy direct snapshot support is still available through:

- `JIRA_BASE_URL`
- `JIRA_API_TOKEN`
- `LINEAR_API_KEY`

## Tests

```bash
python -m pytest -q tests -p no:cacheprovider
```
