# Issue #19 development-corpus readiness

Generated 2026-10-04 after the BENCH-03 registry identity correction. The matrix is source-preparation and Direct-AI only; no Reader v3 Condition B run was started.

| Benchmark | PDF | SHA | Reconstruction/pages | Figure/table/equation inventory | Visual prep | Direct-AI + envelope | Provenance |
|---|---:|---:|---:|---:|---:|---:|---:|
| BENCH-02 | ✅ | `e9a0d312…87395a` | ✅ | ✅ | ✅ | ✅ | ✅ |
| BENCH-03 | ✅ | `b4d103e6…4eabce` | ✅ | ✅ | ✅ | ✅ | ✅ |
| BENCH-04 | ✅ | `6eae057a…2ab68970` | ✅ | ✅ | ✅ | ✅ | ✅ |
| BENCH-05 | ✅ | `6f3030ab…0c8dbaf` | ✅ | ✅ | ✅ | ✅ | ✅ |

## BENCH-03 identity and evidence correction

- Canonical paper: **A high-resolution canopy height model of the Earth** — Nico Lang, Walter Jetz, Konrad Schindler, Jan Dirk Wegner; 2023; *Nature Ecology & Evolution*; DOI `10.1038/s41559-023-02206-6`.
- Active source: Nature publisher full PDF, 28 pages, SHA-256 `b4d103e6ab0664d96c31a00a0ee4d99e9fbc54a9f1a8eeea500716843d4eabce`.
- The former `10.1016/j.rse.2022.113070` identity is quarantined and no active artifacts derive from it.
- Registry evidence was changed from the stale Figure 3 / Figure 7 / Table 3 labels to Figure 1, Figure 2, Figure 3, and Extended Data Table 1. Ground truth was updated to the formal paper's actual evidence and limitations.
- BENCH-03 inventory contains Figures 1–4, Extended Data Figures 1–8, Extended Data Tables 1–2, and 79 equations. Continuation-caption duplicates remain explicitly marked `NEEDS_REVIEW`; they are not silently promoted.

## Scope guard

BENCH-01 remains excluded. No unseen paper was selected, no Condition B was run, Issue #20 was not executed, and no Issue #22 or Reader scientific contract/prompt was modified.
