import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pika
from qdrant_client import QdrantClient
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


def create_analysis_event(anomaly_event: dict) -> dict:
    anomaly_event_id = anomaly_event["event_id"]

    return {
        "event_id": str(uuid4()),
        "event_type": "CausalAnalysisResult",
        "source": "analyzer-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": anomaly_event_id,
        "causation_id": anomaly_event_id,
        "payload": {
            "summary": "Static MVP analysis placeholder",
            "anomaly_event_id": anomaly_event_id,
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

            analysis_event = create_analysis_event(anomaly_event)

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