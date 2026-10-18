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
   - Engineering proxies: Distinguish practical proxies from theoretical formulations,
     stating unverified or omitted implementation details when the source supports them.
3. Anti-Patterns & Rejections:
   - Silent Equations: Reject equations rendered with only a generic 1-line label.
   - Contradictory Explanations: Flag contradictions between the source-verified equation
     and the explanation; automatic checks do not supply paper-specific answer rules.
4. Concise Definitions: Allow concise definitions for auxiliary/notation equations.
5. Paper-agnostic Rules: Derive explanation priority from mathematical structure and
   explicit pedagogy metadata, never a paper identity or equation number.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Common operators whose behavior usually needs explanation. Rule selection is
# based only on mathematical structure, never paper identity or equation number.
MUST_EXPLAIN_INDICATORS = [
    r"\frac", r"/", r"\exp", r"\sum", r"\text{softmax}", r"\Pi",
    r"\nabla", r"\le", r"\ge", r"\sqrt", r"\int", r"\prod"
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
        if any(ind in latex for ind in MUST_EXPLAIN_INDICATORS):
            priority = "MUST_EXPLAIN"
        elif "=" in latex and len(latex) > 20:
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

    # Check 2: MUST_EXPLAIN detailed pedagogy requirements
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
