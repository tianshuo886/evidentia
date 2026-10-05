---
name: evidentia
description: Evidence-grounded Paper Research OS for one paper at a time. Build a source-reconstructed Paper Model and Evidence Graph, perform six independent Lens rereads, freeze the facts, render a unified Paper/Project Reader, and produce a provenance-linked Research Delta for a project. Use when the user asks to deeply read, audit, transfer, or build research memory from a supplied paper PDF. Not for paper search, triage, or multi-paper surveys.
license: Apache-2.0
compatibility: Python 3.9+, PyMuPDF, JSON Schema, and the existing Evidentia source-reconstruction dependencies.
metadata:
  version: "1.1.2"
  argument-hint: "<paper.pdf> --out <directory> [--supplement ...] | apply --paper <directory> --project <document> [--focus ...] | memory ..."
---

# Evidentia · Evidence-Grounded Paper Research OS

Evidentia turns one supplied paper into a durable, deeply reasoned research object:

```text
PDF → Source Reconstruction (Page-first Visual Track) → Source Lock
    ├── Evidence Structure Track (Claims, O/I/A, Figures, Tables, Evidence Graph)
    └── Argument Reconstruction Track (Problem, Motivation, Gap, Hypothesis, Scope, model/argument_reconstruction.json)
    → Open Reading (AgentTask) → Baseline Lock → Six Independent Lenses (AgentTask)
    → Semantic Reconciliation → Argument-Aware Cross-Lens Scientific Synthesis
    → Evidence Verification → Frozen Paper Model + Evidence Graph
    → Chinese-first Narrative Reader (HTML/MD/PDF) → release regression gate → PAPER_COMPLETE (STOP)

[Explicit User Request Only]
→ Contextual Apply (/evidentia-apply) → Separate Project Reader (apply/<project>/)
→ Optional Frozen Research Memory (/evidentia-memory)
```

## Entries

```bash
/evidentia <paper.pdf | DOI | arXiv-ID> [--out <directory>] [--supplement <supp.pdf>] [--mode standard|ensemble]
/evidentia-apply --paper <paper-output-dir> --project <project-document> [--focus <section>]
/evidentia-memory [commit-paper|commit-project|relation|inspect|snapshot|export|import]
```

Supports local PDF files, DOIs (e.g. `10.1038/...`), arXiv IDs (e.g. `1706.03762`), and direct paper URLs. Automatically acquires paper metadata, overview markdown, and open-access source PDF via `pa` (Paper Acquire), CrossRef, and Unpaywall. If `--out` is omitted, a local PDF is processed in a same-named workspace beside the source paper; identifier-based acquisition uses the available paper library and the same paper-folder convention. The workspace root contains the source PDF and user-facing reader copies, while internal artifacts remain under that single directory.

## Execution harness boundary

The six independent Round-1 lenses are a required part of the workflow and remain separate even when one model executes all of them. Use the currently active execution harness and do not proactively switch harnesses or providers. Multi-harness routing and lens-to-model assignment are intentionally left open for a future design; do not invent them here.

**Paper reading is the default contract**: Default execution can terminate at `PAPER_COMPLETE` only after the frozen paper understanding, Chinese-first Paper Reader (`reader/paper_reader.html`, `paper_reader.md`, `reader/paper_reader.pdf`), bound semantic/visual reviews, and the real-paper regression release report all pass. Apply loads exactly one project document **only after explicit user intent** and writes exclusively to `apply/<project>/`.

## Required output

```text
<out>/
├── source/paper.pdf [+ supplements]
├── source_pages/                    # full-page high-res rasterization (page-001.png, ...)
├── working/                         # source-only Open Reading boundary
├── tasks/                           # schema-valid AgentTask packets
│   ├── open_reading.json
│   ├── reconciliation.json
│   └── lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json
├── agent_runs/                      # immutable records of AgentResultEnvelope executions
├── model/
│   ├── paper_model.json             # final reconciled model (Open Reading draft → frozen final)
│   ├── open_reading_model.json      # immutable lens baseline snapshot (snapshot_baseline.py)
│   ├── open_reading_manifest.json   # baseline hashes + contract/prompt versions
│   ├── argument_reconstruction.json # first-class argument topology, author vs assessed argument, evidence promotion
│   ├── candidate_clusters.json      # Layer 1 deterministic pre-clustering
│   ├── frozen_evidence_package.json # immutable shared Council evidence boundary
│   ├── lens_reconciliation.json     # compatibility mirror of Chair item output
│   ├── lens_council.json            # Chair reconciliation, bounded cross-exam, unresolved state
│   ├── scientific_synthesis.json    # synthesis derived only from Council output
│   ├── evidence_graph.json          # typed claim/evidence relations (bound to SOURCE_SHA256)
│   ├── figure_inventory.json        # extraction record (bound to SOURCE_SHA256)
│   ├── source_map.json
│   └── manifest.json                # freeze hashes and audit status
├── lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json
├── council/round1/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json # frozen Round 1 snapshots
├── reader/                          # Chinese-first Paper Reader (immutable & project-independent)
│   ├── paper_reader_ir.json         # single synthesis-rich content IR (and render_ir.json)
│   ├── paper_reader.html            # interactive deep-reading report (and reader.html)
│   ├── paper_reader.md              # complete Markdown deep-reading report (and reader.md)
│   └── paper_reader.pdf             # print snapshot (and reader.pdf)
├── apply/<project>/                 # created ONLY after explicit Apply request
│   ├── project_context.json
│   ├── research_delta.json
│   ├── project_reader.html
│   ├── project_reader.md
│   └── memory_augmented_synthesis.json
└── notes.md
```

## Non-negotiable rules

1. **Source before interpretation.** Reconstruct pages, sections, captions, figures, tables, equations, experiments and in-text mentions before writing claims.
2. **Paper reading is default; project isolation is absolute.** Default run runs `PAPER_READING` intent and terminates at `PAPER_COMPLETE`. Project files, chats, plans and memory are strictly forbidden during paper reading. Zero `apply/` artifacts created by default.
3. **Natural structure and argument reconstruction first.** Recover the paper's own argumentative topology (`model/argument_reconstruction.json`) before mapping to canonical fields. Explicitly distinguish Author Argument (what authors argue) from Evidentia-Assessed Argument (what evidence actually justifies).
4. **Extraction does not imply presentation (Evidence promotion).** Selectively promote decisive evidence (`narrative_core`, `narrative_support`) to the main narrative; keep catalog and supplementary evidence in the audit appendix (`audit_only`, `uncertain`).
5. **Renderer purity: renderers must be scientifically dumb.** Production renderers format presentation, typography, and layout, but must never invent mechanisms, limitations, hyperparameters, optimizers, or domain boilerplate. When evidence is absent, state explicitly or omit.
6. **Page-first visual reconstruction; zero whole-page fallbacks.** Render complete PDF pages first, visually localize evidence second, deterministically crop third, verify fourth. Never publish a whole-page screenshot as a Figure/Table asset. Low-confidence visual binding fails closed to `NEEDS_REVIEW`.
7. **Claim discipline.** Keep Observation, Author Interpretation and Reader Assessment separate. Distinguish in-paper evidence from cited evidence.
8. **Independent Lens passes.** Author, Reviewer, Mechanism, Builder, Anomaly and Counterfactual are separate Round-1 rereads of one shared frozen evidence package. One combined summary is not a Lens pass.
9. **Evidence-grounded Lens Council.** A Council Chair reconciles Round-1 findings, may request at most one bounded selective cross-examination round, never uses majority voting, and preserves unresolved states.
10. **Cross-lens scientific synthesis without majority voting.** Scientific Synthesis consumes the Chair Council output, not raw Lens reports. Contradictions, anomalies, caveats and counterfactuals must be preserved, never erased.
10. **Chinese-first human reader; source preserved underneath.** Reader outputs are Chinese-first by default for human deep reading. Technical English terms and source evidence are preserved in parentheses.
11. **Apply is EXPLICIT-REQUEST-ONLY.** Project Apply is not the next phase of a normal read; it runs only upon explicit user request. Paper outputs (`reader/`) and project outputs (`apply/<project>/`) are physically separate. The Paper Reader is immutable.
12. **Uncertainty is data.** NOT_STATED, AMBIGUOUS, INSUFFICIENT_EVIDENCE, MODEL_UNCERTAIN and UNRESOLVED remain visible. Fail closed on uncertain tables (`STRUCTURE_UNCERTAIN`).

## Executable workflow

```bash
# 1. Initialize source reconstruction and generate Open Reading task packet
python scripts/evidentia.py run --pdf paper.pdf --out output

# 2. Host Agent reads tasks/open_reading.json, reasons over paper facts, writes model/paper_model.json
# Then advances baseline lock and generates six independent Lens task packets:
python scripts/evidentia.py run --out output

# 3. Host Agent executes tasks in tasks/lens/*.json independently and writes lens/<lens>.json
# Then advances reconciliation, scientific synthesis, evidence graph, freeze, and reader:
python scripts/evidentia.py run --out output
# Terminated at PAPER_COMPLETE!

# 4. Explicit Contextual Apply (ONLY when user explicitly requests project application)
python scripts/pipeline.py apply --paper output --project project.md
# Produces apply/project/project_reader.html & research_delta.json
python scripts/validate_delta.py --paper output --delta output/apply/project/research_delta.json
python scripts/full_audit.py --out output
```

`phase.py` prevents skipping phases (artifact + schema + hash + dependency checks). `init_run.py` creates the source-only boundary. `snapshot_baseline.py` freezes the lens baseline. `init_apply.py` verifies the freeze before copying one project document. Validators fail closed on missing files, duplicate IDs, dangling references, incomplete Lens passes, missing critical assets, source/base SHA mismatch, reconciliation provenance loss, hash changes or Reader omissions.

## Lenses

- **Author:** what the authors want the reader to believe and where rhetoric outruns evidence.
- **Reviewer:** controls, confounds, ablations, evaluation mismatch and weakest link.
- **Mechanism:** correlation, mechanism, causality, minimal A→B→C chain and falsifier.
- **Builder:** detachable methods, losses, protocols, preprocessing, diagnostics and evaluation.
- **Anomaly:** real failures, subgroup flips, negative results and downplayed findings; empty is valid.
- **Counterfactual:** serious alternative explanations that reuse the paper's evidence.

## Reader structure (open paper-specific narrative + quiet provenance appendix)

The Reader follows the paper's reconstructed argument topology. Section count, titles, identity, and order are selected for that paper by the Dynamic Narrative Plan; no universal problem/gap/method/results/limits sequence is required. Chinese-first prose carries the explanation; figures, equations, and local source links appear where that paper's argument needs them. A quiet appendix links to the separate Evidence Atlas for audit detail; O/I/A cards and Lens vocabulary never enter the human narrative.

默认 Reader 不包含“可复用技术内容”或项目迁移章节。论文技术细节提取是单独的显式意图（`PAPER_TECHNICAL_EXTRACTION`）；项目迁移仍只通过显式 `/evidentia-apply` 请求产生，且永不改写冻结 Paper Reader。

### Intent Model & Faithful-reading Firewall

> **永久设计原则：First understand the paper on its own terms. Only transfer it when the user asks. Relevance is not permission.**

系统通过 `scripts/intent_router.py` 严格区分四类意图，默认意图为 `PAPER_READING`：
- `PAPER_READING` (默认)：严禁从项目材料、研究记忆或相关性中推断迁移意图。严禁在阅读阶段访问 `apply/`、`project/` 或 `memory/project/`。
- `PAPER_TECHNICAL_EXTRACTION` (显式技术提取)：当且仅当用户明确请求可复现算法/组件时触发，严格限于论文技术范畴，产生独立工件 `reader/technical_extraction.md` 和 `.html`。
- `PROJECT_APPLY` (显式项目适配)：当且仅当用户明确要求结合项目时触发，工件严格隔离于 `apply/<project>/`，冻结 Paper Reader 哈希绝对不变。
- `MEMORY_OPERATION` (显式记忆操作)：管理和检索长期跨论文记忆。

### 认识论分层契约 (Epistemic Labeling)

即使在显式项目迁移中，也必须保持分层边界：
```text
Paper fact (论文实证)
↓
Evidentia interpretation (机制与研判)
↓
Transferable principle (可迁移原理)
↓
Applicability condition (适用条件与边界)
↓
Project mapping (项目映射与假设变化)
↓
Proposed adaptation (建议适配方案)
```
严禁将建议适配方案混淆为原论文贡献；所有推荐必须追溯论文证据，并明确项目假设的改变。

Project Delta appears exclusively in `apply/<project>/project_reader.html` and `.md`. Every Delta item links back to Paper Claim, Figure, Table, Experiment or page IDs.

## Out of scope

Paper acquisition/search, multi-paper survey generation, invented figures, abstract-only reading, silent frozen edits, forced novelty, and paper-specific fixtures. Regression papers are external inputs to this skill.
