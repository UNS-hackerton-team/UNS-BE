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
- Sign up: `POST /api/v1/auth/signup`
- Login: `POST /api/v1/auth/login`
- Current user: `GET /api/v1/auth/me`

Example auth body:

```json
{
  "username": "kanghee",
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

The auth flow now uses a local SQLite database file configured by `APP_DATABASE_PATH`.
Passwords are stored as salted PBKDF2 hashes for local development.
