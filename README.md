# UNS-BE

FastAPI backend for the AI PM Workspace MVP.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger.

## Implemented MVP API areas

- Auth: signup, login, current user
- Workspace: create, detail, invite lookup, invite regenerate/deactivate
- Invite: validate and join
- Project: create, list, detail
- Project member profile: create/update/list
- Backlog: list/create/update/delete
- Sprint: create/list/add issues
- Issue: create, status update, assignee update
- AI: task generation, assignment recommendation, assignment confirmation
- Chat: shared AI PM chat, personal AI chat
- Dashboard: issue counts, workload summary, bottleneck text

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

- The app uses SQLite configured by `APP_DATABASE_PATH`.
- Passwords are stored as salted PBKDF2 hashes.
- The current AI features are deterministic MVP logic intended for hackathon demos.
- Product and API planning notes live in `docs/ai-pm-workspace-spec.md`.
