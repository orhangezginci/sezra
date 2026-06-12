# SEZRA Python Detector Blueprint

## Overview

This blueprint provides a minimal Python-based SEZRA detector service.

The blueprint is intentionally simple and fully self-contained.

It is designed to be:

* copyable
* independently deployable
* easy to modify
* framework-independent
* hyper-decoupled

The recommended workflow is:

```bash
copy blueprint
modify logic
preserve event contracts
deploy independently
```

This blueprint communicates with the SEZRA ecosystem exclusively through RabbitMQ event streams.

No internal SEZRA runtime dependencies are required.

---

# Included Files

| File               | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `main.py`          | Detector runtime implementation              |
| `component.json`   | Component metadata and runtime configuration |
| `requirements.txt` | Python dependencies                          |
| `Dockerfile`       | Container build definition                   |
| `README.md`        | Blueprint documentation                      |

---

# Placeholder Variables

The following placeholders must be replaced before use.

| Placeholder        | Description                  |
| ------------------ | ---------------------------- |
| `{{COMPONENT_ID}}` | Unique component identifier  |
| `{{SERVICE_NAME}}` | Runtime service name         |
| `{{DISPLAY_NAME}}` | Human-readable detector name |

Example:

```json
{
  "id": "latency-spike-detector",
  "service_name": "latency-spike-detector-service",
  "display_name": "Latency Spike Detector"
}
```

---

# Environment Variables

The detector expects the following environment variables.

| Variable            | Description       |
| ------------------- | ----------------- |
| `RABBITMQ_HOST`     | RabbitMQ hostname |
| `RABBITMQ_PORT`     | RabbitMQ port     |
| `RABBITMQ_USER`     | RabbitMQ username |
| `RABBITMQ_PASSWORD` | RabbitMQ password |

---

# Running The Detector

## Local Python Execution

```bash
pip install -r requirements.txt
python main.py
```

---

## Docker Build

```bash
docker build -t my-detector .
```

---

## Docker Run

```bash
docker run \
  -e RABBITMQ_HOST=localhost \
  -e RABBITMQ_PORT=5672 \
  -e RABBITMQ_USER=guest \
  -e RABBITMQ_PASSWORD=guest \
  my-detector
```

---

# Detector Extension Points

The following functions are intended to be modified by detector developers.

---

## should_process()

Defines whether an incoming event should be processed.

Example use cases:

* filter metrics
* filter services
* filter event types
* filter observation categories

---

## detect_deviation()

Contains the core anomaly detection logic.

Example implementations:

* spike detection
* drop detection
* moving averages
* z-score analysis
* threshold detection
* ML-based scoring
* custom statistical models

---

## create_anomaly_event()

Defines the anomaly payload structure and explanation text.

Developers may customize:

* anomaly types
* explanations
* metadata
* detector-specific payload fields

while preserving the SEZRA event envelope contract.

---

# Event Contracts

All SEZRA services communicate exclusively through standardized event envelopes.

See:

```text
docs/event_contract.md
```

The event contract is the interoperability layer of SEZRA.

Services MUST communicate only through documented events.

---

# Hyper-Decoupled Architecture

SEZRA intentionally avoids centralized runtime frameworks.

Services:

* MUST remain independently deployable
* MUST communicate only through events
* MUST NOT directly depend on internal service code
* MAY use different programming languages and frameworks

SEZRA favors:

```text
Blueprints over mandatory SDKs
Contracts over runtime coupling
Hyper-decoupled services over centralized frameworks
```

---

# Recommended Workflow

```text
copy blueprint
adapt implementation
preserve contracts
deploy independently
```

instead of depending on shared runtime frameworks.

---

# Future Ecosystem

Future SEZRA versions may introduce:

* detector marketplaces
* adapter marketplaces
* Studio orchestration tooling
* component registries
* optional SDKs
* deployment automation

while preserving the core hyper-decoupled architecture.
