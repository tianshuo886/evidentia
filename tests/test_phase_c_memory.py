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

def test_two_stage_apply_with_memory_synthesis(tmp_path):
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    proj_doc = tmp_path / 'proj.md'
    proj_doc.write_text("Goal: feature extraction under low lighting conditions.")
    
    # Run Apply with --with-memory
    res = subprocess.run([
        PY, str(ROOT / 'scripts/apply_agent.py'),
        '--paper', str(p_dir),
        '--project', str(proj_doc),
        '--with-memory',
        '--memory-root', str(mem_root)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr

    # Stage A artifact exists
    delta_p = p_dir / 'apply/proj/research_delta.json'
    assert delta_p.exists()

    # Stage B artifact exists
    synth_p = p_dir / 'apply/proj/memory_augmented_synthesis.json'
    assert synth_p.exists()

    synth = json.loads(synth_p.read_text(encoding='utf-8'))
    assert synth['project_id'] == 'proj'
    assert 'local_delta_sha256' in synth
    assert 'retrieved_memory_items' in synth

def test_memory_relation_and_inspect(tmp_path):
    import memory_relation
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    c1 = memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # Inspect paper commit
    ins_commit = memory_manager.inspect_memory(c1, custom_root=mem_root)
    assert ins_commit is not None
    assert ins_commit['kind'] == 'MEMORY_COMMIT'
    assert ins_commit['paper_id'] == 'p1'

    # Add cross-paper typed relation
    rel_id = memory_relation.add_relation(
        source_id=f"MEM-{c1}-C01",
        target_id="MEM-EXTERNAL-C01",
        rel_type="SUPPORTS",
        reason="Method mechanism replicates in independent evaluation",
        source_paper="p1",
        target_paper="p2",
        evidence_ids=["F01"],
        custom_root=mem_root
    )
    assert rel_id.startswith("REL-")

    # Inspect relation
    ins_rel = memory_manager.inspect_memory(rel_id, custom_root=mem_root)
    assert ins_rel is not None
    assert ins_rel['kind'] == 'MEMORY_RELATION'
    assert ins_rel['relation_type'] == 'SUPPORTS'

def test_memory_snapshot_export_import(tmp_path):
    import memory_snapshot, memory_export, memory_import
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # 1. Snapshot
    snap_dir = tmp_path / 'snapshot_test'
    memory_snapshot.create_snapshot(out_dir=snap_dir, custom_root=mem_root)
    assert (snap_dir / 'snapshot_meta.json').exists()
    assert (snap_dir / 'memory_manifest.json').exists()

    # 2. Export
    export_file = tmp_path / 'export.tar.gz'
    memory_export.export_memory(out_file=export_file, custom_root=mem_root)
    assert export_file.exists()

    # 3. Import into fresh root
    fresh_root = tmp_path / 'fresh_memory'
    reindexed = memory_import.import_memory(export_file, custom_root=fresh_root)
    assert reindexed >= 2
    assert (fresh_root / 'memory.sqlite').exists()
    hits = memory_manager.search_memory("Attention", custom_root=fresh_root)
    assert len(hits) >= 1

def test_stage_b_memory_synthesis_task_and_sha_binding(tmp_path):
    """P0-2 Hardening: Stage B constructs memory_bundle.json & AgentTask, binds to local delta SHA, and waits when no agent is active."""
    mem_root = tmp_path / 'memory'
    p_dir = tmp_path / 'paper_run'
    p_dir.mkdir()
    fixture(p_dir)
    run('freeze_check.py', '--out', str(p_dir))
    memory_manager.commit_paper(p_dir, custom_root=mem_root)

    # Initialize run_state.json
    rs_p = p_dir / 'run_state.json'
    rs_p.write_text(json.dumps({
        "schema_version": "1.0",
        "run_id": "test-run",
        "mode": "evidentia",
        "phase": "FREEZE",
        "allowed_inputs": ["working/paper.pdf"],
        "artifacts": {}
    }, indent=2))

    proj_doc = tmp_path / 'proj.md'
    proj_doc.write_text("Goal: feature extraction under low lighting conditions.")

    import apply_agent
    # Run Stage A
    apply_agent.run_local_apply(p_dir, proj_doc, fixture=True)
    delta_p = p_dir / 'apply/proj/research_delta.json'
    assert delta_p.exists()

    # Run Stage B with fixture=False (simulating absence of Host Agent)
    apply_agent.run_memory_synthesis(p_dir, 'proj', memory_root=mem_root, fixture=False)

    # 1. Memory bundle and task packet created
    bundle_p = p_dir / 'apply/proj/memory_bundle.json'
    assert bundle_p.exists()
    task_p = p_dir / 'tasks/apply/proj_memory_synthesis.json'
    assert task_p.exists()

    # 2. Workflow must pause in WAITING_FOR_MEMORY_SYNTHESIS_AGENT
    rs_p = p_dir / 'run_state.json'
    rs = json.loads(rs_p.read_text())
    assert rs.get('phase') == "WAITING_FOR_MEMORY_SYNTHESIS_AGENT"

    # 3. Memory synthesis not yet created by Python
    synth_p = p_dir / 'apply/proj/memory_augmented_synthesis.json'
    assert not synth_p.exists()



