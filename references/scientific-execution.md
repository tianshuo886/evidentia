# Scientific Execution Architecture

Evidentia v1.0 establishes an absolute architectural boundary between deterministic orchestration and scientific reasoning:

```text
Deterministic Code (Python)          Host Agent (LLM / Reasoner)
---------------------------          ---------------------------
- PDF text & visual extraction       - Paper interpretation
- ID generation & hashing            - Claim formulation
- State machine advancement          - Lens critical rereading
- Schema validation                  - Semantic reconciliation
- Evidence bundle generation         - Localized verification
- Fail-closed freeze checks          - Transfer analysis & Apply
- Database indexing & HTML rendering
```

## Non-Negotiable Invariants

1. **Source Before Interpretation**: No scientific statement may be formed without concrete grounding in reconstructed source objects (pages, sections, figures, tables, equations, mentions).
2. **Deterministic Code Never Invents Science**: Production execution code is strictly prohibited from containing hardcoded scientific conclusions, templates, or manufactured numbers.
3. **Host-Agnostic Execution**: Standard Mode executes fully on any compatible single model/host (Codex, Claude Code, Pi) using standard JSON task packets.
4. **Project Invisibility during Reading**: Open Reading has zero access to project documents, project goals, or long-term research memory.
