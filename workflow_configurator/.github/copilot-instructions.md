# Copilot Behavior for {{PROJECT_NAME}}

Read `AGENTS.md` and `docs/WORKFLOW_CONFIG.md`; do not duplicate their commands.

- Follow the resolved `{{INSTALLATION_SURFACE}}` surface and `{{PLAN_TIER}}`
  plan tier instead of imposing the same process on every task.
- Research/docs/trivial configuration require no code tests.
- Search and reuse before adding code. Keep non-goals explicit and avoid
  speculative abstractions, dependencies, configuration, or cleanup.
- Test changed behavior or a named risk with the smallest affected check after
  a coherent slice. Broaden only at the configured checkpoint.
- Use MemPalace according to `{{MEMORY_POLICY}}`, always with
  `wing="{{MEMORY_WING}}"` for project reads and writes.
- Use codebase-memory according to `{{CODE_INTELLIGENCE_POLICY}}` with project
  `{{CODEBASE_PROJECT_ID}}`; name only tools exposed in the active session and
  verify current behavior in live files. Skip it for known-file/literal lookups;
  use Scout for orientation, Verify for task claims, and Auditor only for
  bounded exhaustive/security claims.
- Preserve hard path, secret, sandbox, destructive-operation, preview,
  collision, and transactional safeguards regardless of expert overrides.
- Keep plans/handoffs current and compact when this surface installs them.
- Report blockers and failed checks; never claim unobserved success.
