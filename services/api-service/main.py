from fastapi import FastAPI, HTTPException
from sqlalchemy import desc
import os

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from sentence_transformers import SentenceTransformer
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal
from models import StoredEventEnvelope

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

COLLECTION_NAME = "sezra_events"
MODEL_NAME = "all-MiniLM-L6-v2"
app = FastAPI(title="SEZRA API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://23.88.106.126:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
qdrant_client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
)

embedding_model = SentenceTransformer(MODEL_NAME)


@app.get("/health")
def health():
    return {"status": "ok"}


def serialize_event(event: StoredEventEnvelope) -> dict:
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


@app.get("/analyses/latest")
def get_latest_analysis():
    session = SessionLocal()

    try:
        event = (
            session.query(StoredEventEnvelope)
            .filter(StoredEventEnvelope.event_type == "AnalysisGenerated")
            .order_by(desc(StoredEventEnvelope.received_at))
            .first()
        )

        if event is None:
            raise HTTPException(status_code=404, detail="No analysis found")

        return serialize_event(event)

    finally:
        session.close()


@app.get("/investigations/latest")
def get_latest_investigation():
    session = SessionLocal()

    try:
        event = (
            session.query(StoredEventEnvelope)
            .filter(StoredEventEnvelope.event_type == "InvestigationGenerated")
            .order_by(desc(StoredEventEnvelope.received_at))
            .first()
        )

        if event is None:
            raise HTTPException(status_code=404, detail="No investigation found")

        return serialize_event(event)

    finally:
        session.close()


@app.get("/events/timeline/{event_id}")
def get_event_timeline(event_id: str):
    session = SessionLocal()

    try:
        events = (
            session.query(StoredEventEnvelope)
            .filter(
                (StoredEventEnvelope.event_id == event_id)
                | (StoredEventEnvelope.correlation_id == event_id)
                | (StoredEventEnvelope.causation_id == event_id)
            )
            .order_by(StoredEventEnvelope.received_at)
            .all()
        )

        return [serialize_event(event) for event in events]

    finally:
        session.close()


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
def semantic_search(query: str, limit: int = 5, source_type: str | None = None):
    vector = embedding_model.encode(query).tolist()

    query_filter = None

    if source_type:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type),
                )
            ]
        )

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=query_filter,
        limit=limit,
    )

    return [
        {
            "score": point.score,
            "payload": point.payload,
        }
        for point in response.points
    ]
