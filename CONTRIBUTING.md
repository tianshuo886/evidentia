# Contributing to Evidentia

Thank you for contributing to Evidentia!

## Architectural Invariants

All contributions must preserve these non-negotiable architectural principles:

1. **Evidentia Core must be Host-Agnostic**: Evidentia Core does not depend on Pi, Codex, Claude Code, or any specific model API. Standard Mode must run on any single compatible host.
2. **Current Focus: Lens × Model**: Harness diversity is strictly excluded as an epistemic signal.
3. **Standard Mode is Complete**: Standard Mode is not a "lite" mode; it includes full source reconstruction, six independent lenses, verification, freeze, reader, and apply.
4. **Consensus ≠ Truth**: Majority voting is prohibited. Scientific findings must be validated against original localized source evidence.
5. **Paper Truth is Frozen First**: Project context cannot retrospectively mutate the canonical Paper Model.
6. **Fail-Closed Gates**: Missing dependencies, hash mismatches, uninspected figures, or unresolved conflicts must fail closed.

## Development & Testing

Run all automated unit and contract tests:

```bash
python3 -m pytest
```

Audit declared capabilities against repository state:

```bash
python3 scripts/contract_audit.py --out .
```

Run evaluation benchmark:

```bash
python3 evals/runners/eval_runner.py
```

## Pull Request Checklist

- [ ] New capabilities are reflected in `capability_matrix.json` and `scripts/contract_audit.py`.
- [ ] No existing fail-closed correctness gates are weakened.
- [ ] All tests pass without warnings.
- [ ] Schema changes are versioned and follow `https://evidentia.dev/schemas/` namespace.
