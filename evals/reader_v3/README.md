# Reader v3 empirical evaluation

This directory is for **real-paper, real-model** Reader evaluation.

The old `evals/baselines/direct_ai_baseline.py` is a synthetic fixture and must
not be cited as evidence that Evidentia outperforms direct strong-model reading.

For each benchmark paper:

1. run `reader_v3_benchmark.py direct` and execute the generated task with the
   same active harness / comparable strong-model capability used by Reader v3;
2. complete Reader v3;
3. run `reader_v3_benchmark.py evaluate`;
4. inspect the pair evaluation and the actual rendered HTML manually;
5. after at least three completed real-paper Readers spanning different structures, run:
   `python scripts/reader_structure_diversity.py --run <method-run> --run <empirical-run> --run <theory-or-review-run>`.

The structural-diversity gate reports section architectures and asks whether the
Reader feels shaped by the paper or by Evidentia. It is intentionally separate
from the full Issue #19 benchmark and fails closed when fewer than three real
Reader outputs are available.

Required development corpus: 5–10 real papers across multiple paper types plus
at least one post-freeze unseen paper.

Release is blocked if Reader v3 regresses materially on narrative clarity,
scientific completeness, or method explanation. Its intended added value is
evidence grounding, figure/table interpretation, validity/boundary analysis,
explicit uncertainty, and provenance.
