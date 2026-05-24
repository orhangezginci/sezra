import json
import os
import time

import pika
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


QDRANT_HOST = required_env("QDRANT_HOST")
QDRANT_PORT = int(required_env("QDRANT_PORT"))

RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")

RAW_EXCHANGE = "sezra.stream.raw"
QUEUE_NAME = "sezra.queue.embedding"

COLLECTION_NAME = "sezra_events"
VECTOR_SIZE = 384


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


def ensure_collection(qdrant_client: QdrantClient) -> None:
    existing_collections = [
        collection.name
        for collection in qdrant_client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing_collections:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        print(f"Qdrant collection already exists: {COLLECTION_NAME}")


def create_dummy_vector() -> list[float]:
    return [0.0] * VECTOR_SIZE


def main() -> None:
    print("SEZRA embedding-service started")

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    ensure_collection(qdrant_client)

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=RAW_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    channel.queue_bind(
        exchange=RAW_EXCHANGE,
        queue=QUEUE_NAME,
    )

    print(f"Listening on queue: {QUEUE_NAME}")

    def handle_message(channel, method, properties, body):
        try:
            envelope = json.loads(body.decode("utf-8"))
            event_id = envelope.get("event_id")

            if not event_id:
                print("Invalid raw event ignored: missing event_id")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            print(f"Received raw event for embedding: {event_id}")

            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=event_id,
                        vector=create_dummy_vector(),
                        payload={
                            "event_id": event_id,
                            "event_type": envelope.get("event_type"),
                            "source": envelope.get("source"),
                            "occurred_at": envelope.get("occurred_at"),
                            "payload": envelope.get("payload", {}),
                        },
                    )
                ],
            )

            print(f"Stored dummy vector for event: {event_id}")

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