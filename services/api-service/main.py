from fastapi import FastAPI, HTTPException
from sqlalchemy import desc

from database import SessionLocal
from models import StoredEventEnvelope


app = FastAPI(title="SEZRA API")


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
