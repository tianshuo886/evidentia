---
name: evidentia
description: Evidence-grounded Paper Research OS for one paper at a time. Build a source-reconstructed Paper Model and Evidence Graph, perform six independent Lens rereads, freeze the facts, render a unified Paper/Project Reader, and produce a provenance-linked Research Delta for a project. Use when the user asks to deeply read, audit, transfer, or build research memory from a supplied paper PDF. Not for paper search, triage, or multi-paper surveys.
license: Apache-2.0
compatibility: ">=Python 3.9"
metadata:
  version: "1.1.1"
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
    → Chinese-first Narrative Reader (HTML/MD/PDF) → PAPER_COMPLETE (STOP)

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

Supports local PDF files, DOIs (e.g. `10.1038/...`), arXiv IDs (e.g. `1706.03762`), and direct paper URLs. Automatically acquires paper metadata, overview markdown, and open-access source PDF via `pa` (Paper Acquire), CrossRef, and Unpaywall. If `--out` is omitted, output defaults to `./runs/<paper_stem>/`. All workspace artifacts are strictly contained within that single directory for clean inspection and one-command deletion.

**Paper reading is the default contract**: Default execution terminates at `PAPER_COMPLETE` after producing the frozen paper understanding and Chinese-first Paper Reader (`reader/paper_reader.html`, `paper_reader.md`, `paper_reader.pdf`). Apply loads exactly one project document **only after explicit user intent** and writes exclusively to `apply/<project>/`.

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
│   ├── lens_reconciliation.json     # Layer 2 semantic reconciliation + recorded conflicts
│   ├── scientific_synthesis.json    # dynamic topic-centered cross-lens synthesis
│   ├── evidence_graph.json          # typed claim/evidence relations (bound to SOURCE_SHA256)
│   ├── figure_inventory.json        # extraction record (bound to SOURCE_SHA256)
│   ├── source_map.json
│   └── manifest.json                # freeze hashes and audit status
├── lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json
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
8. **Independent Lens passes.** Author, Reviewer, Mechanism, Builder, Anomaly and Counterfactual are separate rereads of the frozen base understanding. One combined summary is not a Lens pass.
9. **Cross-lens scientific synthesis without majority voting.** Dynamically derive synthesis units from reconstructed arguments and Lens findings (`scientific_synthesis.json`), free of hardcoded domain templates. Contradictions, anomalies, caveats and counterfactuals must be preserved, never erased.
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

## Reader structure (Seven-layer hierarchy)

1. **一分钟看懂这篇论文:** 研究问题、核心方法、核心发现、最大价值、最大风险/边界。
2. **论文到底在解决什么问题:** 背景痛点、已有先验局限、切入点、重要度判定。
3. **方法到底怎么工作:** 端到端流程、核心组件拆解、公式中文通俗解读与物理意义。
4. **关键实验逐个说明:** 核心图表逐一精读（对比内容、读图指引、证明范围、盲区、异常信号）。
5. **综合科学判断:** 最坚实证据链、最薄弱推理链、先验假设、替代解释、反常现象、适用边界。
6. **可复用技术内容:** 可解耦算法组件、损失函数、预处理策略、迁移落地建议。
7. **证据审计附录:** 主张与 O/I/A 证据卡片列表、跨透镜争议焦点、页面锚点、验证状态（次级可折叠）。

Project Delta appears exclusively in `apply/<project>/project_reader.html` and `.md`. Every Delta item links back to Paper Claim, Figure, Table, Experiment or page IDs.

## Out of scope

Paper acquisition/search, multi-paper survey generation, invented figures, abstract-only reading, silent frozen edits, forced novelty, and paper-specific fixtures. Regression papers are external inputs to this skill.
