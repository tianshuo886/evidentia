import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visual_localization_protocol import create_visual_tasks
from validate_common import load_json, schema_validate


def test_visual_localization_is_semantic_verification_over_geometry_candidates(tmp_path):
    root = tmp_path / "paper"
    (root / "source").mkdir(parents=True)
    (root / "source_pages").mkdir()
    (root / "model").mkdir()
    (root / "source/paper.pdf").write_bytes(b"%PDF-1.4\nvisual-v3-test\n%%EOF\n")
    (root / "source_pages/page-001.png").write_bytes(b"not-a-real-png-needed-for-task-generation")
    (root / "model/figure_inventory.json").write_text(json.dumps({
        "items": [{
            "id": "F01",
            "kind": "figure",
            "page": 1,
            "paper_label": "Fig. 1",
            "caption_original": "A multi-panel scientific figure.",
            "figure_bbox": [10, 20, 300, 400],
            "file": "assets/figures/candidate.png",
            "localization_method": "MULTIMODAL_PAGE_LOCALIZATION",
            "localization_confidence": 0.61
        }]
    }))

    tasks = create_visual_tasks(root)
    assert len(tasks) == 1
    task = load_json(tasks[0])
    assert task["task_type"] == "VISUAL_LOCALIZATION"
    assert task["required_capability"] == "VISUAL_EVIDENCE_LOCALIZATION"
    assert "FULL_PAGE_SEMANTIC_LOCALIZATION" in task["constraints"]
    assert "NO_WHOLE_PAGE_FALLBACK" in task["constraints"]
    assert task["input_artifacts"]["candidates"][0]["candidate_bbox_pdf"] == [10, 20, 300, 400]
    assert "RESEARCH_MEMORY" in task["prohibited_context"]
    assert not schema_validate(task, "agent_task")
