# paper_model.json — canonical truth schema (v1)

Top-level keys only. No rendering fields here; presentation lives in `render_ir.json`.

```json
{
  "paper": {"title": "", "authors": [], "venue": "", "year": null,
            "doi": "", "pdf_sha256": ""},
  "natural_structure": ["Existing failure", "New mechanism", "..."],
  "paper_type": "method|empirical|theory|dataset|benchmark|review|hybrid",
  "questions": [{"id": "Q01", "text": "", "page": null}],
  "claims": [{"id": "C01", "statement": "", "page": null,
              "evidence": ["F06", "E04"],
              "epistemic": "VERIFIED|SUPPORTED|PARTIAL|NOT_STATED|AMBIGUOUS|INSUFFICIENT_EVIDENCE|MODEL_UNCERTAIN|NEEDS_SUPPLEMENT|NEEDS_CITATION_TRACE",
              "evidence_scope": "IN_PAPER_EVIDENCE|CITED_EVIDENCE"}],
  "observations": [{"id": "O01", "text": "", "source": ["F06"], "page": null}],
  "author_interpretations": [{"claim": "C01", "text": "", "page": null}],
  "reader_assessments": [{"claim": "C01", "verdict": "", "reason": "", "epistemic": "SUPPORTED"}],
  "experiments": [{"id": "E01", "question": "", "design": "", "variables": "",
                   "control": "", "result": "", "supports": ["C01"],
                   "limitation": "", "page": null}],
  "figures": [{"id": "F06", "paper_label": "Fig. 6", "page": 9,
               "caption_original": "", "role": "critical|supporting|context|diagnostic",
               "depth": "deep|normal|light",
               "question": "", "observation": "", "author_interpretation": "",
               "reader_assessment": "", "supports_claims": ["C05"],
               "limitations": ["B02"], "open_questions": ["Q04"],
               "file": "assets/figures/fig06_p9_1555x1091.png"}],
  "methods": [{"name": "", "mechanism": "A → B → C", "assumptions": ["A01"],
               "novelty_vs_sota": "", "page": null}],
  "data": {"sources": [], "scale": "", "preprocessing": "", "splits": "",
           "leakage_risk": "", "metrics": "", "page": null},
  "assumptions": [{"id": "A01", "text": "", "page": null}],
  "limitations": [{"id": "B01", "text": "", "self_admitted": true, "page": null}],
  "open_questions": [{"id": "Q04", "text": "", "source": ["F06"]}],
  "anomalies": [],
  "side_findings": [],
  "portable_components": [{"name": "", "io": "", "page": null}],
  "argument_chain": ["Problem", "Hypothesis", "Design", "Experiment",
                     "Observation", "Claim", "Boundary"]
}
```

## evidence_graph.json

`{"nodes": [{"id": "C07", "kind": "claim|experiment|figure|assumption|boundary|question"}],
  "edges": [{"from": "C07", "rel": "supported_by|depends_on|challenged_by|limited_by",
             "to": "F06"}]}` — every claim reachable to ≥1 evidence node.

## render_ir.json (presentation only)

`{"dashboard": {...}, "paper_map": [...], "claim_cards": [...],
  "figure_blocks": [...], "experiment_cards": [...], "delta_section": null|{...}}`.
Adapter rule: drop nothing silently; unresolved stays visible.
