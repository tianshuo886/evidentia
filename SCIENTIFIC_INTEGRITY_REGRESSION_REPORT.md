# SCIENTIFIC INTEGRITY REGRESSION REPORT

**Target Issue:** [#36 — Reader v3 Scientific Integrity: claim semantics, attribution, and fail-closed verification](https://github.com/tianshuo886/evidentia/issues/36)  
**Execution Date:** 2026-10-11  
**Status:** ACCEPTED (Zero Unresolved Material P0 Science/Attribution Errors)  
**Verification Gate:** FAIL-CLOSED SCIENTIFIC INTEGRITY GATE (`scripts/scientific_claim_verifier.py`, `scripts/reader_acceptance.py`)

---

## 1. Provenance and Locked Artifacts

| Artifact | Location / Ref | SHA256 Hash |
| :--- | :--- | :--- |
| **Source Paper (PDF)** | *RingMoClaw: An Experience-Inspired Multi-Agent Framework for Self-Evolving Research in Remote Sensing*, arXiv:2609.00814v2 | `32df5e2843de7e8ccd52d56b9dfed257c26786ef3b71fbc397a1c3a5e26fb0fa` |
| **Defective Reader (Markdown)** | `evals/reader_v3/semantic_regressions/ringmoclaw/defective_reader.md` | `08b1e9768ab3373a8d3e035523799f0c31dfc845ecf5b120d06a93ef1983c789` |
| **Corrected Reader (Markdown)** | `evals/reader_v3/semantic_regressions/ringmoclaw/corrected_reader.md` | Bound in evaluation suite |
| **Source Lock Record** | `evals/reader_v3/semantic_regressions/ringmoclaw/source_lock.json` | Hash-bound JSON |
| **Failure Manifest** | `evals/reader_v3/semantic_regressions/ringmoclaw/reading_failure_manifest.json` | Hash-bound JSON (8 failure items) |
| **Claim Ledger Schema** | `schemas/claim_ledger.schema.json` | Hash-bound JSON Schema Draft 2020-12 |

---

## 2. Reproduction and Concrete Defect Audit (Eight Findings)

Each of the eight concrete semantic regressions observed in the real-paper output was evaluated against the primary PDF source text, tables, and captions.

### 2.1 Detrimental Precision & Recall Semantics (Table X, p.14)
- **Source Anchor:** PDF p.14 Table X & surrounding text:
  > *"Here, TP denotes a candidate identified as detrimental by the five-minute protocol and confirmed to be detrimental after full training... Precision = TP / (TP + FP) = 1.00... Recall = TP / (TP + FN) = 0.83... Among the six candidates that are detrimental after full training, five are successfully identified during the five-minute stage, yielding a recall of 0.83."*
- **Defective Reading (FAIL):**
  > *"对劣化候选策略的早筛拦截精度达到惊人的 1.00（无一漏过）... 召回率为 0.83，意味着有约 17% 的潜质策略因早期收敛缓慢而被过早扼杀。"*
- **Factual Error:** Positive class is *detrimental candidates*. Precision=1.00 means zero false alarms (every candidate flagged as detrimental was truly detrimental), NOT that zero were missed ("无一漏过"). Recall=0.83 means 5 out of 6 true detrimental candidates were intercepted and 1 detrimental candidate (17%) escaped early screening. It does *not* mean 17% of promising strategies were killed.
- **Corrected Reading (PASS):**
  > *"五分钟敏捷验证在预测劣化候选策略时的精确率为 1.00（即所有被判定为劣化的候选策略经全量验证均为真实劣化，实现零误拦截），而对劣化候选策略的召回率为 0.83（全量训练中 6 个真实劣化候选中有 5 个被成功早筛拦截，1 个劣化策略漏过早筛）。"*

### 2.2 Failed Iterations Semantics (Table IX, p.14)
- **Source Anchor:** PDF p.14 Table IX caption / notes:
  > *"“Failed” reports the number of non-improving iterations per caption."*
- **Defective Reading (FAIL):**
  > *"需要 14 轮且发生 6 次严重训练失败。"*
- **Factual Error:** `Failed=6` represents 6 non-improving exploration iterations where a proposed candidate did not outperform previous validation accuracy. Conflating this with catastrophic training crashes or runtime exceptions is a material factual error.
- **Corrected Reading (PASS):**
  > *"需要 14 轮且经历了 6 次非提升探索迭代（failed iterations，指未能带来验证集精度增益的候选搜索尝试，而非训练程序崩溃）。"*

### 2.3 GPU-hours vs Wall-Clock Hours Accounting (Table VII, p.14)
- **Source Anchor:** PDF p.14 Table VII:
  > *AutoResearch: GPU-hours = 26.90, Wall-clock (h) = 13.45*  
  > *RingMoClaw: GPU-hours = 12.14, Wall-clock (h) = 10.61*
- **Defective Reading (FAIL):**
  > *"GPU 运行时间从 AutoResearch 的 26.90 小时压减至 12.14 小时。"*
- **Factual Error:** Collapses GPU-hours (cumulative compute resource across GPUs) and elapsed real time (wall-clock hours: 13.45 -> 10.61 h) into an ambiguous "GPU 运行时间".
- **Corrected Reading (PASS):**
  > *"总 GPU 算力消耗（GPU-hours）从 AutoResearch 的 26.90 小时压减至 12.14 小时，端到端实际挂钟时间（wall-clock hours）从 13.45 小时缩减至 10.61 小时。"*

### 2.4 Bibliographic Precedence: Preprint vs Unverified Venue (p.1)
- **Source Anchor:** PDF p.1 title page:
  > *"arXiv:2609.00814v2 [cs.CV] 12 Sep 2026"*
- **Defective Reading (FAIL):**
  > *"Kaiyue Kang... · IEEE Transactions on Geoscience and Remote Sensing (TGRS) · 2026"*
- **Factual Error:** The PDF carries only an arXiv preprint stamp. Stating IEEE TGRS 2026 as verified journal publication without an authoritative verified external bibliographic record violates scientific epistemic integrity.
- **Corrected Reading (PASS):**
  > *"Kaiyue Kang... · arXiv:2609.00814v2 (preprint · venue unverified) · 2026"*

### 2.5 Author Attribution vs Project Context Leakage Firewall (p.15)
- **Source Anchor:** PDF p.15 Discussion and Conclusion. Zero occurrence of PROSAIL or PINN.
- **Defective Reading (FAIL):**
  > *"作者坦承…若要迁移至涉及机理先验（如大气辐射传输方程 PROSAIL、冠层多性状物理耦合 PINN）的定量遥感科学计算，必须将物理可解释性与守恒定律作为硬性边界写入 Critic 的方案与结果审查准则中。"*
- **Factual Error:** Conflating researcher/user workspace project context with author statements. Attributing external domain claims to the paper authors breaches the faithful-reading firewall.
- **Corrected Reading (PASS):**
  > Removed false attribution. In default `PAPER_READING` mode, the reader notes only author-stated boundaries regarding pure data-driven pattern matching versus physics-informed operators.

### 2.6 FAIR1M Best-of-Three Run Selection Protocol (p.9 Table I)
- **Source Anchor:** PDF p.9 text:
  > *"The evolution process was independently repeated three times, and Table I reports the best trajectory."*
- **Defective Reading (FAIL):** Presented as a single deterministic run or typical mean trajectory without disclosing run selection.
- **Corrected Reading (PASS):**
  > Explicitly states: *"（注：演化流程独立重复三次，表I 报告的是三次独立重复演化试验中的最优轨迹结果）"*.

### 2.7 Detection Baseline vs MSFR/CPR Setup Context (p.9 & p.13 Table VI)
- **Source Anchor:** PDF p.9 (YOLO11x-OBB detection head baseline) & p.13 Table VI.
- **Defective Reading (FAIL):** Conflated Table I incremental trajectory gains directly with Table VI isolated module evaluations without stating baseline context.
- **Corrected Reading (PASS):** Clarified detector head and backbone setup context when discussing Table VI modules.

### 2.8 LEVIR-CD F1 vs IoU Metric Definition Verification (p.12 Table IV)
- **Source Anchor:** Table IV reports Baseline F1=89.53, IoU=87.10; EvoChangeStar F1=90.54, IoU=89.97; BIT F1=89.31, IoU=89.37.
- **Defective Reading (FAIL):** Unqualified numerical citation ignoring metric relationship.
- **Corrected Reading (PASS):** Flags benchmark-specific class macro/micro averaging conventions accounting for the F1-IoU relationship on LEVIR-CD.

---

## 3. Architecture and Implementation Summary

1. **Atomic Claim Ledger (`schemas/claim_ledger.schema.json` & `scripts/scientific_claim_verifier.py`)**:
   - Stores per-assertion records with: `claim_id`, `statement`, `source_anchors`, `evidence_refs`, `epistemic_category`, `numerical_semantics` (metric, positive class, unit, statistic, denominator, baseline, selection protocol), `attribution`, `confidence`, `boundaries`, `verdict`, and `verifier_reasoning`.
   - Internal only: never leaked into human-facing Kami reading surface as card soup.
2. **Fail-Closed Verification Engine (`scripts/scientific_claim_verifier.py`)**:
   - Independent adversarial check evaluating formulas, cross-table comparisons, variable definitions, and attribution.
   - Enforces fail-closed verdicts: `SUPPORTED`, `QUALIFIED`, `CONTRADICTED`, `UNSUPPORTED`, `UNRESOLVED`.
   - Any critical `CONTRADICTED` claim or invented attribution produces status `FAIL` and blocks `PAPER_COMPLETE`.
3. **Actionable Feedback & Patch Generation**:
   - Verifier outputs actionable patch instructions targeting Lead Writer revisions (exact offending span, source anchor, and suggested replacement).
   - Kami renderers remain presentation-only: no text mutation inside Kami.
4. **Venue Interface & Quiet Header Qualification**:
   - Quiet, plain-text reading header distinguishing `preprint · venue unverified` from externally verified peer-reviewed publications.

---

## 4. Test and Gate Validation Evidence

- **Dedicated Semantic Integrity Suite (`tests/test_scientific_integrity.py`):**
  - `test_failure_manifest_and_source_lock_exist_and_validate`: PASS
  - `test_defective_reader_fails_gate_with_concrete_reasons`: PASS (catches all 6 P0 blockers with exact diagnostic rules)
  - `test_corrected_reader_passes_gate_cleanly`: PASS (0 P0 blockers, status PASS)
  - `test_precision_recall_positive_class_unit_semantics`: PASS
  - `test_failed_iterations_vs_execution_failure`: PASS
  - `test_gpu_hours_vs_wall_clock_accounting`: PASS
  - `test_bibliographic_evidence_precedence`: PASS
  - `test_paper_only_firewall_against_prosail_pinn_leakage`: PASS
  - `test_atomic_claim_ledger_schema_and_integrity`: PASS
  - `test_adversarial_mutation_on_plausible_prose_fails`: PASS
- **Complete Test Suite:** 215 / 215 tests passing across entire Evidentia harness.

---

## 5. Exit Criteria / Sign-off for Issue #36

- [x] Machine-readable minimal fixtures created in `evals/reader_v3/semantic_regressions/ringmoclaw/`.
- [x] Defective `reader.md` fails gate deterministically with exact line-level diagnostic rules.
- [x] Corrected `reader.md` passes gate without false rejections.
- [x] Atomic Claim Ledger schema and verification engine implemented and tested.
- [x] Zero unresolved material P0 science/attribution errors on the RingMoClaw benchmark.
- [x] Ready to advance to **Issue #37** (Deep Explanation & Visual Coverage).
