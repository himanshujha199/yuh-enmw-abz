import os
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "users_data.json")

QDRANT_COLLECTION_SCHEMES = "schemes"
QDRANT_COLLECTION_HEALTH = "health"
QDRANT_COLLECTION_SERVICES = "services"
EMBEDDING_DIMENSION = 384
