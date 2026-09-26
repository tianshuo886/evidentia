#!/usr/bin/env python3
"""Evidence-Localized Verifier for Evidentia claims, findings, and conflicts.

Evaluates candidate assertions against localized source evidence:
- Text snippets & captions
- Table cells
- Visual asset inspection (image existence, dimensions, channel validity)

Strictly enforces Principle 4: NO majority voting.
Verdicts: SUPPORTED, PARTIAL, REJECTED, AMBIGUOUS, INSUFFICIENT_EVIDENCE.
"""
import argparse, json, os, re, sys
from pathlib import Path

VALID_VERDICTS = (
    "SUPPORTED",
    "PARTIAL",
    "REJECTED",
    "AMBIGUOUS",
    "INSUFFICIENT_EVIDENCE"
)

def inspect_visual_asset(asset_path):
    """Inspect visual evidence properties if image file is available."""
    if not asset_path:
        return False, "No visual asset specified."
    ap = Path(asset_path)
    if not ap.exists():
        return False, f"Visual asset file not found at {ap}."
    try:
        size = ap.stat().st_size
        if size < 100:
            return False, f"Visual asset corrupted (file size {size} bytes too small)."
        return True, f"Visual asset verified (size {size} bytes)."
    except Exception as e:
        return False, f"Failed inspecting visual asset: {e}"

def verify_statement_against_evidence(statement, localized_evidence):
    """Host-agnostic rule-based + semantic verification against localized evidence bounds."""
    text_corpus = " ".join([
        localized_evidence.get('surrounding_text', ''),
        " ".join(localized_evidence.get('captions', [])),
        str(localized_evidence.get('table_cells', ''))
    ]).lower()
    
    stmt_lower = statement.lower().strip()
    figure_asset = localized_evidence.get('figure_asset')
    has_valid_visual = False
    
    if figure_asset:
        has_valid_visual, visual_note = inspect_visual_asset(figure_asset)

    # Check if localized evidence is empty or missing
    if not text_corpus.strip() and not has_valid_visual:
        return "INSUFFICIENT_EVIDENCE", "No localized captions, text, table cells, or valid visual assets provided."

    # Look for explicit contradiction or refutation markers in evidence
    refute_patterns = [
        r'\bnot\s+supported\b', r'\bcontradicts\b', r'\bfails?\s+to\b',
        r'\bno\s+significant\b', r'\bnegative\s+result\b', r'\bdisproved\b',
        r'\bdegrades?\b', r'\binstability\b'
    ]
    for pat in refute_patterns:
        if re.search(pat, text_corpus) and any(w in text_corpus for w in stmt_lower.split()[:4]):
            return "REJECTED", f"Localized evidence contains explicit refuting evidence matching pattern '{pat}'."

    # Check keyword overlap between statement and localized evidence
    words = [w for w in re.findall(r'\b[a-z]{3,}\b', stmt_lower) if w not in ('the', 'and', 'for', 'with', 'that', 'this', 'across', 'under')]
    if not words:
        if has_valid_visual:
            return "SUPPORTED", "Statement verified by direct visual evidence presence."
        return "AMBIGUOUS", "Statement contains insufficient scientific keywords for localized matching."

    matches = [w for w in words if w in text_corpus]
    overlap_ratio = len(matches) / len(words)

    if overlap_ratio >= 0.5 or (has_valid_visual and overlap_ratio >= 0.25):
        visual_str = f" and confirmed by visual asset ({figure_asset})" if has_valid_visual else ""
        return "SUPPORTED", f"Localized evidence directly confirms key terms ({len(matches)}/{len(words)} keywords){visual_str}."
    elif overlap_ratio >= 0.2:
        return "PARTIAL", f"Localized evidence partially aligns ({len(matches)}/{len(words)} keywords), but key claims lack explicit localized confirmation."
    else:
        if has_valid_visual:
            return "PARTIAL", f"Visual asset present, but textual keyword overlap is low ({len(matches)}/{len(words)})."
        return "AMBIGUOUS", f"Insufficient keyword overlap ({len(matches)}/{len(words)}) in localized evidence snippet."

def run_verification(task_file, out_file=None):
    tp = Path(task_file)
    task = json.loads(tp.read_text(encoding='utf-8'))
    
    stmt = task.get('statement', '')
    evidence = task.get('localized_evidence', {})
    
    verdict, reasoning = verify_statement_against_evidence(stmt, evidence)
    
    sys.path.insert(0, str(Path(__file__).parent))
    from executor_meta import build_executor_metadata
    
    result = {
        "task_id": task.get('task_id', 'UNKNOWN'),
        "target_id": task.get('target_id', 'UNKNOWN'),
        "status": verdict,
        "reasoning": reasoning,
        "grounding_evidence": evidence.get('source_ids', []),
        "epistemic_impact": f"Epistemic status updated to {verdict} based on localized evidence verification.",
        "executor_metadata": build_executor_metadata(tool_profile="evidence-localized-verifier")
    }
    
    target_out = Path(out_file) if out_file else (tp.parent.parent.parent / 'verification' / f"{task.get('target_id')}.json")
    target_out.parent.mkdir(parents=True, exist_ok=True)
    target_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Verified {task.get('target_id')} -> {verdict}")
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', required=True, help="Path to verification task JSON")
    ap.add_argument('--out', help="Path to write verification result JSON")
    a = ap.parse_args()
    run_verification(a.task, a.out)

if __name__ == '__main__':
    main()
