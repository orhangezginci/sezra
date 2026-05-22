# SEZRA

Autonomous event-driven orchestration and causal discovery engine.
## RabbitMQ Exchange Convention

SEZRA uses RabbitMQ fanout exchanges for event distribution.

Initial exchanges:

| Exchange | Type | Purpose |
|---|---|---|
| `sezra.raw.events` | `fanout` | Normalized incoming data events from adapters |
| `sezra.anomaly.events` | `fanout` | Anomaly events produced by detector services |
| `sezra.analysis.events` | `fanout` | Causal analysis result events produced by analyzer services |

All messages use the public `EventEnvelope` JSON contract:

```text
contracts/event_envelope.schema.json

## Development

Python-only v0.1.

Internal communication:
- RabbitMQ fanout events

Persistent history:
- PostgreSQL event store

Vector search:
- Qdrant

Local AI:
- Ollama