# SEZRA Blueprints

SEZRA blueprints are copyable starting points for building custom components.

They are intentionally not SDKs.

A blueprint is meant to be copied, modified, owned, and deployed independently.

---

# Why Blueprints?

SEZRA follows a hyper-decoupled architecture.

Components should not need to compile against SEZRA, import SEZRA runtime code, or depend on a shared framework.

They only need to speak SEZRA events.

```text
Contracts over runtime coupling
Blueprints over mandatory SDKs
Protocol over framework
```

---

# Available Blueprints

```text
blueprints/
├── adapters/
│   └── python/
└── detectors/
    └── python/
```

---

# Component Types

| Type     | Purpose                                           |
| -------- | ------------------------------------------------- |
| Adapter  | Translates external systems into SEZRA events     |
| Detector | Transforms SEZRA observations into anomaly events |

---

# Recommended Workflow

```text
copy blueprint
replace placeholders
modify implementation
preserve event contracts
deploy independently
```

---

# Philosophy

Code duplication is acceptable.

Runtime coupling is not.

Blueprints keep components:

* easy to understand
* easy to replace
* easy to implement
* easy to rewrite in another language
* independently deployable

Future SEZRA tooling may generate components from these blueprints, but generated components should remain fully independent.

---

# Language Agnostic by Design

SEZRA components may be implemented in:

* Python
* Go
* .NET
* Java
* Rust
* Node.js
* C++
* or any other language

The only requirement is compatibility with documented SEZRA event contracts.

---

# Hyper-Decoupled Architecture

SEZRA intentionally avoids centralized runtime dependencies between services.

Each component owns:

* its own runtime
* its own dependencies
* its own deployment lifecycle
* its own implementation details

This enables:

* massive parallel development
* easy mocking
* independent deployments
* low integration friction
* simplified experimentation
* long-term maintainability

---

# Blueprint Goal

Blueprints exist to reduce friction.

Developers should be able to:

```text
copy
modify
run
experiment
```

without spending days fighting:

* dependency injection
* framework bootstrapping
* shared runtime libraries
* complex build systems
* centralized orchestration frameworks

---

# Future Direction

Future SEZRA tooling may include:

* component generators
* marketplace integrations
* Studio orchestration
* descriptor validation
* flow visualization
* blueprint registries

while preserving the core philosophy:

```text
hyper-decoupled services
connected through contracts and events
```
