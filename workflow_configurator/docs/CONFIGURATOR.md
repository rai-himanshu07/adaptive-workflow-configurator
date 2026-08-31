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
testing, profiles, MCPs, optional capabilities, commands, rigor, canonical
MemPalace/codebase-memory identities, session profile, and typed overrides.

Config v1 imports conservatively. Normal fields migrate; ambiguous free-form
policy or unsafe approval weakening is rejected for manual review.

### Adaptive policy

The core derives:

- installation surface: minimal / standard / governed;
- plan tier: none / mini / compact / governed;
- validation: none / focused / broad;
- documentation: changed-only / handoff / full;
- memory and code intelligence: off / on-demand / required;
- review: self / independent;
- protocol guard: off / on.

Default minimal output is only:

```text
AGENTS.md
.github/copilot-instructions.md
docs/WORKFLOW_CONFIG.md
```

Standard adds compact agents, task state, context exclusions, and a
surface-aware doctor. Governed adds selected specification, guard, and evidence
surfaces. The data-science experiment runner is a separate optional capability.

### Advanced Overrides

The native editor shows each derived value, selected value, and whether it is
stronger, equal, or weaker. Weaker values require a reason and Apply
confirmation.

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

## Task and Testing Tiers

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
