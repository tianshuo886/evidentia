# Architecture invariants

1. Source reconstruction precedes interpretation.
2. `paper_model.json` and `evidence_graph.json` are canonical, schema-validated facts.
3. Six Lens files are independent rereads of a frozen base; merge keeps provenance.
4. Freeze writes hashes; apply must verify them before creating a Research Delta.
5. The Reader is an adapter with its own information architecture. Kami tooling may provide typography, MathJax and PDF print support only.
6. Paper and Project views share one HTML surface but never share mutable data.
