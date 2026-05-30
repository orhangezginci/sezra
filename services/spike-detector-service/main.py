import json
import os
import time

import pika
from datetime import datetime, timezone
from uuid import uuid4

last_values: dict[str, float] = {}
SPIKE_THRESHOLD = 100

def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


RABBITMQ_HOST = required_env("RABBITMQ_HOST")
RABBITMQ_PORT = int(required_env("RABBITMQ_PORT"))
RABBITMQ_USER = required_env("RABBITMQ_USER")
RABBITMQ_PASSWORD = required_env("RABBITMQ_PASSWORD")

RAW_EXCHANGE = "sezra.stream.raw"
ANOMALY_EXCHANGE = "sezra.stream.anomaly"
QUEUE_NAME = "sezra.queue.spike_detector"


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
        print(
            f"Ignored non-observation event: "
            f"source_type={source_type}"
        )
        return False

    return True

def detect_spike(
    metric: str,
    current_value: float,
) -> tuple[bool, float | None]:
    previous_value = last_values.get(metric)

    last_values[metric] = current_value

    if previous_value is None:
        print(f"Baseline initialized for metric: {metric}")
        return False, None

    increase_amount = current_value - previous_value

    if increase_amount >= SPIKE_THRESHOLD:
        return True, previous_value

    return False, previous_value

def create_anomaly_event(
    envelope: dict,
    metric: str,
    previous_value: float,
    current_value: float,
) -> dict:
    increase_amount = current_value - previous_value

    return {
        "event_id": str(uuid4()),
        "event_type": "AnomalyDetected",
        "source": "spike-detector-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": envelope["event_id"],
        "causation_id": envelope["event_id"],
        "payload": {
            "metric": metric,
            "previous_value": previous_value,
            "current_value": current_value,
            "increase_amount": increase_amount,
            "threshold": SPIKE_THRESHOLD,
            "reason": "value increased above previous observation",
            "source_event_id": envelope["event_id"],
        },
    }

def main() -> None:
    print("SEZRA spike-detector-service started")

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
        """
        Callback function to handle messages consumed from the RabbitMQ queue.

        This function always acknowledges messages, even if an error occurs during processing,
        to prevent message re-delivery and ensure proper message queue semantics.

        Args:
            channel: The channel object.
            method: Delivery method/frame with delivery_tag.
            properties: Message properties.
            body: The message body as bytes.
        """
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

            spike_detected, previous_value = detect_spike(
                metric=metric,
                current_value=float(current_value),
            )

            if spike_detected:
                print(f"Spike anomaly detected for metric: {metric}")
                anomaly_event = create_anomaly_event(
                envelope=envelope,
                metric=metric,
                previous_value=previous_value,
                current_value=float(current_value),
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