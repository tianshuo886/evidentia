"""Phase C11 Frozen Research Memory acceptance tests.

Validates:
- Memory root & database initialization
- Immutable JSON object storage + SQLite rebuildable indexing
- Paper Memory Commit (only for verified FROZEN papers)
- Refusal of unfrozen paper commits
- Project Memory Commit & Experiment Outcome recording
- FTS5 full-text search with exact provenance
- Memory integrity verification and index rebuild
- Open Reading Memory Firewall enforcement
"""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from test_gates import fixture, run, sha_bytes, L
import memory_manager

def test_memory_root_and_db_init(tmp_path):
    mem_root = tmp_path / 'memory_root'
    root = memory_manager.get_memory_root(mem_root)
    assert root.exists()
    assert (root / 'memory.sqlite').exists()
    assert (root / 'memory_manifest.json').exists()
    assert (root / 'objects/paper_commits').exists()
    assert (root / 'objects/project_commits').exists()
    assert (root / 'objects/outcomes').exists()

def test_commit_paper_and_refuse_unfrozen(tmp_path):
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)

    # 1. Attempting commit before freeze must be REFUSED
    try:
        memory_manager.commit_paper(p_dir, custom_root=mem_root)
        assert False, "Should have failed on unfrozen paper"
    except SystemExit as e:
        assert "REFUSED" in str(e)

    # 2. Freeze the paper model
    res_freeze = run('freeze_check.py', '--out', str(p_dir))
    assert res_freeze.returncode == 0

    # 3. Commit frozen paper
    commit_id = memory_manager.commit_paper(p_dir, custom_root=mem_root)
    assert commit_id.startswith("PC-")
    
    # Verify canonical JSON objects in objects/paper_commits/
    commit_dir = mem_root / 'objects/paper_commits' / commit_id
    assert (commit_dir / 'commit.json').exists()
    assert (commit_dir / 'items.json').exists()

    items = json.loads((commit_dir / 'items.json').read_text())
    assert len(items) >= 2
    types = {it['memory_type'] for it in items}
    assert 'PAPER' in types
    assert 'CLAIM' in types

def test_project_commit_and_experiment_outcome(tmp_path):
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # Generate Project Delta
    proj_doc = tmp_path / 'proj.md'
    proj_doc.write_text("Goal: optimize feature representation under low lighting conditions.")
    run('apply_agent.py', '--paper', str(p_dir), '--project', str(proj_doc))

    # Commit project
    prj_commit_id = memory_manager.commit_project(p_dir, "proj", custom_root=mem_root)
    assert prj_commit_id.startswith("PRJ-")

    # Record experiment outcome
    outcome_id = memory_manager.record_outcome(
        project_id="proj",
        experiment_id="EXP-01",
        verdict="SUCCESS",
        findings="Model converged 2x faster with verified loss.",
        custom_root=mem_root
    )
    assert outcome_id.startswith("OUT-")
    assert (mem_root / 'objects/outcomes' / f"{outcome_id}.json").exists()

def test_memory_search_and_provenance(tmp_path):
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # Search by keyword in committed text
    results = memory_manager.search_memory("Attention", custom_root=mem_root)
    assert len(results) >= 1
    hit = results[0]
    assert 'memory_id' in hit
    assert 'paper_id' in hit
    assert 'source_ids' in hit
    assert 'epistemic_state' in hit
    assert 'source_sha256' in hit

def test_memory_integrity_and_rebuild_index(tmp_path):
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # Verify integrity
    errs = memory_manager.verify_memory_integrity(custom_root=mem_root)
    assert not errs, f"Memory integrity errors: {errs}"

    # Rebuild index from canonical JSON objects
    reindexed = memory_manager.rebuild_index(custom_root=mem_root)
    assert reindexed >= 2

def test_open_reading_memory_firewall():
    # Valid isolated task
    clean_task = {
        "task_id": "TASK-01",
        "task_type": "OPEN_READING",
        "input_artifacts": {"source_pdf": "source/paper.pdf"},
        "prohibited_context": ["RESEARCH_MEMORY", "project documents"]
    }
    ok, _ = memory_manager.enforce_open_reading_firewall(clean_task)
    assert ok is True

    # Leaked memory in prohibited context missing
    unprotected_task = {
        "task_id": "TASK-02",
        "task_type": "OPEN_READING",
        "input_artifacts": {"source_pdf": "source/paper.pdf"},
        "prohibited_context": ["chat history"]
    }
    ok, msg = memory_manager.enforce_open_reading_firewall(unprotected_task)
    assert ok is False
    assert "RESEARCH_MEMORY" in msg

    # Leaked memory artifact in inputs
    leaked_task = {
        "task_id": "TASK-03",
        "task_type": "OPEN_READING",
        "input_artifacts": {"memory_db": "memory/memory.sqlite"},
        "prohibited_context": ["RESEARCH_MEMORY"]
    }
    ok, msg = memory_manager.enforce_open_reading_firewall(leaked_task)
    assert ok is False
    assert "leaked" in msg
