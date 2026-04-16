"""In-memory user store with optional JSON file persistence. No SQLite needed."""
import json
import os
from datetime import datetime, timezone

_users: dict[str, dict] = {}
_query_history: list[dict] = []
_STORAGE_FILE = "users_data.json"


def init_db(db_path: str = _STORAGE_FILE):
    """Load existing data from JSON file if it exists."""
    global _users, _query_history
    if os.path.exists(db_path):
        with open(db_path) as f:
            data = json.load(f)
            _users = data.get("users", {})
            _query_history = data.get("query_history", [])


def _save(db_path: str = _STORAGE_FILE):
    """Persist current state to JSON file."""
    with open(db_path, "w") as f:
        json.dump({"users": _users, "query_history": _query_history}, f, indent=2, default=str)


def get_user(db_path: str, phone: str) -> dict | None:
    return _users.get(phone)


def upsert_user(db_path: str, phone: str, name: str = None, language: str = "hi",
                state: str = None, occupation: str = None,
                land_acres: float = None, family_size: int = None):
    existing = _users.get(phone, {})
    _users[phone] = {
        "phone": phone,
        "name": name or existing.get("name"),
        "language": language or existing.get("language", "hi"),
        "state": state or existing.get("state"),
        "occupation": occupation or existing.get("occupation"),
        "land_acres": land_acres if land_acres is not None else existing.get("land_acres"),
        "family_size": family_size if family_size is not None else existing.get("family_size"),
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(db_path)


def log_query(db_path: str, phone: str, topic: str, domain: str,
              query_text: str, response_summary: str):
    _query_history.append({
        "phone": phone,
        "topic": topic,
        "domain": domain,
        "query_text": query_text,
        "response_summary": response_summary,
        "resolved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _save(db_path)


def get_recent_queries(db_path: str, phone: str, limit: int = 5) -> list[dict]:
    user_queries = [q for q in _query_history if q["phone"] == phone]
    return sorted(user_queries, key=lambda x: x["created_at"], reverse=True)[:limit]
