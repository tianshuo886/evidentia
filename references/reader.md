# Chinese-first Deep-Reading Scientific Reader Contract (Reader v3)

In Evidentia Reader v3, the primary human-facing reader is authored by the strong-model Lead Writer as a semantic manuscript (`reader/narrative_manuscript.json`), governed by `schemas/narrative_manuscript.schema.json`. `scripts/render_paper_reader.py` transforms this manuscript into presentation-grade HTML, Markdown, and vector PDF.

## Physical Separation from Project Apply
The Paper Reader is strictly project-independent and immutable. Project Apply deltas are never merged into `reader/paper_reader.html`. Instead, explicit Apply requests generate separate reports under `apply/<project>/project_reader.html` and `.md`.

## Paper-Specific Dynamic Narrative Plan (Anti-Template)
The manuscript follows the paper's reconstructed argument topology. Section count, titles, and order follow the paper's question, method, decisive results, assessment, and boundaries; they are not forced into a universal IMRaD sequence. Every section is rich Chinese-first prose with local evidence links and figures placed where the argument needs them.

The final section records what the evidence establishes and what remains open. A quiet provenance appendix links to the separate Evidence Atlas for claim-level inspection; audit roles and internal pipeline metadata never enter the human narrative.

Default `PAPER_READING` does not output reuse or migration sections. Technical extraction is an explicit secondary intent (`PAPER_TECHNICAL_EXTRACTION`); project migration occurs only through explicit `/evidentia-apply` and never alters the frozen Paper Reader.

## Kami Presentation Boundary
Kami is strictly presentation-only. Kami owns typography, spacing, responsive layout, visual hierarchy, and vector PDF rendering. Evidentia and the Lead Writer own scientific meaning, section order, claim calibration, and evidence interpretation.
