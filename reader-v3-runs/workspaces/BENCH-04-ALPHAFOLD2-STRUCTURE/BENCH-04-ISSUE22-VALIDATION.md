# BENCH-04 Issue #22 Reader v3 Validation

## Identity and provenance

- Paper/workspace: `BENCH-04-ALPHAFOLD2-STRUCTURE`
- Source SHA-256: `6eae057a9faf4f671c3101e0745ed704460c6d3dec77243dfd3a9f2d2ab68970`
- Immutable code candidate verified before execution: `d7f32ad690a51eec5bcaac19bd64a25eec866d4d`
- Final `reader/narrative_manuscript.json` SHA-256: `b602293bc12f0ce5b795f0d40530098dafe92e1e2fe36b0fa26910ba8dc8ff48`
- Run provenance: `agent_runs/TASK-V3-READER-VALIDATION/run-001.json`
- Reused direct baseline: `agent_runs/TASK-V3-DIRECT-BENCH-04-ALPHAFOLD2-STRUCTURE/run-001.json` (source hash, task identity, schema, contract version and paper-only provenance validated).

## Completed canonical stages

1. Semantic visual verification: full-page checks verified F01–F05 and rejected phantom T01; Fig. 1's former partial Templates crop was replaced by a full multi-panel crop.
2. Lead Reader: `model/paper_understanding_draft.json`.
3. Four core lenses: Argument & Narrative, Method & Study Design, Evidence & Results, Validity & Boundary.
4. Two adaptive lenses: Mechanism & Causality and Reproducibility & Implementation. Each output was independently checkpointed and no Lens consumed another Lens output.
5. Revision Memo: `model/revision_memo.json`.
6. Dynamic Narrative Plan: `model/narrative_plan.json`.
7. Lead Writer: `reader/narrative_manuscript.json`.
8. Source-grounded v3 integrity: PASS (`reader/source_grounded_integrity.json`; zero v3 integrity errors).
9. Rendered HTML, Markdown, PDF and Evidence Atlas are present under `reader/`.

## Final section titles/order

1. 先看作者究竟证明了什么
2. 从MSA到三维结构：一个耦合的表示系统
3. 网络如何被训练，又如何被观察
4. 消融把架构主张变成可检验的比较
5. 成功依赖什么：MSA深度与跨链接触
6. 讨论：高精度预测的边界与用途

## AlphaFold paper's actual explanatory/argumentative structure

The paper first establishes its empirical claim with blind CASP14 performance, representative structures, recent-PDB transfer, and confidence calibration. It then opens the system: MSA and residue-pair representations circulate through Evoformer triangle operations, and a frame-based structure module with IPA/FAPE performs geometric refinement. Training choices, ablations, and intermediate trajectories make the architecture experimentally inspectable. Finally, the paper analyzes MSA depth and cross-chain contacts, then discusses PDB-conditioned scope and biological use. This is a layered empirical case, not a generic problem→gap→method→experiments→results→limitations template.

## Generic template leakage and integrity

- Generic template leakage: none detected in primary narrative; section identifiers are paper-specific and no fixed universal chapter titles were used.
- Internal Reader/Lens vocabulary leakage: none detected in primary narrative.
- Narrative manuscript schema: PASS.
- Lead Reader, all six Lens outputs, Revision Memo and Dynamic Narrative Plan schemas: PASS.
- Section order preserves the Dynamic Narrative Plan: PASS.
- Source evidence references and visual asset existence: PASS.
- Source-grounded integrity report: PASS.

## Is the Reader shaped by this paper or by Evidentia?

**Answer: shaped by this paper.** Evidentia determines the disciplined reading protocol, evidence binding and integrity gates, but the resulting Reader follows AlphaFold's own explanatory sequence—benchmark claim, coupled representations and geometry, training/trajectory interpretation, ablations, MSA/contact boundaries, and PDB-conditioned discussion. It does not force the paper into a reusable generic outline.
