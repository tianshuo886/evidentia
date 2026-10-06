# Evidentia · Issue #25 Agentero Adapter Contract Specification

**Issue #25: Agentero Adapter — Reference Implementation of the Reader-First Workspace Contract**  
*Host Action Mapping Specification*

- **Authority:** Evidentia Host-Neutral Workspace Contract (`ISSUE24_WORKSPACE_CONTRACT.md`, `schemas/workspace_contract.schema.json`)
- **Adapter Location:** `adapters/agentero/`
- **Host Role:** Agentero (`poco-ai/Agentero`) as an optional reference host environment
- **Architectural Boundary:** Canonical Workspace Contract remains authoritative. The adapter transforms host events to and from canonical contract envelopes.

---

## 1. Paper Workspace Mapping in Agentero Vault

An Evidentia-enabled paper in an Agentero vault follows the unified layout:

```text
<agentero-vault>/papers/<paper-id>/
├── <paper-id>.pdf                 # Agentero native PDF target (archival/verification)
├── NOTES.md                       # Agentero native human Markdown notes
├── marks/                         # Agentero native visual annotations
└── evidentia/                     # Canonical Evidentia Workspace root
    ├── reader/
    │   ├── paper_reader.html      # PRIMARY READING SURFACE
    │   ├── paper_reader.md        # Alternative Markdown Reader
    │   ├── paper_reader.pdf       # Vector print snapshot
    │   ├── evidence_atlas.html    # Evidence drill-down
    │   ├── evidence_atlas.json    # Structured evidence items
    │   ├── narrative_manuscript.json # Publication manuscript
    │   └── frozen_paper_object.json  # Cryptographic FPO
    ├── model/
    │   └── manifest.json          # Freeze integrity manifest
    ├── source/
    │   ├── paper.pdf              # Verified source PDF (SHA-locked)
    │   └── source_sha256.txt
    ├── assets/                    # Page-localized visual crops
    ├── notes/
    │   └── notes.json             # Structured private notes store
    ├── corrections/
    │   └── proposals.json         # Non-mutating correction proposals
    └── apply/                     # Contextual project transfer (explicit only)
```

The adapter provides bi-directional discovery:
- Resolves an Evidentia workspace inside an existing Agentero paper folder;
- Creates a lightweight Agentero paper folder facade around a standalone Evidentia workspace.

---

## 2. Action Mapping Specifications

### 1. `OPEN_READER`
- **Evidentia Request:** `{"action": "OPEN_READER", "payload": {"anchor": str, "format": "html"|"markdown"}}`
- **Agentero Host Primitive:** Dual-pane main view; document viewer (HTML iframe or Markdown renderer).
- **Adapter Transformation:**
  - Verifies that `reader/paper_reader.html` exists.
  - If `anchor` is supplied, normalizes anchor (e.g. `#s1`, `ch-s1`), resolves via `WorkspaceSession.open_reader()`, and forms host deep-link URI: `file://.../paper_reader.html#<anchor>`.
  - Sets Agentero active tab to the Reader, explicitly overriding default PDF view.
- **Response Mapping:**
  ```json
  {
    "host_action": "SET_ACTIVE_DOCUMENT",
    "document_type": "READER_PRIMARY",
    "uri": "file://.../paper_reader.html",
    "target_anchor": "s1",
    "sections_outline": [ ... ],
    "surface_role": "PRIMARY"
  }
  ```
- **Failure Behavior:** If anchor not found, returns `STALE_OR_INVALID_ANCHOR` with list of available valid anchors. Viewer opens at document root.
- **Provenance Behavior:** Records `reader_manuscript_sha256` in view metadata.
- **Human Review Required:** No.

---

### 2. `GET_READER_SELECTION`
- **Evidentia Request:** `{"action": "GET_READER_SELECTION", "payload": {"selection_text": str, "anchor": str}}`
- **Agentero Host Primitive:** Active DOM text selection event in Reader pane.
- **Adapter Transformation:** Calls `WorkspaceSession.get_reader_selection()`. Gathers enclosing section ID/title, bound evidence references (`evidence_refs`), and source page anchors.
- **Response Mapping:**
  ```json
  {
    "selected_text": "...",
    "section_id": "s2",
    "section_title": "从任务增量到低秩重参数化",
    "bound_evidence_ids": ["F01", "p.2", "p.4"],
    "bound_source_pages": [2, 4]
  }
  ```
- **Failure Behavior:** Falls back to first section if selection cannot be localized.
- **Provenance Behavior:** Binds selection to active Frozen Paper Object SHA.
- **Human Review Required:** No.

---

### 3. `OPEN_EVIDENCE`
- **Evidentia Request:** `{"action": "OPEN_EVIDENCE", "payload": {"evidence_id": str}}`
- **Agentero Host Primitive:** Modal preview dialog or secondary side-panel inspection view.
- **Adapter Transformation:** Resolves `evidence_id` in Evidence Atlas. Retrieves asset crop PNG (`assets/figures/...`), caption, and bidirectional links.
- **Response Mapping:**
  ```json
  {
    "host_action": "SHOW_EVIDENCE_CARD",
    "evidence_id": "F01",
    "label": "Figure 1",
    "asset_uri": "file://.../crop_F01_p1_151x153.png",
    "caption": "...",
    "source_jump": {"page": 1},
    "related_reader_anchors": [{"section_id": "s2", "anchor": "s2"}]
  }
  ```
- **Failure Behavior:** Returns `EVIDENCE_NOT_FOUND` if ID does not exist in atlas.
- **Provenance Behavior:** Includes verification status (`VERIFIED`).
- **Human Review Required:** No.

---

### 4. `OPEN_SOURCE`
- **Evidentia Request:** `{"action": "OPEN_SOURCE", "payload": {"page": int, "region": dict}}`
- **Agentero Host Primitive:** Built-in PDF reader with page navigation (`#page=N`).
- **Adapter Transformation:** Maps request to Agentero PDF viewer command targeting `source/paper.pdf#page=<page>`. Tags view as secondary/verification.
- **Response Mapping:**
  ```json
  {
    "host_action": "OPEN_PDF_PAGE",
    "pdf_uri": "file://.../source/paper.pdf",
    "page": 4,
    "surface_role": "VERIFICATION_ONLY",
    "default_surface": false,
    "evidence_on_page": [ ... ]
  }
  ```
- **Failure Behavior:** Defaults to page 1 if page out of bounds.
- **Provenance Behavior:** Validates `source_sha256` matches source PDF file.
- **Human Review Required:** No.

---

### 5. `ASK_WITH_CONTEXT`
- **Evidentia Request:** `{"action": "ASK_WITH_CONTEXT", "payload": {"question": str, "selection": dict, "anchor": str}}`
- **Agentero Host Primitive:** Companion chat pane via ACP / BYOA / MCP agent dispatch.
- **Adapter Transformation:**
  - Extracts selection context and bound evidence items.
  - Dispatches through `WorkspaceSession.ask_with_context()`.
  - Packages answer with tripartite epistemic attribution (`OBSERVATION`, `AUTHOR_INTERPRETATION`, `READER_ASSESSMENT`).
  - Filters all internal Lens markers (`INTERNAL_LENS_MARKERS`) unless `debug_mode=True`.
- **Response Mapping:**
  ```json
  {
    "host_action": "APPEND_CHAT_MESSAGE",
    "role": "assistant",
    "content": "...",
    "epistemic_category": "AUTHOR_INTERPRETATION",
    "cited_evidence": [ ... ],
    "reader_anchor": "s1"
  }
  ```
- **Failure Behavior:** Emits grounded error message if question cannot be answered.
- **Provenance Behavior:** Binds answer to Reader anchor and evidence IDs.
- **Human Review Required:** No.

---

### 6. `CREATE_PRIVATE_NOTE`
- **Evidentia Request:** `{"action": "CREATE_PRIVATE_NOTE", "payload": {"text": str, "anchor": str, "evidence_id": str}}`
- **Agentero Host Primitive:** Appending to paper `NOTES.md` and saving to `marks/`.
- **Adapter Transformation:**
  - Persists structured note to Evidentia `notes/notes.json` via `WorkspaceSession.create_private_note()`.
  - Synchronizes human-readable entry to Agentero `NOTES.md` using Markdown formatting with backlinks.
  - Verifies Reader manuscript SHA-256 before and after (zero silent mutation).
- **Response Mapping:**
  ```json
  {
    "host_action": "NOTE_SAVED",
    "note_id": "note-...",
    "markdown_path": "NOTES.md",
    "mutation_check": "PASSED_READER_SHA_UNCHANGED"
  }
  ```
- **Failure Behavior:** Fails closed if content is empty or schema invalid.
- **Provenance Behavior:** Author type set to `"USER"`.
- **Human Review Required:** No.

---

### 7. `LIST_NOTES` / `UPDATE_NOTE` / `DELETE_NOTE`
- **Evidentia Request:** Standard note CRUD requests.
- **Agentero Host Primitive:** Reading, editing, or deleting lines in `NOTES.md` and `notes/notes.json`.
- **Adapter Transformation:** Dispatches to `WorkspaceSession`. Keeps `NOTES.md` and `notes/notes.json` synchronized. Asserts zero mutation of Reader files.
- **Human Review Required:** No.

---

### 8. `PROPOSE_CORRECTION`
- **Evidentia Request:** `{"action": "PROPOSE_CORRECTION", "payload": {"anchor": str, "rationale": str, "proposed_text": str}}`
- **Agentero Host Primitive:** Diff-review interface / pending patch queue.
- **Adapter Transformation:**
  - Records proposal in `corrections/proposals.json` via `WorkspaceSession.propose_correction()`.
  - Formats diff representation for Agentero diff viewer:
    `- <original text at anchor>`
    `+ <proposed text>`
  - Original Frozen Reader files remain 100% untouched.
- **Response Mapping:**
  ```json
  {
    "host_action": "SHOW_CORRECTION_DIFF",
    "proposal_id": "corr-...",
    "status": "PROPOSED",
    "anchor": "s2",
    "diff_preview": "...",
    "base_version": "v1"
  }
  ```
- **Failure Behavior:** Rejects if anchor is invalid.
- **Provenance Behavior:** Base manuscript SHA-256 verified identical.
- **Human Review Required:** **YES (Mandatory).**

---

### 9. `REVIEW_CORRECTION`
- **Evidentia Request:** `{"action": "REVIEW_CORRECTION", "payload": {"proposal_id": str, "decision": "ACCEPT"|"REJECT", "reviewer_rationale": str}}`
- **Agentero Host Primitive:** Accept or Reject button clicked in Agentero review UI.
- **Adapter Transformation:** Dispatches to `WorkspaceSession.review_correction()`.
  - If `REJECT`: Status becomes `REJECTED`; zero file mutations; active version remains `v1`.
  - If `ACCEPT`: Status becomes `ACCEPTED`; creates version `v2` under `versions/v2/` with new manuscript and FPO hash, leaving original `v1` completely immutable.
- **Response Mapping:**
  ```json
  {
    "host_action": "CORRECTION_REVIEWED",
    "decision": "ACCEPT" | "REJECT",
    "active_version": "v2",
    "original_version": "v1",
    "message": "..."
  }
  ```
- **Human Review Required:** Explicit human action.

---

### 10. `START_PROJECT_APPLY`
- **Evidentia Request:** `{"action": "START_PROJECT_APPLY", "payload": {"project_context": dict}}`
- **Agentero Host Primitive:** Explicit user command (e.g. `/apply` slash command or "Apply to Project" button).
- **Adapter Transformation:**
  - Verifies paper is post-freeze (`FROZEN`).
  - Verifies `project_context` is non-empty and explicit.
  - Calls `WorkspaceSession.start_project_apply()`.
  - Writes transfer envelope to `apply/<project_id>/`.
  - Ordinary Reader Q&A is protected: never receives unsolicited project context.
- **Response Mapping:**
  ```json
  {
    "host_action": "OPEN_APPLY_WORKSPACE",
    "project_id": "...",
    "status": "APPLY_INITIALIZED",
    "isolation_audit": "PASSED"
  }
  ```
- **Failure Behavior:** Fails closed if paper is unfrozen or context is missing.
- **Human Review Required:** Explicit user action.

---

### 11. `QUERY_RESEARCH_MEMORY`
- **Evidentia Request:** `{"action": "QUERY_RESEARCH_MEMORY", "payload": {"query": str}}`
- **Agentero Host Primitive:** Vault-wide search / MCP memory lookup.
- **Adapter Transformation:** Verifies post-freeze state; dispatches to `memory_manager.search_memory()`. Blocks pre-freeze pipelines.
- **Response Mapping:** Returns matching paper memory objects and transfer units.
- **Human Review Required:** No.

---

### 12. `DISPATCH_ACTION`
- **Universal Router:** Accepts any canonical action name and payload, validating input and output against `schemas/workspace_contract.schema.json`.
