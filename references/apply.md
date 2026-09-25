# /evidentia-apply — contextual re-read → Research Delta

Command: `/evidentia-apply --paper <paper-output-dir> --project <project-main-doc> [--focus <section>]`

1. Refuse unfrozen dirs (`manifest.json` status must be FROZEN). Load frozen
   model + one project doc. Re-scan the paper for evidence the blind read
   underweighted. New relevance notes allowed; frozen observations immutable
   (real errors → explicit `paper_model_revision`, never silent edits).
2. Split Side Findings (real off-mainline phenomena) from Portable Components;
   pack components into Transfer Units with verdicts
   DIRECT / ADAPT / INSPIRATION_ONLY / REJECT + specific reason codes
   (`different_data_regime, different_label_semantics, different_scale,
   different_physical_assumption, different_sensor_or_modality,
   different_causal_interpretation, different_deployment_constraint,
   insufficient_evidence, already_covered, cost_exceeds_value`).
3. Delta types: New Evidence, Changed Belief, New Unknown, Portable Method,
   Invalidated/Deprioritized Plan (deleting a bad experiment = success),
   New Experiment. `NO_NEW_ACTIONABLE_EXPERIMENT` is legal; repackaging
   existing plans as new is forbidden.
4. Each experiment proposal: Source (which evidence) / Delta vs current plan /
   Hypothesis / Integration point / Cost / Risk / Decision Value (what success
   AND failure each change — mandatory, not "may improve R²").
5. Write `apply/<project>/research_delta.json`; same frozen paper supports
   many projects (`apply/project_A|B|C/`); update unified reader; re-verify
   links. Report delta counts + paths in chat, not the full reader.
