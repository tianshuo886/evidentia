# Evidentia · Issue #24 Architecture & Workspace Contract

**Issue #24: Reader-first Human–AI Research Workspace**  
*Interact with the reconstructed paper, not a raw-PDF-first chat.*

- **Repository:** `tianshuo886/evidentia`
- **Canonical Branch:** `master`
- **Scientific Core:** Evidentia Reader Reset v3 (FROZEN; `SCIENTIFIC_SEMANTICS_CHANGED = NO`)
- **Canonical Model Policy:** `antigravity/gemini-3.8-flash [magpie]`
- **Status:** PASS / COMPLETE
- **Issue #25 Readiness:** `ISSUE25_ADAPTER_READY = YES`

---

## 1. Product Philosophy & Core Principles

Evidentia was created because:
1. Raw academic papers are dense, non-linear, and time-consuming to read;
2. Generic raw-PDF-first chat systems lose figures, tables, and mathematical derivations, detaching claims from underlying empirical proof;
3. Goal-directed prompts over-focus on narrow keywords, ignoring critical boundary conditions;
4. Structured research insights are easily forgotten without durable, auditable memory.

Issue #24 introduces the **Human–AI Research Workspace** while strictly adhering to the fundamental product principle:

> **Reader is the primary surface.**  
> **Source PDF / Evidence Atlas is the evidence surface.**  
> **AI is the interactive reasoning layer.**  
> **Research Memory is the persistence layer.**  
> **Project Apply is explicit and post-freeze only.**

### Explicit Anti-Patterns Repudiated
- **No Raw-PDF-First Chat:** The user interface must never default to an English PDF split-screen with a generic chat bot. The primary reading and comprehension surface is the Chinese Academic Reader generated from the frozen paper understanding.
- **No Zotero Clone:** Evidentia is a deep comprehension and epistemological audit engine, not a generic citation management tool.
- **No Agentero Lock-in:** Evidentia Core is host-neutral. Agentero is an optional downstream reference adapter (deferred to Issue #25), not the scientific foundation.

---

## 2. Host-Neutral Workspace Architecture

The system follows a clean three-tier separation:

```text
┌────────────────────────────────────────────────────────┐
│               Frozen Paper Object (FPO)                │
│    (Immutable, Content-Addressed, Cryptographic SHA)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Workspace Contract Engine                │
│    (Host-Neutral Capabilities, Envelopes & Routing)    │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   CLI Reference Harness   │    │  Downstream Host Adapters │
│  (scripts/workspace_     │    │  (Agentero #25, Web UI,  │
│       harness.py)        │    │    Desktop Apps, etc.)   │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 3. Versioned Frozen Paper Object (FPO)

The **Frozen Paper Object** represents a verified, completed Evidentia reading run. It is schema-validated under `schemas/frozen_paper_object.schema.json` and implemented in `scripts/frozen_paper_object.py`.

### Schema Attributes
- `schema_version`: `"1.0"`
- `paper_id`: Stable identifier (e.g. `BENCH-02-LORA-ADAPTATION`)
- `version`: Version identifier (`"v1"`, `"v2"`, etc.)
- `frozen`: `true`
- `freeze_timestamp`: ISO 8601 UTC timestamp
- `parent_version`: `null` for initial freeze, or string (e.g. `"v1"`) for post-correction versions
- `source`:
  - `path`: Relative path to `source/paper.pdf`
  - `sha256`: Cryptographic SHA-256 of the source PDF
  - `title`, `doi`, `venue`, `year`: Metadata
- `source_sha256`: Duplicate top-level hash for fast validation
- `reader_manuscript_sha256`: SHA-256 of `narrative_manuscript.json`
- `reader`:
  - `manuscript_path`: Relative path to `reader/narrative_manuscript.json`
  - `html_path`: Relative path to `reader/paper_reader.html`
  - `markdown_path`: Relative path to `reader/paper_reader.md`
- `rendered_artifacts`:
  - `reader_html`: Path and SHA-256
  - `reader_md`: Path and SHA-256
  - `evidence_atlas_html`: Path
  - `evidence_atlas_json`: Path and SHA-256
- `evidence_atlas`:
  - `path`: `reader/evidence_atlas.json`
  - `sha256`: SHA-256 hash
  - `items_count`: Integer count of evidence items
- `source_map`:
  - `path`: `model/source_map.json`
  - `sha256`: SHA-256 hash
- `scientific_execution_provenance`:
  - `pipeline`: `"reader_v3"`
  - `canonical_model_policy`: `"antigravity/gemini-3.8-flash [magpie]"`
  - `narrative_plan_sha256`: SHA-256 hash
  - `revision_memo_sha256`: SHA-256 hash
  - `integrity_validation`: `"PASSED"`
- `correction_lineage`: Array of correction lineage records
- `object_sha256`: Deterministic hash of the core canonical metadata

---

## 4. Workspace Capability Contract

All workspace actions are declared in `schemas/workspace_contract.schema.json` and dispatched via `WorkspaceSession.dispatch_action(action, payload)`.

```json
{
  "schema_version": "1.0",
  "action": "ACTION_NAME",
  "paper_id": "PAPER_ID",
  "status": "SUCCESS" | "ERROR",
  "payload": { ... },
  "result": { ... },
  "error_code": null,
  "error_message": null
}
```

### Capability Definitions

| Capability | Parameters | Semantics & Purpose |
|---|---|---|
| `OPEN_READER` | `anchor` (optional), `format` (`html`/`markdown`) | **Primary reading surface.** Opens the Frozen Chinese Reader. Resolves section/block anchors; fails closed with `STALE_OR_INVALID_ANCHOR` if anchor is stale. |
| `GET_READER_SELECTION` | `selection_text`, `anchor`, `start_char`, `end_char` | Extracts Reader excerpt, associates section metadata, extracts bound evidence references (`evidence_refs`) and source anchors (`source_anchors`). |
| `OPEN_EVIDENCE` | `evidence_id` | **Supporting drill-down infrastructure.** Resolves evidence item (figure crop, table, equation), providing bidirectional links to the source PDF and back to Reader sections (`related_reader_anchors`). |
| `OPEN_SOURCE` | `page`, `region` (optional) | **Secondary verification only.** Opens source PDF page. Tagged `surface_role: "VERIFICATION_ONLY"`, `default_surface: false`. Lists evidence items on the page. |
| `ASK_WITH_CONTEXT` | `question`, `selection`, `anchor`, `evidence_refs`, `debug_mode` | **Interactive reasoning layer.** Formulates evidence-grounded responses citing Reader anchors and evidence items. Classifies claims into tripartite epistemic attribution. Filters internal Lens mechanics. |
| `CREATE_PRIVATE_NOTE` | `text`, `anchor`, `evidence_id`, `page`, `region` | **User annotation layer.** Persists private user note bound to anchors/evidence. Strictly preserves Frozen Reader SHA-256 (zero silent mutation). |
| `LIST_NOTES` | `anchor` (optional), `evidence_id` (optional) | Queries user notes. |
| `UPDATE_NOTE` | `note_id`, `text`, `tags` | Updates note while guaranteeing Reader immutability. |
| `DELETE_NOTE` | `note_id` | Deletes note while guaranteeing Reader immutability. |
| `PROPOSE_CORRECTION` | `anchor`, `rationale`, `proposed_text`, `source_evidence` | **Non-mutating correction proposal.** Records proposal record with `status: "PROPOSED"`. Original Reader remains 100% untouched. |
| `REVIEW_CORRECTION` | `proposal_id`, `decision` (`ACCEPT`/`REJECT`), `reviewer_rationale` | Evaluates proposal. Rejection preserves state. Acceptance creates a **new version** (`v2`), generating a new manuscript hash, leaving original `v1` immutable. |
| `START_PROJECT_APPLY` | `project_context` | **Explicit Project Apply trigger.** Opt-in only post-freeze. Fails if paper is unfrozen or context is missing. Leaves Frozen Reader untouched. |
| `QUERY_RESEARCH_MEMORY` | `query`, `filters` | Queries durable cross-paper memory post-freeze. Refuses unfrozen papers. |

---

## 5. Selection-Aware Ask & Epistemic Attribution

When a user selects a passage in the Reader and asks a question, the Ask layer receives:
1. Selected text and section anchor;
2. Bound evidence items from Evidence Atlas (`F01`, `T01`, `EQ-01`, etc.);
3. Relevant source map blocks for English text verification;
4. Equation details from equation inventory for mathematical derivations.

### Tripartite Epistemic Attribution
Evidentia enforces a clear three-way distinction in research interaction:
- **`OBSERVATION` (观测事实):** Direct numerical facts, table measurements, and figure curves directly reported in the paper.
- **`AUTHOR_INTERPRETATION` (作者主张):** Theoretical hypotheses, architectural rationale, and qualitative explanations formulated by the authors.
- **`READER_ASSESSMENT` (Evidentia 审读评估):** Independent scientific boundary assessments, verification status, and limitations audited by Evidentia.

### Zero Internal Lens Leakage
Unless `debug_mode=true` is explicitly requested, responses never leak internal pipeline mechanics (`"Author Lens"`, `"Reviewer Lens"`, `"Mechanism Lens"`, `"Builder Lens"`, `"Anomaly Lens"`, `"Counterfactual Lens"`, `"Lens Council"`, `"Council Chair"`, etc.).

---

## 6. Bidirectional Evidence Navigation

The Workspace bridges the Frozen Reader and source evidence in both directions:
- **Reader → Evidence:** Reading a block displays citations `〔F01, p.4〕`. Clicking opens evidence item `F01` with visual asset preview and page location.
- **Evidence → Reader:** Inspecting an evidence item in the Evidence Atlas surfaces all Reader sections and blocks that cite this evidence (`related_reader_anchors`), maintaining the Frozen Reader as the intellectual authority.

---

## 7. Private Notes Isolation

User notes are strictly isolated from the scientific core:
- **Storage:** Persisted under `notes/notes.json` (or host-configured user storage).
- **Attribution:** Marked `author_type: "USER"`.
- **Integrity Assertion:** Note creation, editing, and deletion compute the SHA-256 of `narrative_manuscript.json` and `paper_reader.html` before and after operations, asserting zero change.

---

## 8. Versioned Correction Workflow

Evidentia prohibits in-place mutation of frozen paper text. Corrections follow a strict formal lifecycle:

```text
Human Proposal (PROPOSE_CORRECTION)
  │  - Anchor, rationale, proposed text, source evidence
  │  - Status: PROPOSED; Original version v1 UNMUTATED
  ▼
Source Reinspection & Evidence Verification
  ▼
Explicit Decision (REVIEW_CORRECTION)
  ├─ REJECT:
  │    - Status: REJECTED; Reviewer rationale recorded
  │    - Zero modification to files; v1 remains active
  │
  └─ ACCEPT:
       - Status: ACCEPTED; Reviewer rationale recorded
       - Original v1 manuscript and FPO remain 100% IMMUTABLE
       - Creates versions/v2/narrative_manuscript.json with new SHA-256
       - Generates frozen_paper_object.v2.json with parent_version: "v1"
       - Records correction_lineage linking proposal ID
```

---

## 9. Integrity Firewalls

1. **Research Memory Firewall (`memory_manager.enforce_open_reading_firewall`):**
   - Pre-freeze Honest Reading tasks (`LEAD_READING`, `LENS_V3`, `REVISION_MEMO`, `NARRATIVE_PLAN`, `LEAD_WRITING`) strictly prohibit research memory.
   - Any memory artifact in `input_artifacts` or omission of `RESEARCH_MEMORY` in `prohibited_context` fails closed.
   - Research memory is accessible only post-freeze for cross-paper recall.

2. **Project Apply Firewall:**
   - Evidentia never automatically maps papers to user projects or injects unsolicited project suggestions into Honest Reading.
   - `START_PROJECT_APPLY` requires an explicit, deliberate user action with a valid `project_context`.
   - The paper must be `FROZEN`.
   - Resulting transfer units are isolated in a separate `apply/` envelope without mutating the Frozen Paper Object.

---

## 10. Real-Paper Workspace Validation

The Workspace Contract and reference harness were verified against three structurally diverse real-paper fixtures from Issue #19/22:

| Paper ID | Intellectual Archetype | Sections | Evidence Items | Validation Result |
|---|---|---|---|---|
| `BENCH-02-LORA-ADAPTATION` | Empirical LLM parameter-efficient adaptation | 7 (`s1`–`s7`) | 204 | **PASS** |
| `BENCH-04-ALPHAFOLD2-STRUCTURE` | Biomolecular deep learning structural breakthrough | 6 (`s1`–`s6`) | 118 | **PASS** |
| `UNSEEN-01-RETHINKING-GENERALIZATION` | Theoretical/empirical generalization paradox | 6 (`SEC-01`–`SEC-06`) | 73 | **PASS** |

### Verified Workflow on Each Paper
1. Open Reader as primary surface (`default_surface = true`, `surface_role = "PRIMARY"`);
2. Select passage and resolve bound evidence and source page anchors;
3. Ask evidence-grounded question with tripartite epistemic attribution and zero internal lens exposure;
4. Open supporting evidence item with bidirectional links and open source PDF for verification;
5. Create private user note with cryptographic proof of zero Reader manuscript SHA mutation;
6. Propose correction without mutating base version;
7. Explicitly trigger Project Apply post-freeze.

---

## 11. Issue #25 Readiness

```text
ISSUE25_ADAPTER_READY = YES
```

The Workspace Contract (`schemas/workspace_contract.schema.json` and `scripts/workspace_contract.py`) provides a stable, host-neutral interface ready for the downstream Agentero reference adapter:
- Capability discovery and action dispatching via `dispatch_action`;
- Reader deep links and anchor resolution via `OPEN_READER`;
- Bidirectional evidence navigation via `OPEN_EVIDENCE` and `OPEN_SOURCE`;
- Selection context handoff via `GET_READER_SELECTION` and `ASK_WITH_CONTEXT`;
- Isolated note persistence via `CREATE_PRIVATE_NOTE` / `LIST_NOTES`;
- Non-mutating versioned correction proposal bridge via `PROPOSE_CORRECTION` / `REVIEW_CORRECTION`;
- Opt-in post-freeze Project Apply via `START_PROJECT_APPLY`.

*Issue #25 implementation is deferred and will be undertaken as its own dedicated goal.*
