# Reader v3 — strong-model-first paper reading

Reader v3 is the migration path defined by Issues #15–#20. It intentionally
coexists with the legacy Reader until real-paper A/B evaluation passes.

## Scientific content path

```
Source reconstruction
  ↓
Lead Reader
  ↓
4 Core + 2 Adaptive Lens passes
  ↓
Revision Memo
  ↓
Lead Writer
  ↓
Evidence binding / Kami rendering
```

Deterministic Python is allowed to orchestrate, validate provenance, crop
vision-verified regions, and render presentation. It must not be the final
scientific author.

## Commands

Given an already initialized paper workspace:

```bash
# Optional but strongly recommended: semantic visual verification
python scripts/visual_localization_protocol.py --out <paper>
# execute tasks/v3/visual/*.json through the active host, then:
python scripts/apply_visual_verification.py --out <paper>

# Build Reader v3 tasks incrementally
python scripts/reader_v3.py prepare --out <paper>
# execute/submit the printed task
python scripts/reader_v3.py prepare --out <paper>
# execute all tasks/v3/lens/*.json
python scripts/reader_v3.py prepare --out <paper>
# execute Revision Memo
python scripts/reader_v3.py prepare --out <paper>
# execute Lead Writer
python scripts/reader_v3.py render --out <paper>
```

Production host submission continues through `agent_submit.py`. The generic
`reader_v3_agent.py` can run replay/fixture/host dispatch paths where available.

## Model / Harness boundary

The v3 core never selects providers. The active harness owns model execution.
One strong model running six isolated specialist contexts is the default.
Second-model verification is targeted and optional.

## Empirical release gate

```bash
python scripts/reader_v3_benchmark.py direct --out <paper>
# execute real direct-reading task
python scripts/reader_v3_benchmark.py evaluate --out <paper>
# execute source-assisted pair evaluation
```

Do not use the legacy synthetic Direct-AI fixture as empirical evidence.
