# Evidentia Reader Presentation Contract

## Core Principle

> **Evidentia owns truth. AI owns narrative. Kami owns presentation.**

The machine model must optimize for correctness and traceability.  
The human Reader must optimize for comprehension and scientific narrative.  
Kami must optimize for document presentation.  
These are three separate responsibilities and must remain distinct.

---

## 1. Dual-Surface Output Architecture

Evidentia outputs two distinct reading surfaces from every paper reading run:

### A. Primary Human Reader (`paper_reader.html`, `paper_reader.pdf`, `paper_reader.md`)

- **Target Audience**: Human researchers seeking deep scientific comprehension.
- **Form Factor**: Editorial long-document, Chinese-first, paragraph-dominant.
- **Presentation Backend**: Kami Chinese long-document system (`long-doc.html`), rendered via Kami's pipeline.
- **Aesthetic**:
  - Parchment warm background (`#f5f4ed`)
  - Warm ivory callout containers (`#faf9f5`)
  - Ink-black text (`#141413`) with olive/dark-warm secondary shades (`#3d3d3a`, `#504e49`)
  - Single brand accent: Navy / Ink-blue (`#1B365D`)
  - Typography: Chinese serif (`TsangerJinKai02` / `Source Han Serif SC` / `Songti SC`)
  - Generous editorial whitespace and chapter rhythm
- **Flow**:
  - Cover with clean title, subtitle, author/venue metadata (no internal hashes or machine IDs)
  - Kami-native Table of Contents
  - 7 Narrative Chapters:
    1. 一分钟理解这篇论文 (Executive summary with lead paragraph and key takeaways)
    2. 论文为什么要做这件事 (Motivation, existing gap, entry point, significance in continuous prose)
    3. 方法是怎么工作的 (End-to-end mechanism, components, equations, assumptions)
    4. 哪些实验真正决定了论文是否成立 (Decisive experiments with inline figures/tables and caveats)
    5. 六个 Lens 合起来，我们应该怎样理解这篇论文 (Synthesized across lenses by scientific topic, not by lens headings)
    6. 哪些东西值得复用 (Source-grounded portable methods, losses, evaluation protocols)
    7. 结论与边界 (Established findings, unproven boundaries, practical precautions)
  - Quiet Appendix linking to the Evidence Atlas
- **Evidence References**: Quiet, local citations (e.g. `[E: F01]`, `[Claim C01]`), never noisy dashboard badges.
- **Chrome**: Zero dashboard grids, verifier badges, or hash status in the primary reading flow.

### B. Secondary Inspection Surface: Evidence Atlas (`evidence_atlas.html`)

- **Target Audience**: Auditors, verifiers, and researchers inspecting provenance.
- **Form Factor**: Dense, claim-centric audit dashboard.
- **Contents**:
  - Claim cards with full IDs (`C01`, `C02`, ...)
  - Observation / Author Interpretation / Reader Assessment (O/I/A) breakdown
  - Verifier status (`VERIFIED`, `CONTRADICTION`, `TENSION`, `UNRESOLVED`)
  - Epistemic states (`SUPPORTED`, `PARTIAL`, `AMBIGUOUS`, etc.)
  - Lens trace and cross-lens conflicts with resolution history
  - Source SHA256 hashes and page references
  - Full bidirectional anchor navigation (Claim ↔ Evidence round-trips)

---

## 2. Forbidden Anti-Patterns (Primary Reader)

The primary Paper Reader must explicitly reject:

1. **Card-per-field layout**: Mapping each IR JSON field into a separate box or card.
2. **Badge-heavy prose**: Peppered status badges (`[SUPPORTED]`, `[VERIFIED]`) inside narrative paragraphs.
3. **Machine IDs in headings**: E.g., `### C01: ...` or `### Figure F01 Block`.
4. **Repeating IR keys as headings**: Turning internal dictionary keys into visual headlines.
5. **Dashboard-style 2-column box grids**: Stacking `.grid-2` boxes across narrative sections.
6. **Raw Lens segregation**: Exposing six separate "Lens Reports" instead of synthesizing them by topic.
7. **Invented scientific boilerplate**: Generating domain claims from Python string fallbacks.
8. **Font shrinking**: Shrinking text sizes artificially to force content onto page boundaries.
9. **Visual noise**: Emoticons, decorative icons, or multi-colored status tags as structural hierarchy.

---

## 3. Strict Fallback Prose Rules

Renderer code is **scientifically dumb**. Production renderers may format or label content, but may never author domain-specific scientific prose.

### Allowed
- Structural UI labels (e.g., "核心发现", "方法机制", "关键实验").
- Neutral metadata labels (e.g., "作者", "发表年份", "引用依据").
- Explicit placeholders used only in test fixtures.
- Deterministic formatting (wrapping text in tags, date formatting, anchor links).

### Forbidden in Production
- Fabricated scientific mechanisms or mathematical interpretations.
- Invented methodological limitations or caveats not present in source evidence.
- Invented optimizer (e.g. "AdamW"), learning-rate warmup, or hyperparameter recommendations.
- Generic figure reading guides that assume axes, error bars, or baselines without source evidence.
- Domain assumptions (e.g. "独立同分布高斯分布", "多模态数据时存在的表征瓶颈").
- Any claim inserted simply because a field was empty in the source JSON.

### Uncertainty Standard
When source evidence is missing, ambiguous, or incomplete, the system must use explicit uncertainty:
- `未在当前证据中确认`
- `论文未明确说明`
- `当前无法可靠判断`

Never fill empty fields with plausible-sounding domain prose.
