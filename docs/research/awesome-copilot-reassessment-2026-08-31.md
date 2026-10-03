# Awesome Copilot Reassessment

**Research date:** 2026-08-31

**Repository:** [github/awesome-copilot](https://github.com/github/awesome-copilot)

**Reviewed revision:** [`f11a4e4`](https://github.com/github/awesome-copilot/commit/f11a4e441c5ff061b4f8ae37952be8c602e4034e)

**Status:** Research only. No Awesome Copilot agent, skill, hook, plugin, or
external service was installed.

**Implementation follow-up:** Workflow Configurator 3.1 implements the compact
evidence-level guidance, redacted MCP audit, metadata-only daily delta check,
review-brief export, and a no-overwrite local specialist-plugin export. The
updater never downloads asset bodies or promotes upstream behavior
automatically.

## Executive Decision

Awesome Copilot is more relevant to this workflow than it was during the first
tool-landscape review, primarily because it is now both:

1. a large, active catalog of Copilot-native customization; and
2. a default plugin marketplace using the emerging Agent Plugins packaging
   standard.

It should still be treated as a **curated upstream source, not a bundle to
install wholesale**.

The strongest opportunities are:

| Opportunity | Decision | Why |
|---|---|---|
| `codebase-memory-mcp` evidence levels | **Adapt into existing guidance** | Scout/Verify/Auditor levels make graph effort proportional to the claim |
| MCP configuration security audit | **Implement a small local read-only check** | Complements the existing threat model with concrete configuration findings |
| Agent Plugin packaging | **Run an optional local pilot** | Could install generic capabilities once instead of copying them into every repository |
| Agent supply-chain checks | **Borrow when external import exists** | Hashes and pinned identities are useful, but no import path currently needs them |
| Agent Skill Stack | **Borrow selection/install patterns only** | Good smallest-stack principles, but the full skill adds about 68 KB and several scripts |
| Secret/license hooks | **Guidance or project-native checks only** | Always-on Bash session hooks would recreate monotonic overhead |

No additional agent roster, memory layer, planning system, codebase
documentation generator, TDD framework, or always-on hook should be added.

## What Changed

At the reviewed revision, the repository contained:

| Category | Count |
|---|---:|
| Custom agents | 221 |
| Instruction files | 192 |
| Agent Skills | 415 |
| Local plugin manifests | 98 |
| Hook packages | 8 |
| Agentic workflow files | 8 |

These are path-based snapshot counts, not a claim that every item is distinct,
compatible, or equally maintained.

The more important change is distribution:

- Awesome Copilot documents `awesome-copilot` as a default marketplace in
  Copilot CLI and VS Code.
- A plugin can bundle agents, skills, hooks, and MCP configuration.
- Community plugins are updated explicitly rather than silently.
- Individual plugin components can be disabled.
- A local plugin directory can be tested before marketplace publication.
- Team marketplace registrations can be pinned to a Git commit.
- Agent Plugins 1.0 defines a portable core for skills and MCP servers, with
  reverse-domain namespaces for client-specific capabilities.

This creates a credible way to separate **generic reusable capability** from
**repository-specific policy and state**.

## Assessment Method

The review used the pinned repository snapshot, repository contribution and
validation rules, individual asset contents and history, official GitHub
plugin documentation, and the Agent Plugins 1.0 specification.

Candidates were judged against the workflow's actual problems:

1. Does it reduce repeated context or repository scaffolding?
2. Does it make effort proportional to task risk?
3. Does it complement rather than duplicate MemPalace, codebase-memory, native
   language tools, and the Configurator?
4. Can it be reviewed before installation or execution?
5. Does it preserve project-specific memory and code identities?
6. Is its runtime, security, and maintenance cost bounded?
7. Can it be disabled or removed cleanly?

Marketplace presence, catalog size, and popularity were not treated as proof of
quality.

## Catalog Quality Boundary

Awesome Copilot has positive governance signals:

- MIT license for repository content;
- active maintenance;
- contribution rules rejecting malicious, security-weakening, and
  unreviewed remote-source content;
- schema/frontmatter validation for skills and plugins;
- pinned GitHub Actions in the sampled validation workflow;
- a documented external-plugin review process.

The automated skill validator checks metadata, directory/name consistency, and
asset size. Plugin validation checks manifest/schema structure and repository
composition. These are useful supply-chain and packaging controls, but they do
not establish that a prompt is proportionate, non-duplicative, or appropriate
for this workflow.

That distinction matters because the same catalog also contains:

- a 100%-coverage-oriented pytest skill;
- refactoring workflows with large mandatory plans;
- context workflows that block implementation pending additional artifacts;
- session-end hooks that run after every session;
- large persona and orchestration packages.

Every item remains a candidate requiring local fit and security review.

## 1. Codebase-Memory Evidence Levels

### Verified useful behavior

The
[`codebase-memory-mcp` skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/codebase-memory-mcp/SKILL.md)
has a precise trigger:

- use the graph for unfamiliar architecture, symbols, relationships, impact,
  data flow, or explicit codebase-memory work;
- skip it for a supplied known file, tiny one-file check, exact literal,
  configuration value, error string, or non-code text.

It then separates claims into:

- **Scout:** positive orientation only; no exhaustive or absence claims;
- **Verify:** normal task work with relevant freshness, source, trace, and
  result-completeness checks;
- **Auditor:** negative, exhaustive, security, dead-code, boundary, and
  complete-impact claims with bounded scope and stronger coverage evidence.

This directly addresses two observed problems:

1. graph tools are sometimes underused for structural work; and
2. expensive discovery is sometimes used for simple known-file work.

The skill also correctly treats graph output as an accelerator rather than the
source of current implementation truth, requires canonical-root matching, and
requires explicit approval for graph mutation.

### Why it must not be copied verbatim

The reviewed skill targets a newer/different tool surface than the active MCP
interface in this environment. It assumes operations or parameters such as:

- `list_projects`;
- `index_status`;
- `detect_changes`;
- `check_index_coverage`;
- trace cursors and coverage pagination;
- missed-graph queries.

The active interface exposes architecture, graph/code search, snippets,
queries, traces, schema inspection, and indexing, but not every operation above.
Unconditional adoption would instruct agents to call tools that do not exist.

### Recommended integration

Add the three evidence levels to the existing generated code-intelligence
guidance. Do not add another always-loaded document or duplicate skill.

The local version should say:

1. capability-detect before naming a tool;
2. verify the indexed project root when the active surface permits it;
3. use Scout for bounded positive orientation;
4. use Verify for ordinary implementation and impact work;
5. use Auditor only for negative/exhaustive/security claims;
6. downgrade the claim when freshness, coverage, or pagination cannot be
   established;
7. always inspect relevant live source before editing.

This is a **core adaptation**, not a new optional dependency. It should reduce
tool calls on simple work while improving rigor where an absolute claim would
otherwise be unsafe.

## 2. MCP Configuration Security Audit

### Verified useful behavior

The
[`mcp-security-audit` skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/mcp-security-audit/SKILL.md)
checks for:

- plaintext credentials;
- shell interpolation/chaining patterns;
- `@latest` package references;
- interactive `npx` use;
- servers outside an approved set.

This fills a real gap. The Configurator already documents MCP threat models and
generates reviewed configuration, but Analyze does not currently turn the
effective configuration into concrete security findings.

### Why it must not be copied verbatim

The upstream examples assume `.mcp.json` with an `mcpServers` object. This
workflow generates VS Code `.vscode/mcp.json` with:

- a `servers` object;
- secure input declarations;
- `sandboxEnabled` for selected local stdio servers;
- user-profile versus workspace-scope rules.

The upstream version check only flags `@latest`; it does not establish that
every executable or package is reproducibly pinned. Its shell-pattern scan also
does not distinguish an inert argument passed directly to a process from text
interpreted by `sh -c`, `bash -c`, PowerShell, or another shell.

Copying it would therefore create schema blind spots and avoidable false
positives.

### Recommended integration

Implement a small, cross-platform, read-only Configurator Analyze check that
runs only when MCP configuration exists or is being generated. It should:

1. understand VS Code `servers` and secure `inputs`;
2. report possible plaintext secrets without echoing secret values;
3. distinguish direct process arguments from explicit shell wrappers;
4. identify floating package versions and unreviewed download-on-start
   commands;
5. report duplicate user/workspace registration;
6. verify expected sandbox settings for local stdio servers;
7. compare selected servers with the reviewed Configurator catalog;
8. treat regex matches as review findings, not proof of exploitation.

This complements
[`MCP_SECURITY.md`](../../workflow_configurator/docs/MCP_SECURITY.md); it does not replace
the threat model or normal approval UI.

## 3. Agent Plugins as a Distribution Layer

### Verified capabilities

Official GitHub documentation says a Copilot CLI plugin can contain agents,
skills, hooks, and MCP configuration. Agent Plugins 1.0 standardizes the
portable skills/MCP portion, while client namespaces can carry host-specific
components.

The reviewed Awesome Copilot documentation also records:

- marketplace discovery in Copilot CLI and VS Code;
- local plugin loading/testing;
- explicit community-plugin updates;
- component-level enable/disable controls;
- Git-SHA pinning for additional team marketplaces;
- repository-local configuration taking precedence on conflict.

### Fit with this workflow

Generic capabilities currently copied into many repositories are candidates
for a small local plugin:

- accessibility, AppSec, tool, research, and lean-code reviewers;
- a compact codebase-memory evidence protocol;
- other truly generic manually invoked skills.

The following must remain project-local:

- `AGENTS.md` and essential repository instructions;
- task-tier and project policy;
- MemPalace wing and codebase-memory project identity;
- active plan, handoff, and task state;
- project commands and environment ownership;
- project-specific hooks, MCP paths, exclusions, and doctor checks;
- the generated file contract and recovery evidence.

This split could reduce repeated files and make generic capabilities versioned
once. It does **not** automatically reduce prompt tokens: installed component
metadata still participates in discovery, and an overfilled plugin would merely
move catalog noise out of the repository.

Plugin support also does not replace repository configuration for every host.
The reviewed Awesome Copilot documentation says GitHub.com's coding agent does
not directly consume installed CLI/VS Code plugins.

### Recommended pilot

Treat plugin packaging as optional and experimental:

1. Build one local `genai-workflow-core` plugin from already-owned generic
   content.
2. Load it from a local directory or local install; do not publish it.
3. Keep all project identities and state in a scratch repository.
4. Verify agent/skill discovery, conflict precedence, disable/uninstall, and
   behavior in both CLI and the supported VS Code channel.
5. Compare generated file count, active metadata, task success, and maintenance
   effort with the current standard surface.
6. Adopt only if it reduces duplicated project files without weakening cloud
   compatibility, review boundaries, or project-specific routing.

Do not enable automatic updates for a reviewed workflow package. Updates should
be pinned, previewed, and explicitly promoted.

## 4. Supply-Chain and Skill-Selection Patterns

### Agent supply chain

The
[`agent-supply-chain` skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/agent-supply-chain/SKILL.md)
provides useful patterns:

- sorted SHA-256 file manifests;
- missing/modified/untracked file detection;
- dependency-version checks;
- promotion gates.

A digest proves equality to a chosen baseline; it does not prove authorship,
review quality, or that the baseline was trustworthy. The current examples also
reference older plugin/MCP layouts. Reintroducing signing, HMAC, or promotion
machinery now would repeat the earlier overdesign problem.

Use these patterns only when the Configurator gains an external
agent/skill/plugin import path. At that point, record:

- canonical source URL;
- exact revision and relative path;
- declared license;
- reviewed files and executable entry points;
- content digest;
- destination and collision result;
- explicit approval and removal path.

### Agent Skill Stack

The
[`agent-skill-stack` skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/agent-skill-stack/SKILL.md)
contains strong principles:

- derive the workflow from the requested outcome;
- search installed capability first;
- prefer the smallest compatible set;
- classify required/helpful/alternative/not-recommended;
- treat third-party instructions and scripts as untrusted;
- separate recommendation from installation consent;
- stage without overwrite;
- test skill routing with direct, paraphrased, and supporting requests.

However, the reviewed skill, references, and scripts total about 68 KB before
agent metadata. It adds local indexes, profiles, manifests, renderers, multiple
registry searches, `npx`, OpenCLI, and paths centered on other agent hosts.
That is too much machinery for the Configurator's small static optional
catalog.

Borrow the smallest-stack, conflict, staged-review, and no-overwrite rules.
Do not install the full skill unless future catalog growth creates a measured
discovery problem that the existing tool evaluator cannot handle.

## 5. Hooks and External Services

### Secret and license hooks

The reviewed hooks are substantial Bash programs:

- `secrets-scanner/scan-secrets.sh`: 10,081 bytes, session-end, 30-second
  timeout, warning mode, diff scope;
- `dependency-license-checker/check-licenses.sh`: 13,665 bytes, session-end,
  60-second timeout, warning mode.

Secret and license checks are valid, but these implementations are
platform-specific and run at the same lifecycle point regardless of whether a
session changed dependencies or sensitive configuration. That conflicts with
adaptive effort.

Prefer:

- the project's existing secret scanner or CI;
- changed-file secret checks after credential/configuration boundaries change;
- dependency/license review only when dependency manifests or lockfiles change;
- an AppSec or tool-evaluator review for high-risk additions.

### Attester Import Check

The Attester hook queries an external service about imports. It has quota and
network failure paths and necessarily reveals package names to that service.
It should not be a default blocker for private or local-first work. If a team
already accepts that service and data flow, it can be evaluated separately as
an optional project policy.

### Session and tool-control hooks

Do not adopt:

- Session Auto-Commit, because commits require explicit user approval;
- Session Logger, because prompt/session logging expands privacy and retention
  surface;
- Tool Guardian, because it duplicates the existing reviewed command guard and
  could create conflicting authority.

## 6. Assets That Do Not Fit

| Asset | Reason not to integrate |
|---|---|
| `acquire-codebase-knowledge` | Generates seven standing codebase documents and recreates the documentation bloat seen in real projects |
| `memory-bank` | Duplicates MemPalace and active handoff/task-state ownership |
| `context-map` | Adds a mandatory review gate and map before implementation |
| `what-context-needed` | Requests files from the user instead of using available search and code-intelligence tools |
| `refactor-plan` / `update-implementation-plan` | Applies a large planning workflow without task-tier proportionality |
| `pytest-coverage` | Treats 100% coverage as the target instead of risk-based tests |
| `tdd-refactor` | Encourages frequent tests and broad pattern/configuration activity even when the task is smaller |
| `ai-team-orchestration` plugin | Duplicates Planner/Executor/Reviewer and optional QA ownership |
| `acreadiness-cockpit` plugin | Adds Node/report/scoring machinery overlapping Configurator Analyze and Guide |
| `context-engineering` plugin | Bundles monotonic planning and context-map behavior |
| Thinking Beast agents | Optimize for exhaustive reasoning and verbose output rather than bounded engineering |

These can remain references for isolated ideas. They should not enter the
generated project surface or default plugin set.

## Decision Matrix

| Candidate | Integration level | Default? | New runtime? | Next action |
|---|---|---:|---:|---|
| Codebase-memory evidence levels | Compact adaptation in existing guidance | Yes, policy-dependent | No | Implement after approval |
| MCP configuration audit | Read-only Configurator Analyze check | When MCP config exists | No | Design focused findings/tests |
| Local workflow plugin | Experimental distribution pilot | No | Copilot plugin support only | Test in scratch repository |
| External customization provenance | Future import gate | No | No | Defer until import is designed |
| Agent Skill Stack | Principles only | No | No | Keep catalog small |
| Secret/license checks | Project-native conditional checks | No | Existing project tools | Document triggers |
| Other catalog content | Reference or reject | No | No | Do not install |

## Proposed Implementation Order

### Phase A: low-risk guidance improvement

1. Add Scout/Verify/Auditor semantics to existing code-intelligence guidance.
2. Preserve capability detection for the active MCP interface.
3. Add focused tests that ensure simple known-file work can skip the graph and
   exhaustive claims require stronger evidence or an explicit limitation.

### Phase B: read-only MCP audit

1. Extend Analyze rather than adding a session hook.
2. Parse the actual VS Code configuration schema.
3. Emit redacted, actionable findings.
4. Test direct-command versus shell-wrapper behavior, secure inputs, package
   pins, sandbox settings, and selected-server consistency.

### Phase C: optional local plugin experiment

1. Package only generic, already-reviewed capabilities.
2. Keep repository-specific policy/state local.
3. Use a scratch project and local plugin path.
4. Measure file reduction, discovery noise, behavior, and uninstall recovery.
5. Stop if the plugin increases active capability noise, weakens cloud-agent
   behavior, or requires duplicate local/plugin copies.

### Phase D: provenance only if imports are added

Do not build an importer merely because the catalog exists. If a future user
story requires external customization import, add pinned source identity,
review staging, hashes, collision refusal, preview, and explicit promotion at
that time.

## Acceptance and Exit Criteria

The recommended work is successful only if:

- a known-file Tier 0/1 task performs no unnecessary graph ritual;
- normal structural work verifies graph evidence against live source;
- exhaustive claims are bounded or explicitly downgraded when evidence is
  incomplete;
- MCP findings are redacted and have low false-positive rates on generated
  configurations;
- no check runs merely because a session ended;
- a plugin pilot measurably reduces repeated repository files;
- project memory/code identities remain explicit and correct;
- all additions are removable without changing application code.

Reject or remove a pilot when:

- it adds more active metadata than it removes;
- agents trigger it on unrelated tasks;
- it duplicates project-local controls;
- security findings are mostly noise;
- cloud/CLI/VS Code behavior requires permanent duplicate surfaces;
- update/provenance work exceeds the saved maintenance effort.

## Final Recommendation

Awesome Copilot should become a **reviewed upstream catalog and packaging
reference**, not another installed framework.

The highest-value immediate adaptation is the codebase-memory evidence-level
model because it directly improves proportionality and confidence without a new
file or dependency. The next useful implementation is a local read-only MCP
configuration audit. Agent Plugin packaging is strategically promising for
cross-project reuse, but should remain an optional scratch pilot until its
actual file, context, and compatibility savings are measured.

Everything else should remain patterns, conditional project-native checks, or
rejected overlap.

## Primary Sources

- [Awesome Copilot repository at reviewed revision](https://github.com/github/awesome-copilot/tree/f11a4e441c5ff061b4f8ae37952be8c602e4034e)
- [Awesome Copilot license](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/LICENSE)
- [Contribution and review rules](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/CONTRIBUTING.md)
- [Skill validator](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/eng/validate-skills.mjs)
- [Plugin validator](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/eng/validate-plugins.mjs)
- [Codebase Memory MCP skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/codebase-memory-mcp/SKILL.md)
- [MCP security audit skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/mcp-security-audit/SKILL.md)
- [Agent supply-chain skill](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/agent-supply-chain/SKILL.md)
- [Agent Skill Stack](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/skills/agent-skill-stack/SKILL.md)
- [Secret scanner hook](https://github.com/github/awesome-copilot/tree/f11a4e441c5ff061b4f8ae37952be8c602e4034e/hooks/secrets-scanner)
- [Dependency license hook](https://github.com/github/awesome-copilot/tree/f11a4e441c5ff061b4f8ae37952be8c602e4034e/hooks/dependency-license-checker)
- [Awesome Copilot plugin guide](https://github.com/github/awesome-copilot/blob/f11a4e441c5ff061b4f8ae37952be8c602e4034e/website/src/content/docs/learning-hub/installing-and-using-plugins.md)
- [Official GitHub plugin creation guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating)
- [Agent Plugins 1.0](https://agent-plugins.org/)

## Update: 2026-10-03 Upstream Checker Delta

**Scope:** Research against the Configurator's cached, checksum-validated
metadata report and selected public source at the exact reported revision. No
upstream asset was installed, imported, or marked reviewed; the local review
baseline was not advanced. The August assessment above remains a historical
snapshot, not a description of today's catalog.

The cached check at `2026-10-03T18:05:39.980187+00:00` compares reviewed
`f11a4e441c5ff061b4f8ae37952be8c602e4034e` to
`143a3d976b3c1603cc8932984d5e1f28501cb5fc`. It reports 47 outstanding
catalog paths, but only one change among the five specifically monitored
assets: the plugin installation guide. Those 47 are **review-queue entries,
not software updates**. The user has not approved any of them.

### Recommended Next Changes

1. **Prevent in-app documentation drift without adding an always-on skill.**
   The Guide lives in `USER_GUIDE` in `workflow_configurator/gui.py`, separately
   from `workflow_configurator/docs/CONFIGURATOR.md`. This caused the October
   Velocity controls and task intake to appear in the app while the Guide still
   described only the older balanced flow. The Guide and a focused regression
   assertion were updated in this session. For future user-visible modes,
   prefer one small shared source for the process summary or a targeted test
   comparing Guide claims to the resolved policy and UI labels. The new
   [docs-sync-audit skill](https://github.com/github/awesome-copilot/blob/143a3d976b3c1603cc8932984d5e1f28501cb5fc/skills/docs-sync-audit/SKILL.md)
   offers useful compare-source-to-docs and generated-doc-source checks, but
   defaults to a full-repository sweep without a scope. Borrow those checks
   for a named changed feature; do not add a standing audit, 13 KB skill, or
   new runtime dependency to the Velocity surface.

2. **Make the upstream queue proportional without silently approving it.**
   `review_items()` adds every catalog change, and `advance_review_baseline()`
   refuses to move while any item lacks a recorded decision. That is correct
   for a claimed fully reviewed baseline, but a single monitored docs change
   currently accompanies 46 other entries, mostly unrelated agents and skills.
   A proposed redesign would foreground monitored changes, then let the user
   explicitly inspect or classify out-of-scope catalog groups. Any bulk
   disposition must record its rationale, scope, revision, and item digests;
   the baseline must not advance unless all entries have an explicit decision.
   Never convert an uninspected path into an `adopt` disposition. Validate this
   interaction with an actual large report before implementing it.

3. **Keep the optional plugin exporter conservative.** The revised
   [upstream plugin guide](https://github.com/github/awesome-copilot/blob/143a3d976b3c1603cc8932984d5e1f28501cb5fc/website/src/content/docs/learning-hub/installing-and-using-plugins.md)
   uses `/plugin` instead of the older `/plugins` dashboard, explains
   marketplace-based installs, and documents component disablement. Official
   [GitHub plugin creation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating)
   and [plugin-format](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
   docs still support a legacy manifest with `agents: "agents/"` and local-path
   testing, which is what the current no-overwrite exporter produces. Agent
   Plugins 1.0 makes skills/MCP configuration portable, but Copilot-specific
   agents move under `com.github.copilot/agents/`; merely adding `$schema` to
   the current export would break discovery. Defer a format migration until a
   local pilot proves discovery, version behavior, uninstall, and actual
   file/context savings in the target VS Code and CLI environments. The local
   `copilot` wrapper asked to install the CLI during research, so no plugin
   runtime verification was attempted. Do not enable marketplace auto-update
   for a reviewed workflow package.

4. **Keep new audits opt-in.** The new
   [test-gap-audit](https://github.com/github/awesome-copilot/blob/143a3d976b3c1603cc8932984d5e1f28501cb5fc/skills/test-gap-audit/SKILL.md)
   skill is read-only, behavior-focused, and useful on a named risky feature;
   without a scope it inventories the entire repository and adds a lengthy
   review. The
   [agent-architecture](https://github.com/github/awesome-copilot/blob/143a3d976b3c1603cc8932984d5e1f28501cb5fc/skills/agent-architecture/SKILL.md)
   skill includes multi-document/PDF design work. Neither belongs in the
   implementation-first default. Invoke a bounded audit or design explicitly
   when its outcome justifies the overhead; do not install the catalog wholesale.

**Order:** keep the Guide drift check (done); pilot a compact, explicit
out-of-scope review interaction before redesigning baseline accounting;
exercise the existing local plugin export only after a suitable Copilot CLI is
already available. Measure whether any change reduces tool calls and active
instruction bytes without weakening Preview, no-overwrite, or review history.
