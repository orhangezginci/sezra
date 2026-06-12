# SEZRA Event Contracts

## Overview

SEZRA Engine is a hyper-decoupled, event-driven semantic analysis platform.

All SEZRA services communicate exclusively through standardized event envelopes over message streams.

Services:

* MUST NOT directly call internal service code
* MUST NOT depend on implementation details of other services
* MAY be implemented in any programming language
* MUST communicate only through documented event contracts

The event contract is the core interoperability layer of SEZRA Engine.

---

# Standard Event Envelope

All SEZRA events MUST use the following envelope structure.

```json
{
  "event_id": "uuid",
  "event_type": "EventType",
  "source": "service-name",
  "occurred_at": "ISO-8601 timestamp",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {}
}
```

---

# Envelope Fields

| Field            | Description                            |
| ---------------- | -------------------------------------- |
| `event_id`       | Unique identifier of this event        |
| `event_type`     | Type name of the event                 |
| `source`         | Producing service                      |
| `occurred_at`    | UTC ISO-8601 timestamp                 |
| `correlation_id` | Shared workflow correlation identifier |
| `causation_id`   | Event that directly caused this event  |
| `payload`        | Event-specific payload                 |

---

# Correlation Rules

## correlation_id

The `correlation_id` tracks an entire event chain.

Example:

```text
RawObservation
→ AnomalyDetected
→ AnalysisGenerated
```

All events in this chain SHOULD share the same `correlation_id`.

---

## causation_id

The `causation_id` identifies the direct parent event.

Example:

```text
AnalysisGenerated
caused by
AnomalyDetected
```

---

# Observation Events

Observation events represent measurable signals or telemetry.

## Example

```json
{
  "event_id": "uuid",
  "event_type": "ObservationReceived",
  "source": "json-file-adapter",
  "occurred_at": "2026-06-02T12:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {
    "source_type": "observation",
    "metric": "api_latency_ms",
    "service": "checkout-api",
    "value": 420
  }
}
```

---

# Observation Payload Fields

| Field         | Description            |
| ------------- | ---------------------- |
| `source_type` | MUST be `observation`  |
| `metric`      | Metric name            |
| `service`     | Related service/system |
| `value`       | Numeric metric value   |

---

# Context Events

Context events represent potentially relevant contextual information.

Context events MAY be:

* metric-based
* textual
* deployment-related
* operational
* business-related
* external-system events

---

## Metric Context Example

```json
{
  "event_id": "uuid",
  "event_type": "ContextReceived",
  "source": "json-file-adapter",
  "occurred_at": "2026-06-02T12:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {
    "source_type": "context",
    "context_type": "metric",
    "metric": "cpu_usage_percent",
    "service": "checkout-api",
    "value": 94
  }
}
```

---

## Text Context Example

```json
{
  "event_id": "uuid",
  "event_type": "ContextReceived",
  "source": "jenkins-adapter",
  "occurred_at": "2026-06-02T12:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {
    "source_type": "context",
    "context_type": "deployment",
    "text": "checkout-api version 1.12.0 deployed with new logging middleware"
  }
}
```

---

# Context Payload Fields

| Field          | Description                     |
| -------------- | ------------------------------- |
| `source_type`  | MUST be `context`               |
| `context_type` | Context category                |
| `metric`       | Optional metric name            |
| `service`      | Optional related service        |
| `value`        | Optional numeric value          |
| `text`         | Optional human-readable context |

---

# Anomaly Events

Anomaly events represent detector outputs.

---

## Example

```json
{
  "event_id": "uuid",
  "event_type": "AnomalyDetected",
  "source": "deviation-detector-service",
  "occurred_at": "2026-06-02T12:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {
    "anomaly_type": "spike",
    "metric": "api_latency_ms",
    "previous_value": 178,
    "current_value": 420,
    "change_amount": 242,
    "reason": "value increased significantly compared to recent history"
  }
}
```

---

# Anomaly Payload Fields

| Field            | Description                  |
| ---------------- | ---------------------------- |
| `anomaly_type`   | Type of anomaly              |
| `metric`         | Metric name                  |
| `previous_value` | Previous observed value      |
| `current_value`  | Current observed value       |
| `change_amount`  | Numeric delta between values |
| `reason`         | Detector explanation         |

---

# Analysis Events

Analysis events represent semantic interpretation results.

---

## Example

```json
{
  "event_id": "uuid",
  "event_type": "AnalysisGenerated",
  "source": "analyzer-service",
  "occurred_at": "2026-06-02T12:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {
    "summary": "SEZRA detected a spike anomaly...",
    "human_readable": {
      "title": "Spike anomaly detected",
      "detected_anomaly": "Metric changed from 178 to 420",
      "most_relevant_context": "CPU usage was 94%",
      "possible_interpretation": "High CPU usage may explain increased latency"
    },
    "related_contexts": []
  }
}
```

---

# Exchange Conventions

| Exchange                | Purpose                   |
| ----------------------- | ------------------------- |
| `sezra.stream.raw`      | Raw incoming events       |
| `sezra.stream.anomaly`  | Detector outputs          |
| `sezra.stream.analysis` | Semantic analysis outputs |

---

# Component Descriptor

SEZRA components MAY provide a local `component.json` descriptor file.

The descriptor contains metadata, runtime configuration, and messaging topology information for a component.

The descriptor is intentionally simple and language-agnostic.

SEZRA favors:

```text
local descriptors over centralized frameworks
copyable blueprints over mandatory SDKs
contracts over runtime coupling
```

---

## Example

```json
{
  "id": "deviation-detector",
  "display_name": "Deviation Detector",
  "version": "1.0.0",
  "detector_type": "statistical",
  "supported_anomalies": [
    "spike",
    "drop"
  ],
  "config": {
    "min_history_size": 3,
    "stddev_multiplier": 2,
    "max_history_size": 50
  },
  "rabbitmq": {
    "queue": "sezra.queue.deviation_detector",
    "input_exchange": "sezra.stream.raw",
    "output_exchange": "sezra.stream.anomaly"
  }
}
```

---

# Descriptor Philosophy

Component descriptors are intended to support:

* detector discovery
* marketplace metadata
* future orchestration tooling
* Studio visualization
* capability inspection
* deployment automation
* copyable service blueprints

without introducing runtime coupling between services.

Services MUST remain independently deployable and independently implementable.

---

# Service Independence Rules

SEZRA services MUST remain independently deployable.

Services MUST:

* communicate only through events
* own their internal implementation
* avoid direct runtime dependencies on other services

Services MAY:

* use different programming languages
* use different internal architectures
* use optional helper SDKs or blueprints

Services MUST NOT:

* directly import internal code from other services
* tightly couple to another service runtime
* bypass event contracts

---

# Blueprint Philosophy

SEZRA favors:

```text
Blueprints over mandatory SDKs
Contracts over shared runtime dependencies
Hyper-decoupled services over centralized frameworks
```

The recommended approach for new service development is:

```text
copy a service blueprint
adapt implementation
preserve event contracts
```

instead of depending on centralized runtime libraries.

---

# Future Extensions

Future SEZRA versions may introduce:

* JSON schema validation
* service capability manifests
* flow definitions
* component registries
* detector marketplaces
* adapter marketplaces
* Studio orchestration metadata
* optional language-specific SDKs

while preserving the core hyper-decoupled architecture.
