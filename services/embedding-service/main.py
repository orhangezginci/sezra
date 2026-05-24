import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


QDRANT_HOST = required_env("QDRANT_HOST")
QDRANT_PORT = int(required_env("QDRANT_PORT"))

COLLECTION_NAME = "sezra_events"
VECTOR_SIZE = 384


def main() -> None:
    print("SEZRA embedding-service started")

    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    existing_collections = [
        collection.name
        for collection in client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing_collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

        print(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        print(f"Qdrant collection already exists: {COLLECTION_NAME}")


if __name__ == "__main__":
    main()