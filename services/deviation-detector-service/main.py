import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

import numpy as np
import pika

COMPONENT_METADATA_PATH = Path("/app/component.json")

metric_history: dict[str, list[float]] = {}

MIN_HISTORY_SIZE = 3
DEVIATION_STDDEV_MULTIPLIER = 2
MAX_HISTORY_SIZE = 50

RAW_EXCHANGE = "sezra.stream.raw"
ANOMALY_EXCHANGE = "sezra.stream.anomaly"
QUEUE_NAME = "sezra.queue.deviation_detector"


class DeviationType(str, Enum):
    SPIKE = "spike"
    DROP = "drop"


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


def should_process(envelope: dict) -> bool:
    payload = envelope.get("payload", {})

    if not isinstance(payload, dict):
        return False

    source_type = payload.get("source_type")

    if source_type != "observation":
        print(f"Ignored non-observation event: " f"source_type={source_type}")
        return False

    return True


def detect_deviation(
    metric: str,
    current_value: float,
) -> tuple[DeviationType | None, float | None]:
    history = metric_history.get(metric, [])

    if len(history) < MIN_HISTORY_SIZE:
        history.append(current_value)
        metric_history[metric] = history

        print(
            f"History initialized for metric: {metric} "
            f"({len(history)}/{MIN_HISTORY_SIZE})"
        )

        return None, None

    previous_value = history[-1]

    mean = np.mean(history)
    stddev = np.std(history)

    history.append(current_value)

    if len(history) > MAX_HISTORY_SIZE:
        history = history[-MAX_HISTORY_SIZE:]

    metric_history[metric] = history

    if stddev == 0:
        print(
            f"Metric={metric} "
            f"Mean={mean:.2f} "
            f"StdDev={stddev:.2f} "
            f"Z-Score=not available"
        )

        return None, previous_value

    z_score = (current_value - mean) / stddev

    print(
        f"Metric={metric} "
        f"Mean={mean:.2f} "
        f"StdDev={stddev:.2f} "
        f"Z-Score={z_score:.2f}"
    )

    if z_score >= DEVIATION_STDDEV_MULTIPLIER:
        return DeviationType.SPIKE, previous_value

    if z_score <= -DEVIATION_STDDEV_MULTIPLIER:
        return DeviationType.DROP, previous_value

    return None, previous_value


def create_anomaly_event(
    envelope: dict,
    metric: str,
    previous_value: float,
    current_value: float,
    deviation_type: DeviationType,
) -> dict:
    change_amount = current_value - previous_value
    if deviation_type == DeviationType.SPIKE:
        reason = "value increased significantly compared to recent history"
    else:
        reason = "value decreased significantly compared to recent history"

    return {
        "event_id": str(uuid4()),
        "event_type": "AnomalyDetected",
        "source": "deviation-detector-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": envelope["event_id"],
        "causation_id": envelope["event_id"],
        "payload": {
            "anomaly_type": deviation_type.value,
            "metric": metric,
            "previous_value": previous_value,
            "current_value": current_value,
            "change_amount": change_amount,
            "reason": reason,
            "source_event_id": envelope["event_id"],
        },
    }


def main() -> None:
    with open(COMPONENT_METADATA_PATH, "r") as file:
        component_metadata = json.load(file)

    print(
        f"Starting component: "
        f"{component_metadata['display_name']} "
        f"({component_metadata['id']})"
)
    print("SEZRA deviation-detector-service started")

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=RAW_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )

    channel.exchange_declare(
        exchange=ANOMALY_EXCHANGE,
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

            print(f"Received raw event: {event_id}")

            if not should_process(envelope):
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            payload = envelope.get("payload", {})

            metric = payload.get("metric")
            current_value = payload.get("value")

            if metric is None or current_value is None:
                print("Invalid observation ignored")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            current_value = float(current_value)

            deviation_detected, previous_value = detect_deviation(
                metric=metric,
                current_value=current_value,
            )

            if deviation_detected and previous_value is not None:
                print(
                    f"{deviation_detected.value.capitalize()} deviation detected "
                    f"for metric: {metric}"
                )

                anomaly_event = create_anomaly_event(
                    envelope=envelope,
                    metric=metric,
                    previous_value=previous_value,
                    current_value=current_value,
                    deviation_type=deviation_detected,
                )

                channel.basic_publish(
                    exchange=ANOMALY_EXCHANGE,
                    routing_key="",
                    body=json.dumps(anomaly_event).encode("utf-8"),
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,
                    ),
                )

                print(f"Published anomaly event: {anomaly_event['event_id']}")

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
