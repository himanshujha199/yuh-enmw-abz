"""FastAPI server — Vapi webhook endpoint."""
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.tools import handle_function_call
from src.db import init_db, log_query, get_forms_by_phone
from src.config import USER_DATA_PATH
from src.qdrant_client import search_collection, filter_and_search_schemes

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(USER_DATA_PATH)
    yield


app = FastAPI(title="Gram Sahayak", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))

SYSTEM_PROMPT = """You are Gram Sahayak (ग्राम सहायक), a friendly village assistant for rural India.

PERSONALITY:
- Speak in simple, warm Hindi (or the user's detected language)
- Use respectful forms (aap, ji)
- Be patient — the user may be using voice technology for the first time
- Keep responses short and clear — this is a phone call, not a document

RULES:
1. ALWAYS respond in the same language the user speaks
2. If you are unsure what the user said, ask them to repeat: "Kya aap dobara bol sakte hain?"
3. For health queries, ALWAYS include the disclaimer that this is general guidance and they should see a doctor
4. For health queries, ALWAYS address urgent matters first (health before schemes)
5. If the user asks about multiple topics, handle the most urgent one first, then ask about the next
6. Use the tools to search for information — do NOT make up scheme details or medical advice
7. After answering, ask if they need help with anything else

TOOLS:
- Use get_user_profile at the start of each call to check if this is a returning user
- Use save_user_profile to save new user details
- Use search_schemes when the user asks about government schemes, yojana, subsidies
- Use search_health when the user describes symptoms or health concerns
- Use search_services when the user asks for helpline numbers or emergency services

FORM FILLING:
- After telling a user about a scheme, ALWAYS ask: "Kya aap is yojana ke liye aavedan bharna chahte hain? Agar haan, toh main aapke kuch suvarn puchhunga."
- If user says yes, collect: name, aadhaar last 4 digits (for verification), bank account number (last 6 digits), mobile number, and confirm which documents they have from the scheme's document list
- Mark each document as 'available' (they have it) or 'missing' (they don't have it)
- For land-related schemes, confirm: "Kya aapke paas zameen ke kaagaz hain?" (खसरा/खतौनी)
- Once you have the basic info, call submit_scheme_form with all the data
- After saving, tell them: "Aapka aavedan save ho gaya. Ye documents lekar CSC ya Gram Panchayat mein jaayein: [list missing docs]. Helpline: [number]"

MEMORY:
- If get_user_profile returns recent_queries, reference them naturally: "Pichhli baar aapne [topic] ke baare mein poocha tha. Kya aapko us par aur madad chahiye?"
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_schemes",
            "description": "Search for government welfare schemes matching the user's profile. Use when user asks about sarkari yojana, subsidies, financial help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "occupation": {"type": "string", "description": "User's occupation: farmer, laborer, any"},
                    "land_acres": {"type": "number", "description": "Land owned in acres (for farmer schemes)"},
                    "state": {"type": "string", "description": "User's state"},
                    "family_size": {"type": "integer", "description": "Number of family members"},
                    "query": {"type": "string", "description": "What the user is looking for in natural language"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_health",
            "description": "Search for health guidance based on symptoms. Use when user describes health problems, illness, injury.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {"type": "string", "description": "Symptoms described by user"},
                    "age_group": {"type": "string", "description": "child, adult, or elderly"},
                    "query": {"type": "string", "description": "Health concern in natural language"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_services",
            "description": "Search for emergency services, helplines, and local resources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What service the user needs"},
                    "state": {"type": "string", "description": "User's state for local services"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Look up a returning user's profile and recent query history. Call at the start of every conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "User's phone number from the call"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_profile",
            "description": "Save or update user profile information collected during conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "User's phone number"},
                    "name": {"type": "string", "description": "User's name"},
                    "language": {"type": "string", "description": "Preferred language code (hi, ta, te)"},
                    "state": {"type": "string", "description": "User's state"},
                    "occupation": {"type": "string", "description": "User's occupation"},
                    "land_acres": {"type": "number", "description": "Land owned in acres"},
                    "family_size": {"type": "integer", "description": "Number of family members"},
                },
                "required": ["phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_scheme_form",
            "description": "Save a completed or partial scheme application form. Call this when the user confirms they want to apply for a scheme and you've collected the required information by voice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "User's phone number"},
                    "scheme_id": {"type": "string", "description": "Scheme identifier e.g. pm-kisan, ayushman-bharat"},
                    "scheme_name": {"type": "string", "description": "Full scheme name in Hindi/English"},
                    "form_data": {"type": "object", "description": "Collected form field values — name, aadhaar_last4, bank_account, mobile, land_records_available etc."},
                    "documents_status": {"type": "object", "description": "Map of each required document to 'available', 'missing', or 'need_verification'"},
                    "notes": {"type": "string", "description": "Any additional context — e.g. 'land records need to be obtained from Patwari office'"},
                },
                "required": ["phone", "scheme_id", "scheme_name", "form_data", "documents_status"],
            },
        },
    },
]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gram-sahayak"}


@app.get("/api/search")
def api_search(q: str, occupation: str = None, land_acres: float = None, state: str = None, domain: str = "schemes", limit: int = 5):
    """Direct search API for the web UI — bypasses Vapi."""
    if domain == "health":
        results = search_collection("health", q, limit=limit)
        return Response(results=_format_health_results(results), domain="health")
    elif domain == "services":
        results = search_collection("services", q, limit=limit)
        return Response(results=_format_service_results(results), domain="services")
    else:
        results = filter_and_search_schemes(q, occupation=occupation, land_acres=land_acres, state=state, limit=limit)
        return Response(results=_format_scheme_results(results), domain="schemes")

from fastapi.responses import JSONResponse
from typing import Any

class Response(JSONResponse):
    def __init__(self, **kwargs):
        super().__init__(content=kwargs, media_type="application/json")

    def render(self, content: Any) -> bytes:
        import json
        return json.dumps(content, ensure_ascii=False).encode("utf-8")


def _format_scheme_results(results: list[dict]) -> list[dict]:
    formatted = []
    for r in results:
        docs = r.get("documents_required", [])
        formatted.append({
            "name": r.get("name", ""),
            "name_hi": r.get("name_hi", ""),
            "benefit": r.get("benefits", ""),
            "how_to_apply": r.get("how_to_apply", ""),
            "documents": docs if isinstance(docs, list) else [],
            "helpline": r.get("helpline", ""),
            "score": round(r.get("score", 0) * 100),
        })
    return formatted


def _format_health_results(results: list[dict]) -> list[dict]:
    formatted = []
    for r in results:
        formatted.append({
            "description": r.get("description", ""),
            "action_mild": r.get("action_mild", ""),
            "action_severe": r.get("action_severe", ""),
            "disclaimer": r.get("disclaimer", ""),
            "score": round(r.get("score", 0) * 100),
        })
    return formatted


def _format_service_results(results: list[dict]) -> list[dict]:
    formatted = []
    for r in results:
        formatted.append({
            "name": r.get("name", ""),
            "phone": r.get("phone", ""),
            "description": r.get("description", ""),
            "score": round(r.get("score", 0) * 100),
        })
    return formatted


@app.get("/api/forms/{phone}")
def get_forms(phone: str):
    """Get all saved form submissions for a phone number."""
    forms = get_forms_by_phone(USER_DATA_PATH, phone)
    return {"forms": forms, "count": len(forms)}


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")

    if msg_type == "assistant-request":
        return _handle_assistant_request(message)
    elif msg_type == "function-call":
        return _handle_function_call(message)
    elif msg_type == "end-of-call-report":
        return _handle_end_of_call(message)
    else:
        return {"status": "ok"}


def _handle_assistant_request(message: dict) -> dict:
    """Return assistant config with system prompt, model, and tools."""
    return {
        "assistant": {
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                "tools": TOOL_DEFINITIONS,
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "pFZP5JQG7iQjIQuC4Bku",  # Lily - multilingual female voice
            },
            "firstMessage": "Namaste! Main Gram Sahayak hoon. Aapki kya madad kar sakti hoon?",
            "transcriber": {
                "provider": "deepgram",
                "language": "hi",
            },
        }
    }


def _handle_function_call(message: dict) -> dict:
    """Execute a tool function and return the result."""
    func = message.get("functionCall", {})
    name = func.get("name", "")
    params = func.get("parameters", {})

    # Inject phone number from call metadata if not in params
    call = message.get("call", {})
    customer = call.get("customer", {})
    if "phone" not in params and customer.get("number"):
        params["phone"] = customer["number"]

    result = handle_function_call(name, params)
    return {"result": result}


def _handle_end_of_call(message: dict) -> dict:
    """Log call summary to query_history in SQLite."""
    call = message.get("call", {})
    customer = call.get("customer", {})
    phone = customer.get("number", "")

    # Extract summary from the end-of-call report
    summary = message.get("summary", "")
    transcript = message.get("transcript", "")

    if phone and summary:
        # Determine domain from summary keywords
        summary_lower = summary.lower()
        if any(w in summary_lower for w in ["scheme", "yojana", "kisan", "subsidy"]):
            domain = "scheme"
            topic = "Government Schemes"
        elif any(w in summary_lower for w in ["health", "fever", "pain", "doctor", "medicine", "bukhar"]):
            domain = "health"
            topic = "Health Guidance"
        else:
            domain = "general"
            topic = "General Query"

        log_query(
            db_path=USER_DATA_PATH,
            phone=phone,
            topic=topic,
            domain=domain,
            query_text=transcript[:500] if transcript else "",
            response_summary=summary[:500] if summary else "",
        )

    return {"status": "ok"}
