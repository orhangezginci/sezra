import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pika

COMPONENT_METADATA_PATH = Path("/app/component.json")


def load_component_metadata() -> dict:
    with open(COMPONENT_METADATA_PATH, "r") as file:
        return json.load(file)


component_metadata = load_component_metadata()
config = component_metadata["config"]
rabbitmq_config = component_metadata["rabbitmq"]

INPUT_FOLDER = Path(config["input_folder"])
PROCESSED_FOLDER = Path(config["processed_folder"])

OUTPUT_EXCHANGE = rabbitmq_config["output_exchange"]

POLL_INTERVAL_SECONDS = 2


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


def read_external_input(file_path: Path) -> dict:
    with open(file_path, "r") as file:
        return json.load(file)


def transform_to_sezra_event(external_data: dict) -> dict:
    source_type = external_data.get("source_type")

    if source_type == "observation":
        event_type = "ObservationReceived"
    elif source_type == "context":
        event_type = "ContextReceived"
    else:
        event_type = "ExternalDataReceived"

    event_id = str(uuid4())

    return {
        "event_id": event_id,
        "event_type": event_type,
        "source": component_metadata["service_name"],
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": event_id,
        "causation_id": event_id,
        "payload": external_data,
    }


def publish_event(channel, event: dict) -> None:
    channel.basic_publish(
        exchange=OUTPUT_EXCHANGE,
        routing_key="",
        body=json.dumps(event).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )


def move_processed_file(file_path: Path) -> None:
    PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)
    target_path = PROCESSED_FOLDER / file_path.name
    shutil.move(str(file_path), str(target_path))


def process_file(channel, file_path: Path) -> None:
    external_data = read_external_input(file_path)
    event = transform_to_sezra_event(external_data)
    publish_event(channel, event)
    move_processed_file(file_path)

    print(f"Published SEZRA event: {event['event_id']} from {file_path.name}")


def main() -> None:
    print(
        f"Starting component: "
        f"{component_metadata['display_name']} "
        f"({component_metadata['id']})"
    )

    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=OUTPUT_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )

    print(f"Watching external input folder: {INPUT_FOLDER}")
    print(f"Publishing SEZRA events to exchange: {OUTPUT_EXCHANGE}")

    while True:
        for file_path in sorted(INPUT_FOLDER.glob("*.json")):
            try:
                process_file(channel, file_path)
            except Exception as error:
                print(f"Failed to process {file_path.name}: {error}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()