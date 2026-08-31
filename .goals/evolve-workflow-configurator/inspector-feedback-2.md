# Inspector feedback — iteration 2

## Verdict

**FAIL**

Iteration 2 fixes most iteration-1 failures, including dry-run mutation,
rollback fault recovery, normal required-directory lifecycle, incomplete-scan
diagnostics, visible GUI reports, duplicated CLI installation logic, core/CLI
policy overrides, and the previously blocked full-suite run. The complete goal
still fails on rollback proof, drift idempotency, and GUI configuration
correctness.

## Scope and evidence

- Compared the complete result from immutable initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through Builder commits
  `8c75f08` and `87a1355`.
- Read the complete iteration-2 diff and the resulting core, CLI, GUI,
  documentation, hooks, and tests.
- Exercised all prior failures independently, including every rollback phase
  and a receipt write which succeeded and then raised.
- Ran the complete suite on a project-local tmpfs mounted in an unprivileged
  user/mount namespace, avoiding the unhealthy NTFS temporary path from
  iteration 1.
- Ran unreadable traversal as mapped unprivileged EUID 1, where direct access
  genuinely raised `PermissionError`.
- Exercised both headless GUI entry points and a real Tk window on
  `DISPLAY=:0`.

The iteration-2 Builder commit has the required title and trailers. The
initial-to-HEAD product/result diff preserves both research documents and adds
no dependency manifest.

## Blocking findings

### 1. Missing required directories are not repaired on reapply

After a successful new-project apply, I removed the empty receipt-created
`docs/plans` directory and reapplied the identical configuration:

```text
DIRECTORY_DRIFT missing_reported=missing
recreated=False
receipt_reused=True
```

Analysis correctly reports the directory as missing, but the no-op receipt
reuse branch at `core.py:2263-2284` tests only `report.safe_actions` (file
actions). It returns before processing `report.directory_states`.

This fails the explicitly requested required-directory idempotency. Receipt
reuse must require that every required directory is present and safe; otherwise
apply must create and receipt the missing directory.

### 2. Receipt reuse ignores configuration/proposal drift

I applied configuration `Alpha`, then applied configuration `Beta` to the same
unchanged generated files. The second analysis had three current conflict
proposals but no writable file action:

```text
CONFIG_DRIFT current_proposals=3
receipt_reused=True
receipt_project=Alpha
receipt_proposals=0
```

The returned receipt therefore does not describe the requested configuration
or its proposals. This contradicts the receipt's purpose of explaining the
apply and makes the non-JSON CLI's printed receipt misleading. The reuse branch
must verify at least target, normalized configuration, current proposal
metadata, required-directory state, and receipt-covered hashes before reusing a
receipt; otherwise write a current no-op receipt/report or clearly return no
receipt.

### 3. A tampered directory receipt can delete a user-owned directory

I created a user-owned empty directory, performed apply, and changed only the
receipt's generated directory path from `docs/plans` to that user directory.
Rollback accepted the modified receipt:

```text
DIRECTORY_RECEIPT_TAMPER refused=False
status=rolled_back
user_dir_exists=False
actual_created_dir_exists=True
```

`rollback_project` accepts any safe relative directory at
`core.py:2608-2641`; it does not constrain entries to the configurator's known
required directories or cross-check `directories`, `created_directories`, and
the apply configuration. Unlike files, directory entries have no content hash
evidence. This directly violates the requirement to remove only objects proven
to have been created by that apply and to refuse tampered rollback state.

Validate directory entries against the exact known required-directory set,
reject duplicates/metadata paths, cross-check redundant receipt fields, and
add a tampered-directory receipt test.

### 4. GUI preset changes silently become protocol-guard opt-outs

Starting the GUI with standard rigor and `protocol_guard=None`, then changing
the visible controls to strong/advanced/large/broad without touching the guard
checkbox produced:

```text
GUI_POLICY stale_before_operation=True
serialized_protocol_guard=False
resolved_guard=False
strong=strong
```

The checkbox is initialized from the old resolved policy
(`gui.py:247-250`), but `_collect` serializes every Boolean variable as an
explicit override (`gui.py:335-336`). There are no variable traces to refresh
the policy/guard when rigor or risk controls change. Thus an untouched default
checkbox becomes a deliberate `False`, disabling what the newly selected
strong preset visibly promises. The policy panel also remains stale until an
operation runs.

Represent guard selection as `auto/on/off` (or track whether the user changed
it), update resolved policy live, and test transitions in both directions.

### 5. GUI target selection retains the old target's derived project name

Launching the GUI for the repository and selecting a different new target,
without an imported explicit project name, produced:

```text
original_name=adaptive-workflow-configurator
selected_name=selected-new-project
configured_name=adaptive-workflow-configurator
matches_selected=False
```

`ConfiguratorController.set_target` only derives a new configuration when the
old name literally equals `"project"` (`gui.py:35-39`). The GUI has no project
name/summary field, so the user cannot correct the stale generated identity.
Track whether identity was derived versus explicitly imported, update derived
identity on target change, or expose editable project name/summary fields.

## Iteration-1 failure retest

| Prior failure | Iteration-2 result |
|---|---|
| Configurator `--apply --dry-run` mutated | **Fixed.** New target remained absent; complete existing-target snapshot, export path, and report output path remained absent/unchanged. Mutually exclusive operations return 2. |
| Rollback could leave a half rollback | **Fixed for tested phases.** `remove-created`, `restore-merged`, `remove-directory`, and `receipt-update` faults each restored the exact applied snapshot and original receipt. |
| Receipt write failure after replacement | **Fixed.** A wrapper performed the real receipt replacement and then raised; recovery restored all applied bytes/modes and receipt status `applied`. |
| `docs/plans` omitted | **Fixed for initial apply/receipt/normal rollback.** It is created, receipted, and removed when still empty. **Not fixed for drift reapply**; see finding 1. |
| Unreadable traversal was silent | **Fixed.** EUID 1 received real `PermissionError`; report had `scan_complete=False`, `traversal.unavailable`, and apply refused incomplete analysis. |
| GUI had no useful preview | **Fixed.** Real Tk report pane showed proposal classification, intended AGENTS content, and diff; Export report wrote one-proposal JSON to the selected external path. |
| CLI duplicated installer implementation | **Fixed.** Legacy and configurator routes now share core selection/render/MCP/safety/apply primitives; remaining wrappers preserve imported compatibility names. |
| Boolean rigor overrides were ineffective | **Fixed in core/CLI.** Both directions of every boolean alias, all string dimensions, and guard opt-in/opt-out resolved correctly. **GUI transition remains incorrect**; see finding 4. |
| Full suite had no result | **Fixed.** All 42 tests passed on healthy project-local tmpfs in 3.046 seconds. |

## Acceptance-criterion verification

1. **PASS — CLI compatibility.** The full legacy test set passes. Independent
   full legacy install exercised defaults, extra profiles, MCP, security hooks,
   context settings, placeholders, additive `.gitignore`, `docs/plans`,
   collision refusal (`rc=3`), and dry-run with no target creation.

2. **PASS — reusable core/thin adapters.** Core has no argparse/Tkinter
   dependency. Legacy and configurator CLI installation now route through
   `apply_project`/`install_legacy`; GUI routes analysis/apply/rollback through
   the same core. Compatibility wrappers are thin rather than parallel
   implementations.

3. **PASS — typed versioned configuration.** Version 1 round-trip and malformed,
   unsupported, aliased, and unknown values are validated with actionable
   errors. Complexity, size, testing, profiles, MCP, commands, rigor,
   overrides, and tri-state protocol-guard policy serialize.

4. **PASS — import/export/defaults.** Configuration round-trip preserves
   supported fields. External export does not create the target. Legacy
   no-option installation retains personal Python/data-science and command
   defaults.

5. **FAIL — concrete rigor and GUI overrides.** Core and CLI resolve every
   required policy dimension, preset, string override, boolean true/false
   direction, and guard opt-in/opt-out. The GUI converts an untouched computed
   guard value into the opposite explicit override after preset changes and
   shows stale policy until an operation; see finding 4.

6. **PASS — deterministic adaptive guidance.** The documented 0/1/2 risk
   contributions and escalation thresholds match code. Low-risk/no-test and
   high-risk broad-diagnostic paths were observed; complexity, size, testing,
   and rigor materially alter generated policy.

7. **PASS — lean-change contract.** Search/reuse, explicit non-goals, no
   speculative abstractions/config/dependencies, minimal surface, and protected
   correctness/operational boundaries remain generated. No hard LOC rule or
   researched external tool is installed.

8. **FAIL — GUI target/policy controls.** The real standard-library Tk window
   exposes the requested visible controls, report, scrolling, commands,
   profiles, MCP, and overrides. Target selection retains the prior target's
   derived project name with no correction field (finding 5), and policy
   transitions mishandle guard defaults (finding 4).

9. **PASS — GUI operations and smoke.** Analyze/Preview populate a visible
   review report; Export report writes current JSON to the selected path;
   import/export/apply/rollback use the controller/core; apply/rollback ask for
   confirmation. Direct and CLI-routed headless smoke returned `ok: true`, and
   the real window/report/export path succeeded.

10. **PASS — structured brownfield analysis.** The observed report detected
    Python/FastAPI, manifests, Conda+uv, uncertain Makefile commands, Git,
    customizations, proposals, safe merges, symlinks, and required-directory
    state. Incomplete traversal is structured rather than hidden.

11. **PASS — analysis/dry-run/preview no mutation.** Complete target snapshots
    matched before/after analyze and preview. Configurator apply+dry-run created
    no new target, receipt, config export, or report output. Existing target
    bytes/directories/modes were unchanged.

12. **PASS — safe apply policy.** Existing AGENTS and MCP bytes remained
    untouched. Only absent workflow files, additive artifact ignore, and absent
    generated search exclusions were written. `.gitignore` mode `0640` and
    settings mode `0600` were preserved.

13. **PASS at report/API boundary — conflict proposals.** Analysis, GUI, and
    JSON results contain intended content, hashes/metadata, and diffs while
    originals remain unchanged. The stale reused receipt defect is recorded
    against criterion 14.

14. **FAIL — receipt proof and tamper refusal.** Normal files, merges, backups,
    required directories, and rollback work. A modified directory receipt can
    delete an unrelated user-owned empty directory, and no-op receipt reuse can
    return an Alpha receipt for a Beta request/proposals; see findings 2 and 3.

15. **FAIL — rollback safety under tampered state.** Symlink/non-regular/path
    hazards, incomplete scans, apply failure, all rollback phases, and receipt
    update recovery passed. Nevertheless rollback accepted unsafe tampered
    directory provenance and deleted user content (finding 3).

16. **FAIL — idempotency under drift.** Unchanged reapply performs no file or
    setting writes and repeated preview is stable. If the required empty
    directory disappears, reapply reports it missing but reuses the old receipt
    without restoring it. Configuration/proposal drift also reuses a
    semantically unrelated receipt; see findings 1 and 2.

17. **PASS for core/CLI initial creation; GUI caveat.** Initial new-project
    apply is complete, placeholder-free, doctor-clean, and includes
    `docs/plans`. Facts recommend rather than force profiles and surface
    Conda+uv/uncertain commands. GUI-selected targets can receive stale project
    identity as described under criterion 8.

18. **PASS — memory/code-intelligence guidance.** Project-scoped retrieval,
    atomic checkpoint, `kg_supersede`, live-file authority, degraded behavior,
    and capability-detected optional graph operations remain correct.

19. **PASS for core/CLI guard behavior.** Strong/explicit opt-in includes the
    reviewed supported lifecycle guard; `--without-protocol-guard` removes it.
    Event-surface and timeout/fail-open limits are documented, and external
    memory success is not claimed. GUI's accidental opt-out is recorded under
    criterion 5.

20. **PASS — documentation.** Architecture, compatibility, fields/presets,
    exact risk mapping, GUI/report launch, new/existing examples, conflict and
    safety policy, receipts/directories, rollback, and headless validation are
    documented with sample paths and no secrets.

21. **FAIL — focused tests still miss shipped safety/state defects.** The
    expanded 514-line test file is proportional and covers most required
    categories, including prior failures. It does not test required-directory
    drift reapply, receipt/config/proposal coherence, tampered directory
    entries, GUI target changes, or GUI preset/guard transitions; all currently
    fail independent testing.

22. **PASS — complete quality gate and workflow smoke.** All 42 tests passed in
    3.046 seconds on healthy project-local tmpfs. Both headless paths and a real
    Tk window passed. Independent legacy/new/existing workflows produced
    observed output. Tests used no network, credentials, production data, or
    required display.

23. **PASS — dependency and separation discipline.** No new dependency,
    service, framework, runtime, backend, or MCP server is introduced.
    Consolidation removed the parallel installer while preserving clear
    core/CLI/GUI boundaries.

24. **PASS — research/user work preservation.** Both research documents remain
    tracked. The complete diff contains no unrelated deletion or dependency
    change.

## Quality-gate and smoke summary

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- `python -m unittest discover -s workflow_configurator/tests -v` on project-local
  tmpfs — **PASS**, 42 tests, 3.046s.
- Generated-project doctor `--strict` — **PASS**.
- Exact generated placeholder `rg` check — **PASS**, no matches.
- Direct and CLI-routed headless Tk smoke — **PASS**, 23 actions, 0 errors.
- Real Tk window, visible proposal/content/diff, and report export — **PASS**.
- Configurator apply+dry-run complete no-mutation snapshots — **PASS**.
- Rollback `remove-created`, `restore-merged`, `remove-directory`,
  `receipt-update`, and post-replace receipt-write recovery — **PASS**.
- Unprivileged unreadable traversal/apply refusal — **PASS**.
- Initial required-directory apply/receipt/rollback — **PASS**.
- Required-directory drift reapply — **FAIL**.
- Tampered directory receipt refusal — **FAIL**.
- GUI preset transition and selected-target identity — **FAIL**.

## Required next iteration

1. Include missing/unsafe required-directory state in the no-op/reuse decision.
2. Reuse receipts only when configuration, proposals, target, directory state,
   and covered hashes match the current request; otherwise persist a coherent
   current result.
3. Constrain and cross-check directory receipt entries so edited metadata
   cannot remove arbitrary user-owned directories.
4. Make GUI protocol-guard selection tri-state/intent-aware and refresh policy
   live when rigor/risk controls change.
5. Update derived project identity when GUI target selection changes, or expose
   editable project name/summary.
6. Add focused regression tests for all five cases above, then rerun the same
   complete tmpfs gate and real/headless GUI smoke.
