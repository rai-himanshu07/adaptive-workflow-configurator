# Optional Security Hooks

Installed only with `--with-security-hooks`. Review every file under
`.github/hooks/` before trusting the workspace.

The PreToolUse guard:

- preserves normal approval behavior for safe operations;
- asks for review of destructive Git, recursive deletion, infrastructure
  deletion, destructive SQL, privilege escalation, download-to-shell, and
  credential-path access;
- denies agent edits to its own hook directory and a small set of unmistakably
  catastrophic disk commands;
- understands both VS Code snake_case and Copilot CLI camelCase payloads and
  emits both platforms' decision envelopes.

Under non-interactive cloud agent, an `ask` decision becomes a denial. Hook
timeouts can fail open, so this is not a security boundary. Keep agent and MCP
sandboxing enabled and retain normal approvals.

The command inspection is intentionally heuristic. Shell aliases, generated
scripts, encoded commands, and unusual syntax can evade it; broad patterns can
also request review for a harmless command. Deterministic organizational policy
belongs in administrator-managed policy hooks and OS/database permissions.

Protect hook files from agent edits in VS Code settings as an additional layer:

```json
{
  "chat.tools.edits.autoApprove": {
    "**/.github/hooks/**": false
  }
}
```

Use **Chat: Configure Hooks**, the **GitHub Copilot Chat Hooks** output channel,
and **Developer: Show Agent Debug Logs** to inspect loading and execution. In
Copilot CLI, inspect `/hooks`. Repository hooks in non-interactive prompt mode
require a trusted folder or explicit repository-hook enablement.
