---
name: evidentia
description: Evidence-grounded Paper Research OS for one paper at a time. Build a source-reconstructed Paper Model and Evidence Graph, perform six independent Lens rereads, freeze the facts, render a unified Paper/Project Reader, and produce a provenance-linked Research Delta for a project. Use when the user asks to deeply read, audit, transfer, or build research memory from a supplied paper PDF. Not for paper search, triage, or multi-paper surveys.
argument-hint: "<paper.pdf> --out <directory> [--supplement ...] | apply --paper <directory> --project <document> [--focus ...]"
---

# Evidentia · Evidence-Grounded Paper Research OS

Evidentia turns one supplied paper into a durable research object:

```text
PDF → Source Reconstruction → Source Lock → Open Reading → Baseline Lock
→ Six Lens Rereads → Reconciliation → Frozen Paper Model + Evidence Graph
→ Unified Reader → Contextual Apply → Research Delta → Literature Memory
```

## Entries

```bash
/evidentia <paper.pdf> --out <directory> [--supplement <supp.pdf>]
/evidentia-apply --paper <paper-output-dir> --project <project-document> [--focus <section>]
```

Open Reading is project-invisible. Apply loads exactly one project document only after the Paper Model is frozen and its hash is verified. Triage and paper search are outside this skill.

## Required output

```text
<out>/
├── source/paper.pdf [+ supplements]
├── working/                         # source-only Open Reading boundary
├── model/
│   ├── paper_model.json             # final reconciled model (Open Reading draft → frozen final)
│   ├── open_reading_model.json      # immutable lens baseline snapshot (snapshot_baseline.py)
│   ├── open_reading_manifest.json   # baseline hashes + contract/prompt versions
│   ├── lens_reconciliation.json     # converged findings w/ supporting_lenses + recorded conflicts
│   ├── evidence_graph.json          # typed claim/evidence relations (bound to SOURCE_SHA256)
│   ├── figure_inventory.json        # extraction record (bound to SOURCE_SHA256)
│   ├── source_map.json
│   └── manifest.json                # freeze hashes and audit status
├── lens_tasks/                      # six independent reread packets
├── lens/{author,reviewer,mechanism,builder,anomaly,counterfactual}.json
├── reader/{reader.html,reader.pdf,render_ir.json}
├── apply/<project>/                 # created only by Apply
│   ├── project_context.json
│   └── research_delta.json
└── notes.md
```

## Non-negotiable rules

1. **Source before interpretation.** Reconstruct pages, sections, captions, figures, tables, equations, experiments and in-text mentions before writing claims.
2. **Project isolation.** Open Reading can access only the paper bundle, supplements and skill resources. Project files, plans, repositories, chats and memory are forbidden.
3. **Natural structure first.** Recover the paper's own argument before mapping to canonical fields.
4. **Full visual coverage.** Every Figure and Table receives a role, depth, inspection record and provenance. Depth changes effort, never coverage.
5. **Claim discipline.** Keep Observation, Author Interpretation and Reader Assessment separate. Distinguish in-paper evidence from cited evidence.
6. **Independent Lens passes.** Author, Reviewer, Mechanism, Builder, Anomaly and Counterfactual are separate rereads of the frozen base understanding. One combined summary is not a Lens pass.
7. **Freeze means immutable.** Apply refuses a missing or changed Paper Model, graph, source PDF or Lens output.
8. **Reader is an adapter.** The Paper Model is truth; HTML/PDF and Kami-compatible presentation are downstream renderings. Do not reshape the science to fit a template.
9. **Apply is a Research Delta.** It may produce Changed Belief, New Evidence, New Unknown, Transfer Unit, Invalidated Plan, or New Experiment. It must be allowed to produce `NO_NEW_ACTIONABLE_EXPERIMENT`.
10. **Uncertainty is data.** NOT_STATED, AMBIGUOUS, INSUFFICIENT_EVIDENCE, MODEL_UNCERTAIN and UNRESOLVED remain visible.

## Executable workflow

```bash
python scripts/pipeline.py read --pdf paper.pdf --out output
# populate model/paper_model.json as the Open Reading draft (project invisible)
python scripts/snapshot_baseline.py --out output
python scripts/lens_runner.py --out output
# run each lens task independently and write its matching lens/*.json
python scripts/check_lenses.py --out output
python scripts/merge_lenses.py --out output
python scripts/build_graph.py --out output
python scripts/validate_model.py --out output
python scripts/freeze_check.py --out output
python scripts/render_reader.py --out output
python scripts/reader_audit.py --out output
python scripts/pipeline.py apply --paper output --project project.md
# fill the contextual reread and Research Delta, then:
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

## Reader depth

- **30 seconds:** dashboard, one-line model, decisive claims and limitations.
- **5 minutes:** Paper Map, argument chain, Claim Cards and decisive figures.
- **30–60 minutes:** Evidence Atlas with original figures, captions, page anchors, experiments, weakest links, anomalies and unresolved questions.

Project Delta appears in the same HTML surface with a separate visual treatment and separate data files. Every Delta item links back to Paper Claim, Figure, Table, Experiment or page IDs.

## Out of scope

Paper acquisition/search, multi-paper survey generation, invented figures, abstract-only reading, silent frozen edits, forced novelty, and paper-specific fixtures. Regression papers are external inputs to this skill.
