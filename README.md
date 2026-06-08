# SEZRA

**Operational events are meaningless in isolation. SEZRA turns them into context-aware reasoning.**

SEZRA is a semantic event reasoning engine built for modern distributed systems.

Instead of only detecting anomalies, SEZRA correlates operational events with surrounding contextual signals to generate human-readable analysis and semantic operational insight.

Feed SEZRA with metrics, logs, context events, CI/CD events, infrastructure signals, or custom business events — and let semantic reasoning emerge across your event streams.

---

# Clone. Run. Experience SEZRA.

https://github.com/user-attachments/assets/e697617a-ac33-48a5-bc0b-bd4c4ee9cde9

```bash
git clone https://github.com/orhangezginci/sezra.git
cd sezra
docker compose up -d
```

Run the demo:

```bash
./scripts/demo-metric-context.sh
```

Fetch the latest generated analysis:

```bash
curl http://localhost:8000/analyses/latest
```

**Example output:**

```text
SEZRA Analysis

Anomaly:
API latency spiked from 178ms to 420ms.

Likely context:
CPU usage for checkout-api was 94%.

Interpretation:
The latency spike may be related to high CPU usage on the same service.
```

---

# What Is SEZRA?

SEZRA is not just another anomaly detector.

It is built around the idea that operational events gain meaning through **semantic context**.

Instead of treating events as isolated signals, SEZRA correlates anomalies with surrounding operational context to generate higher-level operational understanding.

SEZRA works across:

* Metrics
* Logs
* Infrastructure signals
* CI/CD events
* Operational telemetry
* Custom business events
* Semantic context streams

It runs locally with Docker Compose, fully headless, in Kubernetes, inside CI/CD pipelines, or as part of larger platforms.

---

# Architecture

SEZRA is intentionally simple and **hyper-decoupled**.

**No shared runtime library. No hidden coupling. No mandatory SDK.**

Every service follows the same contract:

```text
consume events → process events → publish events
```

```mermaid
flowchart TD

    %% =========================
    %% STYLES
    %% =========================
    classDef external fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#0f172a
    classDef bus fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#052e16
    classDef detector fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef semantic fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#431407
    classDef storage fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#500724
    classDef core fill:#ccfbf1,stroke:#0f766e,stroke-width:2px,color:#042f2e
    classDef api fill:#ecfccb,stroke:#65a30d,stroke-width:2px,color:#1a2e05
    classDef legend fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#0f172a

    %% =========================
    %% EXTERNAL INPUTS
    %% =========================
    subgraph External["🌍 External Sources"]
        ADAPTER["JSON File Adapter<br/>+ Future Adapters"]
        EXTERNAL["Metrics / Logs / CI-CD<br/>Infra Events"]
    end

    %% =========================
    %% EVENT BUS
    %% =========================
    RABBIT["🐰 RabbitMQ<br/>Event Fabric"]

    %% =========================
    %% DETECTORS
    %% =========================
    subgraph Detectors["🔍 Anomaly Detectors"]
        SPIKE["Spike Detector"]
        DROP["Drop Detector"]
    end

    %% =========================
    %% SEMANTIC LAYER
    %% =========================
    subgraph Semantic["🧠 Semantic Layer"]
        EMBED["Embedding Service"]
        QDRANT["Qdrant<br/>Vector Store"]
    end

    %% =========================
    %% CORE PROCESSING
    %% =========================
    ANALYZER["Analyzer Service<br/>Semantic Reasoning"]

    %% =========================
    %% STORAGE
    %% =========================
    subgraph Storage["💾 Storage"]
        EVENTSTORE["Event Store"]
        PG["PostgreSQL<br/>Event Store"]
    end

    %% =========================
    %% OUTPUT
    %% =========================
    API["REST API"]

    %% =========================
    %% FUTURE
    %% =========================
    STUDIO["SEZRA Studio"]

    %% =========================
    %% LEGEND
    %% =========================
    subgraph Legend["Legend"]
        L1["External Sources"]
        L2["Event Fabric"]
        L3["Processing Services"]
        L4["Storage"]
    end

    %% =========================
    %% DATA FLOW
    %% =========================
    EXTERNAL -->|"raw events"| ADAPTER
    ADAPTER -->|"publish"| RABBIT

    RABBIT -->|"observe"| SPIKE
    RABBIT -->|"observe"| DROP
    RABBIT -->|"embed"| EMBED

    SPIKE -->|"anomalies"| RABBIT
    DROP -->|"anomalies"| RABBIT

    EMBED -->|"embeddings"| QDRANT

    RABBIT -->|"anomaly events"| ANALYZER
    QDRANT -->|"semantic context"| ANALYZER

    ANALYZER -->|"analyses"| RABBIT

    RABBIT -->|"persist"| EVENTSTORE
    EVENTSTORE --> PG

    API -->|"query"| PG
    API -->|"semantic search"| QDRANT
    API -->|"live events"| RABBIT

    STUDIO -->|"visual workflows"| API

    %% =========================
    %% APPLY STYLES
    %% =========================
    class External external
    class RABBIT bus
    class SPIKE,DROP detector
    class Semantic,EMBED,QDRANT semantic
    class Storage,PG,EVENTSTORE storage
    class ANALYZER core
    class API api
    class Legend,L1,L2,L3,L4 legend
```

SEZRA services are independently deployable and replaceable.

A detector can be written in Python, an adapter in Go, an enricher in Rust — as long as they speak SEZRA events, they belong in the system.

---

# Current MVP Features

* Semantic anomaly analysis
* Context-aware event correlation
* Human-readable operational reasoning
* RabbitMQ event fabric with proper envelopes
* PostgreSQL event store
* Qdrant semantic vector search
* REST API
* Dead-letter event persistence
* Failure classification
* Envelope validation
* Runtime health checks
* Docker Compose deployment
* Hyper-decoupled services

---

# Example Use Cases

* Correlate application latency spikes with infrastructure signals
* Enrich operational telemetry with semantic context
* Analyze CI/CD failures
* Process business events semantically
* Run headless operational reasoning pipelines

---

# SEZRA Studio

SEZRA Studio will be the official visual interface for the SEZRA engine — a visual pipeline builder that follows the same hyper-decoupled and semantic-first philosophy.

The engine itself remains fully usable without Studio.

---

# Roadmap

## Near-term

* Statistical baseline detectors
* Additional adapters & enrichers
* Improved semantic reasoning
* Public demo environment

## Long-term

* Visual pipeline orchestration (Studio)
* Plugin ecosystem
* Advanced reasoning services
* Enterprise integrations

---

# Philosophy

Operational systems already produce enormous amounts of events.

The missing piece is **semantic understanding**.

SEZRA exists to transform isolated operational signals into contextual, human-understandable operational reasoning.
