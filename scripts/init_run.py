#!/usr/bin/env python3
"""Initialize a source-only Evidentia run boundary (Phase-A: schema-valid run_state)."""
import argparse, hashlib, json, shutil, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from intent_router import route_intent, get_intent_boundaries, INTENTS

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--supplement', action='append', default=[])
    ap.add_argument('--intent', choices=INTENTS, default=None)
    ap.add_argument('--prompt', default=None)
    a = ap.parse_args()

    intent = route_intent(prompt=a.prompt, explicit=a.intent)
    if intent == "PROJECT_APPLY":
        sys.exit("Error: PROJECT_APPLY must be initialized via init_apply.py or pipeline.py apply after paper reading is complete.")

    r = Path(a.out)
    (r / 'working').mkdir(parents=True, exist_ok=True)
    (r / 'source').mkdir(exist_ok=True)

    src_pdf = Path(a.pdf).resolve()
    if src_pdf != (r / 'working/paper.pdf').resolve():
        shutil.copy2(a.pdf, r / 'working/paper.pdf')
    if src_pdf != (r / 'source/paper.pdf').resolve():
        shutil.copy2(a.pdf, r / 'source/paper.pdf')

    for s in a.supplement:
        s_pdf = Path(s).resolve()
        if s_pdf != (r / 'working' / Path(s).name).resolve():
            shutil.copy2(s, r / 'working' / Path(s).name)
        if s_pdf != (r / 'source' / Path(s).name).resolve():
            shutil.copy2(s, r / 'source' / Path(s).name)

    boundaries = get_intent_boundaries(intent)
    allowed = ['working/paper.pdf'] + [f'working/{Path(s).name}' for s in a.supplement]
    forbidden = boundaries.get('forbidden_inputs', ['apply/', 'project/', 'memory/project/'])

    state = {
        'schema_version': '1.0',
        'run_id': str(uuid.uuid4()),
        'mode': 'evidentia',
        'intent': intent,
        'phase': 'INGEST',
        'source_sha256': sha(a.pdf),
        'base_sha256': None,
        'allowed_inputs': allowed,
        'forbidden_inputs': forbidden,
        'artifacts': {},
        'completed_phases': [],
        'artifact_hashes': {},
        'executor': {},
        'history': [{'phase': 'INGEST', 'status': 'started', 'at': datetime.now(timezone.utc).isoformat()}]
    }
    (r / 'run_state.json').write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'initialized {r}/run_state.json with intent {intent}')

if __name__ == '__main__':
    main()
