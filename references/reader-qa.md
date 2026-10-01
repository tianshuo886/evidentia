# Reader QA contract

Reader QA has two layers:

1. **Machine audit:** `reader_audit.py` checks that every canonical Claim and Figure is represented in the compatibility IR, every asset exists, no template token or audit card vocabulary leaks into the human Reader, and the Reader is generated.
2. **Visual audit:** inspect the paper-specific story flow in HTML and PDF, including source captions, page anchors, equations, figure clarity, clipping, page breaks, and the distinct Paper/Project boundary. Claim-level O/I/A inspection belongs to the separate Evidence Atlas.

The acceptance gate also enforces evidence locality: every `narrative_core` or
`narrative_support` figure/table from `argument_reconstruction.json` must have
one local primary-Reader block with a decodable source asset. Every structured
source-map equation must have one corresponding block. Verified equations are
rendered from verified LaTeX; equations without verified LaTeX must carry a
decodable source crop, otherwise the run fails closed with `NEEDS_REVIEW`.

A PDF that renders successfully is not evidence that the layout is readable. Visual inspection remains a required human step because pixels and captions cannot be fully judged by JSON validation.

## Release gate v2

`PAPER_COMPLETE` is a release decision, not a render result. The production
path runs `scripts/reader_acceptance.py` with the real-corpus report and will
only release when the narrative, Lens invisibility, inline evidence, equation,
faithful-reading, unsupported-prose, HTML/Markdown/PDF parity, and visual
review gates all pass. A direct `--artifact-only` check is useful while a
workspace is being built, but it can return `READER_ACCEPTED` only; it cannot
promote a run to `PAPER_COMPLETE`.

The report is produced by `scripts/reader_regression.py` from
`evals/reader_regression/corpus.json`. The corpus contains five real
development papers spanning at least three domains and one post-freeze unseen
paper, each bound to its source PDF hash, semantic and visual review packets,
gold checklist, and selected direct-reading baselines. Reviews are immutable
evidence packets: pending, stale, hash-mismatched, or unnamed reviews fail the
gate. The regression report is re-evaluated and cryptographically checked when
`PAPER_COMPLETE` is requested.
