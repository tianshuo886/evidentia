# BENCH-05 Issue #22 validation note

- **Benchmark:** `BENCH-05-QUANTUM-SUPREMACY-ABLATION`
- **Paper:** Arute et al., “Quantum Supremacy Using a Programmable Superconducting Processor” (Nature, 2019)
- **Source SHA-256:** `6f3030abb7d9d4f0624a5cbe5ca2ff673df63afc85c97fadd0bf7db780c8dbaf`
- **Immutable code candidate:** `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` (checked out and verified before execution)
- **Final manuscript SHA-256:** `869977cb403b2d23a04a44e371d3669212232cef93993be2ce0913db5ffbb9c1`
- **Reader contract:** v3.0; Lead Writer prompt v3.1; source policy `REAL_PUBLIC_FULL_PDF_ONLY`
- **Run/task provenance:** canonical workspace `reader-v3-runs/workspaces/BENCH-05-QUANTUM-SUPREMACY-ABLATION`; recovered source-matched visual, Lead Reader, six context-isolated Lens outputs, Revision Memo, and Dynamic Narrative Plan from accessible async workspace; Lead Writer persisted as `agent_runs/TASK-V3-LEAD-WRITING/run-001.json` under this validation run. The original task records are `TASK-V3-LEAD-READING`, `TASK-V3-LENS-{ARGUMENT_NARRATIVE,EVIDENCE_RESULTS,MEASUREMENT_INTEGRITY,MECHANISM_CAUSALITY,METHOD_STUDY_DESIGN,VALIDITY_BOUNDARY}`, `TASK-V3-REVISION-MEMO`, and `TASK-V3-NARRATIVE-PLAN`.

## Canonical pipeline evidence

1. Semantic visual verification: `visual/page-002.json` through `visual/page-005.json`; manifest `model/visual_v3_manifest.json`.
2. Lead Reader: `model/paper_understanding_draft.json`.
3. Six independent specialist outputs: `lens_v3/*.json`; manifest `model/lens_v3_manifest.json`.
4. Revision Memo: `model/revision_memo.json`.
5. Dynamic Narrative Plan: `model/narrative_plan.json`.
6. Lead Writer: `reader/narrative_manuscript.json`.
7. Source-grounded integrity validation: `reader/source_grounded_integrity.json` (`PASS`).
8. Rendered final Reader: `reader/paper_reader.html`, `reader/paper_reader.md`, `reader/paper_reader.pdf`; provenance atlas `reader/evidence_atlas.html` and `reader/evidence_atlas.json`.

## Final section sequence and actual scientific argument

The nine sections are paper-shaped rather than universal slots:

1. **起点：两个问题与一个里程碑** — frames the two engineering/complexity questions and limits the claim to a task-specific milestone.
2. **选定任务与度量标尺** — defines random circuit sampling and F_XEB, while exposing that the verification metric itself depends on classical probabilities.
3. **打造仪器：Sycamore 与高保真门** — establishes the 54-position/53-used-qubit device and the system-level parallel-operation premise.
4. **读取仪器误差：从逐项误差到乘法模型** — measures local/system error rates and introduces the scale-up product model as a load-bearing assumption.
5. **关键一跃：让不可测者变得可测** — explains patch/elided/verification circuits and why Fig. 4a is the method-validating control.
6. **测量本身：霸权读数** — reports the 53-qubit, 20-cycle estimate `F_XEB=(2.24±0.21)×10^-3`, explicitly distinguishing it from a directly recomputed full hard circuit.
7. **对位：经典代价的外推** — places the ~200 s quantum runtime against a same-task, same-fidelity classical resource estimate, making the “~10,000 years” figure an extrapolation rather than a completed direct run.
8. **为何不是伪信号：数字化误差模型与可证伪性** — connects interference/error structure to the product model and states falsifiers.
9. **边界与未决：它证明了什么、没证明什么** — preserves task specificity, non-fault-tolerant status, extrapolation uncertainty, and the inability to independently recompute the hardest distribution end-to-end.

The actual argument is therefore a **verification ladder**: instrument → local error characterization → product model → simplification estimator → controlled estimator validation → hard-circuit quantum estimate → classical cost extrapolation → explicit validity boundaries. It is not a generic problem/gap/method/result/limitation narrative.

## Evidence boundaries and verification limits

- Source PDF is the seven-page real paper only; all stage artifacts carry the same source SHA.
- Fig. 1–4 assets are vision-verified crops, and page visual outputs are retained.
- `F_XEB` on the hardest circuit is an estimate whose method is validated on a simulable control family; it is not a direct evaluation of every ideal output probability.
- The classical “~10,000 years” comparison is algorithm/resource extrapolation from simulable regimes, not a literal completed run.
- The full hardest-circuit data are archived but not independently recomputed by this validation.
- The Pauli/digitalized error model’s validity domain and correlated-error behavior remain open.
- The manuscript’s schema, plan order, source references, local assets, output files, stage completeness, and internal-vocabulary firewall all passed `reader/source_grounded_integrity.json`.

## Issue #22 template-bias assessment

No universal slot sequence was imposed: the manuscript follows the paper’s own replacement/verification ladder, gives the estimator-validation control its own section, and separates measured device facts, controlled estimates, and cost extrapolations. The only visible template-like symptom is editorial repetition around Fig. 4, because that single source figure genuinely carries both estimator validation and the headline comparison; the repetition is labeled by question and does not collapse the two evidentiary roles. A second mild symptom is the recurring “what this does/does not prove” callout style, used here to preserve the paper’s unusually important verification boundaries rather than to inject generic limitation boilerplate.

**Answer — Is the Reader shaped by this paper or by Evidentia?** It is shaped primarily by this paper. The nine-section order follows the paper’s verification ladder and its load-bearing estimator validation; Evidentia contributes the provenance discipline, explicit uncertainty labels, visual binding, and anti-template checks, but it does not supply the scientific story or force a canonical section architecture.

## Durable artifact status

`reader/narrative_manuscript.json` and this note are durably persisted in the canonical BENCH-05 workspace. No Reader v3 scientific contracts, Kami/Workspace/Agentero components, Issue #19/#20 formal benchmark, unseen-paper selection, or PR #26 merge were changed or started.
