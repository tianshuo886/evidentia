#!/usr/bin/env python3
"""SYNTHETIC UNIT-TEST FIXTURE — NOT an empirical Direct-AI benchmark.

This module simulates the shape of a direct-reading baseline for deterministic
tests only. It MUST NOT be used to claim that Evidentia matches or outperforms a
real strong model reading a real PDF. Reader v3 empirical comparisons are created
by scripts/reader_v3_benchmark.py.

Historically this fixture simulated giving a paper PDF directly to a strong model,
which outputs a single-pass reading report with Kami-styled presentation.

Characteristics:
- Highly readable and fluent narrative
- BUT lacks:
  * Fine-grained multimodal bounding box localization & cropped assets
  * Bidirectional claim <-> visual evidence provenance
  * Explicit 6-lens independent cross-examination
  * Systematic anomaly isolation & counterfactual conflict preservation
  * Fail-closed verification gates
  * Immutable hash-frozen state
"""
import json
from pathlib import Path

def run_direct_ai_baseline(paper_doc):
    title = paper_doc.get('title', 'Research Paper')
    sections = paper_doc.get('sections', [])
    
    # Fluent, well-structured single-pass summary typical of GPT-4o / Claude 3.5 Sonnet + Kami
    report_zh = f"""# {title} — 深度精读（Direct AI + Kami）

## 核心观点与总结
本文针对领域痛点提出了一种新颖的方法架构，在标准数据集上取得了领先的表现。

## 方法与机制
通过引入端到端流转设计，有效提升了特征提取的表达能力与表征一致性。

## 实验与结果
在主要基准评估中，所提方案在准确率与效率上均优于传统基线。

## 局限与思考
方法在实际落地时可能受到特定超参数与数据质量的制约。
"""
    
    claims = [
        {
            "id": "DAI-C01",
            "statement": f"{title} 提出了高效的端到端学习模型并在基准上取得最优性能。",
            "observation": "论文报道在基准测试中超越了对照方法。",
            "evidence": ["p.1"],
            "epistemic": "SUPPORTED"
        },
        {
            "id": "DAI-C02",
            "statement": "所提机制能够有效降低计算冗余并加速收敛。",
            "observation": "模型参数与收敛曲线表现出平稳特性。",
            "evidence": ["F01"],
            "epistemic": "SUPPORTED"
        }
    ]
    
    # Missing explicit anomaly detection and alternative explanations (known single-pass weakness)
    return {
        "condition": "Condition_A_Direct_AI_Kami",
        "title": title,
        "report_zh": report_zh,
        "claims": claims,
        "findings": [
            {"id": "DAI-F01", "statement": "所提架构性能优良，具有较好的泛化潜力。"}
        ],
        "multimodal_evidence_reconstructed": False,
        "has_provenance_graph": False,
        "independent_lenses_count": 1,
        "contradictions_preserved": 0,
        "anomalies_isolated": 0,
        "frozen_sha_lock": False
    }

if __name__ == '__main__':
    doc = {"title": "Test Paper", "sections": ["Intro", "Method", "Eval"]}
    res = run_direct_ai_baseline(doc)
    print(json.dumps(res, indent=2, ensure_ascii=False))
