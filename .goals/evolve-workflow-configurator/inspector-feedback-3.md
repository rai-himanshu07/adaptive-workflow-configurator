# Inspector feedback — iteration 3

## Verdict

**FAIL**

Iteration 3 fixes the iteration-2 receipt-reuse drift and GUI state-transition
defects in normal operation. The complete goal still fails state-integrity,
malformed-receipt error handling, rollback recovery, and real GUI layout
requirements. All repository tests pass, but they do not exercise the
adversarial failures below.

## Scope and method

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through Builder commits
  `8c75f08`, `87a1355`, and `2deb318`.
- Treated both previous Inspector reports as mandatory regressions.
- Read the complete iteration-3 diff and resulting core/CLI/GUI/docs/tests.
- Ran all filesystem-heavy checks on a project-local tmpfs in an unprivileged
  user/mount namespace rather than the unhealthy NTFS temporary path.
- Tested unreadable traversal as mapped EUID 1, where direct file access
  genuinely raised `PermissionError`.
- Exercised the real Tk window on `DISPLAY=:0`, not only helper functions.

The Builder commit title and trailers are correct. The complete result preserves
both research documents and changes no dependency manifest.

## Blocking findings

### 1. Every rollback fault leaves the restored receipt unusable

I independently injected each supported rollback phase failure, then retried
rollback against the receipt which still says `applied`:

```text
remove-created  -> retry RollbackError: required directory metadata changed
restore-merged  -> retry RollbackError: required directory metadata changed
remove-directory -> retry RollbackError: required directory metadata changed
receipt-update  -> retry RollbackError: required directory metadata changed
post-replace receipt failure -> same retry failure
```

The first failure claims that the applied snapshot was restored. It restores
file bytes and receipt bytes, but `restore_applied_snapshot` at
`core.py:3033-3056` unconditionally calls `chmod` on the required directory.
Even when the directory was never removed, this changes ctime. After a late
failure, the directory is recreated with a different inode as well:

```text
remove-created:
  inode unchanged, stored_ctime_matches=False, claims_restored=True
receipt-update:
  stored_inode_matches=False, stored_ctime_matches=False, claims_restored=True
```

The unchanged restored receipt still contains the old ctime/inode, and the next
rollback is rejected at `core.py:2957-2967`. This is not a complete applied
snapshot and leaves an ambiguous state after every tested rollback fault.

Recovery must preserve directory identity (for example, transactionally rename
rather than delete before commit) or write a coherently updated applied receipt
after safe recovery. Tests must verify a second rollback succeeds, not only
that selected file bytes and old receipt bytes match immediately.

### 2. A fully recomputed receipt can delete a pre-existing user directory

The new digest catches simple edits, exact-path violations, duplicates, and
unrecomputed metadata. It is an unkeyed digest stored in the same editable JSON,
so it does not prove provenance.

I began with a user-owned, pre-existing, empty `docs/plans`, applied the
configurator, then changed the directory entry from `created=false` to
`created=true`, set a forged operation timestamp, and consistently recomputed
the directory fingerprint, aggregate directory hash, created-directory list,
and receipt integrity digest. Rollback accepted it:

```text
SELF_CONSISTENT_USER_DIR_FORGERY
  result=ACCEPTED
  status=rolled_back
  user_directory_exists=False
```

The exact required-directory whitelist prevents redirecting the entry to an
arbitrary name, but it cannot distinguish a pre-existing user-owned
`docs/plans` from one created by apply once all proof is editable together.
This violates “removes only files proven to have been created” and “refuses
tampered state.” Do not present a self-contained checksum as provenance.
Directory deletion needs an independent trustworthy creation record/commit
mechanism, or rollback must conservatively leave directories in place.

### 3. A missing receipt timestamp escapes as `KeyError` and CLI traceback

`_load_receipt` uses `raw["operation_started_ns"]` at `core.py:2645` but omits
that field from its required-field loop at `core.py:2620-2639`. A precisely
shaped receipt missing only that field produces:

```text
MALFORMED_RECEIPT_CLI rc=1
traceback=True
KeyError: 'operation_started_ns'
```

This is neither an actionable `RollbackError` nor the CLI's concise
`configurator error`. Add every indexed field to schema validation and test
each required field independently.

### 4. Real GUI controls overlap in two grid rows

The real Tk window has these top-level grid occupants:

```text
row 6: Testing, its combobox, Stack profiles, its frame
row 7: Engineering rigor, its combobox, MCP choices, its frame
```

`gui.py:259` starts the five policy controls at row 3, but
`gui.py:270` resets `row = len(controls) + 1` as if they started at row 1.
Later widgets overlay Testing and Engineering rigor, making required controls
obscured/unusable and violating the production/accessibility constraint.
Calculate the next row from the actual offset and add a real/fake-widget layout
assertion that every top-level field occupies a distinct row.

## Mandatory regression results

### Iteration 1

| Regression | Result |
|---|---|
| Configurator apply+dry-run no mutation | **PASS.** New target, existing snapshot, export path, report output, and receipt all remained absent/unchanged. |
| Rollback phase recovery | **FAIL semantically.** Immediate file bytes are restored, but new directory metadata validation makes every restored receipt non-retryable; finding 1. |
| Initial required directory creation | **PASS.** `docs/plans` is created, receipted, and normally rolled back. |
| Unreadable traversal | **PASS.** Real EUID-1 denial yielded `scan_complete=false`, `traversal.unavailable`, and blocked apply. |
| Visible GUI preview/export | **PASS.** Proposal, intended content, diff, and JSON export were observed in a real window. |
| CLI/core consolidation | **PASS.** Legacy and configurator installation use shared core primitives. |
| Preset/override behavior | **PASS in core/CLI and current GUI state logic.** |
| Full suite | **PASS**, 45 tests in 3.030s on tmpfs. |

### Iteration 2

| Regression | Result |
|---|---|
| Missing `docs/plans` drift reapply | **PASS.** Directory was recreated and a new receipt recorded `created_directories=["docs/plans"]`; unchanged state still reused its receipt. |
| Config drift receipt coherence | **PASS.** Alpha→Beta produced a new Beta receipt with all three current proposals. |
| Proposal drift receipt coherence | **PASS.** User content v1→v2 produced a new receipt whose diff contains v2. |
| Covered-file hash drift | **PASS.** Modified AGENTS prevented reuse and appeared in the new receipt proposal. |
| Project/target drift | **PASS.** A copied foreign-target receipt was not reused. |
| Simple tampered directory path | **PASS.** Refused with target unchanged. |
| Duplicate directory entry | **PASS.** Refused with target unchanged. |
| Escaping directory path | **PASS.** Refused with target unchanged. |
| `.workflow_configurator` directory path | **PASS.** Refused with target unchanged. |
| Inconsistent `created_directories` | **PASS.** Refused with target unchanged. |
| Incorrect inode metadata | **PASS.** Refused with target unchanged. |
| Self-consistent provenance forgery | **FAIL**; finding 2. |
| GUI guard auto/on/off, live both directions | **PASS.** Auto followed standard→strong→light; explicit on/off persisted across both directions and policy text updated live. |
| GUI derived identity | **PASS.** Target change updated the derived project name. |
| GUI explicit identity | **PASS after collect.** Manual name remained explicit across target change. |
| GUI imported identity | **PASS.** Imported name/summary remained explicit while controller target changed. |
| Real GUI layout | **FAIL**; finding 4. |

## Acceptance-criterion verification

1. **PASS — legacy CLI behavior.** All legacy tests pass. Independent all-flag
   install exercised project facts, commands, profiles, every MCP choice,
   unsandboxed option, security hooks, context settings, additive ignore,
   collision refusal (`rc=3`), no-default/context/artifact opt-outs, and
   dry-run no mutation.

2. **PASS — shared typed core.** Core remains argparse/Tkinter-free. CLI and GUI
   are adapters over shared analyze/preview/apply/rollback and compatibility
   wrappers do not restore the old duplicate installer.

3. **PASS — configuration model.** Versioned JSON round-trip, validation,
   profiles, MCP, command overrides, rigor, safety fields, aliases, and
   actionable malformed configuration behavior remain correct.

4. **PASS — import/export and defaults.** External config export/import
   round-tripped without target creation; omitted new options reproduced legacy
   Python/data-science defaults.

5. **PASS — concrete rigor policy.** Every preset and concrete dimension is
   populated; all string and boolean override directions work. Real GUI
   auto/on/off transitions followed policy live and explicit choices persisted.

6. **PASS — deterministic adaptation.** Documented risk inputs and thresholds
   match generated output. Low-risk/no-code and high-risk planning,
   diagnostics, and review paths were observed.

7. **PASS — lean-change guidance.** The required search/reuse, non-goals,
   anti-speculation, minimal-surface, and protected-boundary contract remains,
   without external researched tooling or universal LOC limits.

8. **FAIL — GUI control exposure/accessibility.** Target, identity, workflow,
   policy, profiles, MCP, commands, and overrides exist and their state logic
   works, but Testing/Stack and Rigor/MCP controls occupy identical grid rows
   and overlay each other in the real window; finding 4.

9. **PASS for operations, with layout failure accounted in criterion 8.** Real
   Analyze/Preview displayed proposal content/diff, report export produced
   current JSON, confirmations remain on apply/rollback, errors are concise,
   and both headless paths pass.

10. **PASS — structured analysis.** Existing-project facts, manifests,
    languages, environment conflict, inferred/uncertain commands, Git,
    customizations, partial state, symlinks, non-regular files, collisions,
    required directories, and incomplete scans are represented.

11. **PASS — no-mutation paths.** Complete existing snapshots matched across
    analyze/preview. Legacy and configurator dry-run created no target, export,
    report, receipt, file, or directory.

12. **PASS — safe apply.** Existing AGENTS/MCP remained byte-identical.
    `.gitignore` and VS Code settings received only documented additive changes
    with modes preserved; conflicting settings remained proposals.

13. **PASS — proposals.** Current API/JSON/GUI reports contain intended content,
    hashes, metadata, and diffs, and config/proposal/hash drift now generates a
    coherent current receipt rather than reusing stale proposals.

14. **FAIL — receipt proof/tamper/missing state.** Normal apply/rollback and
    simple field tampering work, but a consistently recomputed receipt deletes a
    pre-existing user directory, and a missing required timestamp escapes schema
    handling as `KeyError`; findings 2 and 3.

15. **FAIL — transactional recovery/state integrity.** Apply failure, normal
    rollback, path/symlink hazards, and immediate file restoration pass. Every
    rollback phase fault changes required-directory metadata while restoring
    the old receipt, so the applied state cannot be rolled back again; finding
    1. The self-consistent forgery also permits user-content deletion.

16. **PASS — practical idempotency/coherence.** Unchanged reapply reuses a
    coherent receipt without file writes. Missing-directory, config, proposal,
    covered hash, and target drift all prevent stale reuse and produce coherent
    new state.

17. **PASS — new-project completeness/recommendations.** New install is
    placeholder-free, doctor-clean, includes `docs/plans`, and reapply is
    stable. Existing facts recommend without forcing and Conda+uv/uncertain
    commands are surfaced.

18. **PASS — memory/code-intelligence guidance.** Targeted retrieval,
    checkpoint, supersede, live authority, degraded mode, and
    capability-detected graph operations remain correct.

19. **PASS — supported protocol guard.** Core/CLI/GUI auto and explicit choices
    behave as intended; supported event names, local-only claims, timeout, and
    fail-open limitations remain documented.

20. **FAIL — safety documentation overclaims recovery/provenance.** Coverage is
    otherwise complete, but README/CONFIGURATOR state that rollback restores the
    complete applied snapshot and removes only receipt-proven directories. Both
    claims are disproved by findings 1 and 2.

21. **FAIL — focused tests miss implemented state transitions.** The 615-line
    focused suite remains proportional and covers broad categories, but it has
    no regression tests for directory/config/proposal/hash reuse despite those
    being the iteration's main core changes. It also compares only product file
    bytes after rollback faults, never verifies receipt retryability/directory
    metadata, omits one-required-field-at-a-time schema tests and
    self-consistent receipt mutation, and tests GUI helpers/controller without
    detecting the real grid overlap.

22. **PASS — full gate and observed workflows.** All 45 tests passed in 3.030s
    on healthy project-local tmpfs. Direct and CLI headless smoke returned
    `ok=true`; a real Tk window was exercised. Independent legacy, new, and
    existing workflows produced observed output without network, credentials,
    or production data.

23. **PASS with maintainability warning.** No dependency, service, runtime,
    framework, memory backend, or MCP server was added; core/CLI/GUI boundaries
    are real. The now 3,187-line core and self-authenticating receipt machinery
    are growing complex enough to require simplification rather than another
    validation layer.

24. **PASS — preservation.** Both research documents remain tracked and no
    unrelated user or dependency content was removed.

## Quality gates and observed smoke

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- `python -m unittest discover -s workflow_configurator/tests -v` on project-local
  tmpfs — **PASS**, 45 tests, 3.030s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder `rg` — **PASS**, no matches.
- Direct and CLI-routed headless GUI smoke — **PASS**, 23 actions, 0 errors.
- Real GUI guard transitions, identity, preview, and export — logic **PASS**.
- Real GUI distinct control layout — **FAIL**, two overlapping row pairs.
- Full legacy flags/collision/dry-run — **PASS**.
- Configurator flags/export/import/dry-run — **PASS**.
- New/existing analyze/preview/apply/reapply/normal rollback — **PASS**.
- Directory/config/proposal/hash/project drift coherence — **PASS**.
- Simple/duplicate/escape/metadata/inconsistent directory receipt edits —
  **PASS**, refused without mutation.
- Missing `operation_started_ns` receipt — **FAIL**, raw KeyError/traceback.
- Self-consistent user-directory receipt forgery — **FAIL**, accepted/deleted.
- All rollback fault phases and post-replace receipt failure — immediate file
  bytes restored, but semantic/retry recovery **FAIL**.
- Unprivileged unreadable traversal — **PASS**.

## Required next iteration

1. Make rollback fault recovery leave a receipt/directory state that passes the
   same verification and can be retried; test retry after every phase.
2. Replace self-contained directory “proof” with independent conservative
   provenance, or never remove directories when creation cannot be proven
   independently.
3. Validate `operation_started_ns` and every required receipt field before
   indexing, returning only actionable `RollbackError`.
4. Fix GUI row allocation and assert distinct rows in a real/fake widget test.
5. Add direct regression coverage for every drift-coherence branch added in
   iteration 3.
