# Generic Host-Agent Task Protocol

Evidentia communicates with host models through standardized JSON task packets, decoupling scientific reasoning from any specific model SDK.

## Task Protocol Flow

```text
Core State (SOURCE_LOCK)
    │
    ▼
Core generates `tasks/open_reading.json` (agent_task schema)
    │
    ▼
State: WAITING_FOR_AGENT
    │
    ▼
Host Agent reads packet + `evidence_bundles/`
    │
    ▼
Host Agent writes result (`agent_result_envelope` schema)
    │
    ▼
Submission via CLI: `evidentia submit --task <id> --result <file>`
    │
    ▼
Core validates schema, provenance, hashes → Advances State
```

## Schemas

- `schemas/agent_task.schema.json`: Declares `task_id`, `task_type`, `required_capability`, `input_artifacts`, `localized_evidence`, `output_schema`, and `prohibited_context`.
- `schemas/agent_result_envelope.schema.json`: Encapsulates output with full executor metadata (`kind`, `host`, `model`, timestamps).
