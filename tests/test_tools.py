import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.tools import handle_function_call
from src.db import init_db

TEST_DB = "test_tools_data.json"


@pytest.fixture(autouse=True)
def setup_teardown():
    import src.db as db_module
    db_module._users = {}
    db_module._query_history = []
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@patch("src.tools.USER_DATA_PATH", TEST_DB)
def test_get_user_profile_new_user():
    result = handle_function_call("get_user_profile", {"phone": "+919999999999"})
    parsed = json.loads(result)
    assert parsed["new_user"] is True
    assert parsed["phone"] == "+919999999999"


@patch("src.tools.USER_DATA_PATH", TEST_DB)
def test_save_user_profile():
    result = handle_function_call("save_user_profile", {
        "phone": "+919999999999",
        "name": "Test",
        "language": "hi",
        "state": "UP",
        "occupation": "farmer",
    })
    assert "saved" in result.lower() or "success" in result.lower()


@patch("src.tools.filter_and_search_schemes")
def test_search_schemes(mock_search):
    mock_search.return_value = [
        {"name": "PM-KISAN", "benefits": "Rs 6000/year", "score": 0.9,
         "how_to_apply": "Visit CSC", "documents_required": ["Aadhaar"], "helpline": "155261"}
    ]
    result = handle_function_call("search_schemes", {
        "occupation": "farmer",
        "land_acres": 2,
        "query": "income support",
    })
    assert "PM-KISAN" in result


@patch("src.tools.search_collection")
def test_search_health(mock_search):
    mock_search.return_value = [
        {"id": "child-fever", "description": "Fever in children",
         "action_mild": "Give paracetamol", "action_severe": "Go to hospital",
         "severity_questions": ["How many days?"], "disclaimer": "Consult doctor", "score": 0.9}
    ]
    result = handle_function_call("search_health", {
        "symptoms": "fever",
        "query": "child has fever",
    })
    assert "paracetamol" in result.lower() or "fever" in result.lower()


@patch("src.tools.search_collection")
def test_search_services(mock_search):
    mock_search.return_value = [
        {"name": "National Ambulance", "phone": "108",
         "description": "Emergency ambulance service", "score": 0.9}
    ]
    result = handle_function_call("search_services", {"query": "ambulance"})
    assert "108" in result
    assert "Ambulance" in result


def test_unknown_function():
    result = handle_function_call("nonexistent_function", {})
    assert "unknown" in result.lower() or "Unknown" in result
