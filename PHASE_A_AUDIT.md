# Phase A — Correctness Foundation: completion audit

Scope: `~/.agents/skills/evidentia` (cwd-adjacent skill repo; `evidentia-skill`
symlink in cwd points here). Verified 2026-09-25 with system python3
(`pip install -r requirements.txt`, `python -m pytest -q` → 25 passed (`python` shims to system python3.9 via `~/.local/bin/python`)).

## 1. Schema migration (§7)
- All 13 `schemas/*.schema.json` `$id` migrated to the
  `github.com/tianshuo886/evidentia/blob/main/schemas/...` namespace.
- `run_state.schema.json` `mode` enum is now `["evidentia"]`, matching
  `scripts/init_run.py` output (`mode: evidentia`). `init_run.py` output
  validates with zero `schema_validate(..., 'run_state')` errors.
- Legacy-name grep over `schemas/ scripts/ tests/ SKILL.md references/`
  returns no hits (only README migration notes remain, by design).

## 2. Source SHA content-address chain (§5)
- `source_map.pdf_sha256`, `figure_inventory.source_sha256` (writer:
  `extract_figs.py` via `validate_common.sha256`), `paper_model.source_sha256`
  (+`paper.pdf_sha256`), `evidence_graph.source_sha256` (writer:
  `build_graph.py`), every `lens/*.json` `source_sha256`
  (writer: `lens_runner.py`).
- `freeze_check.py` compares each against `sha256(source/paper.pdf)` and
  FAILs CLOSED on any mismatch; missing chain fields also fail.
- Negative evidence: `source/paper.pdf` tampered → `freeze_check` rc=1 with
  `source_map.pdf_sha256 mismatch ... (wrong or changed PDF)` (+ inventory /
  model / graph mismatches).

## 3. Open Reading Base vs Final Model (§6)
- New: `scripts/snapshot_baseline.py` →
  `model/open_reading_model.json` (byte copy of the Open Reading draft) +
  `model/open_reading_manifest.json` (`source_sha256`, `base_model_sha256`,
  `lens_contract_version`, `prompt_version`; schema:
  `schemas/open_reading_manifest.schema.json`).
- `lens_runner.py` prefers `open_reading_model.json` as lens base, records
  `source_sha256/base_sha256/lens_contract_version/prompt_version/executor`.
- `check_lenses.py` + `freeze_check.py` refuse lenses whose `base_sha256 !=
  open_reading_manifest.base_model_sha256` (stale baseline) and whose
  `source_sha256 != actual PDF` (wrong-paper lens). `freeze_check.py` also
  refuses a mutated `open_reading_model.json` (hash vs manifest).
- `phase.py` OPEN_READING gate requires the baseline snapshot + schema-valid
  manifest; LENS gate requires `lens_reconciliation.json`.
- Negative evidence: stale `base_sha256` → `check_lenses` rc=1
  (`base_sha256 mismatch (stale baseline ...)`); mutated baseline →
  `freeze_check` rc=1 (`open_reading_model.json hash mismatch manifest
  (changed baseline)`).

## 4. Reconciliation provenance (§17, back-ends §14/16 data shape)
- `merge_lenses.py` converges identical `(statement, evidence)` findings into
  ONE item keeping ALL `supporting_lenses` + `supporting_findings`
  (`model/lens_reconciliation.json`, schema:
  `schemas/lens_reconciliation.schema.json`); multi-lens items marked
  `AGREEMENT`; same-evidence/distinct-statement groups recorded in
  `paper_model.lens_conflicts` as TENSION (no majority voting anywhere).
- `validate_model.py` fails `reconciliation provenance loss` on empty
  `from_lens` and fails when `lens_conflicts` is missing.
- Positive evidence: `test_merge_preserves_supporting_lenses`
  (reviewer+counterfactual same finding → one item, both lenses, AGREEMENT).

## 5. run_state orchestration (§24)
- `init_run.py` writes schema-valid state (`mode: evidentia`, `source_sha256`
  of input PDF, `completed_phases`, `artifact_hashes`, `executor`, history).
- `phase.py` validates `run_state.json` schema, enforces ORDER, requires
  artifact-exists + schema-valid + hash-recorded + dependency-valid per phase
  (source recon / open reading+baseline / lens+reconciliation / freeze
  re-verify / reader audit), detects source-PDF change on resume, records
  `completed_phases` + per-phase `artifact_hashes`.
- End-to-end: INIT → SOURCE_RECONSTRUCTION → OPEN_READING → LENS → FREEZE
  advances cleanly on a synthetic PDF; `run_state.phase == FREEZE`.
- Negative: resume with changed `source/paper.pdf` → `phase.py` rc=1
  (`source/paper.pdf changed since run start ... refused`); bad-mode
  `run_state.json` → rc=1.

## 6. Normalization (§8)
- `references/normalization.md`: claim-inline O/A/R strings = required short
  summaries; top-level `observations[]/author_interpretations[]/
  reader_assessments[]` = canonical detail; Evidence Graph owns relations;
  source-layer vs interpretation-layer field ownership; inventory (extraction)
  vs model figures/tables (interpretation) with freeze-enforced ID-set
  equality.

## 7. Freeze hardening (§42-freeze subset in Phase-A scope)
- Covered fails: changed PDF, stale/wrong-paper lens, changed baseline,
  dangling ref, missing lens, missing critical asset (pre-existing),
  unverified conflict shape (lens_conflicts required), invalid schema,
  invalid figure `binding_method`, frozen-asset tamper (`verify_frozen.py`
  rc=1), delta-against-tampered-model (`validate_delta.py` rc=1).
- Not in Phase A (later phases): full E2E Standard-Mode auto-read without
  manual `paper_model.json` drafting, ensemble/adaptive escalation, reader
  Evidence Atlas rebuild, evals corpus + CI.

## 8b. Verifier-round hardening (2026-09-26)
- `schemas/lens.schema.json` now **requires** `base_model_sha256` (+ legacy
  `base_sha256`), `lens_contract_version`, `prompt_version`; `check_lenses.py`
  and `freeze_check.py` cross-check all three against
  `open_reading_manifest` (stale/wrong values refused).
- `schemas/lens_task.schema.json` permits the Phase-A task fields
  (`source_sha256/base_sha256/base_model_sha256/lens_contract_version/
  prompt_version/executor`); generated `lens_tasks/*.json` self-validate
  (test `test_lens_task_files_validate_own_schema`).
- `schemas/paper_model.schema.json` `lens_synthesis` items permit `epistemic`
  (what `merge_lenses.py` writes); merge output re-validated in tests.
- `freeze_check.py` schema-validates `open_reading_manifest`,
  **requires** `model/lens_reconciliation.json` (schema + SHA checked), and
  refuses erased conflicts (synthesis items sharing evidence with distinct
  statements but no covering `lens_conflicts` entry).
- `phase.py` enforces pre-recorded `artifact_hashes` (tamper between phases
  refused) and schema-validates the freeze manifest incl. `source_sha256`
  vs actual PDF and `base_model_sha256` vs run-state baseline.
- `python -m pytest -q` works (`python` → system python3.9 shim).

## 8c. Verification surface (all re-runnable)
- `python3 -m pytest -q` → **19 passed** (`tests/test_contracts.py`,
  `tests/test_gates.py` incl. SHA-aware fixture, `tests/test_phase_a.py`:
  generated-JSON self-validation + 17 fail-closed cases + merge provenance).
- CLI smoke: `--help` rc=0 for snapshot_baseline/phase/freeze_check/
  check_lenses/merge_lenses/build_graph/validate_model/verify_frozen/
  validate_delta/source_audit/reader_audit/init_run/ingest/lens_runner.
- Live E2E + 4 negative probes re-run 2026-09-25 (see shell history);
  representative outputs archived in `/tmp/e2e2`, `/tmp/neg1..4`.

## 9. Preservation evidence (untouched surface)
- `scripts/kami_adapter.py` + `references/kami-integration.md` mtimes remain
  the skill baseline (`2026-09-26 00:02`); no core script imports kami
  (`grep -rln kami scripts/*.py` hits only `kami_adapter.py`).
- Six lenses unchanged (`author reviewer mechanism builder anomaly
  counterfactual`); no new lens; no harness-diversity scoring; no majority
  voting (merge records TENSION, never resolves by count); no networked
  paper search touched.

## 10. Preserved constraints
- §1 five principles intact; host-agnostic (no Pi/Codex/Claude特化 in Core);
  six lenses unchanged, no new lens; no harness-diversity scoring; no
  majority voting; Kami untouched; no networked paper search.
