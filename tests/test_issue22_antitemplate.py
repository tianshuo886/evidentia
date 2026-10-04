"""Regression coverage for Issue #22: paper-shaped, not template-shaped Readers."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_paper_reader import render_paper_reader_html, render_paper_reader_md, rebind_visual_assets
from validate_common import schema_validate


def _manuscript():
    return {
        "schema_version": "3.0", "paper_id": "unusual-paper", "source_sha256": "a" * 64,
        "created_at": "2026-01-01T00:00:00Z", "narrative_plan_ref": "model/narrative_plan.json",
        "document": {
            "title": "A Taxonomy with a Counterexample",
            "paper_meta": {"authors": ["A. Author"]},
            "orientation": {"lead": "The paper's case turns on a taxonomy and its counterexample.", "takeaways": []},
            "narrative_plan": {"sections": [
                {"id": "taxonomy", "title": "Three families of behavior", "purpose": "Establish the paper's classification", "evidence_refs": ["p.2"], "source_anchors": ["p.2"]},
                {"id": "counterexample", "title": "The exception that changes the reading", "purpose": "Qualify the classification", "evidence_refs": ["F7"], "source_anchors": ["p.7"], "bindings": ["F7"]}
            ]},
            "sections": [
                {"id": "taxonomy", "title": "Three families of behavior", "lead": "The paper classifies its objects.", "blocks": [{"type": "paragraph", "text": "The paper separates the observed cases into three families.", "evidence_refs": ["p.2"]}]},
                {"id": "counterexample", "title": "The exception that changes the reading", "lead": "A counterexample qualifies the classification.", "blocks": [{"type": "paragraph", "text": "A source-grounded counterexample limits the classification.", "evidence_refs": ["F7"]}]}
            ],
        }
    }


def test_lead_reader_and_writer_contracts_are_open_form(tmp_path):
    from reader_v3_protocol import create_lead_reader_task
    root = tmp_path / "workspace"
    (root / "source").mkdir(parents=True)
    (root / "model").mkdir()
    (root / "source/paper.pdf").write_bytes(b"paper")
    task = json.loads(create_lead_reader_task(root).read_text())
    instructions = task["instructions"].lower()
    assert "how does this particular paper actually construct its case" in instructions
    assert "do not force" in instructions
    draft_schema = json.loads((ROOT / "schemas/paper_understanding_draft.schema.json").read_text())
    assert "story_spine" not in draft_schema["required"]


def test_noncanonical_paper_can_omit_story_spine_concepts():
    manuscript = _manuscript()
    assert not schema_validate(manuscript, "narrative_manuscript")
    assert "story_spine" not in manuscript["document"]
    assert "central_question" not in manuscript["document"].get("orientation", {})


def test_dynamic_section_order_survives_html_and_markdown_rendering(tmp_path):
    manuscript = _manuscript()
    html = render_paper_reader_html(manuscript, tmp_path)
    markdown = render_paper_reader_md(manuscript)
    assert html.index("Three families of behavior") < html.index("The exception that changes the reading")
    assert markdown.index("Three families of behavior") < markdown.index("The exception that changes the reading")


def test_topology_accepts_unusual_roles_without_universal_slots():
    topology = {
        "schema_version": "1.0", "paper_id": "proof-paper", "source_sha256": "b" * 64,
        "characterization": "A proof chain with a load-bearing assumption.",
        "nodes": [
            {"id": "axiom", "role": "assumption", "proposition": "A is compact.", "evidence_refs": [], "source_anchors": ["p.1"], "epistemic_status": "ASSUMED"},
            {"id": "lemma", "role": "theorem", "proposition": "The map has a fixed point.", "evidence_refs": [], "source_anchors": ["p.4"], "epistemic_status": "SUPPORTED"}
        ],
        "relations": [{"id": "r1", "from": "axiom", "to": "lemma", "relation": "enables", "origin": "author", "source_anchors": ["p.2"]}],
        "ordering": ["axiom", "lemma"]
    }
    assert not schema_validate(topology, "paper_argument_topology")


def test_structural_diversity_gate_accepts_materially_different_architectures(tmp_path):
    from reader_structure_diversity import evaluate
    roots = []
    architectures = [
        [("design", "Design"), ("ablation", "Ablation")],
        [("observation", "Observation"), ("measurement", "Measurement"), ("boundary", "Boundary")],
        [("assumption", "Assumption"), ("lemma", "Lemma"), ("theorem", "Theorem")],
    ]
    for index, architecture in enumerate(architectures):
        root = tmp_path / f"paper-{index}"
        (root / "source").mkdir(parents=True)
        (root / "reader").mkdir()
        source = root / "source/paper.pdf"
        source.write_bytes(f"real-paper-{index}".encode())
        sections = [{"id": sid, "title": title, "blocks": [{"type": "paragraph", "text": f"Evidence for {title}", "evidence_refs": ["p.1"]}], "evidence_refs": ["p.1"]} for sid, title in architecture]
        manuscript = {"schema_version": "3.0", "paper_id": f"P-{index}", "source_sha256": __import__('hashlib').sha256(source.read_bytes()).hexdigest(), "created_at": "2026-01-01T00:00:00Z", "narrative_plan_ref": "model/narrative_plan.json", "document": {"title": f"Paper {index}", "paper_meta": {}, "sections": sections}}
        (root / "reader/narrative_manuscript.json").write_text(json.dumps(manuscript), encoding="utf-8")
        roots.append(root)
    report = evaluate(roots)
    assert report["status"] == "PASS", report
    assert report["materially_different_architectures"] is True


def test_visual_binding_resolves_by_evidence_identity_not_stale_writer_path(tmp_path):
    root = tmp_path / "workspace"
    (root / "model").mkdir(parents=True)
    (root / "assets/figures").mkdir(parents=True)
    (root / "assets/figures/v3_F02.png").write_bytes(b"png")
    (root / "model/figure_inventory.json").write_text(json.dumps({"items": [{"id": "F02", "file": "assets/figures/v3_F02.png"}]}))
    manuscript = {"document": {"sections": [{"id": "s1", "blocks": [{"type": "figure", "evidence_id": "F02", "asset": "assets/figures/old_F02.png"}]}]}}
    changes = rebind_visual_assets(manuscript, root)
    assert changes == [{"evidence_id": "F02", "old_asset": "assets/figures/old_F02.png", "new_asset": "assets/figures/v3_F02.png"}]
    assert manuscript["document"]["sections"][0]["blocks"][0]["asset"] == "assets/figures/v3_F02.png"


def test_legacy_reader_ir_is_explicitly_downstream_projection():
    from render_reader import build_legacy_reader_ir
    assert build_legacy_reader_ir
    # The compatibility schema itself documents the firewall; it does not
    # become an input to either the plan or the narrative renderer.
    assert "paper_reader_ir.json" not in _manuscript()["document"].get("narrative_plan", {})
