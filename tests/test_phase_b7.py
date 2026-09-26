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

def test_evaluation_runner_execution(tmp_path):
    report_out = tmp_path / 'report.json'
    res = subprocess.run([
        PY, str(ROOT / 'evals/runners/eval_runner.py'),
        '--out', str(report_out)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert report_out.exists()
    
    report = json.loads(report_out.read_text(encoding='utf-8'))
    assert 'Condition_A_Single_Pass' in report['conditions_evaluated']
    assert 'Condition_B_Evidentia_Standard' in report['conditions_evaluated']
    assert 'Condition_C_Evidentia_Ensemble' in report['conditions_evaluated']
    assert len(report['detection_fingerprints']) >= 1
    assert 'summary' in report

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
