# Final Workflow Configurator Change Plan

**Created:** 2026-08-30
**Status:** implemented and verified
**Baseline:** `f186715`
**Task tier:** 3 — governed redesign
**User decision:** constrained expert overrides; hard safety is never overridable

## Goal

Deliver a local-first PySide6 configurator that installs only the workflow
surface a project earns, varies effort by task/risk, integrates safely into
existing projects, uses MemPalace/codebase-memory deliberately, keeps niche
capabilities optional, and explains itself fully in the UI.

Evidence is in the seven assessments under [`docs/research/`](../research/),
especially the [real-project audit](../research/real-project-workflow-audit-2026-08-30.md),
[memory audit](../research/memory-routing-persistence-assessment-2026-08-30.md),
and [lock assessment](../research/mempalace-lock-contention-assessment-2026-08-30.md).

## Confirmed Problems

- Every install begins with 20 workflow files; the doctor is 966 lines.
- New projects default to about 960 lines of data-science experiment tooling.
- Generated agents prescribe plans, memory, code graphs, and tests too broadly.
- Config v1 accepts arbitrary policy prose and safety weakening.
- The GUI exposes one undocumented `NAME=VALUE` override that cannot display or
  reset imported overrides.
- Project memory wing, code graph identity/freshness, and MemPalace writer
  topology are absent.
- Analyze does not measure workflow/test/documentation overhead.
- Help is a five-line message; there is no About UI.

## Locked Decisions

1. Keep native PySide6; core/CLI must work without it.
2. Keep additive preview-gated brownfield Apply and transactional failure cleanup.
3. Never auto-overwrite, delete, roll back, install, upgrade, or update external
   tools/personas/MCPs.
4. Niche capabilities are optional and off by default.
5. OpenSpec and Spec Kit are mutually exclusive.
6. Planner/Executor/Reviewer own workflow; specialists are bounded lenses.
7. `wing_copilot` is global; project memory uses one explicit canonical wing.
8. Do not use the goal skill.
9. No new runtime dependency, generic plugin framework, or universal LOC limit.

## Maintenance Budget

- Minimal generated surface: at most 3 files / approximately 250 lines.
- Standard base: target at most 12 files / 900 lines before selected extras.
- Installed doctor: target at most 300 lines.
- Optional specialist: one file, at most 60 lines.
- Expected new modules: `config_model.py`, `policy.py`, `analysis.py`,
  `apply.py`, `recovery.py`, `catalog.py`.
- Any extra production module, new dependency, unexpected subsystem, or roughly
  1,500+ net-new production lines triggers one re-review/replan.

## Target Architecture

| File | Ownership |
|---|---|
| `config_model.py` | Config v2, validation, v1 migration |
| `policy.py` | surfaces, task tiers, typed overrides |
| `catalog.py` | capability metadata/recommendations |
| `analysis.py` | read-only inventory and audit metrics |
| `apply.py` | preview, safe merges, transaction |
| `recovery.py` | passive/manual recovery |
| `manifest.py` | retained small manifest serializer |
| `core.py` | thin stable compatibility facade |
| `install.py` | thin CLI adapter |
| `gui.py` | Qt controller/pages/dialogs |

Extract a responsibility only in the phase that changes it; avoid move-only
churn and duplicate helpers.

## Configuration v2 and Overrides

Add `memory_wing`, `codebase_project_id`, `session_profile`, and structured
overrides:

```json
{
  "version": 2,
  "memory_wing": "qc_tool",
  "codebase_project_id": "QC_Tool",
  "session_profile": "auto",
  "policy_overrides": {
    "plan_tier": {"value": "mini", "reason": "Two-session change"}
  }
}
```

Typed dimensions:

- installation: minimal / standard / governed;
- plan: none / mini / compact / governed;
- validation: none / focused / broad;
- documentation: changed-only / handoff / full;
- memory and code intelligence: off / on-demand / required;
- review: self / independent;
- protocol guard: off / on.

Advanced Override UI:

- replace raw text with a native table/dialog;
- show derived value, override, stronger/equal/weaker classification, and Reset;
- require a reason and confirmation for weakening;
- show active overrides in Preview/Apply and record reasons in config/manifest;
- change the GUI in the same commit as config v2 so no intermediate build is
  incompatible.

Never expose overrides for path/symlink checks, secrets, destructive actions,
MCP sandbox safeguards, preview freshness, collision policy, transaction
cleanup, overwrite/deletion, or rollback.

v1 migration:

- carry normal fields unchanged;
- map `install_guard`, `require_review`, `require_memory`, and
  `require_code_intelligence` only where unambiguous;
- treat `require_plan=true` and free-form prose as unresolved;
- map `require_plan=false` only with a visible migration reason;
- reject `require_approval=false`; drop `true` because approval remains active;
- export v2 only after review.

## Adaptive Installation and Task Policy

| Surface | Installed by default |
|---|---|
| Minimal | `AGENTS.md`, short Copilot instructions, compact workflow config |
| Standard | compact agents, plan/handoff, targeted memory/code guidance, context exclusions, compact doctor |
| Governed | one spec system, selected guards/specialists, stronger evidence |

Derive the surface from existing size, complexity, testing, rigor, and selected
capabilities. Expert override is allowed under the reason/confirmation rule.

- Do not default data-science tooling for every new project.
- Keep Python instructions lightweight.
- Split the approximately 900-line experiment runner into an optional capability.
- In brownfield projects, recommend detected profiles; never add silently.
- Selecting Spec Kit makes it the plan/task source of truth; local handoff is
  pointer-only.

| Tier | Work | Plan | Validation | Memory/code |
|---|---|---|---|---|
| 0 | question, research, docs, trivial config | none | none or format/diagnostic | only if controlling |
| 1 | bounded low-risk edit | inline/mini ≤25 lines | smallest affected check | on-demand |
| 2 | coupled or multi-session behavior | compact ≤80 lines | focused per coherent slice; broad at checkpoint | targeted/project-scoped |
| 3 | security, migration, regulated, cross-service/team | Spec Kit/governed | broad relevant evidence | required where applicable |

Testing rules:

- add tests only for changed behavior, reproduced bugs, or named risks;
- do not test merely because a file was touched;
- check coherent slices, not every small edit;
- rerun the failing check while fixing it;
- run broad checks once at a checkpoint/high-risk gate;
- summarize successful output; never paste it into plans/handoffs.

Plans declare `**Task tier:** N`. Standard/governed handoffs repeat it and stay
within 30–40 lines / 3 KB. The Stop guard reads the declared tier, validates the
pointer/budget, accepts no plan for Tier 0 or inline Tier 1, and never claims an
external memory write succeeded.

## Memory and Code Intelligence

MemPalace:

- derive/edit one canonical lowercase `memory_wing`;
- use it explicitly in diary read/search/checkpoint/mine/sync guidance;
- distinguish mined source from durable decisions/session synthesis;
- detect case/separator/`wing_` aliases and likely global-wing leakage;
- show migration preview only—never merge/delete automatically;
- show version, backend, writable/blocked state, and read-only/writable hub;
- make holder PID optional diagnostic detail, not a portable requirement;
- recommend MemPalace 3.8 shared hub for multi-session/manual mining, but never
  upgrade or stop services during project Apply.

codebase-memory:

- store a canonical project ID;
- Configurator CLI probes may show database/root/HEAD/nodes/edges/changes,
  auto-index/watch, and team-artifact state;
- separately detect the MCP tools actually exposed to the agent;
- generated guidance names `index_status`/`detect_changes` only when exposed;
- use available graph tools with freshness marked unverified otherwise;
- do not mandate graph work for Tier 0/1.

All probes are read-only, timeout-bounded, and report degraded state plainly.

## Project Audit and Brownfield Adoption

Extend the existing Analyze/Review report with:

- production/test/workflow/documentation LOC and ratios;
- agent/skill/instruction/hook/MCP counts;
- recommended versus selected surface;
- plan/handoff size and pointer validity;
- repeated full-suite command strings;
- legacy/partial/ignored workflow artifacts;
- large files/Python functions and optional live graph hot spots;
- unexpected files/APIs/dependencies and duplicated test setup.

These are review triggers, not failures based solely on size.

- Extract `analysis.py` here.
- Replace the 966-line doctor with a surface-aware ≤300-line checker driven by
  generated config.
- Move costly environment/tool diagnostics into read-only Analyze.
- Classify old template files as required, optional, redundant, user-owned, or
  unknown; export manual cleanup guidance and never delete them.

## Capability Catalog and Session Profiles

Replace the checkbox wall with searchable categories and a detail pane showing:
type, selected/recommended/installed state, actual delivery, task trigger,
local/remote/credential warning, overlap/conflict, qualitative context cost,
guardrail, and verification link. Never invent numeric token savings.

Selectable project MCPs:

- DuckDB, Postgres, MarkItDown, Context7, Hugging Face.

Optional/pilot:

- rtk, Serena, affected-test selection, jscpd CLI;
- OpenSpec or Spec Kit;
- metadata-only OpenTelemetry;
- Vulture, Knip, project-specific Semgrep;
- experiment runner;
- Archify for explicit milestone diagrams only;
- compact accessibility, tool/dependency, AppSec, research, and
  AI-code/minimal-change specialist lenses.

Specialists are short, source-attributed, independent, and off by default. Do
not install the Agency roster.

Documentation-only watch/reject list:

- TencentDB Agent Memory, Understand-Anything, Headroom Desktop, Ponytail
  package/MCP, n8n, DeepSeek Harness, agent-world, full ECC/settings packs, and
  Skill Recorder until human UI automation is a real need.

Session guidance profiles:

- quick/docs, resume/history, large-code, symbol refactor;
- data analysis, document ingestion, ML/model selection, PR/issues.

The UI may generate/copy instructions but must not claim it changed a running
agent session when the host exposes no live toggle.

## Native Qt UX, About, and How-To

Pages:

1. Project
2. Workflow
3. Memory & Code
4. Tools & Profiles
5. Review & Apply
6. Recovery
7. Guide

Guide content:

- Analyze vs Preview vs Apply;
- surfaces, tiers, and test cadence;
- new vs existing project behavior;
- MCP configuration vs guidance-only options;
- memory/code identity and MemPalace hub locking;
- Advanced Overrides and permanent safety boundaries;
- conflict proposals and manual recovery.

Add contextual help for complex controls and catalog entries.

Add **Help → About Workflow Configurator** with app/template/config versions,
purpose, local-first/no-telemetry statement, what it can and cannot modify,
runtime/dependencies, license/provenance, and local documentation/research links.

## Implementation Order

1. `config_model.py` + `policy.py` + v1 migration + functional override dialog.
2. Adaptive surfaces, task tiers, compact templates, optional experiment runner.
3. Memory/code identity and read-only health/topology probes.
4. `analysis.py`, workflow metrics, compact doctor/guard, brownfield cleanup report.
5. `catalog.py`, session profiles, optional specialist templates.
6. `apply.py`/`recovery.py` extraction while preserving existing safety behavior.
7. Final Qt pages, catalog UX, Guide, About, and override polish.
8. Documentation, test consolidation, full acceptance, independent diff review,
   local commit, and project-scoped MemPalace checkpoint.

Each step is one coherent checkpoint after targeted validation. Do not run the
full suite after every small edit.

## Validation

Use compact matrices/subtests for config migration, surfaces, task tiers,
overrides, selected files, memory/code IDs, audit metrics, brownfield safety,
catalog conflicts, and Qt Guide/About/preview gating.

Consolidate redundant recovery-history tests but retain one test per distinct
safety invariant.

Cadence:

1. targeted model/policy tests after steps 1–2;
2. targeted analysis/Apply tests after steps 3–6;
3. one real Qt run after step 7;
4. one full suite plus minimal/standard/governed scratch-project matrix at the
   final checkpoint;
5. final diff, compile/type diagnostics, launcher check, and high-DPI inspection.

## Release Acceptance

- Minimal existing project previews only the three-file base.
- Standard/governed surfaces add only their documented artifacts.
- Research/docs require no code tests.
- Broad validation occurs only at configured checkpoints/high risk.
- Generated MemPalace operations always name the project wing.
- Memory aliases/lock topology and graph freshness are visible without mutation.
- Niche capabilities and specialists are off by default.
- Imported overrides are visible/resettable; weakening requires reason/confirmation.
- Hard safety cannot be represented as an override.
- About and complete How-To are available in the Qt UI.
- Brownfield conflicts and old generated files are never changed/deleted.
- Core/CLI/headless operation does not import PySide6.
- No new runtime dependency; final diff is within or explicitly re-approved
  against the maintenance budget.

## Non-Goals

No automatic MemPalace/process/wing migration, live MCP-session toggling,
second memory/graph/agent runtime, mandatory Archify, universal size threshold,
automatic simplifier, project-manager replacement, or generic plugin framework.

## Implementation Result

- Config schema v2, conservative v1 migration, typed expert overrides, and
  permanent safety boundaries implemented.
- Minimal/standard/governed scratch projects produce 3/12/23 files; Spec Kit
  omits the local planner and plan template.
- Canonical memory/code identities, bounded health checks, workflow metrics,
  searchable optional catalog, session profiles, compact specialists, Guide,
  About, and native Qt override UI implemented.
- Project doctor reduced from 966 to exactly 300 lines.
- Apply/recovery responsibilities extracted; incomplete rollback preserves
  recovery evidence and cleanup failures are explicit.
- 61 tests, headless smoke, real Qt acceptance, strict doctor checks, launcher
  syntax, diagnostics, and `git diff --check` passed in Conda `py311`.
