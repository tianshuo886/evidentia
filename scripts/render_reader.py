#!/usr/bin/env python3
"""Unified Reader orchestrator for Evidentia (Issue #9).

Principle: "Evidentia owns truth. AI owns narrative. Kami owns presentation."

Architecture:
1. Semantic Narrative IR:
   - reader/narrative_manuscript.json (composed by narrative_composer_agent)
2. Primary Editorial Reader (Human deep-reading):
   - reader/paper_reader.html (Kami Chinese long-doc presentation backend)
   - reader/paper_reader.md (Editorial markdown document)
   - reader/paper_reader.pdf (Kami WeasyPrint vector delivery)
3. Secondary Inspection Surface (Audit & provenance):
   - reader/evidence_atlas.html (Claim ↔ Evidence navigation, O/I/A, verifier status)
   - reader/evidence_atlas.json
4. Backward Compatibility Aliases:
   - reader/reader.html -> symlink / copy of paper_reader.html
   - reader/reader.md   -> symlink / copy of paper_reader.md
   - reader/reader.pdf  -> symlink / copy of paper_reader.pdf
   - reader/paper_reader_ir.json & reader/render_ir.json
"""
import argparse, html, json, os, re, shutil, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, schema_validate, sha256
from build_argument_reconstruction import build_argument_reconstruction
from narrative_composer_agent import compose_narrative_manuscript
from render_paper_reader import render_paper_reader, render_block_html
from render_evidence_atlas import render_evidence_atlas
from intent_router import route_intent, INTENTS
import kami_adapter

def esc(x):
    return html.escape(str(x or ''))

def build_legacy_reader_ir(r, manuscript=None):
    """Write a compatibility projection without rebuilding a second narrative.

    The v2 manuscript is the source of presentation truth.  This projection is
    retained for older consumers and deliberately contains no dashboard copy,
    role labels, or generated scientific claims.
    """
    manuscript = manuscript or load_json(r / 'reader/narrative_manuscript.json')
    doc = manuscript.get('document', {})
    spine = doc.get('story_spine', {})  # compatibility metadata only
    chapters = doc.get('sections') or doc.get('chapters', [])
    pm = load_json(r / 'model/paper_model.json') if (r / 'model/paper_model.json').exists() else {}
    claims = pm.get('claims', [])
    inv = load_json(r / 'model/figure_inventory.json') if (r / 'model/figure_inventory.json').exists() else {}
    appendix_figs = [dict(x) for x in pm.get('figures', [])]
    appendix_tables = [dict(x) for x in pm.get('tables', [])]
    if not appendix_figs:
        appendix_figs = [dict(x) for x in inv.get('items', []) if x.get('kind') == 'figure']
    if not appendix_tables:
        appendix_tables = [dict(x) for x in inv.get('items', []) if x.get('kind') == 'table']
    figs = []
    tables = []
    units = []
    evidence_ids = []
    for chapter in chapters:
        text_parts = []
        chapter_evidence = []
        for block in chapter.get('blocks', []):
            if block.get('text'):
                text_parts.append(block.get('text'))
            chapter_evidence.extend(block.get('evidence_refs', []))
            if block.get('type') == 'figure':
                figs.append({'id': block.get('evidence_id'), 'caption_original': block.get('caption'), 'file': block.get('asset'), 'page': block.get('page', 1)})
            elif block.get('type') == 'table':
                tables.append({'id': block.get('evidence_id'), 'caption_original': block.get('caption'), 'file': block.get('asset'), 'page': block.get('page', 1)})
        evidence_ids.extend(chapter_evidence)
        units.append({'section_id': chapter.get('id'), 'purpose': chapter.get('purpose', ''), 'heading_zh': chapter.get('title', ''), 'narrative_text_zh': ' '.join(text_parts), 'argument_unit_ids': list(chapter.get('argument_refs') or []), 'claim_ids': [], 'evidence_ids': list(dict.fromkeys(chapter_evidence)), 'source_anchors': list(chapter.get('source_anchors') or []), 'bindings': list(chapter.get('bindings') or [])})
    summary = doc.get('executive_summary', {})
    final_text = ' '.join(b.get('text', '') for c in chapters[-2:] for b in c.get('blocks', []) if b.get('text'))
    ir = {
        'schema_version': '2.0',
        'compatibility_projection': True,
        'paper_id': manuscript.get('paper_id', r.name),
        'title': doc.get('title', ''),
        'source_sha256': manuscript.get('source_sha256', ''),
        'one_minute_summary': {
            'research_question_zh': summary.get('key_question', spine.get('central_question', '')),
            'core_method_zh': spine.get('central_move', ''),
            'key_findings_zh': summary.get('core_finding', ''),
            'primary_value_zh': spine.get('motivation', ''),
            'key_risks_boundaries_zh': summary.get('core_boundary', ''),
        },
        'problem_and_context': {
            'background_zh': spine.get('motivation', ''),
            'prior_limitations_zh': spine.get('prior_gap', ''),
            'entry_point_zh': spine.get('central_move', ''),
            'why_it_matters_zh': spine.get('central_question', ''),
        },
        'method_and_mechanisms': {'pipeline_flow_zh': spine.get('method_logic', ''), 'components': [], 'equations_explained': []},
        'decisive_experiments': [
            {'id': f.get('id', ''), 'title_zh': f.get('caption_original', ''), 'what_is_compared_zh': '', 'how_to_read_zh': '', 'what_it_proves_zh': '', 'what_it_does_not_prove_zh': '', 'anomalies_caveats_zh': '', 'paper_label': f.get('caption_original', ''), 'page': f.get('page', 1), 'asset': f.get('file'), 'supports_claims': [], 'evidence_refs': [f.get('id', '')], 'promotion_status': 'narrative_support'} for f in figs + tables
        ],
        'scientific_assessment': {
            'strongest_evidence_zh': summary.get('core_finding', ''),
            'weakest_links_zh': final_text,
            'assumptions_zh': spine.get('prior_gap', ''),
            'alternative_explanations_zh': final_text,
            'anomalies_and_negatives_zh': final_text,
            'boundaries_zh': summary.get('core_boundary', ''),
            'unresolved_questions_zh': '；'.join(spine.get('scope_and_limits', [])),
        },
        'reusable_components': [],
        'audit_appendix': {'claims': claims, 'figures': appendix_figs, 'tables': appendix_tables},
        'narrative_units': units,
        'claim_cards': [c.get('id') for c in claims], 'figure_blocks': [f.get('id') for f in figs], 'table_blocks': [t.get('id') for t in tables],
    }
    return ir

def render_reader(workspace_root: Path, kami_root: Path = None, intent=None) -> dict:
    """Master rendering entrypoint orchestrating narrative, presentation, and atlas."""
    r = Path(workspace_root)
    reader_dir = r / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)

    # A manuscript must be derived from the persisted argument artifact.  The
    # compatibility fixture and ad-hoc callers may not have built it yet, so
    # create that single upstream artifact before composing the Reader.
    if not (r / 'model/argument_reconstruction.json').exists():
        build_argument_reconstruction(r)

    # 1. Compose semantic narrative manuscript
    manuscript = compose_narrative_manuscript(r, intent=intent)
    manuscript_file = reader_dir / 'narrative_manuscript.json'
    manuscript_file.write_text(json.dumps(manuscript, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # 2. Render primary Paper Reader (HTML, MD, PDF via Kami)
    reader_res = render_paper_reader(r, kami_root=kami_root)

    # 3. Render secondary inspection Evidence Atlas (HTML, JSON)
    atlas_res = render_evidence_atlas(r)

    # 4. Generate backward compatibility IR files
    legacy_ir = build_legacy_reader_ir(r, manuscript=manuscript)
    (reader_dir / 'paper_reader_ir.json').write_text(json.dumps(legacy_ir, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (reader_dir / 'render_ir.json').write_text(json.dumps(legacy_ir, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # 5. Create backward compatibility symlinks/copies
    paper_html = reader_dir / 'paper_reader.html'
    compat_html = reader_dir / 'reader.html'
    if paper_html.exists():
        shutil.copy2(str(paper_html), str(compat_html))

    paper_md = reader_dir / 'paper_reader.md'
    compat_md = reader_dir / 'reader.md'
    if paper_md.exists():
        shutil.copy2(str(paper_md), str(compat_md))

    paper_pdf = reader_dir / 'paper_reader.pdf'
    compat_pdf = reader_dir / 'reader.pdf'
    if paper_pdf.exists():
        shutil.copy2(str(paper_pdf), str(compat_pdf))

    # Paper-named copy if title/id exists
    pm = load_json(r / 'model/paper_model.json')
    paper_id = pm.get('paper_id') or r.name
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', str(paper_id)).strip('_')
    if safe_name and safe_name not in ('reader', 'paper_reader'):
        named_html = reader_dir / f'{safe_name}.html'
        named_pdf = reader_dir / f'{safe_name}.pdf'
        if paper_html.exists():
            shutil.copy2(str(paper_html), str(named_html))
        if paper_pdf.exists():
            shutil.copy2(str(paper_pdf), str(named_pdf))

    # Dedicated standalone technical extraction artifacts (Issue #12)
    tech_md_p = reader_dir / 'technical_extraction.md'
    tech_html_p = reader_dir / 'technical_extraction.html'
    document = manuscript.get('document', {})
    tech_ch = next((ch for ch in (document.get('sections') or document.get('chapters', [])) if ch.get('id') in ('technical_extraction', 'technical-extraction')), None)
    if tech_ch:
        p_title = manuscript.get('document', {}).get('title', '论文')
        lines = [
            f"# {p_title} · 论文技术细节提取 (Technical Extraction)",
            f"\n> 声明：本报告仅整理论文自身明确给出的算法、输入输出与实验设置，严格局限于论文自身技术范围，不包含用户项目适配或迁移建议。\n",
            f"## {tech_ch.get('title', '论文技术细节提取')}",
            f"{tech_ch.get('lead', '')}\n"
        ]
        for b in tech_ch.get('blocks', []):
            if b.get('type') == 'paragraph':
                lines.append(f"{b.get('text', '')}\n")
            elif b.get('type') == 'callout':
                lines.append(f"> {b.get('text', '')}\n")
        tech_md_p.write_text("\n".join(lines) + "\n", encoding='utf-8')

        body_blocks = "\n".join([render_block_html(b, r) for b in tech_ch.get('blocks', [])])
        tech_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{html.escape(p_title)} · 论文技术细节提取</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif; line-height: 1.6; max-width: 860px; margin: 0 auto; padding: 32px 24px; color: #1e293b; background: #faf9f5; }}
h1 {{ color: #1B365D; border-bottom: 2px solid #1B365D; padding-bottom: 12px; }}
.lead {{ font-size: 1.1em; color: #475569; margin-bottom: 24px; font-style: italic; }}
.callout {{ background: #f1f5f9; border-left: 4px solid #1B365D; padding: 16px; margin: 16px 0; border-radius: 4px; }}
.back-link {{ margin-bottom: 16px; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="back-link"><a href="paper_reader.html">← 返回全文研读报告</a></div>
<h1>{html.escape(p_title)}</h1>
<p class="lead">{html.escape(tech_ch.get('lead', ''))}</p>
<div class="content">
{body_blocks}
</div>
</body>
</html>"""
        tech_html_p.write_text(tech_html, encoding='utf-8')
    else:
        if tech_md_p.exists():
            tech_md_p.unlink()
        if tech_html_p.exists():
            tech_html_p.unlink()

    # 6. Collect Kami audit report
    kami_adapter.collect_kami_report(paper_pdf, html_path=paper_html, kami_root=kami_root, out_dir=r)

    return {
        "status": "OK",
        "paper_reader_html": str(paper_html),
        "paper_reader_pdf": str(paper_pdf),
        "evidence_atlas_html": str(reader_dir / 'evidence_atlas.html'),
        "narrative_manuscript": str(manuscript_file)
    }

def main():
    ap = argparse.ArgumentParser(description="Render Chinese-first Scientific Reader and Evidence Atlas.")
    ap.add_argument('--out', required=True, help="Workspace run directory")
    ap.add_argument('--kami-root', default=None, help="Path to Kami skill/clone")
    ap.add_argument('--intent', choices=('PAPER_READING', 'PAPER_TECHNICAL_EXTRACTION'), default=None)
    ap.add_argument('--prompt', default=None, help="User prompt to route intent from")
    args = ap.parse_args()
    intent = route_intent(prompt=args.prompt, explicit=args.intent)
    render_reader(Path(args.out), kami_root=args.kami_root, intent=intent)
    return 0

if __name__ == '__main__':
    sys.exit(main())
