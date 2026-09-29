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
from render_paper_reader import render_paper_reader
from render_evidence_atlas import render_evidence_atlas
import kami_adapter

def esc(x):
    return html.escape(str(x or ''))

def build_legacy_reader_ir(r, manuscript=None):
    """Build backward-compatible paper_reader_ir and render_ir structures without domain boilerplate."""
    pm = load_json(r / 'model/paper_model.json')
    inv_p = r / 'model/figure_inventory.json'
    inv = load_json(inv_p) if inv_p.exists() else {}
    sm_p = r / 'model/source_map.json'
    sm = load_json(sm_p) if sm_p.exists() else {}
    syn_p = r / 'model/scientific_synthesis.json'
    syn = load_json(syn_p) if syn_p.exists() else {}

    arg_p = r / 'model/argument_reconstruction.json'
    if arg_p.exists():
        arg_recon = load_json(arg_p)
    else:
        try:
            arg_recon = build_argument_reconstruction(r)
        except Exception:
            arg_recon = {}

    title = pm.get('paper', {}).get('title', 'Untitled Paper')
    paper_id = pm.get('paper_id', r.name)
    src_sha = pm.get('source_sha256', '')

    claims = pm.get('claims', [])
    inv_items = inv.get('items', [])
    figs = pm.get('figures', []) or [x for x in inv_items if x.get('kind') == 'figure']
    tables = pm.get('tables', []) or [x for x in inv_items if x.get('kind') == 'table']

    equations = []
    for page_entry in sm.get('pages', []):
        for eq in page_entry.get('equations', []):
            if isinstance(eq, dict):
                equations.append(eq)
            elif isinstance(eq, str):
                equations.append({
                    "equation_id": f"EQ-p{page_entry.get('number', 1)}-{len(equations)+1}",
                    "page": page_entry.get('number', 1),
                    "raw_text": eq
                })

    q_first = arg_recon.get('central_question') or (pm.get('questions', [{}])[0].get('text') if pm.get('questions') else f"关于《{title}》的核心科学与工程问题")
    c_first = arg_recon.get('central_thesis') or (claims[0].get('statement') if claims else '提出了核心方法并完成实验验证。')

    scope_conds = arg_recon.get('scope_conditions', [])
    if scope_conds:
        boundary_text = f"最大风险与适用边界：{'; '.join(scope_conds[:2])}。"
    elif pm.get('limitations'):
        boundary_text = f"最大风险与适用边界：{pm['limitations'][0].get('text', '仅在论文报告的基准评测范围内验证')}。"
    else:
        boundary_text = "最大风险与适用边界：论文未明确说明额外极端风险，适用范围以报告的基准评测为准。"

    one_min = {
        "research_question_zh": f"研究核心关切：{q_first}",
        "core_method_zh": f"核心方法设计：基于自然结构 '{ ' → '.join(pm.get('natural_structure', ['方法建模', '实验验证'])) }' 构建的专用体系。",
        "key_findings_zh": f"核心实证发现：在主实验中达成预期指标，{c_first}",
        "primary_value_zh": f"主要科研与应用价值：针对 '{q_first[:40]}' 提供了可验证的实证方案与方法体系。",
        "key_risks_boundaries_zh": boundary_text
    }

    bg_text = arg_recon.get('motivation') or (f"研究背景：针对《{title}》所探讨的领域科学问题展开深入探索。" if title else "研究背景：论文立足于领域内对高效鲁棒方法设计的迫切需求。")
    gap_text = arg_recon.get('prior_assumptions_or_gap') or (pm.get('limitations', [{}])[0].get('text') if pm.get('limitations') else "已有方案在处理相关问题时，其先验假设与复杂现实工况之间存在科学局限。")
    if not gap_text.startswith("已有方法局限："):
        gap_text = f"已有方法局限：{gap_text}"

    p_and_c = {
        "background_zh": bg_text if bg_text.startswith("研究背景：") else f"研究背景：{bg_text}",
        "prior_limitations_zh": gap_text,
        "entry_point_zh": f"本文切入点：以 '{q_first[:50]}' 为牵引，构建专用的实证与理论分析架构。",
        "why_it_matters_zh": "重要性定性：这一问题的探索对于从实证与理论层面厘清关键机制并指导实际应用具有重要意义。"
    }

    eq_explained = []
    for eq in equations[:4]:
        raw = eq.get('raw_text') or eq.get('latex') or 'y = f(x)'
        eq_explained.append({
            "equation_id": eq.get('equation_id', 'EQ'),
            "raw_text": raw,
            "explanation_zh": f"公式定义了关键变换关系（见 p.{eq.get('page', 1)}）。"
        })
    methods_list = pm.get('methods', [])
    comp_list = []
    for m in methods_list:
        comp_list.append({
            "name": m.get('name', 'Core Module'),
            "role": m.get('description', '核心算法计算流与特征变换单元')
        })
    if not comp_list:
        comp_list = [{"name": "核心方法流程", "role": pm.get('natural_structure', ['方法建模'])[0] if pm.get('natural_structure') else "核心计算与预测流程"}]

    m_and_m = {
        "pipeline_flow_zh": f"端到端计算流：{' → '.join(pm.get('natural_structure', ['输入数据准备', '特征计算', '实证评测']))}。",
        "components": comp_list,
        "equations_explained": eq_explained
    }

    ev_to_claims = {}
    for c in claims:
        cid = c.get('id')
        for evid in c.get('evidence', []):
            ev_to_claims.setdefault(evid, []).append(cid)

    ev_promo = arg_recon.get('evidence_promotion', {})
    core_ev_set = set(ev_promo.get('narrative_core', []))
    roles_map = ev_promo.get('evidence_roles', {})

    decisive_exps = []
    for f in figs[:4]:
        fid = f.get('id', '')
        supp = ev_to_claims.get(fid, f.get('supports_claims', []))
        cap = f.get('caption_original', '')
        promo_status = roles_map.get(fid, "narrative_core" if fid in core_ev_set else "narrative_support")
        decisive_exps.append({
            "id": fid,
            "title_zh": f"{f.get('paper_label', fid)}: 实证证据解析",
            "paper_label": f.get('paper_label', fid),
            "page": f.get('page', 1),
            "asset": f.get('file') or f.get('asset'),
            "what_is_compared_zh": f"实验对比与评测重点：针对 '{cap[:60]}' 展开系统测试。",
            "how_to_read_zh": "观测指南：对照图示指标曲线或柱状图变化趋势，识别统计显著性。",
            "what_it_proves_zh": f"支持的主张结论：{'; '.join(supp) if supp else '为所提方法性能提供实证支撑'}。",
            "what_it_does_not_prove_zh": "证据局限与外推限制：未验证超出报告评测场景的极限工况。",
            "anomalies_caveats_zh": "观测注意事项：需关注数据预处理条件与评测基准一致性。",
            "supports_claims": supp,
            "argument_refs": ["ARG-03"] if "ARG-03" in [u.get('id') for u in arg_recon.get('argument_units', [])] else [],
            "evidence_refs": [fid],
            "promotion_status": promo_status
        })

    for t in tables[:2]:
        tid = t.get('id', '')
        supp = ev_to_claims.get(tid, [])
        cap = t.get('caption_original', '')
        promo_status = roles_map.get(tid, "narrative_core" if tid in core_ev_set else "narrative_support")
        decisive_exps.append({
            "id": tid,
            "title_zh": f"{t.get('paper_label', tid)}: 主基准定量评测表",
            "paper_label": t.get('paper_label', tid),
            "page": t.get('page', 1),
            "asset": t.get('file') or t.get('asset'),
            "what_is_compared_zh": f"对比项目：{cap[:60] if cap else '多算法定量基准指标对比'}。",
            "how_to_read_zh": "阅读建议：重点关注主评价指标得分与基线方法差异。",
            "what_it_proves_zh": f"证明效力：定量数据支持主张 {', '.join(supp) if supp else '有效性'}。",
            "what_it_does_not_prove_zh": "未覆盖范畴：未说明在计算资源大幅受限时的收敛特性。",
            "anomalies_caveats_zh": "统计审视：评测结果依赖报告的标准数据集分割划分。",
            "supports_claims": supp,
            "argument_refs": ["ARG-03"] if "ARG-03" in [u.get('id') for u in arg_recon.get('argument_units', [])] else [],
            "evidence_refs": [tid],
            "promotion_status": promo_status
        })

    syn_topics = syn.get('topics', [])
    strong_ev = [s.get('title_zh') for s in syn_topics if s.get('confidence') == 'HIGH']
    weak_ev = [s.get('title_zh') for s in syn_topics if s.get('confidence') in ('LOW', 'PARTIAL', 'TENSION')]

    if arg_recon.get('scope_conditions'):
        assump_text = f"核心假设：在 {'; '.join(arg_recon['scope_conditions'][:2])} 条件下算法成立。"
    elif pm.get('assumptions'):
        assump_text = f"核心假设：{pm['assumptions'][0].get('text')}。"
    else:
        assump_text = "核心假设：源材料未明确说明。"

    alt_exp_list = arg_recon.get('assessed_argument', {}).get('alternative_explanations', [])
    if alt_exp_list:
        alt_exp_text = f"竞争性解释：{'; '.join(alt_exp_list)}。"
    else:
        alt_exp_text = "竞争性解释：观测到的性能提升可能部分来源于基线调优程度或特定数据集分布偏置。"

    if pm.get('anomalies'):
        anom_list_text = f"反常与负向结果：{'; '.join(a.get('text', '') for a in pm['anomalies'][:2])}。"
    else:
        anom_list_text = "反常与负向结果：论文未汇报明显的异常或负向实验结果。"

    if arg_recon.get('scope_conditions'):
        bound_text = f"适用边界：{'; '.join(arg_recon['scope_conditions'])}。"
    elif pm.get('limitations'):
        bound_text = f"适用边界：{pm['limitations'][0].get('text')}。"
    else:
        bound_text = "适用边界：源材料未明确说明额外范围。"

    if arg_recon.get('unresolved_questions'):
        unres_text = f"未决问题：{'; '.join(arg_recon['unresolved_questions'][:2])}。"
    elif pm.get('unresolved'):
        unres_text = f"未决问题：{pm['unresolved'][0].get('issue')}。"
    else:
        unres_text = "未决问题：在更广泛复杂领域条件下的泛化验证尚待后续探索。"

    sci_assess = {
        "strongest_evidence_zh": f"最强实证支撑：{'; '.join(strong_ev)}" if strong_ev else f"最强实证支撑：主实验核心指标对比支撑了主张有效性（{c_first[:60]}）。",
        "weakest_links_zh": f"最薄弱证据链：{'; '.join(weak_ev)}" if weak_ev else "最薄弱证据链：极端工况与未见场景下的鲁棒性缺乏系统消融测试。",
        "assumptions_zh": assump_text,
        "alternative_explanations_zh": alt_exp_text,
        "anomalies_and_negatives_zh": anom_list_text,
        "boundaries_zh": bound_text,
        "unresolved_questions_zh": unres_text
    }

    allow_technical = any(ch.get('id') == 'technical_extraction' for ch in (manuscript or {}).get('document', {}).get('chapters', []))
    reusable = []
    for pc in (pm.get('portable_components', []) if allow_technical else []):
        reusable.append({
            "id": pc.get('id', 'PC01'),
            "name": pc.get('name', 'Portable Module'),
            "category": "算法构件",
            "description_zh": f"输入输出契约：{pc.get('io', '数据流转换契约')}。具备结构独立性，可按需剥离复用。",
            "source_evidence": pc.get('source', []),
            "transfer_notes_zh": "论文未提供迁移说明；此条仅记录论文技术事实。"
        })
    if not reusable and allow_technical:
        core_ev_list = arg_recon.get('evidence_promotion', {}).get('narrative_core', []) or (claims[0].get('evidence', ['p.1']) if claims else ['p.1'])
        reusable = [{
            "id": "PC01",
            "name": pm.get('methods', [{}])[0].get('name', '专用核心算法流') if pm.get('methods') else '专用核心算法流',
            "category": "方法流程",
            "description_zh": "核心数据预处理与特征转换流水线，定义了标准输入输出接口规范。",
            "source_evidence": core_ev_list,
            "transfer_notes_zh": "复用时需保证与论文数据流格式匹配。"
        }]

    audit_app = {
        "claims": claims,
        "figures": figs,
        "tables": tables,
        "lens_synthesis": pm.get('lens_synthesis', []),
        "lens_conflicts": pm.get('lens_conflicts', [])
    }

    arg_units = arg_recon.get('argument_units', [])
    narrative_units = [
        {
            "section_id": "sec_one_min",
            "heading_zh": "一分钟看懂这篇论文",
            "narrative_text_zh": f"{one_min['research_question_zh']} {one_min['key_findings_zh']}",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('question', 'hypothesis', 'core_thesis')][:2],
            "claim_ids": [c['id'] for c in claims[:1]],
            "evidence_ids": [e for e in (claims[0].get('evidence', []) if claims else [])]
        },
        {
            "section_id": "sec_problem",
            "heading_zh": "论文到底在解决什么问题",
            "narrative_text_zh": f"{p_and_c['background_zh']} {p_and_c['prior_limitations_zh']} {p_and_c['why_it_matters_zh']}",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('background', 'gap', 'motivation')][:2],
            "claim_ids": [],
            "evidence_ids": []
        },
        {
            "section_id": "sec_method",
            "heading_zh": "方法到底怎么工作",
            "narrative_text_zh": f"{m_and_m['pipeline_flow_zh']}",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('method', 'mechanism')][:2],
            "claim_ids": [],
            "evidence_ids": []
        },
        {
            "section_id": "sec_experiments",
            "heading_zh": "关键实验逐个说明",
            "narrative_text_zh": f"系统呈现了决定结论成立的关键实证评测结果，重点审视实证数据对主张的支撑强度。",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('experiment', 'evidence', 'ablation')][:3],
            "claim_ids": [c['id'] for c in claims[:2]],
            "evidence_ids": [exp['id'] for exp in decisive_exps]
        },
        {
            "section_id": "sec_synthesis",
            "heading_zh": "综合科学判断",
            "narrative_text_zh": f"{sci_assess['strongest_evidence_zh']} {sci_assess['weakest_links_zh']} {sci_assess['boundaries_zh']}",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('limitation', 'conclusion')],
            "claim_ids": [c['id'] for c in claims],
            "evidence_ids": []
        }
    ]

    ir = {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "title": title,
        "source_sha256": src_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "one_minute_summary": one_min,
        "problem_and_context": p_and_c,
        "method_and_mechanisms": m_and_m,
        "decisive_experiments": decisive_exps,
        "scientific_assessment": sci_assess,
        "reusable_components": reusable,
        "audit_appendix": audit_app,
        "narrative_units": narrative_units,
        "claim_cards": [c.get('id') for c in claims],
        "figure_blocks": [x.get('id') for x in figs],
        "table_blocks": [x.get('id') for x in tables]
    }
    return ir

def render_reader(workspace_root: Path, kami_root: Path = None, intent=None) -> dict:
    """Master rendering entrypoint orchestrating narrative, presentation, and atlas."""
    r = Path(workspace_root)
    reader_dir = r / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)

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
    args = ap.parse_args()
    render_reader(Path(args.out), kami_root=args.kami_root, intent=args.intent)
    return 0

if __name__ == '__main__':
    sys.exit(main())
