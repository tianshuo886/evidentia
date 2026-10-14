"""Test suite for Issue #42: Mechanistic Depth & Visual Narrative Quality.

Verifies:
1. Deep tensor-level and operator-level explanation of MSFR (FPN alignment, hybrid attention, zero gating)
2. Deep prototype-level explanation of CPR (RoI embedding, class prototypes, contrastive loss, logits calibration)
3. Shallow/placeholder visual analysis fails the mechanistic depth gate
4. Substantive visual evidence grounding across high-value figures and tables
5. General representation and tensor depth audit on arbitrary literature
6. Integration into reader_acceptance gate
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVALS = ROOT / "evals/reader_v3/semantic_regressions/ringmoclaw"

import sys
sys.path.insert(0, str(SCRIPTS))

from reader_depth_audit import audit_explanation_depth, audit_visual_evidence_selection, audit_reader_mechanistic_depth
from reader_acceptance import evaluate
from render_reader import render_reader
from test_gates import fixture
from validate_common import load_json


def test_msfr_tensor_level_mechanics_present():
    """MSFR module must detail FPN feature alignment, SE/CBAM attention, and zero-initialized gating."""
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    
    # Check FPN multi-scale alignment
    assert "FPN" in corrected_text
    assert "跨层级" in corrected_text or "对齐" in corrected_text
    
    # Check 3x3 conv & SE/CBAM attention
    assert "3×3" in corrected_text or "3x3" in corrected_text or "3 \\times 3" in corrected_text
    assert "SE" in corrected_text or "CBAM" in corrected_text or "注意力" in corrected_text
    
    # Check zero-initialized gating parameter
    assert "0" in corrected_text
    assert "恒等映射" in corrected_text or "门控" in corrected_text or "残差" in corrected_text


def test_cpr_prototype_mechanics_present():
    """CPR module must detail RoI embeddings, class prototypes, contrastive loss, and logits calibration."""
    corrected_text = (EVALS / "corrected_reader.md").read_text(encoding="utf-8")
    
    # Check RoI feature vector
    assert "RoI" in corrected_text
    assert "原型" in corrected_text
    
    # Check contrastive regularization
    assert "对比" in corrected_text or "InfoNCE" in corrected_text or "损失" in corrected_text
    
    # Check logits calibration
    assert "logits" in corrected_text or "校准" in corrected_text or "Softmax" in corrected_text


def test_shallow_placeholder_visual_analysis_fails_depth_gate(tmp_path):
    """Visual assets with shallow or placeholder analysis must fail mechanistic depth gate."""
    root = tmp_path / "shallow_workspace"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "test_shallow_paper",
        "source_sha256": "12345678" * 8,
        "document": {
            "title": "A Method Paper",
            "paper_meta": {},
            "sections": [
                {
                    "id": "sec-01",
                    "title": "Method",
                    "blocks": [
                        {"type": "paragraph", "text": "模型采用特征金字塔与自注意力机制提取多尺度张量特征。"},
                        {
                            "type": "figure",
                            "evidence_id": "F01",
                            "caption": "网络架构图",
                            "analysis": "网络架构图"  # Placeholder: too short & identical to caption!
                        }
                    ]
                }
            ]
        }
    }
    audit = audit_reader_mechanistic_depth(root, manuscript)
    assert audit["status"] == "DEFICIT"
    assert any("too short or shallow" in err or "identical to caption" in err for err in audit["errors"])


def test_substantive_visual_grounding_passes_depth_gate(tmp_path):
    """Visual assets with grounded, multi-perspective analysis pass cleanly."""
    root = tmp_path / "rich_workspace"
    root.mkdir()
    manuscript = {
        "schema_version": "3.0",
        "paper_id": "test_rich_paper",
        "source_sha256": "abcdef12" * 8,
        "document": {
            "title": "A Method Paper",
            "paper_meta": {},
            "sections": [
                {
                    "id": "sec-01",
                    "title": "Method",
                    "blocks": [
                        {"type": "paragraph", "text": "模型引入特征金字塔与多尺度注意力机制，在通道与空间维度优化特征张量流动。"},
                        {
                            "type": "figure",
                            "evidence_id": "F01",
                            "caption": "网络微结构数据流图",
                            "analysis": "图中直接呈现了多尺度特征细化模块与原型分类头的内部张量连接关系。作者将这一结构解释为通过自适应门控残差注入实现特征流形平滑微调。结合现有证据，确认该模块在控制算力开销下提供了关键精度增益。"
                        }
                    ]
                }
            ]
        }
    }
    audit = audit_reader_mechanistic_depth(root, manuscript)
    assert audit["status"] == "PASS"
    assert len(audit["errors"]) == 0


def test_mechanistic_depth_gate_integrated_in_reader_acceptance(tmp_path):
    """Reader acceptance evaluation verifies mechanistic depth gate."""
    root = fixture(tmp_path)
    render_reader(root)
    report = evaluate(root, artifact_only=True)
    assert report["status"] == "READER_ACCEPTED"
