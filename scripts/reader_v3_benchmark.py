#!/usr/bin/env python3
"""Create real Direct-AI vs Reader-v3 benchmark tasks.

This module does not simulate a baseline. It creates host-neutral tasks that must
be executed by a real strong model against the real paper and then evaluated.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from validate_common import load_json, sha256
from task_protocol import validate_and_write_task
from executor_meta import build_executor_metadata


def _paper_id(root: Path):
    pm=root/"model/paper_model.json"
    if pm.exists():
        return str(load_json(pm).get("paper_id") or root.name)
    return root.name


def create_direct_task(root: Path) -> Path:
    root=Path(root); pdf=root/"source/paper.pdf"
    pid=_paper_id(root); safe=re.sub(r"[^A-Za-z0-9_.-]+","_",pid)
    task={
      "task_id":f"TASK-V3-DIRECT-{safe.upper()}",
      "task_type":"DIRECT_READING_BASELINE",
      "required_capability":"DEEP_SCIENTIFIC_READING",
      "scientific_contract":"Read the real paper directly with no Evidentia intermediate artifacts. Produce the strongest fair deep-reading baseline.",
      "description":"Real direct strong-model paper-reading baseline.",
      "input_artifacts":{"source_pdf":"source/paper.pdf"},
      "target_output":f"evals/reader_v3/{safe}/direct_ai.json",
      "output_schema":"direct_reading_baseline",
      "source_sha256":sha256(pdf),"base_sha256":None,
      "contract_version":"3.0","prompt_version":"3.0",
      "allowed_inputs":["source/paper.pdf"],"forbidden_inputs":["model/","lens/","lens_v3/","reader/","apply/","project/","memory/"],
      "prohibited_context":["Evidentia intermediate artifacts","PROJECT_APPLY","RESEARCH_MEMORY"],
      "constraints":["REAL_MODEL_BASELINE","NO_EVIDENTIA_CONTEXT"],
      "instructions":(
        "Read this paper directly and produce the best deep-reading report you can for a researcher. "
        "Explain the problem/gap, method/study design, decisive evidence and experiments, major findings, "
        "what the evidence does and does not establish, limitations and unresolved questions. "
        "Use coherent Chinese-first narrative. Do not assume or reference any Evidentia output."
      ),
      "executor_template":build_executor_metadata()
    }
    return validate_and_write_task(task,root/f"tasks/v3/benchmark/{safe}/direct_ai.json")


def create_evaluation_task(root: Path) -> Path:
    root=Path(root); pid=_paper_id(root); safe=re.sub(r"[^A-Za-z0-9_.-]+","_",pid)
    direct=root/f"evals/reader_v3/{safe}/direct_ai.json"
    v3=root/"reader/narrative_manuscript.json"
    if not direct.exists() or not v3.exists():
        raise FileNotFoundError("Both real Direct-AI baseline and Reader v3 manuscript are required")
    task={
      "task_id":f"TASK-V3-EVAL-{safe.upper()}",
      "task_type":"READER_EVALUATION",
      "required_capability":"SCIENTIFIC_READER_EVALUATION",
      "scientific_contract":"Compare the two real reading outputs dimension-by-dimension without collapsing them to one synthetic score.",
      "description":"Real Direct-AI vs Evidentia Reader v3 evaluation.",
      "input_artifacts":{
        "source_pdf":"source/paper.pdf",
        "direct_ai":f"evals/reader_v3/{safe}/direct_ai.json",
        "evidentia_v3":"reader/narrative_manuscript.json"
      },
      "target_output":f"evals/reader_v3/{safe}/pair_evaluation.json",
      "output_schema":"reader_pair_evaluation",
      "source_sha256":sha256(root/"source/paper.pdf"),
      "base_sha256":None,"contract_version":"3.0","prompt_version":"3.0",
      "allowed_inputs":["source/paper.pdf",f"evals/reader_v3/{safe}/direct_ai.json","reader/narrative_manuscript.json"],
      "forbidden_inputs":["apply/","project/","memory/"],
      "constraints":["DIMENSION_LEVEL_EVALUATION","NO_SINGLE_OVERALL_SCORE","SOURCE_ASSISTED"],
      "instructions":(
        "Evaluate Direct AI and Evidentia v3 against the source paper. Score each requested dimension 1-5 and provide a concrete evidence note. "
        "Do not choose a single winner or collapse all dimensions into one score. Explicitly identify release blockers. "
        "Narrative clarity, scientific completeness and method explanation are non-regression dimensions; "
        "evidence grounding, visual interpretation, critique, uncertainty and provenance are intended Evidentia value-add dimensions."
      ),
      "executor_template":build_executor_metadata()
    }
    return validate_and_write_task(task,root/f"tasks/v3/benchmark/{safe}/evaluate.json")


def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    for name in ("direct","evaluate"):
        p=sub.add_parser(name);p.add_argument("--out",required=True)
    args=ap.parse_args();root=Path(args.out)
    p=create_direct_task(root) if args.cmd=="direct" else create_evaluation_task(root)
    print(p)


if __name__=="__main__":
    main()
