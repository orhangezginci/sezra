from fastapi import FastAPI, HTTPException
from sqlalchemy import desc
import os

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from database import SessionLocal
from models import StoredEventEnvelope

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

COLLECTION_NAME = "sezra_events"
MODEL_NAME = "all-MiniLM-L6-v2"
app = FastAPI(title="SEZRA API")

qdrant_client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
)

embedding_model = SentenceTransformer(MODEL_NAME)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/events")
def get_events(limit: int = 20):
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be a positive integer")

    session = SessionLocal()

    try:
        events = (
            session.query(StoredEventEnvelope)
            .order_by(desc(StoredEventEnvelope.received_at))
            .limit(limit)
            .all()
        )

        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source": event.source,
                "occurred_at": event.occurred_at,
                "received_at": event.received_at,
                "correlation_id": event.correlation_id,
                "causation_id": event.causation_id,
                "payload": event.payload,
            }
            for event in events
        ]
    finally:
        session.close()


@app.get("/events/{event_id}")
def get_event(event_id: str):
    session = SessionLocal()

    try:
        event = (
            session.query(StoredEventEnvelope)
            .filter(StoredEventEnvelope.event_id == event_id)
            .first()
        )
    finally:
        session.close()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "source": event.source,
        "occurred_at": event.occurred_at,
        "received_at": event.received_at,
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "payload": event.payload,
    }
@app.get("/events/type/{event_type}")
def get_events_by_type(event_type: str, limit: int = 20):
    session = SessionLocal()

    try:
        events = (
            session.query(StoredEventEnvelope)
            .filter(StoredEventEnvelope.event_type == event_type)
            .order_by(desc(StoredEventEnvelope.received_at))
            .limit(limit)
            .all()
        )

        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source": event.source,
                "occurred_at": event.occurred_at,
                "received_at": event.received_at,
                "correlation_id": event.correlation_id,
                "causation_id": event.causation_id,
                "payload": event.payload,
            }
            for event in events
        ]

    finally:
        session.close()

@app.get("/events/correlation/{correlation_id}")
def get_events_by_correlation(correlation_id: str, limit: int = 20):
    session = SessionLocal()

    try:
        events = (
            session.query(StoredEventEnvelope)
            .filter(StoredEventEnvelope.correlation_id == correlation_id)
            .order_by(desc(StoredEventEnvelope.received_at))
            .limit(limit)
            .all()
        )

        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source": event.source,
                "occurred_at": event.occurred_at,
                "received_at": event.received_at,
                "correlation_id": event.correlation_id,
                "causation_id": event.causation_id,
                "payload": event.payload,
            }
            for event in events
        ]

    finally:
        session.close()
@app.get("/semantic/search")
def semantic_search(query: str, limit: int = 5):
    vector = embedding_model.encode(query).tolist()

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
    )

    return [
        {
            "score": point.score,
            "payload": point.payload,
        }
        for point in response.points
    ]