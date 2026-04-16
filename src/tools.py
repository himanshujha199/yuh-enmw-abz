"""Tool functions that Vapi calls via function-call webhooks."""
import json
from src.db import get_user, upsert_user, log_query, get_recent_queries
from src.qdrant_client import search_collection, filter_and_search_schemes
from src.config import USER_DATA_PATH


def handle_function_call(function_name: str, parameters: dict) -> str:
    """Dispatch a Vapi function call to the appropriate handler. Returns a string result."""
    handlers = {
        "search_schemes": _search_schemes,
        "search_health": _search_health,
        "search_services": _search_services,
        "get_user_profile": _get_user_profile,
        "save_user_profile": _save_user_profile,
    }
    handler = handlers.get(function_name)
    if not handler:
        return f"Unknown function: {function_name}"
    return handler(parameters)


def _search_schemes(params: dict) -> str:
    results = filter_and_search_schemes(
        query_text=params.get("query", "government scheme"),
        occupation=params.get("occupation"),
        land_acres=params.get("land_acres"),
        state=params.get("state"),
        limit=3,
    )
    if not results:
        return "No matching schemes found for your profile. Please provide more details about your occupation and location."

    lines = []
    for i, r in enumerate(results, 1):
        docs = ", ".join(r.get("documents_required", []))
        lines.append(
            f"{i}. {r['name']}: {r.get('benefits', 'N/A')}. "
            f"How to apply: {r.get('how_to_apply', 'N/A')}. "
            f"Documents needed: {docs}. "
            f"Helpline: {r.get('helpline', 'N/A')}."
        )
    return "Matching government schemes:\n" + "\n".join(lines)


def _search_health(params: dict) -> str:
    query = params.get("query", params.get("symptoms", "health issue"))
    results = search_collection("health", query, limit=2)
    if not results:
        return "I could not find specific guidance. Please call ambulance at 108 or visit nearest hospital."

    r = results[0]
    questions = "\n".join(f"- {q}" for q in r.get("severity_questions", []))
    return (
        f"Health guidance for: {r.get('description', r['id'])}\n\n"
        f"To assess severity, I need to ask:\n{questions}\n\n"
        f"For mild cases: {r.get('action_mild', 'N/A')}\n\n"
        f"Seek immediate medical help if: {r.get('action_severe', 'N/A')}\n\n"
        f"IMPORTANT: {r.get('disclaimer', 'Please consult a doctor.')}"
    )


def _search_services(params: dict) -> str:
    query = params.get("query", "emergency helpline")
    results = search_collection("services", query, limit=3)
    if not results:
        return "For emergencies call 112 (police) or 108 (ambulance)."

    lines = [f"- {r['name']}: {r.get('phone', 'N/A')} — {r.get('description', '')[:100]}" for r in results]
    return "Available services:\n" + "\n".join(lines)


def _get_user_profile(params: dict) -> str:
    phone = params.get("phone", "")
    user = get_user(USER_DATA_PATH, phone)
    if not user:
        return json.dumps({"new_user": True, "phone": phone})

    recent = get_recent_queries(USER_DATA_PATH, phone, limit=3)
    user_data = {k: v for k, v in user.items() if v is not None}
    user_data["recent_queries"] = [
        {"topic": q["topic"], "domain": q["domain"], "date": q["created_at"]}
        for q in recent
    ]
    return json.dumps(user_data)


def _save_user_profile(params: dict) -> str:
    phone = params.get("phone")
    if not phone:
        return "Error: phone number is required"

    upsert_user(
        db_path=USER_DATA_PATH,
        phone=phone,
        name=params.get("name"),
        language=params.get("language", "hi"),
        state=params.get("state"),
        occupation=params.get("occupation"),
        land_acres=params.get("land_acres"),
        family_size=params.get("family_size"),
    )
    return f"Profile saved successfully for {params.get('name', phone)}"
