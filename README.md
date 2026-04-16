# Gram Sahayak — Voice AI Village Assistant

A multilingual voice AI assistant that helps rural Indian citizens access government welfare schemes, basic healthcare guidance, and emergency services through a simple phone call in Hindi.

**Hackathon Project** — PS3: Voice AI Agent for Accessibility & Societal Impact  
**Stack**: Vapi + Qdrant + FastAPI + GPT-4o-mini

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your API keys (Vapi, Qdrant Cloud, OpenAI)

# 2. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Ingest knowledge base into Qdrant
python scripts/ingest.py

# 4. Start the server
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload

# 5. Expose to internet (in another terminal)
ngrok http 8000

# 6. Configure Vapi
# Set your Vapi assistant's Server URL to: https://<ngrok-url>/vapi/webhook

# 7. Call the Vapi phone number and speak in Hindi!
```

## Run Tests

```bash
python -m pytest tests/ -v
```

## Demo Script

**Scenario**: Sunita, a farmer's wife from Madhya Pradesh, calls about her sick child and government schemes.

1. *"Namaste, mera naam Sunita hai, Madhya Pradesh se hoon"*
2. *"Mere bachche ko bukhar hai do din se"* → health guidance with paracetamol dosage
3. *"Humaare paas 3 acre zameen hai, koi sarkari yojana hai?"* → PM-KISAN, Fasal Bima matched
4. Hang up. Call again → agent remembers Sunita and follows up

## Architecture

```
Phone Call → Vapi (STT/TTS) → FastAPI (webhook) → Qdrant (semantic search)
                                                 → JSON store (user memory)
```

## Knowledge Base

| Collection | Count | Description |
|-----------|-------|-------------|
| schemes | 20 | Government welfare schemes (PM-KISAN, Ayushman Bharat, etc.) |
| health | 15 | First-aid protocols (fever, snake bite, burns, etc.) |
| services | 20 | Helplines and emergency services (108, 112, 181, etc.) |

## Project Structure

```
gram-sahayak/
├── data/           # JSON knowledge base files
├── scripts/        # Ingestion and retrieval test scripts
├── src/            # Application code
│   ├── config.py   # Environment config
│   ├── db.py       # In-memory user store (JSON persistence)
│   ├── embeddings.py  # Multilingual embedding wrapper
│   ├── qdrant_client.py  # Qdrant search helpers
│   ├── tools.py    # Vapi tool functions
│   └── server.py   # FastAPI webhook server
├── tests/          # Pytest test suite
└── vapi/           # Vapi assistant config reference
```
