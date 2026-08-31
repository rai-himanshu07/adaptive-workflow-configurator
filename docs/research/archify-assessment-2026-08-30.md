# Archify Assessment

**Assessment date:** 2026-08-30

**Repository:** [tt-a1i/archify](https://github.com/tt-a1i/archify)

**Reviewed revision:** `39a21139`, release 2.16.0

## Verdict

**Keep Archify optional and use it only for milestone documentation. Do not
make it a core MCP, code-intelligence component, or routine workflow step.**

Archify is useful, but for a narrower purpose than its name may suggest. It is
a deterministic diagram artifact generator, not a tool that understands a
codebase by itself.

Expected value:

- high for one-time architecture, workflow, dataflow, sequence, or lifecycle
  diagrams;
- moderate for occasional architecture-delta reviews;
- low to zero for day-to-day implementation;
- negative if agents are required to update diagrams after small changes.

## What Archify Actually Does

Archify is a Node.js CLI plus an Agent Skill instruction bundle.

The agent authors typed JSON intermediate representation (IR), then the CLI:

1. validates it against a JSON schema and layout rules;
2. deterministically renders it;
3. atomically writes a self-contained interactive HTML/SVG artifact;
4. returns a SHA-256 delivery receipt.

It supports five artifact types:

- architecture;
- workflow;
- sequence;
- dataflow;
- lifecycle.

The resulting local HTML supports navigation, pan/zoom, light/dark themes,
deep links, and PNG/SVG/WebM export.

## What It Does Not Do

Archify does not:

- parse source code;
- build a symbol or call graph;
- resolve imports;
- identify runtime dependencies;
- calculate blast radius;
- maintain project memory;
- index a repository;
- automatically keep a diagram synchronized with code.

When given a repository, the **agent** must inspect and understand the code,
author the JSON IR, and supply any source references. Archify validates and
renders that authored description.

This distinction prevents it from replacing codebase-memory.

## Local Requirements and Privacy

Verified characteristics:

- Node.js 18 or newer;
- MIT license;
- no required server, cloud account, or hosted service;
- published bundle designed to run without installing runtime dependencies;
- local self-contained output;
- no telemetry;
- optional update-check HTTP request, disableable with
  `ARCHIFY_UPDATE_CHECK_DISABLED=1`;
- optional Chromium only for visual containment checks.

The local-first model fits this project well.

## Maturity

Archify is active but still fast-moving:

- release 2.16.0 was published on 2026-08-30;
- four feature releases appeared during August 2026;
- CI covers multiple Node versions and operating systems;
- golden, browser, packaging, and reproducibility checks exist;
- development is concentrated around one primary maintainer and
  agent-assisted contributions.

The activity is positive, but the rapid release cadence also implies contract
and artifact churn. It should not be installed as mandatory infrastructure.

## Fit With the Existing Stack

### codebase-memory

codebase-memory answers:

> What symbols, calls, routes, dependencies, clusters, and impact paths exist
> in the actual code?

Archify answers:

> How should an already-understood architecture be presented to a human?

They are complementary but not integrated. codebase-memory can provide
evidence for an Archify diagram, while Archify should never be treated as the
evidence source.

### MemPalace

There is no functional overlap.

- MemPalace stores durable decisions, session synthesis, and facts.
- Archify creates a visual artifact.

A project decision can reference an Archify IR or generated artifact, but the
artifact is not memory.

### DuckDB

There is no direct integration. Archify's `dataflow` type could document a
DuckDB pipeline, but it neither queries nor profiles DuckDB.

### Workflow Configurator

The best fit is visualizing:

- adaptive rigor selection;
- Planner/Executor/Reviewer boundaries;
- memory and code-intelligence routing;
- preview/apply/restore flow;
- shared MemPalace hub topology;
- task lifecycle and failure states.

It is not a replacement for the native PySide6 Configurator UI. Its output is
an HTML viewer, so it also does not satisfy the prior requirement for the main
application to remain non-web-based.

## Copilot Compatibility

The repository explicitly documents Cursor, Claude Code, Codex CLI, OpenCode,
DeepSeek Harness, and Raven installation paths. GitHub Copilot is not listed.

Its `SKILL.md` structure may be portable to a local Copilot Agent Skill, but
that path is not officially documented or verified. Treat Copilot support as
an experiment, not a supported integration.

The deterministic CLI can still be invoked manually after a Copilot agent
produces JSON IR.

## Token Economics

Archify can reduce later explanation cost when a complex system is repeatedly
reviewed by humans. It does not automatically reduce the cost of understanding
the code.

Generation requires an agent to:

- read the skill contract and relevant schema;
- inspect the system or code evidence;
- author the IR;
- validate it;
- correct schema/layout failures;
- regenerate the artifact.

A realistic generation may consume several thousand tokens. Exact costs depend
on diagram scope and model; published benchmarks for this workflow were not
found.

Therefore:

- do not invoke it during normal code edits;
- do not require diagrams for every plan or pull request;
- do not automatically regenerate after file changes;
- use it when one diagram will replace repeated architectural explanation.

Generated HTML examples are also substantial, often hundreds of kilobytes or
more, so automatic artifact accumulation would repeat the documentation-bloat
problem found in the real-project audit.

## Patterns Worth Borrowing

Archify contains several useful patterns even when the tool is not installed:

### 1. Typed intermediate representation

Agents produce a constrained, versioned JSON artifact rather than directly
generating arbitrary HTML/SVG.

This mirrors the Configurator's typed configuration model and is worth
retaining for any future visualization feature.

### 2. Validate before delivery

Schema and layout validation occur before the final artifact is accepted.
Failures remain explicit and bounded.

### 3. Deterministic rendering

The same accepted IR produces a reproducible artifact rather than another
model-generated drawing.

### 4. Evidence links

Architecture components can include file and line references plus a pinned Git
revision. Those references are authored rather than discovered, but they make
review easier.

### 5. Delivery receipts

Atomic output plus a digest gives a verifiable artifact boundary without
inventing complex rollback machinery.

### 6. Architecture delta

`archify compare` can present before/delta/after views from two accepted IR
snapshots. This is useful only for real architectural milestones.

## Recommended Integration Policy

Add Archify, at most, as a disabled-by-default optional integration:

```text
Category: Documentation / Visualization
Trigger: explicit user request or architecture milestone
Install: manual and reviewed
Automatic invocation: never
Required for normal tasks: no
```

Good uses:

1. one architecture/workflow diagram for the Workflow Configurator;
2. one lifecycle diagram for adaptive task rigor;
3. one hub diagram if the MemPalace topology is redesigned;
4. occasional before/after architecture artifact for a major refactor.

Poor uses:

- routine code review;
- source exploration;
- impact analysis;
- memory retrieval;
- every-task planning;
- automatic documentation synchronization.

## Final Recommendation

Archify has **moderate one-off value and marginal recurring value**.

Do not install it globally or add it to every generated project. Borrow its
typed-IR, validate-then-render, evidence-link, and receipt patterns. Offer the
actual tool only when the user explicitly wants a polished visual artifact.

## Primary Sources

- [README](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/README.md)
- [Agent Skill contract](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/archify/SKILL.md)
- [Architecture schema](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/archify/schemas/architecture.schema.json)
- [Package metadata](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/archify/package.json)
- [Design document](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/DESIGN.md)
- [Changelog](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/CHANGELOG.md)
- [License](https://github.com/tt-a1i/archify/blob/39a21139a4661203888049d44e3b8c0da13fa576/LICENSE)
