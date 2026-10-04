#!/usr/bin/env python3
"""Paper Acquire Bridge for Evidentia v1.1.1.

Seamlessly bridges Evidentia with Paper Acquire (pa CLI), ArXiv, Unpaywall, and CrossRef:
- Auto-detects DOIs (e.g. 10.1038/..., https://doi.org/...)
- Auto-detects ArXiv IDs and URLs (e.g. 1706.03762, https://arxiv.org/abs/...)
- Auto-detects direct PDF URLs
- Fetches full metadata (title, authors, venue, year, abstract) via CrossRef & Unpaywall
- Integrates with local `pa` CLI when available to synchronize local paper library & overview markdown
- Downloads open-access source PDF directly into workspace source/paper.pdf
- If publisher PDF is strictly paywalled, synthesizes structured source PDF from acquired text/abstract
"""
import json, os, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

USER_AGENT = 'Evidentia/1.1 (https://github.com/tianshuo886/evidentia; mailto:evidentia@evidentia.dev)'

def is_doi(s):
    s = s.strip()
    return bool(re.match(r'^(https?://(dx\.)?doi\.org/|doi:)?10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+$', s, re.I))

def is_arxiv(s):
    s = s.strip()
    # arXiv's DOI form (10.48550/arXiv.<id>) must resolve through the
    # canonical arXiv PDF endpoint, not Crossref/Unpaywall metadata fallback.
    return (
        bool(re.match(r'^(https?://arxiv\.org/(abs|pdf)/)?([0-9]{4}\.[0-9]{4,5}(v[0-9]+)?)$', s, re.I))
        or bool(re.match(r'^arxiv:[0-9]{4}\.[0-9]{4,5}', s, re.I))
        or bool(re.match(r'^(?:https?://(dx\.)?doi\.org/)?10\.48550/arxiv\.[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?$', s, re.I))
    )

def is_url(s):
    return s.strip().startswith('http://') or s.strip().startswith('https://')

def extract_doi(s):
    m = re.search(r'10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+', s)
    return m.group(0).rstrip('.') if m else s.strip()

def extract_arxiv_id(s):
    m = re.search(r'[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?', s)
    return m.group(0) if m else s.strip()

def download_file(url, target_path):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, 'wb') as f:
        shutil.copyfileobj(resp, f)
    return target_path


def validate_full_pdf(path, *, min_pages=2, min_text_chars=1000):
    """Fail closed unless *path* is a plausible real full-paper PDF.

    This deliberately rejects metadata/abstract-only and Evidentia-synthesized
    PDFs while leaving the historical permissive API unchanged unless callers
    request strict validation.
    """
    path = Path(path)
    try:
        if not path.read_bytes()[:1024].lstrip().startswith(b'%PDF-'):
            raise ValueError("Source is not a PDF (HTML/metadata substitution refused)")
        import fitz
        doc = fitz.open(path)
        if not doc.is_pdf or doc.needs_pass:
            raise ValueError("Source must be an unencrypted PDF")
        first_text = "\n".join(doc[i].get_text() for i in range(min(2, doc.page_count))).lower()
        if "acquired via evidentia paper acquire bridge" in first_text:
            raise ValueError("Evidentia-synthesized PDF is not an acceptable benchmark source")
        if path.stat().st_size < 20_000:
            raise ValueError(f"PDF is implausibly small ({path.stat().st_size} bytes): {path}")
        if doc.page_count < min_pages:
            raise ValueError(f"PDF has only {doc.page_count} page(s); full paper required")
        text_chars = sum(len(page.get_text().strip()) for page in doc)
        if text_chars < min_text_chars:
            raise ValueError(f"PDF contains only {text_chars} extracted text characters; full paper required")
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for strict PDF validation") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Unreadable PDF: {path}: {exc}") from exc
    return path

def query_crossref(doi):
    clean_doi = extract_doi(doi)
    url = f"https://api.crossref.org/works/{clean_doi}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            msg = data.get('message', {})
            title = (msg.get('title') or [''])[0]
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in msg.get('author', [])]
            year = (msg.get('issued', {}).get('date-parts') or [[None]])[0][0]
            venue = (msg.get('container-title') or [''])[0]
            abstract = msg.get('abstract', '')
            # Clean JATS XML tags if present in CrossRef abstract
            if abstract:
                abstract = re.sub(r'<[^>]+>', '', abstract).strip()
            return {
                "title": title,
                "authors": authors,
                "year": year,
                "venue": venue,
                "doi": clean_doi,
                "abstract": abstract
            }
    except Exception:
        return None

def query_unpaywall(doi):
    clean_doi = extract_doi(doi)
    url = f"https://api.unpaywall.org/v2/{clean_doi}?email=evidentia@evidentia.dev"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            best = data.get('best_oa_location') or {}
            pdf_url = best.get('url_for_pdf') or best.get('url')
            return {
                "is_oa": data.get('is_oa', False),
                "pdf_url": pdf_url,
                "title": data.get('title', ''),
                "year": data.get('year')
            }
    except Exception:
        return None

def try_pa_acquire(identifier):
    """Invoke local `pa acquire` CLI if installed."""
    try:
        res = subprocess.run(['pa', 'acquire', str(identifier)], capture_output=True, text=True, timeout=20)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return None

def synthesize_pdf_from_text(title, abstract, sections, out_pdf_path):
    """Generate a clean source-compliant PDF when publisher PDF is behind subscription paywall."""
    import fitz
    doc = fitz.open()

    # Page 1: Metadata & Abstract
    p1 = doc.new_page(width=595, height=842)
    header = f"{title}\n\n[Acquired via Evidentia Paper Acquire Bridge]\n\nAbstract\n{abstract or 'No abstract provided in open-access metadata.'}\n"
    p1.insert_text((50, 60), header, fontsize=11)

    # Subsequent pages: Sections
    if sections:
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((50, 60), "\n\n".join(sections), fontsize=10)

    out_pdf_path = Path(out_pdf_path)
    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf_path))
    return out_pdf_path

def acquire_paper(input_str, out_dir=None, target_pdf_path=None, require_full_pdf=False):
    """Acquire paper by local path, DOI, arXiv ID, or URL.

    ``require_full_pdf`` is used by empirical benchmark preparation and refuses
    the legacy metadata/abstract synthesis fallback.
    """
    s = str(input_str).strip()

    # 1. Local PDF check
    p = Path(s)
    if p.exists() and p.suffix.lower() == '.pdf':
        if require_full_pdf:
            validate_full_pdf(p)
        return p, {"source_type": "LOCAL_PDF", "path": str(p.resolve())}

    print(f"[PAPER_ACQUIRE] Resolving paper identifier: {s}...")
    acquired_meta = {"identifier": s}
    resolved_pdf = target_pdf_path or (Path(out_dir) / 'source/paper.pdf' if out_dir else Path('/tmp/paper.pdf'))
    resolved_pdf = Path(resolved_pdf)

    # 2. ArXiv ID or URL
    if is_arxiv(s):
        arxiv_id = extract_arxiv_id(s)
        acquired_meta["arxiv_id"] = arxiv_id
        acquired_meta["source_type"] = "ARXIV"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Try `pa` CLI
        pa_data = try_pa_acquire(arxiv_id)
        if pa_data:
            acquired_meta.update(pa_data)
            if pa_data.get('pdf_url'):
                pdf_url = pa_data['pdf_url']

        acquired_meta["source_url"] = pdf_url
        print(f"[PAPER_ACQUIRE] Downloading ArXiv PDF from {pdf_url}...")
        download_file(pdf_url, resolved_pdf)
        if require_full_pdf:
            validate_full_pdf(resolved_pdf)
        return resolved_pdf, acquired_meta

    # 3. DOI
    if is_doi(s):
        doi = extract_doi(s)
        acquired_meta["doi"] = doi
        acquired_meta["source_type"] = "DOI"

        # 3a. CrossRef metadata
        cr_data = query_crossref(doi)
        if cr_data:
            acquired_meta.update(cr_data)
            print(f"[PAPER_ACQUIRE] Found CrossRef entry: '{cr_data.get('title')}' ({cr_data.get('year')}) in {cr_data.get('venue')}")

        # 3b. Try `pa` CLI
        pa_data = try_pa_acquire(doi)
        if pa_data:
            acquired_meta.update(pa_data)

        # 3c. Unpaywall Open Access resolution
        upw_data = query_unpaywall(doi)
        pdf_url = None
        if upw_data and upw_data.get('pdf_url'):
            pdf_url = upw_data['pdf_url']
        elif pa_data and pa_data.get('pdf_url'):
            pdf_url = pa_data['pdf_url']

        if pdf_url:
            print(f"[PAPER_ACQUIRE] Downloading Open Access PDF from {pdf_url}...")
            acquired_meta["source_url"] = pdf_url
            try:
                download_file(pdf_url, resolved_pdf)
                if require_full_pdf:
                    validate_full_pdf(resolved_pdf)
                return resolved_pdf, acquired_meta
            except Exception as e:
                if require_full_pdf:
                    raise ValueError(f"Downloaded source is not a valid full PDF: {e}") from e
                print(f"[PAPER_ACQUIRE] Direct PDF download failed: {e}. Falling back to structured synthesis.")

        # 3d. Paywalled fallback: synthesize structured PDF from acquired metadata & abstract
        title = acquired_meta.get('title', f"Paper {doi}")
        abstract = acquired_meta.get('abstract', '')
        if require_full_pdf:
            raise ValueError(f"No publicly accessible full PDF resolved for DOI {doi}; synthetic substitution is forbidden")
        print(f"[PAPER_ACQUIRE] Note: Direct publisher PDF requires institutional subscription. Synthesizing structured source PDF from verified metadata & abstract...")
        synthesize_pdf_from_text(title, abstract, [f"DOI: {doi}", f"Venue: {acquired_meta.get('venue', '')}", f"Authors: {', '.join(acquired_meta.get('authors', []))}"], resolved_pdf)
        return resolved_pdf, acquired_meta

    # 4. Direct HTTP(S) URL to PDF
    if is_url(s) and (s.lower().endswith('.pdf') or 'pdf' in s.lower()):
        print(f"[PAPER_ACQUIRE] Downloading direct PDF URL from {s}...")
        download_file(s, resolved_pdf)
        if require_full_pdf:
            validate_full_pdf(resolved_pdf)
        return resolved_pdf, {"source_type": "DIRECT_URL", "url": s, "source_url": s}

    raise ValueError(f"Could not resolve paper input '{s}'. Please provide a valid PDF file path, DOI, arXiv ID, or URL.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: paper_acquire_bridge.py <doi_or_arxiv_or_url> [<target_pdf>]")
    pdf_path, meta = acquire_paper(sys.argv[1], target_pdf_path=sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"OK: Acquired paper -> {pdf_path}")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
