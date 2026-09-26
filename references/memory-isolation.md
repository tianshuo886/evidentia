# Open Reading Memory Firewall

To prevent confirmation bias, Evidentia enforces strict technical isolation between past research memory and the reading of a new paper.

## Isolation Policy

During the following workflow phases:
- `SOURCE_RECONSTRUCTION`
- `SOURCE_LOCK`
- `OPEN_READING`
- `BASELINE_LOCK`
- `LENS_EXECUTION`

The long-term research memory directory and database are completely inaccessible to the Host Agent.

## Technical Enforcement

`memory_manager.py` provides `enforce_open_reading_firewall()`:
1. Rejects any task packet that lacks `RESEARCH_MEMORY` in its `prohibited_context`.
2. Rejects any task packet whose `input_artifacts` contains memory paths or database files.
3. Quantifies `open_reading_contamination_rate` during evaluation (Critical Invariant: MUST BE 0.0).

Memory retrieval is permitted only after `FINAL_FREEZE` during Stage B of Apply or explicit cross-paper synthesis.
