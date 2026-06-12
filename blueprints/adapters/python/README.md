# SEZRA Python Adapter Blueprint

## Overview

This blueprint provides a minimal Python-based SEZRA adapter service.

Adapters translate external systems and external data sources into standardized SEZRA events.

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
modify external integration logic
preserve SEZRA event contracts
deploy independently
```

Adapters communicate with SEZRA exclusively through RabbitMQ event streams.

No internal SEZRA runtime dependencies are required.

---

# Included Files

| File               | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `main.py`          | Adapter runtime implementation               |
| `component.json`   | Component metadata and runtime configuration |
| `requirements.txt` | Python dependencies                          |
| `Dockerfile`       | Container build definition                   |
| `README.md`        | Blueprint documentation                      |

---

# Placeholder Variables

The following placeholders must be replaced before use.

| Placeholder        | Description                 |
| ------------------ | --------------------------- |
| `{{COMPONENT_ID}}` | Unique component identifier |
| `{{SERVICE_NAME}}` | Runtime service name        |
| `{{DISPLAY_NAME}}` | Human-readable adapter name |

Example:

```json
{
  "id": "sap-order-adapter",
  "service_name": "sap-order-adapter-service",
  "display_name": "SAP Order Adapter"
}
```

---

# Environment Variables

The adapter expects the following environment variables.

| Variable            | Description       |
| ------------------- | ----------------- |
| `RABBITMQ_HOST`     | RabbitMQ hostname |
| `RABBITMQ_PORT`     | RabbitMQ port     |
| `RABBITMQ_USER`     | RabbitMQ username |
| `RABBITMQ_PASSWORD` | RabbitMQ password |

---

# Running The Adapter

## Local Python Execution

```bash
pip install -r requirements.txt
python main.py
```

---

## Docker Build

```bash
docker build -t my-adapter .
```

---

## Docker Run

```bash
docker run \
  -e RABBITMQ_HOST=localhost \
  -e RABBITMQ_PORT=5672 \
  -e RABBITMQ_USER=guest \
  -e RABBITMQ_PASSWORD=guest \
  my-adapter
```

---

# Adapter Responsibility

Adapters are responsible for:

```text
external system → SEZRA event
```

Adapters do NOT perform semantic analysis.

Adapters do NOT directly depend on internal SEZRA services.

Adapters only translate external data into standardized SEZRA event envelopes.

---

# Adapter Extension Points

The following functions are intended to be modified by adapter developers.

---

## read_external_input()

Reads data from an external system or source.

Example sources:

* JSON files
* Excel files
* IMAP email inboxes
* REST APIs
* Webhooks
* Databases
* Monitoring systems
* Message queues

---

## transform_to_sezra_event()

Maps external data into standardized SEZRA event envelopes.

The adapter MUST preserve the SEZRA event contract structure.

---

## publish_event()

Publishes standardized SEZRA events to RabbitMQ streams.

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

* adapter marketplaces
* detector marketplaces
* Studio orchestration tooling
* component registries
* deployment automation
* optional SDKs

while preserving the core hyper-decoupled architecture.
