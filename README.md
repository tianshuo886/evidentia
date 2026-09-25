# paper-read · Paper Research OS

A complete single-paper research skill: source reconstruction, project-invisible open reading, six independent Lens rereads, frozen evidence-grounded Paper Model, unified Paper/Project Reader, contextual Research Delta, and reusable literature memory.

This repository contains only the skill and its executable contracts. Papers used for testing remain external inputs.

## Entrypoints

```bash
python scripts/pipeline.py read --pdf paper.pdf --out output
python scripts/lens_runner.py --out output
python scripts/phase.py --out output --complete SOURCE_RECONSTRUCTION
python scripts/freeze_check.py --out output
python scripts/render_reader.py --out output
python scripts/pipeline.py apply --paper output --project project.md
python scripts/validate_delta.py --paper output --delta output/apply/project/research_delta.json
```

The system refuses missing schemas, dangling provenance, incomplete Lens passes, changed frozen hashes, unresolved coverage declarations, and Reader omissions. It stores Paper facts and Project Delta separately while presenting both in one Reader.
