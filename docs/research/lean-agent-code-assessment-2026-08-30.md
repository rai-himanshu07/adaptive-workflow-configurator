# Lean Agent-Generated Code Assessment

**Research date:** 2026-08-30

**Scope:** How to make coding agents minimize maintenance and comprehension
burden when the same required behavior and quality can be achieved with a
smaller, simpler implementation.

**Status:** Research only. No tool or rule has been installed.

**Related:** [Broader agent workflow assessment](agent-workflow-assessment-2026-08-30.md)

## Executive Conclusion

The primary objective is maintainability and understanding, not lower model
cost and not line reduction for its own sake. Among implementations with
equivalent required behavior, correctness, reliability, performance, and
operational quality, prefer the one with less code and fewer concepts to own.
A 10,000-line solution is a maintenance problem when the same outcome can be
expressed clearly and safely in a fraction of that surface.

"Fewer lines" is still not a safe objective by itself. A dense 200-line
implementation can be harder to maintain than a clear 300-line one. The target
is to remove **accidental complexity** while leaving essential domain and
operational complexity explicit. Lean code means fewer unnecessary concepts
and maintenance surfaces:

- reuse instead of parallel implementations;
- no speculative abstractions, configuration, or extension points;
- no new dependency when the standard library, platform, or an installed
  dependency already solves the current requirement;
- fewer public APIs, files, layers, and state transitions;
- no duplicate tests or test scaffolding;
- preserve required validation, errors, security, observability, and
  accessibility.

The best control is a three-stage system:

1. **Before generation:** require a small reuse/non-goal/size contract and use
   codebase search to find the existing path.
2. **After generation:** measure the actual diff with deterministic local
   tools.
3. **Only when a signal fires:** run one diff-scoped simplification review,
   then re-measure and verify behavior.

This avoids unnecessary churn and repeated reinterpretation of already-correct
code. Lower token cost may be a side effect, but it is not the definition of
success.

Ponytail has a useful idea but is not a necessary runtime dependency. It is
primarily a large prompt/ruleset. Its own corrected benchmark shows meaningful
source-LOC reduction on over-build-prone tasks, but its own cost study shows
that the prompt can cost more on OpenAI reasoning models. There is no
Copilot-specific cost benchmark.

**Recommendation:** do not install Ponytail's MCP server or full plugin.
Distill a few safe rules into the implementation/review workflow and evaluate
them against deterministic diff metrics. The package can be reconsidered only
if that small rule set is insufficient.

## What the Current Workflow Misses

The existing full template has two useful rules in
[AGENTS.md](../../workflow_configurator/AGENTS.md):

- make the smallest change satisfying the requested behavior;
- follow nearby implementation and test patterns before introducing
  abstractions.

Those rules are directionally correct but not operationalized:

- the [plan template](../../workflow_configurator/docs/PLAN.template.md) does not name
  existing code to reuse or set an expected implementation surface;
- the [Executor](../../workflow_configurator/.github/agents/executor.agent.md) limits
  scope but does not compare the result with a size or abstraction budget;
- the [Reviewer](../../workflow_configurator/.github/agents/reviewer.agent.md)
  prioritizes missing tests but not unnecessary code, duplication, dependency
  growth, or avoidable indirection;
- the project doctor does not inspect diff LOC, added files, dependencies,
  duplication, dead code, or complexity;
- neither template distinguishes useful robustness from speculative
  generality;
- there is no conditional simplification step.

The current repository also contains several 500-1,000 line Python modules.
That observation is not a finding that they are bloated. It demonstrates why
line count must trigger inspection rather than act as a verdict.

## Evidence That the Problem Is Broader Than One Workflow

Two 2026 preprints provide relevant evidence:

- [AI IDEs or Autonomous Agents?](https://arxiv.org/abs/2601.13597) uses a
  staggered difference-in-differences design with matched repositories. Its
  abstract reports persistent post-adoption quality risk, including about 18%
  more static-analysis warnings and 39% higher cognitive complexity. This is a
  causal-design preprint, not a randomized trial, and attribution/adoption
  measurement remains a limitation.
- [Debt Behind the AI Boom](https://arxiv.org/abs/2603.28592) analyzes about
  302,600 verified AI-authored commits across 6,299 repositories. It reports
  that code smells made up 89.3% of identified issues, every assistant had more
  than 15% of commits introduce at least one issue, and 22.7% of tracked
  introduced issues survived to the latest revision. This is observational
  evidence about maintainability debt, not proof that every agent change is
  verbose.

These studies support deterministic quality controls. They do not justify
code golf or a universal LOC cap.

## Why Agents Overbuild

The following mechanisms are supported by the local audit and by observed
agent behavior; not every item has a controlled LOC study:

1. **Incomplete repository context:** the model does not see an existing helper
   and writes a parallel one.
2. **Ambiguous non-goals:** the agent implements plausible future requirements
   to appear complete.
3. **Defensive generality:** one current use becomes an interface, factory,
   configuration layer, registry, and multiple implementations.
4. **New-dependency bias:** a familiar package is easier for the model to
   recall than the repository's existing or native solution.
5. **Additive planning:** every plan step creates an artifact/layer rather than
   converging on the smallest final design.
6. **Review asymmetry:** missing code/tests are criticized, while excess code
   is rarely a formal review finding.
7. **Test-count incentives:** broad test requirements generate repeated setup,
   fixtures, and near-identical cases even when one parameterized or contract
   test would establish the behavior.
8. **Unbounded self-improvement:** repeated reviewer/simplifier loops spend
   tokens, churn correct code, and can reintroduce abstractions removed by the
   previous pass.

## Ponytail Assessment

### What it actually is

[Ponytail](https://github.com/DietrichGebert/ponytail) is an MIT-licensed
portable prompt/ruleset, not a code analyzer or transformer.

Its canonical
[SKILL.md](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)
defines a ladder:

1. question whether code is needed;
2. reuse existing code;
3. prefer the standard library;
4. prefer native platform behavior;
5. prefer an already installed dependency;
6. use the minimum code that works.

It also discourages single-implementation interfaces, speculative scaffolding,
and unnecessary files. These are valuable principles.

The complete ruleset is well over a thousand input tokens depending on the
tokenizer and mode. It is delivered as context:

- static Copilot repository/global instructions are an always-on fallback;
- the full plugin/hook adapter runs in both VS Code Agent Host and Copilot CLI,
  despite the portability document still describing VS Code as
  instruction-only;
- on Copilot, the plugin injects the rules once through `SessionStart`; its
  per-prompt hook updates local mode state but does not re-inject the rules;
- other hosts use hooks, AGENTS.md, rules, or an MCP server;
- the MCP server serves the same rules rather than analyzing source.

Adding the MCP form would therefore add another server and tool schema to
deliver text that can already live in a skill. It has no technical advantage
for this setup.

### What the benchmarks actually show

The first Ponytail benchmark overstated the effect by counting conversational
prose as code. [Issue #126](https://github.com/DietrichGebert/ponytail/issues/126)
showed that a simple "one example, no commentary" baseline reduced average
output from 108 lines to 16, while Ponytail produced 8.25. The maintainer
accepted the critique and rebuilt the benchmark.

The corrected
[agentic benchmark](https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/results/2026-06-18-agentic.md):

- used real headless Claude Code sessions;
- edited a pinned FastAPI/React repository;
- measured added lines in `git diff`, not chat prose;
- ran 12 feature tasks with four runs per arm on Haiku 4.5;
- reported a mean 54% reduction in added LOC;
- found the largest reductions where native HTML controls replaced custom
  components;
- found little difference on already-minimal CRUD work.

This is meaningful evidence that the rules can reduce actual source diffs. It
is still a vendor-designed benchmark on one model, one repository, and tasks
chosen partly for over-building opportunity. It is not a universal expected
reduction.

The vendor's
[cost verification](https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/results/2026-06-17-cost-verification.md)
is especially important:

- the rules reduced cost on the tested Claude models;
- they made gpt-5.4-mini about 26% more expensive;
- they made gpt-5.5 about 39% more expensive and slightly slower;
- the report attributes the reversal to repeated ruleset input and additional
  reasoning tokens outweighing shorter output.

Those OpenAI results are not Copilot measurements. They establish that savings
are model- and workload-dependent and validate the user's concern about added
token consumption.

[Issue #121](https://github.com/DietrichGebert/ponytail/issues/121) reports an
independent Cursor SDK experiment where Ponytail often caused more reading,
tool calls, and estimated token cost while shortening some written output.
That task produced a large test-design draft rather than production source, so
it is useful cost evidence but not a source-code-size benchmark.

### Integration and behavior risks

The full ruleset is not a clean fit for the current workflow:

- "Code first" and "never stall" can conflict with required planning and user
  decisions; [issue #757](https://github.com/DietrichGebert/ponytail/issues/757)
  documents a current plan-gate conflict.
- The skill proposes an ad hoc `demo()` or a new `test_*.py` as a minimum
  runnable check. Existing project test conventions should win instead.
- Strong pressure toward fewer lines can remove useful errors, validation, or
  boundary handling. The rules say not to do this, but the optimization
  pressure remains.
- Copilot's integration is young.
  [Issue #759](https://github.com/DietrichGebert/ponytail/issues/759) documents
  an open VS Code Remote path-resolution bug.
- Static Copilot instructions apply on every request; plugin-injected rules
  become standing session context after `SessionStart`. Both add input context
  even when the implementation is already lean.

### Ponytail verdict

**Do not install the plugin or MCP server now. Do not copy the full ruleset
into global instructions. Never use `ultra` as an unattended default.**

Pilot only these distilled principles, loaded in the Executor or a manual
lean-code skill:

1. Search for the existing helper, type, component, or shared path before
   creating one.
2. Prefer a repository pattern, standard library, native platform feature, or
   installed dependency over a new abstraction/dependency.
3. Do not add speculative configuration, extension points, or an abstraction
   with only one present use unless the requirement demands it.
4. Minimize new public surfaces and files, not readability.
5. Never remove required validation, error handling, security, accessibility,
   observability, or requested behavior to meet a size target.
6. When the diff exceeds its planned surface, explain why or simplify it once.

This captures most of Ponytail's value in a much smaller, locally owned
contract without executing third-party hooks.

## Prevention Before Generation

### 1. Add a lean-change contract

For implementation tasks, the plan or first implementation note should record:

```text
Existing code to reuse:
Expected files touched:
New files/public APIs/dependencies expected:
Explicit non-goals:
Risks that must not be simplified away:
Size/complexity condition that triggers re-review:
```

This is an estimate, not a promise. Its purpose is to make a 2-file change
that becomes 20 files visibly suspicious before review.

For a small, low-risk task, the default expectation should be:

- use existing files and dependencies;
- add no architectural layer;
- add no configuration for hypothetical future variation;
- introduce no public API beyond the requested contract;
- add a focused regression test only when behavior changes or a bug needs
  protection.

### 2. Make reuse discovery cheap

Before adding a helper, component, service, or type:

1. use codebase-memory semantic/symbol search for equivalent concepts;
2. inspect the nearest existing implementation and its callers;
3. use language-service references/rename for exact symbol work;
4. read only the relevant source after structural discovery.

MemPalace should supply prior architectural decisions such as "do not add a
service layer here." It should not be used as proof of current code or as a
duplicate source index.

### 3. Specify non-goals

Good non-goals are more effective than "be concise":

- no plugin architecture;
- no generic framework;
- no new dependency;
- no compatibility layer beyond named versions;
- no unrelated cleanup;
- no additional endpoint/UI state beyond the acceptance criteria.

The model then has a clear boundary without losing correctness detail.

## Measure the Artifact, Not the Agent's Intent

### Metrics

Track a small differential set per task/PR:

1. production LOC added and removed;
2. files added and files touched;
3. dependencies added;
4. duplicated blocks introduced;
5. maximum new/changed-function complexity and size;
6. unused files, exports, symbols, and dependencies;
7. test LOC relative to changed behavior, reviewed qualitatively;
8. defects, review findings, and follow-up rework;
9. model input/output tokens, tool calls, and simplification-pass count as
   secondary operational measurements, not code-quality objectives.

Do not fail solely because LOC is high. Migrations, generated clients, schemas,
fixtures, parsers, and explicit compatibility tables can be legitimately
large. Exclude generated/vendor paths and require a short explanation for a
budget exception.

### Budget policy

Use task-specific review triggers rather than one global hard cap:

- Tier 1 changes should normally stay in one or two existing modules, add no
  dependency, and add no new layer. A surprisingly large diff triggers review.
- Tier 2 changes declare an expected surface in the plan. A result several
  times larger triggers one simplification/replanning decision.
- Tier 3/4 high-risk work can exceed a size budget when explicit correctness or
  migration requirements justify it.

Collect a baseline across real tasks before selecting numeric thresholds.
Otherwise the first threshold will encode guesswork and encourage gaming.

## Minimal Deterministic Tooling

The leanest tool strategy is progressive. Do not install every item below.

### Level 0: no new dependency

- `git diff --stat` and `git diff --numstat` for files and LOC;
- the existing package manifest/lockfile diff for new dependencies;
- codebase-memory search and graph queries for reuse, impact, and complexity;
- the existing formatter, linter, type checker, and tests.

This should cover most small tasks.

### Level 1: enable rules in tools the project already owns

For Python projects already using Ruff:

- [SIM rules](https://docs.astral.sh/ruff/rules/#flake8-simplify-sim) replace
  redundant conditionals, repeated context managers, reimplemented built-ins,
  and other avoidable code;
- [C901](https://docs.astral.sh/ruff/rules/complex-structure/) flags excessive
  cyclomatic complexity;
- [PLR0915](https://docs.astral.sh/ruff/rules/too-many-statements/) and related
  project-approved Pylint-derived rules can flag oversized functions.

Do not add standalone flake8-simplify when Ruff already supplies the relevant
rules.

For JavaScript/TypeScript projects already using ESLint:

- [complexity](https://eslint.org/docs/latest/rules/complexity);
- [max-lines-per-function](https://eslint.org/docs/latest/rules/max-lines-per-function);
- optionally max depth/statements and duplicate-import rules already supported
  by the project's ESLint version.

Line limits can encourage artificial file/function splitting. Use them with
complexity and duplication signals, and introduce them as warnings before
making them gates.

### Level 2: conditional or periodic tools

#### jscpd

[jscpd](https://github.com/kucherenko/jscpd) detects copied blocks across many
languages. Its
[AI reporter](https://github.com/kucherenko/jscpd/blob/master/docs/ai-ready.md)
emits compact clone locations and summary data. It also offers an MCP server.

Use the CLI/AI reporter conditionally on large or clone-prone diffs. Do not add
its MCP server globally at first: four more tools and a standing index are not
justified when a one-shot CLI command can answer the question.

#### Vulture

[Vulture](https://github.com/jendrikseipp/vulture) finds unused Python code and
assigns confidence levels. Dynamic imports, decorators, frameworks, and
reflection can create false positives.

Use high-confidence output as deletion candidates during periodic cleanup or a
large refactor, not as an automatic deletion gate after every edit.

#### Knip

[Knip](https://github.com/webpro-nl/knip) identifies unused JavaScript/
TypeScript files, exports, and dependencies. It is useful only in projects
whose build/runtime conventions it understands.

Use it in an existing JS/TS toolchain or periodic audit. Do not add it to
Python-only or small static projects.

#### Semgrep

[Semgrep](https://github.com/semgrep/semgrep) can encode a repeated,
project-specific rule such as "use the shared client rather than constructing
another one." That is valuable after the same mistake has occurred more than
once.

Do not create generic Semgrep rules for one incident, and do not enable its MCP
server merely to reduce code size. A local CLI/CI rule has less context and
security overhead.

### Tools not needed by default

- Radon, Xenon, or Lizard can provide richer complexity/NLOC gates, but are
  redundant if Ruff/ESLint and codebase-memory already answer the project's
  real questions.
- SonarQube is too heavy for the default personal workflow.
- another coding agent or repository graph is not required.
- mutation testing can assess test value, but it is compute-heavy and should
  not become a default response to test bloat.

## One Conditional Simplification Pass

Run a simplification review only when one of these fires:

- diff exceeds the planned surface;
- a new dependency or public API appears unexpectedly;
- duplication is introduced;
- changed functions cross an established complexity/size threshold;
- unused code is detected;
- test scaffolding is disproportionate or repeated.

The reviewer receives:

- the task and non-goals;
- the diff, not the whole repository;
- existing reusable symbols identified by codebase-memory;
- deterministic findings with exact file locations.

It asks:

1. Can existing code replace new code?
2. Can a native/standard-library feature replace a custom layer?
3. Is any abstraction serving only a hypothetical future use?
4. Can files, dependencies, branches, state, or tests be deleted/merged?
5. Did simplification remove a required guard or contract?

Perform at most one LLM simplification pass. Then:

1. rerun deterministic measurements;
2. run the smallest behavior check affected by the simplification;
3. run broader checks only when the task/risk tier requires them;
4. stop rather than entering a reviewer-simplifier loop.

## Test-Code Bloat

Lean production code with a thousand lines of repetitive tests is not a lean
change.

Review test additions for:

- repeated setup that belongs in an existing helper/fixture;
- near-identical tests that should be parameterized;
- tests of implementation details rather than observable behavior;
- separate tests whose assertions can be one contract table;
- generated mocks/fakes for a dependency that did not need to exist;
- success/failure matrices unrelated to the changed risk;
- snapshots where a smaller semantic assertion is sufficient.

A bug fix normally needs one focused regression case. New public or high-risk
behavior can justify a broader matrix. Test value and risk coverage matter
more than test LOC, so this remains a review decision rather than a hard ratio.

## Copilot-Compatible Control Flow

No runtime replacement is required:

1. **Planner/Executor context:** record the lean-change contract.
2. **Before edit:** use codebase-memory/language search for reuse.
3. **During edit:** existing formatter/linter auto-fixes simple redundancy.
4. **At agent stop or review:** a fast local script reads `git diff --numstat`,
   file/dependency changes, and configured project-native metrics. The hook is
   `Stop` in VS Code and `agentStop` in Copilot CLI/cloud terminology.
5. **If within budget:** finish with no extra model pass.
6. **If outside budget:** `Stop`/`agentStop` can request one additional
   simplification turn with the compact findings.
7. **At CI/checkpoint:** mirror the deterministic checks appropriate to the
   repository.

Copilot hook timeouts can fail open, and stop-event continuation is bounded.
The mechanism is a strong review trigger, not a perfect security boundary.

## Proposed Evaluation

Before enforcing new rules, compare a small set of real tasks:

- same repository state;
- same model, reasoning level, enabled tools, and acceptance criteria;
- baseline current workflow versus distilled lean rules;
- include already-simple tasks and over-build-prone UI/API tasks;
- measure production/test LOC, files, dependencies, duplication, complexity,
  tokens, tool calls, wall time, defects, review findings, and rework.

Do not use only artificial "native input versus custom component" tasks, which
would overstate the benefit.

Suggested decision criteria:

- keep the rules only if source size/maintenance surfaces fall without more
  defects or lost boundary handling;
- accept higher generation cost when it produces a materially easier system to
  understand and maintain; reject recurring token/tool overhead only when it
  provides negligible maintenance benefit;
- reject automatic simplification that creates churn or needs repeated model
  passes;
- calibrate project-specific thresholds from the observed baseline.

## Research Verdict

### Adopt as workflow principles

- optimize for the smallest maintenance surface only after required behavior
  and quality are held equivalent;
- reuse/search before generation;
- explicit non-goals;
- no speculative abstraction/configuration/dependency;
- task-specific implementation surface budget;
- simplicity as a first-class review criterion;
- protect required correctness and operational boundaries.

### Pilot

- distilled Ponytail-like rules in the Executor/manual skill, not the package;
- diff/file/dependency review triggers using Git;
- existing Ruff or ESLint simplification/complexity rules;
- one conditional diff-scoped lean review;
- jscpd CLI only if duplication appears in real diffs.

### Periodic/conditional

- Vulture for Python dead-code audits;
- Knip for JS/TS unused files/exports/dependencies;
- Semgrep for a repeated project-specific overbuilding pattern.

### Do not adopt now

- Ponytail MCP server;
- Ponytail full plugin/global rules;
- Ponytail `ultra` mode;
- a mandatory simplifier agent after every implementation;
- universal hard LOC limits;
- a large default quality-tool stack;
- another memory/code-graph/agent runtime for this problem.

## Primary Sources

- [Ponytail repository](https://github.com/DietrichGebert/ponytail)
- [Ponytail skill](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)
- [Ponytail agent portability](https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md)
- [Ponytail corrected agentic benchmark](https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/results/2026-06-18-agentic.md)
- [Ponytail cost verification](https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/results/2026-06-17-cost-verification.md)
- [Ponytail baseline critique, issue #126](https://github.com/DietrichGebert/ponytail/issues/126)
- [Ponytail independent cost/tool-call experiment, issue #121](https://github.com/DietrichGebert/ponytail/issues/121)
- [Ponytail plan-gate conflict, issue #757](https://github.com/DietrichGebert/ponytail/issues/757)
- [Ponytail Copilot Remote bug, issue #759](https://github.com/DietrichGebert/ponytail/issues/759)
- [AI IDEs or Autonomous Agents?](https://arxiv.org/abs/2601.13597)
- [Debt Behind the AI Boom](https://arxiv.org/abs/2603.28592)
- [Ruff rules](https://docs.astral.sh/ruff/rules/)
- [ESLint rules](https://eslint.org/docs/latest/rules/)
- [jscpd AI-ready integrations](https://github.com/kucherenko/jscpd/blob/master/docs/ai-ready.md)
- [Vulture](https://github.com/jendrikseipp/vulture)
- [Knip](https://github.com/webpro-nl/knip)
- [Semgrep](https://github.com/semgrep/semgrep)
