# UNS-BE

FastAPI base project for the UNS backend.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Server:

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /health`
- Login: `POST /api/v1/auth/login`
- Current user: `GET /api/v1/auth/me`

Example login body:

```json
{
  "email": "admin@example.com",
  "password": "admin1234"
}
```

## Project structure

```text
app/
  api/
  core/
  schemas/
  services/
tests/
```

## Notes

The login flow currently uses demo credentials from `.env`.
Replace `app/services/auth.py` with real database-backed authentication when you wire up users.
