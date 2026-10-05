# Evidentia Reader v3 Issue #19 Formal Evaluation Protocol

**Document Version:** 1.0 (Frozen)  
**Associated Issue:** tianshuo886/evidentia#19  
**Reader v3 Freeze SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`  
**Protocol JSON:** `ISSUE19_EVALUATION_PROTOCOL.json`  
**Frozen Protocol SHA-256:** `3f68d0b34d27c21914c113a901bf22c4377bb967ed0c51a1f4178948f984507c` (Canonical content: `416140feaca5ceff97ed31b00d2c7eb0cea885bfcb580bc90d20f41daffe6ab0`)  
**Canonical Scientific Model:** `antigravity/gemini-3.8-flash [magpie]` (High Reasoning Profile)  

---

## 1. Benchmark Purpose and Governance

This protocol defines the formal, post-freeze, release-gating Direct-AI vs. Evidentia Reader v3 A/B benchmark on 6 real scientific papers. Reader v3 scientific architecture is **strictly frozen** at commit `4139ca7b0b1ae72c0930801df5e50653b59a7e92`. No scientific architecture changes, schema alterations, or prompt rewrites are permitted during benchmark execution.

Any change to the primary release gate after generation of the first Condition A/B output is strictly prohibited.

---

## 2. Benchmark Corpus Matrix

The benchmark consists of exactly 6 full, peer-reviewed, open-access research papers covering diverse argumentative topologies:

| Benchmark ID | Paper Title | Canonical DOI / arXiv | Source PDF Path | Source SHA-256 | Corpus Role |
|---|---|---|---|---|---|
| **BENCH-01** | *Attention Is All You Need* | `10.48550/arXiv.1706.03762` | `reader-v3-runs/workspaces/BENCH-01-VASWANI-ATTENTION/source/paper.pdf` | `bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697` | ML Foundational Architecture |
| **BENCH-02** | *LoRA: Low-Rank Adaptation of Large Language Models* | `10.48550/arXiv.2106.09685` | `reader-v3-runs/workspaces/BENCH-02-LORA-ADAPTATION/source/paper.pdf` | `e9a0d3128767db616085dc0f4e6e455e672e89af823e8ed1282793682787395a` | PEFT & System Serving |
| **BENCH-03** | *A high-resolution canopy height model of the Earth* | `10.1038/s41559-023-02206-6` | `reader-v3-runs/workspaces/BENCH-03-REMOTE-SENSING-FOREST/source/paper.pdf` | `b4d103e6ab0664d96c31a00a0ee4d99e9fbc54a9f1a8eeea500716843d4eabce` | Remote Sensing & Geospatial Modeling |
| **BENCH-04** | *Highly accurate protein structure prediction with AlphaFold* | `10.1038/s41586-021-03819-2` | `reader-v3-runs/workspaces/BENCH-04-ALPHAFOLD2-STRUCTURE/source/paper.pdf` | `6eae057a9faf4f671c3101e0745ed704460c6d3dec77243dfd3a9f2d2ab68970` | Computational Biophysics & Geometric DL |
| **BENCH-05** | *Quantum supremacy using a programmable superconducting processor* | `10.1038/s41586-019-1666-5` | `reader-v3-runs/workspaces/BENCH-05-QUANTUM-SUPREMACY-ABLATION/source/paper.pdf` | `6f3030abb7d9d4f0624a5cbe5ca2ff673df63afc85c97fadd0bf7db780c8dbaf` | Quantum Computing & Precision Metrology |
| **UNSEEN-01** | *Understanding deep learning requires rethinking generalization* | `10.48550/arXiv.1611.03530` | `evals/unseen/source/paper.pdf` | `a71f1294a021cebc6939ec977fc073b6d7b4f183950eba761ec55364d30b729f` | Mandatory Unseen Paper (Theorem/Proof & Falsification) |

*The unseen paper is mandatory and cannot be removed, replaced, or discounted regardless of performance.*

---

## 3. Condition A: Direct Gemini Baseline

- **Model:** `antigravity/gemini-3.8-flash [magpie]`
- **Input:** Authentic source PDF **ONLY**.
- **Forbidden Scaffolding:** No source map, no visual inventory, no Lens outputs, no Evidentia schemas, no Research Memory or Project Apply context.
- **Prompt:** High-quality direct scientific reading prompt asking for an in-depth, publication-grade Chinese deep reading respecting the paper's native argumentative structure, with rigorous citation of figures, tables, equations, and explicit boundary analysis.

---

## 4. Condition B: Frozen Evidentia Reader v3

- **Freeze SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`
- **Scientific Pipeline:**
  1. Deterministic Source Reconstruction & Visual Localization
  2. Lead Reader (Gemini)
  3. 4 Core + 2 Adaptive Lenses (Gemini, context-isolated)
  4. Revision Memo (Gemini)
  5. Anti-Template Narrative Plan (Gemini)
  6. Lead Writer (Gemini) -> `narrative_manuscript.schema.json`
  7. Fail-Closed Anti-Template & Structural Diversity Gates
  8. Rendering backend -> Kami HTML/PDF & Evidence Atlas
- **Strict Isolation:** No sibling Lens crosstalk; zero consumption of Project Apply / Research Memory.

---

## 5. Evaluation Dimensions & Scoring Rubric

All evaluations are conducted across 14 fine-grained dimensions:

1. **Narrative clarity** (`narrative_clarity`)* [Core No-Regression]
2. **Scientific completeness** (`scientific_completeness`)* [Core No-Regression]
3. **Method / study-design / proof explanation** (`method_explanation`)* [Core No-Regression]
4. **Experiment / result understanding** (`experiment_result_understanding`)
5. **Figure / table / equation correctness** (`figure_table_correctness`)
6. **Conclusion calibration** (`conclusion_calibration`)
7. **Limitations / boundary coverage** (`boundary_coverage`)
8. **Critical insight** (`critical_insight`)
9. **Unsupported / hallucinated prose** (`unsupported_prose`) [Safety, 5=Zero hallucination]
10. **Explicit uncertainty handling** (`explicit_uncertainty_handling`)
11. **Provenance / auditability usefulness** (`provenance_usefulness`)
12. **Overall paper comprehension** (`overall_understandability`)
13. **Paper-specific narrative completeness** (`paper_specific_narrative_completeness`)
14. **Template-bias leakage** (`template_bias_leakage`) [Safety, 5=Zero template bias]

*\*Core No-Regression Dimensions: Condition B must not regress versus Condition A.*

---

## 6. Blinding, Label-Swapping & Adjudication Procedure

For every paper:
1. Outputs are stripped of metadata and anonymized as **REPORT X** and **REPORT Y**.
2. **Evaluation 1:** Independent Gemini evaluation of REPORT X vs. REPORT Y.
3. **Evaluation 2:** Independent Gemini evaluation with **mirrored order and swapped labels** (REPORT Y as first, REPORT X as second).
4. **Adjudication:** If Eval 1 and Eval 2 disagree on a Core No-Regression dimension, a 3rd independent Gemini session performs blind adjudication.

---

## 7. Predeclared Release Gate (`ISSUE19_RELEASE_GATE`)

The release gate passes (`PASS`) if and only if:
1. **No-Regression Core:** Condition B does not suffer a net adjudicated loss on any of the 3 Core dimensions across the corpus, and suffers **zero losses** on UNSEEN-01.
2. **Required Added Value:** Evidentia demonstrates clear superiority in figure/table interpretation, boundary analysis, explicit uncertainty, and provenance.
3. **Hallucination Safety:** Condition B produces zero severe source-inconsistent hallucinations.
4. **Template-Bias Safety:** UNSEEN-01 retains its native theorem/falsification structure without template collapse.
5. **All 6 Papers Included:** Complete benchmark data for all 6 papers must be preserved.

---

## 8. Operational & Quota Policies

- **Single Canonical Model:** `antigravity/gemini-3.8-flash [magpie]`. No fallback models permitted.
- **Quota Interruption:** If rate limits occur, all durable artifacts are checkpointed cleanly and resumed without invalidating completed work.
