# GPT Agent Workflow Template

This is Himanshu's local-first GitHub Copilot workflow configurator for VS Code
1.129 or newer. It derives minimal, standard, or governed project guidance from
actual size, complexity, testing, rigor, and selected capabilities instead of
imposing one workflow everywhere.

Requirements: Python 3.10 or newer for the CLI/core. The optional native UI
uses PySide6. MemPalace and codebase-memory remain first-class optional
capabilities: project operations use explicit identities and are invoked
on-demand or required only by the resolved policy.

The installer:

- legacy installs preflight every destination and abort before writing on any
  collision; configurator mode classifies conflicts as reviewable proposals;
- replaces required project facts instead of leaving executable placeholders;
- defaults to a three-file minimal surface and adds profiles/capabilities only
  when selected;
- derives the project name from the target and supplies personal command
  defaults while allowing explicit overrides;
- keeps project-local MCP servers opt-in and sandboxes local servers;
- never auto-installs external tools or deletes legacy workflow files.

## Install

The normal personal install is deliberately short. Run a dry run first:

```bash
python workflow_configurator/install.py ~/projects/my-project --dry-run
```

Run it without `--dry-run` after reviewing the file list. Defaults are project
name from the target directory, `pytest -x -q`, `ruff check .`, `pyright`, no
local run command, and the minimal three-file workflow surface.

Override project-specific facts when needed:

```bash
python workflow_configurator/install.py ~/projects/my-project \
  --project-name "Forecast Service" \
  --summary "Forecasting service for internal planning." \
  --run-command "uvicorn app.main:app --reload" \
  --profile fastapi
```

Use `none` explicitly to disable a command. Add stack profiles deliberately.
Context exclusions are generated only for standard/governed surfaces. Use
`--without-artifact-gitignore` when an existing ignore policy is managed
elsewhere.

The legacy installer never overwrites workflow/configuration files. Its one
intentional merge is `.gitignore`: when the DS profile is active and no
equivalent rule exists, it preserves existing content and appends a labeled
`artifacts/` rule. Configurator mode adds missing files and performs the same
documented safe merges only after explicit `--apply`.
If the destination already has an `AGENTS.md`, `.github/`, `.vscode/mcp.json`,
or workflow document, merge the corresponding template manually instead of
deleting project-specific guidance.

Optional hardening:

```bash
python workflow_configurator/install.py ... \
  --with-security-hooks
```

`--with-security-hooks` selects the governed surface and installs executable
repository hook code; inspect it before trusting the workspace. No option
overwrites an existing destination file.

## Profiles

| Profile | Files installed |
|---|---|
| `python` | Python implementation and test rules |
| `data-science` | Leakage and reproducibility rules |
| `fastapi` | API boundary, async, validation, and endpoint test rules |
| `react` | React and TypeScript state, API, accessibility, and test rules |

No stack profile is installed by default. Use `--profile python`,
`--profile data-science`, `--profile fastapi`, or `--profile react` only when
the project needs it. The experiment runner is a separate optional integration.

## Conda And uv

The project manager is selected deterministically, never per command:

- Existing `environment.yml`/`conda-lock.yml`: continue with Conda.
- Existing `uv.lock` or uv-configured `pyproject.toml`: continue with uv.
- Both marker families: stop and resolve ownership; never mix them.
- New ML/data project: default to Miniforge/Conda and commit `environment.yml`.
- New pure-Python tool or CLI: uv is supported with committed `uv.lock`.

The default pytest, Ruff, and Pyright commands are environment-agnostic: run
them after `conda activate`, through `conda run`, or through `uv run` according
to the selected manager. See `docs/ENVIRONMENT_POLICY.md` in an installed
project.

`uv tool` and `uvx` used for MCP servers are tool plumbing, not project
dependency managers. They do not create, update, or enter the project's
environment.

## Optional MCP Servers

Personal default: register folder-independent services such as MemPalace,
codebase-memory-mcp, and Context7 once in the active VS Code user profile. Keep
DuckDB, MarkItDown, Postgres, and any server using workspace-relative paths or
permissions in workspace scope. A user-profile MCP file is also evaluated when
no folder is open, so it must not contain `${workspaceFolder}`. Enable only the
servers needed for a workspace or chat.

Open the user-profile file through **MCP: Open User Configuration**.

| Name | Default posture |
|---|---|
| `duckdb` | Ephemeral in-memory, read-write as required by DuckDB, sandboxed; state disappears when the server stops |
| `postgres` | Restricted SQL mode, sandboxed, credential from a secure input prompt |
| `markitdown` | Local, sandboxed to workspace files |
| `context7` | Remote documentation search, no key by default |
| `huggingface` | Remote public search; configure enabled tools in Hugging Face settings |

Use `--mcp` more than once when needed:

```bash
python workflow_configurator/install.py ~/projects/my-project \
  --mcp duckdb \
  --mcp context7
```

No MCP configuration is created when no server is selected. Do not register the
same server in both user and workspace scope. Review generated
`.vscode/mcp.json`, trust only known publishers, and enable only the tools needed
for the current session.

The local sandbox permits workspace reads, blocks workspace writes, and limits
network access to localhost plus PyPI hosts needed by `uvx` for pinned package
bootstrap. If Postgres is remote, add its exact hostname to the sandbox
allowlist. Do not disable the sandbox as a shortcut.
On Linux, sandbox startup requires `bwrap`, `socat`, and `rg` on VS Code's
inherited PATH.

Ubuntu 24.04 and newer commonly enable
`kernel.apparmor_restrict_unprivileged_userns=1`. That host policy can let
Bubblewrap start while denying `CAP_SYS_ADMIN` to VS Code's nested
`apply-seccomp` helper. If startup fails with `write /proc/self/setgroups`, do
not disable the AppArmor restriction globally as a casual fix. For reviewed
local servers, regenerate the project configuration with
`--without-mcp-sandbox`; VS Code then retains normal per-tool confirmations.
The stronger alternative is a reviewed host AppArmor policy that grants the
required user namespace capability only to the relevant sandbox path.

Local package pins were checked on 2026-08-01: MotherDuck MCP `1.0.7`, Postgres
MCP `0.3.0`, and MarkItDown MCP `0.0.1a4`. MarkItDown's MCP package is still a
prerelease, so revalidate its behavior before widening filesystem or network
access. Review and deliberately update these pins rather than switching to
`latest`.

## Workflow

- Tier 0 questions/research/docs/trivial configuration need no plan and no code
  tests.
- Tier 1 bounded edits use an inline/mini plan and the smallest affected check.
- Tier 2 coupled or multi-session changes use a compact plan/handoff.
- Tier 3 security/migration/regulated/cross-service work uses the governed path.

Use MemPalace and codebase-memory only according to the generated project
policy. Project memory operations always name the configured wing. Broad tests
run once at a logical checkpoint or governed risk gate, not after every edit.

## Validate After Installation

For standard/governed installs, open **Chat: Open Customizations** and confirm
that selected agents, skills, and instructions load without diagnostics. Then
check:

```bash
rg -n '\{\{[A-Z0-9_]+\}\}' AGENTS.md .github docs
```

The command should return no matches. Run each configured project command once
before relying on the executor workflow.

Read only the protocol documents actually installed by the selected surface.

## Adaptive workflow configurator

The installer provides a standard-library-first core split into typed config,
policy, catalog, analysis, Apply, recovery, upstream metadata, and local plugin
export responsibilities. `install.py` and optional PySide6 `gui.py` are
adapters; core/CLI use does not require Qt.

Configuration schema v2 includes complexity, scope, testing, stack profiles,
MCPs, optional capabilities, commands, rigor, canonical memory/code identities,
session profile, and typed expert overrides. It derives minimal, standard, or
governed installation plus concrete plan, validation, documentation, memory,
code-intelligence, review, and guard policy.
The generated `docs/WORKFLOW_CONFIG.md` makes those values visible and includes
the maintenance-first lean-change contract: search/reuse first, explicit
non-goals, no speculative abstractions/configuration/dependencies, a minimal
public/file surface, and protection of required correctness and operational
boundaries. It never installs Ponytail or imposes a universal LOC limit.

Analyze and preview are strictly read-only for an existing target:

```bash
python workflow_configurator/install.py ../existing-project --workflow existing --analyze --json
python workflow_configurator/install.py ../existing-project --workflow existing --preview --output review.json
```

Reports detect manifests/languages, environment and Git/customization state,
workflow/test/docs LOC and ratios, plan/handoff budgets, legacy surface,
large files/Python functions, memory topology, graph state, symlinks,
non-regular files, and redacted MCP configuration findings. Actions are
`missing`, `identical`, `safe_merge`,
`conflicting_proposal`, or `unsafe`; conflict proposals include rendered
content and a unified diff. `scan_complete` and structured traversal/read
diagnostics expose permission, unreadable-file, and bounded-scan failures
instead of hiding them. The selected policy is a recommendation for new
projects, not a silent override of existing declarations.

In configurator mode, only explicit `--apply` mutates an existing target. It adds missing files, appends the
labeled `artifacts/` rule to `.gitignore` while preserving mode, and adds only
absent artifact/search exclusions to structured VS Code settings. It never
automatically overwrites AGENTS, instructions, skills, hooks, plans, MCP, or
other user-owned content. Passive manifests live under
`.workflow_configurator/manifests/` and safe-merge backups under
`.workflow_configurator/backups/`; required empty directories such as `docs/plans` are
recorded in the manifest. A manifest records target identity, normalized
configuration, added files, proposals, safe merges, backup paths, hashes, modes,
and required directories for explanation only. Apply cleans up its own writes
and restores safe merges if that running apply fails, even when a completed
write reports an error; no later command deletes, overwrites, or restores a
project path automatically. The default restore plan aggregates still-material
manifests for the canonical target so no-op or proposal-only reapply cannot hide
earlier paths and backup mappings. Explicit manifest selection remains
invocation-specific. For a repeated destination, the active mapping is the
newest material entry whose recorded after hash/mode matches the current path;
older entries remain clearly labeled history. Missing or manually changed
destinations are marked for review. Use the manual plan to review added paths
and copy a reviewed backup to its documented destination.

```bash
python workflow_configurator/install.py ../existing-project --workflow existing --apply
python workflow_configurator/install.py ../existing-project --restore-instructions
```

Use `--import-config`/`--export-config` for versioned JSON without changing the
target. The optional PySide6 GUI exposes the complete workflow without
requiring CLI flags. Install its isolated optional dependency in whichever
interpreter you selected for the configurator:

```bash
python -m pip install -r workflow_configurator/requirements-gui.txt
python workflow_configurator/install.py --gui ../existing-project
python workflow_configurator/gui.py --headless-smoke
```

It opens as a compact, high-DPI-aware Qt window with **Project**, **Workflow**,
**Memory & Code**, **Tools & Profiles**, **Review & Apply**, **Updates &
Plugins**, **Recovery**, and **Guide** pages. It uses native controls/dialogs, a
searchable capability tree, typed Advanced Overrides, a structured action/diff
view with wrapped panes, explicit proposal acknowledgement/manual-merge actions,
exact Apply blockers, contextual help, and an About dialog. A visible **Close**
button and `Ctrl+Q` close the application.

On Linux, run `./launch-workflow-configurator.sh` directly or run
`./install-workflow-configurator-launcher.sh` once to add **Workflow
Configurator** to the desktop application menu.

On Windows, double-click `launch-workflow-configurator.cmd`, or run
`install-workflow-configurator-launcher.cmd` to add a current-user Start Menu
shortcut. The PowerShell installer accepts `-DesktopShortcut` for an optional
current-user Desktop link and `-Uninstall` to remove its shortcut and saved
interpreter. It writes only under `%LOCALAPPDATA%` and `%APPDATA%`; it does not
request elevation, edit the registry or PATH, install services/tasks, or write
to Program Files.

Both platforms prefer an explicit `WORKFLOW_CONFIGURATOR_PYTHON`, the active
environment, repository `.venv` or `.conda`, an explicit legacy
`WORKFLOW_CONFIGURATOR_ENV`, the interpreter saved by the user-level installer,
and finally an available system Python. No environment name is hardcoded.

Advanced Overrides expose only typed process controls. Weakening requires a
stored reason and confirmation. Path, secret, destructive-operation, sandbox,
preview, collision, transactional, overwrite, deletion, and rollback safety
cannot be overridden.

Tools & Profiles distinguishes project-local MCP configuration, bundled local
optional templates, and guidance-only external capabilities. Session profiles
generate truthful enable/disable guidance without claiming to modify a running
agent session. Nothing external is auto-installed.

Updates & Plugins performs a metadata-only Awesome Copilot check at most once
per 24 hours. It compares public commit/tree metadata with the locally reviewed
baseline and stores a corruption-detection checksum under the user cache
directory. A user may explicitly fetch one selected, size-capped text asset to
view a read-only diff, record a rationale-backed disposition, and advance the
local baseline after every item has a decision. It sends no project data and
never installs or applies upstream content. Network failure preserves the last
report. Use `gui.py --no-update-check` for an explicitly offline launch.

Analyze and Preview include a deterministic **Context footprint** comparison
between the current project and the result of safe Apply. It reports lines and
UTF-8 bytes for always-on, path-specific, and on-demand context; handoff/plan
size; configured MCP servers; searchable historical material; and exact
duplicate instruction blocks. It is a context proxy, not an exact token or cost
forecast.

Memory & Code health derives a policy-aware continuity status:
`READY`, `LIMITED`, `DEGRADED`, or `DISABLED`. Raw service diagnostics remain
available below the summary.

The same page can preview and export a local Copilot plugin containing only the
five reviewed generic specialists. The preview lists every file and SHA-256
digest; export refuses an existing destination and does not install, enable,
publish, or update the plugin. Project policy, memory/code identities, commands,
task state, guards, and recovery evidence remain repository-local.

Apply stays disabled until the current target and settings have a successful
matching preview; changing the form invalidates that preview. **Export report**
writes the JSON preview only to an explicit user-selected path. `--dry-run`
always wins over configurator `--apply` and never writes a target or export
file.

See `docs/CONFIGURATOR.md` for the full conflict policy, passive manifest and
backup format, presets, examples, and headless validation guidance.
