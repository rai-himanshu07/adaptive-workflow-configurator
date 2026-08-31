# Agency Agents and TencentDB Agent Memory Assessment

**Research date:** 2026-08-30

**Scope:** Relevance to the local Workflow Configurator, GitHub Copilot
VS Code/CLI, MemPalace, and codebase-memory.

**Status:** Research only. Neither project was installed or enabled.

## Executive Decision

| Project | What it actually is | Verdict |
|---|---|---|
| [Agency Agents](https://github.com/msitarzewski/agency-agents) | Large, community-maintained prompt/persona catalog plus multi-host conversion and installation scripts | **Watch; selectively borrow patterns** |
| [TencentDB Agent Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory) | Team memory platform with an LLM proxy, chat-memory pipeline, skill/wiki assets, and a separate CodeGraph/Wiki MCP service | **Watch; do not integrate now** |

Neither project should be added as an automatically installed dependency.

Agency Agents can improve the Configurator's **specialist-role design and
validation**, but only through small reviewed adaptations. Installing hundreds
of personas would add picker noise, instruction volume, quality variance, and a
new update/supply-chain surface.

TencentDB Agent Memory does not currently provide a supported Copilot path for
its core chat-memory product. In its MCP-native module, CodeGraph overlaps
codebase-memory; the linked Wiki/search graph is the novel capability. That
benefit is not yet enough to justify Node.js 22, service state, LLM processing,
and unresolved deployment/license questions.

## Evaluation Criteria

The projects were assessed against the current system's priorities:

1. GitHub Copilot VS Code and CLI compatibility.
2. Local-first operation and data boundaries.
3. Token/context overhead.
4. Maintenance and operational burden.
5. Safe existing-project integration.
6. Overlap with Planner/Executor/Reviewer, skills, MemPalace, and
   codebase-memory.
7. Ability to improve the Configurator without auto-installing remote code or
   unreviewed prompts.

Popularity was not treated as proof of quality. Both repositories have unusually
rapid growth and high issue counts for their age.

---

# Agency Agents

## What it is

Agency Agents is a prompt catalog, not an agent runtime or orchestration
framework.

The repository contains approximately 270+ Markdown personas organized into
18 divisions. Each persona has frontmatter plus sections such as identity,
mission, rules, deliverables, workflow, communication style, and success
metrics.

Primary sources:

- [Repository](https://github.com/msitarzewski/agency-agents)
- [README](https://github.com/msitarzewski/agency-agents/blob/main/README.md)
- [Supported-tool manifest](https://github.com/msitarzewski/agency-agents/blob/main/tools.json)
- [Security policy](https://github.com/msitarzewski/agency-agents/blob/main/SECURITY.md)
- [Originality checker](https://github.com/msitarzewski/agency-agents/blob/main/scripts/check-agent-originality.sh)

Its scripts convert and copy persona files into the configuration conventions
of multiple hosts. It does not provide:

- an execution loop;
- workflow state;
- memory;
- model routing;
- tool sandboxing;
- behavior evaluation;
- deterministic protocol enforcement.

## Copilot compatibility

GitHub Copilot is a first-class target.

The catalog's Markdown/frontmatter format is already close to Copilot custom
agents, so its installer can copy selected persona files into
`.github/agents/`. It also recognizes Copilot CLI.

This is technically compatible, but compatibility does not imply that the full
roster is useful. Hundreds of agents would:

- overwhelm the agent picker;
- make role selection less obvious;
- increase maintenance and upgrade noise;
- create inconsistent authority/tool expectations;
- conflict with the Configurator's small Planner/Executor/Reviewer workflow.

Selective installation is essential. The upstream installer itself supports
division and individual-agent filters.

## Token and context impact

The catalog's personas are long. Sampled agents are commonly 10–25 KB and
contain extensive identity, examples, processes, and communication rules.

Only the selected agent should normally enter the active prompt, but installing
the entire catalog still increases:

- discovery/catalog metadata;
- picker complexity;
- likelihood of choosing a near-duplicate role;
- maintenance and audit cost.

The upstream Hermes integration includes special lazy routing specifically to
avoid advertising every persona at session start. That design is evidence that
mass-installing the roster has a real context/catalog cost.

## Quality and security

Positive signals:

- MIT license.
- Active maintenance.
- Fixed persona template.
- CI checks for structural consistency.
- An entity-neutralized eight-word-shingle Jaccard checker to reject near-copy
  personas.
- A security policy that treats persona files as non-executable and prohibits
  credentials and prompt injection.

Limitations:

- The full catalog was not independently reviewed.
- Community-authored prompt quality will vary.
- Security policy is not a sandbox.
- Installation/conversion scripts are executable and modify host
  configuration.
- A closed security issue reported hidden Unicode soft-hyphen characters in
  two agent files. The issue may have been accidental and was closed, but it
  demonstrates why invisible-character scanning is valuable.
- The recommended companion desktop application auto-updates content, which
  conflicts with this Configurator's review-before-apply policy.

## Useful patterns for this tool

### 1. Specialist role template

The persona structure is a useful checklist:

- identity and domain;
- mission;
- critical boundaries;
- concrete deliverables;
- workflow;
- communication expectations;
- measurable success criteria.

The Configurator could use a **shortened** version for optional specialists
while retaining local constraints:

- allowed tools;
- read/write permissions;
- applicable risk tiers;
- required evidence;
- handoff destination;
- lean-code and test-proportionality rules.

### 2. Agent originality lint

The upstream originality script is one of the strongest reusable ideas.

The Configurator could eventually add a small local validation that:

- strips frontmatter;
- normalizes known entity substitutions;
- creates word shingles;
- compares a candidate persona with installed agents;
- warns or blocks obvious copies.

This would prevent the local agent collection from growing through cosmetic
reskins.

### 3. Manifest-driven host paths

The upstream `tools.json` pattern centralizes:

- supported host;
- detection paths;
- destination paths;
- file format;
- install scope;
- version command.

If the Configurator later supports Claude Code, Codex, Gemini CLI, and Copilot,
this is cleaner than scattering paths and formats across scripts.

### 4. Small reviewed specialist set

Potential upstream inspirations, not direct imports:

- [Minimal Change Engineer](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-minimal-change-engineer.md)
- [Accessibility Auditor](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-accessibility-auditor.md)
- [AI-Generated Code Auditor](https://github.com/msitarzewski/agency-agents/blob/main/security/security-ai-generated-code-auditor.md)
- [Tool Evaluator](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-tool-evaluator.md)
- [Research Synthesist](https://github.com/msitarzewski/agency-agents/blob/main/research/research-synthesist.md)

These should be treated as references and rewritten into shorter local agents.
They should not replace Planner/Executor/Reviewer.

## Safe future integration design

If persona import is later implemented:

1. User explicitly chooses one file and a pinned commit SHA.
2. The Configurator fetches or opens it as inert text only.
3. Content is placed in an external review/staging area, never directly into
   `.github/agents/`.
4. Validation checks:
   - expected frontmatter;
   - hidden/invisible Unicode;
   - suspicious instruction patterns;
   - size/token estimate;
   - near-duplicate similarity;
   - conflicting tool/permission claims.
5. Show full source, diff, provenance, and license.
6. Adapt it to the local short-agent template.
7. Explicit Apply installs only that reviewed persona.
8. Never auto-update it.
9. Keep installed specialists to a small documented limit.

## Agency Agents verdict

**Watch; pilot only the persona-template and originality-check concepts.**

Do not:

- install the complete roster;
- run the auto-updating application;
- run the Hermes plugin;
- automatically execute upstream conversion/install scripts;
- treat star count as evidence of safety or quality.

---

# TencentDB Agent Memory

## What it is

TencentDB Agent Memory is a multi-module team memory platform:

- `MemoryCore` — chat capture, memory extraction, retrieval;
- `MemoryKnowledge` — Wiki and CodeGraph;
- `MemoryProxy` — request interception and context injection;
- `MemoryPanel` — management UI;
- SDK/client adapters.

Primary sources:

- [Repository](https://github.com/TencentCloud/TencentDB-Agent-Memory)
- [README](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/README.md)
- [Deployment guide](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/README.deployment.md)
- [Root license](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/LICENSE)
- [MemoryKnowledge package](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/MemoryKnowledge/package.json)
- [MCP tool definitions](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/MemoryKnowledge/src/mcp/tools.ts)

## Memory architecture

Chat memory uses four levels:

- L0: raw conversations;
- L1: extracted atomic facts;
- L2: summarized scene blocks;
- L3: synthesized long-term persona.

Recall combines:

- BM25;
- vector retrieval;
- reciprocal-rank fusion;
- result-count, score, character, and timeout limits.

The Knowledge module adds:

- LLM-generated Wiki pages;
- document links;
- graph expansion;
- Louvain community detection;
- a CodeGraph based on the third-party `@colbymchenry/codegraph` package.

No equivalent to MemPalace's explicit temporal `kg_supersede`,
`kg_invalidate`, and point-in-time fact queries was established from the
reviewed public documentation.

## Deployment modes

### Standalone

- SQLite vector/database state.
- Local JSONL/Markdown files.
- In-process scheduling.
- No Tencent Cloud database dependency.
- Still requires an OpenAI-compatible LLM endpoint for chat-memory extraction
  and the default embedding workflow.

### Service

- Tencent Cloud VectorDB.
- Tencent Cloud Object Storage.
- Redis.
- Optional credential broker.
- Multi-tenant/team deployment.

The full stack adds Node.js 22, pnpm, multiple services/containers, database
state, ports, credentials, and operational maintenance.

## Copilot compatibility

The primary chat-memory integration is an LLM reverse proxy. Supported client
adapters listed by the project include products such as Claude Code, Codex,
OpenCode, and others, but not GitHub Copilot VS Code/CLI.

The proxy approach changes an agent's model endpoint so it can:

1. capture requests/responses;
2. inject memories and skills into the system prompt;
3. forward the request to the upstream LLM.

This is not available for the existing Copilot Business workflow and would
introduce another request/cache/cost boundary even if it were.

`MemoryKnowledge` is different: it includes a standard stdio MCP server with
12 read-only query tools:

- eight CodeGraph tools;
- four Wiki tools.

It may be technically registerable with Copilot as generic MCP, but the vendor
does not document or verify that integration. VS Code could use a deliberately
reviewed workspace `mcp.json`; Copilot CLI does not consume that file and would
need separate `copilot mcp add`/`.mcp.json` configuration plus a minimal tool
allowlist.

## Privacy and security

- Chat content is sent to the configured LLM endpoint for memory extraction.
- The default documented endpoint is OpenAI-compatible cloud.
- Local embedding code appears to exist in-tree, but an open feature request
  still asks for supported local/offline embedding. Treat it as partially
  implemented rather than a documented, reliable production path.
- CodeGraph creation clones a repository URL on the service side.
- Documentation says public HTTPS repositories are currently the primary
  supported path; private repository/SSH handling is evolving.
- No root `SECURITY.md` was found.
- Team visibility/ACL claims exist, but their enforcement code was not audited
  in this assessment.
- Optional telemetry/tracing dependencies exist and must be reviewed before
  enablement.

## License and maturity

The root `LICENSE` and package metadata say MIT.

However, `README.docker.md` says:

> Proprietary — Tencent Cloud

This contradiction should be clarified before using or redistributing Docker
images.

The repository is young and fast-moving:

- public beta/release activity concentrated in July–August 2026;
- current v2.0.x changes;
- a large active issue queue;
- recent reports concerning memory semantics, skill registration, startup,
  deletion behavior, and proxy compatibility.

Treat it as an actively stabilizing product rather than mature infrastructure.

## Benchmark quality

The README publishes one PersonaMem comparison:

- baseline: 48%;
- with TencentDB Agent Memory: 76%;
- claimed relative improvement: 59%.

No benchmark harness, dataset configuration, model settings, split, or
evaluation script was found in the repository. The number is a vendor claim
and cannot be independently reproduced from the supplied source.

## Comparison with the current stack

### Versus MemPalace

Overlap:

- conversation capture;
- long-term summaries;
- semantic retrieval;
- persistent project/user context.

MemPalace currently has stronger fit here because it:

- is already integrated through MCP;
- is local by default;
- provides explicit diary/checkpoint operations;
- has a temporal fact API;
- requires no request-rewriting proxy;
- is already part of the documented workflow.

TencentDB adds potential team-level advantages:

- shared memory service;
- management panel;
- visibility scopes;
- central skill and Wiki assets.

Those advantages matter only if a real multi-user/team memory requirement
exists and the operational/privacy costs are accepted.

### Versus codebase-memory

TencentDB CodeGraph overlaps:

- code search;
- callers and callees;
- impact analysis;
- code-file/symbol exploration.

The existing codebase-memory installation is better aligned because it indexes
the live local working tree and already exposes architecture, call/data flow,
complexity, and structural search through MCP.

TencentDB CodeGraph appears oriented around a service cloning a repository.
Support for local uncommitted changes was not established.

### Net result

- Chat Memory duplicates MemPalace but lacks a Copilot adapter.
- CodeGraph duplicates codebase-memory.
- Wiki/link-graph search is the clearest novel capability and could help shared
  onboarding or architecture documentation, but it still requires
  substantially more infrastructure and LLM processing.
- Skill assets overlap the Configurator's local `.github/skills/` model.

## Potential lessons for this tool

Worth borrowing as design concepts:

1. Clear separation among chat memory, skills, Wiki knowledge, and code graph.
2. Explicit recall budgets for count, characters, score, and timeout.
3. A team-level memory/asset dashboard if this tool later becomes multi-user.
4. Visibility/governance metadata for shared assets.
5. Asynchronous memory compaction tiers, provided source data remains available
   and summaries are treated as non-authoritative.

Not worth adopting now:

- LLM proxy integration;
- MemoryCore as a MemPalace replacement;
- CodeGraph beside codebase-memory;
- full Docker stack;
- Tencent Cloud service mode;
- benchmark-driven claims without reproducible evidence.

## TencentDB Agent Memory verdict

**Watch. Do not add it to the Configurator's selectable integrations now.**

Revisit only if:

1. an official Copilot or complete memory MCP adapter appears;
2. local/offline embeddings become a documented and reliable supported path;
3. private/local working-tree CodeGraph is supported;
4. the Docker license contradiction is resolved;
5. reproducible benchmarks are published;
6. the project demonstrates stable upgrade and deletion semantics.

An isolated CodeGraph-only comparison could be considered later, but it would
still duplicate the existing graph and require Node.js 22. The expected payoff
does not currently justify even that pilot.

---

# Recommended Configurator Changes

## Near term

Do not add either repository to the automatic MCP/install catalog.

Add a future **Specialist Roles** capability only if users need it:

- local or pinned-source persona import;
- external staging and full diff;
- invisible-Unicode and prompt-pattern scan;
- originality/near-duplicate check;
- token-size estimate;
- rewrite into a compact local role;
- explicit Apply;
- provenance record;
- no automatic updates.

The first useful specialist templates should be local adaptations of:

- minimal-change reviewer;
- accessibility auditor;
- AI-generated-code auditor;
- tool evaluator;
- research synthesist.

## Later, only for team use

If team-shared memory becomes a requirement, add a generic **Memory Backend
Assessment** screen rather than hard-coding TencentDB:

- deployment mode;
- data destination;
- LLM/embedding destination;
- temporal fact support;
- Copilot integration surface;
- local working-tree support;
- retention/deletion/export controls;
- authentication/ACL model;
- operational dependencies;
- benchmark evidence.

TencentDB Agent Memory can be one evaluated backend after it meets the revisit
conditions above.

## Final recommendation

- **Agency Agents:** mine patterns and selected personas; do not install the
  catalog.
- **TencentDB Agent Memory:** watch; do not integrate.
- **Current stack:** continue improving the small local Planner/Executor/
  Reviewer, MemPalace, and codebase-memory system before adding another large
  agent or memory surface.
