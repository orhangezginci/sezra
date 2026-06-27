import json
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

import pika

RAW_EXCHANGE = "sezra.stream.raw"
ENRICHED_EXCHANGE = "sezra.stream.enriched"
QUEUE_NAME = "sezra.queue.level_1_enricher"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")


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


def words(value: str) -> str:
    return re.sub(r"[_\-]+", " ", str(value)).strip()


def collect_scalar_fields(payload: dict, prefix: str = "") -> list[str]:
    parts = []

    for key, value in payload.items():
        field_name = words(f"{prefix}{key}")

        if isinstance(value, dict):
            parts.extend(collect_scalar_fields(value, prefix=f"{field_name} "))
            continue

        if isinstance(value, (str, int, float, bool)) and value is not None:
            parts.append(f"{field_name}: {words(value)}.")

    return parts


def update_lifecycle(event: dict, stage: str) -> dict:
    lifecycle = dict(event.get("lifecycle", {}))
    history = list(lifecycle.get("history", []))

    history.append(
        {
            "stage": stage,
            "service": "level-1-enricher-service",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    lifecycle["stage"] = stage
    lifecycle["history"] = history

    return lifecycle


def build_semantic_text(event: dict) -> str:
    payload = event.get("payload", {})

    parts = []

    event_type = event.get("event_type")
    source = event.get("source")

    if event_type:
        parts.append(f"Event type: {words(event_type)}.")

    if source:
        parts.append(f"Source: {words(source)}.")

    if isinstance(payload, dict):
        parts.extend(collect_scalar_fields(payload))

    return " ".join(parts).strip()


def create_enriched_event(event: dict) -> dict:
    enriched_event = dict(event)
    payload = dict(event.get("payload", {}))

    payload["semantic_text"] = build_semantic_text(event)
    payload["enrichments"] = [
    {
        "level": 1,
        "service": "level-1-enricher-service",
        "strategy": "generic scalar field expansion",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
]

    enriched_event["payload"] = payload
    enriched_event["event_id"] = str(uuid4())
    enriched_event["source"] = "level-1-enricher-service"
    enriched_event["causation_id"] = event.get("event_id")
    enriched_event["correlation_id"] = event.get("correlation_id") or event.get(
        "event_id"
    )

    enriched_event["lifecycle"] = update_lifecycle(
        event=event,
        stage="enriched",
    )
    return enriched_event


def main() -> None:
    print("SEZRA level-1-enricher-service started")

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=RAW_EXCHANGE, exchange_type="fanout", durable=True
    )
    channel.exchange_declare(
        exchange=ENRICHED_EXCHANGE, exchange_type="fanout", durable=True
    )

    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=RAW_EXCHANGE, queue=QUEUE_NAME)

    print(f"Listening on queue: {QUEUE_NAME}")

    def handle_message(channel, method, properties, body):
        try:
            event = json.loads(body.decode("utf-8"))
            event_id = event.get("event_id")

            print(f"Received raw event: {event_id}")

            enriched_event = create_enriched_event(event)

            channel.basic_publish(
                exchange=ENRICHED_EXCHANGE,
                routing_key="",
                body=json.dumps(enriched_event).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )

            print(f"Published enriched event: {enriched_event['event_id']}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as error:
            print(f"Invalid JSON ignored: {error}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as error:
            print(f"Unexpected enricher error: {error}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_message)
    channel.start_consuming()


if __name__ == "__main__":
    main()
