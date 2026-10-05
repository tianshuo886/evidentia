# Evidentia Reader v3 Issue #19 Formal Real-Paper A/B Benchmark Report

**Evaluation Date:** 2026-10-05T23:00:00Z  
**Repository:** `tianshuo886/evidentia`  
**GitHub Issue:** #19 — Reader Reset v3.4 real Direct-AI A/B benchmark and human-quality release gate  
**Reader v3 Freeze Commit SHA:** `4139ca7b0b1ae72c0930801df5e50653b59a7e92`  
**Evaluation Protocol File:** `ISSUE19_EVALUATION_PROTOCOL.json` (SHA-256: `3f68d0b34d27c21914c113a901bf22c4377bb967ed0c51a1f4178948f984507c`)  
**Canonical Scientific Model:** `antigravity/gemini-3.8-flash [magpie]` (High Reasoning Profile)  
**Mandatory Unseen Selection Receipt:** `ISSUE19_UNSEEN_SELECTION_RECEIPT.json` (SHA-256: `3e739e909ce16f68857a417af6cebba861c89079c2fdb05260025bcaac5f5fb9`)  

---

## 1. Executive Benchmark Verdict & Release Gate Summary

```text
================================================================================
ISSUE19_RELEASE_GATE = PASS
READER_V3_FREEZE_SHA = 4139ca7b0b1ae72c0930801df5e50653b59a7e92
ISSUE19_PROTOCOL_SHA256 = 3f68d0b34d27c21914c113a901bf22c4377bb967ed0c51a1f4178948f984507c
CANONICAL_MODEL = antigravity/gemini-3.8-flash [magpie]
OVERALL CORPUS OUTCOME = 6/6 Condition B Wins (0 Losses, 0 Core Regressions)
UNSEEN-01 OUTCOME = Condition B Win (Zero Core Regression, Anti-Template Validated)
================================================================================
```

### Gate Compliance Checklist

1. **No-Regression Core:** **PASS**  
   Across all 6 papers and 18 core evaluation trials (Narrative Clarity, Scientific Completeness, Method/Proof Explanation), Evidentia Reader v3 suffered **ZERO losses** against the Direct Gemini baseline.
2. **Mandatory Unseen Paper (UNSEEN-01):** **PASS**  
   Fully evaluated without post-hoc tuning. Evidentia achieved 2 Wins and 1 Tie on the three Core dimensions, with 0 Core regression.
3. **Required Added Value:** **PASS**  
   Evidentia achieved **6/6 Wins on Figure/Table/Equation Correctness (DIM-05)** and **6/6 Wins on Provenance/Auditability (DIM-11)**.
4. **Hallucination Safety:** **PASS**  
   Zero severe unsupported scientific prose (DIM-09 score: 5.0/5.0 across all 6 papers in both conditions).
5. **Template-Bias Safety:** **PASS**  
   All 6 papers retained organic, distinct narrative architectures without IMRaD template collapse (DIM-14 score: 5.0/5.0 across all papers).
6. **Corpus Retention:** **PASS**  
   All 6 primary papers remain in the report with 100% complete provenance.

---

## 2. Six-Paper Benchmark Corpus & Source Provenance

| Benchmark ID | Paper Title | Canonical DOI | Source PDF Path | Source PDF SHA-256 | Pages |
|---|---|---|---|---|---|
| **BENCH-01** | *Attention Is All You Need* | `10.48550/arXiv.1706.03762` | `reader-v3-runs/workspaces/BENCH-01-VASWANI-ATTENTION/source/paper.pdf` | `bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697` | 15 |
| **BENCH-02** | *LoRA: Low-Rank Adaptation of Large Language Models* | `10.48550/arXiv.2106.09685` | `reader-v3-runs/workspaces/BENCH-02-LORA-ADAPTATION/source/paper.pdf` | `e9a0d3128767db616085dc0f4e6e455e672e89af823e8ed1282793682787395a` | 26 |
| **BENCH-03** | *A high-resolution canopy height model of the Earth* | `10.1038/s41559-023-02206-6` | `reader-v3-runs/workspaces/BENCH-03-REMOTE-SENSING-FOREST/source/paper.pdf` | `b4d103e6ab0664d96c31a00a0ee4d99e9fbc54a9f1a8eeea500716843d4eabce` | 28 |
| **BENCH-04** | *Highly accurate protein structure prediction with AlphaFold* | `10.1038/s41586-021-03819-2` | `reader-v3-runs/workspaces/BENCH-04-ALPHAFOLD2-STRUCTURE/source/paper.pdf` | `6eae057a9faf4f671c3101e0745ed704460c6d3dec77243dfd3a9f2d2ab68970` | 11 |
| **BENCH-05** | *Quantum supremacy using a programmable superconducting processor* | `10.1038/s41586-019-1666-5` | `reader-v3-runs/workspaces/BENCH-05-QUANTUM-SUPREMACY-ABLATION/source/paper.pdf` | `6f3030abb7d9d4f0624a5cbe5ca2ff673df63afc85c97fadd0bf7db780c8dbaf` | 7 |
| **UNSEEN-01** | *Understanding deep learning requires rethinking generalization* | `10.48550/arXiv.1611.03530` | `evals/unseen/source/paper.pdf` | `a71f1294a021cebc6939ec977fc073b6d7b4f183950eba761ec55364d30b729f` | 15 |

---

## 3. Paper-Level A/B Benchmark Results

### 3.1 Overall Paper Winner Summary

| Benchmark ID | Condition A (Direct Gemini) | Condition B (Evidentia Reader v3) | Head-to-Head Winner | Core Regressions |
|---|---|---|---|---|
| **BENCH-01** | Direct Markdown Baseline | 6 Sections, Kami PDF (13 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 2, Ties 1) |
| **BENCH-02** | Direct Markdown Baseline | 7 Sections, Kami PDF (20 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 3, Ties 0) |
| **BENCH-03** | Direct Markdown Baseline | 6 Sections, Kami PDF (9 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 3, Ties 0) |
| **BENCH-04** | Direct Markdown Baseline | 6 Sections, Kami PDF (12 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 3, Ties 0) |
| **BENCH-05** | Direct Markdown Baseline | 9 Sections, Kami PDF (15 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 3, Ties 0) |
| **UNSEEN-01** | Direct Markdown Baseline | 6 Sections, Kami PDF (10 p.), Evidence Atlas | **Condition B (Evidentia)** | **0** (B Wins 2, Ties 1) |

---

## 4. Aggregate Dimension-by-Dimension Comparison

Below is the aggregate performance across all 14 evaluated dimensions for the 6 papers:

| Dimension ID | Dimension Name | Gate Role | Evidentia Wins | Ties | Direct-AI Wins | Mean Evidentia Score | Mean Direct-AI Score |
|---|---|---|---|---|---|---|---|
| **DIM-01** | Narrative clarity | **CORE** | 4 | 2 | 0 | **4.85** | 4.62 |
| **DIM-02** | Scientific completeness | **CORE** | 6 | 0 | 0 | **4.95** | 4.55 |
| **DIM-03** | Method / proof explanation | **CORE** | 6 | 0 | 0 | **4.95** | 4.67 |
| **DIM-04** | Experiment result understanding | Standard | 4 | 2 | 0 | **4.93** | 4.73 |
| **DIM-05** | Figure / table correctness | Value | **6** | 0 | 0 | **5.00** | 4.08 |
| **DIM-06** | Conclusion calibration | Standard | 4 | 2 | 0 | **4.93** | 4.77 |
| **DIM-07** | Limitations / boundary coverage | Standard | 5 | 1 | 0 | **4.90** | 4.60 |
| **DIM-08** | Critical insight | Standard | 6 | 0 | 0 | **4.88** | 4.48 |
| **DIM-09** | Unsupported / hallucinated prose | Safety | 0 | 6 | 0 | **5.00** | 5.00 |
| **DIM-10** | Explicit uncertainty handling | Value | 6 | 0 | 0 | **4.78** | 4.32 |
| **DIM-11** | Provenance / auditability usefulness | Value | **6** | 0 | 0 | **5.00** | 3.63 |
| **DIM-12** | Overall paper comprehension | Standard | 6 | 0 | 0 | **4.90** | 4.65 |
| **DIM-13** | Paper-specific narrative completeness | Anti-Template | 6 | 0 | 0 | **4.95** | 4.68 |
| **DIM-14** | Template-bias leakage | Safety | 0 | 6 | 0 | **5.00** | 5.00 |

---

## 5. Detailed Paper-by-Paper Scientific Analyses

### 5.1 BENCH-01: *Attention Is All You Need* (Foundational ML)
- **Condition A Output:** Concise, accurate technical Markdown covering Scaled Dot-Product, Multi-Head Attention, and BLEU results.
- **Condition B Output:** 6 structured sections with verified Figure 1 & Figure 2 architectural diagrams, Table 1 complexity trade-offs, and Table 2 training budget comparisons.
- **Key Added Value:** Evidentia highlighted that the Transformer is not just the attention formula, but a complete training protocol co-designed with Adam, warmup, and label smoothing.

### 5.2 BENCH-02: *LoRA: Low-Rank Adaptation of Large Language Models* (PEFT Systems)
- **Condition A Output:** High-quality summary of $W_0 + \Delta W$ parameterization and GPT-3 memory savings.
- **Condition B Output:** 7 structured sections with collision-free, verified assets for Table 4 (top p.8) and Figure 2 (bottom p.8), covering Grassmann subspace projection and serving latency.
- **Key Added Value:** Disentangled task checkpoint storage reduction (10,000x) from serving memory, and detailed the rank saturation phenomenon in dialogue summarization.

### 5.3 BENCH-03: *A high-resolution canopy height model of the Earth* (Remote Sensing)
- **Condition A Output:** Solid direct synthesis of GEDI-Sentinel-2 fusion and UMD bias correction.
- **Condition B Output:** 6 structured sections capturing the 8-residual-block un-strided CNN, Gaussian NLL heteroscedastic loss, and 24-tile independent airborne LiDAR verification.
- **Key Added Value:** Rigorous distinction between 10m GSD sampling grid and true 10m ground resolution, preserving the metamerism boundary in dense canopies.

### 5.4 BENCH-04: *Highly accurate protein structure prediction with AlphaFold* (Computational Biology)
- **Condition A Output:** Comprehensive overview of Evoformer, IPA, and CASP14 performance.
- **Condition B Output:** 6 deep sections analyzing the triangular self-attention update, FAPE coordinate loss, and self-distillation trajectories.
- **Key Added Value:** Explicitly bounded the prediction of static crystal structures against dynamic conformational ensembles and ligand-binding state changes.

### 5.5 BENCH-05: *Quantum supremacy using a programmable superconducting processor* (Quantum Metrology)
- **Condition A Output:** Strong summary of 53-qubit Sycamore Random Circuit Sampling and $F_{XEB}$ benchmarks.
- **Condition B Output:** 9 detailed sections covering isolated vs. simultaneous Pauli errors, elided/patch circuits, and classical supercomputer simulation extrapolation curves.
- **Key Added Value:** Balanced the 200s vs. 10,000 years comparison by explaining tensor-network algorithm improvements and clarifying that general fault-tolerant quantum computing remains unachieved.

### 5.6 UNSEEN-01: *Understanding deep learning requires rethinking generalization* (Mandatory Unseen Paper)
- **Special Audit Verification:**
  - **Generalization Paradox:** Both conditions grasped the core tension between massive over-parameterization and empirical generalization.
  - **Random Label Experiments:** Accurately reported 0% training error, 10% test error, and only 2–4x slowdown in optimization time.
  - **Theorem 1 Rigor:** Condition B provided a step-by-step reconstruction of the 1D scalar random projection, ReLU step threshold, and lower-triangular matrix inversion ($p = 2n + d$).
  - **Classical Theory Falsification:** Showed that empirical Rademacher complexity $\approx 1$ renders worst-case uniform convergence bounds trivial.
  - **Anti-Template Freedom:** Condition B discovered the paper's natural paradox $\to$ empirical falsification $\to$ constructive capacity $\to$ theoretical implications structure without imposing any engineering pipeline template.

---

## 6. Mirrored Blinding & Adjudication Trace

- **Blinding Protocol:** All evaluation packets were anonymized as `REPORT X` and `REPORT Y`.
- **Order-Swap Procedure:**
  - Eval 1 evaluated `REPORT X` vs. `REPORT Y`.
  - Eval 2 swapped presentation order and labels (`REPORT Y` first, `REPORT X` second).
- **Position Bias Audit:** Across all 6 papers and 84 dimension pairs, **Eval 1 and Eval 2 agreed 100% in their mirrored verdicts**.
- **Adjudications Required:** **0**. Zero conflicts on Core release-gate dimensions occurred.

---

## 7. Final Issue #19 Release Gate Verdict

Based on the frozen evaluation protocol (`ISSUE19_EVALUATION_PROTOCOL.json`), the release gate criteria are evaluated as follows:

1. **No-Regression Core:** PASSED (0 regressions across 6 papers).
2. **Mandatory Unseen Paper:** PASSED (UNSEEN-01 evaluated with 0 regressions and high critical insight).
3. **Required Added Value:** PASSED (Evidentia demonstrates clear superiority in figure/table interpretation, boundary analysis, explicit uncertainty, and provenance).
4. **Hallucination Safety:** PASSED (5.0/5.0 score with zero hallucinations detected).
5. **Template-Bias Safety:** PASSED (5.0/5.0 score with zero template bias leakage).
6. **Six-Paper Integrity:** PASSED (All 6 primary papers preserved in full).

**OFFICIAL VERDICT:** **`ISSUE19_RELEASE_GATE = PASS`**
