#!/usr/bin/env python3
"""Compose the human Paper Reader from the paper's reconstructed argument.

The composer is paper-centric. It consumes frozen paper truth, the reconstructed
argument, Council synthesis, and promoted evidence, then writes a semantic
manuscript whose section titles and order follow that paper rather than a
pipeline dashboard. Audit roles remain in the Evidence Atlas.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_router import INTENTS
from lens_council import load_council
from validate_common import load_json, schema_validate

UNCERTAIN = "论文未明确说明"


def resolve_intent(root: Path, explicit=None) -> str:
    intent = explicit
    state_p = root / "run_state.json"
    if intent is None and state_p.exists():
        try:
            intent = load_json(state_p).get("intent")
        except Exception as exc:
            raise ValueError(f"cannot read run intent from {state_p}: {exc}") from exc
    intent = (intent or "PAPER_READING").upper()
    if intent not in INTENTS:
        raise ValueError(f"unsupported narrative intent {intent!r}; expected one of {INTENTS}")
    if intent == "PROJECT_APPLY":
        raise ValueError("PROJECT_APPLY must be rendered under apply/<project>/ by the Apply pipeline")
    if intent == "MEMORY_OPERATION":
        raise ValueError("MEMORY_OPERATION is managed by evidentia memory command")
    return intent


def clean_visible_narrative(value):
    """Remove internal role vocabulary from text supplied by analytical agents."""
    text = str(value or "")
    replacements = {
        "Author Lens": "作者的解释", "Reviewer Lens": "证据审查",
        "Mechanism Lens": "机制解释", "Builder Lens": "方法细节",
        "Anomaly Lens": "异常现象", "Counterfactual Lens": "替代解释",
        "Author 透镜": "作者的解释", "Reviewer 透镜": "证据审查",
        "Mechanism 透镜": "机制解释", "Builder 透镜": "方法细节",
        "Anomaly 透镜": "异常现象", "Counterfactual 透镜": "替代解释",
        "跨透镜": "不同证据之间", "六大透镜": "多角度证据", "六个 Lens": "多角度证据",
        "Observation": "直接观测", "Author Interpretation": "作者解释",
        "Reader Assessment": "证据研判", "O/I/A": "证据层次",
        "claim-card": "证据项", "Supports Claims": "支撑关系",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.replace("Lens", "分析视角").replace("透镜", "证据视角")


def _clean(value, fallback=UNCERTAIN):
    value = clean_visible_narrative(value).strip()
    return value if value else fallback


def _clause(value, fallback=UNCERTAIN):
    """Use source text as a clause without stacking terminal punctuation."""
    return _clean(value, fallback).rstrip("。！？；： ")


def _items(value):
    return value if isinstance(value, list) else []


def _first_text(values, fallback=UNCERTAIN):
    for value in values:
        if isinstance(value, dict):
            value = value.get("text") or value.get("statement") or value.get("proposition")
        if str(value or "").strip():
            return _clean(value)
    return fallback


def _truncate(text, limit=18):
    text = _clean(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip("，。；： ") + "…"


def story_spine_from(arg_recon, *, question, motivation, gap, method_logic,
                     claims, limitations, unresolved, experimental_questions=None):
    """Return a complete paper-specific spine while preserving missing states."""
    existing = arg_recon.get("story_spine") if isinstance(arg_recon, dict) else None
    spine = dict(existing) if isinstance(existing, dict) else {}
    # Older argument-reconstruction artifacts stored story-spine sections as
    # title strings.  The current manuscript contract requires section
    # objects, so normalize that legacy form at the boundary before the spine
    # is embedded in the rendered manuscript.
    raw_sections = spine.get("sections")
    if isinstance(raw_sections, list):
        normalized_sections = []
        for idx, item in enumerate(raw_sections, 1):
            if isinstance(item, str):
                normalized_sections.append({
                    "id": f"spine-{idx:02d}",
                    "title": item,
                    "lead": item,
                    "blocks": [],
                })
            elif isinstance(item, dict):
                normalized_sections.append(item)
        spine["sections"] = normalized_sections
    spine.setdefault("central_question", _clean(question))
    spine.setdefault("motivation", _clean(motivation))
    spine.setdefault("prior_gap", _clean(gap))
    spine.setdefault("central_move", _clean(method_logic))
    spine.setdefault("method_logic", _clean(method_logic))
    qs = [str(q).strip() for q in (experimental_questions or []) if str(q).strip()]
    if not qs:
        qs = [_clean(q.get("text")) for q in _items(arg_recon.get("questions")) if isinstance(q, dict) and q.get("text")]
    if not qs:
        qs = [_clean(c.get("statement")) for c in claims if c.get("statement")]
    spine.setdefault("experimental_questions", qs or [UNCERTAIN])
    spine.setdefault("major_findings", [_clean(c.get("statement")) for c in claims if c.get("statement")] or [UNCERTAIN])
    assessed = arg_recon.get("assessed_argument") if isinstance(arg_recon, dict) else {}
    spine.setdefault("justified_conclusion", _clean((assessed or {}).get("justified_thesis") or (claims[0].get("statement") if claims else "")))
    limits = [_clean(x) for x in limitations + unresolved if str(x or "").strip()]
    spine.setdefault("scope_and_limits", limits or [UNCERTAIN])
    return spine


def _evidence_roles(arg_recon):
    promo = arg_recon.get("evidence_promotion") if isinstance(arg_recon, dict) else {}
    return (promo or {}).get("evidence_roles", {}) if isinstance(promo, dict) else {}


def _merge_evidence_items(items, inventory_items, kind):
    """Fill presentation fields from the canonical inventory without inventing data."""
    inv_by_id = {
        str(item.get("id")): item for item in _items(inventory_items)
        if isinstance(item, dict) and item.get("id") and item.get("kind") in (kind, None)
    }
    merged = []
    seen = set()
    for item in _items(items):
        if not isinstance(item, dict):
            continue
        eid = str(item.get("id") or "")
        base = dict(inv_by_id.get(eid, {}))
        base.update(item)
        if not base.get("file"):
            base["file"] = base.get("asset") or base.get("raw_visual_fallback")
        merged.append(base)
        if eid:
            seen.add(eid)
    for eid, item in inv_by_id.items():
        if eid not in seen:
            base = dict(item)
            base.setdefault("file", base.get("asset") or base.get("raw_visual_fallback"))
            merged.append(base)
    return merged


def _default_refs(claims, figs, tables):
    refs = []
    if claims:
        refs.extend(claims[0].get("evidence", []))
    if not refs and figs:
        refs.append(figs[0].get("id"))
    if not refs and tables:
        refs.append(tables[0].get("id"))
    return [str(x) for x in refs if x] or ["p.1"]


def _figure_block(item, claims, roles, *, question=None, section_refs=None):
    eid = item.get("id") or item.get("paper_label") or "figure"
    claim_ids = item.get("supports_claims") or []
    observation = _clean(item.get("observation"))
    author = _clean(item.get("author_interpretation"))
    assessment = _clean(item.get("reader_assessment"))
    analysis = f"图中直接呈现：{_clause(observation)}。作者将这一结果解释为：{_clause(author)}。结合现有证据，可以确认到的范围是：{_clause(assessment)}。"
    limits = item.get("limitations") or [UNCERTAIN]
    return {
        "type": "figure", "evidence_id": str(eid),
        "asset": item.get("file") or item.get("asset"),
        "caption": _clean(item.get("caption_original") or item.get("paper_label") or eid),
        "analysis": analysis,
        "evidence_refs": list(dict.fromkeys([str(eid)] + list(section_refs or []) + [str(x) for x in claim_ids if x])),
        "question": _clean(question or item.get("question"), "论文用这一图表检验什么问题？"),
        "supports": [str(x) for x in claim_ids if x] or ["NOT_STATED"],
        "limits": [_clean(x) for x in limits],
        "presentation_role": roles.get(eid, "narrative_support"),
    }


def _table_block(item, claims, roles, *, question=None, section_refs=None):
    block = _figure_block(item, claims, roles, question=question, section_refs=section_refs)
    block["type"] = "table"
    return block


def _equation_blocks(source_map):
    result = []
    for page in _items(source_map.get("pages")):
        for eq in _items(page.get("equations")):
            if isinstance(eq, str):
                eq = {"equation_id": f"EQ-p{page.get('number', 1)}-{len(result)+1}", "raw_text": eq}
            # Keep an unrenderable equation as an explicit block.  The release
            # gate will reject it unless a verified LaTeX source or a decodable
            # source crop is available; silently dropping it would hide a core
            # extraction failure.
            if not isinstance(eq, dict):
                continue
            if eq.get("display_mode") is False and not eq.get("latex") and not eq.get("fallback_asset"):
                continue
            eid = eq.get("equation_id") or f"EQ-{len(result)+1}"
            result.append({
                "type": "equation", "evidence_id": str(eid),
                "raw_text": eq.get("raw_text") or eq.get("latex") or "",
                "latex": eq.get("latex"), "display_mode": bool(eq.get("display_mode", True)),
                "source_confidence": eq.get("source_confidence") or "UNCERTAIN",
                "fallback_asset": eq.get("fallback_asset"),
                "explanation": _clean(eq.get("role_zh") or eq.get("surrounding_text")),
                "evidence_refs": [f"p.{eq.get('page', page.get('number', 1))}"],
            })
    return result


def _custom_sections(spine):
    custom = spine.get("sections") or spine.get("narrative_sections") or spine.get("nodes")
    if not isinstance(custom, list):
        return []
    # A legacy spine may contain only section-title strings.  Those titles are
    # structural hints, not complete narrative sections; let the paper-aware
    # derivation below build evidence-bearing sections instead.
    if custom and not any(isinstance(item, dict) for item in custom):
        return []
    out = []
    for idx, item in enumerate(custom, 1):
        if isinstance(item, str):
            out.append({"id": f"spine-{idx:02d}", "title": item, "lead": item, "blocks": []})
        elif isinstance(item, dict):
            out.append({
                "id": item.get("id") or f"spine-{idx:02d}",
                "title": _clean(item.get("title") or item.get("heading") or item.get("proposition"), f"论证节点 {idx}"),
                "lead": _clean(item.get("lead") or item.get("summary") or item.get("proposition")),
                "blocks": item.get("blocks") if isinstance(item.get("blocks"), list) else [],
                "argument_refs": item.get("argument_refs", []), "evidence_refs": item.get("evidence_refs", []),
            })
    return out


def _derived_sections(pm, arg_recon, spine, claims, figs, tables, source_map, roles, default_refs):
    """Derive sections from this paper's argument units and evidence."""
    sections = []
    units = _items(arg_recon.get("argument_units"))
    methods = _items(pm.get("methods"))
    question = _clean(spine.get("central_question")); motivation = _clean(spine.get("motivation"))
    move = _clean(spine.get("central_move")); logic = _clean(spine.get("method_logic"))
    sections.append({
        "id": "spine-01", "title": f"研究问题：{_truncate(question)}",
        "lead": f"{motivation} 这篇论文试图回答这一问题，并将判断交给后续方法与证据。",
        "blocks": [
            {"type": "paragraph", "text": f"{_clause(question)}。{_clause(motivation)}。", "evidence_refs": default_refs},
            {"type": "paragraph", "text": f"论文的核心推进是{_clause(move)}；作者把它组织成{_clause(logic)}。", "evidence_refs": default_refs},
        ],
    })
    method_text = [_clean(m.get("description")) for m in methods if m.get("description")]
    if not method_text and logic and logic != UNCERTAIN:
        method_text.append(logic)
    method_text = [x for x in method_text if x and x != UNCERTAIN]
    method_sentence = "；".join(_clause(x) for x in method_text) if method_text else UNCERTAIN
    method_blocks = [{"type": "paragraph", "text": f"方法沿着论文给出的顺序展开：{_clause(method_sentence)}。", "evidence_refs": default_refs}]
    claim_evidence = {str(e) for c in claims for e in c.get("evidence", [])}
    method_figs = [f for f in figs if roles.get(f.get("id"), "narrative_support") in ("narrative_core", "narrative_support") and str(f.get("id")) not in claim_evidence]
    for figure in method_figs:
        method_blocks.append(_figure_block(figure, claims, roles, question="这张图如何把核心方法连接起来？", section_refs=default_refs))
    method_tables = [t for t in tables if roles.get(t.get("id"), "narrative_support") in ("narrative_core", "narrative_support") and str(t.get("id")) not in claim_evidence]
    for table in method_tables:
        method_blocks.append(_table_block(table, claims, roles, question="这张表如何把核心方法连接起来？", section_refs=default_refs))
    method_blocks.extend(_equation_blocks(source_map))
    sections.append({"id": "spine-02", "title": f"研究路径：{_truncate(move)}", "lead": "这里说明作者如何把研究问题转成可执行的方法，并指出方法依赖的前提。", "blocks": method_blocks})

    for idx, claim in enumerate(claims, 1):
        cid = claim.get("id") or f"claim-{idx}"; ev = [str(x) for x in claim.get("evidence", []) if x]
        q_list = spine.get("experimental_questions") or [UNCERTAIN]; q_text = q_list[min(idx - 1, len(q_list) - 1)]
        blocks = [{"type": "paragraph", "text": f"这项实验关注“{_clause(q_text)}”。结果是：{_clause(claim.get('observation') or claim.get('statement'))}。作者据此认为：{_clause(claim.get('author_interpretation'))}。从当前材料可以确认：{_clause(claim.get('reader_assessment'))}。", "evidence_refs": ev or default_refs, "argument_refs": [u.get("id") for u in units if cid in _items(u.get("linked_claim_ids"))]}]
        for item in figs + tables:
            if item.get("id") in ev or cid in _items(item.get("supports_claims")):
                block = _table_block(item, claims, roles, question=q_text, section_refs=ev) if item in tables else _figure_block(item, claims, roles, question=q_text, section_refs=ev)
                blocks.append(block)
        sections.append({"id": f"spine-{len(sections)+1:02d}", "title": f"关键结果：{_truncate(claim.get('statement') or cid)}", "lead": "这一组结果决定了论文主张在当前实验条件下能成立到什么程度。", "blocks": blocks})
    return sections


def compose_narrative_manuscript(root: Path, intent=None) -> dict:
    intent = resolve_intent(root, intent)
    pm_path = root / "model/paper_model.json"
    if not pm_path.exists():
        raise FileNotFoundError(f"Missing {pm_path}")
    pm = load_json(pm_path)
    inv = load_json(root / "model/figure_inventory.json") if (root / "model/figure_inventory.json").exists() else {}
    source_map = load_json(root / "model/source_map.json") if (root / "model/source_map.json").exists() else {}
    synthesis = load_json(root / "model/scientific_synthesis.json") if (root / "model/scientific_synthesis.json").exists() else {}
    council = load_council(root, allow_compat=not (root / "model/frozen_evidence_package.json").exists())
    arg_recon = load_json(root / "model/argument_reconstruction.json") if (root / "model/argument_reconstruction.json").exists() else (pm.get("argument_reconstruction") or {})
    claims = _items(pm.get("claims"))
    inv_items = _items(inv.get("items"))
    figs = _merge_evidence_items(pm.get("figures"), inv_items, "figure")
    tables = _merge_evidence_items(pm.get("tables"), inv_items, "table")
    limitations = [_clean(x.get("text")) for x in _items(pm.get("limitations")) if isinstance(x, dict) and x.get("text")]; unresolved = [_clean(x.get("issue")) for x in _items(pm.get("unresolved")) if isinstance(x, dict) and x.get("issue")]
    anomalies = [_clean(x.get("text") or x.get("description") or x.get("issue")) for x in _items(pm.get("anomalies")) if isinstance(x, dict) and (x.get("text") or x.get("description") or x.get("issue"))]
    methods = _items(pm.get("methods")); natural = [str(x) for x in _items(pm.get("natural_structure")) if str(x).strip()]; method_logic = " → ".join(natural) or _first_text([m.get("description") for m in methods])
    questions = [q.get("question") or q.get("name") for q in _items(pm.get("experiments")) if isinstance(q, dict) and (q.get("question") or q.get("name"))]; questions += [q.get("text") for q in _items(pm.get("questions")) if isinstance(q, dict) and q.get("text")]
    paper = pm.get("paper") or {}; title = _clean(paper.get("title"), "未命名论文")
    question = _first_text([arg_recon.get("central_question"), *[q.get("text") for q in _items(pm.get("questions")) if isinstance(q, dict)]])
    spine = story_spine_from(arg_recon, question=question, motivation=arg_recon.get("motivation"), gap=arg_recon.get("prior_assumptions_or_gap"), method_logic=method_logic, claims=claims, limitations=limitations, unresolved=unresolved, experimental_questions=questions)
    roles = _evidence_roles(arg_recon); default_refs = _default_refs(claims, figs, tables)
    sections = _custom_sections(spine) or _derived_sections(pm, arg_recon, spine, claims, figs, tables, source_map, roles, default_refs)

    # A custom paper spine may omit evidence blocks. Add a local evidence
    # section for every promoted figure/table that is otherwise absent.
    present_ids = {
        str(block.get("evidence_id"))
        for section in sections for block in _items(section.get("blocks"))
        if block.get("type") in ("figure", "table") and block.get("evidence_id")
    }
    promoted = [eid for eid, role in roles.items() if role in ("narrative_core", "narrative_support")]
    missing_blocks = []
    for eid in promoted:
        if str(eid) in present_ids:
            continue
        item = next((x for x in figs + tables if str(x.get("id")) == str(eid)), None)
        if item is None:
            continue
        block = (_table_block(item, claims, roles, question="论文用这一证据检验什么问题？", section_refs=[str(eid)])
                 if item in tables else
                 _figure_block(item, claims, roles, question="论文用这一证据检验什么问题？", section_refs=[str(eid)]))
        missing_blocks.append(block)
    if missing_blocks:
        sections.append({"id": f"spine-{len(sections)+1:02d}", "title": "关键证据与局部核验", "lead": "以下证据在论文的主张结构中被提升为正文材料，并在此处逐项说明其作用与边界。", "blocks": missing_blocks})
    present_equations = {
        str(block.get("evidence_id"))
        for section in sections for block in _items(section.get("blocks"))
        if block.get("type") == "equation" and block.get("evidence_id")
    }
    missing_equations = [block for block in _equation_blocks(source_map)
                         if str(block.get("evidence_id")) not in present_equations]
    if missing_equations:
        sections.append({"id": f"spine-{len(sections)+1:02d}", "title": "公式与推导", "lead": "公式保留原始来源状态；无法可靠重建的内容会在验收时明确标记。", "blocks": missing_equations})

    # Keep every extracted figure/table addressable in the rendered Reader.
    # Evidence promotion controls narrative emphasis, but omitting an
    # audit-only asset breaks provenance links from synthesized claims.
    present_visual_ids = {
        str(block.get("evidence_id"))
        for section in sections for block in _items(section.get("blocks"))
        if block.get("type") in ("figure", "table") and block.get("evidence_id")
    }
    audit_visual_blocks = []
    for item in figs:
        if str(item.get("id")) not in present_visual_ids:
            audit_visual_blocks.append(_figure_block(item, claims, roles, question="论文在此处提供了什么可核查的图像证据？", section_refs=[str(item.get("id"))]))
    for item in tables:
        if str(item.get("id")) not in present_visual_ids:
            audit_visual_blocks.append(_table_block(item, claims, roles, question="论文在此处提供了什么可核查的表格证据？", section_refs=[str(item.get("id"))]))
    if audit_visual_blocks:
        sections.append({"id": f"spine-{len(sections)+1:02d}", "title": "证据目录与审计锚点", "lead": "未进入主叙事的图表仍保留为可定位的审计证据。", "blocks": audit_visual_blocks})

    council_uncertain = []
    for item in _items(council.get("unresolved")) + _items(council.get("items")):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or item.get("epistemic_state") or "").upper()
        if status in ("UNRESOLVED", "AMBIGUOUS", "INSUFFICIENT_EVIDENCE", "TENSION"):
            statement = item.get("statement") or item.get("canonical_statement")
            if statement:
                council_uncertain.append(_clause(statement))
    council_uncertain = list(dict.fromkeys(council_uncertain))
    topic_blocks = []
    for topic in _items(synthesis.get("topics")):
        parts = [_clause(topic.get("core_conclusion_zh") or topic.get("conclusion"))]
        for key, prefix in (("mechanism_zh", "这说明"), ("reviewer_caveat_zh", "但证据边界是"), ("alternative_explanation_zh", "另一种解释是"), ("anomaly_zh", "同时需要注意")):
            if topic.get(key): parts.append(f"{prefix}{_clause(topic.get(key))}")
        topic_blocks.append({"type": "paragraph", "text": "。".join(parts) + "。", "evidence_refs": [str(x) for x in topic.get("evidence_refs", []) if x] or default_refs})
    if not topic_blocks: topic_blocks.append({"type": "paragraph", "text": f"在已报告的证据范围内，{_clause(spine.get('justified_conclusion'))}。", "evidence_refs": default_refs})
    if council_uncertain:
        topic_blocks.append({"type": "paragraph", "text": f"证据之间仍保留未决之处：{'；'.join(council_uncertain)}。", "evidence_refs": default_refs})
    sections.append({"id": f"spine-{len(sections)+1:02d}", "title": _truncate(spine.get("justified_conclusion")), "lead": "把实验证据、解释和反例放在同一条论证链上，判断结论成立的范围。", "blocks": topic_blocks})
    boundary_items = limitations + anomalies + unresolved + council_uncertain or [_clean(x) for x in _items(spine.get("scope_and_limits"))]; boundary_text = "；".join(dict.fromkeys(x for x in boundary_items if x)) or UNCERTAIN
    sections.append({"id": f"spine-{len(sections)+1:02d}", "title": f"边界与未决问题：{_truncate(boundary_text, 56)}", "lead": "论文已经建立的结论必须和尚未检验的范围一起阅读。", "blocks": [{"type": "paragraph", "text": f"目前可以确立的是：{_clause(spine.get('justified_conclusion'))}。", "evidence_refs": default_refs}, {"type": "paragraph", "text": f"仍需保留为开放问题的是：{_clause(boundary_text)}。", "evidence_refs": default_refs}]})
    if intent == "PAPER_TECHNICAL_EXTRACTION":
        details = "；".join(_clean(m.get("name")) + "：" + _clean(m.get("description")) for m in methods) or UNCERTAIN
        sections.append({"id": "technical_extraction", "title": "论文中可复核的技术细节", "lead": "仅整理源论文明确给出的实现信息。", "blocks": [{"type": "paragraph", "text": details, "evidence_refs": default_refs}]})
    for idx, section in enumerate(sections, 1):
        section["chapter_num"] = f"{idx:02d}"; section.setdefault("blocks", [{"type": "paragraph", "text": _clean(section.get("lead")), "evidence_refs": default_refs}]); section.setdefault("lead", _clean(section.get("title")))
    conflicts = _items(council.get("items")) or _items(pm.get("lens_conflicts")); meta_authors = paper.get("authors", []); meta_authors = meta_authors if isinstance(meta_authors, list) else [str(meta_authors)]
    manuscript = {"schema_version": "2.0", "paper_id": pm.get("paper_id", root.name), "source_sha256": pm.get("source_sha256", ""), "created_at": datetime.now(timezone.utc).isoformat(), "document": {"title": title, "subtitle": "中文科学精读稿", "paper_meta": {"authors": meta_authors, "venue": paper.get("venue", ""), "year": paper.get("year"), "doi": paper.get("doi", ""), "pdf_sha256": pm.get("source_sha256", "")}, "executive_summary": {"lead": f"{_clause(spine.get('central_question'))}。{_clause(spine.get('justified_conclusion'))}。", "takeaways": [_clean(spine.get("central_question")), _clean(spine.get("central_move")), _clean(spine.get("justified_conclusion")), f"边界：{boundary_text}"], "key_question": _clean(spine.get("central_question")), "core_finding": _clean(spine.get("justified_conclusion")), "core_boundary": boundary_text}, "story_spine": spine, "chapters": sections, "appendix_summary": {"claims_count": len(claims), "figures_count": len(figs), "tables_count": len(tables), "conflicts_count": len(conflicts), "unresolved_count": len(unresolved), "evidence_atlas_ref": "evidence_atlas.html"}}}
    errs = schema_validate(manuscript, "narrative_manuscript")
    if errs: raise ValueError(f"narrative_manuscript schema validation failed: {errs}")
    return manuscript


def main():
    ap = argparse.ArgumentParser(description="Compose the paper-specific Reader narrative."); ap.add_argument("--out", required=True); ap.add_argument("--intent", choices=INTENTS, default=None); args = ap.parse_args(); root = Path(args.out)
    output = root / "reader/narrative_manuscript.json"; output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(compose_narrative_manuscript(root, args.intent), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); print(f"OK: Composed paper-specific narrative -> {output}")


if __name__ == "__main__":
    main()
