# Workflow Configurator

`workflow_configurator` is a local-first adaptive workflow configurator with:

- a standard-library core;
- a CLI in `install.py`;
- an optional native PySide6 desktop UI;
- read-only brownfield analysis;
- redacted MCP configuration auditing;
- metadata-only upstream delta checks;
- no-overwrite local specialist-plugin export;
- preview-gated additive Apply;
- passive manifests and manual-only recovery.

No external tool, skill, MCP, memory service, persona, or dependency is
installed automatically.

## Configuration v2

Versioned JSON stores project identity, new/existing mode, complexity, size,
testing, profiles, free-text technologies, MCPs, optional capabilities, commands,
rigor, execution mode, optional initial task, canonical MemPalace/codebase-memory
identities, session profile, and typed overrides.

New v2 configurations leave test, lint, typecheck, and run commands unconfigured.
Choose multiple reviewed stack profiles when useful, and describe technologies
without a bundled profile (such as Rust) in the free-text technology stack.
Commands may combine tools from several languages. Legacy installs and v1
config imports retain their Python command defaults.

New projects default to `velocity`, which uses compact instructions
and bounded project-memory/code-graph lookups, but plans, tests, lint, typechecks,
project doctor, reviews, and optional hooks run only on explicit request. Hard
path, secret, sandbox, preview, collision, and transaction protections remain.
Explicit policy overrides may require checks or review again; selecting hooks
installs them to run at their configured events.
Choose `balanced` for the adaptive task-tier process with its automatic checks
and review. Imported v1 or older v2 configurations without an execution-mode
field retain Balanced rather than silently weakening their existing policy;
the legacy installer also remains Balanced.

An optional initial task is stored in `docs/CURRENT_TASK.md` only after Preview
and explicit Apply. A new chat request or explicitly named file takes precedence;
without a task, the agent asks instead of guessing. Existing task files become
reviewable proposals, never automatic overwrites. Task text also appears in
config exports, preview data, and Apply manifests; do not put secrets in it.

Config v1 imports conservatively. Normal fields migrate; ambiguous free-form
policy or unsafe approval weakening is rejected for manual review.

### Adaptive policy

The core derives:

- installation surface: minimal / standard / governed;
- plan tier: none / mini / compact / governed;
- validation: manual / none / focused / broad;
- documentation: changed-only / handoff / full;
- memory and code intelligence: off / on-demand / required;
- review: manual / self / independent;
- protocol guard: off / on.

Default minimal output is only:

```text
AGENTS.md
.github/copilot-instructions.md
docs/WORKFLOW_CONFIG.md
```

Standard adds compact agents, task state, context exclusions, and a
surface-aware doctor. Governed adds selected specification, guard, and evidence
surfaces. Velocity keeps required memory and graph usage without promoting the
file bundle by itself. The data-science experiment runner is a separate optional
capability.

### Advanced Overrides

The native editor shows each derived value, selected value, and whether it is
stronger, equal, or weaker. Weaker values require a reason and Apply
confirmation.

`auto` removes the explicit override and uses the value derived from execution
mode, complexity, project size, testing level, rigor, selected integrations,
and security hooks.
Options below are ordered from lighter to stronger. Stronger plan,
documentation, memory, code-intelligence, review, or guard choices can promote
the effective generated file set even when the installation-surface override is
lighter.

#### Installation surface

Controls the generated workflow-file bundle. This is a floor, not an absolute
cap: stronger choices in other dimensions can promote it.

| Option | Behavior |
|---|---|
| `minimal` | Install only compact always-on instructions and the generated workflow configuration; stronger plan, documentation, memory, code-intelligence, review, or guard choices can still promote the effective file set (required memory and graph stay compact in velocity mode). |
| `standard` | Add planner/executor/reviewer roles, compact handoff and resume skills, the project doctor, and context exclusions when enabled. |
| `governed` | Add the Standard surface plus governed planning, memory, code-intelligence, environment, observability, MCP, and safety guidance. |

#### Plan tier

Controls whether work needs no plan, a small inline plan, a compact persisted
plan, or a governed specification.

| Option | Behavior |
|---|---|
| `none` | No plan artifact by default; start bounded implementation or ask when the task is unclear. |
| `mini` | Inline or mini plan, at most 25 lines, for bounded low-risk edits. |
| `compact` | Compact approved plan, at most 80 lines, for coupled or multi-session changes; ensures at least the Standard surface and a `docs/plans` directory. |
| `governed` | Governed specification and risk record before implementation; promotes the Governed surface, while Spec Kit can own the plan artifacts. |

#### Validation tier

Controls expected verification scope. It neither installs a test runner nor
weakens permanent safety checks.

| Option | Behavior |
|---|---|
| `manual` | Run tests, lint, typecheck, and project doctor only when the user requests them. |
| `none` | No code tests for research/docs; use only the smallest applicable diagnostic. |
| `focused` | Run the smallest affected check after a coherent implementation slice. |
| `broad` | Run focused checks plus broad relevant tests or diagnostics at a logical checkpoint. |

#### Documentation tier

Controls ongoing documentation and handoff obligations. It never permits
skipping user-facing or operational documentation directly affected by a task.

| Option | Behavior |
|---|---|
| `changed-only` | Update only user-facing or operational documentation changed by the task. |
| `handoff` | Keep a concise current-state handoff for work that spans sessions; ensures at least the Standard surface. |
| `full` | Maintain governed handoff, recovery, and operator evidence without copied command output; promotes the Governed surface. |

#### Memory policy

Controls MemPalace invocation. The canonical project wing remains configured
even when memory use is off.

| Option | Behavior |
|---|---|
| `off` | Do not call project memory when history is explicitly irrelevant. |
| `on-demand` | Use the canonical project wing only when prior decisions or session history matter. |
| `required` | Use project-scoped retrieval and an explicit-wing checkpoint for substantial work; promotes the Governed surface except in velocity mode. |

#### Code-intelligence policy

Controls codebase-memory usage. The configured project identity remains
available and live files remain authoritative.

| Option | Behavior |
|---|---|
| `off` | Use live files and language/text search for the bounded task. |
| `on-demand` | Use available graph tools when architecture, callers, impact, or reuse discovery matters. |
| `required` | Verify the available graph surface and use it for architecture and impact before editing; promotes the Governed surface except in velocity mode. |

#### Review tier

Controls when review is expected. It never authorizes overwriting a
conflicting project file.

| Option | Behavior |
|---|---|
| `manual` | Run self-review or an independent reviewer only when the user requests it. |
| `self` | Self-review the final diff and relevant evidence; do not manufacture findings. |
| `independent` | Independent read-only review is required before completion or release; promotes the Governed surface. |

#### Protocol guard

Controls the optional local workflow hook. It never replaces human review or
the configurator's permanent safety boundaries.

| Option | Behavior |
|---|---|
| `off` | Do not install the optional workflow guard; hard path, secret, preview, collision, and transactional safeguards remain active. |
| `on` | Install the reviewed local guard that checks handoff, plan, and change-isolation facts; promotes the Governed surface but cannot prove external memory, review, or test success. |

Hard safety is not represented as an override:

- path/symlink boundaries;
- secret handling;
- destructive-operation approval;
- MCP sandbox safeguards;
- preview freshness;
- user-file collision policy;
- transactional cleanup;
- overwrite, deletion, and rollback.

CLI:

```bash
python workflow_configurator/install.py TARGET \
  --workflow existing \
  --override validation_tier=focused \
  --override-reason validation_tier='Existing targeted CI covers the change' \
  --preview
```

The old `--policy-override` is deprecated and accepted only where v1 migration
is unambiguous.

## Balanced Mode: Task and Testing Tiers

These automatic task tiers apply to Balanced mode. In default Velocity, plans,
checks, doctor, and review are user-invoked unless a stronger explicit policy
override requires them.

| Tier | Work | Plan | Validation |
|---|---|---|---|
| 0 | question, research, docs, trivial config | none | none or smallest diagnostic |
| 1 | bounded low-risk edit | inline/mini, up to 25 lines | smallest affected check |
| 2 | coupled or multi-session behavior | compact, up to 80 lines | focused per coherent slice; broad at checkpoint |
| 3 | security, migration, regulated, cross-service/team | governed/Spec Kit | broad relevant evidence |

Tests are added for changed behavior, reproduced bugs, or named risks—not
merely because a file was touched. Broad suites run at logical checkpoints or
governed risk boundaries.

## New and Existing Projects

Read-only analysis/preview:

```bash
python workflow_configurator/install.py ../project --workflow existing --analyze --json
python workflow_configurator/install.py ../project --workflow existing --preview
```

Explicit Apply:

```bash
python workflow_configurator/install.py ../project --workflow existing --apply
```

Analyze reports project declarations plus production/test/workflow/docs LOC,
ratios, customization counts, plan/handoff budgets, legacy generated surface,
large files/Python functions, memory topology, code-graph state, and redacted
MCP configuration findings.

It also reports a deterministic context-footprint proxy for current and
safe-post-Apply state:

- always-on instruction lines and UTF-8 bytes;
- path-specific and on-demand workflow context;
- handoff and active-plan size;
- configured MCP server count;
- searchable historical material;
- exact repeated instruction blocks across context files.

The report does not estimate exact model tokens, cache behavior, runtime tool
schemas, or retrieved-memory volume. Measure those separately through trusted
local telemetry when needed.

Existing user-owned files are never overwritten. Conflicts remain proposals
with intended content and diffs. Old generated files outside the selected
surface are reported for manual cleanup and never deleted.

In **Review & Apply**, select a row to inspect its wrapped diff. A conflicting
proposal can be copied, opened for manual merging, or acknowledged as reviewed
while explicitly keeping the existing file. Acknowledgement never authorizes an
overwrite and does not block unrelated safe additions. If Apply is disabled, the
page names the exact scan, error, or unsafe-path blocker instead of presenting a
generic message. Unified diffs use palette-aware green additions, red removals,
blue hunk headers, and neutral file headers; `+`, `-`, `@@`, `+++`, and `---`
markers remain visible so meaning does not depend on color.

Project-local dependency and tool caches such as `.conda`, `.venv`,
`node_modules`, `.tox`, and Python analysis caches are excluded from bounded
inspection. They cannot consume the traversal budget or create false incomplete
scan failures.

Repository discovery is separate from Apply safety. Git repositories use
tracked plus non-ignored files; non-Git projects use the bounded fallback walk.
Both retain only manifests, source/text metrics, workflow customizations, and
non-regular entries. Discovery uses 25,000/100,000/250,000 entry budgets for
small/medium/large projects and may report partial metrics, but it does not block
Apply. Every intended destination is validated directly for containment,
symlinks, type, collision state, Preview freshness, and safe transactional
writing.

## Memory and Code Intelligence

Each project has:

- one canonical MemPalace `memory_wing`;
- one `codebase_project_id`.

Generated project reads/writes always name the wing. `wing_copilot` is reserved
for cross-project lessons. Mining refreshes source retrieval; checkpoints record
decisions and session synthesis.

Health checks are read-only and bounded. They display MemPalace version,
backend/wing aliases, writable/blocked state, hub status, and code graph
root/HEAD/nodes/edges/change state where available.

The GUI interprets those facts according to the resolved policy:

- `READY`: configured services are ready;
- `LIMITED`: an on-demand service is unavailable when requested;
- `DEGRADED`: a service required by policy is not ready;
- `DISABLED`: continuity services were deliberately disabled.

This status affects continuity expectations, not safe file-configuration
availability. Raw technical health remains visible below the summary.

MemPalace 3.6 writable MCP sessions can block manual mining. A reviewed 3.8
shared writable hub is recommended for multi-session/manual-mine use. The
Configurator diagnoses but never upgrades, stops, unlocks, or migrates it.

Generated agent guidance names optional codebase-memory status/change tools
only when the active agent surface exposes them.

Graph effort follows the claim:

- Scout for positive orientation;
- Verify for normal task-directed claims;
- Auditor for bounded negative, exhaustive, security, dead-code, or
  complete-impact claims.

Known-file, exact-literal, and trivial non-code work can skip the graph.

## Tools, Profiles, and Specialists

Project MCP configuration is available for DuckDB, Postgres, MarkItDown,
Context7, and Hugging Face.

Optional capabilities include rtk, Serena, affected-test selection, jscpd,
OpenSpec or Spec Kit, metadata-only OpenTelemetry, Vulture, Knip,
project-specific Semgrep, the experiment runner, and Archify milestone
diagrams.

Compact local specialist lenses—accessibility, tool/dependency, AppSec,
research, and lean-code review—are independently selectable and off by default.
The Agency Agents roster is not installed.

Session profiles provide enable/disable guidance for quick/docs,
resume/history, large-code, symbol refactor, data analysis, document ingestion,
ML/model selection, and PR/issues. They never claim to change an already-running
agent session.

## Native Desktop UI

Install and launch with the Python executable selected for this checkout:

```bash
python -m pip install -r workflow_configurator/requirements-gui.txt
python workflow_configurator/install.py --gui ../project
```

The desktop launcher resolves a concrete interpreter rather than assuming an
environment manager or name. Selection order is explicit
`WORKFLOW_CONFIGURATOR_PYTHON`, active virtual/Conda environment, repository
`.venv` or `.conda`, explicit legacy `WORKFLOW_CONFIGURATOR_ENV`, the interpreter
saved when the user-level launcher was installed, then system Python. Re-run the
installer after intentionally changing its saved interpreter.

Linux:

```bash
./install-workflow-configurator-launcher.sh
```

Windows:

```powershell
.\install-workflow-configurator-launcher.ps1
.\install-workflow-configurator-launcher.ps1 -DesktopShortcut
.\install-workflow-configurator-launcher.ps1 -Uninstall
```

The Windows installer creates only a current-user Start Menu shortcut through
`WScript.Shell`, stores the selected interpreter under
`%LOCALAPPDATA%\workflow-configurator`, and optionally creates a current-user Desktop
shortcut. It never requests UAC/elevation, modifies machine or user registry
keys, changes PATH, installs a service or scheduled task, or writes to Program
Files. The `.cmd` wrappers provide double-click entry points without changing
PowerShell execution policy.

Pages:

1. Project
2. Workflow
3. Memory & Code
4. Tools & Profiles
5. Review & Apply
6. Updates & Plugins
7. Recovery
8. Guide

The searchable capability tree, typed override dialog, standard controls, native
file dialogs, action/diff review, complete in-app Guide, and About dialog avoid
requiring CLI knowledge.

Apply stays disabled until a successful preview matches the current target and
configuration.

## Updates and Local Plugin Export

On launch, the GUI checks public Awesome Copilot metadata when the last
successful check is older than 24 hours. Three bounded API responses provide the
current commit, current catalog tree, and locally reviewed tree. The tool stores
only source revision, paths, blob identifiers, categories, counts, timestamps,
and a corruption-detection checksum in the user cache.

Automatic checks remain metadata-only. Review is an explicit state machine:

```text
unseen -> inspected -> disposition recorded -> baseline eligible
```

- **Inspect selected** fetches only that asset's old/current Git blobs.
- Each decoded UTF-8 body is capped at 256 KB and displayed read-only as
  untrusted content.
- Decisions are `adopt`, `optional-pilot`, `patterns-only`, `watch`, or `reject`
  and require a rationale.
- The local state ledger lives under `XDG_STATE_HOME` (or
  `~/.local/state/workflow-configurator/`).
- **Advance reviewed baseline** is enabled only when every outstanding item has
  a decision and always requires confirmation.
- Advancing changes local review state only; it does not alter built-in
  capabilities.

The queue remains deliberately non-executable:

- no external agent, skill, hook, plugin, or dependency is installed;
- no project data is sent;
- no built-in recommendation changes automatically;
- a network or schema failure preserves the previous cache;
- a Markdown review brief contains the delta and prior decision boundaries.

This avoids repeating the entire catalog audit while preserving explicit human
promotion.

The plugin pilot has a separate preview and confirmation from project Apply. It
exports five existing specialist files, `plugin.json`, `README.md`, and a
SHA-256 manifest into a new directory. It refuses overwrite and never runs
`copilot plugin install`; the user reviews and tests that command separately.

## Passive Recovery

Apply writes informational manifests under `.workflow_configurator/manifests/` and exact
safe-merge backups under `.workflow_configurator/backups/`. They never authorize a later
write.

```bash
python workflow_configurator/install.py ../project --restore-instructions
```

Recovery lists generated paths and backup-to-destination mappings for manual
review. No project file or directory is restored or removed automatically.

## Validation

Run validation with the selected interpreter. It may be an activated `.venv`, a
repository `.conda`, a named Conda environment, or another compatible Python:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s workflow_configurator/tests
python workflow_configurator/gui.py --headless-smoke
```

Use isolated cache/state paths for release validation. When a display is
available, also inspect the resizable high-DPI window once at the release
checkpoint.

## Documentation authority

- `README.md` is the quick start and feature inventory.
- This file defines the configurator's behavioral contract.
- `AI_WORKFLOW_GUIDE_2026.md` defines general developer workflow principles.
- `docs/research/` is supporting evidence and is not a second policy source.
