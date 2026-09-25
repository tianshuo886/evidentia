# Reader QA contract

Reader QA has two layers:

1. **Machine audit:** `reader_audit.py` checks that every canonical Claim and Figure is represented in `render_ir.json`, every asset exists, no template token remains, and the Reader is generated.
2. **Visual audit:** inspect HTML and PDF at Dashboard, Claim Card, Evidence Atlas, Figure Evidence Block, Weakest Link and Project Delta boundaries. Confirm original captions, page anchors, math, figure clarity, no clipping, and distinct Paper/Project styling.

A PDF that renders successfully is not evidence that the layout is readable. Visual inspection remains a required human step because pixels and captions cannot be fully judged by JSON validation.
