import json
import os
import time
from pathlib import Path

import pika
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database import SessionLocal
from models import StoredEventEnvelope


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "sezra")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "sezra")

EXCHANGES = [
    "sezra.stream.raw",
    "sezra.stream.anomaly",
    "sezra.stream.analysis",
    "sezra.stream.dead_letter",
]

QUEUE_NAME = "sezra.queue.event_store"
SCHEMA_PATH = Path("/contracts/event_envelope.schema.json")


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_event(envelope: dict) -> str:
    session = SessionLocal()

    try:
        stored_event = StoredEventEnvelope(
            event_id=envelope["event_id"],
            event_type=envelope["event_type"],
            source=envelope["source"],
            occurred_at=envelope["occurred_at"],
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("causation_id"),
            payload=envelope["payload"],
        )

        session.add(stored_event)
        session.commit()

        return "saved"

    except IntegrityError:
        session.rollback()
        return "duplicate"

    except SQLAlchemyError:
        session.rollback()
        raise

    finally:
        session.close()


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


def main() -> None:
    schema = load_schema()

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    for exchange in EXCHANGES:
        channel.exchange_declare(
            exchange=exchange,
            exchange_type="fanout",
            durable=True,
        )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    for exchange in EXCHANGES:
        channel.queue_bind(
            exchange=exchange,
            queue=QUEUE_NAME,
        )

    print("SEZRA event-store-service listening for events")

    def handle_message(channel, method, properties, body):
        try:
            envelope = json.loads(body.decode("utf-8"))
            validate(instance=envelope, schema=schema)

            result = save_event(envelope)

            if result == "saved":
                print(f"Event saved: {envelope['event_id']}")

            elif result == "duplicate":
                print(f"Duplicate event ignored: {envelope['event_id']}")

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as error:
            print(f"Invalid JSON message: {error}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except ValidationError as error:
            print(f"Invalid EventEnvelope: {error.message}")
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except SQLAlchemyError as error:
            print(f"Database error, message will be requeued: {error}")
            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True,
            )

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=handle_message,
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()