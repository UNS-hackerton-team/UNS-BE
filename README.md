# UNS-BE

FastAPI backend for the AI PM Workspace MVP.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger.

## Docker

Create `.env` first:

```bash
cp .env.example .env
```

Run both app and database:

```bash
docker compose up --build
```

Useful commands:

```bash
docker compose up -d postgres
docker compose up --build app
docker compose down
```

When the app runs inside Docker, it connects to PostgreSQL with:

```env
APP_DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/uns
```

From your local machine, direct DB access stays:

```env
APP_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/uns
```

## Main endpoints

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /health`
- Sign up: `POST /api/v1/auth/signup`
- Login: `POST /api/v1/auth/login`
- Current user: `GET /api/v1/auth/me`
- Jira snapshot: `POST /api/v1/work-tracking/jira/snapshot`
- Linear snapshot: `POST /api/v1/work-tracking/linear/snapshot`
- Unified dashboard: `POST /api/v1/work-tracking/dashboard`

## Implemented MVP API areas

- Auth: signup, login, current user
- Workspace: list, create, detail, invite lookup, invite regenerate/deactivate
- Invite: validate and join
- Project: create, list, detail
- Project member profile: create/update/list
- Backlog: list/create/update/delete
- Sprint: create/list/add issues
- Issue: create, status update, assignee update
- AI: task generation, assignment recommendation, assignment confirmation
- Chat: shared AI PM chat, personal AI chat
- Dashboard: issue counts, workload summary, bottleneck text
- External work tracking: Jira sprint/backlog snapshot, Linear cycle/backlog snapshot, unified progress dashboard

## Example auth payloads

Signup:

```json
{
  "name": "Kanghee",
  "email": "kanghee@example.com",
  "password": "password123"
}
```

Login:

```json
{
  "email": "kanghee@example.com",
  "password": "password123"
}
```

Project profile:

```json
{
  "project_role": "BACKEND",
  "tech_stack": ["FastAPI", "SQLite", "JWT"],
  "strong_tasks": ["API", "database", "auth"],
  "disliked_tasks": ["design"],
  "available_hours_per_day": 6,
  "experience_level": "ADVANCED"
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
  api/v1/
  core/
  db/
  schemas/
  services/
docs/
tests/
```

## Notes

- The app uses PostgreSQL via `APP_DATABASE_URL` by default.
- `docker compose up -d postgres` starts a local database on `localhost:55432`.
- SQLite is still supported for tests or lightweight local runs with a URL such as `sqlite:///./uns.db`.
- Passwords are stored as salted PBKDF2 hashes.
- The current AI features are deterministic MVP logic intended for hackathon demos.
- Product and API planning notes live in `docs/ai-pm-workspace-spec.md`.
- Jira uses the official Agile REST API for board, sprint, and backlog data.
- Linear uses its GraphQL API for team, cycle, and issue data.
- The unified dashboard progress API normalizes Jira and Linear items and can group results by source, scope, project, team, assignee, label, or status category.
