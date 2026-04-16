import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("src.server.handle_function_call", return_value="PM-KISAN: Rs 6000/year")
def test_vapi_function_call_webhook(mock_handler):
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "search_schemes",
                "parameters": {"occupation": "farmer", "query": "income support"}
            },
            "call": {
                "id": "call_test",
                "customer": {"number": "+919876543210"}
            }
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    assert "result" in response.json()
    mock_handler.assert_called_once_with("search_schemes", {
        "occupation": "farmer", "query": "income support", "phone": "+919876543210"
    })


def test_vapi_assistant_request():
    payload = {
        "message": {
            "type": "assistant-request",
            "call": {
                "id": "call_test",
                "customer": {"number": "+919876543210"}
            }
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "assistant" in data
    assert "model" in data["assistant"]


@patch("src.server.log_query")
def test_vapi_end_of_call_report(mock_log):
    payload = {
        "message": {
            "type": "end-of-call-report",
            "summary": "User asked about PM-KISAN scheme eligibility",
            "transcript": "Namaste, mujhe PM-KISAN ke baare mein batao",
            "call": {
                "id": "call_test",
                "customer": {"number": "+919876543210"}
            }
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert call_args.kwargs["domain"] == "scheme"


def test_vapi_unknown_message_type():
    payload = {
        "message": {
            "type": "unknown-event",
            "call": {"id": "call_test"}
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
