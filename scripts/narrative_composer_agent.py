#!/usr/bin/env python3
"""Dedicated Narrative Composer Agent for Evidentia (Issue #9).

Principle: "Evidentia owns truth. AI owns narrative. Kami owns presentation."

Responsibilities:
- Synthesizes frozen models, evidence graph, source map, and six independent Lenses
  into a semantic narrative manuscript IR: reader/narrative_manuscript.json.
- Runs strictly AFTER scientific synthesis and verification.
- Strictly isolated from project Apply context (never touches apply/).
- Zero domain-specific Python fallback boilerplate (no fabricated optimizers,
  attention losses, Gaussian i.i.d. assumptions, or generic ML caveats).
- Reconstructs scientific argument in natural editorial flow.
- Synthesizes all six Lenses by scientific topic, never as disjoint mini-reports.
- Cites evidence IDs internally for every non-trivial interpretation.
"""
import argparse, json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from validate_common import load_json, schema_validate, sha256
from build_argument_reconstruction import build_argument_reconstruction

LENSES = ('author', 'reviewer', 'mechanism', 'builder', 'anomaly', 'counterfactual')
INTENTS = ('PAPER_READING', 'PAPER_TECHNICAL_EXTRACTION', 'PROJECT_APPLY')

def resolve_intent(root: Path, explicit=None) -> str:
    """Resolve an explicit output intent without reading project context."""
    intent = explicit
    state_p = root / 'run_state.json'
    if intent is None and state_p.exists():
        try:
            intent = load_json(state_p).get('intent')
        except Exception as exc:
            raise ValueError(f"cannot read run intent from {state_p}: {exc}")
    intent = (intent or 'PAPER_READING').upper()
    if intent not in INTENTS:
        raise ValueError(f"unsupported narrative intent {intent!r}; expected one of {INTENTS}")
    if intent == 'PROJECT_APPLY':
        # Apply has its own renderer and must never mutate the frozen paper reader.
        raise ValueError('PROJECT_APPLY must be rendered under apply/<project>/ by the Apply pipeline')
    return intent

def story_spine_from(arg_recon, *, question, motivation, gap, method_logic, claims, limitations, unresolved, experimental_questions=None):
    """Return a complete semantic spine while preserving explicit missing states."""
    existing = arg_recon.get('story_spine') if isinstance(arg_recon, dict) else None
    if isinstance(existing, dict):
        spine = dict(existing)
    else:
        spine = {}
    spine.setdefault('central_question', question or 'NOT_STATED')
    spine.setdefault('motivation', motivation or 'NOT_STATED')
    spine.setdefault('prior_gap', gap or 'NOT_STATED')
    spine.setdefault('central_move', method_logic or 'NOT_STATED')
    spine.setdefault('method_logic', method_logic or 'NOT_STATED')
    exp_qs = [q for q in (experimental_questions or []) if str(q).strip()] or [q.get('text', '') for q in (arg_recon.get('questions') or []) if q.get('text')] or [c.get('statement', '') for c in claims if c.get('statement')]
    spine.setdefault('experimental_questions', exp_qs or ['NOT_STATED'])
    spine.setdefault('major_findings', [c.get('statement', '') for c in claims if c.get('statement')] or ['NOT_STATED'])
    spine.setdefault('justified_conclusion', arg_recon.get('assessed_argument', {}).get('justified_thesis') or (claims[0].get('statement') if claims else 'NOT_STATED'))
    spine.setdefault('scope_and_limits', [x for x in (limitations + unresolved) if x] or ['NOT_STATED'])
    return spine

def clean_visible_narrative(value):
    """Hide internal analytical role names from the default human narrative."""
    text = str(value or '')
    replacements = {
        'Author Lens': '作者分析', 'Reviewer Lens': '证据审查',
        'Mechanism Lens': '机制分析', 'Builder Lens': '技术分析',
        'Anomaly Lens': '异常分析', 'Counterfactual Lens': '替代解释分析',
        'Author 透镜': '作者分析', 'Reviewer 透镜': '证据审查',
        'Mechanism 透镜': '机制分析', 'Builder 透镜': '技术分析',
        'Anomaly 透镜': '异常分析', 'Counterfactual 透镜': '替代解释分析',
        '跨透镜': '不同证据之间', '六大透镜': '多角度证据', '六个 Lens': '多角度证据',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.replace('Lens', '分析视角').replace('透镜', '证据视角')

def extract_lens_findings(root):
    findings_by_lens = {}
    for l in LENSES:
        lp = root / 'lens' / f'{l}.json'
        if lp.exists():
            try:
                data = load_json(lp)
                findings_by_lens[l] = data.get('findings', [])
            except Exception:
                findings_by_lens[l] = []
    return findings_by_lens

def compose_narrative_manuscript(root: Path, intent=None) -> dict:
    """Generate the semantic narrative manuscript IR from frozen paper models."""
    intent = resolve_intent(root, intent)
    # Intent isolation check: must not read or depend on apply/
    pm_path = root / 'model/paper_model.json'
    if not pm_path.exists():
        raise FileNotFoundError(f"Missing {pm_path}")
    pm = load_json(pm_path)
    
    source_sha = pm.get('source_sha256', '')
    paper_id = pm.get('paper_id', root.name)
    paper = pm.get('paper', {})
    paper_title = paper.get('title', 'Untitled Paper')
    
    # Load supporting models if present
    inv_path = root / 'model/figure_inventory.json'
    inv = load_json(inv_path) if inv_path.exists() else {}
    
    sm_path = root / 'model/source_map.json'
    sm = load_json(sm_path) if sm_path.exists() else {}
    
    syn_path = root / 'model/scientific_synthesis.json'
    syn = load_json(syn_path) if syn_path.exists() else {}
    
    rec_path = root / 'model/lens_reconciliation.json'
    rec = load_json(rec_path) if rec_path.exists() else {}
    
    arg_path = root / 'model/argument_reconstruction.json'
    if arg_path.exists():
        arg_recon = load_json(arg_path)
    else:
        try:
            arg_recon = build_argument_reconstruction(root)
        except Exception:
            arg_recon = {}
            
    lens_findings = extract_lens_findings(root)

    claims = pm.get('claims', [])
    figs = pm.get('figures', []) or [x for x in inv.get('items', []) if x.get('kind') == 'figure']
    tables = pm.get('tables', []) or [x for x in inv.get('items', []) if x.get('kind') == 'table']
    conflicts = pm.get('lens_conflicts', []) or rec.get('items', [])
    unresolved = pm.get('unresolved', [])
    assumptions = pm.get('assumptions', [])
    limitations = pm.get('limitations', [])
    anomalies = pm.get('anomalies', [])
    portable = pm.get('portable_components', [])
    evidence_roles = (arg_recon.get('evidence_promotion') or {}).get('evidence_roles', {})
    
    # Extract equations
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

    # Evidence mapping
    all_evidence_ids = set()
    for c in claims:
        all_evidence_ids.update(c.get('evidence', []))
    for f in figs:
        if f.get('id'):
            all_evidence_ids.add(f.get('id'))
    for t in tables:
        if t.get('id'):
            all_evidence_ids.add(t.get('id'))
    default_ev = sorted(list(all_evidence_ids))[:2] if all_evidence_ids else ['p.1']

    # --- Semantic story spine (paper-centric; never Lens-centric) ---
    q_first = arg_recon.get('central_question') or (pm.get('questions', [{}])[0].get('text') if pm.get('questions') else f"关于《{paper_title}》的核心科学与工程问题")
    c_first = arg_recon.get('central_thesis') or (claims[0].get('statement') if claims else 'NOT_STATED')
    
    scope_conds = arg_recon.get('scope_conditions', [])
    if scope_conds:
        boundary_summary = f"适用边界与主要约束：{'; '.join(scope_conds[:2])}。"
    elif limitations:
        boundary_summary = f"适用边界与主要约束：{limitations[0].get('text', '以论文报告的基准评测场景为准')}。"
    else:
        boundary_summary = "适用边界与主要约束：论文未明确说明额外约束，有效性范围以报告的基准实验为准。"

    ch1_takeaways = []
    if q_first:
        ch1_takeaways.append(f"核心研究问题：{q_first}")
    if claims:
        ch1_takeaways.append(f"核心实证结论：{claims[0].get('statement')}")
    nat_struct = pm.get('natural_structure', [])
    if nat_struct:
        ch1_takeaways.append(f"方法架构脉络：{' → '.join(nat_struct[:4])}")
    elif pm.get('methods'):
        ch1_takeaways.append(f"主要提出方法：{pm['methods'][0].get('name', '核心算法设计')}")
    ch1_takeaways.append(boundary_summary)

    exp_questions = []
    for exp in pm.get('experiments', []):
        if isinstance(exp, dict) and (exp.get('question') or exp.get('name')):
            exp_questions.append(exp.get('question') or exp.get('name'))
        elif isinstance(exp, str) and exp.strip():
            exp_questions.append(exp.strip())
    if not exp_questions:
        for q in pm.get('questions', []):
            if isinstance(q, dict) and q.get('text'):
                exp_questions.append(q['text'])
            elif isinstance(q, str) and q.strip():
                exp_questions.append(q.strip())

    method_logic = ' → '.join(nat_struct[:6]) if nat_struct else (methods_list[0].get('description', '') if (methods_list := pm.get('methods', [])) else '')
    story_spine = story_spine_from(
        arg_recon,
        question=q_first,
        motivation=arg_recon.get('motivation', ''),
        gap=arg_recon.get('prior_assumptions_or_gap', ''),
        method_logic=method_logic,
        claims=claims,
        limitations=[l.get('text', '') for l in limitations if isinstance(l, dict)],
        unresolved=[u.get('issue', '') for u in unresolved if isinstance(u, dict)],
        experimental_questions=exp_questions
    )

    # --- Chapter 1: 一分钟理解这篇论文 ---
    ch1_blocks = [
        {
            "type": "paragraph",
            "text": f"本文围绕“{story_spine['central_question']}”展开。研究切入点是：{story_spine['motivation']} 核心方法/主张是：{story_spine['central_move']} 实验结果显示：{c_first}",
            "evidence_refs": claims[0].get('evidence', default_ev) if claims else default_ev,
            "argument_refs": ["ARG-01"] if "ARG-01" in [u.get('id') for u in arg_recon.get('argument_units', [])] else []
        },
        {
            "type": "takeaway",
            "text": f"这篇论文的中心推进是：{story_spine['central_move']} 其证据边界是：{boundary_summary}",
            "evidence_refs": claims[0].get('evidence', default_ev) if claims else default_ev
        },
        {
            "type": "callout",
            "text": "【研读导读】下文按问题、方法、实验和结论的关系展开；源材料未支持的环节会保留为未说明或未决状态。",
            "evidence_refs": []
        }
    ]

    # --- Chapter 2: 论文为什么要做这件事 ---
    motivation = story_spine.get('motivation') or 'NOT_STATED'
    gap = story_spine.get('prior_gap') or 'NOT_STATED'
    entry_point = story_spine.get('central_move') or 'NOT_STATED'
    why_matters = arg_recon.get('why_it_matters') or 'NOT_STATED'

    ch2_blocks = [
        {
            "type": "paragraph",
            "text": f"【研究背景与动机】{motivation}",
            "evidence_refs": ["p.1"]
        },
        {
            "type": "paragraph",
            "text": f"【既有局限与科学缺口】{gap}",
            "evidence_refs": ["p.1"]
        },
        {
            "type": "callout",
            "text": f"本文核心切入点：{entry_point}",
            "evidence_refs": []
        },
        {
            "type": "paragraph",
            "text": f"【研究意义】{why_matters}",
            "evidence_refs": []
        }
    ]

    # --- Chapter 3: 方法是怎么工作的 ---
    ch3_blocks = []
    methods_list = pm.get('methods', [])
    if methods_list:
        m_desc_items = []
        for m in methods_list:
            m_desc_items.append(f"**{m.get('name', '核心模块')}**：{m.get('description') or 'NOT_STATED'}")
        ch3_blocks.append({
            "type": "paragraph",
            "text": f"作者提出的整体方法由多个核心组件构成：\n" + "\n".join(f"- {it}" for it in m_desc_items),
            "evidence_refs": default_ev
        })
    elif nat_struct:
        ch3_blocks.append({
            "type": "paragraph",
            "text": f"根据论文展开脉络，核心方法沿以下计算流推进：{' → '.join(nat_struct)}。各阶段紧密衔接，共同支撑最终实证主张。",
            "evidence_refs": default_ev
        })
    else:
        ch3_blocks.append({
            "type": "paragraph",
            "text": "【方法结构】源材料未提供可进一步拆分的方法组件；请以原文方法段落和页面证据为准。",
            "evidence_refs": default_ev
        })

    # Integrate system / workflow figures inline into Chapter 3 if available
    system_figs = [f for f in figs if evidence_roles.get(f.get('id')) not in ('audit_only', 'uncertain') and (f.get('role') in ('critical', 'architecture', 'overview') or '流程' in f.get('caption_original', '') or 'Figure 1' in f.get('paper_label', ''))]
    if not system_figs and figs:
        promotable = [f for f in figs if evidence_roles.get(f.get('id'), 'narrative_support') in ('narrative_core', 'narrative_support')]
        system_figs = promotable[:1]
    for sf in system_figs[:1]:
        sf_id = sf.get('id', 'F01')
        ch3_blocks.append({
            "type": "figure",
            "evidence_id": sf_id,
            "asset": sf.get('file') or sf.get('asset'),
            "caption": f"{sf.get('paper_label', sf_id)}: {sf.get('caption_original', '方法整体架构与工作流示意图')}",
            "analysis": sf.get('author_interpretation') or sf.get('observation') or "源材料未提供可核验的图内解释。",
            "evidence_refs": [sf_id],
            "presentation_role": evidence_roles.get(sf_id, 'narrative_support'),
            "question": sf.get('question') or "该架构图如何支撑核心方法的数据流与处理逻辑？",
            "supports": sf.get('supports_claims') or (claims and [claims[0].get('id', 'C01')]) or ['NOT_STATED'],
            "limits": sf.get('limitations') or ['NOT_STATED']
        })

    # Integrate equations into Chapter 3
    for eq in equations[:3]:
        if not eq.get('latex') and not eq.get('fallback_asset'):
            # Unverified OCR/text extraction remains in the source map, not main narrative.
            continue
        raw_eq = eq.get('raw_text') or eq.get('latex') or ''
        ch3_blocks.append({
            "type": "equation",
            "evidence_id": eq.get('equation_id', 'EQ'),
            "raw_text": raw_eq,
            "explanation": eq.get('role_zh') or eq.get('surrounding_text') or "源材料未提供该公式的完整语义说明。",
            "latex": eq.get('latex'),
            "display_mode": bool(eq.get('display_mode', True)),
            "source_confidence": eq.get('source_confidence') or ('VERIFIED' if eq.get('latex') else 'UNCERTAIN'),
            "fallback_asset": eq.get('fallback_asset'),
            "evidence_refs": [eq.get('equation_id', 'EQ'), f"p.{eq.get('page', 1)}"]
        })

    if assumptions:
        assump_texts = [a.get('text', '') for a in assumptions if a.get('text')]
        ch3_blocks.append({
            "type": "callout",
            "text": f"【理论前提与假设】方法有效性依赖如下前提：{'; '.join(assump_texts)}。",
            "evidence_refs": default_ev
        })

    # --- Chapter 4: 哪些实验真正决定了论文是否成立 ---
    ch4_blocks = [
        {
            "type": "paragraph",
            "text": "科学评估的核心在于辨析决定论文结论真伪的关键实验。下述实验与图表构成了论文最主要的实证支柱：",
            "evidence_refs": default_ev
        }
    ]

    # Decisive experiments from argument reconstruction or figs/tables
    decisive_items = []
    for f in figs:
        if evidence_roles.get(f.get('id'), 'narrative_support') in ('narrative_core', 'narrative_support'):
            decisive_items.append(('figure', f))
    for t in tables:
        if evidence_roles.get(t.get('id'), 'narrative_support') in ('narrative_core', 'narrative_support'):
            decisive_items.append(('table', t))
    
    if not decisive_items:
        ch4_blocks.append({
            "type": "paragraph",
            "text": "当前模型未提取到可独立呈现的图表资产；正文证据仍保留在页面锚点和主张卡片中。",
            "evidence_refs": default_ev
        })
    else:
        for kind, item in decisive_items[:3]:
            iid = item.get('id', '')
            label = item.get('paper_label', iid)
            cap = item.get('caption_original', '实证评测结果')
            obs = item.get('observation') or "源材料未提供可核验的客观观测说明。"
            auth = item.get('author_interpretation') or "源材料未提供作者解释。"
            read = item.get('reader_assessment') or "当前证据不足以给出独立研判。"
            
            analysis_text = f"**实证观测 (Observation)**：{obs}\n\n**作者推断 (Author Interpretation)**：{auth}\n\n**读者研判 (Reader Assessment)**：{read}"
            
            if kind == 'figure':
                ch4_blocks.append({
                    "type": "figure",
                    "evidence_id": iid,
                    "asset": item.get('file') or item.get('asset'),
                    "caption": f"{label}: {cap}",
                    "analysis": analysis_text,
                    "evidence_refs": [iid] + item.get('supports_claims', []),
                    "presentation_role": evidence_roles.get(iid, 'narrative_support'),
                    "question": item.get('question') or "这个实验在检验什么核心问题？",
                    "supports": item.get('supports_claims') or (claims and [claims[0].get('id', 'C01')]) or ['NOT_STATED'],
                    "limits": item.get('limitations') or ['NOT_STATED']
                })
            else:
                ch4_blocks.append({
                    "type": "table",
                    "evidence_id": iid,
                    "asset": item.get('file') or item.get('asset'),
                    "caption": f"{label}: {cap}",
                    "analysis": analysis_text,
                    "evidence_refs": [iid] + item.get('supports_claims', []),
                    "presentation_role": evidence_roles.get(iid, 'narrative_support'),
                    "question": item.get('question') or "该定量评测检验什么核心指标与主张？",
                    "supports": item.get('supports_claims') or (claims and [claims[0].get('id', 'C01')]) or ['NOT_STATED'],
                    "limits": item.get('limitations') or ['NOT_STATED']
                })

    # --- Chapter 5: 证据最终支持了什么 ---
    ch5_blocks = [
        {
            "type": "paragraph",
            "text": "本节把实验结果、解释、替代解释和适用边界放回同一条科学论证链，回答证据到底支持了什么。",
            "evidence_refs": default_ev
        },
        {
            "type": "paragraph",
            "text": f"【证据支持的结论】{story_spine['justified_conclusion']}",
            "evidence_refs": default_ev
        }
    ]

    syn_topics = syn.get('topics', [])
    if syn_topics:
        for top in syn_topics:
            t_title = clean_visible_narrative(top.get('title_zh', '科学议题审视'))
            t_concl = clean_visible_narrative(top.get('core_conclusion_zh', ''))
            t_ev = top.get('evidence_refs', default_ev)
            t_mech = clean_visible_narrative(top.get('mechanism_zh'))
            t_rev = clean_visible_narrative(top.get('reviewer_caveat_zh'))
            t_ano = clean_visible_narrative(top.get('anomaly_zh'))
            t_alt = clean_visible_narrative(top.get('alternative_explanation_zh'))
            
            topic_narrative = [f"**{t_title}**", t_concl]
            if t_mech:
                topic_narrative.append(f"- **机制解释**：{t_mech}")
            if t_rev:
                topic_narrative.append(f"- **证据限制**：{t_rev}")
            if t_ano:
                topic_narrative.append(f"- **反常与负例**：{t_ano}")
            if t_alt:
                topic_narrative.append(f"- **替代解释**：{t_alt}")
                
            ch5_blocks.append({
                "type": "callout" if top.get('confidence') in ('PARTIAL', 'LOW', 'TENSION') else "paragraph",
                "text": "\n\n".join(topic_narrative),
                "evidence_refs": t_ev
            })
    else:
        # Dynamic cross-lens synthesis when scientific_synthesis artifact is light
        core_claim_stmt = claims[0].get('statement') if claims else '核心主张'
        ch5_blocks.append({
            "type": "paragraph",
            "text": f"【核心主张有效性综合审视】围绕主张“{core_claim_stmt}”，当前证据支持范围以已报告的实验条件为准；未测试场景的证据强度仍未确定。",
            "evidence_refs": default_ev
        })
        if anomalies:
            anom_text = "; ".join(a.get('text', '') for a in anomalies[:2])
            ch5_blocks.append({
                "type": "callout",
                "text": f"【反常现象与负例】{anom_text}",
                "evidence_refs": default_ev
            })
        else:
            ch5_blocks.append({
                "type": "paragraph",
                "text": "【反常与边界】当前材料未报告可核验的显著反常负例；这不等同于已证明不存在反常。",
                "evidence_refs": default_ev
            })

    # --- Optional technical extraction (explicit intent only) ---
    ch6_blocks = [
        {
            "type": "paragraph",
            "text": "从论文技术结构视角，提取论文中描述完整、具备明确输入输出的技术实现细节：",
            "evidence_refs": default_ev
        }
    ]

    if portable:
        for p_item in portable:
            p_name = p_item.get('name', '技术组件')
            p_io = p_item.get('io', '数据输入输出契约')
            p_src = p_item.get('source', default_ev)
            p_notes = clean_visible_narrative(p_item.get('description_zh') or p_item.get('description') or p_item.get('transfer_notes') or '论文未提供额外实现说明。')
            ch6_blocks.append({
                "type": "callout",
                "text": f"**{p_name}**\n- **I/O 契约**: {p_io}\n- **来源依据**: {', '.join(p_src)}\n- **技术实现说明**: {p_notes}",
                "evidence_refs": p_src
            })
    else:
        ch6_blocks.append({
            "type": "paragraph",
            "text": "当前证据未确认可独立拆分的技术组件；论文没有提供可独立提取的组件边界。",
            "evidence_refs": default_ev
        })

    # --- Chapter 7: 结论与边界 ---
    established_points = [c.get('statement') for c in claims if c.get('epistemic') in ('SUPPORTED', 'VERIFIED')]
    if not established_points and claims:
        established_points = [claims[0].get('statement')]
    
    unproven_points = []
    if limitations:
        unproven_points.extend([l.get('text') for l in limitations if l.get('text')])
    if unresolved:
        unproven_points.extend([u.get('issue') for u in unresolved if u.get('issue')])
    if not unproven_points:
        unproven_points = ["未在当前证据中确认超出基准范围的外推泛化性能。"]

    concl_text = "【已确立的科学事实】\n" + "\n".join(f"- {p}" for p in established_points) + "\n\n【未验证边界与开放问题】\n" + "\n".join(f"- {u}" for u in unproven_points)
    ch7_blocks = [
        {
            "type": "paragraph",
            "text": concl_text,
            "evidence_refs": default_ev
        },
        {
            "type": "takeaway",
            "text": f"【总结】《{paper_title}》在所设定的基准评测下得到上述结果；对未报告场景的结论仍需保持未决。",
            "evidence_refs": default_ev
        }
    ]

    chapters = [
        {
            "id": "one_minute",
            "chapter_num": "01",
            "title": "一分钟看懂这篇论文",
            "lead": "快速全景概览：科学问题、核心突破、实证结论与边界约束。",
            "blocks": ch1_blocks
        },
        {
            "id": "problem",
            "chapter_num": "02",
            "title": "论文到底在解决什么问题",
            "lead": "追溯研究脉络，厘清既有方案的科学局限与本文的切入动因。",
            "blocks": ch2_blocks
        },
        {
            "id": "method",
            "chapter_num": "03",
            "title": "方法到底怎么工作",
            "lead": "深入端到端工作机制，拆解算法流程、核心公式与理论假设。",
            "blocks": ch3_blocks
        },
        {
            "id": "experiments",
            "chapter_num": "04",
            "title": "关键实验逐个说明",
            "lead": "聚焦关键图表与基准对比，客观审视实证数据对主张的支撑强度。",
            "blocks": ch4_blocks
        },
        {
            "id": "synthesis",
            "chapter_num": "05",
            "title": "证据最终支持了什么",
            "lead": "把证据、解释、替代解释与边界放回论文自身的科学论证链。",
            "blocks": ch5_blocks
        },
        {
            "id": "conclusions",
            "chapter_num": "06",
            "title": "结论与边界",
            "lead": "总结论文已经建立的结论、适用边界与仍未解决的问题。",
            "blocks": ch7_blocks
        }
    ]

    if intent == 'PAPER_TECHNICAL_EXTRACTION':
        chapters.insert(-1, {
            "id": "technical_extraction",
            "chapter_num": str(len(chapters) + 1).zfill(2),
            "title": "论文技术细节提取",
            "lead": "仅整理论文明确给出的算法、输入输出与实验设置；严格局限于论文自身技术范围。",
            "blocks": ch6_blocks
        })

    meta_authors = paper.get('authors', [])
    if isinstance(meta_authors, str):
        meta_authors = [meta_authors]
        
    manuscript = {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "source_sha256": source_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "document": {
            "title": paper_title,
            "subtitle": "Evidentia 深度科学研读与证据重构报告",
            "paper_meta": {
                "authors": meta_authors,
                "venue": paper.get('venue', ''),
                "year": paper.get('year', 2026),
                "doi": paper.get('doi', ''),
                "pdf_sha256": source_sha
            },
            "executive_summary": {
                "lead": f"《{paper_title}》聚焦于“{q_first}”。{c_first}",
                "takeaways": ch1_takeaways,
                "key_question": q_first,
                "core_finding": c_first,
                "core_boundary": boundary_summary
            },
            "story_spine": story_spine,
            "chapters": chapters,
            "appendix_summary": {
                "claims_count": len(claims),
                "figures_count": len(figs),
                "tables_count": len(tables),
                "conflicts_count": len(conflicts),
                "unresolved_count": len(unresolved),
                "evidence_atlas_ref": "evidence_atlas.html"
            }
        }
    }

    errs = schema_validate(manuscript, 'narrative_manuscript')
    if errs:
        raise ValueError(f"narrative_manuscript schema validation failed: {errs}")

    return manuscript

def main():
    ap = argparse.ArgumentParser(description="Compose semantic narrative manuscript IR.")
    ap.add_argument('--out', required=True, help="Workspace run directory containing model/")
    ap.add_argument('--intent', choices=INTENTS, default=None, help="Explicit paper output intent; default follows run_state or PAPER_READING")
    args = ap.parse_args()
    root = Path(args.out)
    
    manuscript = compose_narrative_manuscript(root, intent=args.intent)
    reader_dir = root / 'reader'
    reader_dir.mkdir(parents=True, exist_ok=True)
    out_file = reader_dir / 'narrative_manuscript.json'
    out_file.write_text(json.dumps(manuscript, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OK: Composed narrative manuscript -> {out_file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
