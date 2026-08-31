# Inspector feedback — iteration 1

## Verdict

**FAIL**

The implementation establishes a useful typed core, safe normal-case brownfield
merges, receipts, an optional Tkinter adapter, and substantially improved
guidance. It does not yet meet the safety and completeness contract. In
particular, configurator-mode `--dry-run` can mutate a project, failed rollback
can leave a half-rolled-back project while its receipt still says `applied`, and
new-project core/apply omits the required `docs/plans` directory.

## Scope examined

- Compared the complete change from initial SHA
  `5ca7af1233eee27790ba99f0987c453890a7c3e1` through Builder commit
  `8c75f08b9f9b5c8012d72ee76b8103070022c640`.
- Reviewed all changed product files, with particular attention to
  `core.py`, `install.py`, `gui.py`, configurator tests, generated workflow
  guidance, memory/code-intelligence guidance, and the local workflow guard.
- Independently exercised legacy installation, new-project and existing-project
  analyze/preview/apply/reapply/rollback, safe merges, proposals, config
  round-trip and malformed input, symlinks, injected apply failure, injected
  rollback failure, headless GUI paths, and a real Tk window.

The Builder commit has the required title and trailers. The diff adds 24 files
or modifications (`5,548` insertions, `29` deletions), including the two
research documents.

## Blocking findings

### 1. `--dry-run` mutates when combined with configurator apply

`install.py:899-908` executes `apply_project` without considering
`args.dry_run`. Reproduction:

```text
python workflow_configurator/install.py TARGET --workflow new --apply --dry-run
rc=0 target_exists=yes agents_exists=yes
apply complete: 30 created, 0 safely merged
receipt: TARGET/.workflow_configurator/receipts/....json
```

This violates the preserved meaning of the pre-existing `--dry-run` flag and
the explicit no-mutation requirement. Reject incompatible operation flags or
make dry-run select preview before any apply path.

### 2. Rollback failure recovery leaves inconsistent state

I applied to an existing project with both `.vscode/settings.json` and
`.gitignore` safe merges, then injected an `OSError` on the second rollback
write. The operation raised `RollbackError`, but the post-failure snapshot did
not equal the applied snapshot:

```text
ROLLBACK_FAILURE raised=ok
restored_applied_snapshot=False
settings_still_applied=False
receipt_status=applied
```

`core.py:2243-2260` restores already-processed merge paths from the pre-apply
backup when rollback itself fails. That preserves the partial rollback instead
of restoring the pre-rollback/applied bytes. Receipt writing at
`core.py:2262-2268` is also outside the recovery `try`, so a receipt-write
failure after file changes can produce the same project/receipt disagreement.

Capture every pre-rollback byte/mode, restore that state on any rollback or
receipt-update failure, and add fault-injection tests at each rollback phase.

### 3. Configurator new-project apply omits `docs/plans`

Both core and CLI new-project apply created 30 files, but:

```text
plans_dir=False
```

Analysis advertises `directories = ["docs/plans"]` at `core.py:1831`, while
`apply_project` never creates report directories. The legacy installer still
creates it at `install.py:692-693`. Generated AGENTS guidance says plans live
there, so configurator mode is not a complete equivalent installation.

### 4. Analysis silently hides inaccessible project areas

With a mode-`000` directory containing `package.json`, analysis returned:

```text
warnings=[]
errors=[]
manifest_seen=False
command_seen=False
```

`_walk_project` and `_safe_file_text` swallow traversal/read failures
(`core.py:1305-1334`). The resulting report appears complete even though facts
were skipped. Record traversal limits and every inaccessible/unreadable area as
a structured warning/error.

### 5. The visible GUI does not present a usable preview

The real Tk window loads and exposes the requested controls, but Analyze and
Preview both call the same controller operation (`gui.py:60-65`) and the view
only displays counts in a one-line status (`gui.py:315-327`). There is no
visible action list, intended content, proposal diff, or preview export target.
Users therefore cannot review what Apply proposes from the GUI. Add a
read-only report/proposal view (or an explicit report export workflow) while
keeping the controller thin.

### 6. Installer logic remains substantially duplicated

The new core is independent of argparse/Tkinter, and the new configurator route
uses it. However, `install.py` still contains a second full installer:

- duplicated file/profile/MCP constants (`install.py:29-140`,
  `core.py:42-102`);
- duplicated MCP rendering (`install.py:364-399`, `core.py:935-1012`);
- duplicated selection, template, `.gitignore`, path-safety, and write/apply
  logic (`install.py:321-715` and corresponding core functions).

This does not satisfy the criterion that the CLI be a thin adapter with no
duplicated installer logic, and makes safety behavior diverge (as the dry-run
and `docs/plans` defects demonstrate). Preserve collision-refusal semantics
through a core policy/mode rather than maintaining two implementations.

### 7. Deliberate policy overrides are not consistently effective

For a light preset, setting `require_plan=true` and `require_review=true`
changes neither resolved field:

```text
require_true_changes_plan=False
require_true_changes_review=False
forced_plan=none for answers/research/docs; short intent before a low-risk edit
forced_review=self-review of the diff and one relevant check
```

`derive_policy` only implements the `False` branch for the boolean aliases
(`core.py:749-763`). Also, `--rigor strong --without-protocol-guard --preview`
still proposes all three workflow-guard files. Either implement both boolean
directions and the documented opt-out or remove misleading controls and
document the supported string overrides precisely.

## Acceptance-criterion verification

1. **FAIL — CLI compatibility.** Legacy full install, all profiles, all MCP
   choices, security hooks, context settings, placeholders, additive
   `.gitignore`, collision refusal (`rc=3`), and legacy dry-run (`target
   absent`) worked. Configurator apply ignores the existing `--dry-run` flag
   and writes 30 files, so every existing flag does not retain its contract.

2. **FAIL — shared typed core/thin adapters.** `core.py` has no argparse or
   Tkinter dependency and GUI controller operations use it. The CLI retains a
   parallel full installer and duplicates core rendering, safety, and apply
   behavior; see blocking finding 6.

3. **PASS — versioned configuration model.** Version 1 JSON covers complexity,
   size, testing, profiles, MCP, commands, rigor, and safety options. Unknown
   fields/values and malformed JSON raise path- and line-specific
   `ConfigError`s.

4. **PASS — import/export and defaults.** A full config with an extra `build`
   command round-tripped exactly. Export to an explicit external path neither
   required nor created the target. Plain legacy install retained Python/data
   science, pytest/Ruff/Pyright, context settings, and artifact-ignore
   defaults.

5. **FAIL — concrete rigor and overrides.** Presets resolve all required
   dimensions and the GUI shows the resolved policy. Deliberate boolean
   `true` overrides are accepted but are no-ops, and the explicit strong-guard
   opt-out is ineffective; see blocking finding 7.

6. **PASS with documentation gap — adaptive guidance.** Minimal/small/no-test
   light policy produced `no-code-test-or-smallest-check`; advanced/large/broad
   escalated to broad/strong behavior and a protocol guard. Output is
   deterministic. The exact risk scoring/escalation thresholds are not
   documented, so `docs/CONFIGURATOR.md` should state how complexity and size
   change resolved policy.

7. **PASS — lean-change contract.** Generated guidance contains search/reuse,
   explicit non-goals, no speculative abstraction/config/dependency, minimal
   surface, and correctness/operational boundaries. No universal LOC cap or
   researched external tool is installed.

8. **PASS — optional standard-library GUI.** Tkinter is imported only in the
   window class. The real display smoke opened a `760x620` window with all four
   profiles, all five MCP choices, configuration controls, commands, safety
   toggles, and policy text. No GUI dependency was added.

9. **FAIL — GUI workflow usefulness.** Apply/rollback have confirmation,
   headless controller smoke works, and errors become concise status. Analyze
   and Preview expose no visible report, proposal, content, or diff, so the GUI
   cannot actually support preview-first review; see blocking finding 5.

10. **PASS for readable projects — structured brownfield analysis.** Normal
    analysis identified Python/FastAPI signals, manifests, Git state,
    Conda+uv conflict, customizations, partial/template files, and action
    classifications. Symlink destinations became `unsafe`. Silent unreadable
    traversal is accounted against criterion 15.

11. **FAIL — no-mutation analysis/dry-run/preview.** Repeated core and CLI
    analyze/preview preserved complete readable-target snapshots and did not
    create `.workflow_configurator`; reports matched. Configurator
    `--apply --dry-run` mutates, directly violating this criterion.

12. **PASS — documented safe apply.** Existing AGENTS and MCP bytes were
    unchanged. Apply added missing files, appended only the artifact rule, and
    added only absent search exclusions. `.gitignore` mode `0640` and settings
    mode `0600` were preserved. Conflicting exclusion values remained
    proposals.

13. **PASS — proposals.** Conflicting AGENTS/MCP actions included rendered
    intended content, current/intended hashes, metadata, and unified diff.
    Original files stayed byte-for-byte unchanged through apply and rollback.

14. **PASS for normal/tamper paths — receipts and verified rollback.** Normal
    receipts/backups explained created and merged paths; normal rollback
    removed created files and restored both safe merges. Missing/malformed,
    escaping, symlinked, modified-created-file, and modified-backup checks are
    present. Rollback fault recovery itself fails criterion 15.

15. **FAIL — hazards and partial failure.** Symlink apply was blocked and
    injected apply failure after 27 writes restored the complete pre-apply
    snapshot. Inaccessible analysis is silently incomplete, and an injected
    rollback write failure leaves half-rolled-back content with an `applied`
    receipt; see blocking findings 2 and 4.

16. **PASS — practical idempotency.** Repeated preview was identical and
    non-mutating. Reapply returned no created/merged actions, reused the
    receipt, did not rewrite files/settings, and did not duplicate the
    `.gitignore` rule.

17. **FAIL — complete new-project mode.** New apply rendered all selected
    files without placeholders and generated diagnostics otherwise worked,
    but it omitted `docs/plans`. Detection correctly recommended rather than
    forced profiles and surfaced Conda+uv markers.

18. **PASS — memory/code-intelligence guidance.** Guidance now prefers
    project-scoped retrieval, atomic `mempalace_checkpoint`, and
    `kg_supersede`, keeps live files authoritative, and describes degraded
    fallback. Nonexistent status/coverage/change APIs are explicitly
    capability-detected rather than required.

19. **PASS with control caveat — lifecycle guard.** The guard uses documented
    `Stop`/`agentStop` surfaces, has a 3-second timeout, checks only local
    state, and explicitly disclaims external memory verification and
    fail-open limitations. The misleading strong guard opt-out should still be
    fixed under criterion 5.

20. **PASS with minor gap — documentation.** README and CONFIGURATOR cover
    architecture, compatibility, GUI launch, config/presets, examples,
    brownfield flow, conflict/safety policy, rollback, and headless validation.
    Add the exact risk/escalation mapping and the GUI preview presentation once
    implemented.

21. **FAIL — focused tests are insufficient for shipped risks.** Existing
    additions cover basic round-trip, one strong policy, analysis snapshot,
    proposals, normal apply/rollback, malformed receipts, a symlink, and one
    new-target apply failure. They do not cover configurator CLI dry-run,
    new-core directory completeness, all preset/override semantics, actual
    reapply, visible GUI preview/apply/rollback, unreadable traversal, apply
    failure after a safe merge, or rollback-phase failures. The missed cases
    correspond directly to blocking defects above.

22. **FAIL — required full gate was not observed passing.** The exact unittest
    discovery command was run with project-local `TMPDIR`. Twelve tests
    reported `ok`; it then remained stuck for more than 14 minutes in
    `test_environment_manager_detection_and_conflict` cleanup, with the Python
    process in uninterruptible NTFS `vfs_unlink` sleep. A kill was requested
    but remained pending, so no final unittest result exists. Both headless GUI
    entry points returned `ok: true`; a real Tk window was also exercised.
    New/existing workflows produced observed output, including the failures
    above.

23. **FAIL — dependency discipline passes, maintainability does not.** No
    dependency manifest, service, runtime, framework, or MCP backend was added;
    implementation is standard-library-first. The 2,357-line core plus the
    retained duplicated installer implementation is not the requested lean
    separation and already produces divergent behavior.

24. **PASS — research/user work preservation.** Both named research documents
    are present and tracked in the Builder commit. The initial-to-HEAD diff
    contains no unrelated deletion or dependency-manifest change.

## Quality gates and observed smoke results

- `git diff --check 5ca7af1..HEAD` — **PASS**.
- Changed Python modules compiled — **PASS**.
- `python -m unittest discover -s workflow_configurator/tests -v` — **NO FINAL
  RESULT / FAIL for acceptance**, as described under criterion 22.
- `python workflow_configurator/gui.py --headless-smoke` — **PASS**, 23 actions,
  0 errors.
- `python workflow_configurator/install.py --headless-smoke .` — **PASS**, 23
  actions, 0 errors.
- Real Tk window construction/update/destroy on available `DISPLAY=:0` —
  **PASS**.
- Generated-project doctor with configured run command and `--strict` —
  **PASS**, 0 errors, 0 warnings.
- Installed-project unresolved-placeholder check — **PASS**, no matches.
- Legacy full install/collision/dry-run — normal cases **PASS**.
- Existing analyze/preview/safe apply/reapply/normal rollback — normal cases
  **PASS**.
- Injected apply failure after a safe merge — **PASS**, complete snapshot
  restored.
- Injected rollback failure — **FAIL**, inconsistent half-rollback observed.

## Required next iteration

1. Make `--dry-run` non-mutating in every CLI mode and test all operation-flag
   combinations.
2. Make rollback transactional, including receipt-status update failures, and
   add phase-by-phase fault injection.
3. Create and receipt/handle required empty directories such as `docs/plans`
   in configurator new-project mode.
4. Surface incomplete traversal/read diagnostics in analysis.
5. Provide an actual visible GUI preview/proposal view.
6. Consolidate the legacy and configurator installer implementations behind
   shared core primitives.
7. Make accepted policy override controls effective and test every preset and
   override direction.
8. Re-run the complete required suite to a final result in a healthy
   filesystem environment.
