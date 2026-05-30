import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pika


last_values: dict[str, float] = {}
DROP_THRESHOLD = 10


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
QUEUE_NAME = "sezra.queue.drop_detector"


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


def detect_drop(envelope: dict) -> dict | None:
    payload = envelope.get("payload", {})

    if not isinstance(payload, dict):
        return None

    source_type = payload.get("source_type")

    if source_type != "observation":
        print(
            f"Ignored non-observation event: "
            f"source_type={source_type}"
        )
        return None

    metric = payload.get("metric")
    value = payload.get("value")

    if metric is None or value is None:
        return None

    try:
        current_value = float(value)
    except (TypeError, ValueError):
        return None

    previous_value = last_values.get(metric)
    last_values[metric] = current_value

    if previous_value is None:
        print(f"Baseline initialized for metric: {metric}")
        return None

    drop_amount = previous_value - current_value

    if drop_amount < DROP_THRESHOLD:
        print(
            f"No drop anomaly for metric: {metric} "
            f"(previous={previous_value}, current={current_value})"
        )
        return None

    return {
        "event_id": str(uuid4()),
        "event_type": "AnomalyDetected",
        "source": "drop-detector-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": envelope["event_id"],
        "causation_id": envelope["event_id"],
        "payload": {
            "anomaly_type": "drop",
            "metric": metric,
            "previous_value": previous_value,
            "current_value": current_value,
            "drop_amount": drop_amount,
            "threshold": DROP_THRESHOLD,
            "reason": "value dropped below previous observation",
            "source_event_id": envelope["event_id"],
        },
    }


def main() -> None:
    print("SEZRA drop-detector-service started")

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

            anomaly_event = detect_drop(envelope)

            if anomaly_event is None:
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            print(
                f"Drop anomaly detected for metric: "
                f"{anomaly_event['payload']['metric']}"
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