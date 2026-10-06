# Evidentia · Issue #25 Agentero Capability Discovery

**Issue #25: Agentero Adapter — Reference Implementation of the Reader-First Workspace Contract**  
*Capability Discovery & Architectural Pre-flight Audit*

- **Target Host:** Agentero (`poco-ai/Agentero`)
- **Protocol Standards:** Local Vault, Agent Client Protocol (ACP), Model Context Protocol (MCP), BYOA (Bring Your Own Agent)
- **Host Role:** Optional downstream reference host for human-agent interaction
- **Evidentia Stance:** Evidentia Core remains host-neutral and fully functional without Agentero installed.

---

## 1. Executive Summary & Host Inventory

Agentero is an open-source, local-first academic research workbench developed by Poco-AI. Its architecture unifies literature storage, PDF viewing, dual-linked Markdown notes (`[[wikilinks]]`), and AI agent companions without vendor lock-in.

### Inventory of Actual Agentero Primitives

| Component / Subsystem | Host Mechanism in Agentero | Evidentia Relevance |
|---|---|---|
| **Vault / Library Organization** | Plain-text local directory containing paper folders, metadata, PDFs, and `.agents/` configuration. | Direct filesystem alignment with Evidentia paper workspaces (`papers/<paper-id>/evidentia/`). |
| **Document Viewing Surfaces** | Dual-pane split viewer: PDF reader on the left, interactive AI companion / Markdown note editor on the right. | **Critical divergence:** Agentero defaults to raw PDF on the left. The Evidentia adapter must enforce a **Reader-first default** by serving `paper_reader.html` as the primary reading document. |
| **Deep Links & Anchors** | PDF page navigation (`#page=N`) and Markdown heading links (`[[note#heading]]`). No native semantic HTML anchor jump for external readers. | Adapter must bridge Reader section anchors (`#s1`, `ch-s1`) and Evidence IDs (`evidence-T01`) to HTML iframe navigation or URI fragments. |
| **Highlights & Visual Marks** | Canvas/DOM text selections persisted as JSON under `marks/` or inline annotations. | Mapped to Evidentia's post-freeze human annotation layer; zero mutation of frozen paper facts. |
| **Persistent Notes** | Per-paper `NOTES.md` and vault-level Markdown files supporting Obsidian-style `[[wikilinks]]`. | Bidirectional synchronization with Evidentia `notes/notes.json`; isolated from scientific core. |
| **Selection Retrieval** | Desktop UI selection event passing selected text and bounding box to companion pane. | Mapped to `GET_READER_SELECTION`; enriched with Evidentia bound evidence references before agent handoff. |
| **Agent Execution (BYOA / ACP)** | Agent Client Protocol (ACP) enables local coding agents (Claude Code, Codex, CLI) to receive state and dispatch tools. | Adapter exposes Evidentia Workspace Contract actions as ACP tools/commands without leaking model names into core contracts. |
| **Model Context Protocol (MCP)** | Agentero acts as an MCP server, exposing vault documents and notes to external MCP clients (Claude Desktop, etc.). | Adapter exposes Evidentia tools (`open_reader`, `ask_with_context`, `open_evidence`) via standard MCP tool definitions. |
| **Diff-Style Human Review** | Review panel showing git/text diffs before applying agent file edits. | Leveraged as presentation infrastructure for Evidentia's `PROPOSE_CORRECTION` / `REVIEW_CORRECTION` lifecycle. |
| **CLI / Headless Interface** | `agentero-cli` and agent skills for automated headless vault management. | Adapter can run headlessly or inside desktop app environment. |

---

## 2. Workspace Contract Capability Mapping Matrix

Every capability defined in Evidentia's canonical Workspace Contract (`schemas/workspace_contract.schema.json`) is classified into exactly one of:
- `NATIVE`: Fully supported out-of-the-box by Agentero.
- `NATIVE_WITH_ADAPTER`: Agentero has the underlying primitive; adapter provides schema translation or layout wrapping.
- `CUSTOM_BRIDGE_REQUIRED`: Agentero lacks the domain concept; adapter implements a dedicated bridge.
- `UNSUPPORTED`: Not feasible in Agentero; requires documented workaround or graceful degradation.

| Workspace Capability | Agentero Classification | Host Primitive in Agentero | Adapter Bridge Strategy |
|---|---|---|---|
| **`OPEN_READER`** | `NATIVE_WITH_ADAPTER` | Web/HTML preview & Markdown document viewer. | Overrides default raw PDF view to open `paper_reader.html` (or `paper_reader.md`). Resolves section anchors (`#s1`). |
| **`GET_READER_SELECTION`** | `NATIVE_WITH_ADAPTER` | UI active selection event buffer. | Captures selected text string and passes to `WorkspaceSession.get_reader_selection()`, which appends bound evidence IDs and source pages. |
| **`OPEN_EVIDENCE`** | `CUSTOM_BRIDGE_REQUIRED` | No native concept of "Evidence Atlas item". | Adapter resolves `evidence_id` (`F01`, `T01`) to crop image asset, caption, verification status, and bidirectional links to source and Reader. |
| **`OPEN_SOURCE`** | `NATIVE_WITH_ADAPTER` | Built-in PDF reader with page navigation (`#page=N`). | Opens source PDF at specified page. Marks surface as `VERIFICATION_ONLY` to uphold Reader-first principle. |
| **`ASK_WITH_CONTEXT`** | `NATIVE_WITH_ADAPTER` | Side-panel companion chat via ACP / BYOA agent runtime. | Packages selection + bound evidence objects + tripartite epistemic classification into prompt context. Excludes internal Lens mechanics. |
| **`CREATE_PRIVATE_NOTE`** | `NATIVE_WITH_ADAPTER` | `NOTES.md` and `marks/` directory in paper vault. | Appends note to `NOTES.md` and saves structured record to `notes/notes.json`. Computes Reader SHA before/after to assert zero mutation. |
| **`LIST_NOTES`** | `NATIVE_WITH_ADAPTER` | Reading `NOTES.md` / `notes/notes.json`. | Reads notes store, filtering by anchor or evidence ID. |
| **`UPDATE_NOTE`** | `NATIVE_WITH_ADAPTER` | Editing `NOTES.md` / `notes/notes.json`. | Updates note record; verifies Reader SHA unchanged. |
| **`DELETE_NOTE`** | `NATIVE_WITH_ADAPTER` | Removing entry from `NOTES.md` / `notes/notes.json`. | Removes note record; verifies Reader SHA unchanged. |
| **`PROPOSE_CORRECTION`** | `CUSTOM_BRIDGE_REQUIRED` | Diff review UI (agent file modification preview). | Adapter records formal proposal in `corrections/proposals.json` without modifying base reader text. Uses Agentero diff viewer for preview. |
| **`REVIEW_CORRECTION`** | `CUSTOM_BRIDGE_REQUIRED` | Human accept/reject button in review UI. | Rejection alters zero files. Acceptance triggers Evidentia versioning engine: creates immutable `v2` FPO and manuscript, retaining `v1` intact. |
| **`START_PROJECT_APPLY`** | `CUSTOM_BRIDGE_REQUIRED` | Custom slash command `/apply` or action button. | Opt-in post-freeze trigger requiring non-empty `project_context`. Spawns Apply envelope without polluting honest reading. |
| **`QUERY_RESEARCH_MEMORY`** | `CUSTOM_BRIDGE_REQUIRED` | Vault-wide FTS5 / [[wikilink]] graph search. | Post-freeze query into Evidentia SQLite/FTS5 memory; strictly blocks unfrozen runs. |
| **`DISPATCH_ACTION`** | `NATIVE_WITH_ADAPTER` | ACP JSON-RPC / MCP tool dispatch envelope. | Universal envelope serialization connecting Agentero tools to `WorkspaceSession.dispatch_action()`. |

---

## 3. Key Findings & Adapter Guardrails

1. **Do not rebuild UI that Agentero provides:**
   - Agentero already provides dual-pane layout, PDF viewing, Markdown note editing, and agent chat transport. Evidentia will not build a custom PDF viewer, Markdown editor, or chat window.
2. **Prevent raw-PDF-first regression:**
   - Agentero's default behavior opens `<paper-id>.pdf` in the main view. The adapter must explicitly configure workspace file associations so that opening an Evidentia-processed paper loads `reader/paper_reader.html` (or `reader/paper_reader.md`) as the primary document.
3. **Isolate scientific facts from human notes:**
   - Agentero `NOTES.md` and annotations are strictly human layer artifacts. They are post-freeze by default and must never silently mutate the Frozen Paper Object.
4. **Honest capability gap handling:**
   - Agentero does not support sub-pixel bounding-box region highlighting inside PDFs. The adapter maps `OPEN_SOURCE(page, region)` to exact page navigation plus visual evidence crop previews, truthfully acknowledging the host limitation rather than faking unsupported coordinates.
