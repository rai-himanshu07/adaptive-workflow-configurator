# Inspector feedback — iteration 6

## Verdict

**FAIL**

Iteration 6 materially improves structure and fixes deletion-free inventory and
GUI reporting. It still does not safely model “latest” rollback or fully
recomputed omitted merge evidence. A second no-argument rollback can silently
select an older receipt and restore a merge, and a self-consistent receipt can
erase all evidence of an applied merge while returning `rolled_back`.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all six Builder
  iterations.
- Used all five prior Inspector reports as mandatory regression lists.
- Read the complete iteration-6 diff and resulting core, typed receipt
  component, CLI, GUI, docs, hooks, and tests.
- Ran filesystem-heavy checks on project-local tmpfs in an unprivileged
  user/mount namespace.
- Exercised unreadable traversal as mapped EUID 1 and the real Tk window on
  `DISPLAY=:0`.

The Builder commit title and trailers are correct. Both research documents
remain tracked and no dependency manifest changed.

## Blocking findings

### 1. No-argument rollback skips the newest completed receipt and mutates an older apply

`receipt.select_latest` validates all files but collects only receipts whose
status is `applied` before choosing the maximum timestamp tuple
(`receipt.py:385-414`). A newer `rolled_back` or `partial` receipt is silently
skipped.

Reproduction:

1. Apply receipt A, which additively merges `.gitignore`.
2. Apply later receipt B with a different configuration and no merge.
3. Explicitly roll back B, making the chronologically newest receipt
   `rolled_back`.
4. Invoke no-argument rollback again.

Observed:

```text
SELECT_AFTER_NEWEST_ROLLEDBACK
  result=ACCEPTED
  selected=older receipt A
  project mutation=True
```

The second rollback restored A's older `.gitignore` backup. The CLI promises
that omitted `RECEIPT_OR_ID` uses the latest receipt; it must choose the newest
validated receipt first and then refuse if that receipt is not rollbackable,
rather than fall back to older state.

The timestamp validation is also incomplete. I increased an older receipt's
`created_at_ns`, recomputed its digest, and left its ISO `created_at` visibly
older. Selection chose the old receipt. `created_at_ns` must be cross-checked
against parsed `created_at`; process-local monotonic time should not establish
cross-process chronology. Exact-key ties and malformed newest candidates were
correctly refused without mutation.

### 2. Fully recomputed omitted merge evidence still returns false `rolled_back`

Starting from a valid `.gitignore` safe merge, I:

- removed the merge entry and its backup;
- changed merge evidence to `identical`;
- added the current full-file hash to `preserved_merge_outputs`;
- moved `.gitignore` into the ordered pre-existing inventory; and
- recomputed covered and integrity hashes.

The internally consistent receipt passed classification:

```text
FULLY_CONSISTENT_OMITTED_MERGE
  result=ACCEPTED
  status=rolled_back
  restored=[]
  manual_generated_paths=[]
  artifacts_rule_still_present=True
```

`_validate_merge_evidence` (`receipt.py:593-648`) trusts editable
`preexisting_paths`, `merge_evidence`, and `preserved_merge_outputs` together.
It therefore cannot distinguish a genuinely pre-existing identical additive
state from omitted apply evidence.

This must produce an explicit `partial`/manual result (or a conservative
refusal), never complete `rolled_back`. A simpler safe rule is: when an enabled
safe-merge path currently has generated additive state but lacks a verified
merge pair, report it as manual/ambiguous regardless of receipt assertions.
Deleting a backup from an otherwise unchanged receipt currently raises
`RollbackError`; that is safe, but it also does not provide the specifically
requested partial/manual API result.

### 3. Configuration-consistent content can still be reclassified as generated

Extra, missing, and reassigned created entries outside the rendered universe
are now correctly rejected. However, if an exact rendered `AGENTS.md` existed
before apply, a fully recomputed receipt can move it from `preexisting_paths`
to `created`. Classification accepts it and reports:

```text
PREEXISTING_EXACT_RECLASSIFIED
  status=rolled_back
  reported_generated=True
  file_preserved=True
```

This cannot cause deletion, and the docs correctly limit the claim to
“configuration-consistent” content. Still, `preserved_generated_paths` is not
historical creation proof; it is only a rendered-content classification based
on mutually editable inventories. Keep that trust boundary explicit in every
API/CLI/GUI label (for example, “receipt-listed rendered paths”) rather than
implying apply provenance.

## Major iteration-6 successes

### Typed receipt centralization

- `ReceiptDocument` and `RollbackClassification` centralize validated state.
- `receipt.py` owns construction, schema/integrity validation, candidate
  selection, rendered/created inventories, safe-merge evidence, coherent reuse,
  and rollback classification.
- Core now calls `build`, `find_coherent`, `resolve`, and `classify`; the old
  parallel receipt parser/coherence/merge verifier was removed.
- `core.py` shrank from 3,425 to 2,854 lines. The new cohesive receipt module is
  962 lines, so runtime code grew by 391 lines overall, but the separation and
  single ownership are materially clearer than iteration 5.

### Deletion-free and exact-merge behavior

- Valid rollback wrote exactly `.gitignore` and `.vscode/settings.json` plus its
  receipt.
- Every generated file and required directory remained unchanged.
- Fully recomputed extra/missing/reassigned created inventories raised
  `RollbackError` without project mutation.
- Reassigned merge path/backup, changed backup, non-forward current content,
  duplicate entry, and missing field all raised before mutation.
- Exact backup→applied transforms restored both documented merges and preserved
  modes.
- Every rollback phase and receipt-update fault restored applied state; a
  second rollback succeeded.

### User-facing rollback reporting

- API reports exact preserved, missing, manual, restored, and required-directory
  lists for valid receipts.
- CLI text lists every preserved path and returns code 1 for `partial`, while
  listing missing/manual paths.
- The real GUI report pane now lists every preserved path and displays both
  missing and manually changed paths for a partial rollback.

## All prior regression results

| Regression | Iteration-6 result |
|---|---|
| Legacy/configurator dry-run no mutation | **PASS** |
| Apply failure transactional cleanup | **PASS** |
| Rollback recovery and second retry for every phase | **PASS** |
| Post-replace receipt failure retry | **PASS** |
| Required directory creation/reapply/preservation | **PASS** |
| No project-file or required-directory deletion | **PASS** |
| Unreadable traversal under EUID 1 | **PASS** |
| Shared CLI/core installer | **PASS** |
| Preset/override/guard behavior | **PASS** |
| Directory/config/proposal/hash/target drift coherence | **PASS** |
| Directory receipt tamper/duplicate/escape/forgery | **PASS safely** |
| Created inventory extra/missing/reassignment outside rendered universe | **PASS**, refused |
| Exact safe-merge path/backup/forward transform | **PASS** |
| All required receipt fields | **PASS**, 33/33 actionable/no traceback |
| GUI layout/preview/export/identity/tri-state | **PASS** |
| GUI rollback path listing | **PASS** |
| Same-second normal chronology | **PASS** |
| Exact timestamp-key tie | **PASS**, refused |
| Invalid candidate | **PASS**, refused without mutation |
| Newest non-applied receipt handling | **FAIL**, older applied receipt selected |
| Fully self-consistent omitted merge+backup | **FAIL**, false `rolled_back` |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Full legacy tests and independent all-flag
   installation passed: defaults, commands, profiles, every MCP choice,
   sandbox opt-out, security hooks, context settings, additive `.gitignore`,
   collision refusal (`rc=3`), opt-outs, and dry-run.

2. **PASS — shared typed layers.** Core is argparse/Tkinter-free; CLI and GUI
   share its operations; typed receipt construction/parsing/coherence is now
   owned by one cohesive component rather than duplicated.

3. **PASS — configuration model.** Versioned JSON supports all required
   dimensions, aliases, and overrides with exact round-trip and actionable
   errors.

4. **PASS — import/export/defaults.** External config import/export does not
   create the target, and omitted options retain personal Python/data-science
   defaults.

5. **PASS — concrete rigor.** Every policy dimension, preset, string/boolean
   override, and GUI guard auto/on/off transition works.

6. **PASS — deterministic adaptation.** Complexity, scope, testing, and rigor
   alter documented guidance deterministically, including low-risk no-code and
   high-risk diagnostics/review paths.

7. **PASS — lean-change contract.** Required reuse/non-goal/anti-speculation/
   minimal-surface/protected-boundary guidance remains without external tools or
   hard LOC rules.

8. **PASS — optional GUI controls.** Real Tk rows are distinct and all target,
   identity, workflow, policy, profile, MCP, command, safety, and override
   controls remain visible without third-party dependencies.

9. **PASS — GUI operations/reporting.** Real preview/export, confirmations,
   concise status, full rollback follow-up lists, identity, tri-state policy,
   and both headless entry points passed.

10. **PASS — structured brownfield analysis.** Manifests/languages,
    environment conflict, uncertain commands, Git/customization/partial state,
    collisions, hazards, directory state, and incomplete scans are represented.

11. **PASS — no-mutation paths.** Analyze/preview snapshots matched. Legacy and
    configurator dry-run wrote no target, output, receipt, file, or directory.

12. **PASS — safe apply.** User AGENTS/MCP remain byte-identical; only missing
    files and documented additive `.gitignore`/settings merges are applied with
    modes preserved.

13. **PASS — proposals.** API/CLI/GUI contain intended content, hashes,
    metadata, and diffs; ordinary drift produces current coherent receipts.

14. **FAIL — ambiguous/latest and omitted evidence.** Rollback is deletion-free
    and exact-write-safe, but it can select an older receipt after the newest was
    completed and can accept fully recomputed omitted merge evidence as complete
    rollback.

15. **FAIL — wrong historical safe restore.** Path/symlink hazards, incomplete
    scans, apply recovery, and transactional rollback retry all pass. Silent
    fallback from the newest completed receipt to an older applied receipt can
    still restore an unintended historical merge.

16. **PASS — apply idempotency/drift.** Unchanged reapply is a no-op. Missing
    directory, config, proposal, target-file hash, receipt hash, and target
    drift prevent stale reuse and create coherent current receipts.

17. **PASS — new-project workflow.** New install is complete,
    placeholder-free, doctor-clean, stable on reapply, and deletion-free on
    rollback. Detection remains advisory.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live authority, degraded mode, and optional graph
    capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI guard intent and opt-out work;
    supported events, local-only scope, timeout, and fail-open behavior remain
    truthful.

20. **FAIL — documentation overstates selection and completeness.** Coverage is
    otherwise complete and the receipt trust boundary is substantially clearer.
    “Latest” selection silently skips a newer completed receipt, and “a partial
    result is never presented as complete” is disproved by the fully recomputed
    omitted-merge reproduction.

21. **FAIL — focused gaps remain.** The 59 passing tests cover normal
    chronology, ties, invalid candidates, inventories, merge checks, GUI lists,
    and fault retries. They do not test no-argument rollback after the newest
    receipt becomes rolled-back/partial, cross-consistency of ISO and nanosecond
    creation time, fully consistent omitted merge+backup plus pre-existing
    inventory, or exact rendered content reclassified from pre-existing to
    created.

22. **PASS — full quality gate/workflows.** All 59 tests passed in 3.629s on
    healthy project-local tmpfs. Doctor, placeholders, real/headless GUI,
    legacy, new, existing, and partial CLI workflows passed with observed output
    and no network, credential, or production-data reliance.

23. **PASS with size caveat — maintainability improved structurally.** No
    dependency/service/runtime was added. Core shrank by 571 lines and receipt
    behavior has one typed owner. Combined core+receipt runtime grew by 391
    lines and the focused test file reached 1,169 lines, so further fixes should
    simplify the trust/state model rather than add more parallel fields.

24. **PASS — preservation.** Both research documents remain tracked; no
    unrelated user or dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Complete unittest discovery on project-local tmpfs — **PASS**, 59 tests,
  3.629s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags, import/export, collision, and dry-run —
  **PASS**.
- New/existing analyze/preview/apply/reapply/explicit rollback — **PASS**.
- Ordinary drift-coherence branches — **PASS**.
- All 33 centralized required receipt fields — **PASS**, actionable.
- Required directory and generated-file deletion-free behavior — **PASS**.
- Every rollback fault and post-replace failure followed by retry — **PASS**.
- Exact safe merge and forged path/backup/content cases — **PASS**.
- Created inventory extra/missing/reassigned outside universe — **PASS**.
- API/CLI/real GUI preserved/missing/manual path output — **PASS**.
- Real GUI layout, preview/export, tri-state policy, and identity — **PASS**.
- Direct/CLI headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Unprivileged unreadable traversal — **PASS**.
- Newest rolled-back receipt handling — **FAIL**, older receipt restored.
- Forged timestamp cross-consistency — **FAIL**, older ISO receipt selected.
- Fully consistent omitted merge evidence — **FAIL**, false `rolled_back`.

## Required next iteration

1. Select the chronologically newest validated receipt across all statuses, then
   refuse if it is not `applied`; never fall back to an older apply.
2. Cross-check `created_at_ns` against parsed `created_at` and avoid using
   process-local monotonic time as cross-process chronology.
3. Treat enabled current additive state without a verified merge pair as
   partial/manual regardless of editable `preexisting`/`identical` assertions.
4. Rename configuration-consistent rendered paths so the API does not imply
   historical creation proof, or add an independent provenance boundary.
5. Add focused regressions for these state combinations without expanding
   another parallel validation path.
