# Goal: Simplify existing-project recovery

## User Request

Proceed with the recommended simplification: remove the automatic rollback and
receipt-signing subsystem. Keep preview-first analysis, safe additive apply,
timestamped backups, an audit manifest, and clear manual restoration
instructions. Preserve the useful configurator, GUI, adaptive policy, and
existing-project functionality already implemented.

## Refined Goal

Replace security-sensitive automatic rollback with a small, non-mutating
recovery workflow. Applying configuration may add missing files and perform only
the two documented safe additive merges; it must save exact backups and a plain
audit manifest. CLI and GUI must show the user which generated files remain and
how to manually restore each merged file, but must never delete or restore
project content automatically from stored metadata.

## Acceptance Criteria

- [ ] Criterion 1: Remove automatic rollback mutation from the public core, CLI,
  and GUI. No operation reads a stored manifest/receipt to delete, overwrite, or
  restore a project path.
- [ ] Criterion 2: Remove HMAC signing, receipt signing keys, secure-key path
  handling, key environment/config options, and associated cryptographic state
  machinery. Analyze, preview, apply, tests, and GUI create no machine-local
  credential.
- [ ] Criterion 3: Preserve all CLI flags and behavior that existed at initial
  repository SHA `5ca7af1233eee27790ba99f0987c453890a7c3e1`.
  Newly introduced rollback flags may be removed or return a concise
  non-mutating migration message directing users to restore instructions.
- [ ] Criterion 4: Preserve the typed adaptive configuration model, rigor
  policy, complexity/size/testing options, stack/MCP selections, import/export,
  profile detection, headless controller, and Tkinter GUI.
- [ ] Criterion 5: Existing-project analyze, preview, and dry-run remain
  completely non-mutating. Conflicting user-owned files remain proposals with
  intended content and diffs.
- [ ] Criterion 6: Explicit apply remains transactional within the running
  process, adds only missing workflow files, and performs only documented
  additive `.gitignore` and `.vscode/settings.json` merges. Injected failure
  restores the exact pre-apply snapshot.
- [ ] Criterion 7: Before each safe merge, apply writes an exact timestamped
  backup outside the user-owned file. A versioned plain audit manifest records
  target identity, normalized configuration, created files, proposals, safe
  merges, backup paths, before/after hashes and modes, and required directories.
  The manifest is informational and is never trusted as authority for writes.
- [ ] Criterion 8: CLI and GUI provide a visible, exportable manual recovery
  plan listing generated paths for review/removal and exact backup-to-destination
  restoration instructions. The GUI uses wording such as “Show restore
  instructions,” not “Rollback,” and performs no restoration itself.
- [ ] Criterion 9: Reapply is idempotent: safe settings are not duplicated,
  identical files are recognized, missing required directories are recreated,
  and a current audit manifest/report accurately reflects configuration or
  proposal drift without changing conflicting files.
- [ ] Criterion 10: Remove obsolete authenticated-receipt/rollback code and its
  adversarial security test matrix. Runtime plus test code has a meaningful net
  deletion relative to SHA `36dab891319fad9bfcf10365d29d3d52bc41604c`;
  no dedicated signing/receipt state module remains unless it has been reduced
  to a small passive manifest serializer.
- [ ] Criterion 11: Documentation clearly distinguishes transactional recovery
  during a failed Apply from later manual restoration using backups. It must not
  claim that the tool can automatically or cryptographically roll back a prior
  apply.
- [ ] Criterion 12: Focused tests cover original CLI compatibility,
  configuration/policy behavior, GUI/headless operation, no-mutation analysis,
  proposals, safe apply, backup/manifest contents, restore instruction
  visibility, idempotency/drift, symlink/path hazards, and injected apply
  failure. The exact full command
  `python -m unittest discover -s workflow_configurator/tests -v` passes without
  environment overrides or access to user credentials.
- [ ] Criterion 13: Generated-project doctor strict mode, placeholder checks,
  new-project flow, existing-project flow, and real/headless Tk smoke pass.
- [ ] Criterion 14: Both research documents and all user work remain preserved.
  No dependency, external framework, service, daemon, or additional MCP server
  is introduced.

## Scope Boundaries

**In scope:**

- Simplifying the configurator's recovery model.
- Passive apply manifests, timestamped backups, and manual restore guidance.
- CLI, GUI, documentation, and focused tests affected by that simplification.
- Deleting superseded HMAC, key, receipt-state, and automatic rollback code.

**Out of scope:**

- Any automatic project-file deletion or restoration after Apply returns.
- Receipt authentication, signing keys, hardlink/symlink key defenses, or
  rollback authorization.
- Reopening unrelated research/tool choices.
- Adding external packages or another workflow framework.

## Applicable Project Conventions

**Quality gate command:**

- `python -m unittest discover -s workflow_configurator/tests -v`
- Generated-project strict doctor and unresolved-placeholder checks.
- Real/headless Tk smoke and observed new/existing project workflows.

**Commit convention:**

- Conventional commits.
- Builder: `refactor(configurator): [B] simplify recovery workflow`
- Inspector: `chore(configurator): [I] verify simplified recovery`
- Required trailers:
  `Assisted-by: OpenAI:GPT-5.6 Luna|Sol` and
  `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

**Guidelines:**

- Preserve original CLI behavior and user-owned files.
- Prefer deletion of superseded complexity over compatibility with unshipped
  experimental rollback APIs.
- Use explicit errors, transactional in-process cleanup, and focused tests.
- Optimize for maintenance and comprehension at equivalent required quality.
