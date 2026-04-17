from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, Range
from src.config import QDRANT_URL, QDRANT_API_KEY
from src.embeddings import get_embedding

_client = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client


def search_collection(
    collection_name: str,
    query_text: str,
    limit: int = 3,
    query_filter: Filter = None,
) -> list[dict]:
    client = _get_client()
    query_vector = get_embedding(query_text)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    )

    return [
        {**point.payload, "score": point.score}
        for point in results.points
    ]


def filter_and_search_schemes(
    query_text: str,
    occupation: str = None,
    land_acres: float = None,
    state: str = None,
    limit: int = 5,
) -> list[dict]:
    # Build a richer query by including occupation and state context
    enriched_query = query_text
    if occupation:
        enriched_query += f" {occupation}"
    if state:
        enriched_query += f" {state}"

    # Pure semantic search — the bilingual descriptions handle matching
    # Filters were too strict and excluded universal schemes
    return search_collection("schemes", enriched_query, limit)
