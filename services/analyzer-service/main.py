import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pika
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sentence_transformers import SentenceTransformer

CONTEXT_SEARCH_RETRIES = 5
CONTEXT_SEARCH_RETRY_DELAY_SECONDS = 2

COLLECTION_NAME = "sezra_events"
MODEL_NAME = "all-MiniLM-L6-v2"

ANOMALY_EXCHANGE = "sezra.stream.anomaly"
INVESTIGATION_EXCHANGE = "sezra.stream.investigation"
ANALYSIS_EXCHANGE = "sezra.stream.analysis"

QUEUE_NAME = "sezra.queue.analyzer"

ANALYZER_DEAD_LETTER_EXCHANGE = "sezra.stream.dead_letter"
ANALYZER_DEAD_LETTER_ROUTING_KEY = "analyzer-service.failed"


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


def validate_event_envelope(event: dict) -> None:
    required_fields = [
        "event_id",
        "event_type",
        "source",
        "occurred_at",
        "payload",
    ]

    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required envelope field: {field}")

    if not isinstance(event["payload"], dict):
        raise ValueError("Envelope payload must be an object")


def build_anomaly_search_text(anomaly_event: dict) -> str:
    payload = anomaly_event.get("payload", {})

    metric = payload.get("metric")
    current_value = payload.get("current_value")
    previous_value = payload.get("previous_value")
    drop_amount = payload.get("drop_amount")
    increase_amount = payload.get("increase_amount")
    reason = payload.get("reason")

    parts = []

    if metric:
        parts.append(f"Anomaly detected for metric {metric}.")

    if previous_value is not None and current_value is not None:
        parts.append(f"The value changed from {previous_value} to {current_value}.")

    if drop_amount is not None:
        parts.append(f"The detected drop amount is {drop_amount}.")

    if increase_amount is not None:
        parts.append(f"The detected increase amount is {increase_amount}.")

    if reason:
        parts.append(f"Reason: {reason}.")

    return " ".join(parts)


def build_investigation_search_text(investigation_event: dict) -> str:
    payload = investigation_event.get("payload", {})

    parts = []
    reason = payload.get("reason")
    subject = payload.get("subject")
    summary = payload.get("summary")

    if reason:
        parts.append(f"Investigation reason: {reason}.")
    if subject:
        parts.append(f"Subject: {subject}.")
    if summary:
        parts.append(f"Summary: {summary}.")

    return " ".join(parts)


def derive_investigation_subject(investigation_event: dict) -> str:
    payload = investigation_event.get("payload", {})

    subject = payload.get("subject")
    if subject:
        return subject

    summary = payload.get("summary")
    if summary:
        return summary.split(".")[0]

    return "Untitled investigation"


def derive_evidence_type(evidence: dict) -> str:
    payload = evidence.get("payload") or {}

    if payload.get("metric") or payload.get("value") is not None:
        return "measurement"

    if payload.get("from") or payload.get("subject"):
        return "message"

    return "unknown"


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
        if not text or text in seen_texts:
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

    anomaly_type = payload.get("anomaly_type")
    metric = payload.get("metric", "unknown metric")
    previous_value = payload.get("previous_value")
    current_value = payload.get("current_value")
    drop_amount = payload.get("drop_amount")
    increase_amount = payload.get("increase_amount")

    anomaly_label = f"{anomaly_type} anomaly" if anomaly_type else "anomaly"

    summary = (
        f'SEZRA detected a {anomaly_label} for metric "{metric}". '
        f"The value changed from {previous_value} to {current_value}."
    )

    if drop_amount is not None:
        summary += f" Detected drop amount: {drop_amount}."
    if increase_amount is not None:
        summary += f" Detected increase amount: {increase_amount}."

    if related_contexts:
        best_context = related_contexts[0]
        summary += (
            " The most relevant contextual event found was: "
            f'"{best_context.get("text")}".'
        )
    else:
        summary += " No relevant contextual event was found."

    return summary


def build_human_readable_analysis(
    anomaly_event: dict,
    related_contexts: list[dict],
) -> dict:
    payload = anomaly_event.get("payload", {})

    anomaly_type = payload.get("anomaly_type", "unknown")
    metric = payload.get("metric", "unknown metric")
    previous_value = payload.get("previous_value")
    current_value = payload.get("current_value")
    increase_amount = payload.get("increase_amount")
    drop_amount = payload.get("drop_amount")

    title = f"{anomaly_type.capitalize()} anomaly detected"

    detected_anomaly = (
        f'Metric "{metric}" changed from {previous_value} to {current_value}.'
    )

    if increase_amount is not None:
        detected_anomaly += f" Increase amount: {increase_amount}."
    if drop_amount is not None:
        detected_anomaly += f" Drop amount: {drop_amount}."

    most_relevant_context = (
        related_contexts[0].get("text")
        if related_contexts
        else "No relevant contextual signal was found."
    )

    possible_interpretation = (
        "The related context may help explain the detected anomaly. "
        "This is a semantic correlation, not a proven causal conclusion."
    )

    return {
        "title": title,
        "detected_anomaly": detected_anomaly,
        "most_relevant_context": most_relevant_context,
        "possible_interpretation": possible_interpretation,
    }


def print_human_readable_analysis(human_readable: dict) -> None:
    print()
    print("SEZRA Analysis")
    print()
    print("Anomaly:")
    print(human_readable["detected_anomaly"])
    print()
    print("Likely context:")
    print(human_readable["most_relevant_context"])
    print()
    print("Interpretation:")
    print(human_readable["possible_interpretation"])
    print()


def search_semantic_evidence(
    qdrant_client: QdrantClient,
    embedding_model: SentenceTransformer,
    search_text: str,
    limit: int = 5,
) -> list[dict]:
    print(f"Semantic evidence query: {search_text}")

    vector = embedding_model.encode(search_text).tolist()

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
    )

    seen_texts = set()
    results = []

    for point in response.points:
        text = point.payload.get("text")

        if not text or text in seen_texts:
            continue

        seen_texts.add(text)

        evidence = {
            "score": point.score,
            "event_id": point.payload.get("event_id"),
            "source": point.payload.get("source"),
            "text": text,
            "payload": point.payload.get("payload"),
        }

        evidence["evidence_type"] = derive_evidence_type(evidence)

        results.append(evidence)

    return results


def build_investigation_summary(
    investigation_event: dict,
    evidence: list[dict],
) -> str:
    subject = derive_investigation_subject(investigation_event)

    lines = [
        f"Investigation: {subject}",
        "",
        "Relevant evidence:",
    ]

    for item in evidence:
        text = item.get("text")

        if text:
            lines.append(f"- {text}")

    return "\n".join(lines)


def create_analysis_event(
    anomaly_event: dict,
    related_contexts: list[dict],
) -> dict:
    anomaly_event_id = anomaly_event["event_id"]

    summary = build_summary(
        anomaly_event=anomaly_event,
        related_contexts=related_contexts,
    )

    human_readable = build_human_readable_analysis(
        anomaly_event=anomaly_event,
        related_contexts=related_contexts,
    )

    return {
        "event_id": str(uuid4()),
        "event_type": "AnalysisGenerated",
        "source": "analyzer-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": anomaly_event_id,
        "causation_id": anomaly_event_id,
        "payload": {
            "summary": summary,
            "human_readable": human_readable,
            "related_contexts": related_contexts,
            "source_anomaly_event_id": anomaly_event_id,
        },
    }


def create_investigation_event(
    investigation_event: dict,
    evidence: list[dict],
    summary: str,
) -> dict:
    investigation_event_id = investigation_event["event_id"]
    subject = derive_investigation_subject(investigation_event)

    return {
        "event_id": str(uuid4()),
        "event_type": "InvestigationGenerated",
        "source": "analyzer-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": investigation_event_id,
        "causation_id": investigation_event_id,
        "payload": {
            "subject": subject,
            "summary": summary,
            "evidence": evidence,
            "source_investigation_event_id": investigation_event_id,
        },
    }


def publish_dead_letter_event(
    channel,
    original_body: bytes,
    error: Exception,
    reason: str,
    failure_class: str,
) -> None:
    failed_event = {
        "event_id": str(uuid4()),
        "event_type": "EventProcessingFailed",
        "source": "analyzer-service",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": None,
        "causation_id": None,
        "payload": {
            "failed_service": "analyzer-service",
            "failure_class": failure_class,
            "reason": reason,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "original_body": original_body.decode("utf-8", errors="replace"),
        },
    }

    channel.basic_publish(
        exchange=ANALYZER_DEAD_LETTER_EXCHANGE,
        routing_key=ANALYZER_DEAD_LETTER_ROUTING_KEY,
        body=json.dumps(failed_event).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )

    print(
        f"Published dead-letter event: {failed_event['event_id']} "
        f"(class={failure_class})"
    )


def main() -> None:
    print("SEZRA analyzer-service started")

    print(f"Loading embedding model: {MODEL_NAME}")
    embedding_model = SentenceTransformer(MODEL_NAME)
    print("Embedding model loaded")

    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    collections = qdrant_client.get_collections()
    print("Connected to Qdrant")
    print(f"Collections: {collections}")

    connection = connect_to_rabbitmq()
    channel = connection.channel()

    for exchange in (
        ANOMALY_EXCHANGE,
        INVESTIGATION_EXCHANGE,
        ANALYSIS_EXCHANGE,
        ANALYZER_DEAD_LETTER_EXCHANGE,
    ):
        channel.exchange_declare(
            exchange=exchange,
            exchange_type="fanout",
            durable=True,
        )

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.queue_bind(exchange=ANOMALY_EXCHANGE, queue=QUEUE_NAME)
    channel.queue_bind(exchange=INVESTIGATION_EXCHANGE, queue=QUEUE_NAME)

    print(f"Listening on queue: {QUEUE_NAME}")

    def handle_message(channel, method, properties, body):
        try:
            event = json.loads(body.decode("utf-8"))
            validate_event_envelope(event)

            event_id = event.get("event_id")
            event_type = event.get("event_type")

            print(f"Received event: {event_type} ({event_id})")

            if event_type == "InvestigationRequested":
                search_text = build_investigation_search_text(event)
                print(f"Investigation search text: {search_text}")

                evidence = search_semantic_evidence(
                    qdrant_client=qdrant_client,
                    embedding_model=embedding_model,
                    search_text=search_text,
                )

                summary = build_investigation_summary(
                    investigation_event=event,
                    evidence=evidence,
                )

                investigation_generated_event = create_investigation_event(
                    investigation_event=event,
                    evidence=evidence,
                    summary=summary,
                )

                channel.basic_publish(
                    exchange=ANALYSIS_EXCHANGE,
                    routing_key="",
                    body=json.dumps(investigation_generated_event).encode("utf-8"),
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,
                    ),
                )

                print(
                    f"Created investigation event: "
                    f"{investigation_generated_event['event_type']}"
                )
                print(
                    f"Published investigation event: "
                    f"{investigation_generated_event['event_id']}"
                )

                print()
                print("SEZRA Investigation")
                print()
                print(summary)
                print()

                print(f"Evidence candidates found: {len(evidence)}")
                for item in evidence:
                    print(
                        f"Evidence candidate: "
                        f"type={item.get('evidence_type')} "
                        f"score={item.get('score')} "
                        f"event_id={item.get('event_id')} "
                        f"source={item.get('source')} "
                        f"text={item.get('text')}"
                    )

                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            if event_type != "AnomalyDetected":
                print(f"Skipping unsupported event type: {event_type}")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            related_contexts = []

            for attempt in range(CONTEXT_SEARCH_RETRIES):
                related_contexts = search_related_contexts(
                    qdrant_client=qdrant_client,
                    embedding_model=embedding_model,
                    anomaly_event=event,
                )

                if related_contexts:
                    break

                print(
                    f"No related context found yet. "
                    f"Retrying context search ({attempt + 1}/{CONTEXT_SEARCH_RETRIES})..."
                )
                time.sleep(CONTEXT_SEARCH_RETRY_DELAY_SECONDS)

            print(f"Related contexts found: {len(related_contexts)}")

            human_readable = build_human_readable_analysis(
                anomaly_event=event,
                related_contexts=related_contexts,
            )

            print_human_readable_analysis(human_readable)

            analysis_event = create_analysis_event(
                anomaly_event=event,
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
            print(f"Invalid JSON received: {error}")
            publish_dead_letter_event(
                channel=channel,
                original_body=body,
                error=error,
                reason="Invalid JSON payload",
                failure_class="permanent",
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except ValueError as error:
            print(f"Invalid SEZRA event envelope: {error}")
            publish_dead_letter_event(
                channel=channel,
                original_body=body,
                error=error,
                reason="Invalid SEZRA event envelope",
                failure_class="permanent",
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as error:
            print(f"Unexpected analyzer error: {error}")
            publish_dead_letter_event(
                channel=channel,
                original_body=body,
                error=error,
                reason="Unexpected analyzer processing failure",
                failure_class="transient",
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=handle_message,
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()
