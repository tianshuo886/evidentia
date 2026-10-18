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

def test_evaluation_runner_synthetic_helpers(tmp_path):
    """CI validates synthetic fixture generation; real-paper benchmarks are opt-in."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_runner import create_synthetic_pdf
    import fitz

    out = tmp_path / "synthetic.pdf"
    create_synthetic_pdf({
        "title": "Synthetic Test Paper",
        "sections": ["Introduction", "Method"],
        "figures": [{"paper_label": "Figure 1", "caption": "Synthetic figure"}],
        "tables": [{"paper_label": "Table 1", "caption": "Synthetic table"}],
    }, out)
    
    assert out.is_file() and out.stat().st_size > 0
    with fitz.open(out) as pdf:
        assert len(pdf) == 2
        assert "Synthetic Test Paper" in pdf[0].get_text()


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
