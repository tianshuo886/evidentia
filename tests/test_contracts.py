import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_init_run_is_source_only():
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);pdf=r/'p.pdf';pdf.write_bytes(b'%PDF fake')
  p=subprocess.run([sys.executable,str(ROOT/'scripts/init_run.py'),'--pdf',str(pdf),'--out',str(r/'out')],capture_output=True,text=True)
  assert p.returncode==0
  state=json.loads((r/'out/run_state.json').read_text());assert state['mode']=='paper-read';assert 'project' not in json.dumps(state).lower()
def test_lens_runner_requires_base_model():
 with tempfile.TemporaryDirectory() as t:
  r=Path(t);(r/'source').mkdir();(r/'source/paper.pdf').write_bytes(b'x');(r/'model').mkdir()
  p=subprocess.run([sys.executable,str(ROOT/'scripts/lens_runner.py'),'--out',str(r)],capture_output=True,text=True)
  assert p.returncode!=0
