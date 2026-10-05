# Evaluation Framework & Benchmark Architecture

Evidentia strictly separates deterministic software engineering correctness from empirical scientific quality validation.

## Empirical Validation: Issue #19 Formal Real-Paper A/B Benchmark

The canonical empirical release gate is established by the formal post-freeze A/B benchmark (**GitHub Issue #19**), frozen at commit `4139ca7b0b1ae72c0930801df5e50653b59a7e92`:

- **Canonical Model:** `antigravity/gemini-3.8-flash [magpie]` (High Reasoning Profile).
- **Primary 6-Paper Corpus:**
  - `BENCH-01`: Attention Is All You Need (ML Foundational)
  - `BENCH-02`: LoRA (PEFT / Serving)
  - `BENCH-03`: Canopy Height Model (Remote Sensing)
  - `BENCH-04`: AlphaFold2 (Biophysics & Geometric DL)
  - `BENCH-05`: Quantum Supremacy (Quantum Metrology)
  - `UNSEEN-01`: Rethinking Generalization (Mandatory Post-Freeze Unseen Paper)
- **Experimental Conditions:**
  - **Condition A (Direct Gemini):** Unassisted strong-model deep reading of the authentic PDF using a frozen publication-grade prompt.
  - **Condition B (Evidentia Reader v3):** Full frozen Reader v3 pipeline (Lead Reader → 4 Core + 2 Adaptive Lenses → Revision Memo → Dynamic Narrative Plan → Lead Writer → Kami Presentation & Evidence Atlas).
- **Blinded Evaluation:** Anonymized packets (`REPORT X` vs `REPORT Y`) with mirrored order swaps to eliminate position bias.
- **Outcome:** **`ISSUE19_RELEASE_GATE = PASS`** (0 core regressions across 18 trials; 6/6 wins on figures and provenance; zero template bias). See `ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md`.

## Deterministic Engineering Tiers

### Tier 0 — Deterministic Correctness (CI Gate)
- Validates all artifacts against JSON Schema Draft 2020-12.
- Enforces cryptographic SHA-256 evidence chain and fail-closed trust boundaries.
- Rejects post-freeze tampering and unverified visual assets.

### Tier 1 — Synthetic Integration
- Tests orchestration state machines, intent isolation, and pipeline plumbing using synthetic test fixtures (`reader_v3_fixture.py`, `is_fixture_enabled()`).
- Clearly labeled as `SYNTHETIC_ONLY` in the capability matrix; never used as empirical quality claims.

### Tier 2 — Recorded Replay Execution
- Replays recorded Host Agent result envelopes to test protocol stability and schema backward compatibility.
