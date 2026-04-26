# UNS-BE

FastAPI base project for the UNS backend.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
uvicorn app.main:app --reload
```

Server:

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /health`
- Sign up: `POST /api/v1/auth/signup`
- Login: `POST /api/v1/auth/login`
- Current user: `GET /api/v1/auth/me`
- Jira snapshot: `POST /api/v1/work-tracking/jira/snapshot`
- Linear snapshot: `POST /api/v1/work-tracking/linear/snapshot`
- Dashboard: `POST /api/v1/work-tracking/dashboard`

Example auth body:

```json
{
  "username": "kanghee",
  "password": "admin1234"
}
```

Example dashboard body:

```json
{
  "group_by": "project",
  "include_items": false,
  "jira": {
    "boards": [
      {
        "board_id": 12,
        "sprint_state": "active",
        "include_backlog": true
      }
    ]
  },
  "linear": {
    "teams": [
      {
        "team_id": "your-linear-team-id",
        "include_current_cycle": true,
        "include_backlog": true
      }
    ]
  }
}
```

## Project structure

```text
app/
  api/
  core/
  db/
  schemas/
  services/
tests/
```

## Notes

The auth flow now uses PostgreSQL via `APP_DATABASE_URL`.
For local development, `docker compose up -d postgres` starts a ready-to-use database on `localhost:55432`.
SQLite is still supported for tests or lightweight local runs with a URL such as `sqlite:///./uns.db`.
Passwords are stored as salted PBKDF2 hashes for local development.
Jira uses the official Agile REST API for board, sprint, and backlog data.
Linear uses its GraphQL API for team, cycle, and issue data.
Dashboard progress is calculated from normalized work items and supports grouping by source, scope, project, team, assignee, label, or status category.
