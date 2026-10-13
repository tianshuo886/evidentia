#!/usr/bin/env python3
"""Reader Math Explanation Audit Tool (Issue #40).

Evaluates whether mathematical formulas in Reader v3 are pedagogically explained,
grounded in source evidence, and free from misleading or mathematically altered semantics.

Verification Criteria:
1. Materiality & Roles: Each equation has a defined operational role and explanation priority
   (MUST_EXPLAIN, CONCISE_DEFINE, AUDIT_ONLY).
2. Teaching Contract (MUST_EXPLAIN equations):
   - Why here: Explains the theoretical or engineering problem that necessitates the formula.
   - What it computes: Identifies inputs, outputs, and constituent symbols.
   - How it works: Decomposes key terms, explaining the intuitive effect of operators,
     signs, fractions, denominators, and exponentials.
   - Engineering proxies: Explicitly distinguishes practical proxies (e.g., CV_50) from
     theoretical formulations (e.g., Hessian norm), stating unverified or omitted details.
3. Anti-Patterns & Rejections:
   - Silent Equations: Reject equations rendered with only a generic 1-line label.
   - Contradictory Explanations: Reject false statements that contradict the mathematics
     (e.g., claiming 1 - B_t rewards bottlenecks or claiming a surrogate is an exact second derivative).
4. Concise Definitions: Allow concise definitions for auxiliary/notation equations.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Common mathematical terms indicating priority
MUST_EXPLAIN_INDICATORS = [
    r"\frac", r"/", r"\exp", r"\sum", r"\text{softmax}", r"\Pi", r"W_0",
    r"\nabla", r"\le", r"\ge", r"Score", r"f_{\text{score}}"
]

CONTRADICTION_RULES = [
    {
        "anchor": r"1\s*-\s*B_t|Score_t|Critic",
        "pattern": r"瓶颈.*(越严重|越大).*得分.*(越高|上升|增加)|奖励.*瓶颈",
        "neg_keywords": ["反转", "抑制", "惩罚", "降低", "扣除", "并非", "压低"],
        "error": "MATHEMATICAL_CONTRADICTION: 错误声称瓶颈越严重得分越高 (1-B_t 实质为反转抑制)"
    },
    {
        "anchor": r"f_\{?\\?text\{score\}\}|f_\{?score\}?|CV_\{?50\}?|cv50|二阶|早筛",
        "pattern": r"(?:准确|严格|精确|直接)计算.*(?:二阶|Hessian)",
        "neg_keywords": ["开销", "代理", "替代", "无法", "不可行", "过大", "并非", "轻量"],
        "error": "MATHEMATICAL_CONTRADICTION: 错误声称工程实现精确计算了二阶 Hessian (实际使用 CV_50 作为轻量代理)"
    }
]


def _clean_text(s: str) -> str:
    if not s:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", str(s))
    # Normalize whitespaces
    return re.sub(r"\s+", " ", clean).strip()


def audit_single_equation(eq_data: dict, full_context_text: str) -> dict:
    """Audit the pedagogical depth and correctness of a single equation."""
    eq_id = eq_data.get("evidence_id") or eq_data.get("equation_id") or "EQ"
    paper_label = eq_data.get("paper_label") or f"Eq. ({eq_data.get('equation_number', '')})"
    latex = eq_data.get("latex") or eq_data.get("raw_text") or ""
    pedagogy = eq_data.get("pedagogy") or {}
    local_exp = eq_data.get("explanation") or ""

    # Priority determination
    priority = pedagogy.get("explanation_priority") or eq_data.get("explanation_priority")
    if not priority:
        eq_num = eq_data.get("equation_number")
        if eq_num in (1, 2, 5, 6, 9, 10, 12, 13) or any(ind in latex for ind in MUST_EXPLAIN_INDICATORS):
            priority = "MUST_EXPLAIN"
        elif eq_num in (3, 4, 7, 8, 11, 14, 15):
            priority = "CONCISE_DEFINE"
        else:
            priority = "AUDIT_ONLY"

    res = {
        "equation_id": eq_id,
        "paper_label": paper_label,
        "priority": priority,
        "role": pedagogy.get("role") or eq_data.get("role_zh") or "公式定义",
        "passed": True,
        "issues": [],
        "checks": {}
    }

    combined_text = f"{local_exp} {full_context_text}"

    # Check 1: Silent equation check
    has_meaningful_local = len(_clean_text(local_exp)) >= 15
    # Look for mentions of eq_id or paper_label in context
    anchor_pattern = rf"{re.escape(eq_id)}|{re.escape(paper_label)}|公式\s*\(?{re.escape(str(eq_data.get('equation_number', '')))}\)?"
    has_prose_mention = bool(re.search(anchor_pattern, full_context_text))

    res["checks"]["not_silent"] = has_meaningful_local or has_prose_mention
    if not (has_meaningful_local or has_prose_mention):
        res["passed"] = False
        res["issues"].append(f"UNEXPLAINED_MATERIAL_EQUATION: {paper_label} [{eq_id}] 缺乏足够教学式解释 (仅有简略标签或空白)")
        return res

    # Check 2: Sentence-level contradiction checks
    sentences = [s.strip() for s in re.split(r"[。；\n]", combined_text) if s.strip()]
    for rule in CONTRADICTION_RULES:
        if re.search(rule["anchor"], latex, re.I) or re.search(rule["anchor"], combined_text, re.I):
            for s in sentences:
                if re.search(rule["pattern"], s):
                    if any(k in s for k in rule.get("neg_keywords", [])):
                        continue
                    res["passed"] = False
                    res["issues"].append(rule["error"])
                    break

    # Check 3: MUST_EXPLAIN detailed pedagogy requirements
    if priority == "MUST_EXPLAIN":
        # A: Term decomposition
        term_interps = pedagogy.get("term_interpretations") or []
        symbols = pedagogy.get("symbol_definitions") or eq_data.get("symbols") or []

        explained_terms = 0
        target_terms = term_interps or symbols
        if target_terms:
            for item in target_terms:
                symbol_token = item.get("symbol") or item.get("term") or ""
                token_clean = symbol_token.replace("\\", "").replace("{", "").replace("}", "").strip()
                meaning = item.get("interpretation") or item.get("meaning_zh") or item.get("intuition") or ""
                # Check if term or its intuition appears in combined text
                if token_clean and (token_clean in combined_text or (meaning and meaning[:6] in combined_text)):
                    explained_terms += 1

            term_coverage = explained_terms / len(target_terms)
            res["checks"]["term_coverage"] = term_coverage
            if term_coverage < 0.4 and len(target_terms) > 1:
                res["passed"] = False
                res["issues"].append(f"INSUFFICIENT_TERM_GROUNDING: {paper_label} 仅解释了 {explained_terms}/{len(target_terms)} 个关键项")

        # B: Special paper-specific semantic audits
        # RingMoClaw Eq. 1: Must explain 1 - B_t bottleneck inversion
        if "1 - B_t" in latex or "1-B_t" in latex:
            explains_inversion = any(kw in combined_text for kw in ["反转", "抑制", "惩罚", "逆向", "1 - B", "1-B"])
            res["checks"]["explains_bottleneck_inversion"] = explains_inversion
            if not explains_inversion:
                res["passed"] = False
                res["issues"].append(f"MISSING_OPERATION_INTUITION: {paper_label} 未解释 1 - B_t 逆向抑制瓶颈的数学直觉")

        # RingMoClaw Eq. 6: Must explain Delta t (rate), stability penalty, and CV_50 proxy
        if "Delta" in latex and ("Acc" in latex or "acc" in latex):
            explains_rate = any(kw in combined_text for kw in ["时间", "效率", "速度", "变化率", "Δt", "Delta t", "单位时间"])
            res["checks"]["explains_rate"] = explains_rate
            if not explains_rate:
                res["passed"] = False
                res["issues"].append(f"MISSING_OPERATION_INTUITION: {paper_label} 未解释除以 Δt 的单位时间效率/变化率意义")

            explains_proxy = any(kw in combined_text for kw in ["变异系数", "CV", "代理", "最后 50 步", "最后50步", "50 步", "轻量"])
            res["checks"]["explains_proxy"] = explains_proxy
            if not explains_proxy:
                res["passed"] = False
                res["issues"].append(f"MISSING_IMPLEMENTATION_PROXY: {paper_label} 未明确说明工程实现中采用损失变异系数作为二阶曲率轻量代理")

        # Attention Eq. 1: Must explain 1/sqrt(d_k) scaling factor preventing gradient saturation
        if "softmax" in latex and ("d_k" in latex or r"\sqrt" in latex):
            explains_scaling = any(kw in combined_text for kw in ["缩放", "方差", "梯度消失", "饱和", "极小", "根号", "d_k"])
            res["checks"]["explains_scaling"] = explains_scaling
            if not explains_scaling:
                res["passed"] = False
                res["issues"].append(f"MISSING_OPERATION_INTUITION: {paper_label} 未解释 1/sqrt(d_k) 缩放因子防止 softmax 梯度饱和的直觉")

        # LoRA Eq. 3: Must explain rank decomposition BA and alpha/r scaling
        if "W_0" in latex and ("B" in latex or "BA" in latex):
            explains_low_rank = any(kw in combined_text for kw in ["低秩", "分解", "本征", "内在秩", "参数量", "降维"])
            res["checks"]["explains_low_rank"] = explains_low_rank
            if not explains_low_rank:
                res["passed"] = False
                res["issues"].append(f"MISSING_OPERATION_INTUITION: {paper_label} 未解释低秩分解重参数化的数学直觉")

    elif priority == "CONCISE_DEFINE":
        # Concise definition check: role or definition must be present
        has_concise_def = len(_clean_text(local_exp)) >= 10 or has_prose_mention
        res["checks"]["has_concise_def"] = has_concise_def
        if not has_concise_def:
            res["passed"] = False
            res["issues"].append(f"MISSING_CONCISE_DEFINITION: {paper_label} 缺乏基本概念定义")

    return res


def audit_math_pedagogy(root: Path, manuscript: dict = None, html_text: str = None, md_text: str = None) -> dict:
    """Comprehensive math pedagogy audit of Reader artifacts."""
    root = Path(root)
    if manuscript is None:
        manuscript_p = root / "reader/narrative_manuscript.json"
        if manuscript_p.exists():
            try:
                manuscript = json.loads(manuscript_p.read_text(encoding="utf-8"))
            except Exception:
                manuscript = {}
        else:
            manuscript = {}

    if html_text is None:
        html_p = root / "reader/paper_reader.html"
        html_text = html_p.read_text(encoding="utf-8") if html_p.exists() else ""

    if md_text is None:
        md_p = root / "reader/paper_reader.md"
        md_text = md_p.read_text(encoding="utf-8") if md_p.exists() else ""

    full_context_text = f"{_clean_text(html_text)} {_clean_text(md_text)}"

    # Gather all equations
    equations_to_audit = []

    # 1. Gather from manuscript blocks
    doc = manuscript.get("document", {})
    sections = doc.get("sections") or doc.get("chapters") or []
    for sec in sections:
        for b in sec.get("blocks", []):
            if b.get("type") == "equation":
                equations_to_audit.append(b)

    # 2. If manuscript has no equations, gather from source_map
    if not equations_to_audit:
        source_map_p = root / "model/source_map.json"
        if source_map_p.exists():
            try:
                sm = json.loads(source_map_p.read_text(encoding="utf-8"))
                for page in sm.get("pages", []):
                    for eq in page.get("equations", []):
                        if isinstance(eq, dict):
                            equations_to_audit.append(eq)
            except Exception:
                pass

    if not equations_to_audit:
        return {
            "status": "PASSED",
            "score": 1.0,
            "equations_count": 0,
            "audited": [],
            "errors": [],
            "warnings": ["No display equations found in reader artifacts to audit."]
        }

    audited_results = []
    all_errors = []
    passed_count = 0

    for eq in equations_to_audit:
        res = audit_single_equation(eq, full_context_text)
        audited_results.append(res)
        if res["passed"]:
            passed_count += 1
        else:
            all_errors.extend(res["issues"])

    score = passed_count / len(equations_to_audit) if equations_to_audit else 1.0
    status = "PASSED" if not all_errors else "FAILED"

    return {
        "status": status,
        "score": round(score, 4),
        "equations_count": len(equations_to_audit),
        "passed_count": passed_count,
        "audited": audited_results,
        "errors": all_errors,
        "warnings": []
    }


def main():
    parser = argparse.ArgumentParser(description="Audit Reader Math Pedagogy")
    parser.add_argument("workspace", type=Path, help="Evidentia run workspace path")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    result = audit_math_pedagogy(args.workspace)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"=== Math Pedagogy Audit: {result['status']} (Score: {result['score'] * 100:.1f}%) ===")
        print(f"Audited {result['equations_count']} equations ({result['passed_count']} passed).")
        for eq in result["audited"]:
            status_icon = "✓" if eq["passed"] else "✗"
            print(f"  [{status_icon}] {eq['paper_label']} [{eq['equation_id']}] ({eq['priority']}): {eq['role']}")
            for issue in eq["issues"]:
                print(f"      -> {issue}")
        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for err in result["errors"]:
                print(f"  - {err}")

    sys.exit(0 if result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
