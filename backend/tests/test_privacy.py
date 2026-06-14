"""Privacy invariant tests (docs/privacy.md). These are the differentiator —
if any of these regress, the product promise is broken.
"""

import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings

settings = get_settings()


@pytest.fixture
def group_with_two(client, login):
    """Alice (owner) + Bob (member), both with private prefs set."""
    alice, bob = login("alice@example.com"), login("bob@example.com")
    gid = client.post("/groups", json={"name": "Crew"}, headers=alice).json()["id"]
    inv = client.post(f"/groups/{gid}/invite", headers=alice).json()
    client.post("/groups/join", json={"token": inv["token"]}, headers=bob)
    client.put(
        f"/groups/{gid}/preferences/me",
        json={"visibility": "private", "diet": ["vegetarian"], "budget_max": 30},
        headers=alice,
    )
    client.put(
        f"/groups/{gid}/preferences/me",
        json={"visibility": "private", "diet": ["vegan"], "budget_max": 25},
        headers=bob,
    )
    return gid, alice, bob


def test_member_only_reads_own_preferences(group_with_two, client):
    gid, alice, bob = group_with_two
    assert client.get(f"/groups/{gid}/preferences/me", headers=alice).json()["budget_max"] == 30
    assert client.get(f"/groups/{gid}/preferences/me", headers=bob).json()["budget_max"] == 25


def test_status_reveals_existence_not_content(group_with_two, client):
    gid, alice, _bob = group_with_two
    st = client.get(f"/groups/{gid}/preferences/status", headers=alice).json()
    assert st["ready"] == 2 and st["total"] == 2
    # No preference content fields leak through the readiness endpoint.
    blob = str(st).lower()
    for leak in ("budget", "vegetarian", "vegan", "diet", "hard_no"):
        assert leak not in blob


def test_non_member_cannot_see_group(client, login):
    alice, mallory = login("alice@example.com"), login("mallory@example.com")
    gid = client.post("/groups", json={"name": "Private"}, headers=alice).json()["id"]
    assert client.get(f"/groups/{gid}", headers=mallory).status_code == 404
    assert client.get(f"/groups/{gid}/preferences/status", headers=mallory).status_code == 404
    assert len(client.get("/groups", headers=mallory).json()) == 0


def test_rls_blocks_cross_user_preference_read_at_db(group_with_two):
    """DB-layer proof: as the RLS-subject app role acting as Bob, a direct query
    for Alice's preferences returns zero rows — even bypassing the API."""
    gid, _alice, _bob = group_with_two
    app_url = settings.database_url.replace("+asyncpg", "+psycopg")
    admin_url = settings.database_url_migrate or app_url
    admin = create_engine(admin_url)
    with admin.connect() as c:
        alice_id = c.execute(
            text("SELECT id FROM users WHERE email='alice@example.com'")
        ).scalar()
        bob_id = c.execute(
            text("SELECT id FROM users WHERE email='bob@example.com'")
        ).scalar()

    app_engine = create_engine(app_url)
    with app_engine.connect() as c:
        c.execute(text("SELECT set_config('app.current_user_id', :u, false)"), {"u": str(bob_id)})
        # Bob can see his own
        own = c.execute(text("SELECT count(*) FROM preferences WHERE user_id = :u"), {"u": str(bob_id)}).scalar()
        # Bob cannot see Alice's
        others = c.execute(text("SELECT count(*) FROM preferences WHERE user_id = :u"), {"u": str(alice_id)}).scalar()
    assert own == 1
    assert others == 0


def test_rls_fail_closed_without_identity():
    """With no app.current_user_id set, the app role sees zero group-scoped rows."""
    app_url = settings.database_url.replace("+asyncpg", "+psycopg")
    eng = create_engine(app_url)
    with eng.connect() as c:
        assert c.execute(text("SELECT count(*) FROM preferences")).scalar() == 0
        assert c.execute(text("SELECT count(*) FROM groups")).scalar() == 0
