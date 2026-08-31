# AI Agent Workflow Assessment

**Research date:** 2026-08-30
**Scope:** GitHub Copilot in VS Code and Copilot CLI, with the existing
MemPalace and codebase-memory workflow
**Status:** Research only. No candidate tool has been installed or adopted.
**Companion:** [Lean agent-generated code assessment](lean-agent-code-assessment-2026-08-30.md)

## Executive Conclusion

The current workflow has good components but the wrong enforcement boundary.
It asks the model to remember mandatory lifecycle behavior, while most of that
behavior lives in prose and manually invoked skills. More instructions will not
make this reliably strict; it will mostly add prompt cost.

The strongest direction is not a larger all-in-one agent framework. It is a
small layered system:

1. **Pre-execution Copilot hooks as the best available enforcement boundary**
   for the few rules that must be enforced. They are stronger than prompts, but
   not absolute: hook timeouts can fail open and VS Code support is currently
   preview/policy-dependent.
2. **Task and risk classification** that chooses the amount of planning,
   research, testing, and review.
3. **One optional spec layer**, selected by project/task rather than imposed
   everywhere.
4. **Better use of MemPalace and codebase-memory before adding another memory
   or repository-understanding product.**
5. **Affected-test selection and compressed command output** instead of full
   validation after every small edit.
6. **Measured pilots with an exit criterion**, not permanent adoption based on
   stars, demos, or claimed token-reduction percentages.

The best candidates for a controlled pilot are:

- **OpenSpec** for light, brownfield-first change specifications.
- **GitHub Spec Kit** for larger or governance-heavy work, not routine fixes.
- **rtk** for local command-output reduction; it has explicit Copilot hook
  support.
- **Ecosystem-native affected-test commands**, with `pytest-testmon` as an
  optional Python example when a suite is genuinely expensive.
- **Serena**, enabled only for symbol-heavy refactoring where existing VS Code
  language tools and codebase-memory are insufficient.

The supplied list also contains several tools that are impressive but not
relevant to this workflow. n8n, OpenWorker, DeepSeek Harness, Forge, and
agent-world are platforms or alternate runtimes, not missing Copilot
capabilities. Understand-Anything substantially overlaps with codebase-memory
while adding LLM cost and unresolved security concerns. The large configuration
collections are useful as pattern libraries, not as frameworks to install
wholesale.

## Method

The assessment used:

- the live repository and its current templates;
- the installed MemPalace 3.6.0 and codebase-memory-mcp 0.9.0 interfaces;
- live local health and index probes;
- primary project repositories, documentation, licenses, issues, and current
  metadata;
- official GitHub and VS Code documentation for Copilot hooks, agents, and
  skills.

Repository popularity was not treated as evidence of fit or quality. Several
very young projects have unusually large star counts. No candidate was executed
against a real project, so installation and runtime behavior still require a
scratch-repository pilot before adoption.

## Assessment Criteria

Each tool or pattern was judged against the actual problems reported:

1. **Protocol determinism:** enforced outside the model, or merely requested in
   a prompt?
2. **Token economics:** reduces total input/output/tool-result volume after
   accounting for its own schemas and generated artifacts?
3. **Adaptive effort:** can research, specs, tests, and reviews be skipped when
   they add no value?
4. **Brownfield fit:** can it enter an existing repository without overwriting
   or duplicating current guidance?
5. **Complementarity:** does it add a capability that MemPalace,
   codebase-memory, VS Code language services, or existing MCP tools do not?
6. **Locality and security:** what code/data leaves the machine, and what
   executable configuration is introduced?
7. **Operational cost:** services, runtimes, indexes, maintenance, and failure
   modes.
8. **Portability:** use of AGENTS.md, Agent Skills, MCP, Git, and other open
   conventions rather than a private runtime.

## Audit of the Current Setup

### 1. Protocol compliance is advisory, not deterministic

The workflow repeats mandatory MemPalace and code-intelligence steps in
[Copilot instructions](../../workflow_configurator/.github/copilot-instructions.md),
the [Planner](../../workflow_configurator/.github/agents/planner.agent.md), the
[Executor](../../workflow_configurator/.github/agents/executor.agent.md), the
[Reviewer](../../workflow_configurator/.github/agents/reviewer.agent.md), and several
skills. This improves the probability of compliance but cannot guarantee it.

The only implemented hook is an optional
[security PreToolUse hook](../../workflow_configurator/.github/hooks/security.json).
There is no lifecycle gate that checks whether a handoff, plan, or memory
checkpoint is current before the agent stops.

The test suite checks that strings such as `mempalace_status`,
`mempalace_diary_write`, and `check_index_coverage` occur in customization
files. It does not evaluate whether an agent actually calls those tools or
updates state. The current tests therefore establish template presence, not
protocol behavior.

This explains the observed need to remind the agent. It is a control-plane
problem, not a wording problem.

### 2. Validation is not proportional to the task

The current setup contains several unconditional or overly broad rules:

- the
  [lightweight Executor](../../templates/.github/agents/executor.agent.md)
  runs the fast tests after every plan step;
- the resume skill always runs the configured fast test command;
- final verification defaults to all configured project checks;
- the FastAPI profile asks for success, validation, and authorization tests for
  each endpoint without distinguishing a new endpoint from an unrelated edit;
- there is no explicit no-test path for research, documentation, analysis, or
  configuration inspection.

The full template is somewhat better because it asks for a focused check after
the first substantive edit, but it still lacks a task/risk matrix governing
when to create tests, when to rerun them, and when full validation is justified.

The repository's 24 tests currently occupy about 1,012 lines. They cover real
installer, security, doctor, and experiment behavior and run successfully, so
their existence is not itself a defect. The workflow defect is encouraging new
tests and repeated execution without first proving that behavior or risk
changed.

### 3. Project profiles are stack-based, not work-based

The installer defaults every project to Python plus data-science profiles.
There is an opt-out, but no discovery step or project-specific recommendation.
More importantly, the workflow has no first-class task categories such as:

- answer/research only;
- documentation;
- small safe code change;
- behavior or API change;
- data/migration/security/high-risk change;
- exploratory ML experiment;
- incident/debugging work.

Planner, Executor, and Reviewer consequently perform similar startup rituals
regardless of whether historical memory, graph analysis, research, or testing
is useful.

### 4. Existing-project integration is incomplete

The [installer](../../workflow_configurator/install.py) safely refuses to overwrite
files, but safety stops at refusal:

- any collision in AGENTS.md, `.github/`, workflow documents, or MCP settings
  aborts the install;
- `.gitignore` is the only file with merge behavior;
- the README tells the user to merge other files manually;
- there is no audit-only adoption report;
- there is no generated-vs-existing diff workspace;
- no installed-component manifest or template version is recorded;
- there is no upgrade, drift, rollback, or uninstall workflow;
- no stack detection proposes the minimum relevant profiles.

This is safe for a new repository but not an integration strategy for a mature
one.

### 5. MemPalace is underused and partly out of date

The current protocol uses status, diary reads, semantic search, diary writes,
drawers, and generic knowledge-graph updates. MemPalace 3.6.0 exposes more
useful primitives:

- project-scoped `wake-up` context;
- an atomic `mempalace_checkpoint` operation that semantic-deduplicates
  durable items and writes the diary in one call;
- `kg_supersede` for an atomic replacement of a single-valued fact;
- sync/prune, repair status, taxonomy, hallways, tunnels, and project mining;
- silent automatic checkpoints through supported harness hooks.

The template currently says to invalidate an old fact and then add the new
one. The installed API recommends `kg_supersede` because separate operations
can overlap at the boundary.

The current workflow calls status, diary read, and search routinely, but never
uses `wake-up`. The local CLI command
`mempalace wake-up --wing adaptive_workflow_configurator` produced about 175 tokens and recovered
the essential prior decision. `wake-up` is not exposed by the active MemPalace
MCP surface, so using it from Copilot would require a small reviewed CLI skill
or an MCP update. Targeted search should follow only when the task depends on
older decisions; it should not be an automatic multi-result search for every
task.

The built-in MemPalace automatic hook supports Claude Code and Codex, not
Copilot. Copilot therefore needs a small native-hook adapter if automatic
checkpointing is required. Instructions alone cannot provide this.

Local health observed during this research:

- MemPalace version 3.6.0, Chroma backend;
- about 175 MB on disk;
- 12,858 drawer vectors and 774 closet vectors;
- SQLite and HNSW counts matched, and live searches worked;
- the palace has no recorded embedder identity, which produces a warning;
- no recent automatic checkpoint was reported before this research;
- the `adaptive_workflow_configurator` wing had only decisions and diary rooms, with no explicit
  hallway or tunnel records.

The low number of project memories is not automatically a problem. MemPalace
should store expensive-to-reconstruct decisions and synthesis, not duplicate
the live code graph.

Two risk caveats matter:

- [Issue #39](https://github.com/MemPalace/mempalace/issues/39) independently
  reproduced strong raw semantic retrieval but found that the published raw
  benchmark bypassed palace structure and that AAAK/room modes scored below
  raw retrieval in that test. Critical technical facts should remain verbatim;
  AAAK should not be assumed lossless.
- [Issue #1329](https://github.com/MemPalace/mempalace/issues/1329) remains open
  and reports severe Chroma/HNSW growth and stop-hook crashes during automated
  transcript ingestion and repeated upserts. Several comments identify
  concurrent writers as a suspected contributor, not a proven sole cause. It
  is a user-reported failure family, not proof that every palace is affected.
  The current local palace is healthy, but size, writer concurrency, real
  search, and repair status should be monitored before increasing automatic
  ingestion.

### 6. codebase-memory is underused and the documented API is mismatched

Before this research, this repository was not indexed. The installed
configuration had `auto_index=false` and `auto_watch=true`, so watching could
not help until an initial index existed.

A moderate local index now contains 307 nodes and 591 edges. It immediately
provided architecture, call paths, complexity signals, and test relationships
without broad source reads.

However:

- codebase-memory-mcp 0.9.0 advertises `list_projects`, `index_status`, and
  `detect_changes` in its CLI, but this VS Code MCP session did not expose them;
- the template requires `check_index_coverage`, which is absent from both the
  exposed MCP surface and the installed 0.9.0 CLI;
- important implementation under hidden `.github/.../scripts` directories was
  excluded from this index, including the project doctor, experiment tooling,
  and security guard;
- the template mentions only a subset of available value: semantic graph
  search, clusters, complexity queries, data-flow tracing, cross-service
  tracing, and diff impact are not incorporated into task routing.

The immediate priority is to align the installed server, VS Code's cached tool
surface, index policy, and documentation. Adding another repository graph
before fixing this would create duplication rather than better context.

Quantitative token and accuracy claims in the codebase-memory README/paper were
not independently reproduced in this research. The demonstrated local benefit
is narrower but real: structural queries returned relevant symbols and paths
with much less source text than broad file reads.

### 7. Observability exists in documentation, not in the operating loop

The current [observability guide](../../workflow_configurator/docs/AGENT_OBSERVABILITY.md)
already describes Copilot context/usage views, Cache Explorer, credit ceilings,
and metadata-only OpenTelemetry. There is no baseline report or acceptance
threshold that turns those signals into decisions.

A new tool should not be adopted unless a short pilot measures at least:

- median input and output tokens per task;
- tool-result characters/tokens;
- number of tool calls and repeated file reads;
- number of test commands and wall time;
- protocol completion rate;
- defect/rework rate;
- setup and maintenance time.

Without this, token-reduction claims simply create another rabbit hole.

## Assessment of the Supplied Projects

| Project | Actual category | Fit | Verdict |
|---|---|---:|---|
| `andrewyng/openworker` | Desktop AI coworker/runtime | Low | Watch |
| `github/spec-kit` | Spec-driven workflow generator | High, conditional | Pilot |
| `n8n-io/n8n` | General workflow automation server | Low for coding core | Reject for core |
| `agent-world.dev` | Agent-state visualizer for another runtime | None | Reject |
| `microsoft/skill-recorder` | Human GUI workflow recorder | Low | Watch |
| `deepseek-ai/deepseek-harness` | Alternate agent runtime | Low | Reject for now |
| `gglucass/headroom-desktop` | Paid proxy/desktop wrapper | Low for Copilot | Reject as bundle |
| `tailcallhq/forgecode` | Alternate coding-agent CLI | Medium as reference | Watch |
| `Egonex-AI/Understand-Anything` | LLM-generated code knowledge graph | Low/duplicative | Reject as dependency |
| `affaan-m/ecc` | Large agent configuration framework | Medium as pattern source | Mine patterns only |
| `ashishpatel26/500-AI-Agents-Projects` | Example catalog | None as infrastructure | Reference only |
| `fcakyon/claude-codex-settings` | Cross-agent config/plugin collection | Medium as pattern source | Mine patterns only |

### OpenWorker

[Repository](https://github.com/andrewyng/openworker)

OpenWorker is a new desktop coworker application for general deliverables,
connectors, teams, memory, and governed autonomy. Its earned-autonomy and audit
trail are useful design references. It is not a repository-native Copilot
extension and its emerging MCP surface is not yet a documented integration
contract. Running it would introduce another agent runtime and memory domain.

**Decision:** watch the governance patterns; do not add it to the coding
workflow.

### GitHub Spec Kit

[Repository](https://github.com/github/spec-kit) ·
[Spec-driven development model](https://github.com/github/spec-kit/blob/main/docs/concepts/sdd.md) ·
[Presets](https://github.com/github/spec-kit/blob/main/docs/reference/presets.md) ·
[Existing-project evolution](https://github.com/github/spec-kit/blob/main/docs/guides/evolving-specs.md)

Spec Kit is the strongest supplied candidate. It creates durable specification,
plan, task, analysis, and implementation artifacts; supports Copilot; and now
has presets/extensions for adapting templates and terminology. It explicitly
recognizes iterative brownfield enhancement.

Its weakness is ceremony. Running the full specify/clarify/plan/tasks/analyze/
implement/converge chain for routine fixes would recreate the exact monotonic
behavior being criticized. It also introduces another plan/spec source of truth
alongside `docs/PLAN.template.md` and `docs/HANDOFF.md`.

**Decision:** pilot only for large, ambiguous, multi-session, regulated, or
cross-team work. If adopted, it must replace the current plan artifact for
those tasks rather than being stacked on top of it.

### n8n

[Repository](https://github.com/n8n-io/n8n) ·
[License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)

n8n is a mature automation platform with broad integrations and MCP/AI nodes.
It is excellent for business workflows, scheduled jobs, approvals, and
cross-system automation. It is a persistent service with credentials, state,
and a source-available license; it does not solve Copilot protocol adherence,
repository context, or test proportionality.

**Decision:** reject for the coding-agent core. Reconsider separately only when
there is a real cross-application automation requirement.

### agent-world.dev

[Site](https://agent-world.dev/)

The researched implementation visualizes state for a different agent runtime.
It is a presentation layer, not enforcement, memory, code intelligence, or
token optimization. The associated project appeared stale and lacked a clear
license/security posture.

**Decision:** reject.

### Microsoft Skill Recorder

[Repository](https://github.com/microsoft/skill-recorder)

Skill Recorder records a human completing a desktop/UI task, then uses Copilot
CLI to infer steps and produce a skill or automation. Local recording is a
positive privacy design, but analysis can send screenshots, clipboard
previews, and event data to GitHub after explicit user action.

It does not observe an agent session and infer better coding protocol. It is
appropriate for repetitive GUI operations, not for fixing handoff/memory/test
discipline.

**Decision:** watch. Use only if human UI automation becomes a concrete need.

### DeepSeek Harness

[Repository](https://github.com/deepseek-ai/deepseek-harness)

DeepSeek Harness is a new plugin-oriented agent runtime with its own event log,
profiles, bundles, and extension lifecycle. Its architecture is relevant to
hard state-machine design, but it is a replacement for Copilot's runtime, not a
small integration. The project describes itself as developer preview and not
security-audited.

**Decision:** reject for now. Re-evaluate only after maturity, audit, and a
documented interoperability seam justify replacing the current driver.

### Headroom Desktop

[Desktop repository](https://github.com/gglucass/headroom-desktop) ·
[Open compression core](https://github.com/chopratejas/headroom)

Headroom Desktop is a paid account-backed desktop wrapper around a local proxy
and several open components. Its compression pipeline can reduce stale text,
JSON, and tool-output volume for supported provider-driven clients, but live
code is intentionally compressed conservatively. Direct Copilot interception
was not established.

The useful pieces can be evaluated independently: the open Headroom core and
rtk. Installing the desktop bundle would also duplicate codebase-memory and
optionally Serena.

**Decision:** reject the desktop bundle. Consider only its open components in
isolated measurements.

### Forge

[Repository](https://github.com/tailcallhq/forgecode)

Forge is a credible Rust coding-agent CLI with planning/research agents,
AGENTS.md and skill conventions, MCP, compaction, model routing, and usage
statistics. Those patterns validate much of the current design.

It is nevertheless a second agent driver with a separate conversation store,
configuration, skills, and model-provider path. Its workspace semantic search
can send code to a hosted Forge endpoint unless self-hosted.

**Decision:** watch and borrow UX ideas. Do not run it in parallel on the same
repositories unless it has a deliberately isolated use case and memory policy.

### Understand-Anything

[Repository](https://github.com/Egonex-AI/Understand-Anything) ·
[Command/prompt-injection report](https://github.com/Egonex-AI/Understand-Anything/issues/481) ·
[Malicious-PR report](https://github.com/Egonex-AI/Understand-Anything/issues/432)

Understand-Anything combines deterministic parsing with a multi-agent LLM pass
to create a persistent JSON knowledge graph and visual onboarding experience.
The viewer can be local, but the initial semantic build uses the configured LLM
and can consume substantial tokens; local-only generation requires an explicit
local model.

It overlaps strongly with codebase-memory architecture and with MemPalace
durable synthesis. The project has no end-to-end token/accuracy benchmark for
its central LLM pipeline, and users have reported high token use. The open
security report identifies unsafe shell quoting and indirect prompt-injection
paths in skill instructions.

**Decision:** do not install as a live dependency. At most, evaluate it later
as a one-time onboarding-document generator in a disposable clone, after the
security issues are resolved.

### Everything Claude Code (ECC)

[Repository](https://github.com/affaan-m/ecc)

ECC is a very large collection of agents, skills, hooks, memory, security, and
context controls. Its Copilot documentation was stale during this review and
understated Copilot's current agent/hook support. Installing the full collection
would add exactly the surface area and token-management problem this project is
trying to reduce. Its memory vault would duplicate MemPalace.

Useful ideas include strategic compaction at semantic breakpoints, explicit
context budgets, destructive-command gates, and scanning executable agent
configuration.

**Decision:** treat as a pattern library. Do not install wholesale.

### 500 AI Agents Projects

[Repository](https://github.com/ashishpatel26/500-AI-Agents-Projects)

This is a discovery catalog and example collection, not a runtime or coherent
quality/security boundary.

**Decision:** keep as a reference list only. Vet any linked project from
scratch.

### claude-codex-settings

[Repository](https://github.com/fcakyon/claude-codex-settings)

This active configuration collection demonstrates shared AGENTS.md-style
guidance, guard hooks, compact output styles, and compaction preservation.
Many components are Claude/Codex-specific rather than directly portable to
Copilot.

**Decision:** cherry-pick concepts after translating them to current Copilot
hook contracts. Do not install the whole marketplace into this workflow.

## Additional Tools and Patterns Worth Considering

### OpenSpec: strongest first brownfield pilot

[Repository](https://github.com/Fission-AI/OpenSpec) ·
[Existing-project guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs/existing-projects.md) ·
[Customization](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md)

OpenSpec is explicitly delta-first: an existing repository documents only the
behavior being changed, then accumulates specs through real work. It does not
ask for a whole-codebase documentation pass. It supports project context and
custom schemas.

This is a closer match than a mandatory full Spec Kit flow for the reported
problems. It still creates another artifact hierarchy, so a pilot must decide
whether OpenSpec replaces the existing plan/handoff artifacts for the selected
task.

**Verdict:** first spec-workflow pilot.

### BMAD Method: useful right-sizing model, potentially too large

[Repository](https://github.com/bmad-code-org/BMAD-METHOD) ·
[Existing-codebase guide](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/existing-codebases/start-in-an-existing-codebase.md)

BMAD has one especially relevant principle: small changes go directly to a
build workflow, multi-session changes get a spec, and large initiatives get a
full planning path. It also tells existing projects not to duplicate knowledge
that agents can obtain from code.

That right-sizing model is worth borrowing. The complete multi-agent method is
larger than necessary and may increase token use.

**Verdict:** design reference or scratch bake-off, not an initial adoption.

### Native Copilot hooks: highest-value enforcement mechanism

[GitHub hook reference](https://docs.github.com/en/copilot/reference/hooks-reference) ·
[VS Code agent hooks](https://code.visualstudio.com/docs/agent-customization/hooks)

Only pre-execution hooks can prevent an action. Event names differ by surface:
VS Code uses `PreToolUse` and `Stop`; Copilot CLI/cloud documentation uses
`preToolUse`, `agentStop`, and `sessionEnd`.

- `preToolUse` can allow, deny, ask, and in supported surfaces update tool
  input;
- `permissionRequest` can allow/deny in Copilot CLI but does not apply to the
  cloud agent or VS Code.

The VS Code `Stop` event and CLI/cloud `agentStop` event can force another turn
so the agent can repair a missing handoff or checkpoint, but they cannot undo
an action and Copilot limits repeated continuations. `sessionEnd` is
observational and cannot guarantee a final write.

Important limitations:

- command-hook crashes/non-zero exits can fail closed, but hook timeouts fail
  open;
- HTTP hook failures generally fail open;
- cloud-agent and VS Code/CLI event/config support differs;
- VS Code hooks are a preview surface and can be disabled by organization
  policy.

The practical conclusion is to enforce a few cheap, fast invariants, not to put
the entire methodology into a hook. A local state ledger and a deterministic
script are sufficient; OPA or another policy server would be premature.

**Verdict:** adopt as the control-plane direction.

### rtk: best concrete output-reduction pilot

[Repository](https://github.com/rtk-ai/rtk) ·
[Copilot hook integration](https://github.com/rtk-ai/rtk/blob/develop/hooks/copilot/README.md)

rtk is a local Rust command proxy that reformats common command output before
the model receives it. Its Copilot hook handles both VS Code's snake_case input
and Copilot CLI's camelCase input. In VS Code it can transparently rewrite tool
input; in Copilot CLI it denies the original call with a compressed-command
suggestion because that surface cannot update the input in the same way.

Its advertised percentages refer to command-output volume, not the total bill.
The only meaningful acceptance test is an A/B comparison on this user's real
Git/test/build commands.

**Verdict:** pilot in a scratch workspace with telemetry and an easy rollback.

### Affected-test selection: prefer native project mechanisms

Use these only where the project already has the corresponding ecosystem:

- Python: [pytest-testmon](https://github.com/tarpas/pytest-testmon) performs
  coverage/dependency-based selection; it is heuristic and should fall back to
  the full relevant suite at a checkpoint.
- Python: [pytest-picked](https://github.com/anapaulagomes/pytest-picked)
  selects changed test files, not unchanged tests affected by changed source;
  it is not a substitute for test impact analysis.
- Jest:
  [`--onlyChanged`, `--changedSince`, and `--findRelatedTests`](https://jestjs.io/docs/cli).
- Vitest:
  [`--changed`](https://github.com/vitest-dev/vitest/blob/main/docs/guide/cli-generated.md).
- Nx:
  [`nx affected -t test`](https://nx.dev/docs/features/ci-features/affected).
- Turborepo:
  [`--affected` and Git-range filters](https://turborepo.dev/docs/reference/run).
- Bazel:
  [target-determinator](https://github.com/bazel-contrib/target-determinator)
  or native reverse-dependency queries.

These commands do not decide when tests are valuable. The workflow still needs
an explicit validation matrix.

**Verdict:** adopt per project only when the existing suite cost justifies it.

### Serena: complementary, but enable only for relevant work

[Repository](https://github.com/oraios/serena) ·
[Client configuration](https://github.com/oraios/serena/blob/main/docs/02-usage/030_clients.md)

Serena adds local language-server-backed symbol navigation and editing. This is
different from codebase-memory's persistent architecture/call graph and can be
valuable for rename/refactor operations.

It also adds MCP tool schemas and language-server setup. VS Code already has
language intelligence, so the benefit must be demonstrated rather than
assumed.

**Verdict:** workspace-scoped pilot for a large refactor; keep disabled for
research, docs, and simple edits.

### Aider repo map: borrow the ranking idea

[Design description](https://aider.chat/2023/10/22/repomap.html)

Aider builds a tree-sitter tag graph and ranks relevant definitions with a
PageRank-like algorithm under a token budget. It is a useful design reference
for prioritizing graph context. Installing Aider as a second coding runtime is
not necessary.

**Verdict:** design reference only.

### Agent customization evaluation and metadata-only telemetry

The existing setup already mentions VS Code's Chat Customizations Evaluations/
Waza path and OpenTelemetry. These are more valuable than another prompt pack:

- behavior evaluations can test whether a skill selects the intended task tier
  and updates required state;
- local metadata-only telemetry can measure model, tokens, cache behavior,
  tool calls, durations, compaction, and failures;
- full prompt/tool content capture should remain disabled.

**Verdict:** operationalize the existing guidance before purchasing or adding a
proxy platform.

## Recommended Adaptive Workflow Model

This is a research conclusion, not an implementation performed in this pass.

| Tier | Typical work | Plan/spec | Research | Test creation | Validation |
|---|---|---|---|---|---|
| 0 | Answer, research, explanation, docs | None | Only as required | None | Links, format, or observable doc check |
| 1 | Local, low-risk edit | Short intent in chat | Normally none | Only for a real regression/contract | Smallest existing affected check |
| 2 | Behavior change or several coupled files | Bounded plan | Targeted unknowns | Focused behavior/contract tests | Affected tests + targeted lint/typecheck |
| 3 | Auth, money, migration, destructive data, concurrency, public API, ML leakage | Approved spec/plan | Required evidence | Required risk-focused tests | Relevant full suite + independent review |
| 4 | Large initiative, ambiguous product change, multi-team/regulatory work | Spec Kit/OpenSpec-style governed artifacts | Dedicated research | Planned test strategy | Staged gates, full release evidence |

Rules that prevent test bloat:

1. Documentation and research do not create or run code tests by default.
2. A refactor does not require new tests when existing tests already prove the
   unchanged contract.
3. A bug fix normally adds one focused regression test, not a broad test
   matrix.
4. New tests are justified by changed observable behavior or a named risk.
5. Run the smallest affected check during implementation.
6. Run broader checks at a logical checkpoint, before review/commit/PR, or for a
   high-risk change—not after every edit.
7. Successful test output should be summarized outside the main model context;
   failure details should remain available on demand.

## Recommended Brownfield Integration Model

Any future installer revision should support an adoption lifecycle:

1. **Audit:** inspect existing AGENTS.md, instructions, skills, hooks, MCP,
   manifests, commands, languages, and generated paths without editing.
2. **Recommend:** propose the minimum base plus optional project/task profiles;
   require user approval.
3. **Stage:** render candidate files to a temporary review area and show
   semantic or three-way diffs against existing guidance.
4. **Merge:** preserve project facts and nearest-scope instructions; never
   replace an existing file blindly.
5. **Record:** write a small manifest with template version, selected
   components, source hashes, and user-owned sections.
6. **Validate:** run discovery/behavior checks appropriate to installed
   components, not the project's whole test suite.
7. **Upgrade:** support dry-run drift reports and component-level updates.
8. **Rollback/uninstall:** remove only files/blocks proven to be installer-owned.

Start with the smallest base. Python, data-science, FastAPI, React, experiments,
database MCPs, and heavy spec workflows should all be opt-in after detection,
not global defaults.

## Reported-Problem Crosswalk

| Reported problem | Research-supported answer |
|---|---|
| Protocol is not followed strictly | Move a small set of invariants from prose to `preToolUse`/`agentStop` checks, retain human review, and evaluate behavior rather than checking for instruction strings. |
| Excessive test creation and repeated testing | Use the task/risk tiers, require a named changed behavior or risk before adding tests, select affected tests, summarize successful output, and reserve broad suites for checkpoints/high-risk work. |
| Same behavior for every project/task | Detect project capabilities, route by task and risk, and load stack/procedure skills only when relevant. |
| No existing-project integration path | Add audit, recommend, staged diff/merge, ownership manifest, upgrade, and rollback phases; pilot a delta-first spec approach rather than documenting the whole codebase. |
| MemPalace/codebase-memory not fully used | Fix the current API/index mismatch first; use project-scoped wake-up, atomic checkpoints, temporal fact supersession, targeted retrieval, graph impact/data-flow/complexity queries, and measured health/coverage checks before adding another memory or graph product. |

## Tool-Rationalization Rules

To prevent the research process itself from becoming the next rabbit hole:

1. One source of truth for each concern:
   - project instructions: AGENTS.md plus scoped Copilot instructions;
   - active work state: one handoff/plan or one selected spec system;
   - durable synthesis: MemPalace;
   - live code structure: codebase-memory plus language services;
   - current truth: Git and the working tree.
2. Do not run two memory vaults, two repository graphs, or two agent drivers for
   the same task without a measured reason.
3. Keep MCP servers disabled unless the current task needs them. DuckDB,
   Postgres, MarkItDown, Hugging Face, Context7, GitHub, Azure, and Jupyter remain
   useful task tools, not mandatory global context.
4. A candidate must beat the baseline over several real tasks, not one demo.
5. Reject tools that save model tokens but add larger maintenance, security, or
   artifact costs.
6. Review executable skills, hooks, MCP definitions, and installers as code.

## Prioritized Research Verdict

### Keep and improve first

1. Native Copilot instructions, scoped instructions, agents, skills, and hooks.
2. MemPalace, with corrected lifecycle use and health safeguards.
3. codebase-memory, after aligning version/tool exposure and index coverage.
4. Existing context exclusions, tool curation, Cache Explorer, and
   metadata-only observability.

### Pilot in scratch repositories

1. OpenSpec for one real brownfield feature.
2. rtk for command-output reduction under Copilot.
3. Spec Kit for one genuinely complex/high-governance task.
4. Affected-test selection in a project whose test suite is actually costly.
5. Serena for one symbol-heavy refactor.

### Borrow patterns without installing the framework

- BMAD's task-size routing and brownfield discipline.
- ECC's context-budget and strategic-compaction ideas.
- claude-codex-settings' guard and compact-output patterns.
- OpenWorker's earned-autonomy/audit concepts.
- Aider's token-budgeted repository-map ranking.

### Watch

- Microsoft Skill Recorder for human UI automation.
- Forge as an alternate CLI if Copilot is ever deliberately replaced for a
  bounded use case.
- OpenWorker's documented interoperability and maturity.
- Headroom's open compression core for non-Copilot clients.

### Reject for the current workflow

- n8n as coding-agent infrastructure.
- agent-world.dev.
- DeepSeek Harness in its current preview state.
- Understand-Anything as a persistent live dependency.
- 500-AI-Agents-Projects as infrastructure.
- full ECC or claude-codex-settings installation.
- simultaneous Spec Kit + OpenSpec + BMAD adoption.

## Evidence Limits

- Candidate tools were assessed statically and were not installed.
- Repository activity and issue state are a snapshot and must be rechecked
  before a pilot.
- Vendor token/accuracy claims were not accepted as facts without a reproducible
  independent result.
- Open issue reports establish credible risk, not universal failure.
- Copilot hook behavior differs among VS Code, CLI, and cloud agent and remains
  partly preview/policy-dependent.
- The shell used for this assessment did not have a `copilot` executable, so
  CLI-specific integration was not tested locally.

## Primary Sources

### Platform and standards

- [GitHub Copilot hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
- [GitHub Copilot customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)
- [VS Code agent hooks](https://code.visualstudio.com/docs/agent-customization/hooks)
- [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [GitHub Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [AGENTS.md](https://agents.md/)
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)

### Supplied projects

- [OpenWorker](https://github.com/andrewyng/openworker)
- [Spec Kit](https://github.com/github/spec-kit)
- [n8n](https://github.com/n8n-io/n8n)
- [agent-world.dev](https://agent-world.dev/)
- [Microsoft Skill Recorder](https://github.com/microsoft/skill-recorder)
- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
- [Headroom Desktop](https://github.com/gglucass/headroom-desktop)
- [Forge](https://github.com/tailcallhq/forgecode)
- [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything)
- [Everything Claude Code](https://github.com/affaan-m/ecc)
- [500 AI Agents Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects)
- [claude-codex-settings](https://github.com/fcakyon/claude-codex-settings)

### Additional candidates

- [OpenSpec](https://github.com/Fission-AI/OpenSpec)
- [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD)
- [rtk](https://github.com/rtk-ai/rtk)
- [Serena](https://github.com/oraios/serena)
- [Aider repository map](https://aider.chat/2023/10/22/repomap.html)
- [pytest-testmon](https://github.com/tarpas/pytest-testmon)
- [pytest-picked](https://github.com/anapaulagomes/pytest-picked)
- [Bazel target-determinator](https://github.com/bazel-contrib/target-determinator)

### Existing local stack

- [MemPalace](https://github.com/MemPalace/mempalace)
- [MemPalace independent benchmark discussion](https://github.com/MemPalace/mempalace/issues/39)
- [MemPalace Chroma/HNSW growth report](https://github.com/MemPalace/mempalace/issues/1329)
- [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)
