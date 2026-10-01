"""Council boundary tests for Issue #14."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_gates import fixture
from lens_council import (build_frozen_evidence_package, snapshot_round1,
                          select_cross_examination_requests, write_council_artifact)
from merge_lenses import run_merge
from scientific_synthesis_agent import run_scientific_synthesis
from narrative_composer_agent import compose_narrative_manuscript
from validate_common import schema_validate, sha256


def test_shared_frozen_package_and_independent_round1(tmp_path):
    root = fixture(tmp_path)
    package = build_frozen_evidence_package(root)
    records = snapshot_round1(root)
    assert package['frozen'] is True
    assert len(records) == 6
    assert all(r['sha256'] == sha256(root / r['artifact']) for r in records)
    assert json.loads((root / 'council/round1/manifest.json').read_text())['independent'] is True


def test_council_preserves_unresolved_and_has_no_vote_field(tmp_path):
    root = fixture(tmp_path)
    build_frozen_evidence_package(root)
    council = write_council_artifact(root, {'items': [{
        'id': 'R-1', 'statement': 'cannot decide', 'status': 'UNRESOLVED',
        'supporting_lenses': ['author', 'reviewer'], 'evidence': ['F01']
    }]})
    assert council['no_majority_voting'] is True
    assert council['unresolved'][0]['status'] == 'UNRESOLVED'
    assert not schema_validate(council, 'lens_council')


def test_cross_examination_is_selective_and_bounded():
    requests = [{'target_item_id': str(i), 'question': 'q'} for i in range(10)]
    selected = select_cross_examination_requests({'cross_examination_requests': requests})
    assert len(selected) == 3
    assert {r['target_item_id'] for r in selected} == {'0', '1', '2'}


def test_synthesis_and_narrative_do_not_reopen_round1(tmp_path):
    root = fixture(tmp_path)
    run_merge(root, fixture=True)
    run_scientific_synthesis(root, fixture=True)
    for lens in ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual'):
        (root / 'lens' / f'{lens}.json').write_text('not-json')
    synthesis = json.loads((root / 'model/scientific_synthesis.json').read_text())
    assert synthesis['council_id']
    manuscript = compose_narrative_manuscript(root)
    assert manuscript['document']['title']
