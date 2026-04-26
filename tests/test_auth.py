import os

from fastapi.testclient import TestClient

os.environ["APP_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.core.config import get_settings
from app.db.database import reset_db_state
from app.main import app


get_settings.cache_clear()


def _reset_database() -> None:
    reset_db_state()


def test_health_check() -> None:
    _reset_database()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_and_login_success() -> None:
    _reset_database()
    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v1/auth/signup",
            json={"username": "kanghee", "password": "admin1234"},
        )
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "kanghee", "password": "admin1234"},
        )

    assert signup_response.status_code == 201
    data = login_response.json()
    assert login_response.status_code == 200
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "kanghee"


def test_signup_duplicate_username() -> None:
    _reset_database()
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/signup",
            json={"username": "kanghee", "password": "admin1234"},
        )
        response = client.post(
            "/api/v1/auth/signup",
            json={"username": "kanghee", "password": "another1234"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


def test_login_failure() -> None:
    _reset_database()
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/signup",
            json={"username": "kanghee", "password": "admin1234"},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "kanghee", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_me_returns_current_user() -> None:
    _reset_database()
    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v1/auth/signup",
            json={"username": "kanghee", "password": "admin1234"},
        )
        access_token = signup_response.json()["access_token"]
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"username": "kanghee"}
