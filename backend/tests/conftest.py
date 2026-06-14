"""Test fixtures. Runs against the local dev DB; truncates between tests."""

import warnings

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings

warnings.filterwarnings("ignore")

settings = get_settings()
# Sync engine (psycopg) as the table owner for fast truncation between tests.
_admin = create_engine(
    settings.database_url_migrate
    or settings.database_url.replace("+asyncpg", "+psycopg")
)

_TABLES = (
    "users, groups, group_members, preferences, plans, plan_attendees, "
    "options, votes, outcomes, executions"
)


@pytest.fixture(autouse=True)
def _clean_db():
    with _admin.begin() as conn:
        conn.execute(text(f"TRUNCATE {_TABLES} CASCADE"))
    yield


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def login(client):
    def _login(email: str) -> dict[str, str]:
        tok = client.post("/auth/magic-link", json={"email": email}).json()["dev_magic_token"]
        access = client.post("/auth/verify", json={"token": tok}).json()["access_token"]
        return {"Authorization": f"Bearer {access}"}

    return _login
