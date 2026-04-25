"""In-memory user store with optional JSON file persistence. No SQLite needed."""
import json
import os
import uuid
from datetime import datetime, timezone

_users: dict[str, dict] = {}
_query_history: list[dict] = []
_form_submissions: list[dict] = []
_STORAGE_FILE = "users_data.json"


def init_db(db_path: str = _STORAGE_FILE):
    """Load existing data from JSON file if it exists."""
    global _users, _query_history, _form_submissions
    if os.path.exists(db_path):
        with open(db_path) as f:
            data = json.load(f)
            _users = data.get("users", {})
            _query_history = data.get("query_history", [])
            _form_submissions = data.get("form_submissions", [])


def _save(db_path: str = _STORAGE_FILE):
    """Persist current state to JSON file."""
    with open(db_path, "w") as f:
        json.dump({"users": _users, "query_history": _query_history, "form_submissions": _form_submissions}, f, indent=2, default=str)


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


def upsert_form_submission(
    db_path: str,
    phone: str,
    scheme_id: str,
    scheme_name: str,
    form_data: dict,
    documents_status: dict,
    notes: str = "",
) -> dict:
    """Save or update a scheme form submission. Only one pending form per scheme per phone."""
    existing = next(
        (f for f in _form_submissions
         if f["phone"] == phone and f["scheme_id"] == scheme_id and f["status"] == "pending"),
        None,
    )
    entry = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "phone": phone,
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "status": "pending",
        "form_data": form_data,
        "documents_status": documents_status,
        "notes": notes,
        "created_at": existing["created_at"] if existing else datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        _form_submissions[_form_submissions.index(existing)] = entry
    else:
        _form_submissions.append(entry)
    _save(db_path)
    return entry


def get_forms_by_phone(db_path: str, phone: str) -> list[dict]:
    return [f for f in _form_submissions if f["phone"] == phone]
