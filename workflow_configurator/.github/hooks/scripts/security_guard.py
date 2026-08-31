#!/usr/bin/env python3
"""Conservative PreToolUse guard for obvious high-risk agent operations."""

from __future__ import annotations

import json
import posixpath
import re
import sys
from pathlib import PurePosixPath
from typing import Any, Iterable


EDIT_TOOL_MARKERS = ("edit", "write", "create", "patch", "replace")
COMMAND_KEYS = {"command", "cmd", "script", "shellcommand", "commandline"}
PATH_KEYS = {"path", "filepath", "file_path", "target", "destination", "source"}
PATH_TOKEN_SPLIT = re.compile(r"[\s\"'`;&|<>(){}\[\],]+")

SENSITIVE_PATH_PATTERNS = (
    re.compile(r"(^|/)\.env(?:\.[^/]+)?$", re.IGNORECASE),
    re.compile(r"(^|/)\.ssh/", re.IGNORECASE),
    re.compile(r"(^|/)\.aws/(?:credentials|config)$", re.IGNORECASE),
    re.compile(r"(^|/)\.azure/", re.IGNORECASE),
    re.compile(r"(^|/)(?:id_rsa|id_ed25519|credentials\.json)$", re.IGNORECASE),
)

CATASTROPHIC_COMMANDS = (
    (re.compile(r"(?:^|[;&|]\s*)rm\s+-[^\n]*r[^\n]*f[^\n]*\s+(?:/|~|\$HOME)(?:\s|$)", re.IGNORECASE), "recursive deletion targets a home or filesystem root"),
    (re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b", re.IGNORECASE), "filesystem formatting is not allowed"),
    (re.compile(r"\bdd\b[^\n]*\bof=/dev/(?:sd|nvme|vd)", re.IGNORECASE), "raw block-device overwrite is not allowed"),
    (re.compile(r"\b(?:Format-Volume|Clear-Disk)\b", re.IGNORECASE), "disk formatting or clearing is not allowed"),
)

REVIEW_COMMANDS = (
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE), "git reset --hard discards work"),
    (re.compile(r"\bgit\s+clean\s+-[^\n]*f", re.IGNORECASE), "git clean can delete untracked work"),
    (re.compile(r"\bgit\s+push\b[^\n]*(?:--force|-f\b)", re.IGNORECASE), "force push rewrites shared history"),
    (re.compile(r"\bgit\s+(?:checkout|restore)\b[^\n]*\s--\s", re.IGNORECASE), "checkout/restore can discard local changes"),
    (re.compile(r"\brm\s+-[^\n]*r", re.IGNORECASE), "recursive deletion requires review"),
    (re.compile(r"\bterraform\s+destroy\b", re.IGNORECASE), "terraform destroy removes infrastructure"),
    (re.compile(r"\bkubectl\s+delete\b", re.IGNORECASE), "kubectl delete changes cluster state"),
    (re.compile(r"\bhelm\s+uninstall\b", re.IGNORECASE), "helm uninstall removes a release"),
    (re.compile(r"\b(?:drop\s+(?:database|schema|table)|truncate\s+(?:table\s+)?)\b", re.IGNORECASE), "destructive SQL requires review"),
    (re.compile(r"\bdelete\s+from\b(?![^;\n]*\bwhere\b)", re.IGNORECASE), "DELETE without an evident WHERE clause requires review"),
    (re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba|z|fi)?sh\b", re.IGNORECASE), "download-to-shell execution requires review"),
    (re.compile(r"\bchmod\s+(?:-R\s+)?777\b", re.IGNORECASE), "world-writable permissions require review"),
    (re.compile(r"(?:^|[;&|]\s*)sudo\b", re.IGNORECASE), "privileged execution requires review"),
    (re.compile(r"\bRemove-Item\b[^\n]*(?:-Recurse|-Force)", re.IGNORECASE), "recursive or forced PowerShell deletion requires review"),
    (re.compile(r"\bSet-ExecutionPolicy\b[^\n]*\bBypass\b", re.IGNORECASE), "execution-policy bypass requires review"),
    (re.compile(r"\b(?:Invoke-WebRequest|iwr)\b[^\n|]*\|\s*(?:Invoke-Expression|iex)\b", re.IGNORECASE), "download-to-expression execution requires review"),
)

def normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return posixpath.normpath(normalized)


def is_hook_path(value: str) -> bool:
    normalized = normalize_path(value).lower()
    parts = PurePosixPath(normalized).parts
    return any(
        parts[index] == ".github" and parts[index + 1] == "hooks"
        for index in range(len(parts) - 1)
    )


def references_hook_path(value: str) -> bool:
    """Detect protected paths after lexically collapsing path traversal."""
    normalized = value.replace("\\", "/")
    for token in PATH_TOKEN_SPLIT.split(normalized):
        candidate = token.strip("*+:=")
        if candidate and is_hook_path(candidate):
            return True
    return False


def walk_values(value: Any, keys: set[str]) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).replace("_", "").lower()
            if normalized_key in {item.replace("_", "").lower() for item in keys} and isinstance(child, str):
                yield child
            yield from walk_values(child, keys)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child, keys)


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


def parse_input() -> tuple[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"invalid hook input: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    tool_input = payload.get("tool_input", payload.get("toolArgs", {}))
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            pass
    return tool_name, tool_input


def output(decision: str | None = None, reason: str | None = None) -> int:
    if decision is None:
        print("{}")
    else:
        print(
            json.dumps(
                {
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                    },
                }
            )
        )
    return 0


def main() -> int:
    try:
        tool_name, tool_input = parse_input()
    except ValueError as error:
        return output("deny", str(error))

    paths = [normalize_path(path) for path in walk_values(tool_input, PATH_KEYS)]
    commands = list(walk_values(tool_input, COMMAND_KEYS))
    all_strings = [value.replace("\\", "/") for value in walk_strings(tool_input)]
    if isinstance(tool_input, str) and any(marker in tool_name.lower() for marker in ("bash", "shell", "terminal", "powershell")):
        commands.append(tool_input)

    editing = any(marker in tool_name.lower() for marker in EDIT_TOOL_MARKERS)
    if editing and any(references_hook_path(value) for value in all_strings):
        return output("deny", "agent edits to .github/hooks are blocked; a human must review guard changes")

    for command in commands:
        if references_hook_path(command):
            return output("deny", "shell access involving .github/hooks is blocked; use a read tool for inspection")
        for pattern, reason in CATASTROPHIC_COMMANDS:
            if pattern.search(command):
                return output("deny", reason)
        for pattern, reason in REVIEW_COMMANDS:
            if pattern.search(command):
                return output("ask", reason)

    if any(pattern.search(path) for path in paths for pattern in SENSITIVE_PATH_PATTERNS):
        return output("ask", "access to a credential-bearing path requires explicit review")
    return output()


if __name__ == "__main__":
    raise SystemExit(main())