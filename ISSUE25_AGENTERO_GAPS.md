# Evidentia · Issue #25 Agentero Capability Gaps Analysis

**Issue #25: Agentero Adapter — Reference Implementation of the Reader-First Workspace Contract**  
*Honest Technical Audit of Host Limitations and Workarounds*

---

## 1. Principles of Gap Disclosure

Evidentia Core prioritizes scientific rigor and truthfulness over superficial cosmetic completeness. Where Agentero's desktop or protocol primitives cannot natively satisfy a requirement of the Workspace Contract:
1. We document the gap explicitly and truthfully;
2. We implement the nearest truthful workaround without faking precision;
3. We preserve the Frozen Reader as the ultimate scientific authority;
4. We do not construct massive custom UI replacements just to hide host limitations.

---

## 2. Capability Gaps Inventory

### Gap 1: Sub-pixel PDF Bounding-Box Region Highlighting
- **What Evidentia Requires:** When a user inspects an evidence item (e.g. `crop_F01_p1_151x153.png`) or invokes `OPEN_SOURCE(page, region)`, the source surface should ideally outline the exact bounding box $(x, y, w, h)$ on the PDF page.
- **What Agentero Provides:** Agentero's PDF viewer supports standard page-level jumps (`#page=N`) and text search highlighting, but does not provide a public protocol or DOM hook for arbitrary polygon/rectangle coordinate overlays on raw PDF pages.
- **Adapter Workaround:** 
  - The adapter navigates to the exact page (`#page=N`);
  - It attaches the verified visual crop asset (`assets/figures/...` or `assets/equations/...`) as an adjacent preview card;
  - It exposes textual coordinate metadata in the inspection envelope.
- **Is Workaround Lossless?** **Partially.** The visual evidence crop itself is 100% authentic and pixel-accurate (extracted during Phase A source reconstruction), but the highlighted border overlay on the full PDF page in Agentero is omitted.
- **Future Enhancement Recommendation:** Propose an ACP extension to Agentero for rendering visual bounding-box overlays (`viewer.highlightRect(page, [x, y, w, h])`).

---

### Gap 2: Native Reader-Anchor Deep Linking in HTML Preview
- **What Evidentia Requires:** When opening the Reader with `OPEN_READER(anchor="s2")`, the host should smoothly scroll and focus directly on Section 2 (`<a id="s2"></a>` or `<div id="ch-s2">`).
- **What Agentero Provides:** Agentero has native heading deep-linking for its internal Markdown notes (`[[note#heading]]`), but its embedded web/HTML preview tab handles external HTML files as static file URIs (`file:///.../paper_reader.html`).
- **Adapter Workaround:** The adapter generates standard URI fragments (`file:///.../paper_reader.html#s2` and `file:///.../paper_reader.html#ch-s2`), which standard WebKit/Chromium Electron webviews natively scroll to, and returns the resolved section heading and character position in the response envelope.
- **Is Workaround Lossless?** **Yes.** Standard HTML fragment navigation works reliably in modern desktop webviews.
- **Future Enhancement Recommendation:** Expose native desktop tab anchor events via ACP so that companion agent windows receive anchor scroll events.

---

### Gap 3: Structured Multi-Block Selection Metadata
- **What Evidentia Requires:** `GET_READER_SELECTION` should identify whether a selection spans multiple epistemic blocks (e.g. a paragraph plus an equation), extracting separate evidence citations for each block.
- **What Agentero Provides:** Agentero's selection event passes a raw text string and broad bounding box coordinates from the active webview.
- **Adapter Workaround:** The adapter takes the raw selected string and fuzzy-aligns it against the structured AST in `narrative_manuscript.json`, reconstructing all enclosing blocks, section IDs, and bound evidence references.
- **Is Workaround Lossless?** **Yes.** Evidentia's in-memory manuscript AST guarantees exact block identification from substring matching.
- **Future Enhancement Recommendation:** None needed; backend AST alignment is more reliable than frontend DOM scraping.

---

### Gap 4: Rich Epistemic Note Metadata in Plain Markdown
- **What Evidentia Requires:** `CREATE_PRIVATE_NOTE` stores rich metadata including target anchors, evidence IDs, source pages, timestamps, author type (`USER`), and cryptographic mutation assertions.
- **What Agentero Provides:** Agentero stores paper notes in a plain Markdown file (`NOTES.md`) for human note-taking and Obsidian interoperability.
- **Adapter Workaround:** The adapter implements **dual-layer storage**:
  1. The canonical structured record is stored in `evidentia/notes/notes.json` conforming to `schemas/private_note.schema.json`;
  2. A formatted Markdown representation is synchronized into Agentero's `NOTES.md` with backlink footers:
     ```markdown
     > **[s2 | F01]** Note text here...
     <!-- evidentia:note-id=note-257726c5250b -->
     ```
- **Is Workaround Lossless?** **Yes.** Human users see natural Markdown notes in Agentero and Obsidian, while Evidentia preserves strict schema-validated records.
- **Future Enhancement Recommendation:** Native Agentero note metadata frontmatter support.

---

### Gap 5: Non-Mutating Scientific Correction Diff Lifecycle
- **What Evidentia Requires:** Corrections proposed by humans must never edit the active Reader in-place. Acceptance must produce a versioned new Frozen Paper Object (`v2`), preserving `v1` immutability.
- **What Agentero Provides:** Agentero's diff review panel is designed for git-style file patches where accepting an edit overwrites the file in-place.
- **Adapter Workaround:** The adapter intercepts the accept action from Agentero's review panel. Rather than overwriting `narrative_manuscript.json`, it calls `WorkspaceSession.review_correction(ACCEPT)`, writing the patch to `versions/v2/narrative_manuscript.json` and generating `frozen_paper_object.v2.json`. The original version remains permanently immutable.
- **Is Workaround Lossless?** **Yes.** This completely prevents silent scientific mutation while giving the user a familiar diff-review experience.
- **Future Enhancement Recommendation:** Agentero could add native support for immutable versioned document forks.
