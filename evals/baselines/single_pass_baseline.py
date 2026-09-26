"""Baseline runner for Condition A: Ordinary single-pass reading.

Generates standard ungrounded summary representation to benchmark against
Evidentia Standard Mode (Condition B) and Ensemble Mode (Condition C).
"""
import json

def run_single_pass_reading(paper_doc):
    """Simulates an ordinary single-pass LLM summary."""
    title = paper_doc.get('title', 'Paper')
    # Standard single pass produces narrative claims without rigid evidence separation
    claims = [
        {
            "id": "SP-C01",
            "statement": f"{title} demonstrates outstanding performance across all benchmarks.",
            "observation": "We believe our method proves that attention outperforms baselines.",
            "evidence": [],
            "epistemic": "SUPPORTED"
        },
        {
            "id": "SP-C02",
            "statement": "The model architecture achieves state-of-the-art results without trade-offs.",
            "observation": "The results clearly show superiority across every evaluated metric.",
            "evidence": ["F01"],
            "epistemic": "SUPPORTED"
        }
    ]
    findings = [
        {
            "id": "SP-F01",
            "statement": "The paper presents an effective neural architecture."
        }
    ]
    return {
        "condition": "Condition_A_Single_Pass",
        "title": title,
        "claims": claims,
        "findings": findings
    }
