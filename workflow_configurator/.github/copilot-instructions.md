# Copilot Behavior for {{PROJECT_NAME}}

{{STARTUP_FILES_RULE}}

- Follow the resolved `{{INSTALLATION_SURFACE}}` surface and `{{PLAN_TIER}}`
  plan tier instead of imposing the same process on every task.
- Research/docs/trivial configuration require no code tests.
- Search and reuse before adding code. Keep non-goals explicit and avoid
  speculative abstractions, dependencies, configuration, or cleanup.
{{COPILOT_VALIDATION_RULE}}
- Use MemPalace according to `{{MEMORY_POLICY}}`, always with
  `wing="{{MEMORY_WING}}"` for project reads and writes.
- Use codebase-memory according to `{{CODE_INTELLIGENCE_POLICY}}` with project
  `{{CODEBASE_PROJECT_ID}}`. {{CODE_INTELLIGENCE_RULE}}
- Preserve hard path, secret, sandbox, destructive-operation, preview,
  collision, and transactional safeguards regardless of expert overrides.
- Keep plans/handoffs current and compact when this surface installs them.
- Report blockers and failed checks; never claim unobserved success.
