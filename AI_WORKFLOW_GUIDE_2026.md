# AI-Assisted Development Workflow Guide — August 2026

**Audience:** Developers and technical leads using GitHub Copilot, local development tools, and optional MCP services.

**Purpose:** Produce correct, maintainable software without turning every task into a large plan, test suite,
documentation project, or permanent tool dependency.

**Companion tool:** [`workflow_configurator`](workflow_configurator/) implements this guidance through a native PySide6 Configurator
with adaptive project surfaces, read-only analysis, preview-gated Apply, explicit memory/code identities, and
manual recovery.

---

## Executive Operating Model

1. **Classify the task and risk.** A question, one-file fix, and database migration do not deserve the same process.
2. **Load only the context and tools needed now.** Instructions, history, file reads, schemas, and output consume context.
3. **Start from live evidence.** Git, current files, language services, tests, and runtime output are authoritative.
4. **Reuse before generating.** Find the existing helper, type, component, pattern, or dependency first.
5. **Change the smallest maintainable surface.** Optimize for comprehension, not the lowest line count.
6. **Validate proportionally.** Check a coherent slice; broaden once at a checkpoint or high-risk boundary.
7. **Persist only durable value.** Active state belongs in a short handoff/spec; decisions belong in project memory.
8. **Review the final artifact.** Unexpected files, APIs, dependencies, tests, or docs need justification.

The goal is not maximum agent activity. It is the lowest total cost that produces correct, understandable,
recoverable software.

---

# 1. Cost and Context

## 1.1 Current Copilot billing

As of 2026-08-31, GitHub documents Copilot as seat licenses plus **GitHub AI Credits**:

- Copilot Business includes 1,900 credits per user/month in a pooled allowance.
- Copilot Enterprise includes 3,900 credits per user/month.
- One credit is $0.01 USD.
- Chat, CLI, cloud agent, Spaces, Spark, and third-party coding-agent interactions consume credits.
- Code completions and next-edit suggestions remain unlimited on paid plans.
- Cost depends on model and input, output, and cached tokens.
- Budget exhaustion does not automatically switch a user to a cheaper model.

The June–September promotional allowances expire on 2026-09-01. Do not freeze model prices or promotions into
project instructions; use GitHub’s live billing pages. GitHub recommends at least VS Code 1.120 and Copilot CLI
1.0.48 for accurate billing terminology and alerts. This workflow targets VS Code 1.129 or newer.

## 1.2 What grows context

- always-on and matching path instructions;
- chat history, summaries, and attachments;
- files read into the conversation;
- enabled tool/MCP definitions;
- tool results and copied command output;
- active plan/handoff content;
- model output.

Common failure patterns:

1. one chat contains unrelated tasks;
2. broad searches and large files remain in history;
3. irrelevant MCPs stay enabled;
4. plans/handoffs accumulate completed history;
5. successful build/test output is copied repeatedly;
6. agents reread code because durable decisions and live structure are confused.

Do not optimize tokens alone. A tool that saves prompt tokens but adds a server, index, security risk, generated
artifacts, and maintenance work can increase total cost.

---

# 2. Adaptive Workflow

## 2.1 Task tiers

| Tier | Typical work | Plan | Validation | Memory/code tools |
|---|---|---|---|---|
| **0** | Question, research, docs, trivial config | None | None or smallest format/diagnostic check | Only if history/structure controls the answer |
| **1** | Bounded low-risk edit | Inline/mini, ≤25 lines | Smallest affected check | On demand |
| **2** | Coupled behavior or multi-session change | Compact, ≤80 lines | Focused per coherent slice; broad at checkpoint | Targeted and project-scoped |
| **3** | Security, migration, regulated, cross-service/team | Governed specification | Broad relevant evidence | Required where applicable |

Tier is task-specific. A large repository can have a Tier 0 question; a small repository can have a Tier 3 auth change.

## 2.2 Project installation surfaces

| Surface | Default contents |
|---|---|
| **Minimal** | `AGENTS.md`, compact Copilot instructions, generated workflow configuration |
| **Standard** | Compact agents, task state, context exclusions, scoped memory/code guidance, project doctor |
| **Governed** | One spec system, selected guards/specialists, stronger evidence/review controls |

Do not install the governed surface because it looks more complete. Workflow files are maintenance surface too.

## 2.3 Constrained expert overrides

Experts may override planning, validation, documentation, memory, code intelligence, review, and protocol guard.
A weaker value requires a recorded reason, visible Preview classification, and confirmation before Apply.

Never allow overrides for:

- path/symlink containment and secret handling;
- destructive-operation approval;
- MCP sandbox safeguards;
- Preview freshness and collision policy;
- transactional cleanup;
- automatic overwrite, deletion, or rollback.

---

# 3. Session and Context Hygiene

## 3.1 Keep sessions focused

Start a new session when the task is complete, the next task has a different objective, history is mostly irrelevant,
or the model/tool set must change substantially. Continue when fixing the current change or executing the next
dependent step while context remains focused.

Use precise file/symbol references. Avoid whole-folder context and broad repository reads when a structural query or
small targeted search will answer the question.

## 3.2 Plan only when it pays

Tier 0 needs no plan. A useful mini/compact plan records:

- observable goal and acceptance criteria;
- non-goals and existing code to reuse;
- expected files, public APIs, and dependencies;
- risks that must not be simplified away;
- ordered steps and cheapest useful verification;
- condition that triggers replanning.

Do not append execution transcripts. Remove completed history or archive it outside the active plan.

## 3.3 Handoff only active state

Use a handoff only for unfinished/multi-session work. Keep it under 40 lines and 3 KB:

- workspace/branch and task tier;
- exact active plan/spec path;
- current status and stopping point;
- last observed checks;
- blockers and pending memory operations;
- next three actions.

Do not include release history, old blockers, benchmark tables, copied output, or completed plan detail.

## 3.4 Delegate selectively

Use a subagent when independent research or verbose execution genuinely benefits from a separate context. Do not
delegate a simple lookup, a few known file reads, a small discovery-edit task, or work the main agent will duplicate.

---

# 4. Copilot Customization Surfaces

## 4.1 Instructions

Official VS Code documentation distinguishes:

- `.github/copilot-instructions.md`: repository-wide essentials;
- `AGENTS.md`: project/agent guidance;
- `.github/instructions/*.instructions.md`: path-specific rules.

Always-on instructions enter applicable requests. Keep them to stable commands, boundaries, environment ownership,
destructive/secret restrictions, and task policy. Keep manuals, research reports, and long examples elsewhere.

## 4.2 Agent Skills

Agent Skills are an open standard supported by Copilot in VS Code, CLI, and cloud agent. VS Code progressively loads
skill metadata, then `SKILL.md`, then supporting resources as needed.

Use a skill for a specialized reusable procedure such as experiment execution, deployment validation, handoff,
project diagnosis, or document conversion. Make expensive workflows manually invocable.

## 4.3 Agent Plugins

Agent Plugins package reusable skills and MCP configuration using an open standard; Copilot plugins can also bundle
agents and hooks. Use a small plugin for generic capabilities shared across repositories, not for project identity or
active task state.

Pilot plugins from a reviewed local directory before marketplace publication. Pin team marketplaces to a reviewed
revision, update explicitly, and disable unused components. Keep `AGENTS.md`, essential repository instructions,
MemPalace/codebase-memory identities, project commands, task state, and project-specific guards in the repository.
Plugins do not replace repository customization for GitHub.com's coding agent.

The Workflow Configurator can preview and export its five reviewed generic specialists as a no-overwrite local
Copilot plugin. It never installs or enables that plugin; project-specific policy and identity remain local.

## 4.4 Custom agents and specialists

Use an agent for distinct authority:

- Planner: bounded plan, no implementation.
- Executor: approved task, no silent redesign.
- Reviewer: findings only, no edits.
- Accessibility/AppSec/tool/lean/research specialists: optional lenses triggered by the task.

Keep the roster small. Large persona catalogs increase discovery, review, and maintenance costs.

## 4.5 Hooks

VS Code Agent Hooks are **Preview**. Hook code can enforce local observable rules when invoked, but preview
availability/format and runtime failures mean hooks are not the sole security boundary.

Good checks:

- destructive commands require confirmation;
- plan pointers stay inside the project;
- plan/handoff budgets are exceeded;
- workflow-control files changed.

Do not claim a hook proved an external memory write, remote health, complete code review, or success after timeout.

---

# 5. Lean Code and Proportional Testing

## 5.1 Lean-code contract

Lean means minimum maintenance and comprehension burden at equivalent behavior and quality. Before implementation:

```text
Existing code to reuse:
Expected files touched:
Expected new files/public APIs/dependencies:
Explicit non-goals:
Correctness/safety boundaries:
Condition that triggers re-review:
```

For small low-risk work, prefer existing files/dependencies, no new architecture layer, no hypothetical
configuration, and no public API beyond the requested contract.

Review triggers:

- unexpected files, APIs, dependencies, or layers;
- duplicated implementation or test setup;
- responsibility added to an existing hot spot;
- changed-function complexity/size;
- unused files, exports, symbols, or dependencies;
- test code disproportionate to changed behavior;
- defects and follow-up rework.

These trigger review, not automatic failure. Generated clients, schemas, migrations, parsers, fixtures, and
compatibility tables may be legitimately large.

Do not run a mandatory simplifier after every implementation. Use one lean-code review only when the declared
surface is materially exceeded. Do not adopt the Ponytail plugin/MCP; its useful principles are already owned here.

## 5.2 A test needs a reason

Add/change a test for:

- changed observable behavior;
- a reproduced bug;
- a named regression risk;
- API/schema/migration contracts;
- security, temporal, numerical, or data boundaries.

Do not add a test because a file/helper was touched or solely to increase coverage.

## 5.3 Validation cadence

1. Form one hypothesis and select the cheapest disproof.
2. Make a coherent implementation slice.
3. Run the smallest affected test/lint/type diagnostic.
4. Fix change-caused failures and rerun that check.
5. Broaden once at a checkpoint/high-risk boundary.
6. Run the relevant full suite before release when project policy requires it.

Reduce test bloat through parameterization, shared fixtures, behavior-level assertions, contract tables, and removal
of stale/duplicated cases. Affected-test tooling is optional; retain a broader checkpoint/release gate.

---

# 6. Brownfield Adoption and the Configurator

## 6.1 Safe existing-project sequence

1. Analyze manifests, languages, environment managers, instructions, agents, skills, hooks, MCPs, task state, and Git.
2. Measure production/test/workflow/docs surface and find broken pointers, repeated commands, and legacy files.
3. Derive the smallest justified installation surface.
4. Preview missing files, additive merges, conflicts, and manual-cleanup candidates.
5. Resolve ownership questions.
6. Apply only missing files and narrowly documented additive merges.
7. Leave conflicting user-owned content untouched.
8. Run the surface-aware project doctor and relevant project checks.
9. Use passive manifests/backups for manual recovery.

Old generated files are never deleted automatically.

## 6.2 Use the tool

```bash
# Read-only analysis
python workflow_configurator/install.py /path/to/project \
  --workflow existing --analyze --json

# Review intended changes
python workflow_configurator/install.py /path/to/project \
  --workflow existing --preview

# Apply only previewable safe additions/merges
python workflow_configurator/install.py /path/to/project \
  --workflow existing --apply
```

Launch the native UI with `./launch-workflow-configurator.sh`, or install its application-menu entry once with
`./install-workflow-configurator-launcher.sh`.

UI pages:

1. Project
2. Workflow
3. Memory & Code
4. Tools & Profiles
5. Review & Apply
6. Recovery
7. Guide

**Help → About Workflow Configurator** shows version, locality, modification boundaries, and provenance. Apply stays
disabled until the current configuration has a matching Preview.

---

# 7. Memory and Code Intelligence

## 7.1 Storage ownership

| Store | Owns |
|---|---|
| Live files, Git, language services, runtime/tests | Current implementation truth |
| Handoff or selected spec system | Current task state |
| Repository instructions | Small stable conventions/commands |
| MemPalace project wing | Durable decisions, rationale, project synthesis |
| `wing_copilot` | Cross-project user/agent/tool lessons |
| codebase-memory | Structural code graph and orientation |

## 7.2 MemPalace project routing

Every project has one canonical wing such as `qc_tool`. Use it explicitly on diary reads, searches, checkpoint items,
checkpoint diary, mine, and sync.

Do not assume `agent_name="copilot"` implies project routing:

- an unscoped diary write defaults to `wing_copilot`;
- an unscoped diary read can span that agent’s diary entries across wings.

Operations have different meanings:

- **mine:** current source/doc chunks for semantic retrieval;
- **sync:** stale mined-source cleanup under documented safety rules;
- **checkpoint/diary:** durable decisions and session synthesis;
- **knowledge graph:** temporal facts and relationships.

Mining code does not record why it changed. An old diary does not prove current implementation.

## 7.3 MemPalace writer topology

MemPalace 3.6 writable MCP sessions could hold the palace lease and block manual mining. Never delete a live lock file
or bypass peer-writer protection casually; concurrent Chroma/FTS/HNSW writers risk corruption.

MemPalace 3.8 supports the preferred multi-session topology:

```text
Agent MCP proxies ─┐
GUI/other client ──┼──> one writable loopback HTTP hub ──> palace
normal CLI mine ───┘
```

Normal mines can forward to the hub. Upgrading alone is insufficient: start/verify the writable hub, point clients
at it, and test on a disposable palace first.

## 7.4 codebase-memory

Use it for architecture, symbols, callers/callees, routes, dependencies, data flow, impact, and hot spots. Use
language-service references/search for small known edits.

Match evidence effort to the claim:

- **Scout:** positive orientation only; no absence, exhaustive, dead-code, or complete-impact claims.
- **Verify:** normal task work; check the root/freshness when exposed and verify graph results in live source.
- **Auditor:** negative, exhaustive, security, or boundary claims; require bounded scope, complete result streams, and
  coverage evidence when the active interface exposes it.

If Auditor evidence is unavailable, narrow the claim instead of inventing certainty.

The local graph is persistent in the user cache. `persistence=true` additionally writes
`.codebase-memory/graph.db.zst` for team bootstrap; `false` does not make the local index ephemeral.

Freshness protocol:

1. Resolve project ID and expected repository root.
2. Check status/change detection when exposed.
3. Verify indexed root matches the selected project.
4. Refresh when missing/stale.
5. Query structure.
6. Read relevant live code before editing.

MCP and CLI surfaces can differ. Do not instruct an agent to call status/change/coverage tools unless its active
surface exposes them. Mark freshness unverified instead of inventing a result. Do not run duplicate code graphs
without measured need.

---

# 8. MCP and Session Profiles

## 8.1 Availability is not invocation

Separate **available**, **enabled in this session**, and **actually needed now**. An installed MCP does not need its
schemas enabled everywhere.

| Session | Enable/use | Keep off unless needed |
|---|---|---|
| Quick question/docs | No proactive MCP; Context7 for a controlling current API | Data/model/document/refactor servers |
| Resume/history | Project-scoped MemPalace | Unrelated servers |
| Large-code investigation | codebase-memory; MemPalace for historical decisions | Database/model/document tools |
| Symbol refactor | LSP + codebase-memory; optionally Serena | Unrelated MCPs |
| Data analysis | DuckDB or Postgres | Document/model/refactor tools |
| Document ingestion | MarkItDown; optionally project memory | Database/model/refactor tools |
| ML/model selection | Hugging Face + Context7 | Database/document tools |
| PR/issues | GitHub tools | Local data/model/document tools |

## 8.2 Scope and security

Use user-profile MCP configuration for folder-independent services without `${workspaceFolder}`. Use workspace scope
for project paths, permissions, or credentials. Do not register the same server in both scopes.

Review publisher, command, arguments, environment, filesystem/network access, and tool count. Use **MCP: List
Servers → Show Output** for startup diagnostics. Remote tools receive query/context data; do not send secrets,
private code, or personal data unless policy explicitly permits it.

When MCP configuration is added or changed, use a read-only audit for plaintext secrets, explicit shell wrappers,
floating packages, unreviewed servers, duplicate scope, and missing sandbox controls. Redact values and treat pattern
matches as review findings, not proof of exploitation.

The Configurator performs this audit during Analyze for proposed/workspace configuration and known VS Code user
profiles. It starts no server and preserves normal source, identity, permission, and runtime review.

Useful task tools:

- **DuckDB:** bounded local CSV/Parquet analytics.
- **Postgres:** development/restricted-replica schema and query diagnostics.
- **MarkItDown:** convert PDF/Office/HTML/image/audio into reviewable Markdown.
- **Context7:** current version-aware library documentation.
- **Hugging Face:** current public model/dataset/paper metadata and licenses.
- **GitHub:** repositories, PRs, issues, and Actions.
- **Azure:** Azure resources/logs when the task is operational.

---

# 9. Models, Agents, and Optional Tools

## 9.1 Model routing

Use strong reasoning for ambiguous architecture, migration, security, and final high-risk review. Use a lower-cost
capable model for bounded implementation with clear acceptance criteria. Check live model pricing rather than
hardcoding it into project instructions.

## 9.2 Conditional specialists

- Accessibility reviewer for UI changes.
- Tool/dependency evaluator for new dependencies, MCPs, or services.
- AppSec reviewer for auth, secrets, injection, and destructive boundaries.
- Research synthesist for evidence-heavy decisions.
- Lean-code reviewer when planned maintenance surface is exceeded.

Planner/Executor/Reviewer own workflow. Specialists return bounded findings, not parallel plans. Agency Agents is a
pattern library, not a roster to install wholesale.

## 9.3 Tool disposition

### Keep and improve first

Native Copilot customization, MemPalace, codebase-memory, language-service tools, project-native commands, context
exclusions, and metadata-only observability.

### Optional pilots

| Capability | Use when | Guardrail |
|---|---|---|
| rtk | Command output is repeatedly large | Keep only if total context cost falls on real tasks |
| Affected-test selection | Suite is materially expensive | Retain release/checkpoint coverage |
| Serena | Symbol refactor exceeds existing LSP/graph support | Remove if it duplicates tools |
| OpenSpec | Brownfield behavior delta spans sessions | Not for routine fixes |
| Spec Kit | Tier 3 ambiguity/governance/migration | Single spec/task source; no duplicate plan |
| jscpd | Duplication appears in real diffs | One-shot CLI before MCP |
| Vulture/Knip | Periodic Python or JS/TS dead-code audit | Review false positives; never auto-delete |
| Semgrep | Repeated project-specific defect | Avoid generic always-on rule packs |
| Archify | One milestone diagram replaces repeated explanation | Never update after every change |
| Experiment runner | Project runs tracked ML experiments | Keep separate from basic DS guidance |
| Agent Plugin packaging | Generic capabilities are copied across repositories | Pilot locally; keep project identity/state in the repository |

### Patterns only/watch

- BMAD: task sizing and brownfield discipline.
- ECC/claude-codex-settings: context and guard patterns.
- OpenWorker: earned autonomy and audit ideas.
- Aider repository map: ranked structural context.
- Skill Recorder: revisit for real repetitive human desktop work.
- Forge/alternate runtimes: reference UX, not a parallel default driver.
- Awesome Copilot Agent Skill Stack: smallest-stack, conflict-review, and staged-install patterns only.
- Agent supply-chain manifests: add only if an external customization import path is created.

### Do not integrate by default

- TencentDB Agent Memory and Understand-Anything: overlap current memory/code graph and add infrastructure/LLM risk.
- Ponytail plugin/MCP: recurring cost for principles already owned locally.
- Headroom Desktop: interception/support uncertainty and overlapping bundle.
- n8n, agent-world, DeepSeek Harness: runtime/orchestration replacements, not missing workflow components.
- Large agent/example catalogs: references, not infrastructure.

A candidate needs a concrete missing capability, locality/privacy review, overlap analysis, bounded pilot, measurable
benefit, and removal path.

---

# 10. Python, Data, and ML

## 10.1 Environment ownership

Use one project dependency manager:

- existing `environment.yml`/`conda-lock.yml`: Conda;
- existing uv-managed `pyproject.toml`/`uv.lock`: uv;
- both: stop and resolve ownership;
- never alternate package operations between them.

The Configurator uses the explicitly selected or active interpreter; target
projects use their own declared environment. A personal Conda environment may be
convenient, but its name is not a portable repository contract.

## 10.2 Native editor tools

Prefer language-service references/implementations, semantic rename, diagnostics, selected interpreter state,
focused tests, and notebook execution over regex or model inference. Do not create an environment or install packages
until project ownership is known.

## 10.3 Data/experiment rules

- Use DuckDB for bounded analytics and direct CSV/Parquet queries.
- Prefer Polars expressions/lazy scans for suitable new pipelines; keep pandas at existing compatibility boundaries.
- Fit transforms only on training data inside validation folds.
- Use time-ordered splits for temporal prediction.
- Keep timestamps timezone-aware (normally UTC) until presentation.
- Preserve missingness/schema drift explicitly.
- Seed stochastic libraries and document nondeterminism.
- Compare against a named/versioned baseline.
- Move reusable notebook logic into importable modules.

Install the optional experiment runner only when the project needs run IDs, fingerprints, metrics, artifact
registration, and reproducible comparison.

---

# 11. Security and Reliability Checklist

1. Treat instructions, skills, agents, hooks, MCP configs, installers, and external repos as code.
2. Pin/review executable dependencies; do not switch to `latest` casually.
3. Keep credentials out of source and use secure input/environment mechanisms.
4. Give data tools restricted development/read-only access where possible.
5. Sandbox local MCP servers and retain tool confirmation.
6. Do not weaken host security globally to make a tool start.
7. Never delete a live MemPalace lock or bypass writer protection without a verified topology.
8. Keep plan/handoff paths inside the project and reject symlink traversal.
9. Re-preview if configuration or project state changes.
10. Preserve recovery evidence when rollback/cleanup is incomplete.
11. Do not commit, push, publish, deploy, or change unrelated work unless asked.
12. Verify sensitive claims in live source/runtime output, not old memory.
13. Treat a marketplace listing as discovery, not security or workflow-fit approval.

---

# 12. Practical Recipes

| Task | Recommended path |
|---|---|
| Quick answer/docs | Tier 0; no plan; no code tests; no proactive MCP unless current docs/history controls it |
| Bounded bug | Reproduce → locate controlling symbol/test → mini intent → focused fix/test → diff review |
| Large refactor | Verify graph root/freshness → trace callers/reuse → compact plan → coherent slices → one broad checkpoint |
| Security/migration | Tier 3 → one governed spec source → risk/rollback evidence → independent review → broad verification |
| New AI tool research | Define missing capability → primary sources → overlap/data/runtime/cost → verdict; do not install |
| Existing project | Configurator Analyze → smallest surface → identities/tools → Preview → safe Apply → doctor/checks |

---

# 13. Staying Current Without Tool Chasing

Monthly:

1. Review [VS Code release notes](https://code.visualstudio.com/updates) and the
   [GitHub Copilot changelog](https://github.blog/changelog/label/copilot/).
2. Check organization AI-credit usage/budgets.
3. Disable unused MCPs and always-on instructions.
4. Check MemPalace topology and codebase-memory freshness.

Quarterly:

1. Recheck billing/model documentation.
2. Review pinned tool releases and security issues.
3. Audit workflow/test/docs ratios.
4. Remove pilots that did not beat the baseline.
5. Revalidate Preview features such as Agent Hooks.

Adopt a tool because it solves a measured problem better than the current stack—not because it is new or popular.

---

# Research and Sources

Local evidence:

- [AI agent workflow assessment](docs/research/agent-workflow-assessment-2026-08-30.md)
- [Lean-code assessment](docs/research/lean-agent-code-assessment-2026-08-30.md)
- [Agency Agents and TencentDB assessment](docs/research/agency-agents-tencentdb-memory-assessment-2026-08-30.md)
- [Real-project audit](docs/research/real-project-workflow-audit-2026-08-30.md)
- [Memory routing/persistence assessment](docs/research/memory-routing-persistence-assessment-2026-08-30.md)
- [MemPalace lock assessment](docs/research/mempalace-lock-contention-assessment-2026-08-30.md)
- [Archify assessment](docs/research/archify-assessment-2026-08-30.md)
- [Awesome Copilot reassessment](docs/research/awesome-copilot-reassessment-2026-08-31.md)
- [Implemented Configurator plan](docs/plans/2026-08-30-final-workflow-configurator-changes.md)

Official references:

- [Copilot licenses and AI credits](https://docs.github.com/en/billing/concepts/product-billing/github-copilot-licenses)
- [Organization/enterprise usage billing](https://docs.github.com/en/copilot/concepts/billing/usage-based-billing-for-organizations-and-enterprises)
- [VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
- [VS Code Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [VS Code Agent Hooks](https://code.visualstudio.com/docs/agent-customization/hooks)
- [VS Code MCP servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers)
- [GitHub Copilot plugin creation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating)
- [Agent Plugins 1.0](https://agent-plugins.org/)
- [MemPalace 3.8 release](https://github.com/MemPalace/mempalace/releases/tag/v3.8.0)

**Last verified:** 2026-08-31. Pricing, model availability, Preview features, and third-party status are time-sensitive.
