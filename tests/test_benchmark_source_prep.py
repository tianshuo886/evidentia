"""Source-preparation boundaries; no scientific Reader/model execution."""
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reader_v3_corpus import _write_benchmark_manifest


def test_registry_identity_mismatch_refuses_substitution(tmp_path):
    paper = {'id': 'TEST', 'title': 'Registered paper', 'open_access_doi': '10.1234/original'}
    with pytest.raises(ValueError, match='owner approval required'):
        _write_benchmark_manifest(tmp_path, paper, tmp_path / 'missing.pdf', {
            'identifier': '10.1234/different', 'source_url': 'https://example.org/other.pdf'
        })
    assert not (tmp_path / 'model/benchmark_manifest.json').exists()


def test_source_hash_lock_refuses_mutation(tmp_path):
    (tmp_path / 'source').mkdir()
    (tmp_path / 'model').mkdir()
    pdf = tmp_path / 'source/paper.pdf'
    pdf.write_bytes(b'first immutable source')
    paper = {'id': 'TEST', 'title': 'Registered paper', 'authors': ['A. Author'], 'open_access_doi': '10.1234/original'}
    acquisition = {'identifier': '10.1234/original', 'source_url': 'https://example.org/original.pdf'}
    manifest = _write_benchmark_manifest(tmp_path, paper, pdf, acquisition)
    assert manifest['current_benchmark_contract']['allowed_inputs'] == ['source/paper.pdf']
    original_lock = (tmp_path / 'source/source_sha256.txt').read_bytes()
    pdf.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='Immutable source SHA changed'):
        _write_benchmark_manifest(tmp_path, paper, pdf, acquisition)
    assert (tmp_path / 'source/source_sha256.txt').read_bytes() == original_lock
