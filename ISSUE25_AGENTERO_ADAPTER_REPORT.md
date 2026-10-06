# Evidentia · Issue #25 Agentero Adapter Report

**Issue #25: [P2] Agentero adapter — reference implementation of the Reader-first workspace contract**  
*Comprehensive Architecture, Implementation, and Validation Report*

- **Repository:** `tianshuo886/evidentia`
- **Canonical Branch:** `master` (developed on `issue25-agentero-adapter`)
- **Starting Master SHA:** `e2d52a5e1df7c87ccd27622cbb3742633c747748`
- **Target Host:** Agentero (`poco-ai/Agentero`) — Optional Reference Host
- **Status:** PASS / COMPLETE
- **Scientific Semantics Invariance:** `SCIENTIFIC_SEMANTICS_CHANGED = NO`

---

## 1. Architectural Principles & Layering

Issue #25 introduces a thin reference adapter connecting Agentero to Evidentia without compromising Evidentia Core's host neutrality:

```text
┌─────────────────────────────────────────────────────────┐
│                     Evidentia Core                      │
│     Reader Reset v3 · Frozen Paper Object (FPO)         │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│               Host-Neutral Workspace Contract           │
│         (schemas/workspace_contract.schema.json)        │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│               Agentero Reference Adapter                │
│                 (adapters/agentero/)                    │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
               ▼                           ▼
┌─────────────────────────────┐  ┌─────────────────────────┐
│     Agentero Local Vault    │  │  Agent Protocols (ACP)  │
│  (papers/<paper-id>/...)    │  │  (Claude Code / BYOA)   │
└─────────────────────────────┘  └─────────────────────────┘
```

### Core Invariants Preserved
1. **Evidentia Core Host Neutrality:** Evidentia does not depend on Agentero. When Agentero is absent, Evidentia operates at 100% capacity in standalone mode (`AGENTERO_UNAVAILABLE` $\rightarrow$ `STANDALONE_FALLBACK`).
2. **Reader-First Default Surface:** Opening a paper in Agentero preferentially resolves `reader/paper_reader.html` (or `paper_reader.md`). Raw PDF is strictly a secondary verification surface (`surface_role: "VERIFICATION_ONLY"`).
3. **Cryptographic Immutability:** Notes, highlights, and correction proposals can never silently mutate a Frozen Paper Object.
4. **Epistemic Integrity:** Tripartite epistemic attribution (`OBSERVATION`, `AUTHOR_INTERPRETATION`, `READER_ASSESSMENT`) is enforced in Ask interactions; internal Lens mechanics are strictly filtered.
5. **Firewalled Boundaries:** Project Apply requires explicit user invocation; Research Memory is blocked during pre-freeze Honest Reading.

---

## 2. Agentero Capability Discovery Summary

| Capability | Agentero Classification | Host Primitive |
|---|---|---|
| `OPEN_READER` | `NATIVE_WITH_ADAPTER` | Embedded HTML/web preview tab; Markdown viewer. |
| `GET_READER_SELECTION` | `NATIVE_WITH_ADAPTER` | Active text selection buffer. |
| `OPEN_EVIDENCE` | `CUSTOM_BRIDGE_REQUIRED` | Asset preview cards and modal inspection. |
| `OPEN_SOURCE` | `NATIVE_WITH_ADAPTER` | Built-in PDF viewer (`#page=N`). |
| `ASK_WITH_CONTEXT` | `NATIVE_WITH_ADAPTER` | Companion AI chat pane via ACP / BYOA / MCP. |
| `CREATE_PRIVATE_NOTE` | `NATIVE_WITH_ADAPTER` | Native `NOTES.md` and `marks/` directory. |
| `LIST_NOTES` | `NATIVE_WITH_ADAPTER` | Reading `NOTES.md` and `notes/notes.json`. |
| `UPDATE_NOTE` / `DELETE_NOTE` | `NATIVE_WITH_ADAPTER` | Updating note stores with immutability checks. |
| `PROPOSE_CORRECTION` | `CUSTOM_BRIDGE_REQUIRED` | Diff review UI representation. |
| `REVIEW_CORRECTION` | `CUSTOM_BRIDGE_REQUIRED` | Accept/reject review flow triggering FPO versioning. |
| `START_PROJECT_APPLY` | `CUSTOM_BRIDGE_REQUIRED` | Opt-in slash command `/apply`. |
| `QUERY_RESEARCH_MEMORY` | `CUSTOM_BRIDGE_REQUIRED` | Post-freeze SQLite/FTS5 search. |
| `DISPATCH_ACTION` | `NATIVE_WITH_ADAPTER` | Universal ACP JSON-RPC tool dispatch. |

*(Full details documented in `ISSUE25_AGENTERO_CAPABILITY_DISCOVERY.md`.)*

---

## 3. Paper Workspace Mapping in Agentero Vault

An Evidentia paper is housed inside the Agentero vault hierarchy:

```text
<vault>/papers/<paper-id>/
├── <paper-id>.pdf                 # Agentero archival PDF copy
├── NOTES.md                       # Agentero human Markdown notes
├── marks/                         # Agentero visual marks
└── evidentia/                     # Canonical Evidentia workspace root
    ├── reader/
    │   ├── paper_reader.html      # PRIMARY READING SURFACE
    │   ├── paper_reader.md        # Deep-reading Markdown report
    │   ├── paper_reader.pdf       # Vector print snapshot
    │   ├── evidence_atlas.html    # Interactive Evidence Atlas
    │   ├── evidence_atlas.json    # Structured evidence items
    │   ├── narrative_manuscript.json # Lead Writer manuscript
    │   └── frozen_paper_object.json  # Cryptographic FPO
    ├── model/                     # Source maps & inventories
    ├── source/                    # Bound source PDF
    ├── assets/                    # Page-localized figure/equation crops
    ├── notes/                     # Structured user notes store
    └── corrections/               # Formal non-mutating correction proposals
```

---

## 4. Subsystem Implementations

### A. Vault Layout & Path Resolution (`adapters/agentero/vault_layout.py`)
- Provides `AgenteroVaultLayout` to discover workspaces whether initialized from a vault root, paper directory, or standalone Evidentia folder.
- Synchronizes structured notes from `notes/notes.json` into human-friendly Markdown entries in `NOTES.md`.

### B. Core Adapter Bridge (`adapters/agentero/agentero_adapter.py`)
- Implements `AgenteroAdapter`:
  - `open_reader(anchor)`: returns `SET_ACTIVE_DOCUMENT` with file URI and anchor fragment (`#s1`);
  - `get_reader_selection()`: enriches text selection with bound evidence and page numbers;
  - `open_evidence(id)`: packages visual asset preview URIs and bidirectional links;
  - `open_source(page, region)`: opens PDF viewer at `#page=N` in verification mode;
  - `ask_with_context(q)`: grounds answers in Reader facts with tripartite epistemic attribution and zero lens leakage;
  - `create_private_note(text)`: writes structured note and updates `NOTES.md` while asserting zero FPO mutation;
  - `propose_correction(anchor, text)`: generates diff representation without mutating active reader;
  - `review_correction(id, decision)`: rejection leaves files unchanged; acceptance generates immutable version `v2`;
  - `start_project_apply(ctx)`: explicit post-freeze entry; isolates project context from ordinary Q&A;
  - `query_research_memory(q)`: queries cross-paper memory post-freeze;
  - `dispatch_action(act, payload)`: universal envelope router.

### C. ACP / MCP Protocol Bridge (`adapters/agentero/acp_bridge.py`)
- Exposes structured tool definitions (`open_reader`, `get_reader_selection`, `open_evidence`, `open_source`, `ask_with_context`, `create_private_note`, `propose_correction`, `start_project_apply`).
- `handle_acp_tool_call()` routes tool calls directly through `AgenteroAdapter.dispatch_action()`.

### D. CLI Management (`adapters/agentero/cli.py`)
- Standalone command-line utility for vault inspection, Reader launching, Ask queries, and note management.

---

## 5. Real-Paper End-to-End Validation

The adapter was rigorously validated against two structurally diverse real-paper fixtures across the complete 13-step sequence:
1. **LoRA (`BENCH-02-LORA-ADAPTATION`):** Empirical LLM adaptation paper with 7 sections, 204 evidence items, and visual figure/table crops.
2. **Rethinking Generalization (`UNSEEN-01-RETHINKING-GENERALIZATION`):** Theoretical deep learning paper with 6 sections and 73 evidence items.

### 13-Step Interaction Sequence Results

| Step | Action Verified | LoRA Result | UNSEEN-01 Result |
|---|---|---|---|
| 1 | Open paper through Agentero adapter | **PASS** | **PASS** |
| 2 | Verify Reader opens as primary surface | **PASS** (`default_surface = true`) | **PASS** (`default_surface = true`) |
| 3 | Select Reader text & resolve bound evidence | **PASS** (captured `F01`, `p.2`, `p.4`) | **PASS** (captured `p.1`, `p.2`) |
| 4 | Ask evidence-grounded question | **PASS** (`AUTHOR_INTERPRETATION`) | **PASS** (`AUTHOR_INTERPRETATION`) |
| 5 | Navigate to bound evidence item | **PASS** (`F01`, linked to `s2` & source) | **PASS** (`F01`, linked to `SEC-01`) |
| 6 | Inspect source PDF / page | **PASS** (`surface_role = VERIFICATION_ONLY`) | **PASS** (`surface_role = VERIFICATION_ONLY`) |
| 7 | Create persistent private note | **PASS** (`notes.json` + `NOTES.md` synced) | **PASS** (`notes.json` + `NOTES.md` synced) |
| 8 | Verify FPO manuscript SHA unchanged | **PASS** (100% identical hash) | **PASS** (100% identical hash) |
| 9 | Create correction proposal | **PASS** (`status = PROPOSED`) | **PASS** (`status = PROPOSED`) |
| 10 | Reject once and prove no mutation | **PASS** (zero file changes) | **PASS** (zero file changes) |
| 11 | Accept controlled correction $\rightarrow$ `v2` | **PASS** (`v2` created; `v1` intact) | **PASS** (`v2` created; `v1` intact) |
| 12 | Invoke explicit Project Apply | **PASS** (`apply/` initialized) | **PASS** (`apply/` initialized) |
| 13 | Verify ordinary Reader Q&A protected | **PASS** (zero project pollution) | **PASS** (zero project pollution) |

---

## 6. Honest Capability Gaps Disclosure

As detailed in `ISSUE25_AGENTERO_GAPS.md`:
1. **Sub-pixel PDF Region Highlighting:** Agentero navigates to `#page=N` but lacks native polygon/bounding-box overlays on PDF pages. Workaround: adapter attaches pixel-accurate asset crop previews (`crop_*.png`).
2. **HTML Preview Deep Links:** Handled losslessly via standard URI fragments (`#s1`, `#ch-s1`).
3. **Structured Multi-Block Selection:** Handled losslessly via backend AST fuzzy-alignment in `narrative_manuscript.json`.
4. **Rich Epistemic Note Metadata:** Handled losslessly via dual-layer storage (`notes.json` structured store + `NOTES.md` human Markdown).
5. **Non-Mutating Correction Diff Lifecycle:** Handled losslessly by intercepting accept actions and redirecting to Evidentia's `v2` versioning engine.

---

## 7. Deterministic Test Results

- `tests/test_agentero_adapter.py`: **12 passed** in 1.08s
- `tests/test_workspace_contract.py`: **9 passed** in 0.60s
- `tests/test_workspace_real_papers.py`: **3 passed** in 0.42s
- Full test suite: **193 passed**, 0 failed across entire repository.
- Scientific semantics changed: **NO**.
