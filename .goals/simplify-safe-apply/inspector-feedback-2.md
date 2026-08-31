# Inspector feedback — replacement goal, iteration 2

## Verdict

**FAIL**

Iteration 2 completely fixes the Apply transaction defect and fixes ordinary
recovery-plan loss after no-op, proposal-only, and configuration-only reapply.
Explicit manifest selection remains invocation-specific, passive metadata never
authorizes a write, all 46 tests pass in both required environments, and every
other replacement-goal workflow remains healthy.

One concrete recovery-guidance defect remains. When the same generated or
safe-merge path is material in more than one invocation, default aggregation
always keeps the **oldest** entry. After a merge is manually restored, user
content changes, and the merge is applied again, core/CLI/GUI show only the old
backup as `manual` and hide the newer exact backup whose state is `ready`.
Likewise, a generated file deleted and recreated under changed configuration is
misclassified from its old hash. This violates the targeted requirement to
aggregate all still-relevant material manifests and provide exact default
recovery guidance.

## Scope and method

- Read only `.goals/simplify-safe-apply/goal.md` and
  `inspector-feedback-1.md`; no superseded authenticated-rollback criteria were
  applied.
- Compared the complete replacement result from initial SHA
  `36dab891319fad9bfcf10365d29d3d52bc41604c` through Builder commit
  `98a0b47f163e870bcacfd9150f2da9e638aca142`.
- Read the complete iteration-2 diff and resulting core, passive manifest
  serializer, CLI, GUI, documentation, and focused tests.
- Ran the exact full suite without environment overrides and again on healthy
  project-local tmpfs.
- Independently tested write-success/raise recovery with complete
  file/directory/type/mode/content snapshots, ordinary and repeated material
  aggregation, explicit selection, forged passive manifests, original CLI
  options, new/existing workflows, doctor/placeholders, EUID-1 traversal, and
  visible/headless Tk.

The Builder commit title and required trailers are correct. The research
documents and user work remain tracked, and no dependency or external runtime
was introduced.

## Blocking finding

### Default deduplication hides the current same-path material event

`_material_manifests` correctly gathers target-matching manifests with created
files or safe merges and sorts them deterministically
(`core.py:2560-2588`). `_aggregate_restore_material` then iterates oldest to
newest but uses `setdefault` by destination path for both created files and
merges (`core.py:2654-2678`). Every later material event for the same path is
discarded before live-state classification.

I exercised a realistic two-merge history:

1. Apply the additive `.gitignore` merge; manifest A records exact backup A.
2. Manually restore backup A, as the product instructs.
3. Add new user content to `.gitignore`.
4. Apply again; manifest B records exact backup B and current applied hash.
5. Request default restore instructions.

Observed:

```text
material manifests: [A, B]
aggregate selected: backup A
aggregate state: manual
explicit manifest B state: ready
```

The default core plan includes both manifest filenames, but its sole
`.gitignore` instruction points to backup A. CLI JSON/text and the real GUI show
that same old mapping and omit backup B. Copying A would discard the user
content added before the second apply; B is the exact inverse source for the
current merge.

The analogous generated-file case also fails classification. After deleting a
generated `AGENTS.md` and recreating it under changed configuration:

```text
aggregate AGENTS.md state: manual
explicit current manifest state: present
material manifests: 2
```

This is not an automatic-write or data-loss bug—the plan remains manual—but it
is a concrete criterion 8/9 violation. Aggregate by material **event**, or choose
the newest entry per path whose hashes/modes match the current state. If older
history remains useful, list it separately rather than replacing the exact
current mapping. Add repeated same-path merge and recreated-file regressions
through core, CLI, and GUI.

## Iteration-1 failure retest

| Prior failure | Iteration-2 result |
|---|---|
| Completed backup write then exception | **Fixed.** Complete pre-apply tree, including metadata directories, restored exactly. |
| Completed generated-file write then exception | **Fixed.** File and all new parent/metadata directories removed exactly. |
| Completed manifest write then exception | **Fixed.** Manifest and metadata tree removed exactly. |
| No-op reapply hides original material manifest | **Fixed.** Default plan retains the original generated paths and backups. |
| Proposal/config-only drift hides earlier material | **Fixed.** Non-material manifests are excluded while earlier material remains. |
| Multiple disjoint material manifests | **Fixed.** Paths from both are included in deterministic order. |
| Explicit selection | **PASS.** It contains only that invocation's entries. |
| Repeated same-path material history | **FAIL.** Oldest entry hides the exact current entry. |

## Major successes

### Exact transactional cleanup

- `_write_new_bytes` registers the path immediately after successful
  `O_EXCL` open through an operation-scoped `ContextVar`.
- Independent wrappers let backup, generated-file, and manifest writes finish,
  then raised before their call sites could update local lists/flags.
- All three operations raised `ApplyError`, restored user merge bytes/modes,
  removed every owned file, and restored the exact complete pre-apply tree,
  including target and `.workflow_configurator` directory presence, types, modes, and
  contents.
- Every normal `fail_after` boundary and a merge write which replaced then
  raised also recovered exactly.

### Ordinary aggregation and passive boundary

- A first material apply followed by no-op and config/proposal-only applies
  retains the first generated paths and exact merge mappings by default.
- A later disjoint React material apply is aggregated with the first; both
  material manifests are ordered deterministically and non-material manifests
  are excluded.
- Repeated calls return identical plans.
- Explicit selection of material or non-material manifests remains exactly
  invocation-specific.
- `ConfiguratorController`, CLI, and GUI use the same core default plan.
- A forged manifest redirected created/merge strings to a user README;
  generating instructions changed no byte.
- Monkeypatching manifest loading to fail proved the rollback compatibility
  entry point does not read stored metadata before returning its fixed
  migration error.

### Complete replacement-goal regression

- No receipt module, HMAC, signature, signing key, key path/environment option,
  or machine-local configurator credential exists. The ambient legacy key's
  metadata remained unchanged during the exact suite.
- Original CLI defaults/options, all profiles/MCP choices, commands, hooks,
  context settings, collision refusal, opt-outs, and dry-run passed.
- Existing analyze/preview preserved exact snapshots; conflicts retained
  intended content/diffs and originals remained unchanged.
- Safe apply changed only missing workflow files and documented additive
  `.gitignore`/settings fields; exact backups, before/after hashes, and modes
  remained correct.
- New apply/reapply and the ordinary default plan passed; generated strict
  doctor reported zero errors/warnings and installed placeholders were absent.
- Existing apply/reapply/config-proposal drift and migration-only rollback
  passed.
- Real GUI layout, preview/diff, report/config/restore exports, apply
  confirmation, ordinary aggregated plan, guard intent, and identity passed;
  no Rollback button exists.
- Direct and CLI-routed headless smoke passed without target mutation.
- EUID-1 unreadable traversal remained actionable and non-mutating.
- Runtime plus focused tests remain meaningfully smaller: 8,008 physical lines
  at the replacement initial SHA versus 5,088 now (`-2,920`).

## Acceptance-criterion verification

1. **PASS — no automatic recovery mutation.** Rollback compatibility never
   reads a manifest or target; plan generation only reads/displays/exports.

2. **PASS — no credential subsystem.** HMAC/key/receipt state is absent and no
   machine-local credential is created or accessed.

3. **PASS — original CLI compatibility.** Every original option and behavior
   remains covered and independently exercised; the later rollback flag gives
   the allowed non-mutating migration message.

4. **PASS — adaptive configuration/UI.** Typed config, rigor, risk controls,
   profiles, MCP, detection, import/export, controller, and Tk GUI remain.

5. **PASS — no-mutation analysis/proposals.** Analyze, preview, and dry-run are
   read-only; conflicting user content remains byte-identical with useful diffs.

6. **PASS — transactional Apply.** All ordinary and post-success injected fault
   boundaries restored the exact complete pre-apply tree.

7. **PASS — passive manifest/backups.** Required audit fields and exact
   timestamp-scoped pre-merge backup bytes/hashes/modes are present.

8. **FAIL — default exact recovery guidance.** Ordinary no-op/drift aggregation
   is fixed, but repeated material for one path hides the newer exact backup and
   current generated entry; see the blocking finding.

9. **FAIL narrowly — current repeated-material drift classification.** Content
   reapply is idempotent where appropriate, required directories are repaired,
   and invocation manifests are accurate. The default report misclassifies a
   current recreated path/merge from the oldest event.

10. **PASS — meaningful net deletion.** The 1,847-line receipt module remains
    deleted, the passive serializer is 82 lines, and runtime plus focused tests
    remain 2,920 lines smaller than the replacement initial state.

11. **PASS for the recovery-model distinction.** Documentation clearly
    separates same-process cleanup from later manual restoration and makes no
    automatic/cryptographic rollback claim. Its newer claim that default
    deduplication preserves all current material is overbroad for the blocking
    same-path case.

12. **FAIL narrowly — one material-history coverage gap.** All 46 tests pass and
    cover the required categories plus both prior failures, but omit a path
    becoming material in more than one invocation with different current
    hashes/backups.

13. **PASS — quality gates/workflows.** Both suites, doctor/placeholders,
    new/existing workflows, real/headless Tk, and unreadable traversal pass.

14. **PASS — preservation/dependency discipline.** Research and user work remain;
    no dependency, framework, service, daemon, or MCP server was introduced.

## Quality gates and observed output

- `git diff --check 36dab89..HEAD` — **PASS**.
- Exact `python -m unittest discover -s workflow_configurator/tests -v`, no environment
  override — **PASS**, 46 tests, 2.759s; ambient key unchanged.
- Complete suite on healthy project-local tmpfs — **PASS**, 46 tests, 2.800s.
- Generated strict doctor — **PASS**, 0 errors/warnings.
- Exact installed placeholder scan — **PASS**, no matches.
- Original CLI all-option/collision/dry-run smoke — **PASS**.
- New/existing analyze/preview/apply/reapply/drift/migration workflows —
  **PASS**.
- Post-success backup/generated/manifest faults — **PASS**, exact complete-tree
  recovery.
- No-op, proposal/config-only, and disjoint-material default aggregation —
  **PASS**.
- Explicit manifest selection — **PASS**, invocation-specific.
- Forged passive manifest / rollback-load guard — **PASS**, no write/read
  authority.
- Repeated same-path merge default plan — **FAIL**, old backup `manual`; current
  exact backup omitted despite explicit state `ready`.
- Recreated generated path default state — **FAIL**, `manual`; explicit current
  state `present`.
- Real/headless GUI and ordinary aggregation visibility — **PASS**; repeated
  same-path GUI inherits the blocking old mapping.
- Unreadable traversal as EUID 1 — **PASS**, actionable/no mutation.

## Required correction

For each repeated destination, preserve material event history or select the
newest entry whose current hashes/modes classify as `present`, `ready`, or
`already-restored`; do not let `setdefault` on the oldest manifest discard the
exact current backup/hash. Cover both repeated safe merge and recreated
generated-file histories through core, CLI, and GUI.
