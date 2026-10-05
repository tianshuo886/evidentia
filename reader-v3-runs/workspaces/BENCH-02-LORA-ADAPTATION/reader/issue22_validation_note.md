# BENCH-02 Issue #22 post-validation note

- Benchmark: `BENCH-02-LORA-ADAPTATION`
- Source: `source/paper.pdf` (26-page arXiv v2, LoRA: Low-Rank Adaptation of Large Language Models)
- `SOURCE_SHA256`: `e9a0d3128767db616085dc0f4e6e455e672e89af823e8ed1282793682787395a`
- Immutable code candidate verified before execution: `ISSUE22_VALIDATION_CODE_SHA=d7f32ad690a51eec5bcaac19bd64a25eec866d4d`
- Run mode: checkpointed host-agent execution in the canonical BENCH-02 workspace; paper-only inputs, no project/memory context.

## Recovery and provenance

The existing source lock, acquisition metadata, source pages, visual candidate tasks/assets, and Direct-AI baseline were recovered and checked against the source SHA. The prior Direct-AI envelope is `agent_runs/TASK-V3-DIRECT-BENCH-02-LORA-ADAPTATION/run-001.json`; its task identity, envelope schema, source SHA, and source-only boundary validate. Source reconstruction was regenerated only where absent (`model/source_map.json`, `model/figure_inventory.json`, `model/equation_inventory.json`) and all hashes bind to the locked PDF.

Semantic visual verification completed 17 page checkpoints. All available candidate crops were verified after full-page inspection; two intentionally fail closed as `NEEDS_REVIEW`: `T13` (page 21, no candidate crop) and `F08` (page 26, no complete candidate asset). The final narrative marks F08 as uncertain and does not present a fabricated image.

Lead Reader, all six independent Lens outputs, Revision Memo, Dynamic Narrative Plan, and Lead Writer each have an immutable `AgentResultEnvelope` under `agent_runs/`. Every final Lens payload has source SHA `e9a0d312...7395a` and baseline SHA `7f5377fff58ba5872ff805196eba449fa044edc91bbfec485f954b1fa212b0a9`.

Six Lens provenance (final payload SHA):

- `lens_v3/argument_narrative.json` — `74e1188e255a8a18dccb4b4ba6e73ebde6107dadf1497ee7c192994e6053cb95`
- `lens_v3/method_study_design.json` — `9ddb7087d7c1e1bdc4f65591b24df2df41fce9c7d37d5d3c434a2374587e9a26`
- `lens_v3/evidence_results.json` — `8fcb47b1236dfc2710ca68f8acc79e6af2306192cff0da3c7b4d4535a49abf5b`
- `lens_v3/validity_boundary.json` — `815d0ab44ae3395d52a1a421986dde41300c7367f8182fd6b7dd48d412d7196f`
- `lens_v3/mechanism_causality.json` — `7a05ec0cf53a8969710f84f8aab087c9073aba293d55644c42c6bf70ba7fa497`
- `lens_v3/reproducibility_implementation.json` — `722d217a00968831bdbc3df6513dd0697e68cc8d9ac14367186188cc89975845`

## Final artifacts and checks

- `model/paper_understanding_draft.json` — schema valid; SHA `7f5377fff58ba5872ff805196eba449fa044edc91bbfec485f954b1fa212b0a9`
- `model/revision_memo.json` — schema valid; SHA `4ba4ff4ef39b6736f3d3373b06e9be4da27d12cf6e6a451dd0b473d54a516683`
- `model/narrative_plan.json` — schema valid; SHA `20648b998fd004bb29ce7b88d541487fe6c6c3c557c4a9e224b79790b2aa49a3`
- `reader/narrative_manuscript.json` — schema valid, Reader-v3 integrity valid, plan order preserved; SHA `096ad5587b71edd3a979409c6849a6facb1ea4e935d87357c77cc44960c12dbf`
- `reader/issue22_integrity_validation.json` — machine validation `PASS`
- Rendered artifacts: `reader/paper_reader.html`, `reader/paper_reader.md`, `reader/paper_reader.pdf`, and `reader/evidence_atlas.html`.

## Paper-shaped structure

The final section order is:

1. 为什么“适配”首先是部署问题
2. 从任务增量到低秩重参数化
3. 把低秩更新放进 Transformer，并折叠回部署图
4. 跨模型实证：少量参数能否保住任务质量
5. rank 与矩阵位置：效率来自哪里
6. 子空间证据提供的机制线索
7. 结论的有效范围与尚未回答的问题

This is the paper's actual argumentative movement: deployment bottleneck → task-increment formulation → low-rank reparameterization → Transformer placement/weight merging → scale-up quality evidence → rank and subspace interpretation → bounded conclusion. Sections 3, 5, and 6 are paper-specific and would disappear or be distorted under a generic problem/method/results/limitations template.

## Template-bias and integrity judgment

No fixed universal chapter IDs or mandatory problem/gap/method/results/limitations slots were used. Mild conventional pressure remains in the deployment-motivation and empirical-result sections because those are genuinely part of this paper; it does not determine the order or collapse the rank/subspace argument. Primary narrative contains no Lens, Council, task/schema/hash, O/I/A, project-transfer, or memory vocabulary. Unknown visual evidence is preserved as uncertainty, and source-grounded integrity/schema checks pass.

**Answer:** the Reader feels shaped by the LoRA paper, not by Evidentia. Evidentia supplies the provenance and isolation scaffolding, but the visible narrative follows this paper's own cost-to-reparameterization-to-evidence-to-mechanism arc and preserves its specific engineering trade-offs and unresolved mechanism/boundary questions.
