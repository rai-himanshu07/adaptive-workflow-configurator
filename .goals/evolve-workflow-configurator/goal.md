# Goal: Evolve the agent workflow configurator

## User Request

Turn the completed workflow/tool research into a production-quality improvement
of `workflow_configurator`. Preserve the existing CLI and current behavior while adding
adaptive project/build configuration, a lightweight local Python GUI, and a
safe, useful workflow for analyzing and configuring existing projects. The
implementation should apply the researched lessons about proportional rigor,
testing, memory/code intelligence, brownfield adoption, lean maintainable code,
diagnostics, previews, backups, and recovery without becoming another large
framework.

The user selected this existing-project conflict policy:

> Add missing files, merge only known-safe settings, and leave conflicting
> files as reviewable proposals.

## Refined Goal

Evolve the current single-file installer into a cohesive, standard-library-first
developer utility with a reusable typed core, backward-compatible CLI, and thin
Tkinter GUI. It must support new and existing repositories, derive concrete
workflow behavior from project complexity, size, testing, and engineering-rigor
configuration, and make all existing-project analysis preview-first and
non-mutating. Explicit apply may add missing files and perform only
well-defined, reversible safe merges; conflicting user-owned files must remain
untouched and be emitted as proposals.

The result must improve maintainability rather than merely reduce LOC or model
cost. Required behavior, correctness, safety, error handling, accessibility,
observability, and existing project conventions are hard constraints.

## Acceptance Criteria

- [ ] Criterion 1: The public behavior and every existing flag of
  `python workflow_configurator/install.py TARGET [options]` remain supported. Existing
  tests for defaults, collision refusal, dry run, MCP generation, security
  hooks, context settings, placeholders, and `.gitignore` behavior continue to
  pass.
- [ ] Criterion 2: Installer logic is exposed through a reusable, typed Python
  application/core layer that does not depend on argparse or Tkinter. CLI and
  GUI are thin adapters over the same analysis/preview/apply operations; logic
  is not duplicated between interfaces.
- [ ] Criterion 3: A versioned, JSON-serializable configuration model supports
  at least project complexity (`minimal`, `standard`, `advanced` or documented
  equivalents), project size/scope (`small`, `medium`, `large`), testing level,
  selected stack profiles, MCP choices, command overrides, and engineering
  rigor. Invalid values and malformed files produce actionable errors rather
  than silent fallbacks.
- [ ] Criterion 4: Configuration can be imported and exported without modifying
  a target project, and round-tripping preserves all supported settings.
  Backward-compatible CLI defaults reproduce the current personal
  Python/data-science installation when new options are omitted.
- [ ] Criterion 5: Engineering rigor is modeled as concrete policy dimensions,
  not only a label. At minimum it controls planning gates, focused versus broad
  validation, documentation/handoff expectations, memory/code-intelligence
  lifecycle, change isolation, safety hooks/approvals, and review requirements.
  Named presets have documented values, and the GUI visibly shows what a preset
  enables and permits deliberate overrides.
- [ ] Criterion 6: Complexity, size, testing, and rigor choices materially alter
  generated workflow guidance/configuration in documented, deterministic ways.
  Research/docs-only and low-risk work have an explicit no-code-test or
  smallest-check path; high-risk work requires stronger planning, validation,
  and review.
- [ ] Criterion 7: Generated guidance includes a maintenance-first lean-change
  contract: search/reuse before adding code, explicit non-goals, no speculative
  abstractions/config/dependencies, minimal public/file surface, and protection
  of required correctness and operational boundaries. It must not impose
  universal hard LOC limits or install Ponytail/other researched tools.
- [ ] Criterion 8: A standard-library Tkinter GUI is available through a clear
  entry point and remains optional. It exposes target selection, new versus
  existing project workflow, complexity, project size, testing level, stack
  profiles, commands, MCP choices, and rigor policy/overrides without requiring
  third-party GUI dependencies.
- [ ] Criterion 9: The GUI can analyze, preview, export/import configuration,
  explicitly apply safe changes, and show concise status/errors. Destructive or
  mutating actions require clear confirmation. UI code remains thin and
  testable without a display; a documented headless smoke path exercises module
  loading/controller behavior, and the real Tkinter window is exercised when a
  display is available.
- [ ] Criterion 10: Existing-project analysis is read-only with respect to the
  target by default. It detects relevant manifests/languages, environment
  manager signals, commands where safely inferable, Git/customization state,
  existing AGENTS/instructions/skills/hooks/MCP/settings/handoff/plan files,
  partial installations, symlinks, and collisions. It returns a structured
  report classifying actions such as identical, missing, safe merge, and
  conflicting proposal.
- [ ] Criterion 11: Analysis/dry-run/preview creates no files or directories
  inside an existing target. Preview artifacts are kept in memory, printed, or
  written only to an explicit output location/system temporary area. Tests
  compare complete target snapshots before and after analysis.
- [ ] Criterion 12: Explicit safe apply adds missing workflow files and performs
  only documented safe merges. At minimum `.gitignore` remains additive and
  mode-preserving. Structured VS Code setting merge may add only absent
  generated-path exclusions; conflicting keys, MCP configuration, AGENTS,
  instructions, skills, hooks, plans, and other user-owned content are never
  overwritten automatically.
- [ ] Criterion 13: Every conflicting file is emitted as a reviewable proposal
  containing the intended rendered content and enough metadata/diff information
  to merge manually. The original target file remains byte-for-byte unchanged.
- [ ] Criterion 14: Explicit apply writes a manifest/receipt and backups outside
  user-owned source files sufficient to explain what was created or safely
  merged. A rollback operation removes only files proven to have been created
  by that apply and restores safely merged files from verified backups. It
  refuses ambiguous, missing, tampered, or unsafe rollback state.
- [ ] Criterion 15: Analyze, preview, safe apply, and rollback defend against
  symlink/path-escape and non-regular-file hazards, report partial failures
  clearly, and avoid leaving half-applied state. Apply is transactional where
  practical and rolls back its own writes on failure.
- [ ] Criterion 16: Re-running analysis/apply is idempotent where practical:
  identical files are recognized, safe settings are not duplicated, already
  added files are not rewritten, and repeated preview does not mutate the
  project.
- [ ] Criterion 17: New-project mode still creates a complete usable
  installation, while detected project facts can recommend rather than
  silently force profiles/defaults. Conflicting Conda/uv markers and uncertain
  commands are surfaced for user decision.
- [ ] Criterion 18: MemPalace guidance is updated to prefer targeted
  project-scoped retrieval, atomic `mempalace_checkpoint`, and `kg_supersede`
  when supported, while keeping live files authoritative and documenting
  degraded behavior. codebase-memory guidance matches the actually available
  tool surface, treats optional coverage/status tools as capability-detected,
  and does not require nonexistent operations.
- [ ] Criterion 19: Protocol enforcement uses supported Copilot lifecycle hooks
  only where they can provide a real check. Strong/governed rigor may install a
  reviewed fast local guard for enforceable handoff/plan/change-isolation
  invariants, but external memory success must not be falsely claimed. Hook
  event-name/surface limitations and fail-open timeout behavior are documented.
- [ ] Criterion 20: Documentation covers architecture, CLI compatibility, GUI
  launch, configuration fields/presets, new-project examples, existing-project
  analyze/preview/apply/rollback flow, conflict policy, safety model, and
  headless UI validation. Examples use temporary/sample paths and no secrets.
- [ ] Criterion 21: Tests are focused and proportional rather than a second
  oversized test framework. They cover configuration validation/round-trip,
  preset-to-policy behavior, CLI backward compatibility, headless GUI/controller
  behavior, new-project install, existing-project no-mutation analysis,
  proposals, safe apply, idempotency, rollback, path/symlink hazards, malformed
  config/receipts, and injected mid-apply failure recovery.
- [ ] Criterion 22: The existing full test suite passes:
  `python -m unittest discover -s workflow_configurator/tests -v`. The implementation
  also exercises the GUI smoke path and both new/existing project workflows with
  observed output. No test may rely on real network services, credentials,
  production data, or a graphical display.
- [ ] Criterion 23: No unnecessary runtime dependency, service, alternate agent
  runtime, spec framework, memory backend, or MCP server is added. Prefer the
  Python standard library and existing project patterns. The implementation is
  split only where separation of core/CLI/GUI concerns materially improves
  understanding and maintenance.
- [ ] Criterion 24: The two existing untracked research documents under
  `docs/research/` are preserved and included in the resulting work. No
  unrelated user content is reverted or deleted.

## Scope Boundaries

**In scope:**

- `workflow_configurator` installer architecture, configuration model, CLI, Tkinter GUI,
  generated templates/guidance, optional protocol guards, diagnostics, and
  focused tests.
- Safe brownfield analysis, preview/proposal export, explicit safe apply,
  receipt/backup, and rollback.
- Documentation and examples directly supporting these capabilities.
- Corrections derived from the 2026-08-30 workflow and lean-code research.

**Out of scope:**

- Automatically rewriting or semantically merging conflicting user-owned
  AGENTS, instruction, skill, hook, MCP, plan, handoff, or source files.
- Installing Ponytail, Spec Kit, OpenSpec, BMAD, rtk, Serena, jscpd, Semgrep,
  Vulture, Knip, or another external tool.
- Replacing Copilot, MemPalace, codebase-memory, the current CLI, or existing
  project package/environment managers.
- Remote services, telemetry collection, a web UI, database-backed state, or
  a long-running daemon.
- Universal LOC/file/test thresholds that trade away clarity or required
  behavior.
- Broad refactors of experiment tooling unrelated to configurator integration.

## Applicable Project Conventions

**Quality gate command:**

- `python -m unittest discover -s workflow_configurator/tests -v`
- Existing generated-project diagnostics use
  `python .github/skills/project-doctor/scripts/doctor.py --root . --strict`.
- Placeholder validation in an installed project uses
  `rg -n '\{\{[A-Z0-9_]+\}\}' AGENTS.md .github docs`.

**Commit convention:**

- Conventional commits.
- Builder title: `type(scope): [B] description` (maximum 72 characters).
- Inspector title: `chore(scope): [I] description` (maximum 72 characters).
- Builder trailer required: `Assisted-by: OpenAI:GPT-5.6 Luna`.
- Inspector trailer required: `Assisted-by: OpenAI:GPT-5.6 Sol`.
- Both commits also include
  `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

**Guidelines:**

- `workflow_configurator/AGENTS.md`
- `templates/AGENTS.md`
- `workflow_configurator/.github/copilot-instructions.md`
- `workflow_configurator/docs/ENVIRONMENT_POLICY.md`
- `workflow_configurator/docs/MCP_SECURITY.md`
- `workflow_configurator/docs/AGENT_SURFACES.md`
- `docs/research/agent-workflow-assessment-2026-08-30.md`
- `docs/research/lean-agent-code-assessment-2026-08-30.md`

**Rules:**

- Make the smallest maintainable change that fully satisfies required behavior.
- Existing project declarations and conventions win; do not invent commands or
  package managers.
- Keep CLI behavior backward compatible and preserve current safe defaults.
- Never overwrite user-owned files silently or follow symlinked destinations.
- Use specific errors and transactional cleanup; do not hide partial failure.
- Keep executable configuration reviewable and local.
- Use focused tests while implementing, then run the complete existing suite
  before declaring completion.
- Preserve all pre-existing and untracked user work.
