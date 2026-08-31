# Real-Project Workflow Audit

**Research date:** 2026-08-30

**Audited projects:**

- `QC_Tool`
- `CoScriBeRA`

**Safety:** Both projects were inspected read-only. No file, Git state,
environment, dependency, or process in either project was changed.

**Session evidence:** No stored Copilot sessions were returned for the exact
workspace paths. Conclusions about behavior therefore come from live files,
Git history where available, MemPalace, and workflow artifacts—not reconstructed
chat transcripts.

## Executive Conclusion

The previous workflow produced valuable correctness, security, release, and
recovery practices. It also demonstrated three serious design failures:

1. **Adaptive policy did not mean adaptive installation.** Small and large
   projects received nearly the same agents, skills, doctor, experiment tooling,
   memory protocol, code-intelligence protocol, and documentation.
2. **Current-state files became history databases.** Handoffs and plans
   accumulated old releases, evidence, and execution logs despite explicit
   instructions to rewrite them and keep handoffs below 50 lines.
3. **MCP availability was treated as inherently useful.** MCPs reduce tokens
   only when a task-specific query replaces more expensive reading or output.
   Every enabled server otherwise adds standing tool-schema/context cost.

The strongest next improvement is not another MCP. It is a **workflow audit and
budget layer**:

- install only the project/task surfaces that are needed;
- choose MCPs through task-specific session profiles;
- cap handoff/plan size deterministically;
- detect code hot spots before adding more behavior to them;
- treat Git, plans, handoffs, and MemPalace as different stores rather than
  copying the same history into all four.

---

# Quantitative Snapshot

## QC_Tool

The Git worktree was already highly active at audit time: 40 tracked Python
files modified plus six untracked source/test files. None were touched by this
audit.

| Area | Observed size |
|---|---:|
| Tracked production Python | 55,036 lines |
| Tracked test Python | 40,627 lines |
| `docs/HANDOFF.md` | 2,296 lines |
| Largest source file, `qc_tool/ui/app.py` | 7,579 lines |
| `qc_tool/engine.py` | 2,384 lines |
| `qc_tool/history/store.py` | 2,204 lines |
| Largest test file, `tests/test_ui.py` | 2,862 lines |

Large functions/classes identified during the audit include:

- `_render_result_view`: approximately 2,695 lines;
- `create_pages`: approximately 2,072 lines;
- `run_qc`: approximately 1,123 lines;
- `RunHistory`: approximately 1,607 lines.

These are maintenance hot spots. QC_Tool has genuine domain complexity—Excel,
PowerPoint, XLSB, formula dependency analysis, history, browser UI, Windows
focus integration, and evidence-preserving comparison—but multi-thousand-line
functions are accidental structural complexity, not an unavoidable property
of that domain.

The workflow handoff skill says:

> Rewrite `docs/HANDOFF.md` as current state, not accumulated history.

and:

> Keep the handoff below 50 lines.

The live handoff is 2,296 lines and includes release history, superseded
blockers, prior plans, long performance evidence, and old next actions. The
instruction was present but not enforced.

Full-suite commands are also copied throughout workflow artifacts:

| Command | Files containing it |
|---|---:|
| `pytest -x -q` | 15 |
| `ruff check .` | 16 |
| `pyright` | 22 |

This repetition consumes context and creates drift without adding executable
coverage.

## CoScriBeRA

This directory has no `.git` metadata, so repository history and working-tree
diffs were unavailable.

| Area | Observed size |
|---|---:|
| Application Python under `src/` | 3,726 lines |
| Test Python | 2,066 lines |
| Documentation under `docs/` | 1,361 lines |
| Agent customizations under `.github/` | 2,256 lines |
| Root `AGENTS.md` | 91 lines |
| `docs/HANDOFF.md` | 90 lines |

The `.github/` customization surface plus `docs/` and root `AGENTS.md` is
approximately the size of the application itself. This is the clearest example
of the one-size-fits-all setup imposing too much operational scaffolding on a
small project.

The largest workflow component is the 964-line project doctor. The largest
application file is the 576-line API job registry. The active business-hardening
plan is 562 lines.

The handoff is much healthier than QC_Tool's, but still exceeds the same
50-line rule by 80%. It repeats detailed checks, architecture decisions, memory
state, blockers, and next actions that already exist in the plan, operational
documentation, and durable memory.

---

# What the Previous Setup Did Well

## QC_Tool

Useful outcomes that should be preserved:

- fail-closed workbook and formula safety;
- bounded worker/memory behavior;
- deterministic evidence hashes and compatibility tests;
- synthetic fixtures instead of private client data;
- typed blocked-run/prerequisite contracts;
- release provenance and cross-platform validation;
- explicit distinctions between proof, approximation, and unavailable
  production evidence.

The volume of testing is not automatically waste. A product dealing with
multiple Office formats, dependency graphs, alignment, private data boundaries,
and release compatibility needs substantial tests. The problem is repeated
execution/logging and monolithic implementation, not simply test count.

## CoScriBeRA

Strong practices include:

- authentication before model initialization;
- request-ID correlation and structured logging;
- archive-before-parse source handling;
- strict citation and source scoping;
- readiness that fails closed;
- hash-chained audit evidence;
- durable job recovery;
- explicit distinction between hardened prototype evidence and regulated
  validation.

The workflow helped produce a rigorous prototype. The goal is to retain that
quality with less scaffolding and repetition.

---

# Where the Workflow Failed

## 1. Instructions were advisory

The 50-line handoff rule failed in both projects:

- QC_Tool: 2,296 lines;
- CoScriBeRA: 90 lines.

The same memory/code-intelligence startup sequence is repeated across:

- `AGENTS.md`;
- repository Copilot instructions;
- Planner;
- Executor;
- Reviewer;
- plan skill;
- resume skill;
- handoff skill;
- project doctor.

Repeating a protocol increases context but does not guarantee compliance.

## 2. Handoff, plan, Git, and memory duplicated history

The intended boundaries should be:

- **Handoff:** exact current state and next action.
- **Plan/spec:** intended scope and unchecked work.
- **Git:** implementation history and changed files.
- **CI/test output:** executable verification.
- **MemPalace:** durable decisions and expensive synthesis.

Instead, the same decisions, checks, versions, files, and historical narrative
appear in multiple places.

QC_Tool's handoff effectively became a project journal. This defeats its purpose
as cheap wake-up context.

## 3. Plans became implementation transcripts

Large plan files accumulated:

- repeated commands;
- step-by-step execution evidence;
- reviewer reconciliation;
- historical changes;
- completed release details;
- follow-up remediation.

That information may be useful, but it should not remain in the active plan
sent to every resumed session.

## 4. Project size changed policy text, not installed surface

The current Configurator derives light/standard/strong policy, but core
installation still begins from a large shared `CORE_FILES` set.

CoScriBeRA received:

- three stage agents;
- five core skills;
- project doctor and script;
- multiple protocol documents;
- observability/security/context documents;
- environment policy;
- experiment tooling through the default data-science profile.

A 3,726-line application should not require a similarly sized workflow layer
unless its risk profile explicitly justifies it.

## 5. The workflow did not prevent code hot spots

The generic instruction "make the smallest change" did not stop thousands of
lines accumulating in individual functions.

The missing control is not another persona. It is a structural trigger:

- identify a changed function/file already above a project-specific threshold;
- show inbound/outbound impact;
- require an explicit reason before adding more responsibility;
- recommend extraction or replacement only when it reduces maintenance;
- review the maintenance surface of the final diff.

## 6. Test policy was repetitive rather than selective

Commands are repeated throughout documents, and plans repeatedly record broad
suite results.

The command itself should live once in `AGENTS.md` or the project manifest.
Plans should reference a stable label such as:

```text
Verify: focused tests for row identity
Checkpoint: project full gate
```

The executable command and latest result should come from current CI/tool
output, not copied prose.

---

# Do More MCPs Reduce Token Consumption?

## Short answer

**No. More MCPs usually increase standing token consumption.**

An MCP helps only when:

```text
schema overhead + MCP result
<
files/tool output/reasoning it replaces
```

Every enabled MCP contributes tool names, descriptions, and input schemas to
the model context. Servers with many tools can cost tokens on every turn even
when no tool is called.

## Existing MCP/tool assessment

### MemPalace

High value when:

- resuming historical work;
- retrieving an old decision;
- recording one durable synthesis/checkpoint.

Wasteful when:

- status, diary, search, drawers, and KG are all called for every trivial task;
- raw command/code state is duplicated into memory;
- several search results are retrieved before the task needs history.

Recommended usage:

- one targeted project wake-up or search;
- one atomic checkpoint at a substantial boundary;
- KG changes only for durable temporal facts.

### codebase-memory

Likely high value for QC_Tool because 55K production lines and large call-flow
hot spots make broad file reading expensive.

Lower value for a 3.7K-line project when the relevant file/symbol is already
known.

Use it for:

- architecture orientation;
- symbol/caller/impact lookup;
- complexity and hot-spot discovery;
- data/cross-service flow.

Do not require it for:

- documentation-only changes;
- known single-file edits;
- non-code research;
- tiny repositories where normal symbol search is cheaper.

### DuckDB

Reduces tokens when SQL can summarize large CSV/Parquet/tabular data instead of
loading it into model context.

It adds no value—and still contributes schema overhead—during UI, docs,
packaging, or normal source refactoring.

### Postgres

Useful only for tasks requiring live schema/query/plan evidence. Keep it off
otherwise. Never treat database access as general project context.

### Context7

Can reduce hallucination and repeated documentation browsing when a current
external API is controlling the change. It does not reduce tokens for
repository-local questions.

### MarkItDown

Useful when the task starts from PDF, Office, or other binary documentation.
Disable it for normal code work.

### Hugging Face

Useful for model/dataset discovery. Disable it for unrelated engineering work.

### Serena

Potentially reduces reads and unsafe textual edits during symbol-heavy
refactors. It overlaps VS Code language tools and codebase-memory, so enable it
only for a refactor session and measure whether it replaces tool calls.

### jscpd

Prefer the one-shot CLI and compact reporter. A persistent MCP is unnecessary
unless snippet-level duplicate lookup becomes frequent.

### rtk

Not an MCP. It can reduce command-output volume and is more directly relevant
to test/build log bloat than another server.

### TencentDB Agent Memory

Do not add. It duplicates current memory/code graph roles and adds a proxy,
services, LLM processing, and operational state without supported Copilot chat
memory integration.

## Recommended session profiles

The Configurator should recommend a **session tool profile**, not merely list
servers. Separate:

- **availability:** whether a server's schema is enabled for the session;
- **invocation policy:** whether the agent should proactively call it.

The current template makes MemPalace mandatory. A minimal profile would
intentionally revise that contract: it may disable the server only for a fresh,
fully bounded task with no historical dependency. If history might matter,
keep it available but use only one targeted retrieval and one substantial
checkpoint.

| Session profile | Enable | Keep off |
|---|---|---|
| Quick edit/docs | No proactive MCP call; optionally Context7 if current external APIs control the task | Data, model, and document servers; disable MemPalace only when history is explicitly irrelevant |
| Resume historical work | MemPalace | Data/document/model servers |
| Large-code investigation | codebase-memory; MemPalace available/called only if historical decisions matter | DuckDB/Postgres/HF/MarkItDown |
| Symbol-heavy refactor | codebase-memory + Serena | Unrelated MCPs |
| Data analysis | DuckDB or Postgres; optionally MemPalace | Serena/HF/MarkItDown unless needed |
| Document ingestion | MarkItDown; optionally MemPalace | Database/code-refactor tools |
| ML/model selection | Hugging Face + Context7 | Database/document/refactor tools |
| PR/issue management | GitHub tools | Local data/model tools |

Choose the profile before starting a session to reduce tool-surface/context
churn. Stable tooling may improve cacheability, but cache effects must be
measured rather than assumed.

## Context budget the GUI should show

For selected MCPs/tools, show:

- server count;
- advertised tool count;
- local versus remote;
- credentials/network required;
- persistent service required;
- expected task benefit;
- overlap warning;
- recommended enable/disable profile.

Do not display a made-up token estimate unless actual serialized schemas are
measured from the running client.

---

# Compact Planning and Logging Policy

## Tier 0: no plan artifact

Use for:

- questions;
- research summaries;
- documentation-only edits;
- trivial configuration;
- known one-file low-risk changes.

Record only:

```text
Intent:
Files:
Check:
```

No handoff is required unless the task stops unfinished.

## Tier 1: mini plan

Use for bounded low-risk implementation.

Maximum: **25 lines**.

Required fields:

- goal;
- non-goals;
- existing code to reuse;
- expected files;
- one to three steps;
- focused check;
- stop condition.

No execution log.

## Tier 2: compact plan

Use for coupled behavior changes or multiple sessions.

Maximum: **80 lines**.

Required fields:

- acceptance criteria;
- decisions and alternatives;
- risks;
- bounded tasks;
- specialist reviews if triggered;
- focused checks;
- final checkpoint.

Completed step history is removed or archived. Do not append command output.

## Tier 3: governed specification

Use Spec Kit for:

- ambiguous product behavior;
- migrations;
- security/auth;
- regulated or evidence-heavy work;
- cross-team/multi-service changes;
- long multi-session initiatives.

Spec Kit becomes the plan/task source of truth. Do not create a parallel local
plan containing the same material.

## Handoff contract

Maximum: **30–40 lines and 3 KB**.

It contains only:

- updated timestamp;
- workspace/branch;
- exact active plan/spec path;
- current status;
- last observed focused/full checks;
- exact stopping point;
- current blockers;
- pending memory operation;
- next three actions.

It does not contain:

- release history;
- completed plan details;
- full decisions;
- benchmark tables;
- old blockers;
- old next actions;
- hashes/digests already stored elsewhere;
- copied test output.

## Enforcement

Add deterministic project-doctor/stop checks:

- handoff line and byte budget;
- allowed headings;
- one active plan pointer;
- referenced plan exists;
- no "Historical", "Superseded", or release-log sections in active handoff;
- active plan line budget by tier;
- repeated full-suite command strings outside `AGENTS.md`;
- stale completion state;

The hook should ask the agent to rewrite current state, not append more history.
MemPalace duplicate detection remains an advisory audit outside deterministic
doctor/stop gates because a local hook cannot prove an external MCP operation
succeeded.

---

# Recommended Configurator Improvements

## Priority 1: Truly adaptive installation surfaces

Split the current large `CORE_FILES` base before adding more GUI surface.
Derive an **installation surface preset** from the existing project size,
complexity, testing, and rigor axes; do not add another independent workflow
mode.

### Minimal surface

For small/low-risk projects:

- `AGENTS.md`;
- short repository instructions;
- compact workflow config;
- optional short handoff only when work spans sessions.

No default:

- three custom agents;
- project doctor;
- experiment runner;
- broad protocol library;
- mandatory code graph;
- mandatory memory ritual.

### Standard surface

Add:

- Planner/Executor/Reviewer;
- compact plan/handoff;
- targeted memory and code-intelligence guidance;
- context exclusions;
- focused doctor checks.

### Governed surface

Add:

- Spec Kit integration;
- lifecycle guard;
- security/review specialist lenses;
- stronger verification;
- full operational evidence documents.

If Spec Kit is selected, it owns specification and task state. The local
handoff remains pointer-only, and any additional evidence document must have a
single narrowly defined purpose rather than duplicating Spec Kit artifacts.

## Priority 2: Plan and handoff budgets

Make verbosity levels concrete configuration:

- none/inline;
- mini;
- compact;
- governed/spec.

Generate the corresponding template and enforce its line/byte budget.

## Priority 3: Extend existing analysis with workflow audit metrics

Extend the current Analyze/Review report rather than adding a separate screen.
Report:

- production/test/workflow LOC;
- workflow-to-application ratio;
- handoff lines/bytes versus configured budget;
- active plan tier and size;
- repeated command strings;
- agent/skill/instruction counts;
- enabled MCP/tool count;
- stale or broken plan pointers;
- partial installation;
- large files/functions and change hot spots;
- ignored/unversioned workflow artifacts.

This gives evidence without another navigation surface.

## Priority 4: Session MCP profiles

Let the GUI choose a task/session profile and emit:

- which servers to enable;
- which to disable;
- why each is present;
- credential/network warning;
- overlap warning;
- CLI/VS Code-specific configuration instructions.

Do not auto-enable every installed MCP.

## Priority 5: Maintenance hot-spot guard

Use live source/codebase-memory evidence to warn when:

- a changed file/function is already a hot spot;
- a new feature expands an oversized function;
- a diff adds unexpected files/public APIs/dependencies;
- tests duplicate existing setup;
- a proposed helper resembles existing code.

These are review triggers, not universal hard limits.

## Priority 6: Conditional specialist lenses

Adopt selected Agency Agents patterns only:

- Accessibility reviewer for UI work;
- Tool/dependency evaluator for new integrations;
- Security/AppSec reviewer for high-risk boundaries;
- Research synthesist for evidence-heavy research;
- AI-generated-code auditor when structural budgets fire.

Keep Planner/Executor/Reviewer as workflow owners.

---

# Recommended Next Implementation Order

1. Split `CORE_FILES` into derived minimal/standard/governed installation
   surfaces.
2. Add handoff/plan tiers and deterministic size checks.
3. Extend the existing analysis/report UI with workflow audit metrics.
4. Add task-scoped MCP session profiles and overlap warnings.
5. Add maintenance hot-spot warnings.
6. Add three compact specialist lenses only after the audit/routing foundation
   works.

Do not add TencentDB Agent Memory or the Agency Agents roster before these
changes. Both would increase surface area without solving the demonstrated
failures.
