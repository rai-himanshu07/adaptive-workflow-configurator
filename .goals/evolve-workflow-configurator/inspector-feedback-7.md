# Inspector feedback — iteration 7

## Verdict

**FAIL**

Iteration 7 fixes the ordinary latest-receipt rules, wall-clock field pairing,
honest rendered-path terminology, real GUI follow-up reporting, and the usual
fully recomputed omitted-merge case. The complete state model still has two
adversarial bypasses: receipt status is not integrity-bound, and changing the
recorded configuration to disable a previously applied merge suppresses the
required partial/manual result. A lifecycle timestamp can also claim that an
operation completed before it started.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all seven Builder
  iterations.
- Used all six prior Inspector reports as mandatory regression lists.
- Read the complete iteration-7 diff and resulting core, typed receipt
  component, CLI, GUI, docs, hooks, and tests.
- Ran filesystem-heavy checks on project-local tmpfs in an unprivileged
  user/mount namespace.
- Exercised unreadable traversal as mapped EUID 1 and the real Tk window on
  `DISPLAY=:0`.

The Builder commit title and trailers are correct. Both research documents
remain tracked and no dependency manifest changed.

## Blocking findings

### 1. Receipt status is not covered by integrity and can bypass latest-state refusal

`receipt.INTEGRITY_FIELDS` (`receipt.py:28-60`) omits both `status` and
`rolled_back_at`, although `status` controls whether no-argument rollback may
run. I applied and rolled back a no-merge receipt, then changed only:

```json
"status": "rolled_back"  ->  "status": "applied"
```

without recomputing the digest. Observed:

```text
hash_unchanged=True
receipt.load validated_status=applied
no-argument rollback=ACCEPTED
```

The normal algorithm correctly chooses the newest receipt across every status
and refuses real `rolled_back` and `partial` receipts. The state field itself is
not corruption-protected, so a one-field edit defeats that rule. Include
`status` (and preferably transition metadata) in the integrity payload and
recompute it during the legitimate transition.

### 2. Fully recomputed omitted-merge evidence can bypass partial by disabling the merge

The unchanged-configuration forgery from iteration 6 now becomes partial as
intended. A structurally complete bypass remains:

1. Apply the `.gitignore` additive merge.
2. Delete its backup and merge entry.
3. Change the receipt configuration to disable artifact management.
4. Recompute the exact rendered inventory/config hash.
5. Mark `.gitignore` as `not-enabled`.
6. Recompute all covered and integrity hashes.

Observed:

```text
OMITTED_MERGE_DISABLED_CONFIG
  result=ACCEPTED
  status=rolled_back
  manual_rendered_paths=[]
  restored=[]
  artifacts_rule_still_present=True
```

`_validate_merge_evidence` immediately continues for a path disabled by the
editable receipt configuration (`receipt.py:678-685`) without checking current
additive state. This violates the explicit requirement that **fully recomputed**
omitted safe-merge evidence always be partial/manual.

Inspect current additive state before the enabled/disabled branch. Any
documented safe path that currently contains generated additive state but lacks
a verified inverse pair must be manual/partial, regardless of recorded config.

### 3. Operation lifecycle timestamps are not wall-clock coherent

ISO `created_at` and `created_at_ns` are now correctly cross-checked and
process-local monotonic values no longer order receipts. However
`operation_started_ns` is only checked for positivity. I set it ten seconds
*after* the matching completion time, recomputed integrity, and the receipt
loaded and was selected:

```text
WALLCLOCK_LIFECYCLE_INCONSISTENCY
  result=ACCEPTED
  operation_started_ns > created_at_ns=True
```

The field is wall-clock (`time.time_ns`) and should not describe an impossible
start/completion order. Validate `operation_started_ns <= created_at_ns` with a
documented clock-adjustment policy, or remove the field if it cannot be made
meaningful. `monotonic_ns` is currently retained for compatibility and assigned
the wall-clock start value; its name should not imply a monotonic sample.

## Major successes

### Latest receipt behavior in normal state

- Reversed lexical UUID suffixes no longer affect selection; the later
  same-second receipt was selected.
- Every candidate is validated; a malformed/inconsistent candidate caused
  refusal with no project mutation.
- Exact validated wall-clock ties were refused as ambiguous.
- A genuinely newest `rolled_back` receipt was refused without older fallback.
- A genuinely newest `partial` receipt was refused without older fallback.
- Modifying `monotonic_ns` did not change ordering.
- `created_at_ns` disagreement with ISO `created_at` was refused.

The remaining status-integrity bypass is finding 1.

### Rendered inventory and honest terminology

- Fully recomputed extra, missing, or reassigned receipt-listed paths outside
  the configuration-rendered universe were refused without mutation.
- Exact rendered content moved between pre-existing and receipt-listed
  inventories was reported only as
  `configuration_consistent_rendered_paths`; API/CLI/GUI made no historical
  creation claim.
- Missing and changed rendered files produced `partial` with exact
  `missing_rendered_paths` and `manual_rendered_paths`.
- The real GUI report displayed every consistent, missing, manual, restored,
  and required-directory follow-up path.

### Deletion-free exact-inverse rollback

- Valid rollback wrote exactly `.gitignore` and
  `.vscode/settings.json` plus receipt metadata.
- Every rendered project file and required directory remained present and
  unchanged.
- Reassigned merge path/backup, changed backup, non-forward current content,
  duplicate entry, and missing entry field all raised before project mutation.
- Exact documented forward/inverse pairs restored both safe merges with modes.
- Every rollback fault phase restored applied content/state and a second
  rollback succeeded.

## All prior regression results

| Regression | Iteration-7 result |
|---|---|
| Legacy/configurator dry-run no mutation | **PASS** |
| Apply failure transactional cleanup | **PASS** |
| Rollback recovery plus retry for every phase | **PASS** |
| Post-replace receipt-write retry | **PASS** |
| Required directory creation/reapply/preservation | **PASS** |
| No rendered project-file or required-directory deletion | **PASS** |
| Unreadable traversal as EUID 1 | **PASS** |
| Shared CLI/core installer | **PASS** |
| Preset/override/guard behavior | **PASS** |
| Directory/config/proposal/hash/target drift coherence | **PASS** |
| Directory receipt tamper/duplicate/escape/forgery | **PASS safely** |
| Receipt-listed inventory extra/missing/reassignment | **PASS**, refused |
| Exact safe-merge path/backup/forward transform | **PASS** |
| All required receipt fields | **PASS**, 33/33 actionable/no traceback |
| GUI layout/preview/export/identity/tri-state | **PASS** |
| GUI rollback follow-up path listing | **PASS** |
| Same-second chronological selection | **PASS** |
| Invalid candidate / exact wall-clock tie | **PASS**, refused |
| Newest real rolled-back/partial receipt | **PASS**, refused without fallback |
| ISO/nanosecond timestamp disagreement | **PASS**, refused |
| Unchanged-config omitted merge+backup | **PASS**, partial/manual |
| Disabled-config omitted merge+backup | **FAIL**, false `rolled_back` |
| Receipt status integrity | **FAIL**, one-field status edit accepted |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Full legacy tests and independent all-flag
   installation passed: defaults, commands, profiles, every MCP choice,
   sandbox opt-out, security hooks, context settings, additive `.gitignore`,
   collision refusal (`rc=3`), opt-outs, and dry-run.

2. **PASS — shared typed layers.** Core is argparse/Tkinter-free; adapters share
   its operations; receipt construction, schema validation, coherence,
   selection, and classification remain centralized in `receipt.py`.

3. **PASS — configuration model.** Versioned JSON supports all required
   dimensions, aliases, and overrides with round-trip and actionable errors.

4. **PASS — import/export/defaults.** External configuration operations do not
   create the target, and omitted options preserve personal Python/data-science
   defaults.

5. **PASS — concrete rigor.** Every policy dimension, preset, string/boolean
   override, and GUI guard auto/on/off transition works.

6. **PASS — deterministic adaptation.** Complexity, scope, testing, and rigor
   change documented low/high-risk workflow behavior deterministically.

7. **PASS — lean-change contract.** Reuse, non-goals, anti-speculation,
   minimal-surface, and protected-boundary guidance remains without external
   tools or universal LOC rules.

8. **PASS — optional GUI controls.** Real Tk rows are distinct and all required
   target, identity, workflow, policy, profile, MCP, command, safety, and
   override controls remain visible without third-party dependencies.

9. **PASS — GUI operations/reporting.** Real preview/export, confirmation,
   concise status, complete rollback lists, identity, tri-state policy, and
   both headless paths passed.

10. **PASS — structured brownfield analysis.** Manifests/languages,
    environment conflict, uncertain commands, Git/customization/partial state,
    collisions, hazards, directory state, and incomplete scans are represented.

11. **PASS — no-mutation paths.** Analyze/preview snapshots matched. Legacy and
    configurator dry-run wrote no target, output, receipt, file, or directory.

12. **PASS — safe apply.** User AGENTS/MCP remain byte-identical; only missing
    files and documented additive `.gitignore`/settings merges are applied with
    modes preserved.

13. **PASS — proposals.** API/CLI/GUI contain intended content, hashes,
    metadata, and diffs; ordinary drift produces coherent current receipts.

14. **FAIL — state/tamper completeness.** Actual newest status and chronology
    rules pass, but status is not integrity-bound and fully recomputed disabled
    configuration can conceal omitted merge evidence as complete rollback.

15. **PASS for mutation safety.** Rollback is deletion-free, exact-inverse-only,
    path/symlink defensive, and transactionally retryable. The remaining
    failures misclassify state but do not delete or overwrite arbitrary content.

16. **PASS — idempotency/drift.** Unchanged reapply is a no-op. Missing
    directory, config, proposal, target hash, receipt hash, and target drift
    prevent stale reuse and create coherent current receipts.

17. **PASS — new-project workflow.** New install is complete,
    placeholder-free, doctor-clean, stable on reapply, and deletion-free on
    rollback. Detection remains advisory.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live authority, degraded mode, and optional graph
    capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI guard intent and opt-out work;
    supported events, local-only scope, timeout, and fail-open behavior remain
    truthful.

20. **FAIL — two documentation claims remain too strong.** Documentation
    correctly explains non-provenance rendered terminology and ordinary latest
    selection. It states that a partial result is never presented as complete
    and that invalid state is refused; findings 1–3 disprove those claims for
    adversarial but structurally accepted state.

21. **FAIL — focused adversarial gaps.** The 62 passing tests cover normal
    latest selection, actual statuses, ties, timestamp disagreement,
    inventories, merge evidence, GUI terminology, and fault retries. They omit
    status-field integrity, disabled-config omitted-merge evidence, and
    operation-start/completion ordering.

22. **PASS — full quality gate/workflows.** All 62 tests passed in 3.353s on
    healthy project-local tmpfs. Doctor, placeholders, real/headless GUI,
    legacy, new, existing, and partial workflows passed with observed output
    and no network, credential, or production-data reliance.

23. **PASS with size caveat — centralized maintainability remains improved.**
    No dependency/service/runtime was added. Receipt state still has one typed
    owner and core remains substantially smaller than iteration 5. Iteration 7
    added 139 runtime lines and 157 test lines; fixes should tighten the existing
    model rather than add another layer or duplicate fields.

24. **PASS — preservation.** Both research documents remain tracked; no
    unrelated user or dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Complete unittest discovery on project-local tmpfs — **PASS**, 62 tests,
  3.353s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags, import/export, collision, and dry-run —
  **PASS**.
- New/existing analyze/preview/apply/reapply/rollback — **PASS** for normal
  receipts.
- Ordinary drift-coherence branches — **PASS**.
- All 33 required receipt fields — **PASS**, actionable/no traceback.
- Required directories/rendered files under valid/forged/fault cases —
  **PASS**, deletion-free.
- Every rollback fault plus second retry — **PASS**.
- Exact safe merges and forged path/backup/content cases — **PASS**.
- API/CLI/real GUI honest rendered/missing/manual lists — **PASS**.
- Real GUI layout, preview/export, tri-state, and identity — **PASS**.
- Direct/CLI headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Unprivileged unreadable traversal — **PASS**.
- Newest actual rolled-back/partial receipt — **PASS**, no fallback.
- Invalid newest / exact tie / ISO-ns mismatch — **PASS**, refused.
- Status-only tamper — **FAIL**, non-applied receipt accepted as applied.
- Disabled-config omitted merge evidence — **FAIL**, false complete status.
- Start-after-completion timestamp — **FAIL**, validated and selectable.

## Required next iteration

1. Bind `status` and transition metadata into receipt integrity.
2. Check current additive state for every safe-merge path before the
   configuration-enabled branch; no verified pair must always be manual/partial.
3. Validate or remove lifecycle timing fields so start cannot follow completion.
4. Add these three adversarial regressions to the centralized receipt tests
   without introducing another validation path.
