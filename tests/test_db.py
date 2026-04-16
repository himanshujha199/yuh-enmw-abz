import os
import json
import pytest
from src.db import init_db, get_user, upsert_user, log_query, get_recent_queries

TEST_DB = "test_users_data.json"


@pytest.fixture(autouse=True)
def setup_teardown():
    # Reset in-memory state
    import src.db as db_module
    db_module._users = {}
    db_module._query_history = []
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_upsert_and_get_new_user():
    upsert_user(
        db_path=TEST_DB,
        phone="+919876543210",
        name="Sunita",
        language="hi",
        state="Madhya Pradesh",
        occupation="farmer_family",
        land_acres=3.0,
        family_size=5,
    )
    user = get_user(TEST_DB, "+919876543210")
    assert user is not None
    assert user["name"] == "Sunita"
    assert user["state"] == "Madhya Pradesh"
    assert user["land_acres"] == 3.0


def test_get_nonexistent_user():
    user = get_user(TEST_DB, "+910000000000")
    assert user is None


def test_upsert_updates_existing_user():
    upsert_user(TEST_DB, phone="+919876543210", name="Sunita", language="hi")
    upsert_user(TEST_DB, phone="+919876543210", name="Sunita Devi", language="hi")
    user = get_user(TEST_DB, "+919876543210")
    assert user["name"] == "Sunita Devi"


def test_log_and_get_queries():
    upsert_user(TEST_DB, phone="+919876543210", name="Sunita", language="hi")
    log_query(
        db_path=TEST_DB,
        phone="+919876543210",
        topic="PM-KISAN",
        domain="scheme",
        query_text="kisan yojana ke baare mein batao",
        response_summary="PM-KISAN: Rs 6000/year",
    )
    log_query(
        db_path=TEST_DB,
        phone="+919876543210",
        topic="child-fever",
        domain="health",
        query_text="bachche ko bukhar hai",
        response_summary="Paracetamol 10-15mg/kg",
    )
    queries = get_recent_queries(TEST_DB, "+919876543210", limit=5)
    assert len(queries) == 2
    assert queries[0]["topic"] == "child-fever"  # Most recent first


def test_persistence():
    """Test that data persists to JSON file."""
    upsert_user(TEST_DB, phone="+919876543210", name="Sunita", language="hi")
    assert os.path.exists(TEST_DB)
    with open(TEST_DB) as f:
        data = json.load(f)
    assert "+919876543210" in data["users"]
