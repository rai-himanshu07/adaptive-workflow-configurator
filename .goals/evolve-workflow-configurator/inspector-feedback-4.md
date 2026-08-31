# Inspector feedback — iteration 4

## Verdict

**FAIL**

Iteration 4 successfully makes required directories rollback-inert, restores
retryable receipts after every injected rollback failure, validates all
required receipt fields, adds direct drift coverage, and fixes the real GUI
layout. One fundamental receipt-provenance gap remains: a self-consistently
rewritten created-file entry can make rollback delete an unrelated user-owned
file.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through all four Builder
  iterations.
- Used all three prior feedback files as mandatory regression lists.
- Read the complete iteration-4 diff and resulting core, CLI, GUI, docs, and
  tests.
- Ran filesystem-heavy checks on project-local tmpfs in an unprivileged
  user/mount namespace.
- Exercised unreadable traversal as mapped EUID 1 and the real Tk window on
  `DISPLAY=:0`.

The Builder commit title and trailers are correct. Both research documents
remain tracked and no dependency manifest changed.

## Blocking finding

### A recomputed created-file receipt can delete arbitrary user content

The iteration correctly handles directory provenance by never deleting or
chmodding required directories. File provenance still trusts the same
self-contained, editable receipt digest.

I created a user-owned `README.md`, applied to that existing project, replaced
one receipt `created` entry with:

- path `README.md`;
- the README's current SHA-256 and mode;
- recomputed `covered_paths`;
- recomputed `covered_sha256`; and
- recomputed `integrity_sha256`.

Rollback accepted the internally consistent receipt:

```text
SELF_CONSISTENT_FILE_FORGERY
  result=ACCEPTED
  status=rolled_back
  user_readme_exists=False
  original_generated_file_exists=True
```

`rollback_project` at `core.py:2913-2931` accepts any safe relative created-file
path whose current bytes match the receipt. It does not constrain the path to
the configuration's rendered destination set, verify the receipt hash against
the intended rendered bytes, or prove the path was absent before apply. The
unkeyed digest can be recomputed alongside the edited data, so it detects
accidental corruption but is not independent provenance.

This directly violates criteria 14 and 15: rollback removed a user-owned file
not proven to have been created by the apply. At minimum, reconstruct and
validate the exact allowed rendered paths/hashes from the receipt configuration
and template version, constrain merge paths to the two documented safe merges,
and reject incomplete/extra/reassigned entries. If creation cannot be proven
independently, use the same conservative policy adopted for directories and do
not delete it.

## Mandatory regression results

### Iteration 1

| Regression | Iteration-4 result |
|---|---|
| Legacy/configurator dry-run no mutation | **PASS.** No target, export, report, receipt, file, or directory was created. |
| Rollback transactional recovery | **PASS for valid receipts.** Immediate state is restored and a second rollback succeeds after every phase. |
| Required `docs/plans` creation | **PASS.** Created and receipted; rollback now deliberately preserves it. |
| Unreadable traversal diagnostics | **PASS.** Real EUID-1 denial produced `traversal.unavailable`, incomplete scan, and blocked apply. |
| Visible GUI preview/export | **PASS.** Proposal, intended content, diff, and exported JSON observed in a real window. |
| CLI/core consolidation | **PASS.** Shared core remains authoritative. |
| Rigor overrides/guard opt-out | **PASS.** All directions and GUI auto/on/off transitions work. |
| Complete suite | **PASS**, 51 tests in 3.335s. |

### Iteration 2

| Regression | Iteration-4 result |
|---|---|
| Missing required-directory drift reapply | **PASS.** Recreated with a new coherent receipt; unchanged reapply reuses the receipt. |
| Configuration drift | **PASS.** Alpha→Beta writes a new Beta receipt. |
| Proposal/covered-file drift | **PASS.** Current edit becomes a current proposal and prevents reuse. |
| Receipt covered-hash drift | **PASS.** Invalid receipt is not reused. |
| Target/project drift | **PASS.** Copied foreign-target receipt is not reused. |
| Simple/duplicate/escaping/metadata/inconsistent directory entries | **PASS.** Refused without directory mutation. |
| Self-consistent forged directory entry | **PASS safely.** Rollback completes but preserves the pre-existing directory byte/metadata state. |
| GUI guard state and target identity | **PASS** in real GUI, including imported identity. |

### Iteration 3

| Regression | Iteration-4 result |
|---|---|
| Required directories never deleted/chmodded | **PASS.** Normal, forged, symlinked, invalid, and fault paths preserved exact mode/device/inode/mtime/ctime. |
| Retry after `remove-created` fault | **PASS.** Receipt remains `applied`; second rollback succeeds. |
| Retry after `restore-merged` fault | **PASS.** Receipt remains `applied`; second rollback succeeds. |
| Retry after compatibility `remove-directory`/`preserve-directory` fault | **PASS.** No directory operation occurs; second rollback succeeds. |
| Retry after `receipt-update` fault | **PASS.** Second rollback succeeds. |
| Retry after receipt replacement succeeds then raises | **PASS.** Recovery restores `applied`; second rollback succeeds. |
| Mutation-count fault boundaries 0/1/2/10 | **PASS.** Each recovers and retries. |
| Every required receipt field | **PASS.** All 20 omissions return CLI code 2, concise `configurator error`, and no traceback. |
| Distinct GUI rows | **PASS.** Helper rows are unique and the real widgets place Testing, Rigor, Stack, and MCP at rows 6, 7, 8, and 9 respectively. |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** Full legacy tests and independent all-flag
   installation passed: defaults, commands, profiles, all MCP choices,
   sandbox opt-out, security hooks, context settings, additive `.gitignore`,
   collision refusal (`rc=3`), opt-outs, and dry-run.

2. **PASS — shared typed core.** Core has no argparse/Tkinter dependency and
   legacy/configurator/GUI operations share its analysis/render/apply/rollback
   primitives.

3. **PASS — configuration model.** Versioned JSON, all required dimensions,
   aliases, validation, round-trip, and actionable malformed configuration
   errors work.

4. **PASS — import/export/defaults.** External import/export does not create the
   target and legacy defaults retain the personal Python/data-science workflow.

5. **PASS — concrete rigor.** Presets populate every policy dimension. String
   and boolean overrides, protocol guard auto/on/off, and live GUI transitions
   work in both directions.

6. **PASS — adaptive guidance.** Complexity, scope, testing, and rigor produce
   documented deterministic changes, including low-risk no-code and high-risk
   diagnostics/review paths.

7. **PASS — lean-change contract.** Search/reuse, non-goals, anti-speculation,
   minimal surface, and protected operational boundaries remain generated
   without external researched tools or hard LOC limits.

8. **PASS — optional GUI controls.** Real Tk controls occupy distinct rows and
   expose target, identity, workflow, risk, profiles, MCP, commands, safety,
   guard intent, and overrides without third-party GUI dependencies.

9. **PASS — GUI operations.** Real preview displayed proposal content/diff;
   report export wrote current JSON; import/export/apply/rollback remain core
   backed with confirmation/status handling. Both headless entry points pass.

10. **PASS — brownfield analysis.** Manifests/languages, Conda+uv, uncertain
    commands, Git, customization/partial state, hazards, actions, directory
    state, and incomplete scans are structured.

11. **PASS — no-mutation paths.** Analyze/preview snapshots matched. Legacy and
    configurator dry-run wrote nothing, including combined export/apply cases.

12. **PASS — safe apply.** User AGENTS/MCP remain byte-identical; only missing
    files and the documented additive `.gitignore`/settings merges are applied
    with modes preserved.

13. **PASS — proposals.** API/JSON/GUI provide rendered intended content,
    metadata, hashes, and diffs, and drift produces a current coherent receipt.

14. **FAIL — file creation provenance.** Normal receipts, backups, required
    fields, target/config/proposal/hash coherence, and conservative directory
    behavior pass. A recomputed created-file entry is accepted and deletes
    unrelated user content; see the blocking finding.

15. **FAIL — rollback safety under self-consistent tamper.** Symlink/path,
    incomplete analysis, apply recovery, valid rollback recovery, and
    directories are safe. Rollback still performs an unsafe deletion from a
    forged-but-internally-consistent created-file entry.

16. **PASS — idempotency/coherence.** Unchanged reapply is a no-op; missing
    directory, config, proposal, target-file hash, receipt hash, and target
    drift all prevent stale reuse and create coherent state.

17. **PASS — new-project workflow.** New install is complete, placeholder-free,
    doctor-clean, and stable on reapply; required directory remains usable after
    rollback. Recommendations do not silently force detected choices.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval, atomic
    checkpoint, supersede, live authority, degraded mode, and optional graph
    capability detection remain correct.

19. **PASS — lifecycle guard.** Core/CLI/GUI intent and opt-out work; supported
    events, local-only claims, timeout, and fail-open limits are documented.

20. **FAIL — safety wording remains too strong.** Documentation accurately says
    directories are always preserved, but still says rollback removes only
    files “proven” created by the receipt. The blocking reproduction disproves
    that claim for a consistently rewritten receipt.

21. **FAIL — one high-risk regression remains uncovered.** The expanded suite
    now directly covers every requested drift branch, all required fields,
    retry after every fault, forged directories, and GUI rows. It does not test
    self-consistent reassignment of a `created` or `merged` file entry to
    user-owned content, which currently fails.

22. **PASS — full quality gate/workflow smoke.** All 51 tests passed in 3.335s
    on healthy project-local tmpfs. Doctor, placeholder check, real/headless
    GUI, legacy, new, and existing workflows passed with observed output and no
    network/credential/production-data reliance.

23. **PASS with a narrow simplification assessment.** No dependency, service,
    framework, runtime, memory backend, or MCP server was added. Iteration 4
    removed inode/ctime/fingerprint-based directory mutation and made rollback
    directories inert. `core.py` changed by 138 insertions/140 deletions
    (3,187→3,185 lines), so the risky directory path was genuinely simplified
    without expanding the core, though the overall module remains large and the
    self-authenticating file-receipt design still needs simplification.

24. **PASS — preservation.** Both research documents remain tracked and no
    unrelated user/dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Complete unittest discovery on project-local tmpfs — **PASS**, 51 tests,
  3.335s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Full legacy/configurator flags, import/export, collision, and dry-run —
  **PASS**.
- New/existing analyze/preview/apply/reapply/normal rollback — **PASS**.
- All drift-coherence branches — **PASS**.
- All 20 required receipt-field omissions — **PASS**, actionable/no traceback.
- Required directory normal/invalid/forged/symlink/fault behavior — **PASS**,
  never deleted or chmodded.
- Every rollback phase, mutation-count fault, and post-replace receipt failure
  followed by a second rollback — **PASS**.
- Real GUI distinct rows, preview/export, tri-state guard, and identity —
  **PASS**.
- Direct and CLI-routed headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Unprivileged unreadable traversal — **PASS**.
- Self-consistent forged created-file receipt — **FAIL**, user README deleted.

## Required next iteration

1. Constrain receipt-created paths and hashes to the exact output set rendered
   from the stored configuration/template version; constrain merged paths to
   documented safe merges and validate entry completeness.
2. Treat the receipt digest as corruption detection, not independent proof; if
   absence-at-apply cannot be established conservatively, do not delete the
   file.
3. Add adversarial tests which recompute every aggregate/integrity field while
   redirecting created and merged entries to user-owned files.
4. Update receipt safety documentation to match the actual trust boundary.
