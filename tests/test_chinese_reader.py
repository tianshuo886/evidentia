"""Tests for Chinese-first Narrative Scientific Reader (P0 Workstream C).

Validates:
- Unified Content IR (paper_reader_ir.json) adhering to schema
- Dual generation of HTML and Markdown from the same IR
- Seven-layer scientific narrative hierarchy in Chinese
- Collapsible secondary audit & provenance appendix
- Bidirectional link preservation
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture
from validate_common import schema_validate

SEVEN_LAYERS = [
    "一分钟看懂这篇论文",
    "论文到底在解决什么问题",
    "方法到底怎么工作",
    "关键实验逐个说明",
    "综合科学判断",
    "可复用技术内容",
    "证据审计附录"
]

def test_chinese_reader_ir_and_dual_rendering(tmp_path):
    r = fixture(tmp_path)
    
    # Run render_reader.py
    res = subprocess.run([
        PY, str(ROOT / 'scripts/render_reader.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    reader_dir = r / 'reader'
    
    # 1. Content IR validation
    ir_p = reader_dir / 'paper_reader_ir.json'
    assert ir_p.exists()
    ir = json.loads(ir_p.read_text(encoding='utf-8'))
    errs = schema_validate(ir, 'paper_reader_ir')
    assert not errs, f"paper_reader_ir schema errors: {errs}"

    # 2. HTML Reader validation
    html_p = reader_dir / 'paper_reader.html'
    assert html_p.exists()
    html_text = html_p.read_text(encoding='utf-8')
    for layer in SEVEN_LAYERS:
        assert layer in html_text, f"Missing narrative section in HTML: {layer}"
    # Verify audit details tag is used
    assert '<details' in html_text
    assert 'Observation' in html_text
    assert 'Author Interpretation' in html_text
    assert 'Reader Assessment' in html_text

    # 3. Markdown Reader validation
    md_p = reader_dir / 'paper_reader.md'
    assert md_p.exists()
    md_text = md_p.read_text(encoding='utf-8')
    for layer in SEVEN_LAYERS:
        assert layer in md_text, f"Missing narrative section in MD: {layer}"

    # 4. Backward compatibility aliases
    assert (reader_dir / 'reader.html').exists()
    assert (reader_dir / 'reader.md').exists()
    assert (reader_dir / 'render_ir.json').exists()

    # 5. Run reader audit
    res_audit = subprocess.run([
        PY, str(ROOT / 'scripts/reader_audit.py'),
        '--out', str(r)
    ], capture_output=True, text=True)
    assert res_audit.returncode == 0, res_audit.stdout + res_audit.stderr
