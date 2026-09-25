# Kami integration (required backend)

Kami is a required dependency of Evidentia, not an optional enhancement.
Without Kami there is no visual QA: `scripts/kami_adapter.py` exits non-zero
when `KAMI_ROOT` is unset or `reader/reader.pdf` is missing, and a Reader
without `reader/kami_audit.json` (status OK) is draft-only, not shippable.

Evidentia and [Kami](https://github.com/tw93/Kami) (tested with v1.16.0) have different responsibilities:

- Evidentia owns Paper Model, Evidence Graph, natural paper structure, Figure/Table provenance, six Lens rereads, Research Delta and Reader information architecture.
- Kami owns document production capabilities: typography, MathJax, PDF rendering, page images, font checks, orphan checks, density checks and visual checks.

Kami must not define the scientific structure. Evidentia renders its own `render_ir.json` and `reader/reader.html`; Kami is then used as the presentation and visual QA backend.

## Setup (required)

`KAMI_ROOT` may point at a full Kami checkout or at an installed kami skill
directory. The adapter resolves `skills/kami/scripts/build.py` first, then
`scripts/build.py`, so both layouts work:

```bash
# Option A: you already have the /kami skill installed
export KAMI_ROOT=~/.agents/skills/kami

# Option B: full repo checkout (tested with v1.16.0)
git clone https://github.com/tw93/Kami.git
export KAMI_ROOT=/path/to/Kami
```

## Run

```bash
python scripts/render_reader.py --out output
python scripts/reader_audit.py --out output
python scripts/kami_adapter.py --out output --kami-root "$KAMI_ROOT"
```

The adapter calls Kami's `build.py` checks for visual rendering, orphan text, density and fonts. It writes `reader/kami_audit.json`. A successful machine check still requires opening the generated page images and confirming figure clarity, caption binding, page breaks, math and Paper/Project visual distinction.

Evidentia's own HTML/PDF rendering is a content fallback for HTML-only reading. It is not a substitute for Kami's visual QA: skipping the adapter leaves the Reader in draft state.
