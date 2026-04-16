"""Embed and upsert all data files into Qdrant collections."""
import json
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, PayloadSchemaType
from src.config import QDRANT_URL, QDRANT_API_KEY, EMBEDDING_DIMENSION
from src.config import QDRANT_COLLECTION_SCHEMES, QDRANT_COLLECTION_HEALTH, QDRANT_COLLECTION_SERVICES
from src.embeddings import get_embedding


def load_json(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def make_embedding_text(doc: dict, doc_type: str) -> str:
    """Concatenate relevant text fields for embedding."""
    if doc_type == "schemes":
        return f"{doc['name']} {doc.get('name_hi', '')} {doc['description']} {doc['benefits']} {' '.join(doc.get('category', []))}"
    elif doc_type == "health":
        return f"{doc['description']} {' '.join(doc['symptoms'])} {doc['action_mild']} {doc['action_severe']}"
    elif doc_type == "services":
        return f"{doc['name']} {doc['description']} {doc.get('category', '')}"
    return doc.get("description", "")


def ingest_collection(client: QdrantClient, collection_name: str, data_path: str, doc_type: str):
    docs = load_json(data_path)

    # Recreate collection
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
    )

    # Embed and upsert
    points = []
    for i, doc in enumerate(docs):
        text = make_embedding_text(doc, doc_type)
        vector = get_embedding(text)
        points.append(PointStruct(id=i, vector=vector, payload=doc))

    client.upsert(collection_name=collection_name, points=points)
    print(f"  Ingested {len(points)} documents into '{collection_name}'")


def main():
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    print("Ingesting knowledge base into Qdrant...")
    ingest_collection(client, QDRANT_COLLECTION_SCHEMES, "data/schemes.json", "schemes")
    ingest_collection(client, QDRANT_COLLECTION_HEALTH, "data/health.json", "health")
    ingest_collection(client, QDRANT_COLLECTION_SERVICES, "data/services.json", "services")

    # Create payload indexes for filtered search on schemes
    client.create_payload_index(QDRANT_COLLECTION_SCHEMES, "eligibility.occupation", PayloadSchemaType.KEYWORD)
    client.create_payload_index(QDRANT_COLLECTION_SCHEMES, "eligibility.land_max_acres", PayloadSchemaType.FLOAT)
    print("  Created payload indexes for scheme filtering")

    print("Done!")


if __name__ == "__main__":
    main()
