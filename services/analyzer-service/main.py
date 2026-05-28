import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pika
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sentence_transformers import SentenceTransformer


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


QDRANT_HOST = required_env("QDRANT_HOST")
QDRANT_PORT = int(required_env("QDRANT_PORT"))

COLLECTION_NAME = "sezra_events"
MODEL_NAME = "all-MiniLM-L6-v2"

RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")

ANOMALY_EXCHANGE = "sezra.stream.anomaly"
ANALYSIS_EXCHANGE = "sezra.stream.analysis"
QUEUE_NAME = "sezra.queue.analyzer"


def connect_to_rabbitmq() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(
        username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
    )

    while True:
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                )
            )
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready yet. Retrying...")
            time.sleep(3)


def build_anomaly_search_text(anomaly_event: dict) -> str:
    payload = anomaly_event.get("payload", {})

    metric = payload.get("metric")
    current_value = payload.get("current_value")
    previous_value = payload.get("previous_value")
    drop_amount = payload.get("drop_amount")
    reason = payload.get("reason")

    parts = []

    if metric:
        parts.append(f"Anomaly detected for metric {metric}.")

    if previous_value is not None and current_value is not None:
        parts.append(
            f"The value changed from {previous_value} to {current_value}."
        )

    if drop_amount is not None:
        parts.append(f"The detected drop amount is {drop_amount}.")

    if reason:
        parts.append(f"Reason: {reason}.")

    return " ".join(parts)


def search_related_contexts(
    qdrant_client: QdrantClient,
    embedding_model: SentenceTransformer,
    anomaly_event: dict,
) -> list[dict]:
    search_text = build_anomaly_search_text(anomaly_event)

    print(f"Semantic anomaly query: {search_text}")

    vector = embedding_model.encode(search_text).tolist()

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value="context"),
                )
            ]
        ),
        limit=3,
    )

    seen_texts = set()
    related_contexts = []

    for point in response.points:
        text = point.payload.get("text")

        if text in seen_texts:
            continue

        seen_texts.add(text)

        related_contexts.append(
            {
                "score": point.score,
                "event_id": point.payload.get("event_id"),
                "source": point.payload.get("source"),
                "text": text,
                "payload": point.payload.get("payload"),
            }
        )

    return related_contexts


def build_summary(
    anomaly_event: dict,
    related_contexts: list[dict],
) -> str:
    payload = anomaly_event.get("payload", {})

    metric = payload.get("metric", "unknown metric")
    previous_value = payload.get("previous_value")
    current_value = payload.get("current_value")
    drop_amount = payload.get("drop_amount")

    summary = (
        f'SEZRA detected an anomaly for metric "{metric}". '
        f"The value changed from {previous_value} to {current_value}."
    )

    if drop_amount is not None:
        summary += f" Detected change amount: {drop_amount}."

    if related_contexts:
        best_context = related_contexts[0]

        summary += (
            " The most relevant contextual event found was: "
            f'"{best_context.get("text")}".'
        )
    else:
        summary += " No relevant contextual event was found."

    return summary


def create_analysis_event(
    anomaly_event: dict,
    related_contexts: list[dict],
) -> dict:
    anomaly_event_id = anomaly_event["event_id"]
    summary = build_summary(anomaly_event, related_contexts)

    return {
        "event_id": str(uuid4()),
        "event_type": "CausalAnalysisResult",
        "source": "analyzer-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": anomaly_event_id,
        "causation_id": anomaly_event_id,
        "payload": {
            "summary": summary,
            "anomaly_event_id": anomaly_event_id,
            "related_contexts": related_contexts,
            "confidence": 0.5,
        },
    }


def main() -> None:
    print("SEZRA analyzer-service started")

    print(f"Loading embedding model: {MODEL_NAME}")
    embedding_model = SentenceTransformer(MODEL_NAME)
    print("Embedding model loaded")

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    collections = qdrant_client.get_collections()

    print("Connected to Qdrant")
    print(f"Collections: {collections}")

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=ANOMALY_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )

    channel.exchange_declare(
        exchange=ANALYSIS_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    channel.queue_bind(
        exchange=ANOMALY_EXCHANGE,
        queue=QUEUE_NAME,
    )

    print(f"Listening on queue: {QUEUE_NAME}")

    def handle_message(channel, method, properties, body):
        try:
            anomaly_event = json.loads(body.decode("utf-8"))
            event_id = anomaly_event.get("event_id")

            if not event_id:
                print("Invalid anomaly event ignored: missing event_id")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            print(f"Received anomaly event: {event_id}")

            related_contexts = search_related_contexts(
                qdrant_client=qdrant_client,
                embedding_model=embedding_model,
                anomaly_event=anomaly_event,
            )

            print(f"Related contexts: {related_contexts}")

            analysis_event = create_analysis_event(
                anomaly_event=anomaly_event,
                related_contexts=related_contexts,
            )

            channel.basic_publish(
                exchange=ANALYSIS_EXCHANGE,
                routing_key="",
                body=json.dumps(analysis_event).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )

            print(f"Published analysis event: {analysis_event['event_id']}")

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as error:
            print(f"Invalid JSON ignored: {error}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=handle_message,
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()