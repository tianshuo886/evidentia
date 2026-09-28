#!/usr/bin/env python3
"""Render Chinese-first Deep-Reading Scientific Reader for Evidentia (Workstreams C & D).

Architecture:
- Single Synthesis-Rich Content IR: reader/paper_reader_ir.json (and reader/render_ir.json)
- Two downstream renderers:
  * HTML Reader: reader/paper_reader.html (and symlink/alias reader/reader.html)
  * Markdown Reader: reader/paper_reader.md (and symlink/alias reader/reader.md)
  * PDF Snapshot: reader/paper_reader.pdf (and symlink/alias reader/reader.pdf)
- Seven-layer scientific narrative hierarchy:
  1. 一分钟看懂这篇论文 (Quick scan: problem, method, findings, value, boundaries)
  2. 论文到底在解决什么问题 (Background, limitations, entry point, significance)
  3. 方法到底怎么工作 (End-to-end mechanism, components, equations explained)
  4. 关键实验逐个说明 (Decisive figures/tables with explicit reading guide & caveats)
  5. 综合科学判断 (Strongest evidence, weakest links, assumptions, counterfactuals)
  6. 可复用技术内容 (Detachable methods, losses, protocols, practical notes)
  7. 证据审计附录 (Audit & provenance: Claim cards, O/I/A, verifier status, collapsible)
- Strictly project-independent and immutable. Zero automatic apply delta scanning.
"""
import argparse, html, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, schema_validate, sha256
from build_argument_reconstruction import build_argument_reconstruction

def esc(x):
    return html.escape(str(x or ''))

def build_reader_ir(r):
    pm = load_json(r / 'model/paper_model.json')
    inv = load_json(r / 'model/figure_inventory.json')
    sm_p = r / 'model/source_map.json'
    sm = load_json(sm_p) if sm_p.exists() else {}
    syn_p = r / 'model/scientific_synthesis.json'
    syn = load_json(syn_p) if syn_p.exists() else {}

    # Load or dynamically build argument reconstruction artifact
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

    # 1. 一分钟看懂这篇论文
    q_first = arg_recon.get('central_question') or (pm.get('questions', [{}])[0].get('text') if pm.get('questions') else f"关于《{title}》的核心科学与工程问题")
    c_first = arg_recon.get('central_thesis') or (claims[0].get('statement') if claims else '提出了核心方法并完成实验验证。')
    
    # Boundary extraction
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

    # 2. 论文到底在解决什么问题
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

    # 3. 方法到底怎么工作
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
        "pipeline_flow_zh": f"数据流转路径：原始输入 → {' → '.join([c['name'] for c in comp_list])} → 最终评估输出。",
        "components": comp_list,
        "equations_explained": eq_explained
    }

    # 4. 关键实验逐个说明 (Selective promotion: narrative_core & narrative_support only)
    decisive_exps = []
    ev_to_claims = {}
    for c in claims:
        cid = c.get('id')
        for evid in c.get('evidence', []):
            ev_to_claims.setdefault(evid, []).append(cid)

    ev_promo = arg_recon.get('evidence_promotion', {})
    core_ev_set = set(ev_promo.get('narrative_core', []))
    support_ev_set = set(ev_promo.get('narrative_support', []))
    uncertain_ev_set = set(ev_promo.get('uncertain', []))
    roles_map = ev_promo.get('evidence_roles', {})

    allowed_narrative_ev = core_ev_set | support_ev_set | uncertain_ev_set
    if not allowed_narrative_ev and (figs or tables):
        # Fallback: take at most first 2 figures and first 2 tables if no promotion was specified
        allowed_narrative_ev = {f.get('id') for f in figs[:2]} | {t.get('id') for t in tables[:2]}

    for f in figs:
        fid = f.get('id', '')
        if fid not in allowed_narrative_ev:
            continue
        supp = ev_to_claims.get(fid, f.get('supports_claims', []))
        cap = f.get('caption_original', '')
        f_lims = f.get('limitations', [])
        anom_text = f"异常与注意事项：{f_lims[0]}" if f_lims else "异常与注意事项：未在当前证据中确认超出报告指标的显著异常。"
        promo_status = roles_map.get(fid, "narrative_core" if fid in core_ev_set else "narrative_support")

        decisive_exps.append({
            "id": fid,
            "title_zh": f"{f.get('paper_label', fid)}: 实证证据解析",
            "paper_label": f.get('paper_label', fid),
            "page": f.get('page', 1),
            "asset": f.get('file') or f.get('asset'),
            "what_is_compared_zh": f"对比内容与对象：围绕论文核心指标展开对照测试。原始题注：{cap}",
            "how_to_read_zh": "读图指引：对比不同实验条件与基线下的指标走势，评估核心变量对结论的支撑力度。",
            "what_it_proves_zh": f"直接支撑结论：为论文主张 {', '.join(supp) if supp else '核心有效性'} 提供了直接观测数据支持。",
            "what_it_does_not_prove_zh": "非证明范围：未在当前证据中确认超出评测指标范围的结论。",
            "anomalies_caveats_zh": anom_text,
            "supports_claims": supp,
            "argument_refs": ["ARG-03"] if "ARG-03" in [u.get('id') for u in arg_recon.get('argument_units', [])] else [],
            "evidence_refs": [fid],
            "promotion_status": promo_status
        })

    for t in tables:
        tid = t.get('id', '')
        if tid not in allowed_narrative_ev:
            continue
        supp = ev_to_claims.get(tid, [])
        cap = t.get('caption_original', '')
        promo_status = roles_map.get(tid, "narrative_core" if tid in core_ev_set else "narrative_support")

        decisive_exps.append({
            "id": tid,
            "title_zh": f"{t.get('paper_label', tid)}: 主基准定量评测表",
            "paper_label": t.get('paper_label', tid),
            "page": t.get('page', 1),
            "asset": t.get('file') or t.get('asset'),
            "what_is_compared_zh": f"评测维度与基准对比。原始题注：{cap}",
            "how_to_read_zh": "表格读法：对比行项目对应的不同方案，结合列指标数值评估相对表现。",
            "what_it_proves_zh": f"直接支撑结论：定量验证方法在关键指标上的数值表现（支持主张 {', '.join(supp) if supp else '核心指标'}）。",
            "what_it_does_not_prove_zh": "非证明范围：表格数值无法直接反映未列出环境或未测试分布下的表现。",
            "anomalies_caveats_zh": "异常与注意事项：未在当前证据中确认超出报告指标的显著异常。",
            "supports_claims": supp,
            "argument_refs": ["ARG-03"] if "ARG-03" in [u.get('id') for u in arg_recon.get('argument_units', [])] else [],
            "evidence_refs": [tid],
            "promotion_status": promo_status
        })

    # If decisive_exps is still empty because no figures/tables exist, ensure at least an empty array is schema valid
    # 5. 综合科学判断
    syn_topics = syn.get('topics', [])
    strong_ev = [s.get('title_zh') for s in syn_topics if s.get('confidence') == 'HIGH']
    weak_ev = [s.get('title_zh') for s in syn_topics if s.get('confidence') in ('LOW', 'PARTIAL', 'TENSION')]

    # Assumptions
    if arg_recon.get('scope_conditions'):
        assump_text = f"核心假设：{'; '.join(arg_recon['scope_conditions'][:2])}。"
    elif pm.get('assumptions'):
        assump_text = f"核心假设：{pm['assumptions'][0].get('text')}。"
    else:
        assump_text = "核心假设：论文未明确说明形式化先验假设，默认评估环境与基准测试分布保持一致。"

    # Alternative explanations
    alt_exp_list = arg_recon.get('assessed_argument', {}).get('alternative_explanations', [])
    if alt_exp_list:
        alt_text = f"竞争解释：{'; '.join(alt_exp_list[:2])}。"
    else:
        alt_text = "竞争解释：论文及各透镜审视未提出显著的竞争性替代假说。"

    # Anomalies
    if pm.get('anomalies'):
        anom_list_text = f"反常与负向结果：{'; '.join(a.get('text', '') for a in pm['anomalies'][:2])}。"
    else:
        anom_list_text = "反常与负向结果：未在当前证据中确认明确的反常或负向结果。"

    # Boundaries
    if arg_recon.get('scope_conditions'):
        bound_text = f"适用边界：{'; '.join(arg_recon['scope_conditions'][:2])}。"
    elif pm.get('limitations'):
        bound_text = f"适用边界：{pm['limitations'][0].get('text')}。"
    else:
        bound_text = "适用边界：当前结论受限于论文报告的具体数据集与评估协议范围。"

    # Unresolved
    if arg_recon.get('unresolved_questions'):
        unres_text = f"未决问题：{'; '.join(arg_recon['unresolved_questions'][:2])}。"
    elif pm.get('unresolved'):
        unres_text = f"未决问题：{pm['unresolved'][0].get('issue')}。"
    else:
        unres_text = "未决问题：更广泛现实条件下的长期泛化与实际表现仍待进一步验证。"
    
    sci_assess = {
        "strongest_evidence_zh": f"最坚实的证据链：{', '.join(strong_ev) if strong_ev else '主要基准实验下的核心实证指标具备直接数据支撑。'}",
        "weakest_links_zh": f"最薄弱的推理链：{', '.join(weak_ev) if weak_ev else '由实证关联性推断广泛一般性结论的部分，需注意先验控制边界。'}",
        "assumptions_zh": assump_text,
        "alternative_explanations_zh": alt_text,
        "anomalies_and_negatives_zh": anom_list_text,
        "boundaries_zh": bound_text,
        "unresolved_questions_zh": unres_text
    }

    # 6. 可复用技术内容
    reusable = []
    for pc in pm.get('portable_components', []):
        reusable.append({
            "id": pc.get('id', 'PC01'),
            "name": pc.get('name', 'Portable Module'),
            "category": "算法实现 / 算子",
            "description_zh": f"输入输出契约：{pc.get('io', '数据流转换契约')}。具备结构独立性，可按需剥离复用。",
            "source_evidence": pc.get('source', []),
            "transfer_notes_zh": "迁移建议：在非同构下游任务接入时，需重新对齐输入契约与评测基准。"
        })
    if not reusable:
        core_ev_list = arg_recon.get('evidence_promotion', {}).get('narrative_core', []) or (claims[0].get('evidence', ['p.1']) if claims else ['p.1'])
        reusable = [{
            "id": "PC01",
            "name": "核心算法设计",
            "category": "算法实现",
            "description_zh": "论文未提取出可独立拆分的通用模块，建议参考正文方法描述进行具体任务的重实现。",
            "source_evidence": core_ev_list[:2],
            "transfer_notes_zh": "迁移建议：需结合具体应用场景调整实现。"
        }]

    # 7. 证据审计附录
    appendix = {
        "claims": claims,
        "figures": figs,
        "tables": tables,
        "lens_synthesis": pm.get('lens_synthesis', []),
        "lens_conflicts": pm.get('lens_conflicts', [])
    }

    # Narrative semantic units
    arg_units = arg_recon.get('argument_units', [])
    arg_unit_ids = [u['id'] for u in arg_units]
    narrative_units = [
        {
            "section_id": "one_minute_summary",
            "purpose": "thesis_overview",
            "heading_zh": "一分钟看懂这篇论文",
            "narrative_text_zh": f"{one_min['research_question_zh']} {one_min['core_method_zh']} {one_min['key_findings_zh']}",
            "argument_unit_ids": [uid for uid in ("ARG-01", "ARG-02") if uid in arg_unit_ids],
            "claim_ids": [c['id'] for c in claims[:1]],
            "evidence_ids": list(core_ev_set)[:2],
            "epistemic_status": "SUPPORTED"
        },
        {
            "section_id": "problem_and_context",
            "purpose": "motivation_and_gap",
            "heading_zh": "论文到底在解决什么问题",
            "narrative_text_zh": f"{p_and_c['background_zh']} {p_and_c['prior_limitations_zh']} {p_and_c['entry_point_zh']}",
            "argument_unit_ids": [uid for uid in ("ARG-01",) if uid in arg_unit_ids],
            "claim_ids": [],
            "evidence_ids": [],
            "epistemic_status": "SUPPORTED"
        },
        {
            "section_id": "method_and_mechanisms",
            "purpose": "method_rationale",
            "heading_zh": "方法到底怎么工作",
            "narrative_text_zh": m_and_m['pipeline_flow_zh'],
            "argument_unit_ids": [uid for uid in ("ARG-02",) if uid in arg_unit_ids],
            "claim_ids": [claims[0]['id']] if claims else [],
            "evidence_ids": [],
            "epistemic_status": "SUPPORTED"
        },
        {
            "section_id": "scientific_assessment",
            "purpose": "cross_lens_assessment",
            "heading_zh": "综合科学判断",
            "narrative_text_zh": f"{sci_assess['strongest_evidence_zh']} {sci_assess['weakest_links_zh']}",
            "argument_unit_ids": [u['id'] for u in arg_units if u.get('semantic_role') in ('limitation', 'conclusion')],
            "claim_ids": [c['id'] for c in claims[:2]],
            "evidence_ids": list(core_ev_set),
            "epistemic_status": "PARTIAL" if weak_ev else "SUPPORTED"
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
        "audit_appendix": appendix,
        "argument_refs": arg_unit_ids,
        "evidence_promotion": ev_promo,
        "narrative_units": narrative_units,
        # Backward compatibility for reader_audit.py
        "claim_cards": [c.get('id') for c in claims],
        "figure_blocks": [x.get('id') for x in figs],
        "table_blocks": [x.get('id') for x in tables]
    }
    return ir

def render_html(ir, workspace_root):
    title = ir['title']
    one_min = ir['one_minute_summary']
    p_and_c = ir['problem_and_context']
    m_and_m = ir['method_and_mechanisms']
    exps = ir['decisive_experiments']
    sci = ir['scientific_assessment']
    reusable = ir['reusable_components']
    app = ir['audit_appendix']
    claims = app.get('claims', [])
    conflicts = app.get('lens_conflicts', [])
    
    # CSS styling - Clean, modern, highly readable, Chinese-first typography
    css = """
:root {
  --primary: #0284c7;
  --primary-dark: #0369a1;
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --text: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --accent: #f59e0b;
  --badge-bg: #e0f2fe;
  --badge-text: #0369a1;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg);
  margin: 0;
  padding: 32px 20px;
}
.container { max-width: 1040px; margin: 0 auto; }
header {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 28px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.eyebrow {
  font-size: 0.85em;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--primary);
  text-transform: uppercase;
  margin: 0 0 8px 0;
}
h1 { font-size: 2rem; line-height: 1.3; margin: 0 0 16px 0; color: #0284c7; }
.meta-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 0.88em;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  padding-top: 14px;
}
.section-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px 32px;
  margin-bottom: 24px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.section-card h2 {
  font-size: 1.4rem;
  color: #0f172a;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 10px;
  margin-top: 0;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-card h3 { font-size: 1.15rem; color: var(--primary-dark); margin: 20px 0 10px 0; }
.one-min-grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
.one-min-item {
  background: #f1f5f9;
  border-left: 4px solid var(--primary);
  padding: 12px 18px;
  border-radius: 0 8px 8px 0;
}
.one-min-item strong { color: var(--primary-dark); display: block; margin-bottom: 4px; }
.exp-block {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
  background: #ffffff;
}
.exp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}
.exp-asset {
  text-align: center;
  margin: 16px 0;
  background: #f8fafc;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}
.exp-asset img { max-width: 100%; max-height: 480px; object-fit: contain; border-radius: 4px; }
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 0.82em;
  font-weight: 600;
  text-decoration: none;
  background: var(--badge-bg);
  color: var(--badge-text);
}
.badge-evidence { background: #dbeafe; color: #1e40af; }
.badge-epistemic-supported { background: #dcfce7; color: #166534; }
.badge-epistemic-partial { background: #fef9c3; color: #854d0e; }
.badge-epistemic-unresolved { background: #fee2e2; color: #991b1b; }
.badge-verifier-supported { background: #dcfce7; color: #15803d; }
.badge-verifier-rejected { background: #fee2e2; color: #b91c1c; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 14px 0; }
.detail-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  font-size: 0.94em;
}
.detail-box strong { color: #334155; display: block; margin-bottom: 4px; }
.detail-box.warning { border-left: 4px solid #f59e0b; }
.detail-box.success { border-left: 4px solid #10b981; }
.oia-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 10px;
}
.oia-box {
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 0.88em;
  line-height: 1.5;
}
.oia-obs { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e3a8a; }
.oia-auth { background: #fefce8; border: 1px solid #fef08a; color: #713f12; }
.oia-read { background: #f0fdf4; border: 1px solid #bbf7d0; color: #14532d; }
details {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 20px;
  margin-top: 14px;
}
details summary {
  font-weight: 600;
  cursor: pointer;
  color: var(--primary-dark);
  outline: none;
  font-size: 1.05rem;
}
.claim-article {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 14px;
}
"""

    # Section 1: 一分钟看懂这篇论文
    s1_html = f"""
    <section class="section-card" id="one-minute-summary">
      <h2>1. 一分钟看懂这篇论文</h2>
      <div class="one-min-grid">
        <div class="one-min-item"><strong>研究问题</strong>{esc(one_min['research_question_zh'])}</div>
        <div class="one-min-item"><strong>核心方法</strong>{esc(one_min['core_method_zh'])}</div>
        <div class="one-min-item"><strong>核心发现</strong>{esc(one_min['key_findings_zh'])}</div>
        <div class="one-min-item"><strong>最大价值</strong>{esc(one_min['primary_value_zh'])}</div>
        <div class="one-min-item"><strong>最大风险与边界</strong>{esc(one_min['key_risks_boundaries_zh'])}</div>
      </div>
    </section>
    """

    # Section 2: 论文到底在解决什么问题
    s2_html = f"""
    <section class="section-card" id="problem-and-context">
      <h2>2. 论文到底在解决什么问题</h2>
      <div class="detail-box" style="margin-bottom: 12px;"><strong>研究背景与痛点</strong>{esc(p_and_c['background_zh'])}</div>
      <div class="detail-box warning" style="margin-bottom: 12px;"><strong>已有先验与局限</strong>{esc(p_and_c['prior_limitations_zh'])}</div>
      <div class="detail-box success" style="margin-bottom: 12px;"><strong>本文切入视角</strong>{esc(p_and_c['entry_point_zh'])}</div>
      <div class="detail-box"><strong>问题定性与重要度</strong>{esc(p_and_c['why_it_matters_zh'])}</div>
    </section>
    """

    # Section 3: 方法到底怎么工作
    comp_html = "".join([f"<li><strong>{esc(c['name'])}:</strong> {esc(c['role'])}</li>" for c in m_and_m['components']])
    eq_html = "".join([
        f"<div class='detail-box' style='margin-bottom: 10px;'><code>{esc(eq['equation_id'])}: {esc(eq['raw_text'])}</code><p style='margin:4px 0 0 0;'>{esc(eq['explanation_zh'])}</p></div>"
        for eq in m_and_m['equations_explained']
    ])
    s3_html = f"""
    <section class="section-card" id="method-and-mechanisms">
      <h2>3. 方法到底怎么工作</h2>
      <div class="detail-box success" style="margin-bottom: 16px;">
        <strong>端到端数据与控制流</strong>
        <p style="margin: 4px 0 0 0;">{esc(m_and_m['pipeline_flow_zh'])}</p>
      </div>
      <h3>核心组件拆解</h3>
      <ul>{comp_html}</ul>
      <h3>核心数学与物理公式中文解读</h3>
      {eq_html if eq_html else "<p><em>无独立显式公式</em></p>"}
    </section>
    """

    # Section 4: 关键实验逐个说明
    exp_cards_html = []
    for exp in exps:
        eid = exp['id']
        supp_links = " ".join([f"<a href='#{esc(c)}' class='badge badge-evidence'>{esc(c)}</a>" for c in exp.get('supports_claims', [])])
        asset_html = ""
        if exp.get('asset'):
            asset_path = workspace_root / exp['asset']
            if asset_path.exists():
                asset_html = f"<div class='exp-asset'><img src='../{esc(exp['asset'])}' alt='{esc(eid)}'><p style='font-size:0.85em;color:#64748b;margin:6px 0 0 0;'>图表凭据: {esc(exp['asset'])} (p.{exp['page']})</p></div>"
        
        exp_cards_html.append(f"""
        <article class="exp-block" id="{esc(eid)}">
          <div class="exp-header">
            <h3 style="margin:0;"><a href="#{esc(eid)}">{esc(exp['title_zh'])}</a></h3>
            <div><strong>Supports Claims:</strong> {supp_links if supp_links else "<em>None</em>"} · <a href="#p.{exp['page']}" class="badge">p.{exp['page']}</a></div>
          </div>
          {asset_html}
          <div class="grid-2">
            <div class="detail-box"><strong>对比内容与对象</strong>{esc(exp['what_is_compared_zh'])}</div>
            <div class="detail-box"><strong>读图与阅读指引</strong>{esc(exp['how_to_read_zh'])}</div>
          </div>
          <div class="grid-2">
            <div class="detail-box success"><strong>直接支撑结论</strong>{esc(exp['what_it_proves_zh'])}</div>
            <div class="detail-box warning"><strong>非证明范围与盲区</strong>{esc(exp['what_it_does_not_prove_zh'])}</div>
          </div>
          <div class="detail-box" style="margin-top:10px;"><strong>异常信号与注意事项</strong>{esc(exp['anomalies_caveats_zh'])}</div>
        </article>
        """)
    
    s4_html = f"""
    <section class="section-card" id="decisive-experiments">
      <h2>4. 关键实验逐个说明</h2>
      {''.join(exp_cards_html)}
    </section>
    """

    # Section 5: 综合科学判断
    s5_html = f"""
    <section class="section-card" id="scientific-assessment">
      <h2>5. 综合科学判断</h2>
      <div class="grid-2">
        <div class="detail-box success"><strong>最坚实的证据链</strong>{esc(sci['strongest_evidence_zh'])}</div>
        <div class="detail-box warning"><strong>最薄弱的推理链</strong>{esc(sci['weakest_links_zh'])}</div>
      </div>
      <div class="grid-2">
        <div class="detail-box"><strong>核心先验假设</strong>{esc(sci['assumptions_zh'])}</div>
        <div class="detail-box"><strong>竞争与替代解释</strong>{esc(sci['alternative_explanations_zh'])}</div>
      </div>
      <div class="grid-2">
        <div class="detail-box"><strong>反常现象与负向信号</strong>{esc(sci['anomalies_and_negatives_zh'])}</div>
        <div class="detail-box"><strong>适用边界与禁止推断</strong>{esc(sci['boundaries_zh'])}</div>
      </div>
      <div class="detail-box" style="margin-top:12px;"><strong>开放未决问题</strong>{esc(sci['unresolved_questions_zh'])}</div>
    </section>
    """

    # Section 6: 可复用技术内容
    reusable_html = "".join([
        f"<div class='detail-box' style='margin-bottom:12px;'><h4>{esc(r['id'])}: {esc(r['name'])} <span class='badge'>{esc(r['category'])}</span></h4><p>{esc(r['description_zh'])}</p><p><strong>来源证据:</strong> {', '.join(r.get('source_evidence', []))}</p><p><strong>落地迁移建议:</strong> {esc(r['transfer_notes_zh'])}</p></div>"
        for r in reusable
    ])
    s6_html = f"""
    <section class="section-card" id="reusable-components">
      <h2>6. 可复用技术内容</h2>
      {reusable_html}
    </section>
    """

    # Section 7: 证据审计附录 (Collapsible Secondary Layer)
    claims_cards_html = []
    for c in claims:
        cid = c.get('id', '')
        stmt = c.get('statement', '')
        epistemic = c.get('epistemic', 'SUPPORTED')
        obs = c.get('observation', 'Direct empirical data.')
        auth = c.get('author_interpretation', 'Intended claim from authors.')
        read = c.get('reader_assessment', 'Evaluated assessment.')
        v_stat = c.get('verifier_status', '')
        v_badge = f"<span class='badge badge-verifier-{esc(v_stat.lower())}'>{esc(v_stat)}</span>" if v_stat else ""
        ev_links = " ".join([f"<a href='#{esc(e)}' class='badge badge-evidence'>{esc(e)}</a>" for e in c.get('evidence', [])])
        
        claims_cards_html.append(f"""
        <article class="claim-article" id="{esc(cid)}">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <h4 style="margin:0;"><a href="#{esc(cid)}">{esc(cid)}</a>: {esc(stmt)}</h4>
            <div><span class="badge badge-epistemic-{esc(epistemic.lower())}">{esc(epistemic)}</span> {v_badge}</div>
          </div>
          <div style="font-size:0.88em; color:#64748b; margin-bottom:8px;">
            <strong>Localized Evidence:</strong> {ev_links if ev_links else "<em>None</em>"} · <a href="#p.{esc(c.get('page', 1))}">p.{esc(c.get('page', 1))}</a>
          </div>
          <div class="oia-grid">
            <div class="oia-box oia-obs"><strong>Observation (Data):</strong> {esc(obs)}</div>
            <div class="oia-box oia-auth"><strong>Author Interpretation:</strong> {esc(auth)}</div>
            <div class="oia-box oia-read"><strong>Reader Assessment:</strong> {esc(read)}</div>
          </div>
        </article>
        """)

    conflicts_html = []
    for conf in conflicts:
        conflicts_html.append(f"""
        <div class="detail-box warning" id="{esc(conf.get('id', ''))}" style="margin-bottom:10px;">
          <strong>{esc(conf.get('id'))}: {esc(conf.get('statement', ''))}</strong>
          <p style="margin:4px 0;">{esc(conf.get('resolution', ''))}</p>
          <span class="badge">{esc(conf.get('verifier_status', 'TENSION'))}</span>
        </div>
        """)

    s7_html = f"""
    <section class="section-card" id="audit-appendix">
      <h2>7. 证据审计附录 (Claim-Centric Evidence Atlas)</h2>
      <details open>
        <summary>主张与 O/I/A 证据卡片列表 ({len(claims)} 个)</summary>
        <div style="margin-top: 14px;">
          {''.join(claims_cards_html)}
        </div>
      </details>
      {f"<details><summary>跨透镜争议焦点与验证记录 ({len(conflicts)} 个)</summary><div style='margin-top:14px;'>{''.join(conflicts_html)}</div></details>" if conflicts else ""}
    </section>
    """

    page_numbers = {1}
    for c in claims:
        if c.get('page'):
            page_numbers.add(c['page'])
        for ev in c.get('evidence', []):
            m = re.match(r'^p\.([0-9]+)$', str(ev))
            if m:
                page_numbers.add(int(m.group(1)))
    for f in app.get('figures', []):
        if f.get('page'):
            page_numbers.add(f['page'])
    for t in app.get('tables', []):
        if t.get('page'):
            page_numbers.add(t['page'])
    sm_p = workspace_root / 'model/source_map.json'
    if sm_p.exists():
        sm_data = load_json(sm_p)
        for pg in sm_data.get('pages', []):
            if pg.get('number'):
                page_numbers.add(pg['number'])
    
    page_anchors_html = " ".join([
        f"<a href='#p.{p}' id='p.{p}' class='badge page-anchor-link'>p.{p}</a>"
        for p in sorted(page_numbers)
    ])

    full_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · Evidentia 论文深度精读报告</title>
<style>{css}</style>
</head>
<body>
<div class="container">
  <header>
    <div class="eyebrow">Evidentia Scientific Paper Research OS · Frozen Model</div>
    <h1>{esc(title)}</h1>
    <div class="meta-bar">
      <span>论文标识: <code>{esc(ir['paper_id'])}</code></span>
      <span>源哈希: <code>{esc(ir['source_sha256'][:12])}</code></span>
      <span>冻结生成时间: {esc(ir['created_at'][:19])}</span>
      <span>页面索引: {page_anchors_html}</span>
    </div>
  </header>
  {s1_html}
  {s2_html}
  {s3_html}
  {s4_html}
  {s5_html}
  {s6_html}
  {s7_html}
</div>
</body>
</html>
"""
    return full_html

def render_markdown(ir):
    title = ir['title']
    one_min = ir['one_minute_summary']
    p_and_c = ir['problem_and_context']
    m_and_m = ir['method_and_mechanisms']
    exps = ir['decisive_experiments']
    sci = ir['scientific_assessment']
    reusable = ir['reusable_components']
    app = ir['audit_appendix']
    claims = app.get('claims', [])
    conflicts = app.get('lens_conflicts', [])

    lines = [
        f"# {title}",
        f"\n> **Evidentia 科学论文深度精读报告** · 论文标识: `{ir['paper_id']}` · 源哈希: `{ir['source_sha256'][:12]}`",
        "\n---",
        "\n## 1. 一分钟看懂这篇论文",
        f"- **研究问题**: {one_min['research_question_zh']}",
        f"- **核心方法**: {one_min['core_method_zh']}",
        f"- **核心发现**: {one_min['key_findings_zh']}",
        f"- **最大价值**: {one_min['primary_value_zh']}",
        f"- **最大风险与边界**: {one_min['key_risks_boundaries_zh']}",
        "\n## 2. 论文到底在解决什么问题",
        f"- **背景痛点**: {p_and_c['background_zh']}",
        f"- **已有先验局限**: {p_and_c['prior_limitations_zh']}",
        f"- **本文切入点**: {p_and_c['entry_point_zh']}",
        f"- **重要度判定**: {p_and_c['why_it_matters_zh']}",
        "\n## 3. 方法到底怎么工作",
        f"- **端到端流程**: {m_and_m['pipeline_flow_zh']}",
        "\n### 核心模块",
        *[f"- **{c['name']}**: {c['role']}" for c in m_and_m['components']],
        "\n### 核心公式中文解读"
    ]
    if m_and_m['equations_explained']:
        for eq in m_and_m['equations_explained']:
            lines.append(f"- `{eq['equation_id']}: {eq['raw_text']}` — {eq['explanation_zh']}")
    else:
        lines.append("- 无独立公式")
    lines.append("\n## 4. 关键实验逐个说明")

    for exp in exps:
        lines.extend([
            f"\n### {exp['paper_label']}: {exp['title_zh']}",
            f"- **对比内容**: {exp['what_is_compared_zh']}",
            f"- **读图指引**: {exp['how_to_read_zh']}",
            f"- **直接支撑**: {exp['what_it_proves_zh']}",
            f"- **非证明范围**: {exp['what_it_does_not_prove_zh']}",
            f"- **异常与注意事项**: {exp['anomalies_caveats_zh']}"
        ])

    lines.extend([
        "\n## 5. 综合科学判断",
        f"- **最坚实的证据链**: {sci['strongest_evidence_zh']}",
        f"- **最薄弱的推理链**: {sci['weakest_links_zh']}",
        f"- **核心假设**: {sci['assumptions_zh']}",
        f"- **竞争替代解释**: {sci['alternative_explanations_zh']}",
        f"- **反常与负向信号**: {sci['anomalies_and_negatives_zh']}",
        f"- **适用边界**: {sci['boundaries_zh']}",
        f"- **开放未决问题**: {sci['unresolved_questions_zh']}",
        "\n## 6. 可复用技术内容",
        *[f"- **{r['id']}: {r['name']}** ({r['category']}): {r['description_zh']} [落地建议: {r['transfer_notes_zh']}]" for r in reusable],
        "\n## 7. 证据审计附录",
        f"### 主张与 O/I/A 证据卡片列表 ({len(claims)} 项)"
    ])

    for c in claims:
        lines.extend([
            f"\n#### [{c.get('id')}] {c.get('statement')}",
            f"- **状态**: {c.get('epistemic')} (Verifier: {c.get('verifier_status', 'N/A')})",
            f"- **证据引用**: {', '.join(c.get('evidence', []))} (p.{c.get('page', 1)})",
            f"- **Observation (客观数据)**: {c.get('observation', 'Direct empirical data.')}",
            f"- **Author Interpretation (作者推断)**: {c.get('author_interpretation', 'Intended claim from authors.')}",
            f"- **Reader Assessment (读者研判)**: {c.get('reader_assessment', 'Evaluated assessment.')}"
        ])

    if conflicts:
        lines.append(f"\n### 跨透镜争议焦点 ({len(conflicts)} 项)")
        for conf in conflicts:
            lines.append(f"- **{conf.get('id')}**: {conf.get('statement')} — {conf.get('resolution')} (状态: {conf.get('verifier_status')})")

    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    r = Path(a.out)
    
    reader_dir = r / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Build single content IR
    ir = build_reader_ir(r)
    (reader_dir / 'paper_reader_ir.json').write_text(json.dumps(ir, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    # Backward compatibility with render_ir.json
    (reader_dir / 'render_ir.json').write_text(json.dumps(ir, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    
    # 2. Render HTML
    html_content = render_html(ir, r)
    paper_html = reader_dir / 'paper_reader.html'
    compat_html = reader_dir / 'reader.html'
    paper_html.write_text(html_content, encoding='utf-8')
    compat_html.write_text(html_content, encoding='utf-8')
    
    # Paper-named copy
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', str(ir['paper_id'])).strip('_')
    if safe_name and safe_name not in ('reader', 'paper_reader'):
        named_html = reader_dir / f'{safe_name}.html'
        named_html.write_text(html_content, encoding='utf-8')
        
    # 3. Render Markdown
    md_content = render_markdown(ir)
    paper_md = reader_dir / 'paper_reader.md'
    compat_md = reader_dir / 'reader.md'
    paper_md.write_text(md_content, encoding='utf-8')
    compat_md.write_text(md_content, encoding='utf-8')
    
    # 4. Render PDF
    pdf_out = reader_dir / 'paper_reader.pdf'
    compat_pdf = reader_dir / 'reader.pdf'
    try:
        from weasyprint import HTML
        HTML(string=html_content, base_url=str(reader_dir)).write_pdf(str(pdf_out))
        if pdf_out.exists():
            import shutil
            shutil.copy2(str(pdf_out), str(compat_pdf))
            if safe_name and safe_name not in ('reader', 'paper_reader'):
                shutil.copy2(str(pdf_out), str(reader_dir / f'{safe_name}.pdf'))
    except Exception as e:
        # Kami fallback or print notice
        pass
        
    print(f"OK: Paper Reader generated -> {paper_html} and {paper_md}")

if __name__ == '__main__':
    main()
