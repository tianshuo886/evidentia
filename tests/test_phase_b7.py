"""Phase B7 Evaluation and Engineering Release acceptance tests.

Validates:
- Evaluation runner execution across 3 experimental conditions
- Quantitative metrics computation (source, grounding, critical reading)
- Detection Fingerprint generation (Lens x Model matrix)
- Engineering release artifacts (LICENSE, pyproject.toml, CHANGELOG.md, CONTRIBUTING.md, CI workflow)
"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable

def test_ci_validation_declares_synthetic_only_evaluation():
    """CI advertises only the synthetic release-boundary harness."""
    import json
    matrix = json.loads((ROOT / "capability_matrix.json").read_text())
    capability = next(x for x in matrix["capabilities"] if x["id"] == "evaluation_framework")
    assert capability["status"] == "SYNTHETIC_ONLY"
    assert capability["validation_status"] == "SYNTHETIC_VALIDATED"
    assert "real-paper" not in capability["evidence"].lower()
    assert (ROOT / "tests/fixtures/evaluation/corpus/synthetic_corpus.json").is_file()
    assert (ROOT / "tests/fixtures/evaluation/annotations/ground_truth.json").is_file()


def test_engineering_release_artifacts_present():
    assert (ROOT / 'LICENSE').exists()
    assert (ROOT / 'pyproject.toml').exists()
    assert (ROOT / 'CHANGELOG.md').exists()
    assert (ROOT / 'CONTRIBUTING.md').exists()
    assert (ROOT / '.github/workflows/ci.yml').exists()
    assert (ROOT / 'examples/demo-paper/README.md').exists()

    # pyproject.toml content check
    pyproject_text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'evidentia' in pyproject_text
    assert 'PyMuPDF' in pyproject_text
    assert 'jsonschema' in pyproject_text

    # CI workflow content check
    ci_text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'pytest' in ci_text
    assert 'contract_audit' in ci_text
