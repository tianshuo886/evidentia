"""Tests for Paper Acquire Bridge in Evidentia (DOI, arXiv, and pa CLI integration)."""
import json, pytest, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import paper_acquire_bridge

def test_identifier_syntax_detection():
    assert paper_acquire_bridge.is_doi("10.1038/s41586-021-03819-2")
    assert paper_acquire_bridge.is_doi("https://doi.org/10.1038/s41586-021-03819-2")
    assert paper_acquire_bridge.is_doi("doi:10.1145/3318464.3389700")

    assert paper_acquire_bridge.is_arxiv("1706.03762")
    assert paper_acquire_bridge.is_arxiv("https://arxiv.org/abs/1706.03762")
    assert paper_acquire_bridge.is_arxiv("arxiv:2312.12345v1")

    assert paper_acquire_bridge.extract_doi("https://doi.org/10.1038/s41586-021-03819-2") == "10.1038/s41586-021-03819-2"
    assert paper_acquire_bridge.extract_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"

def test_acquire_local_pdf(tmp_path):
    fake_pdf = tmp_path / 'sample.pdf'
    fake_pdf.write_bytes(b'%PDF-1.5 test content')

    resolved_path, meta = paper_acquire_bridge.acquire_paper(fake_pdf)
    assert resolved_path == fake_pdf
    assert meta['source_type'] == 'LOCAL_PDF'

def test_query_crossref_metadata():
    # Test real CrossRef API resolution on AlphaFold 2 DOI
    meta = paper_acquire_bridge.query_crossref("10.1038/s41586-021-03819-2")
    assert meta is not None
    assert "AlphaFold" in meta['title']
    assert meta['year'] == 2021
    assert "Nature" in meta['venue']
    assert len(meta['authors']) >= 5

def test_query_unpaywall_resolution():
    # Test Unpaywall open access resolution with retry
    res = None
    for _ in range(3):
        res = paper_acquire_bridge.query_unpaywall("10.1038/s41586-021-03819-2")
        if res:
            break
    if res is not None:
        assert res.get('is_oa') is True
        assert res.get('pdf_url') is not None
        assert res['pdf_url'].endswith('.pdf')
