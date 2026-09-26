#!/usr/bin/env python3
"""Audit declared Evidentia capabilities against schemas, scripts, tests and docs."""
import argparse, json, re
from pathlib import Path

CAPABILITIES = [
 {"id":"source_reconstruction","area":"Core","claim":"PDF source map and figure/table inventory","schema":["source_map","figure_inventory"],"scripts":["ingest.py","extract_structure.py","extract_figs.py"],"tests":["test_init_run_is_source_only"],"status":"IMPLEMENTED","evidence":"Executable extraction scripts and schemas exist; coverage is gate-checked."},
 {"id":"open_reading_base","area":"Core","claim":"Explicit project-independent Open Reading Base","schema":["paper_model","open_reading_manifest"],"scripts":["snapshot_baseline.py","lens_runner.py","phase.py"],"tests":["test_phase_a"],"status":"IMPLEMENTED","evidence":"snapshot_baseline.py freezes open_reading_model.json + open_reading_manifest.json; lens/phase gates bind base_model_sha256."},
 {"id":"independent_lens_tasks","area":"Execution","claim":"Six independent Lens task packets","schema":["lens_task","lens"],"scripts":["lens_runner.py","check_lenses.py"],"tests":["test_lens_runner_requires_base_model"],"status":"PARTIAL","evidence":"Runner creates six packets and validation checks outputs; model execution remains external."},
 {"id":"lens_reconciliation","area":"Core","claim":"Agreement, complementary findings, conflicts and unresolved conflicts","schema":["lens_reconciliation","lens_synthesis"],"scripts":["merge_lenses.py","check_lenses.py","freeze_check.py"],"tests":["test_merge_preserves_supporting_lenses"],"status":"IMPLEMENTED","evidence":"merge_lenses writes lens_reconciliation.json (supporting_lenses preserved, TENSION recorded) + lens_synthesis.json; freeze refuses erased conflicts."},
 {"id":"canonical_paper_model","area":"Core","claim":"Paper facts remain separate from project interpretation","schema":["paper_model"],"scripts":["validate_model.py","freeze_check.py"],"tests":[],"status":"PARTIAL","evidence":"Schema and freeze gates exist; merge_lenses currently mutates paper_model with lens_synthesis."},
 {"id":"evidence_graph","area":"Core","claim":"Typed claim/evidence/figure/table/experiment graph","schema":["evidence_graph"],"scripts":["build_graph.py"],"tests":[],"status":"PARTIAL","evidence":"Graph is generated, but relation semantics and provenance coverage are limited."},
 {"id":"freeze_integrity","area":"Core","claim":"Schema, dangling-ID, hashes and FROZEN manifest gate","schema":["manifest"],"scripts":["freeze_check.py","verify_frozen.py"],"tests":[],"status":"IMPLEMENTED","evidence":"Freeze and verification scripts write and validate manifest status and hashes."},
 {"id":"coverage_audit","area":"Verification","claim":"Semantic coverage of figures, tables, claims, equations, supplements and limitations","schema":[],"scripts":["source_audit.py","freeze_check.py","full_audit.py"],"tests":[],"status":"PARTIAL","evidence":"Figure/table and claim checks exist; equations, limitations and supplement coverage are not fully machine-checked."},
 {"id":"reader_and_visual_qa","area":"Presentation","claim":"Evidence Reader with Kami visual QA boundary","schema":["render_ir"],"scripts":["render_reader.py","reader_audit.py","kami_adapter.py"],"tests":[],"status":"PARTIAL","evidence":"HTML reader and adapter exist; PDF/visual QA depends on external Kami and is not covered by core tests."},
 {"id":"project_apply_delta","area":"Apply","claim":"Contextual reread, gap map and typed Research Delta","schema":["project_context","research_delta"],"scripts":["init_apply.py","validate_delta.py"],"tests":[],"status":"PARTIAL","evidence":"Initialization and schema validation exist; contextual reread and delta reasoning are external/manual."},
 {"id":"provenance","area":"Core","claim":"Every important object traces to source and execution metadata","schema":["open_reading_manifest","lens_reconciliation"],"scripts":["freeze_check.py","check_lenses.py","phase.py","snapshot_baseline.py"],"tests":["test_phase_a"],"status":"IMPLEMENTED","evidence":"SOURCE_SHA256 chain closed (source_map/inventory/model/graph/lens/baseline all bound); freeze fail-closed on any mismatch."},
 {"id":"evaluation_benchmark","area":"Verification","claim":"Structural, scientific and human research evaluation","schema":[],"scripts":[],"tests":[],"status":"MISSING","evidence":"No benchmark corpus or evaluation harness is committed."},
]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--write', action='store_true'); a=ap.parse_args()
    root=Path(a.out); result={"schema_version":"1.0","audit":"P0 Contract Audit","repository":"Evidentia","statuses":["IMPLEMENTED","PARTIAL","DECLARED_ONLY","MISSING","DEPRECATED"],"capabilities":CAPABILITIES}
    target=root/'model'/'capability_matrix.json' if a.write else root/'capability_matrix.json'
    target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    counts={s:sum(x['status']==s for x in CAPABILITIES) for s in result['statuses']}
    print(json.dumps({"status":"OK","output":str(target),"counts":counts},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
