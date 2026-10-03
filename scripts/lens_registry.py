#!/usr/bin/env python3
"""Reader v3 Lens registry.

Lens diversity comes from questions, not models. Four core lenses are universal;
two specialist lenses are selected from paper type/content. Anomaly detection and
counterfactual reasoning are cross-cutting checks embedded in every relevant lens.
"""
from __future__ import annotations
from typing import Dict, List

CORE_LENSES = [
    {
        "id": "argument_narrative",
        "kind": "core",
        "title": "Argument & Narrative",
        "capability": "SCIENTIFIC_ARGUMENT_RECONSTRUCTION",
        "questions": [
            "What scientific problem is the paper trying to solve and why does it matter?",
            "What limitation or gap in prior work motivates the paper?",
            "What is the central design move or proposition?",
            "How does the argument progress from problem to method to evidence to conclusion?",
            "What role does each decisive experiment play in that argument?"
        ],
        "forbidden": ["project transfer", "implementation advice unrelated to faithful reading"]
    },
    {
        "id": "method_study_design",
        "kind": "core",
        "title": "Method & Study Design",
        "capability": "SCIENTIFIC_METHOD_READING",
        "questions": [
            "What did the authors actually do, in operational order?",
            "Why does each method/study component exist?",
            "What assumptions, controls, variables, training choices, measurements or proof steps matter?",
            "Which design choices are necessary to interpret the results correctly?"
        ],
        "forbidden": ["project transfer"]
    },
    {
        "id": "evidence_results",
        "kind": "core",
        "title": "Evidence & Results",
        "capability": "SCIENTIFIC_EVIDENCE_READING",
        "questions": [
            "What does each decisive figure/table/experiment directly show?",
            "Which claim does each result support?",
            "What is the magnitude/direction of the result where the source states it?",
            "What does the evidence not establish?",
            "Are there anomalous or off-trend observations that matter?"
        ],
        "forbidden": ["invented numerical values", "project transfer"]
    },
    {
        "id": "validity_boundary",
        "kind": "core",
        "title": "Validity & Boundary",
        "capability": "SCIENTIFIC_VALIDITY_REVIEW",
        "questions": [
            "Are controls, baselines, comparisons and evaluation protocols adequate?",
            "Are there confounds, leakage, causal overclaims or unsupported generalizations?",
            "What alternative explanation could fit the same evidence?",
            "Under what tested conditions does the conclusion hold, and what remains untested?"
        ],
        "forbidden": ["project transfer"]
    }
]

SPECIALISTS: Dict[str, dict] = {
    "mechanism_causality": {
        "id": "mechanism_causality", "kind": "specialist",
        "title": "Mechanism & Causality",
        "capability": "SCIENTIFIC_MECHANISM_ANALYSIS",
        "questions": [
            "What mechanism is claimed to produce the observed result?",
            "Which evidence identifies that mechanism rather than correlation?",
            "What observation would falsify the proposed mechanism?",
            "What competing mechanism remains plausible?"
        ],
        "forbidden": ["project transfer"]
    },
    "reproducibility_implementation": {
        "id": "reproducibility_implementation", "kind": "specialist",
        "title": "Reproducibility & Implementation",
        "capability": "SCIENTIFIC_REPRODUCIBILITY_REVIEW",
        "questions": [
            "Could an independent researcher reproduce the study from the paper?",
            "Which preprocessing, hyperparameters, protocols, data or implementation details are explicit?",
            "Which missing details could materially change the result?"
        ],
        "forbidden": ["project transfer", "recommendations for the user's project"]
    },
    "proof_integrity": {
        "id": "proof_integrity", "kind": "specialist",
        "title": "Proof Integrity",
        "capability": "FORMAL_PROOF_REVIEW",
        "questions": [
            "What are the theorem dependencies and proof-critical steps?",
            "Where are assumptions introduced?",
            "Do intermediate lemmas actually imply the stated conclusion?"
        ],
        "forbidden": ["project transfer"]
    },
    "assumption_sensitivity": {
        "id": "assumption_sensitivity", "kind": "specialist",
        "title": "Assumption Sensitivity",
        "capability": "SCIENTIFIC_ASSUMPTION_REVIEW",
        "questions": [
            "Which assumptions are load-bearing?",
            "Which conclusions fail or weaken if an assumption changes?",
            "Which assumptions are tested versus merely asserted?"
        ],
        "forbidden": ["project transfer"]
    },
    "measurement_integrity": {
        "id": "measurement_integrity", "kind": "specialist",
        "title": "Measurement Integrity",
        "capability": "SCIENTIFIC_MEASUREMENT_REVIEW",
        "questions": [
            "How are the key variables measured or operationalized?",
            "What calibration, instrument, sampling or preprocessing choices affect validity?",
            "Could measurement artifacts explain part of the result?"
        ],
        "forbidden": ["project transfer"]
    },
    "statistical_causal_inference": {
        "id": "statistical_causal_inference", "kind": "specialist",
        "title": "Statistical & Causal Inference",
        "capability": "STATISTICAL_CAUSAL_REVIEW",
        "questions": [
            "Does the statistical analysis match the study design?",
            "Are uncertainty, multiple comparisons, effect size and identification handled appropriately?",
            "Which claims are associational versus causal?"
        ],
        "forbidden": ["project transfer"]
    },
    "taxonomy_coverage": {
        "id": "taxonomy_coverage", "kind": "specialist",
        "title": "Taxonomy & Coverage",
        "capability": "REVIEW_COVERAGE_ANALYSIS",
        "questions": [
            "Is the taxonomy internally coherent and sufficiently complete?",
            "How were included studies/systems selected?",
            "What selection or coverage bias could distort the synthesis?"
        ],
        "forbidden": ["project transfer"]
    }
}

TYPE_TO_SPECIALISTS = {
    "theory": ("proof_integrity", "assumption_sensitivity"),
    "mathematical": ("proof_integrity", "assumption_sensitivity"),
    "experimental": ("measurement_integrity", "mechanism_causality"),
    "measurement": ("measurement_integrity", "mechanism_causality"),
    "clinical": ("statistical_causal_inference", "measurement_integrity"),
    "observational": ("statistical_causal_inference", "measurement_integrity"),
    "review": ("taxonomy_coverage", "assumption_sensitivity"),
    "survey": ("taxonomy_coverage", "assumption_sensitivity"),
    "method": ("mechanism_causality", "reproducibility_implementation"),
    "machine_learning": ("mechanism_causality", "reproducibility_implementation"),
    "remote_sensing": ("mechanism_causality", "reproducibility_implementation"),
}

def _normalize_paper_type(value: str) -> str:
    value = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ml": "machine_learning", "machinelearning": "machine_learning",
        "empirical": "experimental", "experiment": "experimental",
        "review_article": "review", "systematic_review": "review",
        "theoretical": "theory", "theorem": "theory",
    }
    return aliases.get(value, value)

def select_lenses(paper_type: str, narrative: str = "") -> List[dict]:
    """Return four universal core lenses plus two paper-appropriate specialists."""
    ptype = _normalize_paper_type(paper_type)
    specialists = list(TYPE_TO_SPECIALISTS.get(ptype, ()))
    text = (narrative or "").lower()

    # Content signals only fill missing specialist slots; they never remove the
    # four universal core lenses.
    if len(specialists) < 2:
        if any(k in text for k in ("theorem", "lemma", "proof", "证明", "定理")):
            specialists.extend(["proof_integrity", "assumption_sensitivity"])
        elif any(k in text for k in ("instrument", "sensor", "measurement", "calibration", "测量", "传感器")):
            specialists.extend(["measurement_integrity", "mechanism_causality"])
        elif any(k in text for k in ("cohort", "odds ratio", "hazard", "causal", "randomized", "临床")):
            specialists.extend(["statistical_causal_inference", "measurement_integrity"])
        elif any(k in text for k in ("survey", "review", "taxonomy", "综述", "分类体系")):
            specialists.extend(["taxonomy_coverage", "assumption_sensitivity"])
        else:
            specialists.extend(["mechanism_causality", "reproducibility_implementation"])

    chosen = []
    for sid in specialists:
        if sid not in chosen and sid in SPECIALISTS:
            chosen.append(sid)
        if len(chosen) == 2:
            break
    return CORE_LENSES + [SPECIALISTS[x] for x in chosen]

if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-type", default="method")
    ap.add_argument("--narrative", default="")
    args = ap.parse_args()
    print(json.dumps(select_lenses(args.paper_type, args.narrative), indent=2, ensure_ascii=False))
