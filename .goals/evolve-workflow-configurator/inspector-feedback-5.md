# Inspector feedback — iteration 5

## Verdict

**FAIL**

Iteration 5 achieves the requested deletion-free rollback boundary: valid and
forged receipts cannot delete project files or required directories, and only
exact documented `.gitignore` / VS Code settings merge pairs are restored.
However, rollback still selects the wrong receipt for same-second applies,
accepts a self-consistent incomplete merge receipt while claiming success, and
does not accurately expose preserved paths in the visible GUI. Receipt-created
paths can also be self-consistently reassigned and then misreported as generated.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all five Builder
  iterations.
- Used all four prior feedback files as mandatory regression lists.
- Read the complete iteration-5 diff and resulting core, CLI, GUI,
  documentation, hooks, and tests.
- Ran filesystem-heavy checks on a project-local tmpfs in an unprivileged
  user/mount namespace.
- Exercised unreadable traversal as mapped EUID 1 and the real Tk window on
  `DISPLAY=:0`.

The Builder commit title and trailers are correct. Both research documents
remain tracked and no dependency manifest changed.

## Blocking findings

### 1. No-argument rollback can select an older same-second receipt

Receipt filenames contain second precision plus a random UUID suffix, while
`_receipt_path_for` selects `sorted(receipts)[-1]`
(`core.py:2639-2642`). The random suffix is not chronological.

I deterministically reproduced the naturally possible ordering with two valid
same-second applies. The first apply safely merged `.gitignore`; the second,
later apply had a different configuration and its own receipt:

```text
first created_at:  2026-08-29T22:45:49.816765+00:00
second created_at: 2026-08-29T22:45:49.829284+00:00
expected latest:   ...-00000000.json
selected:          ...-ffffffff.json
latest_selected:   False
```

`python workflow_configurator/install.py TARGET --rollback --json` returned success for
the older receipt and unexpectedly removed the additive `artifacts/` rule.
This violates the CLI promise that omitted `RECEIPT_OR_ID` uses the latest
receipt and the requirement to refuse ambiguous rollback state.

Select by validated `created_at`/a monotonic sequence (not UUID lexical order),
and add a same-second multi-receipt regression with materially different merge
effects.

### 2. Forged created entries are harmless but reported as generated

Deletion-free behavior fixed the iteration-4 data-loss bug: after replacing a
receipt-created entry with a fully recomputed user-owned `README.md` entry,
both the README and the original generated file remained untouched.

The result was nevertheless inaccurate:

```text
safe=True
reported_user_as_generated=True
omits_actual_generated=True
```

Fully recomputed extra and incomplete created arrays likewise returned 24 or 22
“preserved generated” paths for an apply that actually created 23. Core/API and
CLI derive this claim directly from editable `created` entries at
`core.py:3170-3181`. The digest detects accidental corruption but does not prove
provenance.

Validate created entries against the exact configuration-rendered path/hash
universe, or call them `receipt-listed paths` and refuse to claim they are
generated. The immutable goal also requires tampered state to be refused.

### 3. The visible GUI reports only a count, not preserved paths

For a valid 23-file apply:

```text
API preserved paths exact: True
CLI listed paths exact:    True
GUI status:
  "Rollback: 23 generated paths preserved for manual review"
GUI path list visible in status/report: False / False
```

The controller retains the full `last_rollback`, but `_run` at
`gui.py:571-575` displays only a count and leaves the report pane empty/stale.
The user cannot perform the promised manual review/removal from the GUI.

Render preserved and missing paths in the scrollable report pane after
rollback, while retaining the concise status count.

### 4. A recomputed incomplete merge receipt can claim rollback without restore

I applied the documented `.gitignore` merge, removed its merge entry and backup
file, consistently recomputed `backups`, `safe_merge_paths`, `covered_paths`,
`covered_sha256`, and `integrity_sha256`, then rolled back:

```text
result=ACCEPTED
status=rolled_back
restored=[]
gitignore_unchanged=True
artifacts_rule_still_present=True
```

This does not overwrite user content, but it accepts missing/tampered state and
claims a completed rollback while the actual apply merge remains. The exact
backup inventory check cannot detect an omitted entry when the corresponding
backup is also removed and all editable aggregates are recomputed.

At minimum, detect an enabled generated additive state with no corresponding
verified merge as ambiguous and refuse or return an explicit partial/manual
status. Documentation must not claim all missing or tampered state is refused
until this boundary is honest.

## Deletion-free and exact-merge adversarial results

### Required directories and project files

- Normal rollback returned `removed=[]`, preserved every created project file,
  and preserved exact required-directory type, mode, device, inode, mtime, and
  ctime.
- Simple tamper, duplicate, escaping path, `.workflow_configurator` path, and
  inconsistent directory fields all raised `RollbackError` with exact
  directory metadata unchanged.
- A fully recomputed `created=true` forgery for a pre-existing `docs/plans`
  completed safely without deleting or chmodding it.
- A replacement `docs/plans` symlink was neither followed nor changed.
- Every injected rollback phase and mutation-count failure left required
  directory metadata exact and all generated files present.

### Safe merge boundary

With both legitimate merges, recorded project writes were exactly:

```text
{".gitignore", ".vscode/settings.json"}
```

Both originals and modes were restored, while every generated path remained.
Each of the following recomputed mutations raised `RollbackError` before any
project-byte change:

- merge path reassigned to a user file;
- backup path reassigned;
- duplicate/extra merge entry;
- incomplete field or extra field;
- changed backup content and recomputed hash;
- extra backup inventory file;
- symlinked backup;
- merge disabled by the receipt configuration;
- non-forward current content; and
- omitted merge entry while its indexed backup remained.

Thus only exact backup→applied instances of the documented additive transforms
are writable. The self-consistent omitted-entry case in finding 4 is a safe
no-op but an incorrect success result.

## All prior feedback regressions

| Regression | Iteration-5 result |
|---|---|
| Configurator apply+dry-run no mutation | **PASS** |
| Rollback content recovery and retry after every phase | **PASS** |
| Post-replace receipt-write recovery and retry | **PASS** |
| Required directory initial creation/receipt/reapply | **PASS** |
| Required directories never deleted/chmodded | **PASS** |
| Unreadable traversal as a meaningful unprivileged user | **PASS** |
| Visible analyze/preview and report export | **PASS** |
| Shared CLI/core installer | **PASS** |
| Every rigor preset/override and guard opt-out | **PASS** |
| Missing-directory drift receipt coherence | **PASS** |
| Configuration drift receipt coherence | **PASS** |
| Proposal/target-file hash drift coherence | **PASS** |
| Receipt-hash drift coherence | **PASS** |
| Target/project drift coherence | **PASS** |
| Directory receipt tamper/duplicate/escape/metadata | **PASS** |
| Self-consistent directory forgery | **PASS safely; directory preserved** |
| GUI auto/on/off live both directions | **PASS** |
| GUI derived/manual/imported identity | **PASS** |
| Real GUI distinct top-level rows | **PASS** |
| All required receipt fields actionable | **PASS**, 25/25 omissions |
| Fully recomputed created-file forgery | **PASS for no deletion; FAIL for provenance reporting** |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Full legacy tests and independent all-flag
   installation passed: defaults, commands, profiles, all MCP choices,
   sandbox opt-out, security hooks, context settings, additive `.gitignore`,
   collision refusal (`rc=3`), opt-outs, and dry-run.

2. **PASS — shared typed core.** Core remains argparse/Tkinter-free. Legacy,
   configurator, and GUI adapters share analysis/render/apply/rollback.

3. **PASS — configuration model.** Versioned JSON covers all required fields,
   aliases, and overrides with actionable validation and exact round-trip.

4. **PASS — import/export/defaults.** External configuration operations do not
   create the target, and omitted options retain personal Python/data-science
   defaults.

5. **PASS — concrete rigor.** All policy dimensions, presets, string/boolean
   overrides, and GUI guard auto/on/off behavior work in both directions.

6. **PASS — deterministic adaptation.** Complexity, scope, testing, and rigor
   materially and deterministically change documented guidance, including
   low-risk no-code and high-risk diagnostics/review paths.

7. **PASS — lean-change contract.** Required reuse/non-goal/anti-speculation/
   minimal-surface/protected-boundary guidance remains without external tools or
   universal LOC rules.

8. **PASS — optional GUI controls.** Real Tk controls use distinct rows and
   expose target, identity, workflow, risk, profiles, MCP, commands, safety,
   policy, and overrides without third-party dependencies.

9. **FAIL — rollback reporting in the GUI.** Analyze/preview/export,
   confirmations, errors, real display, and headless controller paths pass.
   Rollback exposes only a count, not the preserved/missing path list needed for
   manual follow-up; finding 3.

10. **PASS — brownfield analysis.** Manifests/languages, Conda+uv, uncertain
    commands, Git, customization/partial state, collisions, symlinks,
    non-regular files, directory state, and incomplete scans are structured.

11. **PASS — no-mutation paths.** Analyze/preview snapshots matched. Legacy and
    configurator dry-run wrote no target, output, receipt, file, or directory.

12. **PASS — safe apply.** User AGENTS/MCP remain byte-identical and only
    missing files plus documented additive `.gitignore`/settings merges are
    applied with modes preserved.

13. **PASS — proposals.** API/CLI/GUI reports contain intended content,
    metadata, hashes, and diffs; ordinary drift produces current coherent
    receipts.

14. **FAIL — ambiguous/tampered receipt coherence.** Rollback is deletion-free
    and exact-merge-only, but default rollback can select an older same-second
    receipt; recomputed created entries are mislabelled as generated; and a
    self-consistent missing merge/backup is accepted as rolled back.

15. **FAIL — wrong-receipt mutation.** Path/symlink hazards, incomplete scans,
    apply recovery, deletion-free behavior, exact merge validation, and retry
    recovery pass. Selecting an older ambiguous receipt can nevertheless
    restore a merge the user did not request to roll back.

16. **PASS — apply idempotency/drift.** Unchanged reapply is a no-op. Missing
    directory, configuration, proposal, target-file hash, receipt hash, and
    target drift all prevent stale reuse and produce coherent current receipts.

17. **PASS — new-project completeness.** New install is complete,
    placeholder-free, doctor-clean, stable on reapply, and preserves required
    directories/generated paths on rollback. Detection remains advisory.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live-file authority, degraded mode, and optional
    graph capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI intent and opt-out work; supported
    event names, local-only scope, timeout, and fail-open behavior are truthful.

20. **FAIL — documentation truthfulness.** Overall documentation coverage is
    complete and correctly describes deletion-free/exact-merge behavior, but
    “refuses missing, tampered, ambiguous state” is disproved by findings 1, 2,
    and 4, and generic generated-path reporting is not visible in the GUI.

21. **FAIL — focused coverage gaps.** The 54 passing tests now cover forged
    created/merge paths and exact pairs, but omit same-second latest-receipt
    selection, self-consistent omitted merge+backup, forged-path reporting
    accuracy, and visible GUI rollback path output.

22. **PASS — full quality gate/workflows.** All 54 tests passed in 3.462s on
    healthy project-local tmpfs. Doctor, placeholders, real/headless GUI,
    legacy, new, and existing workflows passed with observed output and no
    network, credentials, or production data.

23. **FAIL — iteration 5 expanded the risky core.** No dependency/service/runtime
    was added and deletion-free mutation is safer. However `core.py` grew from
    3,185 to 3,425 lines (`+308/-68`) and the focused test file from 821 to 955
    lines. New derived receipt fields and validation are repeated across
    construction, loading, reuse, merge verification, inventory verification,
    and rollback. This is expansion rather than the requested lean
    simplification, and the uncovered selection/coherence gaps demonstrate its
    maintenance cost. A typed receipt/state component with one validation path
    would materially improve separation without adding a framework.

24. **PASS — preservation.** Both research documents remain tracked; no
    unrelated user or dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Complete unittest discovery on project-local tmpfs — **PASS**, 54 tests,
  3.462s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags, import/export, collision, and dry-run —
  **PASS**.
- New/existing analyze/preview/apply/reapply/explicit rollback — **PASS**.
- Every ordinary drift-coherence branch — **PASS**.
- All 25 actual receipt-field omissions — **PASS**, concise/no traceback.
- Required directories under normal/forged/symlink/fault cases — **PASS**,
  exact metadata preserved.
- Every rollback phase/mutation-count/post-replace fault followed by retry —
  **PASS**.
- Exact `.gitignore`/settings safe merge writes and eleven forged merge cases —
  **PASS**.
- Real GUI rows, preview/export, tri-state guard, and identity — **PASS**.
- Direct and CLI-routed headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Unprivileged unreadable traversal — **PASS**.
- Same-second no-argument latest receipt — **FAIL**, older receipt selected and
  unexpected `.gitignore` restore performed.
- GUI rollback path list — **FAIL**, only count visible.
- Self-consistent created-entry reporting — **FAIL**, user path labelled
  generated and actual generated path omitted.
- Self-consistent omitted merge+backup — **FAIL**, status says rolled back while
  additive merge remains.

## Required next iteration

1. Select the latest receipt by validated chronological metadata (or use a
   sortable high-resolution ID), and handle ambiguity explicitly.
2. Validate created entries against configuration-rendered paths/hashes, or
   rename them as untrusted receipt-listed paths and stop claiming provenance.
3. Display preserved and missing rollback paths in the GUI report pane.
4. Detect/represent incomplete merge evidence as ambiguous or partial rather
   than returning `rolled_back`.
5. Consolidate receipt parsing/coherence/rollback validation into one typed,
   maintainable path instead of adding further parallel field checks.
