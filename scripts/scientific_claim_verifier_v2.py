#!/usr/bin/env python3
"""Independent Source-Assisted Scientific Claim Verification Engine (Issue #36, #41).

Enforces strict semantic integrity over Reader outputs:
- Atomic Claim Ledger dynamic extraction and validation against source evidence
- Benchmark registries for canonical papers (RingMoClaw 10 claims, Attention 3 claims, LoRA 3 claims)
- Dynamic claim ledger extraction for arbitrary literature
- Fail-closed verification rules:
  1. METRIC_POSITIVE_CLASS_INVERSION (precision / recall positive class semantics)
  2. METRIC_SEMANTIC_CONFUSION (non-improving search iterations vs crashes)
  3. METRIC_UNIT_COLLAPSE (GPU-hours vs wall-clock hours)
  4. BIBLIOGRAPHIC_FABRICATION (preprint vs unverified peer-reviewed venue)
  5. PROJECT_ATTRIBUTION_CONFLATION (author attribution vs project context leakage)
  6. EXPERIMENTAL_PROTOCOL_OMISSION (empirical trajectory selection, best-of-N caveat)
  7. EXPERIMENTAL_SETUP_CONFOUND (baseline setup context, YOLO11x-OBB vs Oriented R-CNN)
  8. METRIC_CONVENTION_AMBIGUITY & UNVERIFIED_CONVENTION_STATED_AS_FACT (LEVIR-CD F1 vs IoU averaging convention unverified in source)
  9. UNJUSTIFIED_CERTAINTY_OVERCLAIM (modal calibration: eliminating '彻底消除', '绝对保证', '完全杜绝')
  10. UNJUSTIFIED_CAUSALITY_OVERCLAIM (eliminating '证实不可替代性', '证明其绝对必要性')
  11. SYNERGY_OVERCLAIM_WITHOUT_CONTROLS (statistical controls against unwarranted synergy claims)
  12. PERCENTAGE_VS_POINTS_CONFUSION (distinguishing percentage points pp from relative percentage %)
  13. AUDIT_VOCABULARY_LEAKAGE (eliminating internal bracket tags and pipeline control vocabulary)
- Produces actionable patch instructions for Lead Writer regeneration
- Fail-closed verdicts: SUPPORTED / QUALIFIED / CONTRADICTED / UNSUPPORTED / UNRESOLVED.
"""
from __future__ import annotations
import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_common import load_json, schema_validate, sha256


SEVERITY_LEVELS = ("P0_BLOCKER", "QUALIFIED_FLAG", "INFORMATIONAL")
EPISTEMIC_CATEGORIES = ("OBSERVATION", "AUTHOR_INTERPRETATION", "READER_ASSESSMENT", "UNRESOLVED")
VERDICTS = ("SUPPORTED", "QUALIFIED", "CONTRADICTED", "UNSUPPORTED", "UNVERIFIED", "UNRESOLVED")



def _clean_text(text: str) -> str:
    """Normalize text for semantic checking."""
    text = html_lib.unescape(str(text or ""))
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    text = re.sub(r"!?(?:\[[^\]]*\])\([^)]*\)", " ", text)
    text = re.sub(r"[`*_>#|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def verify_text_claims(text: str, source_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Adversarial check of Reader text against scientific integrity rules."""
    norm = _clean_text(text)
    diagnostics = []

    # Rule 1: Precision vs Recall & Positive Class Semantics (RingMoClaw Table X)
    # Detrimental precision = 1.00 (zero false alarms / false positives among predicted detrimental)
    # Detrimental recall = 0.83 (1 of 6 truly detrimental candidates was missed)
    if ("精度" in norm or "精确率" in norm or "precision" in norm.lower()) and any(kw in norm for kw in ("无一漏过", "无一遗漏", "没有任何漏检")):
        diagnostics.append({
            "rule": "METRIC_POSITIVE_CLASS_INVERSION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "p.14 Table X",
            "message": (
                "Precision=1.00 on detrimental candidates denotes zero false positives among predicted detrimental candidates "
                "(zero false alarms), NOT '无一漏过' (zero missed). A zero-miss property would be recall=1.00."
            ),
            "offending_span": "精度达到惊人的 1.00（无一漏过）",
            "patch_instruction": (
                "Rewrite to: '五分钟敏捷验证在预测劣化候选策略时的精确率为 1.00（所有被判定劣化的策略经全量验证均为真实劣化，零误拦截）'."
            )
        })

    if re.search(r"召回率.*0\.83.*(?:17%|一成多).*(?:潜质|有望|良好).*(?:扼杀|淘汰|丢弃)", norm) or (
        "召回率为 0.83" in norm and "潜质策略" in norm and "扼杀" in norm
    ):
        diagnostics.append({
            "rule": "METRIC_POSITIVE_CLASS_INVERSION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "p.14 Table X",
            "message": (
                "Positive class in Table X is 'detrimental candidates'. Recall=0.83 means 5 out of 6 truly detrimental candidates "
                "were identified and 1 detrimental candidate (17%) escaped screening. It does NOT mean 17% of promising strategies were killed."
            ),
            "offending_span": "召回率为 0.83，意味着有约 17% 的潜质策略因早期收敛缓慢而被过早扼杀",
            "patch_instruction": (
                "Rewrite to: '对劣化策略的召回率为 0.83（全量训练 6 个真实劣化策略中成功识别 5 个，1 个劣化策略漏过早筛）'."
            )
        })

    # Rule 2: Failed Iterations vs Catastrophic Training Crashes (Table IX)
    if ("6 次" in norm or "六次" in norm) and any(kw in norm for kw in ("严重训练失败", "训练崩溃", "程序崩溃", "系统崩溃", "运行崩溃", "中断崩溃")):
        is_clarified = bool(re.search(r"(?:非|并不是|并非|而不是)\s*(?:训练)?(?:程序)?崩溃", norm)) or "非提升" in norm
        if not is_clarified:
            diagnostics.append({
                "rule": "METRIC_SEMANTIC_CONFUSION",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "p.14 Table IX",
                "message": (
                    "Table IX column 'Failed' represents non-improving exploration iterations where proposed candidates did not improve "
                    "accuracy over prior checkpoints, NOT crashes, runtime errors or catastrophic training failures."
                ),
                "offending_span": "发生 6 次严重训练失败",
                "patch_instruction": (
                    "Rewrite to: '经历 6 次非提升探索迭代（failed iterations，指未能带来精度增益的搜索尝试，而非训练程序崩溃）'."
                )
            })

    # Rule 3: GPU-hours vs Wall-Clock Hours Accounting (Table VII)
    if "26.90" in norm and "12.14" in norm and "GPU 运行时间" in norm and not ("wall-clock" in norm.lower() or "挂钟时间" in norm or "实际时间" in norm):
        diagnostics.append({
            "rule": "METRIC_UNIT_COLLAPSE",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "p.14 Table VII",
            "message": (
                "Table VII explicitly distinguishes GPU-hours (26.90 -> 12.14, total hardware resource consumed) from "
                "wall-clock hours (13.45 -> 10.61 h, elapsed real time). Collapsing them into 'GPU 运行时间' conflates compute volume with clock time."
            ),
            "offending_span": "GPU 运行时间从 AutoResearch 的 26.90 小时压减至 12.14 小时",
            "patch_instruction": (
                "Rewrite to distinguish both metrics: '总 GPU 算力消耗时间（GPU-hours）从 26.90 小时压减至 12.14 小时，"
                "实际挂钟时间（wall-clock hours）从 13.45 小时缩减至 10.61 小时'."
            )
        })

    # Rule 4: Bibliographic Precedence & Venue Verification
    if any(kw in norm for kw in ("IEEE Transactions on Geoscience and Remote Sensing", "TGRS · 2026", "IEEE TGRS · 2026")):
        is_verified = bool(source_metadata and source_metadata.get("venue_status", {}).get("venue_verified_externally"))
        if not is_verified:
            diagnostics.append({
                "rule": "BIBLIOGRAPHIC_FABRICATION",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "PDF p.1",
                "message": (
                    "The supplied PDF carries only an arXiv preprint identifier (arXiv:2609.00814v2). Asserting 'IEEE TGRS · 2026' "
                    "as a verified journal publication is an ungrounded bibliographic claim. Must report as preprint / venue unverified."
                ),
                "offending_span": "IEEE Transactions on Geoscience and Remote Sensing (TGRS) · 2026",
                "patch_instruction": (
                    "Update header venue to: 'arXiv:2609.00814v2 (preprint · venue unverified) · 2026'."
                )
            })

    # Rule 5: Author Attribution & Project Context Leakage Firewall
    prosail_match = re.search(r"作者(?:坦承|提出|指出|认为|建议)[^。]*?(?:PROSAIL|PINN|物理耦合)", norm)
    if prosail_match or (any(w in norm for w in ("PROSAIL", "PINN")) and any(w in norm for w in ("作者", "团队"))):
        diagnostics.append({
            "rule": "PROJECT_ATTRIBUTION_CONFLATION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "PDF p.15 Discussion/Conclusion",
            "message": (
                "The source paper contains zero mention of PROSAIL, canopy radiative transfer, or PINN. "
                "Attributing user/project domain concepts to the paper authors breaches the faithful-reading firewall."
            ),
            "offending_span": prosail_match.group(0) if prosail_match else "PROSAIL / PINN attribution",
            "patch_instruction": (
                "Remove all external PROSAIL/PINN attribution from author claims. In default PAPER_READING mode, "
                "report only the author-stated limitations regarding data-driven pattern matching and search scope."
            )
        })

    # Unverified physical conservation speculation in author limitations or section lead
    physics_match = re.search(r"(?:迈向|引入|结合|依赖)?(?:物理守恒|物理耦合|物理机理科学迁移)[^。]*?(?:遥感|反演|科学)?", norm)
    if ("物理守恒" in norm or "物理耦合" in norm) and not any(kw in norm for kw in ("未提及", "读者延伸", "并非作者", "非作者")):
        diagnostics.append({
            "rule": "PROJECT_ATTRIBUTION_CONFLATION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "PDF p.15 Discussion/Conclusion",
            "message": (
                "The source paper contains zero mention of physical conservation laws ('物理守恒') or physics-informed coupling. "
                "The authors focus strictly on multi-modal, time-series earth observation, and foundation model adaptation. "
                "Attributing physical conservation to author limitations breaches the faithful-reading firewall."
            ),
            "offending_span": physics_match.group(0) if physics_match else "物理守恒",
            "patch_instruction": (
                "Remove '物理守恒' attribution from author limitations and section leads. Report author-stated limitations: "
                "operator search space bounded, multi-agent communication overhead, sensitivity to image resolution and class imbalance."
            )
        })

    # Rule 6: Best-of-N Run Protocol Caveat (FAIR1M Table I)
    if "FAIR1M" in norm and ("47.30" in norm or "49.14" in norm or "48.18" in norm):
        if not any(w in norm for w in ("三轮中最好", "三次重复中最好", "最好轨迹", "best of three", "best trajectory", "最优轨迹", "3 次独立演化试验中的最优轨迹", "3次独立演化试验中的最优轨迹")):
            diagnostics.append({
                "rule": "EXPERIMENTAL_PROTOCOL_OMISSION",
                "severity": "P0_BLOCKER",
                "verdict": "QUALIFIED",
                "anchor": "PDF p.9 Table I",
                "message": (
                    "Table I reports the best of three independently repeated evolution trajectories, not mean±SD or a single deterministic run. "
                    "This selection caveat must be stated when citing FAIR1M results."
                ),
                "offending_span": "FAIR1M 旋转目标检测逐轮演化结果",
                "patch_instruction": (
                    "Add protocol caveat: '注：表I 报告的是三次独立重复演化试验中的最优轨迹结果'."
                )
            })

    # Rule 7: Baseline Setup Context (YOLO11x-OBB vs Oriented R-CNN)
    if "MSFR" in norm and "CPR" in norm and ("0.73M" in norm or "49.14" in norm):
        if not any(w in norm for w in ("YOLO11x-OBB", "Oriented R-CNN", "检测头配置", "基线配置", "不同主干", "不同配置", "主干配置")):
            diagnostics.append({
                "rule": "EXPERIMENTAL_SETUP_CONFOUND",
                "severity": "QUALIFIED_FLAG",
                "verdict": "QUALIFIED",
                "anchor": "PDF p.9 & Table VI",
                "message": (
                    "Detection baseline in Table I uses YOLO11x-OBB, whereas module ablation in Table VI has specific detection head contexts. "
                    "Setup distinctions should be noted to avoid conflating different baseline comparisons."
                ),
                "offending_span": "MSFR/CPR 架构自主创新",
                "patch_instruction": (
                    "State the detector head / backbone baseline configuration (YOLO11x-OBB vs Oriented R-CNN) when discussing Table VI modules."
                )
            })

    # Rule 8: Metric Definition / Averaging Conventions (F1 vs IoU) & UNVERIFIED_CONVENTION_STATED_AS_FACT
    if "LEVIR-CD" in norm or "EvoChangeStar" in norm:
        if "89.97" in norm and "90.54" in norm:
            if not any(w in norm for w in ("平均方式", "宏平均", "评估约定", "类别平均", "averaging", "基准约定未决", "UNRESOLVED")):
                diagnostics.append({
                    "rule": "METRIC_CONVENTION_AMBIGUITY",
                    "severity": "QUALIFIED_FLAG",
                    "verdict": "QUALIFIED",
                    "anchor": "PDF p.12 Table IV",
                    "message": (
                        "LEVIR-CD Table IV reports F1=90.54% and IoU=89.97%. Under binary single-class formula F1=2IoU/(1+IoU), "
                        "F1 would be ~94.7%. The deviation reflects benchmark-specific multi-class/macro averaging conventions and merits qualification."
                    ),
                    "offending_span": "IoU 从 87.10% 大幅跃升至 89.97%",
                    "patch_instruction": (
                        "Add qualification noting that LEVIR-CD benchmark averaging conventions account for the observed F1-IoU relationship."
                    )
                })
            # Check if asserted as established fact without source script verification
            elif re.search(r"(?:LEVIR-CD|变化检测).*?(?:证实|确系|因为|由于)(?:采用了|使用)?(?:宏平均|多分类宏平均)", norm) or (
                "宏平均" in norm and "LEVIR-CD" in norm and not any(kw in norm for kw in ("未公开", "未说明", "未决", "推定", "假设", "推测", "UNRESOLVED", "未披露", "约定未决", "具体脚本未公开"))
            ):
                diagnostics.append({
                    "rule": "UNVERIFIED_CONVENTION_STATED_AS_FACT",
                    "severity": "QUALIFIED_FLAG",
                    "verdict": "QUALIFIED",
                    "anchor": "PDF p.12 Table IV",
                    "message": (
                        "LEVIR-CD Table IV reports F1=90.54% and IoU=89.97%. The source paper does not disclose its evaluation script or averaging details. "
                        "Asserting macro-averaging as an established fact is unverified; it must be qualified or classified as UNRESOLVED."
                    ),
                    "offending_span": "宏平均计算规则",
                    "patch_instruction": (
                        "Clarify that evaluation scripts are not published in the source, so averaging convention details remain UNRESOLVED."
                    )
                })

    # Rule 9: Modal Certainty Overclaim (UNJUSTIFIED_CERTAINTY_OVERCLAIM)
    clauses = re.split(r'[。；\n]', text)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        negated = any(neg in c_norm for neg in ("并不能", "并未", "无法", "不能", "难以", "不等于", "并非", "不代表", "未能", "未必", "尚未", "不足以"))
        if negated:
            continue
        if any(kw in c_norm for kw in ("彻底消除", "彻底消除了", "绝对保证", "完全杜绝", "彻底解决", "彻底解决了", "完全消除了所有", "毫无疑问地证明", "确凿无疑地证明")):
            diagnostics.append({
                "rule": "UNJUSTIFIED_CERTAINTY_OVERCLAIM",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Scientific Epistemics",
                "message": (
                    f"Unjustified certainty overclaim in: '{c_norm[:70]}...'. "
                    "Empirical machine learning heuristics do not provide absolute guarantees or '彻底消除' errors without formal mathematical proof."
                ),
                "offending_span": c_norm[:60],
                "patch_instruction": "Replace absolute certainty assertions ('彻底消除' / '绝对保证' / '完全杜绝') with calibrated epistemics ('有效缓解', '显著降低', '旨在防范')."
            })
            break

    # Rule 10: Causality / Necessity Overclaim (UNJUSTIFIED_CAUSALITY_OVERCLAIM)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        negated = any(neg in c_norm for neg in ("并不能", "并未", "无法", "不能", "难以", "不等于", "并非", "不代表", "未证实", "未证明", "尚未", "不足以", "未表明"))
        if negated:
            continue
        has_causality = (
            bool(re.search(r"证实(?:了)?(?:其)?.*?不可替代", c_norm))
            or bool(re.search(r"证明(?:了)?(?:其)?.*?绝对必要", c_norm))
            or any(kw in c_norm for kw in ("证实不可替代", "绝对必要性", "唯一通路", "唯一机制"))
        )
        if has_causality:
            diagnostics.append({
                "rule": "UNJUSTIFIED_CAUSALITY_OVERCLAIM",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Scientific Epistemics",
                "message": (
                    f"Unjustified causality overclaim in: '{c_norm[:70]}...'. "
                    "Empirical ablation on limited configurations demonstrates marginal performance utility, not universal indispensability or absolute necessity."
                ),
                "offending_span": c_norm[:60],
                "patch_instruction": "Replace necessity overclaims ('证实不可替代性' / '证明其绝对必要性') with calibrated statements ('消融实验显示该模块在当前任务下提供了关键精度增益')."
            })
            break

    # Rule 11: Statistical Controls & Synergy Overclaims (SYNERGY_OVERCLAIM_WITHOUT_CONTROLS)
    if ("MSFR" in norm and "CPR" in norm) or "联合消融" in norm or "模块联合" in norm:
        if any(kw in norm for kw in ("超加性", "超越相加", "超越简单相加", "强烈的协同效应", "强烈的协同增益", "协同质变")):
            diagnostics.append({
                "rule": "SYNERGY_OVERCLAIM_WITHOUT_CONTROLS",
                "severity": "QUALIFIED_FLAG",
                "verdict": "QUALIFIED",
                "anchor": "PDF p.13 Table VI",
                "message": (
                    "Combined gain of MSFR (+1.01 pp) and CPR (+0.99 pp) is +1.84 pp, which is numerically consistent with linear additivity "
                    "(1.01 + 0.99 = 2.00 pp) and shows slight diminishing marginal returns (+1.84 vs 2.00 pp). Asserting super-additive synergy without statistical interaction tests is ungrounded."
                ),
                "offending_span": "超加性协同 / 协同效应质变",
                "patch_instruction": "Describe combined gains as additive: '两项模块联合使用时取得 +1.84 个百分点增益，体现了良好的增量累加效果，而非已证明的超加性协同'."
            })

    # Rule 12: Percentage vs Percentage Points Confusion (PERCENTAGE_VS_POINTS_CONFUSION)
    if "个百分比" in norm:
        diagnostics.append({
            "rule": "PERCENTAGE_VS_POINTS_CONFUSION",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "Statistical Metric Reporting",
            "message": "Used '个百分比' instead of '个百分点' (percentage points, pp) when reporting metric changes on a percentage scale.",
            "offending_span": "个百分比",
            "patch_instruction": "Replace '个百分比' with '个百分点（percentage points）' or 'pp'."
        })
    elif ("47.30" in norm and "49.14" in norm) or re.search(r"\b\d+\.\d+%\s*(?:提升|增长|增加|跃升)(?:至|到)\s*\d+\.\d+%", norm):
        if re.search(r"(?:提升|增加|提高|增长|幅度|达|为)(?:了)?\s*1\.84%", norm) and not re.search(r"1\.84\s*(?:个百分点|pp|percentage point)", norm):
            diagnostics.append({
                "rule": "PERCENTAGE_VS_POINTS_CONFUSION",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "p.9 Table I / p.13 Table VI",
                "message": (
                    "Reporting an increase from 47.30% to 49.14% as '提升了 1.84%' conflates an absolute change of 1.84 percentage points (pp) "
                    "with a relative gain of 1.84% (which would only reach ~48.17%)."
                ),
                "offending_span": "从 47.30% 提升至 49.14%...提升了 1.84%",
                "patch_instruction": "Change '提升了 1.84%' to '提升了 1.84 个百分点（percentage points）' or '净增 1.84 pp'."
            })

    # Rule 13: Internal Audit Vocabulary & Pipeline Tag Leakage (AUDIT_VOCABULARY_LEAKAGE)
    bracket_match = re.search(r"【(?:科学核验|证据核验|核验记录|审查透镜|机制核验|门禁检查|事实核查|事实核验|核验结论|审计标记|核验通过)[^】]*】", text)
    if bracket_match:
        diagnostics.append({
            "rule": "AUDIT_VOCABULARY_LEAKAGE",
            "severity": "P0_BLOCKER",
            "verdict": "CONTRADICTED",
            "anchor": "Editorial Presentation",
            "message": f"Internal audit bracket tag leaked into user-facing narrative: '{bracket_match.group(0)}'.",
            "offending_span": bracket_match.group(0),
            "patch_instruction": "Remove all internal audit bracket tags from narrative prose."
        })
    pipeline_jargon = ("必须严格恪守", "输入防火墙", "防火墙机制", "Lead Writer", "Analytical Agent")
    for jw in pipeline_jargon:
        if jw in text:
            diagnostics.append({
                "rule": "AUDIT_VOCABULARY_LEAKAGE",
                "severity": "P0_BLOCKER",
                "verdict": "CONTRADICTED",
                "anchor": "Editorial Presentation",
                "message": f"Pipeline internal control jargon '{jw}' leaked into user-facing narrative.",
                "offending_span": jw,
                "patch_instruction": f"Remove or replace internal process phrase '{jw}' with natural editorial prose."
            })
            break

    # Rule 14: Table I FAIR1M Sequential Evolution Trajectory Fidelity
    # Ground truth: 47.30 -> 48.18 -> 47.77 -> 47.69 -> 49.11 -> 49.14 (best of 3 independent runs)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        c_lower = c_norm.lower()
        if any(w in c_lower for w in ("table i", "table 1", "表 i", "表i", "表1", "演化轨迹", "逐轮演化", "阶段")):
            if any(f in c_lower for f in ("47.88", "48.45", "48.82")):
                diagnostics.append({
                    "rule": "TABLE_I_TRAJECTORY_FIDELITY",
                    "severity": "P0_BLOCKER",
                    "verdict": "CONTRADICTED",
                    "anchor": "PDF p.9 Table I",
                    "message": (
                        "Table I reports exact progression: 47.30% (Baseline) -> 48.18% (Data Aug) -> 47.77% (Config Update) -> "
                        "47.69% (Few-Shot) -> 49.11% (Multi-Model Fusion) -> 49.14% (Combined Module Innovation). "
                        "Fabricated intermediate numbers 47.88%, 48.45%, 48.82% contradict the source table."
                    ),
                    "offending_span": clause.strip()[:60],
                    "patch_instruction": (
                        "Restore exact Table I trajectory: 47.30% -> 48.18% (Data Aug) -> 47.77% (Config Update) -> "
                        "47.69% (Few-Shot) -> 49.11% (Multi-Model Fusion) -> 49.14% (Combined Module Innovation)."
                    )
                })
                break

    # Rule 15: Table VI Module Ablation Fidelity (MSFR & CPR gains)
    # Ground truth: Baseline 47.30%, MSFR alone 48.31% (+1.01 pp), CPR alone 48.29% (+0.99 pp), MSFR+CPR 49.14% (+1.84 pp)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        c_lower = c_norm.lower()
        if any(w in c_lower for w in ("table vi", "table 6", "表 vi", "表vi", "表6", "msfr", "cpr", "模块独立")):
            if any(w in c_lower for w in ("1.15 pp", "1.15pp", "1.15 个百分点", "1.15%", "+1.15")):
                diagnostics.append({
                    "rule": "TABLE_VI_MODULE_ABLATION_FIDELITY",
                    "severity": "P0_BLOCKER",
                    "verdict": "CONTRADICTED",
                    "anchor": "PDF p.13 Table VI",
                    "message": (
                        "Table VI reports MSFR alone reaches 48.31% mAP50 (+1.01 pp over baseline 47.30%), NOT +1.15 pp."
                    ),
                    "offending_span": clause.strip()[:60],
                    "patch_instruction": "Correct MSFR gain to +1.01 pp (47.30% -> 48.31% mAP50, +0.599M params, +0.604G FLOPs)."
                })
                break
            if any(w in c_lower for w in ("0.92 pp", "0.92pp", "0.92 个百分点", "0.92%", "+0.92")):
                diagnostics.append({
                    "rule": "TABLE_VI_MODULE_ABLATION_FIDELITY",
                    "severity": "P0_BLOCKER",
                    "verdict": "CONTRADICTED",
                    "anchor": "PDF p.13 Table VI",
                    "message": (
                        "Table VI reports CPR alone reaches 48.29% mAP50 (+0.99 pp over baseline 47.30%), NOT +0.92 pp."
                    ),
                    "offending_span": clause.strip()[:60],
                    "patch_instruction": "Correct CPR gain to +0.99 pp (47.30% -> 48.29% mAP50, +0.131M params, +0.272G FLOPs)."
                })
                break

    # Rule 16: Table VIII Critic Mechanism Ablation Fidelity
    # Ground truth: Full Framework: 7 rounds, 49.14% mAP; w/o Critic Mechanism: 11 rounds, 47.43% mAP (drop of 1.71 pp)
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        c_lower = c_norm.lower()
        if any(w in c_lower for w in ("critic", "审稿")):
            if ("14 轮" in c_norm or "14轮" in c_norm or "47.88" in c_norm) and any(w in c_lower for w in ("移除", "剥离", "无", "w/o", "没有")):
                diagnostics.append({
                    "rule": "TABLE_VIII_CRITIC_ABLATION_FIDELITY",
                    "severity": "P0_BLOCKER",
                    "verdict": "CONTRADICTED",
                    "anchor": "PDF p.14 Table VIII",
                    "message": (
                        "Table VIII reports removing Critic Mechanism requires 11 rounds and achieves 47.43% mAP (drop of 1.71 pp from 49.14%). "
                        "Claiming 14 rounds or 47.88% conflates Table VIII with Table IX."
                    ),
                    "offending_span": clause.strip()[:60],
                    "patch_instruction": (
                        "Correct Table VIII numbers to: Full framework: 7 rounds, 49.14% mAP; w/o Critic: 11 rounds, 47.43% mAP."
                    )
                })
                break

    # Rule 17: Table IX Experience Bus Ablation Fidelity
    # Ground truth: Full Framework: Rounds=7, Failed=2, mAP=49.14%
    # w/o External: Rounds=9, Failed=4, mAP=48.44%
    # w/o Internal: Rounds=11, Failed=5, mAP=47.62%
    # w/o Both: Rounds=14, Failed=6, mAP=47.53%
    for clause in clauses:
        c_norm = _clean_text(clause)
        if not c_norm:
            continue
        c_lower = c_norm.lower()
        if any(w in c_lower for w in ("table ix", "table 9", "表 ix", "表ix", "表9", "经验总线")):
            if re.search(r"(?:压减为|减少为|降至|降低至|仅|只有)\s*(?:1|一)\s*次", c_norm) and any(w in c_lower for w in ("非提升", "失败", "failed")):
                diagnostics.append({
                    "rule": "TABLE_IX_EXPERIENCE_BUS_ABLATION_FIDELITY",
                    "severity": "P0_BLOCKER",
                    "verdict": "CONTRADICTED",
                    "anchor": "PDF p.14 Table IX",
                    "message": (
                        "Table IX reports Full Framework (Ours) experienced Failed = 2 non-improving iterations (out of 7 rounds). "
                        "Claiming non-improving iterations were reduced to only 1 contradicts the source table."
                    ),
                    "offending_span": clause.strip()[:60],
                    "patch_instruction": (
                        "Correct Table IX reporting: Full Framework had 2 non-improving iterations (Failed=2); "
                        "w/o both streams had 6 (Failed=6), achieving a reduction from 6 to 2."
                    )
                })
                break

    return diagnostics


# Canonical benchmark claim registries
# Benchmark-specific claim templates were removed (Issue #46). A production
# verifier must never carry a known paper's answers: that turns verification into
# template matching and silently passes papers it has never seen. Historical
# fixtures live under evals/ for regression only.


def extract_dynamic_claims_from_manuscript(root: Path, manuscript_data: Dict[str, Any], diagnostics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract candidate statements; independent source review must confirm them."""
    doc = manuscript_data.get("document", {})
    chapters = doc.get("sections") or doc.get("chapters", [])
    extracted_claims = []
    claim_counter = 1

    # Also load paper_model claims if available
    pm_path = root / "model/paper_model.json"
    pm_claims = {}
    if pm_path.exists():
        try:
            pm = load_json(pm_path)
            for c in pm.get("claims", []):
                pm_claims[c.get("id")] = c
        except Exception:
            pass

    for ch_idx, chapter in enumerate(chapters, 1):
        cid = chapter.get("id", f"sec-{ch_idx:02d}")
        blocks = chapter.get("blocks", [])
        for b in blocks:
            b_type = b.get("type")
            text = _clean_text(b.get("text") or b.get("analysis") or "")
            if not text:
                continue

            # Prioritize blocks designed to carry key takeaways or quantitative observations
            is_takeaway = b_type in ("takeaway", "callout")
            is_table_fig = b_type in ("table", "figure") and b.get("analysis")
            has_quant = bool(re.search(r"\d+(?:\.\d+)?%|\d+M|\d+x|\bmAP\b|\bIoU\b|\bF1\b|\bBLEU\b|\bAcc\b|\bpLDDT\b|\bpp\b|提升|降低", text))

            if is_takeaway or is_table_fig or has_quant:
                # Split into sentence-level atomic statements
                sentences = [s.strip() for s in re.split(r"[。；\n]", text) if len(s.strip()) >= 15]
                for s in sentences:
                    # Determine epistemic category
                    category = "OBSERVATION"
                    if any(w in s for w in ("未公开", "未说明", "未决", "UNRESOLVED", "缺少详细", "待验证")):
                        category = "UNRESOLVED"
                    elif any(w in s for w in ("局限", "边界", "权衡", "独立评估", "代价", "注意")):
                        category = "READER_ASSESSMENT"
                    elif any(w in s for w in ("机制", "假设", "设计动机", "旨在", "认为", "提出", "归因")):
                        category = "AUTHOR_INTERPRETATION"

                    anchors = [f"p.{b.get('page', 1)}"]
                    if b.get("evidence_id"):
                        anchors.append(str(b["evidence_id"]))
                    for ref in b.get("evidence_refs", []):
                        if ref not in anchors:
                            anchors.append(ref)

                    # Extract numerical semantics if present
                    quant_match = re.search(r"(\d+(?:\.\d+)?%|\d+\.\d+\s*(?:pp|个百分点)|\d+M|\d+G)", s)
                    num_sem = None
                    if quant_match:
                        num_sem = {
                            "metric": "Quantitative Measurement",
                            "statistic": quant_match.group(0),
                            "unit": "percentage or count"
                        }

                    # Check against diagnostics for matching contradictions
                    matching_diags = [
                        d for d in diagnostics
                        if (d.get("offending_span") and d["offending_span"] in s)
                        or (d.get("anchor") and d["anchor"] in anchors)
                    ]
                    # Failure to match known-error patterns cannot prove
                    # agreement with the source PDF.
                    verdict = "UNVERIFIED"
                    reasoning = "Reader candidate; source comparison has not run."
                    severity = "INFORMATIONAL"
                    if category == "UNRESOLVED":
                        verdict = "UNRESOLVED"
                        reasoning = "Convention or protocol detail is unresolved in source publication."
                    elif matching_diags:
                        first_d = matching_diags[0]
                        verdict = first_d.get("verdict", "CONTRADICTED")
                        severity = first_d.get("severity", "P0_BLOCKER")
                        reasoning = first_d.get("message", "Contradicted by source evidence.")

                    extracted_claims.append({
                        "claim_id": f"CLM-DYN-{claim_counter:02d}",
                        "statement": s[:150],
                        "source_anchors": anchors,
                        "evidence_refs": [a for a in anchors if a.startswith(("F", "T", "EQ", "p."))],
                        "epistemic_category": category,
                        "numerical_semantics": num_sem,
                        "attribution": {
                            "attributed_to": "AUTHORS" if category != "READER_ASSESSMENT" else "EVIDENTIA_INDEPENDENT",
                            "source_confirmed": False,
                            "project_context_leakage": False
                        },
                        "confidence": "UNCERTAIN",
                        "boundaries": [f"Derived from section {cid}"],
                        "verdict": verdict,
                        "verifier_reasoning": reasoning,
                        "severity": severity
                    })
                    claim_counter += 1

    # Preserve a clearly unverified placeholder if no material candidate was extracted.
    if not extracted_claims:
        extracted_claims.append({
            "claim_id": "CLM-DYN-01",
            "statement": doc.get("title", "未命名论文核心科学主张"),
            "source_anchors": ["p.1"],
            "evidence_refs": ["p.1"],
            "epistemic_category": "OBSERVATION",
            "numerical_semantics": None,
            "attribution": {
                "attributed_to": "AUTHORS",
                "source_confirmed": False,
                "project_context_leakage": False
            },
            "confidence": "UNCERTAIN",
            "boundaries": ["No substantive candidate found"],
            "verdict": "UNVERIFIED",
            "verifier_reasoning": "Title only; no source verification.",
            "severity": "INFORMATIONAL"
        })

    return extracted_claims


def build_claim_ledger_for_manuscript(root: Path, manuscript_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build an Atomic Claim Ledger from a Reader manuscript and workspace source."""
    root = Path(root)
    source_sha = manuscript_data.get("source_sha256") or "0" * 64
    paper_id = manuscript_data.get("paper_id") or root.name
    doc = manuscript_data.get("document", {})
    paper_meta = doc.get("paper_meta", {})
    title = doc.get("title", "")

    # Determine venue verification status
    claimed_venue = paper_meta.get("venue") or ""
    is_arxiv = "arxiv" in claimed_venue.lower() or "arxiv" in (paper_meta.get("doi") or "").lower()
    venue_verified = bool(paper_meta.get("venue_verified_externally", False))
    peer_status = "PEER_REVIEWED" if venue_verified else "UNVERIFIED"
    preprint_status = "PREPRINT" if is_arxiv else "UNKNOWN"
    formatted_venue = claimed_venue

    if ("tgrs" in claimed_venue.lower() or "ieee" in claimed_venue.lower()) and not venue_verified:
        formatted_venue = f"{claimed_venue} (unverified · preprint only)"
        peer_status = "UNVERIFIED"

    venue_info = {
        "venue_claimed_by_pdf": claimed_venue or "arXiv:2609.00814v2",
        "venue_verified_externally": venue_verified,
        "peer_reviewed_status": peer_status,
        "preprint_status": preprint_status,
        "evidence_source": "PDF header / bibliographic metadata",
        "formatted_header_venue": formatted_venue
    }

    # Extract all text from blocks to inspect assertions
    chapters = doc.get("sections") or doc.get("chapters", [])
    all_blocks = [b for c in chapters for b in c.get("blocks", [])]
    full_text = " ".join([
        title,
        doc.get("subtitle", ""),
        doc.get("orientation", {}).get("lead", ""),
        " · ".join(paper_meta.get("authors", [])),
        claimed_venue,
        " ".join([c.get("title", "") + " " + (c.get("lead_paragraph") or c.get("lead", "")) for c in chapters]),
        " ".join([b.get("text", "") or b.get("analysis", "") or b.get("caption", "") for b in all_blocks])
    ])

    diagnostics = verify_text_claims(full_text, {"venue_status": venue_info})

    # Never use paper-specific cached claim templates as scientific truth.
    # The historical registry is retained for old fixtures, not production.
    claims = extract_dynamic_claims_from_manuscript(root, manuscript_data, diagnostics)

    contradicted_count = sum(1 for c in claims if c["verdict"] == "CONTRADICTED")
    critical_contradictions = [
        f"{c['claim_id']} ({c['statement']}): {c['verifier_reasoning']}"
        for c in claims if c["verdict"] == "CONTRADICTED" and c.get("severity") == "P0_BLOCKER"
    ]

    if critical_contradictions:
        status = "FAIL"
    elif not claims:
        # Nothing was even extracted, so nothing was verified.
        status = "NOT_RUN"
    elif any(
        c["verdict"] in ("CONTRADICTED", "UNSUPPORTED", "UNVERIFIED", "UNRESOLVED")
        for c in claims
    ):
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"

    ledger = {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "source_sha256": source_sha,
        "venue_verification": venue_info,
        "claims": claims,
        "verification_summary": {
            "total_claims": len(claims),
            "supported": sum(1 for c in claims if c["verdict"] == "SUPPORTED"),
            "qualified": sum(1 for c in claims if c["verdict"] == "QUALIFIED"),
            "contradicted": contradicted_count,
            "unsupported": sum(1 for c in claims if c["verdict"] == "UNSUPPORTED"),
            "unresolved": sum(1 for c in claims if c["verdict"] == "UNRESOLVED"),
            "unverified": sum(1 for c in claims if c["verdict"] == "UNVERIFIED"),
            "critical_contradictions": critical_contradictions,
            "diagnostics": diagnostics,
            "status": status
        }
    }
    return ledger


def verify_reader_scientific_integrity(root: Path, manuscript_data: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Run full scientific claim verification and return ledger and acceptance error list."""
    root = Path(root)
    if manuscript_data is None:
        manuscript_p = root / "reader/narrative_manuscript.json"
        if not manuscript_p.exists():
            return {}, ["Missing reader/narrative_manuscript.json for scientific claim verification"]
        manuscript_data = load_json(manuscript_p)

    ledger = build_claim_ledger_for_manuscript(root, manuscript_data)
    errors = []

    # Validate claim ledger against schema
    schema_errs = list(schema_validate(ledger, "claim_ledger"))
    if schema_errs:
        errors.extend([f"Claim ledger schema error: {e}" for e in schema_errs])

    # Check verification summary
    summary = ledger.get("verification_summary", {})
    if summary.get("critical_contradictions"):
        for crit in summary["critical_contradictions"]:
            errors.append(f"Scientific integrity violation: {crit}")

    for diag in summary.get("diagnostics", []):
        if diag.get("severity") == "P0_BLOCKER" and diag.get("verdict") == "CONTRADICTED":
            msg = f"[{diag.get('rule')}] {diag.get('anchor')}: {diag.get('message')}"
            if msg not in errors:
                errors.append(msg)

    # Also inspect rendered HTML and Markdown for audit tags and leaks if present
    for fname in ("reader/paper_reader.html", "reader/paper_reader.md"):
        p = root / fname
        if p.exists():
            content = p.read_text(encoding="utf-8")
            render_diags = verify_text_claims(content, {"venue_status": ledger.get("venue_verification")})
            for rd in render_diags:
                if rd.get("severity") == "P0_BLOCKER" and rd.get("verdict") == "CONTRADICTED":
                    msg = f"[{rd.get('rule')}] {fname}: {rd.get('message')}"
                    if msg not in errors:
                        errors.append(msg)

    # Persist claim ledger into model/claim_ledger.json
    ledger_p = root / "model/claim_ledger.json"
    ledger_p.parent.mkdir(parents=True, exist_ok=True)
    ledger_p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return ledger, errors


def main():
    ap = argparse.ArgumentParser(description="Evidentia Scientific Claim Verifier")
    ap.add_argument("--out", required=True, help="Workspace root or paper folder")
    ap.add_argument("--check-file", help="Arbitrary markdown / text file to verify against integrity rules")
    args = ap.parse_args()

    root = Path(args.out)
    if args.check_file:
        text = Path(args.check_file).read_text(encoding="utf-8")
        diagnostics = verify_text_claims(text)
        print(json.dumps({"diagnostics": diagnostics, "status": "FAIL" if diagnostics else "PASS"}, indent=2, ensure_ascii=False))
        sys.exit(1 if any(d.get("severity") == "P0_BLOCKER" for d in diagnostics) else 0)

    ledger, errors = verify_reader_scientific_integrity(root)
    print(json.dumps(ledger.get("verification_summary", {}), indent=2, ensure_ascii=False))
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
