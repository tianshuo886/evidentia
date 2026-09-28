#!/usr/bin/env python3
"""Render project-specific apply results into apply/<project>/project_reader.html and project_reader.md.

Physically separated from Paper Reader:
- Paper Reader is immutable, frozen, and project-independent
- Project Reader lives exclusively under apply/<project>/
- Provenance links point back to frozen paper claims, figures, tables, and experiments
"""
import argparse, html, json, sys
from pathlib import Path

def esc(x):
    return html.escape(str(x or ''))

def render_project_reader(paper_dir, project_dir):
    p_dir = Path(paper_dir)
    target_dir = Path(project_dir)
    
    delta_p = target_dir / 'research_delta.json'
    if not delta_p.exists():
        sys.exit(f"Missing {delta_p}")
    delta = json.loads(delta_p.read_text(encoding='utf-8'))
    
    pm_p = p_dir / 'model/paper_model.json'
    pm = json.loads(pm_p.read_text(encoding='utf-8')) if pm_p.exists() else {}
    paper_title = pm.get('paper', {}).get('title', 'Paper')
    project_name = delta.get('project', {}).get('name', target_dir.name)
    
    tus = delta.get('transfer_units', [])
    cb = delta.get('changed_beliefs', [])
    ne = delta.get('new_evidence', [])
    nu = delta.get('new_unknowns', [])
    exp = delta.get('experiments', [])
    
    # HTML generation
    tu_rows = "".join([
        f"<tr><td><strong>{esc(u.get('id'))}</strong></td><td><span class='badge verdict-{esc(u.get('verdict','').lower())}'>{esc(u.get('verdict'))}</span></td><td>{esc(u.get('source_component') or u.get('reason'))}</td><td>{esc(', '.join(u.get('source', [])))}</td></tr>"
        for u in tus
    ])
    
    exp_cards = "".join([
        f"<div class='card'><h4>{esc(e.get('id', 'EXP'))}: {esc(e.get('hypothesis', ''))}</h4><p><strong>Delta vs Plan:</strong> {esc(e.get('delta_vs_current_plan', ''))}</p><p><strong>Source Evidence:</strong> {esc(', '.join(e.get('source', [])))}</p><p><strong>Decision Value:</strong> {esc(e.get('decision_value', ''))}</p></div>"
        for e in exp
    ])
    
    html_content = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{esc(project_name)} · Project Research Delta</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.6; max-width: 960px; margin: 0 auto; padding: 24px; color: #1e293b; background: #f8fafc; }}
header {{ border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 24px; }}
h1 {{ color: #0f172a; margin: 0 0 8px 0; }}
.meta {{ color: #64748b; font-size: 0.9em; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 600; }}
.verdict-direct {{ background: #dcfce7; color: #166534; }}
.verdict-adapt {{ background: #fef9c3; color: #854d0e; }}
.verdict-inspiration_only {{ background: #e0e7ff; color: #3730a3; }}
.verdict-reject {{ background: #fee2e2; color: #991b1b; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th, td {{ padding: 10px 14px; border: 1px solid #e2e8f0; text-align: left; }}
th {{ background: #f1f5f9; font-weight: 600; }}
.card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
</style>
</head>
<body>
<header>
  <div class="meta">EVIDENTIA PROJECT RESEARCH DELTA · CONTEXTUAL APPLY</div>
  <h1>项目迁移研报: {esc(project_name)}</h1>
  <div class="meta">关联论文: {esc(paper_title)} · 冻结模型 SHA: <code>{esc(delta.get('paper_model_sha256', '')[:12])}</code></div>
</header>

<section>
  <h2>迁移单元 (Transfer Units)</h2>
  <table>
    <thead><tr><th>ID</th><th>判定 (Verdict)</th><th>组件 / 理由</th><th>来源证据</th></tr></thead>
    <tbody>{tu_rows if tu_rows else "<tr><td colspan='4'>无显式迁移组件</td></tr>"}</tbody>
  </table>
</section>

<section>
  <h2>认知变化与新发现</h2>
  <ul>
    {''.join(f"<li><strong>{esc(b.get('id'))}:</strong> {esc(b.get('statement'))} (<em>{esc(b.get('impact_on_project'))}</em>)</li>" for b in cb) if cb else "<li>无显著先验认知变更</li>"}
  </ul>
</section>

<section>
  <h2>派生实验设计 (Actionable Experiments)</h2>
  {exp_cards if exp_cards else "<p><em>NO_NEW_ACTIONABLE_EXPERIMENT: 当前论文证据不足以支撑针对该项目的新增实验。</em></p>"}
</section>
</body>
</html>
"""
    (target_dir / 'project_reader.html').write_text(html_content, encoding='utf-8')
    
    # Markdown generation
    md_lines = [
        f"# 项目迁移研报: {project_name}",
        f"\n- **关联论文**: {paper_title}",
        f"- **论文冻结 SHA**: `{delta.get('paper_model_sha256', '')}`",
        f"- **生成时间**: {delta.get('created_at', '')}",
        "\n## 1. 迁移单元 (Transfer Units)",
        "| ID | 判定 | 组件 / 理由 | 来源证据 |",
        "|---|---|---|---|"
    ]
    for u in tus:
        md_lines.append(f"| {u.get('id')} | **{u.get('verdict')}** | {u.get('source_component') or u.get('reason')} | {', '.join(u.get('source', []))} |")
    if not tus:
        md_lines.append("| - | NONE | 无显式迁移组件 | - |")
        
    md_lines.append("\n## 2. 认知变化 (Changed Beliefs)")
    if cb:
        for b in cb:
            md_lines.append(f"- **{b.get('id')}**: {b.get('statement')} (影响: {b.get('impact_on_project')})")
    else:
        md_lines.append("- 无显著先验认知变更")

    md_lines.append("\n## 3. 派生实验设计 (Actionable Experiments)")
    if exp:
        for e in exp:
            md_lines.append(f"### {e.get('id', 'EXP')}: {e.get('hypothesis', '')}\n- **基线对比**: {e.get('delta_vs_current_plan', '')}\n- **来源证据**: {', '.join(e.get('source', []))}\n- **决策价值**: {e.get('decision_value', '')}")
    else:
        md_lines.append("_NO_NEW_ACTIONABLE_EXPERIMENT_")
    
    (target_dir / 'project_reader.md').write_text("\n".join(md_lines) + "\n", encoding='utf-8')
    print(f"OK: Generated project reader -> {target_dir / 'project_reader.html'} and .md")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paper', required=True)
    ap.add_argument('--project-dir', required=True)
    a = ap.parse_args()
    render_project_reader(a.paper, a.project_dir)

if __name__ == '__main__':
    main()
