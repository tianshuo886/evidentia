# Evidentia

[English](README.md) · [中文](README.zh-CN.md)

## Evidence-Grounded Paper Research OS

Evidentia is a single-paper research system for turning a supplied PDF into a durable, inspectable research object. It reconstructs the paper’s evidence surface, reads it from six independent perspectives, freezes the paper facts, renders a unified reader, and optionally maps the paper into a project without mutating the original understanding.

The repository contains the reusable skill only. It does not contain a particular paper, benchmark article, or project.

## Why Evidentia exists

Normal paper summaries lose the parts that matter for research work:

- figures become prose and their original evidence disappears;
- conclusions are detached from the figures, tables and experiments that support them;
- the reader follows the paper’s narrative without testing its weak links or alternatives;
- project goals bias the first reading and make the paper appear to confirm existing plans;
- later review starts from chat history instead of a stable, machine-readable object;
- fixed templates encourage chapter-by-chapter paraphrase and miss anomalies, negative results and reusable technical components.

Evidentia addresses these problems with a frozen Paper Model, typed Evidence Graph, source reconstruction, six independent Lens rereads, a unified Paper/Project Reader and a provenance-linked Research Delta.

## Core architecture

```text
paper.pdf
   ↓
source-only ingest + Figure/Table reconstruction
   ↓
Paper Model + Evidence Graph
   ↓
Author / Reviewer / Mechanism / Builder / Anomaly / Counterfactual
   ↓
freeze + SHA-256 integrity gate
   ↓
Paper Reader (HTML primary, PDF snapshot)
   ↓
optional contextual apply to one project
   ↓
Research Delta + Project Gap Map + literature index
```

The Paper Model is canonical truth. Renderers, Kami-compatible presentation and project analysis are downstream adapters.

## Installation

### Requirements

- Python 3.10+
- PyMuPDF (figure/table extraction)
- jsonschema (schema + freeze gates)
- pytest (run the gates)
- WeasyPrint, optional: PDF snapshot only; HTML reader works without it.

### Install

```bash
git clone https://github.com/tianshuo886/evidentia.git
cd evidentia
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## Basic use

### 1. Start a source-only read

```bash
python scripts/pipeline.py read \\
  --pdf /path/to/paper.pdf \\
  --out /path/to/paper-output
```

With supplements:

```bash
python scripts/pipeline.py read \\
  --pdf paper.pdf \\
  --supplement supplement.pdf \\
  --out paper-output
```

This creates the isolated `working/` bundle, copies the source PDF, extracts the Figure/Table inventory, and builds the source map. It does not load any project context.

### 2. Build the six Lens task packets

```bash
python scripts/lens_runner.py --out paper-output
```

Run the six packets independently against the source PDF and frozen base model. Write the six corresponding files under `paper-output/lens/`.

### 3. Validate and freeze

```bash
python scripts/check_lenses.py --out paper-output
python scripts/merge_lenses.py --out paper-output
python scripts/build_graph.py --out paper-output
python scripts/validate_model.py --out paper-output
python scripts/freeze_check.py --out paper-output
```

A freeze fails on missing Lens files, dangling IDs, uninspected Figures/Tables, missing critical assets, invalid coverage declarations, or unsupported claims.

### 4. Render and audit the Reader

```bash
python scripts/render_reader.py --out paper-output
python scripts/reader_audit.py --out paper-output
```

The Reader has three reading depths: a 30-second dashboard, a 5-minute argument view, and a 30–60-minute Evidence Atlas. HTML is the primary surface; PDF is an archive snapshot.

### 5. Apply the frozen paper to a project

```bash
python scripts/pipeline.py apply \\
  --paper paper-output \\
  --project /path/to/project.md \\
  --focus "water-vapor reconstruction"
```

Apply first verifies the frozen hashes and copies exactly one project document into `apply/<project>/`. Complete the contextual reread there, fill `project_context.json` and `research_delta.json`, then validate:

```bash
python scripts/validate_delta.py \\
  --paper paper-output \\
  --delta paper-output/apply/project/research_delta.json
```

A valid Research Delta may change a belief, expose an unknown, transfer a component, invalidate an experiment, propose an experiment with decision value, or explicitly conclude `NO_NEW_ACTIONABLE_EXPERIMENT`.

## Output objects

| Object | Purpose |
|---|---|
| `paper_model.json` | Canonical paper facts and epistemic states |
| `evidence_graph.json` | Typed links between claims, observations, figures, tables and experiments |
| `source_map.json` | Page, section, equation and in-text mention provenance |
| `lens/*.json` | Six independent reread outputs |
| `manifest.json` | Freeze status and SHA-256 hashes |
| `reader/reader.html` | Primary human reading surface |
| `research_delta.json` | Project-specific consequences kept separate from paper facts |
| `literature_index.json` | Stable cross-paper memory foundation |

## Design principles

- **Open Reading before project projection:** project context changes what to inspect later, not what the paper says.
- **Natural structure before schema:** recover the paper’s argument before filling fields.
- **Figure-first evidence:** every Figure and Table is inventoried and inspected.
- **Observation / interpretation / assessment separation:** data, author explanation and reader judgment remain distinct.
- **Independent Lens passes:** six rereads cannot be replaced by one blended summary.
- **Freeze before Apply:** project analysis cannot silently edit paper facts.
- **Kami as presentation:** display tooling cannot define the paper’s information architecture.
- **Uncertainty is legitimate:** the system preserves unresolved and insufficient evidence states.

## Use cases

- Deep reading of a method paper before adapting its protocol.
- Auditing whether a paper’s strongest claim is actually supported by its figures and experiments.
- Finding reusable losses, diagnostics, ablations, sampling strategies and failure modes.
- Comparing a paper’s evidence with a project’s explicit research gaps.
- Deciding whether a planned experiment should be transferred, adapted, deprioritized or rejected.
- Building a durable, searchable memory of papers without relying on chat history.

## Security and isolation

Open Reading receives only the paper bundle and skill resources. Project repositories, plans, chats, memory and connectors are outside its input boundary. Apply is a separate phase and starts only after the Paper Model is frozen and hash-verified.

## Tests

```bash
pytest -q
```

The tests include negative cases for dangling evidence, missing Lens files, missing critical assets and tampered frozen models.

## Naming

The repository is `evidentia`. The Skill name is **Evidentia** and the descriptor is **Evidence-Grounded Paper Research OS**. The old `paper-read` URL redirects to the new location.


## Kami integration

See `references/kami-integration.md` for the rendering and visual QA bridge.
