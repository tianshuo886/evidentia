# Kami integration

Evidentia and [Kami](https://github.com/tw93/Kami) have different responsibilities:

- Evidentia owns Paper Model, Evidence Graph, natural paper structure, Figure/Table provenance, six Lens rereads, Research Delta and Reader information architecture.
- Kami owns document production capabilities: typography, MathJax, PDF rendering, page images, font checks, orphan checks, density checks and visual checks.

Kami must not define the scientific structure. Evidentia renders its own `render_ir.json` and `reader/reader.html`; Kami is then used as the presentation and visual QA backend.

## Setup

```bash
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

If Kami is unavailable, Evidentia's own HTML/PDF fallback remains usable. It is a fallback renderer, not a replacement for Kami's visual QA.
