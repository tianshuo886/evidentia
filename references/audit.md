# Coverage + content audits

## Freeze gate (`freeze_check.py --out <out>`, exit 0 required)

- [ ] every inventory figure/table has role + depth (type changes depth, never coverage)
- [ ] every claim has evidence IDs or epistemic NOT_STATED
- [ ] unresolved list explicit; supplement/methods-appendix/ablations/negative results inspected
- [ ] `manifest.json` written (sha256, counts, status FROZEN)

## Reader content audit (model → reader)

- [ ] no `{{…}}` placeholders; every figure ref resolves to a file
- [ ] captions verbatim; page/figure IDs intact; unresolved visible
- [ ] delta source links (`[C07][Fig.6b]`) resolve both directions
- [ ] no science reshaped for Kami tokens (adapter adds presentation, never edits facts)

## Visual QA (spot-check rendered pages)

Figure clarity; caption bound to figure; no Evidence Block split across pages;
Claim Cards not over-dense; PAPER vs PROJECT visually distinct (ink-blue vs
olive); math renders; no PDF clipping; anchors/sidebar work. Build success ≠
done — look at pages.
