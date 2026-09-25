# Unified Paper Reader contract

`paper_model.json` is canonical truth. `scripts/render_reader.py` produces the primary `reader/reader.html`, a PDF snapshot, and `render_ir.json`. The Reader has three depths: 30-second dashboard, 5-minute argument and claim map, and 30–60-minute Evidence Atlas. Paper facts use ink-blue styling; project deltas use olive styling and live in separate `apply/<project>/research_delta.json` files. The Kami adapter may reuse typography, math and print tooling, but its long-document schema cannot determine the Paper Reader information architecture.
