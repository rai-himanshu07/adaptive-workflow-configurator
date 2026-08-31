# Inspector feedback — replacement goal, iteration 3

## Verdict

**PASS**

Iteration 3 implements the selected repeated-history behavior without
resurrecting automatic rollback. For each repeated path, the default plan
selects the newest entry whose recorded after hash and mode match the current
file, exposes every non-active entry as passive history, and keeps explicit
manifest selection invocation-specific. The behavior passed independently
through core, CLI, controller, and the real GUI for both a repeated
`.gitignore` merge and a generated file recreated under changed configuration.

Both earlier defects remain fixed, all 48 tests pass without environment
overrides and on healthy tmpfs, and every required replacement-goal smoke
passes.

## Scope and method

- Read only `.goals/simplify-safe-apply/goal.md`,
  `inspector-feedback-1.md`, and `inspector-feedback-2.md`.
- Compared the complete replacement result from initial SHA
  `36dab891319fad9bfcf10365d29d3d52bc41604c` through Builder commit
  `ee4246cfc40729d3af3554d890d59bc5a040f58c`.
- Read the iteration-3 diff and resulting aggregation/state helpers,
  user-facing renderers, documentation, and tests.
- Independently reproduced the two repeated-history workflows and exercised
  core, CLI JSON/text, controller, visible GUI, export, and explicit selection.
- Retested passive metadata, all three post-success write failures, exact and
  tmpfs suites, new/existing CLI workflows, doctor/placeholders, and both Tk
  smoke paths.

The Builder commit title and trailers are correct. No product file was edited
by the Inspector.

## Targeted repeated-history verification

### Repeated safe merge

The test sequence was:

1. Apply the additive `.gitignore` merge and retain manifest/backup A.
2. Manually copy backup A to `.gitignore`.
3. Add new user content.
4. Apply again, producing manifest/backup B.
5. Perform a no-op reapply and a proposal/config-only drift apply.
6. Request default and explicit restore plans.

Observed across core, CLI, and controller:

```text
active manifest: B
active backup: B
active state: ready
history: A
no-op/drift manifests: excluded from material aggregation
```

- Default `manifest_paths` contained A and B in deterministic chronological
  order.
- The sole active `.gitignore` mapping used B's exact backup, after hash, and
  mode.
- A remained present under `history` with its manifest, backup, path, kind, and
  state; it never replaced B.
- Repeating the default call returned an equal plan.
- Explicit A, B, no-op, and drift selection each returned only that
  invocation's entries and `history=[]`.
- CLI JSON matched core; CLI text showed backup B plus the clearly labeled
  history section and manifest A.
- `ConfiguratorController.restore_instructions()` matched core exactly.

The real GUI displayed B as the active ready mapping, displayed A under
**Older material history (not active mappings)**, exported the same JSON, and
did not change the target.

### Recreated generated file

I applied configuration Alpha, deleted its generated `AGENTS.md`, recreated it
by applying changed configuration Beta, then performed a no-op reapply.

Observed:

```text
active manifest: Beta invocation
active hash/mode: Beta invocation
active state: present
history: Alpha invocation
```

Core, CLI JSON, controller, and the real GUI agreed. The default plan excluded
the no-op manifest, retained the old entry as history, and selected the current
Beta content. Explicit Beta selection contained only Beta and no history.
Generating and exporting every plan preserved the complete target snapshot.

### Selection implementation

`_aggregate_restore_material` groups every entry by destination, orders events
by parsed manifest time/name/index, evaluates current hash/mode, and chooses
the newest current match. If nothing matches it conservatively selects the
newest event and labels its state `manual`/`missing`. All non-selected events
are retained as sorted history with their source manifest. This matches the
user-selected contract.

## Prior defect regression

| Regression | Iteration-3 result |
|---|---|
| Completed backup write then raises | **PASS.** Exact complete pre-apply tree and metadata restored. |
| Completed generated-file write then raises | **PASS.** Exact complete pre-apply tree and metadata restored. |
| Completed manifest write then raises | **PASS.** Exact complete pre-apply tree and metadata restored. |
| No-op reapply hides prior material | **PASS.** Prior paths/backups remain default-active/history as applicable. |
| Proposal/config-only drift hides material | **PASS.** Non-material invocation is excluded; material plan remains. |
| Disjoint material manifests | **PASS.** Deterministically aggregated. |
| Repeated same-path safe merge | **PASS.** Newest current exact backup active; prior entry is history. |
| Recreated generated path | **PASS.** Current configuration entry active/present; prior entry is history. |
| Explicit manifest selection | **PASS.** Invocation-specific with no aggregate history. |

The late-write checks compared files and directories, including type, mode, and
content, not only project file bytes.

## Passive safety and simplified architecture

- A forged passive manifest redirected created/merge strings to a user file;
  plan generation only displayed/classified them and made no write.
- With `manifest.load` forced to raise, `rollback_project` still returned its
  fixed migration error, proving it does not consult stored metadata.
- The GUI has **Show restore instructions** and no Rollback button.
- No receipt module, HMAC, signature, signing-key path/environment option, or
  configurator credential exists.
- The old ambient key's metadata was unchanged by the exact suite.
- Runtime plus focused tests remain meaningfully smaller: 8,008 physical lines
  at the replacement initial SHA versus 5,285 now (`-2,723`).
- The passive serializer remains 82 lines; no dependency or alternate recovery
  framework was added.

## Acceptance-criterion verification

1. **PASS — no automatic rollback mutation.** The compatibility call reads no
   manifest/target and writes nothing; plans are display/export only.

2. **PASS — no HMAC/key subsystem.** Cryptographic receipt/key machinery and
   credential access remain absent.

3. **PASS — original CLI compatibility.** The complete compatibility suite
   passes and new/existing CLI smoke retains original collision, dry-run,
   profile, MCP, hook, settings, and command behavior.

4. **PASS — adaptive configuration/UI.** Typed config, rigor, risk inputs,
   profiles, MCP, detection, import/export, controller, and Tk GUI remain.

5. **PASS — read-only analysis/proposals.** Analyze, preview, and dry-run are
   non-mutating; conflict content and diffs remain available.

6. **PASS — transactional Apply.** Ordinary and write-success/raise failures for
   backups, generated files, manifests, and safe merges restore the exact
   complete pre-apply tree.

7. **PASS — passive manifests/exact backups.** Required audit fields,
   timestamp-scoped backup mappings, hashes, and modes remain correct.

8. **PASS — visible manual recovery.** Default core/CLI/GUI guidance selects the
   exact current mapping, preserves older history visibly, exports cleanly, and
   explicit selection stays invocation-specific.

9. **PASS — idempotency and drift.** No-op settings/files are not duplicated;
   required directories are repaired; proposal/config drift retains material
   guidance; repeated material selects current content accurately.

10. **PASS — meaningful net deletion.** The 1,847-line receipt subsystem remains
    deleted and runtime plus focused tests remain 2,723 lines smaller than the
    replacement initial state.

11. **PASS — truthful recovery documentation.** Documentation distinguishes
    same-process cleanup from later manual restoration and accurately describes
    current active/history selection without claiming automatic rollback.

12. **PASS — focused tests and full gate.** The two new direct regressions cover
    the previously missing repeated merge and recreated-file histories; all 48
    tests pass in both environments.

13. **PASS — required workflows/smoke.** Generated strict doctor,
    placeholders, new/existing workflows, and real/headless Tk all pass.

14. **PASS — preservation/dependency discipline.** Research and user work remain;
    no dependency, service, daemon, framework, or MCP server was introduced.

## Quality gates and observed output

- `git diff --check 36dab89..HEAD` — **PASS**.
- Exact `python -m unittest discover -s workflow_configurator/tests -v`, no environment
  overrides — **PASS**, 48 tests, 2.815s; ambient key unchanged.
- Complete suite on healthy project-local tmpfs — **PASS**, 48 tests, 2.859s.
- Repeated `.gitignore` core/CLI/controller/real-GUI path — **PASS**.
- Recreated generated-file core/CLI/controller/real-GUI path — **PASS**.
- Explicit material/no-op/drift manifest plans — **PASS**,
  invocation-specific.
- Forged passive plan and rollback-load guard — **PASS**, no writes.
- Three post-success write faults — **PASS**, exact complete-tree recovery.
- Generated doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder scan — **PASS**, no matches.
- New apply/reapply/default-plan and existing analyze/preview/apply/reapply —
  **PASS**.
- Migration-only rollback — **PASS**, concise and non-mutating.
- Real GUI restore-plan visibility/export/layout/manual wording — **PASS**.
- Direct and CLI-routed headless Tk smoke — **PASS**, no target creation.

## Non-blocking improvement

The heading “Older material history” can include a chronologically newer but
non-active event when a user manually restores content matching an earlier
manifest. “Other material history (not active mappings)” would be more exact.
This is wording only: the API preserves source manifest/time, active selection
still matches current state, and no acceptance criterion is affected.
