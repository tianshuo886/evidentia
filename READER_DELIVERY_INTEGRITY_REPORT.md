# Reader Delivery Integrity & Offline Asset Remediation Report (Issue #43)

## 1. Executive Summary

This report documents the resolution of **Issue #43 (Delivery Integrity)** as part of the P0 Reader Scientific Quality Remediation series on `tianshuo886/evidentia`.

Prior to this fix, the delivered human-facing Reader HTML artifacts contained presentation-layer flaws including 15 broken internal anchor targets, 1 self-loop anchor, 15 unparsed literal `\n` sequences, duplicate publication year rendering (`2026 · 2026`), duplicate citation pills (`〔p.1, p.2〕 [p.1] [p.2]`), and image clipping on high-resolution figures.

All 6 delivery defects have been resolved systematically in `scripts/render_paper_reader.py`, verified with a new deterministic auditor (`scripts/reader_delivery_audit.py`), integrated as a formal fail-closed acceptance gate in `scripts/reader_acceptance.py`, and verified with 275 passing tests across the repository.

---

## 2. Quantitative Verification & Before/After Comparison

The verification was conducted deterministically against both the defective baseline (`evals/reader_v3/semantic_regressions/ringmoclaw/oct13_run/reader.html`, SHA256 `e9a14884c0c2cba03e7be3678f6373989e8666b38c84d53d7cd0011e702f45ac`) and the freshly rendered deliverable:

| Delivery Metric | Defective Baseline (`oct13_run`) | Remediated Delivery Output | Verification Gate |
| :--- | :---: | :---: | :---: |
| **Unresolved Internal Fragment Targets** | **15** (`evidence-EQ-05`, `evidence-T04`, `p.2`–`p.20`) | **0** (All validly resolved) | `delivery_integrity` |
| **Self-Loop Anchors** | **1** (`<a id="p.1" href="#p.1">`) | **0** (Clean `<span>` anchors) | `delivery_integrity` |
| **Literal Unparsed `\n` Sequences** | **15** (`\\n1. `, `\\n2. `, etc.) | **0** (Valid HTML breaks `<br>`) | `delivery_integrity` |
| **Cover Duplicate Year** | **1** (`2026 · 2026`) | **0** (`2026` rendered once) | `delivery_integrity` |
| **Prose Citation Duplication** | **17** duplicate pill clusters | **0** (Deduplicated inline pills) | `delivery_integrity` |
| **Relocatable Asset Handlers** | Missing (`onerror` absent) | **Present** on all figures/tables | `delivery_integrity` |
| **Figure Max-Height & Object Fit** | `380px`, no `object-fit` | `520px; object-fit: contain;` | CSS Inspection |
| **Print Media Styles** | None | `@media print` page breaks & containment | CSS Inspection |

---

## 3. Detailed Root Causes & Architectural Fixes

### 3.1. Internal Fragment Resolution & Elimination of Self-Loops
- **Root Cause**:
  1. The page anchor generator in `#ch-sources` only extracted page numbers from `paper_model.json` top-level entities, ignoring page references cited within manuscript prose and evidence references. Consequently, `p.2`, `p.4` ... `p.20` had no matching elements with `id="p.N"`.
  2. Unrendered evidence items (`EQ-05`, `T04`) cited in narrative paragraphs generated `#evidence-EQ-05` links even though they were only present in `evidence_atlas.html`.
  3. `p.1` was rendered as `<a id="p.1" href="#p.1">p.1</a>`, which is a self-loop anchor pointing to its own element.
- **Fix**:
  1. Implemented two-pass DOM ID collection in `render_paper_reader_html`: Pass 1 scans all section blocks, evidence references, and in-text `p.N` patterns to dynamically assemble `local_ids`.
  2. Citations for evidence not rendered in the narrative story are routed to `evidence_atlas.html#evidence-{id}`.
  3. Page anchors are generated as `<span class="page-anchor" id="p.{n}"><a href="../source/paper.pdf#page={n}" target="_blank">p.{n}</a></span>` (or plain span if source PDF is unavailable), eliminating self-loops and providing functional PDF jump points.

### 3.2. Literal `\n` Escape Normalization
- **Root Cause**: JSON string deserialization or model authoring produced escaped `\\n` (ASCII 92 + 110) sequences in text fields (`\n1. `, `\n2. `). Previous code used `text.replace('\n', '<br>')` which only replaced ASCII 10 (line feed), leaving literal `\n` printed as visible text in the browser.
- **Fix**:
  - Implemented `normalize_text_newlines(text: str) -> str`, which translates non-LaTeX `\\n` into actual newline characters while safely preserving LaTeX math commands (`\nabla`, `\neq`, `\nu`, `\notin`, `\null`, `\ni`, `\neg`, `\ne`, `\natural`, `\nearrow`, `\nwarrow`, `\norm`).
  - Integrated into `sanitize_editorial_text`, ensuring all paragraphs, callouts, takeaways, and analyses format numbered lists and line breaks cleanly into `<br>` and `</p><p>`.

### 3.3. Cover Metadata Year Deduplication
- **Root Cause**: `meta_line` concatenated `authors`, `venue`, and `str(year)`. When `venue` was formatted as `arXiv:... (preprint · venue unverified) · 2026`, appending `2026` produced `2026 · 2026`.
- **Fix**: Implemented `format_meta_line(authors, venue, year)` using regex word-boundary checks (`rf'\b{re.escape(year_str)}\b'`) to verify whether the publication year is already present in `venue` before appending. Applied across both HTML and Markdown renderers.

### 3.4. Inline Citation Pill Deduplication
- **Root Cause**: Lead Writer prose contained Chinese citation brackets (e.g. `〔p.1, p.2〕`), while `evidence_refs` also listed `['p.1', 'p.2']`. `render_block_html` appended trailing `{cites}`, causing duplicate pills: `...〔p.1, p.2〕 [p.1] [p.2]`.
- **Fix**: Implemented `format_cites_in_text_html(text, local_ids)`:
  - In-text `〔...〕` brackets are parsed and directly converted into styled citation pill spans (`<span class="evidence-cites"><a ...>...</a></span>`).
  - The referenced IDs are tracked, and only *unreferenced* items in `evidence_refs` are appended at the end.
  - Markdown renderer mirrors this deduplication, eliminating duplicate markdown brackets (`〔...〕 〔...〕`).

### 3.5. Relocatable Offline Bundles & Presentation Quality
- **Root Cause**: Static relative image paths (`../assets/...`) broke if bundles were moved or opened in flat directory layouts. Small figure container heights (`max-height: 380px`) caused high-aspect ratio figures to appear compressed.
- **Fix**:
  - Added `onerror` fallback handlers on all figure, table, and equation images: `onerror="this.onerror=null; this.src=this.src.includes('../')?this.src.replace('../',''):('../'+this.src);"`
  - Updated `KAMI_LONG_DOC_CSS` figure rules: `max-height: 520px; object-fit: contain;`
  - Added comprehensive `@media print` rules enforcing page breaks before chapters (`break-before: page;`) and preventing awkward block splitting (`break-inside: avoid;`).

---

## 4. Verification & Gate Integration

1. **Deterministic Delivery Auditor (`scripts/reader_delivery_audit.py`)**:
   - Command-line and programmatic API auditing HTML DOM and Markdown for unresolved targets, self-links, literal escapes, duplicate years, duplicate citations, and missing image files.
2. **Acceptance Gate Integration (`scripts/reader_acceptance.py`)**:
   - Added `"delivery_integrity"` to the formal `GATES` tuple.
   - Evaluated as fail-closed gate `errors.gate = "delivery_integrity"`.
3. **Unit & Regression Test Coverage (`tests/test_reader_delivery_integrity.py`)**:
   - `test_defective_oct13_artifact_fails_delivery_audit`: Verifies exact diagnostic failure of defective fixture across all 5 checks.
   - `test_regenerated_reader_passes_delivery_audit`: Verifies 100% pass on regenerated reader.
   - `test_delivery_integrity_gate_registered_in_acceptance`: Verifies gate registration.
   - `test_css_figure_dimensions_and_print_rules`: Verifies CSS presentation and print rules.
   - `test_image_relocatable_onerror_handler`: Verifies relocatable fallback handlers.
4. **Repository-Wide Test Suite**:
   - 275 tests passed (`pytest` 100% green).
