"""FastAPI server — Vapi webhook endpoint."""
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.tools import handle_function_call
from src.db import init_db, log_query
from src.config import USER_DATA_PATH

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
]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gram-sahayak"}


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
