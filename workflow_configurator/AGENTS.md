# {{PROJECT_NAME}} Agent Guide

{{PROJECT_SUMMARY}}

## Commands

| Action | Command |
|---|---|
| Focused test | `{{TEST_COMMAND}}` |
| Lint | `{{LINT_COMMAND}}` |
| Typecheck | `{{TYPECHECK_COMMAND}}` |
| Run | `{{RUN_COMMAND}}` |

`Not configured` means inspect existing manifests and ask before adding tooling.
Use the project's declared environment manager; never mix Conda and uv
dependency operations.

## Active Policy

- Surface: `{{INSTALLATION_SURFACE}}`
- Plan tier: `{{PLAN_TIER}}`
- Validation tier: `{{VALIDATION_TIER}}`
- Memory: `{{MEMORY_POLICY}}` in wing `{{MEMORY_WING}}`
- Code intelligence: `{{CODE_INTELLIGENCE_POLICY}}` for project
  `{{CODEBASE_PROJECT_ID}}`
- Technologies: {{TECHNOLOGY_STACK}}
- Review: `{{REVIEW_TIER}}`

Detailed resolved policy and selected optional capabilities are in
`docs/WORKFLOW_CONFIG.md`.

## Working Rules

- Start from the named behavior, file, symbol, or failure.
- Inspect nearby conventions and reuse existing code before adding a helper,
  layer, dependency, public API, or configuration.
- State non-goals; do not implement plausible future work.
- Keep the diff single-purpose and never modify unrelated user work.
- Preserve required validation, errors, security, accessibility, operations,
  and recovery even when simplifying.
- Never expose credentials or perform destructive filesystem, database,
  deployment, or Git operations without explicit approval.
- Add tests only for changed behavior, a reproduced bug, or a named risk.
{{VALIDATION_RULE}}
- Report failed or unavailable checks plainly.

## Task Routing

{{TASK_ROUTING_RULES}}

Use MemPalace only according to the active memory policy and always scope
project operations to `{{MEMORY_WING}}`. Use codebase-memory only according to
the active code-intelligence policy; live files and project checks remain the
current source of truth.
