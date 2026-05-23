import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pika


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


INPUT_FOLDER = Path(os.getenv("INPUT_FOLDER", "/data/inbox"))
PROCESSED_FOLDER = Path(os.getenv("PROCESSED_FOLDER", "/data/processed"))

RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")

EXCHANGE_NAME = "sezra.stream.raw"


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
    print("SEZRA json-file-adapter started")
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Processed folder: {PROCESSED_FOLDER}")

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="fanout",
        durable=True,
    )

    print(f"Connected to RabbitMQ exchange: {EXCHANGE_NAME}")

    json_files = sorted(INPUT_FOLDER.glob("*.json"))

    print(f"Found {len(json_files)} JSON file(s)")

    for json_file in json_files:
        print(f"Reading JSON file: {json_file.name}")

        with json_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        envelope = {
            "event_id": str(uuid4()),
            "event_type": "JsonFileReceived",
            "source": f"json-file-adapter:{json_file.name}",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": None,
            "causation_id": None,
            "payload": payload,
        }

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="",
            body=json.dumps(envelope).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )

        print(f"Published event: {envelope['event_id']}")

        processed_file = PROCESSED_FOLDER / json_file.name
        shutil.move(str(json_file), str(processed_file))

        print(f"Moved file to processed: {processed_file.name}")

    connection.close()
    print("RabbitMQ connection closed")


if __name__ == "__main__":
    main()