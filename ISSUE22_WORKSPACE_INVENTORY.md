# Issue #22 Workspace Normalization Report

Inventory checkpoint: 2026-10-05T08:46:23Z. Scope was limited to workspace inventory and safe cache cleanup. No model job, Lens execution, synthesis job, rendering run, merge, branch deletion, worktree deletion, worker release, or terminal close was performed.

The report preserves historical FAIL evidence and records the current state before any future Issue #22 revalidation.

## Classification legend

- `KEEP_ACTIVE`: required checkout, branch, runtime, or unrelated active resource.
- `KEEP_EVIDENCE_ONLY`: historical or generated evidence that must remain recoverable and should not be used as an active writer workspace.
- `SAFE_TO_REMOVE_NOW`: disposable cache or temporary derivative with no unique evidence.
- `REMOVE_AFTER_FINAL_ISSUE22_FREEZE`: retained until the final verdict and immutable evidence freeze; no removal was performed here.
- `UNKNOWN_NEEDS_REVIEW`: the inventory is incomplete or the runtime state is not strong enough to justify removal.

## Git worktrees

| Resource | Type | Branch / SHA | Status | Unique evidence | Decision | Reason |
|---|---|---|---|---|---|---|
| `/Users/shentianshuo/.agents/skills/evidentia` | primary worktree | `reader-reset-v3` / `22dcbcb5c9d935f7518a61c9457aa68a25801ae5` | dirty with untracked evidence | historical Issue #22 manifests, validation history, structural diversity report, revalidation manifest, `reader-v3-runs/` | `KEEP_ACTIVE` | Primary checkout explicitly protected. |
| `/Users/shentianshuo/.agents/skills/evidentia-reader-v3-antitemplate` | PR worktree | `reader-v3-antitemplate` / `c2039ff687aa1034706e2a42299c4ec8024d47d5` | clean | PR #26 candidate code and checked-in repair | `KEEP_ACTIVE` | Required PR #26 checkout and frozen candidate SHA. |
| `/Users/shentianshuo/.agents/skills/evidentia-benchmark-prep` | Issue #19 worktree | `benchmark-prep-issue19` / `7184eef6111a59efbbc21dd68cc81411382a9bc1` | clean | Issue #19 corpus preparation and `reader-v3-runs/` evidence, 113M | `KEEP_EVIDENCE_ONLY` | Explicitly protected Issue #19 material. |
| `/Users/shentianshuo/orca/workspaces/evidentia/bench02-issue22` | detached benchmark workspace | detached / `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` | dirty, 55 status entries | unique BENCH-02 visual crops, task inputs, Lens/Reader outputs | `KEEP_EVIDENCE_ONLY` | Canonical BENCH-02 workspace; preserve before any final cleanup. |
| `/Users/shentianshuo/orca/workspaces/evidentia/bench04-issue22` | detached benchmark workspace | detached / `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` | dirty, 21 status entries | unique BENCH-04 figures, Lens runs, validation note | `KEEP_EVIDENCE_ONLY` | Canonical BENCH-04 workspace; contains unique evidence. |
| `/Users/shentianshuo/orca/workspaces/evidentia/bench05-issue22` | detached benchmark workspace | detached / `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` | dirty, 30 status entries | unique BENCH-05 Lens, staging, visual, and validation artifacts | `KEEP_EVIDENCE_ONLY` | Canonical BENCH-05 workspace; contains unique evidence. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-goal0` | Issue #22 repair lineage | `tianshuo886/issue22-goal0` / `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` | clean | historical Goal 0 branch lineage and audit note | `REMOVE_AFTER_FINAL_ISSUE22_FREEZE` | No unique dirty files found, but preserve branch lineage until the final freeze. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-lora-visual-fix` | Issue #22 repair worktree | `tianshuo886/issue22-lora-visual-fix` / `612f705071b3554a0c251dcb1a0a88af1ef33c7d` | clean | committed generic LoRA visual extraction repair | `KEEP_EVIDENCE_ONLY` | Required visual repair provenance and historical implementation. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-provenance-hardening` | Issue #22 repair worktree | `tianshuo886/issue22-provenance-hardening` / `29c55343f81111c236075a9eb37485919cf539cc` | clean | committed receipt, envelope, and promoted-output integrity repair | `KEEP_EVIDENCE_ONLY` | Required provenance repair provenance and historical implementation. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-reval-bench02` | fresh revalidation workspace | `tianshuo886/issue22-reval-bench02` / `c2039ff687aa1034706e2a42299c4ec8024d47d5` | dirty with `reader-v3-runs/revalidation/` | six Lens receipts, input manifests, gateway records, revision memo, narrative plan | `KEEP_EVIDENCE_ONLY` | Current BENCH-02 revalidation evidence; final manuscript is still absent. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-reval-bench04` | fresh revalidation workspace | `tianshuo886/issue22-reval-bench04` / `c2039ff687aa1034706e2a42299c4ec8024d47d5` | dirty with `reader-v3-runs/revalidation/` | six Lens receipts, input manifests, gateway records, revision memo, narrative plan | `KEEP_EVIDENCE_ONLY` | Current BENCH-04 revalidation evidence; final manuscript is still absent. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-reval-bench05` | fresh revalidation workspace | `tianshuo886/issue22-reval-bench05` / `c2039ff687aa1034706e2a42299c4ec8024d47d5` | dirty with `reader-v3-runs/revalidation/` | six Lens receipts, input manifests, gateway records, revision memo, narrative plan | `KEEP_EVIDENCE_ONLY` | Current BENCH-05 revalidation evidence; final manuscript is still absent. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-summary-audit` | Issue #22 audit worktree | `tianshuo886/issue22-summary-audit` / `ee9ec8dc4313ceb03423f100584c5fb3d5da0fbc` | dirty, 141 status entries | continuation commits, revalidation receipts, invalidation records, structural and integrity reports | `KEEP_EVIDENCE_ONLY` | Unique audit lineage and unpublished evidence. |

The Git worktree inventory contains 13 worktrees. No worktree was removed.

## Local and remote branches

| Resource | Type | Branch / SHA | Status | Unique evidence | Decision | Reason |
|---|---|---|---|---|---|---|
| `master` | local branch | `4efd17397fda195a2a0dd3bf9246c55d1aa4e8c1` | not checked out | repository base lineage | `KEEP_ACTIVE` | Repository branch; outside Issue #22 cleanup. |
| `reader-reset-v3` | local branch | `22dcbcb5c9d935f7518a61c9457aa68a25801ae5` | checked out | primary checkout | `KEEP_ACTIVE` | Protected base branch. |
| `reader-v3-antitemplate` | local branch | `c2039ff687aa1034706e2a42299c4ec8024d47d5` | checked out | PR #26 candidate | `KEEP_ACTIVE` | Protected PR branch. |
| `benchmark-prep-issue19` | local branch | `7184eef6111a59efbbc21dd68cc81411382a9bc1` | checked out | Issue #19 evidence | `KEEP_EVIDENCE_ONLY` | Explicitly protected. |
| `tianshuo886/bench02-issue22` | local branch | `3d7078fd0341adf8613d7229bcb030435baa5725` | unlisted worktree branch | benchmark lineage | `REMOVE_AFTER_FINAL_ISSUE22_FREEZE` | Retain until final preservation and verdict. |
| `tianshuo886/bench04-issue22` | local branch | `3d7078fd0341adf8613d7229bcb030435baa5725` | unlisted worktree branch | benchmark lineage | `REMOVE_AFTER_FINAL_ISSUE22_FREEZE` | Retain until final preservation and verdict. |
| `tianshuo886/bench05-issue22` | local branch | `3d7078fd0341adf8613d7229bcb030435baa5725` | unlisted worktree branch | benchmark lineage | `REMOVE_AFTER_FINAL_ISSUE22_FREEZE` | Retain until final preservation and verdict. |
| `tianshuo886/issue22-goal0` | local branch | `d7f32ad690a51eec5bcaac19bd64a25eec866d4d` | checked out in worktree | Goal 0 lineage | `REMOVE_AFTER_FINAL_ISSUE22_FREEZE` | Do not remove before final freeze. |
| `tianshuo886/issue22-lora-visual-fix` | local branch | `612f705071b3554a0c251dcb1a0a88af1ef33c7d` | checked out in worktree | visual repair commit | `KEEP_EVIDENCE_ONLY` | Preserve implementation provenance. |
| `tianshuo886/issue22-provenance-hardening` | local branch | `29c55343f81111c236075a9eb37485919cf539cc` | checked out in worktree | provenance repair commit | `KEEP_EVIDENCE_ONLY` | Preserve implementation provenance. |
| `tianshuo886/issue22-reval-bench02` | local branch | `c2039ff687aa1034706e2a42299c4ec8024d47d5` | checked out in worktree | fresh BENCH-02 revalidation | `KEEP_EVIDENCE_ONLY` | Current evidence lineage. |
| `tianshuo886/issue22-reval-bench04` | local branch | `c2039ff687aa1034706e2a42299c4ec8024d47d5` | checked out in worktree | fresh BENCH-04 revalidation | `KEEP_EVIDENCE_ONLY` | Current evidence lineage. |
| `tianshuo886/issue22-reval-bench05` | local branch | `c2039ff687aa1034706e2a42299c4ec8024d47d5` | checked out in worktree | fresh BENCH-05 revalidation | `KEEP_EVIDENCE_ONLY` | Current evidence lineage. |
| `tianshuo886/issue22-summary-audit` | local branch | `ee9ec8dc4313ceb03423f100584c5fb3d5da0fbc` | checked out in worktree | summary audit lineage | `KEEP_EVIDENCE_ONLY` | Unique audit history. |
| `origin/reader-reset-v3` | remote branch | `cd3b6eed17ca49ae4adab01c2a76ffd7447d254c` | available locally and on origin | PR base | `KEEP_ACTIVE` | Protected PR base. |
| `origin/reader-v3-antitemplate` | remote branch | `c2039ff687aa1034706e2a42299c4ec8024d47d5` | available locally and on origin | PR head | `KEEP_ACTIVE` | Protected PR head. |
| remote `origin/*issue22*` refs | remote branch inventory | none returned by `git ls-remote --heads origin` | no separately named remote Issue #22 refs | none | `UNKNOWN_NEEDS_REVIEW` | Only the two reader refs above are present; no remote `tianshuo886/*` refs were published. |

The local repository has 14 branches. No branch was deleted or force-updated.

## Orca agents, child sessions, and asynchronous workflows

| Resource | Type | Branch / SHA | Status | Unique evidence | Decision | Reason |
|---|---|---|---|---|---|---|
| `run_67024d229c76` | current Issue #22 orchestration run | coordinator on primary checkout / candidate `c2039ff` | coordinator terminal connected; 31 dispatch records | final repair audit, worker lifecycle, quota-block evidence | `KEEP_EVIDENCE_ONLY` | Preserve the current audit run. No worker release or reset performed. |
| `run_5f6584033dc1` | prior Issue #22 orchestration run | historical candidate `46de137...` | completed historical run | prior 18-Lens execution audit | `KEEP_EVIDENCE_ONLY` | Immutable historical record. |
| `run_bb949bb71bec` | prior Issue #22 orchestration run | repair lineage | settled historical run | provenance and visual repair audit | `KEEP_EVIDENCE_ONLY` | Immutable historical record. |
| `run_2c6331d7e9c5` | prior Issue #22 orchestration run | Goal 0 DAG | settled historical run | candidate freeze and benchmark DAG audit | `KEEP_EVIDENCE_ONLY` | Immutable historical record. |
| current run workers | supervised child workers | BENCH-02/04/05 revalidation roots | 27 `succeeded/completed/reclaimable`; 4 `stopped/failed/retained` | worker outputs and lifecycle messages | `UNKNOWN_NEEDS_REVIEW` | Terminals are connected/retained in Orca; release requires a separate runtime action and was intentionally not performed during normalization. |
| live Orca terminals | active agent sessions | 60 connected terminals total; 1 primary coordinator, 27 current-run worker-owned panes, plus historical/reclaimable panes and unrelated sessions | connected | terminal previews, worker output, child-session context | `UNKNOWN_NEEDS_REVIEW` | Runtime liveness is not a deletion authorization. Leave untouched. |
| `.pi/agent/sessions/` Issue #22 session archives | child session records | primary, `bench02`, `bench04`, `bench05`, `issue22-goal0`, `issue22-summary-audit` paths found | persisted | full child transcripts and goal/audit records | `KEEP_EVIDENCE_ONLY` | Preserve session history. |
| `/Users/shentianshuo/.claude/projects/-Users-shentianshuo-orca-workspaces-evidentia-issue22-summary-audit` | external agent session archive | summary-audit workspace | persisted | Claude/agent audit transcript | `KEEP_EVIDENCE_ONLY` | Preserve immutable audit records. |
| unrelated RSE sessions and `/Users/shentianshuo/Documents/杭电研/tian` terminal | unrelated active sessions | outside Issue #22 | connected | unrelated work | `KEEP_ACTIVE` | Outside cleanup scope; no action taken. |

## Issue #22 evidence and audit directories

| Resource | Type | Branch / SHA | Status | Unique evidence | Decision | Reason |
|---|---|---|---|---|---|---|
| `/Users/shentianshuo/.agents/skills/evidentia/ISSUE22_EVIDENCE_MANIFEST.json` | historical evidence manifest | primary / `reader-reset-v3` | present; SHA-256 `82b35e32580f0ec8d879469ad4bdd5960daaf10948cae1437d4679055894a026` | historical FAIL evidence | `KEEP_EVIDENCE_ONLY` | Do not rewrite or delete. |
| `/Users/shentianshuo/.agents/skills/evidentia/ISSUE22_REAL_PAPER_VALIDATION.md` | historical release report | primary | present; SHA-256 `ca784043d52e50d2fc8bd932ee3857f510716474a44830f372aa9230b24c377a` | historical FAIL / NEEDS_REVISION state | `KEEP_EVIDENCE_ONLY` | Historical verdict is immutable evidence. |
| `/Users/shentianshuo/.agents/skills/evidentia/ISSUE22_STRUCTURAL_DIVERSITY_EXACT.json` | structural diversity report | primary | present; SHA-256 `3b067a4c59cb05c538d8a60ba2c50a17611a26f1ecaba4ce994e214c84062d01` | structural diversity PASS | `KEEP_EVIDENCE_ONLY` | Required release evidence. |
| `/Users/shentianshuo/.agents/skills/evidentia/ISSUE22_REVALIDATION_EVIDENCE.json` | current revalidation manifest | primary / candidate `c2039ff` | present; SHA-256 `5fc84de00bf6831d18886c08c97e72d400dbd0a078117a3fd2bfbf14e8c216a7` | 18 accepted Lens receipt records, downstream artifacts, blocker state | `KEEP_EVIDENCE_ONLY` | Current revalidation is blocked and must remain recoverable. |
| `/Users/shentianshuo/.agents/skills/evidentia/reader-v3-runs/` | primary evidence tree | primary | 121M, 893 files | canonical source, Reader, and benchmark artifacts | `KEEP_EVIDENCE_ONLY` | Required evidence tree. |
| `/Users/shentianshuo/orca/evidence/issue22/pr26-reader-v3-runs/` | preserved PR evidence copy | PR #26 candidate | 59M, 660 files; preservation manifest present | preserved pre-revalidation PR evidence | `KEEP_EVIDENCE_ONLY` | Explicit preservation destination. |
| `/Users/shentianshuo/orca/evidence/issue22/visual-revalidation/` | LoRA visual repair evidence | candidate visual repair | 13M; repaired F01 and distinct T04/F02 assets | F01 completion and collision repair evidence | `KEEP_EVIDENCE_ONLY` | Required visual repair evidence. |
| `/Users/shentianshuo/orca/workspaces/evidentia/issue22-summary-audit/reader-v3-runs/` | audit evidence tree | `ee9ec8d` | 453M, 3762 files | unique receipts, invalidation records, structural/integrity audits | `KEEP_EVIDENCE_ONLY` | Unique unpublished audit evidence. |
| `issue22-reval-bench02/reader-v3-runs/revalidation/` | fresh BENCH-02 evidence | `c2039ff` | 114M, 1487 files | six Lens receipts and downstream memo/plan | `KEEP_EVIDENCE_ONLY` | Final manuscript and post-repair Lens rerun remain outstanding. |
| `issue22-reval-bench04/reader-v3-runs/revalidation/` | fresh BENCH-04 evidence | `c2039ff` | 124M, 991 files | six Lens receipts and downstream memo/plan | `KEEP_EVIDENCE_ONLY` | Final manuscript and post-repair Lens rerun remain outstanding. |
| `issue22-reval-bench05/reader-v3-runs/revalidation/` | fresh BENCH-05 evidence | `c2039ff` | 86M, 720 files | six Lens receipts and downstream memo/plan | `KEEP_EVIDENCE_ONLY` | Final manuscript and post-repair Lens rerun remain outstanding. |
| `PHASE_A_AUDIT.md` in primary and Issue #22 worktrees | audit reports | respective worktree SHAs | present | phase audit history | `KEEP_EVIDENCE_ONLY` | Preserve audit trail. |
| Issue #19 evidence | worktree/evidence inventory | `benchmark-prep-issue19` / `7184eef` | found and preserved | corpus preparation and benchmark evidence | `KEEP_EVIDENCE_ONLY` | Explicitly protected. |
| Issue #20 worktree/evidence | requested protected resource | no named worktree, branch, or matching evidence path found | unresolved | no resource could be verified | `UNKNOWN_NEEDS_REVIEW` | Do not delete or infer absence as proof of completion; review outside this normalization pass. |

## Temporary directories

| Resource | Type | Branch / SHA | Status | Unique evidence | Decision | Reason |
|---|---|---|---|---|---|---|
| `/private/tmp/issue22-pr26-code` | temporary source snapshot | copied PR-era source; not a Git worktree | 115M; differs from current PR checkout in seven generated/test files | source snapshot used by prior checks | `KEEP_EVIDENCE_ONLY` | Not proven redundant byte-for-byte; retain for audit recovery. |
| `/private/tmp/issue22-writer-B05` | failed Lead Writer scratch bundle | downstream attempt | 12M; task, result, source, model, visual, and equation inputs | quota-blocked writer attempt and exact input bundle | `KEEP_EVIDENCE_ONLY` | Preserve failure context and input provenance. |
| `/private/tmp/ISSUE22_EVIDENCE_MANIFEST.json` and `/private/tmp/issue22-*.json` audit outputs | temporary audit records | current and historical runs | present | worker lists, run lists, structural checks, manifests, and checker output | `KEEP_EVIDENCE_ONLY` | Contents are small but may be needed to reconstruct the audit; no deletion. |
| `/private/tmp/claude-501/-Users-shentianshuo-orca-workspaces-evidentia-issue22-summary-audit` | temporary agent runtime directory | summary-audit | present | runtime scratch state | `KEEP_EVIDENCE_ONLY` | Keep with the related session and audit lineage. |
| Python `.pytest_cache`, `__pycache__`, and interpreter bytecode caches under protected Evidentia roots and `/private/tmp/issue22-pr26-code/.pytest_cache` | generated cache | derived from protected worktrees | removed 16 cache directories | no unique evidence; regenerable test cache only | `SAFE_TO_REMOVE_NOW` | Only disposable cache directories were removed after checking their contents were bytecode/test cache files. |

## Cleanup performed

Only the following disposable cache directories were removed:

- `.pytest_cache` from the primary checkout, PR checkout, Issue #19 checkout, and Issue #22 worktrees.
- Python interpreter cache directories under `~/Library/Caches/com.apple.python` for the Evidentia roots and two `evidentia-audit-*` cache directories.
- `/private/tmp/issue22-pr26-code/.pytest_cache`.

The cleanup removed 18 cache directories. No source, PDF, image, manifest, receipt, run, branch, worktree, session archive, worker record, or audit directory was removed.

## Post-cleanup state

- Primary checkout remains on `reader-reset-v3` at `22dcbcb5c9d935f7518a61c9457aa68a25801ae5`.
- PR #26 checkout and remote head remain at candidate `c2039ff687aa1034706e2a42299c4ec8024d47d5`.
- Historical Issue #22 FAIL evidence remains present and unchanged.
- Required structural diversity, gateway receipt, Lens provenance, and LoRA visual repair evidence remains present.
- All 13 Git worktrees remain registered.
- All 14 local branches remain.
- No remote Issue #22 branch was deleted.
- All 60 live Orca terminals and all current-run worker records remain registered.
- Issue #22 remains blocked before the post-repair Lens rerun and final manuscripts.

Workspace normalization is complete. No scientific revalidation or expensive model work was started.
