# Inspector feedback — replacement goal, iteration 1

## Verdict

**FAIL**

The replacement substantially achieves the intended simplification. The
1,847-line authenticated receipt/key subsystem is deleted, a small passive
manifest serializer remains, automatic rollback never reads metadata, exact
safe-merge backups and visible manual plans work, both complete test runs pass,
and runtime plus tests shrink by more than 3,200 lines.

Two focused defects remain. First, Apply is not transactional if a completed
new-file write reports failure before its caller records that path: injected
post-write failures leave a backup, generated project file, or manifest plus
metadata directories behind. Second, the default “latest manifest” plan becomes
empty after an idempotent reapply, hiding the earlier generated paths and backup
restore mappings that the user still needs. Explicit selection of the first
manifest remains correct.

## Scope and method

- Read only the immutable replacement goal at
  `.goals/simplify-safe-apply/goal.md`.
- Compared the complete implementation from replacement initial SHA
  `36dab891319fad9bfcf10365d29d3d52bc41604c` to Builder commit
  `b509ebb4811177849fe214c4ca1c8179f737a4c0`.
- Read the resulting core, passive serializer, CLI, GUI, docs, and focused
  tests; did not apply superseded automatic-rollback requirements.
- Ran the exact full suite with no environment override, then again on a
  healthy project-local tmpfs.
- Independently exercised every original CLI option, configured new/existing
  workflows, passive/tampered manifests, exact backups, migration-only rollback,
  dry-run/analyze/preview, proposal drift, required-directory drift,
  idempotency, all built-in failure boundaries, post-write faults, generated
  doctor/placeholders, unreadable traversal as EUID 1, and real/headless Tk.

The Builder commit title and required trailers are correct. Both research
documents and prior goal history remain tracked. No dependency manifest,
service, framework, daemon, or MCP backend was added.

## Blocking findings

### 1. Completed new-file writes can escape same-process transaction cleanup

`apply_project` calls `_write_new_bytes` and records the new path only after the
call returns:

- backup: write at `core.py:2341`, append at `core.py:2342`;
- generated project file: write at `core.py:2355`, append at
  `core.py:2356`;
- manifest: write at `core.py:2411-2417`, set `manifest_written=True` at
  `core.py:2418`.

The exception cleanup at `core.py:2420-2441` knows only the paths already added
to those lists/flags. I wrapped the real `_write_new_bytes`, allowed it to
complete its atomic creation, then raised before returning to each call site.
All three applies correctly raised `ApplyError`, but the complete pre-apply
snapshot was not restored:

```text
LATE_WRITE backup snapshot_restored False
remaining .workflow_configurator/backups/<id>/.vscode/settings.json

LATE_WRITE created snapshot_restored False
remaining AGENTS.md

LATE_WRITE manifest snapshot_restored False
remaining .workflow_configurator/manifests/<id>.json
```

The backup/manifest cases also left their newly created `.workflow_configurator`
directory trees. This is the same important fault boundary previously handled
for merge replacement: a write may succeed and its caller may still observe an
exception (for example, a wrapper, audit hook, or post-write filesystem error).
It violates criterion 6's requirement that injected failure restore the exact
pre-apply snapshot.

Register intended owned paths before calling the write primitive, or have the
primitive return/raise explicit ownership state that cleanup consumes. Add
write-then-raise tests independently for backups, project files, and the
manifest, comparing the complete tree including `.workflow_configurator`.

### 2. A no-op reapply makes default recovery guidance lose useful history

Each explicit apply writes a new manifest. On an unchanged reapply,
`created_files=[]` and `safe_merges=[]`, which is truthful for that invocation.
`restore_instructions(target=...)` then selects that newest manifest solely by
timestamp (`core.py:2474-2516`). The default CLI and visible GUI therefore show
no generated paths and no safe-merge backups after reapply:

```text
NEW_PLANS first-generated 35 latest-generated 0
EXISTING first plan merges 2 latest plan merges 0

GUI_CONTROLLER_FIRST generated 27 merges 1
GUI_CONTROLLER_AFTER_REAPPLY generated 0 merges 0 report_none=True
```

The first manifest still contains correct paths and exact backup mappings when
selected explicitly, so no project safety issue results. The default
`--restore-instructions` and GUI button nevertheless cease to provide the
manual recovery information promised by criterion 8 after the normal,
explicitly required idempotent-reapply workflow.

Preserve a cumulative passive recovery inventory, point a no-op manifest to the
prior applicable manifest, or make default restore guidance select/aggregate
the newest manifests that contain the still-relevant generated/merge records.
Keep each invocation's audit record truthful and continue treating all content
as display-only.

## Major successes

### Simplification and passive trust boundary

- `workflow_configurator/receipt.py` is deleted in full; no HMAC, signature,
  signing-key path, signing environment variable, cryptographic receipt, or
  machine-local configurator credential remains.
- Exact-suite observation confirmed the old ambient key metadata was unchanged.
- `manifest.py` is 82 lines and serializes only schema 1 audit data.
- `rollback_project` raises a fixed migration message without reading a
  manifest or target. Monkeypatching `manifest.load` to fail proved the
  compatibility call does not consult metadata.
- A fully forged manifest redirected generated and safe-merge entries to a user
  README; restore-plan generation only displayed the strings and changed no
  target byte.
- Runtime plus focused test code fell from 8,008 to 4,780 lines (`-3,228`), while
  the complete replacement diff overall is `873` insertions / `4,092` deletions.

### Passive manifests, backups, and manual guidance

- A normal manifest includes schema/id/time, canonical target plus device/inode,
  normalized configuration, created paths/hashes/modes, proposals, safe merge
  paths/backups/before-after hashes/modes, required directories, and
  `manual-only` policy.
- Both `.gitignore` and settings backups were written before their merge,
  byte-identical to the originals, mode-matching, timestamp-ID-scoped, and
  correctly paired with the applied hashes.
- Explicit CLI and GUI plans list every generated path and exact
  backup-to-destination mapping, export JSON, state that actions are manual, and
  leave the complete target unchanged.
- The GUI contains **Show restore instructions** and **Export restore plan**,
  and no Rollback button.
- `--rollback` returns code 2 with a concise migration message and no mutation.

### Apply, proposals, and ordinary recovery

- Safe apply preserved user AGENTS, MCP, README, and conflicting settings;
  only missing workflow files and the two documented additive merges changed.
- Modes `0640` and `0600` were preserved for `.gitignore` and settings.
- Every built-in `fail_after` boundary restored the exact complete snapshot and
  removed `.workflow_configurator`.
- A merge replacement which completed and then raised was restored from the
  already registered before-image.
- Required `docs/plans` drift was recreated and recorded.
- Configuration/proposal drift wrote a current manifest while the conflict
  remained byte-identical.
- Analyze, preview, export, configurator dry-run, and legacy dry-run were
  non-mutating.

### Compatibility, diagnostics, and UI

- Every option present at original SHA `5ca7af1` remains accepted.
- Independent all-option legacy install passed profiles, all MCP choices,
  security hooks, context settings, commands, collision refusal (`rc=3`),
  opt-outs, and dry-run.
- Generated new project was placeholder-free and strict-doctor clean.
- Existing analysis surfaced Conda+uv signals and proposal diffs.
- EUID-1 unreadable traversal produced
  `traversal.permission-denied`, blocked apply, and wrote no metadata.
- Real Tk rows, preview/content/diff, config/report/restore export,
  apply confirmation, full explicit restore plan, guard auto/on/off, and
  derived/explicit/imported identity passed.
- Direct and CLI-routed headless smoke passed without creating targets.

## Acceptance-criterion verification

1. **PASS — no automatic manifest-authorized mutation.** The removed rollback
   compatibility API/CLI reads no manifest and writes nothing. Restore-plan
   reading is display/export only.

2. **PASS — no HMAC/key/credential subsystem.** Receipt/key code and tests are
   gone, imports/searches find none, non-mutating and apply paths create no
   machine-local credential, and the pre-existing ambient key was untouched.

3. **PASS — original CLI compatibility.** Every initial option remains and the
   complete original behavior tests plus independent all-option workflows pass.
   The later rollback flag provides the permitted concise migration path.

4. **PASS — adaptive product capability.** Typed config, rigor, risk inputs,
   profiles, MCP, detection, import/export, controller, and Tk GUI remain.

5. **PASS — read-only analysis/proposals.** Analyze, preview, and dry-run
   preserve complete targets. Conflicts expose intended content/diffs and remain
   byte-identical.

6. **FAIL — one transaction boundary remains incomplete.** Built-in failures
   and merge-write-after-replace recovery pass, but completed backup/generated/
   manifest writes that then raise escape cleanup; finding 1.

7. **PASS — passive audit data and exact backups.** All required fields,
   before/after hashes and modes, timestamped IDs, and exact pre-merge bytes were
   independently verified.

8. **FAIL — default plan is not durable across reapply.** Explicit plans and
   visible CLI/GUI mapping are clear and exportable, but the normal no-argument
   CLI/GUI plan becomes empty after idempotent reapply; finding 2.

9. **PASS for content idempotency/drift.** Settings/files are not duplicated or
   rewritten; required directories are repaired; current manifests accurately
   describe each invocation's config/proposals. The recovery-plan history gap
   is recorded under criterion 8.

10. **PASS — meaningful net deletion.** The 1,847-line receipt module and
    adversarial matrix are removed. Runtime+tests have a 3,228-line net deletion;
    the passive serializer is only 82 lines.

11. **PASS — documentation distinguishes recovery models.** It accurately
    separates same-process Apply cleanup from later owner-reviewed backup
    copying and makes no automatic/cryptographic rollback claim. Finding 1 is an
    implementation gap in the promised Apply transaction.

12. **FAIL — focused tests miss both shipped defects.** The 44 passing tests
    cover the requested broad categories but only inject `fail_after` after
    successful caller bookkeeping, not write-success/raise-before-bookkeeping.
    They select the latest no-op manifest without checking that default
    user-facing recovery remains useful after reapply.

13. **PASS — final workflows/smoke.** Both complete suites, strict doctor,
    placeholders, new/existing flows, EUID-1 traversal, and real/headless Tk
    passed.

14. **PASS — preservation/dependency discipline.** Research and user work remain;
    no dependency, external runtime, service, framework, daemon, or MCP server
    was introduced.

## Quality gates and observed smoke

- `git diff --check 36dab89..HEAD` — **PASS**.
- Exact `python -m unittest discover -s workflow_configurator/tests -v` with no
  environment override — **PASS**, 44 tests, 2.640s; ambient key unchanged.
- Complete suite on healthy project-local tmpfs — **PASS**, 44 tests, 2.695s.
- Generated-project doctor `--strict` — **PASS**, 0 errors/warnings.
- Exact installed placeholder scan — **PASS**, no matches.
- Full original CLI options/collision/dry-run/opt-outs — **PASS**.
- New/existing analyze/preview/apply/reapply/migration-only rollback —
  **PASS** for project behavior.
- Passive/tampered manifest never authorizes a write — **PASS**.
- Exact two-backup mapping, hashes, modes, and explicit plans — **PASS**.
- Built-in `fail_after` boundaries and post-merge-write fault — **PASS**,
  exact recovery.
- Post-backup, post-generated-file, and post-manifest write faults — **FAIL**,
  partial artifacts remain.
- Default plan after no-op reapply — **FAIL**, empty generated/merge guidance.
- Real/headless GUI, explicit plan visibility/export, policy, and identity —
  **PASS**.
- Unreadable traversal as mapped EUID 1 — **PASS**, actionable/no mutation.

## Required next iteration

1. Register backup, generated-file, and manifest paths before invoking
   `_write_new_bytes`, or return explicit ownership state, so a completed
   write-then-raise is always cleaned.
2. Add one direct post-success exception regression for each new-file category
   and compare the complete tree, including metadata.
3. Keep per-invocation manifests truthful while making no-argument CLI/GUI
   restore guidance retain or aggregate earlier still-relevant paths/backups
   after a no-op reapply.
4. Test the visible/default plan after reapply, not only explicit old-manifest
   selection.
