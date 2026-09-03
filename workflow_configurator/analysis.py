"""Bounded, read-only workflow and maintenance-surface metrics."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .catalog import REVIEWED_MCP_SERVER_NAMES


SOURCE_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".c",
    ".cpp",
}
TEXT_SUFFIXES = SOURCE_SUFFIXES | {".md", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml"}
WORKFLOW_DOC_NAMES = {
    "AGENTS.md",
    "HANDOFF.md",
    "PLAN.template.md",
    "MEMORY_PROTOCOL.md",
    "CODE_INTELLIGENCE.md",
    "WORKFLOW_CONFIG.md",
}
PLAN_BUDGETS = {"none": 0, "mini": 25, "compact": 80, "governed": 0}
TASK_TIERS = {"0": "none", "1": "mini", "2": "compact", "3": "governed"}
ALWAYS_ON_CONTEXT_PATHS = {
    "AGENTS.md",
    ".github/copilot-instructions.md",
}
ON_DEMAND_CONTEXT_PATHS = {
    "docs/AGENT_CONTEXT.md",
    "docs/AGENT_OBSERVABILITY.md",
    "docs/AGENT_SURFACES.md",
    "docs/CODE_INTELLIGENCE.md",
    "docs/ENVIRONMENT_POLICY.md",
    "docs/HANDOFF.md",
    "docs/MCP_SECURITY.md",
    "docs/MEMORY_PROTOCOL.md",
    "docs/PLAN.template.md",
    "docs/SECURITY_HOOKS.md",
    "docs/WORKFLOW_CONFIG.md",
    "docs/WORKFLOW_GUARD.md",
}
_SECRET_KEY = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|credential|database[_-]?uri|db[_-]?url)"
)
_SECRET_VALUES = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN(?: RSA)? PRIVATE KEY-----"),
    re.compile(r"://[^/\s:@]+:[^@\s/]+@"),
)
_INPUT_REFERENCE = re.compile(r"^\$\{input:([^}]+)\}$")
_ENV_REFERENCE = re.compile(r"^\$\{env:[A-Za-z_][A-Za-z0-9_]*\}$")
_SHELL_COMMANDS = {"bash", "cmd", "fish", "powershell", "pwsh", "sh", "zsh"}
_SHELL_FLAGS = {"-c", "-command", "/c"}


def _relative(target: Path, path: Path) -> str:
    return path.relative_to(target).as_posix()


def _project_file(target: Path, relative: str) -> Path | None:
    normalized = relative.replace("\\", "/")
    candidate_relative = Path(normalized)
    if (
        not normalized
        or candidate_relative.is_absolute()
        or ".." in candidate_relative.parts
        or any(part in {"", "."} for part in candidate_relative.parts)
    ):
        return None
    current = target
    for part in candidate_relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        current.resolve(strict=False).relative_to(target.resolve(strict=False))
    except (OSError, ValueError):
        return None
    return current if current.is_file() else None


def _read_text(
    path: Path,
    *,
    target: Path | None = None,
    max_bytes: int = 1_000_000,
) -> str | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
            return None
        if target is not None:
            relative = path.relative_to(target).as_posix()
            if _project_file(target, relative) != path:
                return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _category(relative: str, path: Path) -> str | None:
    parts = Path(relative).parts
    if (
        relative == "AGENTS.md"
        or ".github" in parts
        or path.name in WORKFLOW_DOC_NAMES
    ):
        return "workflow"
    if "tests" in parts or path.name.startswith(("test_", "spec.")) or ".test." in path.name:
        return "test"
    if path.suffix.lower() in {".md", ".rst"} or "docs" in parts:
        return "documentation"
    if path.suffix.lower() in SOURCE_SUFFIXES:
        return "production"
    return None


def _function_sizes(path: Path, text: str) -> list[dict[str, object]]:
    if path.suffix.lower() != ".py":
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", None)
        if isinstance(end, int):
            lines = end - node.lineno + 1
            if lines >= 100:
                result.append(
                    {
                        "name": node.name,
                        "start": node.lineno,
                        "lines": lines,
                    }
                )
    return result


def _content_stats(files: Mapping[str, bytes]) -> dict[str, int]:
    return {
        "files": len(files),
        "lines": sum(
            len(content.decode("utf-8", errors="replace").splitlines())
            for content in files.values()
        ),
        "bytes": sum(len(content) for content in files.values()),
    }


def _context_kind(path: str) -> str | None:
    if path in ALWAYS_ON_CONTEXT_PATHS:
        return "always_on"
    if path.startswith(".github/instructions/") and path.endswith(
        ".instructions.md"
    ):
        return "path_specific"
    if (
        path.startswith(".github/agents/")
        or path.endswith("/SKILL.md")
        or path in ON_DEMAND_CONTEXT_PATHS
    ):
        return "on_demand"
    return None


def _context_snapshot(files: Mapping[str, bytes]) -> dict[str, object]:
    groups: dict[str, dict[str, bytes]] = {
        "always_on": {},
        "path_specific": {},
        "on_demand": {},
    }
    for path, content in files.items():
        kind = _context_kind(path)
        if kind is not None:
            groups[kind][path] = content
    context_files = {
        path: content
        for group in groups.values()
        for path, content in group.items()
    }
    return {
        **{
            name: {
                **_content_stats(group),
                "paths": sorted(group),
            }
            for name, group in groups.items()
        },
        "total": _content_stats(context_files),
        "handoff": _content_stats(
            {
                path: content
                for path, content in files.items()
                if path == "docs/HANDOFF.md"
            }
        ),
        "mcp_servers": _mcp_server_count(files.get(".vscode/mcp.json")),
    }


def _mcp_server_count(content: bytes | None) -> int:
    if content is None:
        return 0
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return 0
    servers = value.get("servers") if isinstance(value, Mapping) else None
    return len(servers) if isinstance(servers, Mapping) else 0


def _normalized_blocks(files: Mapping[str, bytes]) -> list[dict[str, object]]:
    occurrences: dict[str, list[str]] = {}
    previews: dict[str, str] = {}
    for path, content in files.items():
        if _context_kind(path) is None:
            continue
        text = content.decode("utf-8", errors="replace")
        for block in re.split(r"\n\s*\n", text):
            lines = [
                re.sub(r"\s+", " ", line.strip())
                for line in block.splitlines()
                if line.strip()
            ]
            normalized = "\n".join(lines)
            if len(lines) < 2 or len(normalized) < 80:
                continue
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            occurrences.setdefault(digest, []).append(path)
            previews[digest] = normalized[:160]
    duplicates = []
    for digest, paths in occurrences.items():
        unique_paths = sorted(set(paths))
        if len(unique_paths) < 2:
            continue
        duplicates.append(
            {
                "sha256": digest,
                "paths": unique_paths,
                "preview": previews[digest],
            }
        )
    return sorted(
        duplicates,
        key=lambda item: (-len(item["paths"]), str(item["preview"])),
    )[:20]


def _change(current: int, proposed: int) -> dict[str, object]:
    delta = proposed - current
    percent = round(delta / current * 100, 1) if current else None
    return {
        "current": current,
        "safe_post_apply": proposed,
        "delta": delta,
        "percent": percent,
    }


def collect_context_footprint(
    current_files: Mapping[str, bytes],
    safe_post_apply_files: Mapping[str, bytes],
    *,
    active_plan: Mapping[str, object] | None = None,
    searchable_history_files: Mapping[str, bytes] | None = None,
) -> dict[str, object]:
    """Return deterministic context proxies without claiming token equivalence."""

    current = _context_snapshot(current_files)
    post_apply = _context_snapshot(safe_post_apply_files)
    current_always = current["always_on"]
    post_always = post_apply["always_on"]
    current_total = current["total"]
    post_total = post_apply["total"]
    assert isinstance(current_always, Mapping)
    assert isinstance(post_always, Mapping)
    assert isinstance(current_total, Mapping)
    assert isinstance(post_total, Mapping)
    history = dict(searchable_history_files or {})
    return {
        "unit": "UTF-8 bytes and physical lines; not an exact token forecast",
        "current": current,
        "safe_post_apply": post_apply,
        "change": {
            "always_on_bytes": _change(
                int(current_always["bytes"]),
                int(post_always["bytes"]),
            ),
            "total_context_bytes": _change(
                int(current_total["bytes"]),
                int(post_total["bytes"]),
            ),
            "mcp_servers": _change(
                int(current["mcp_servers"]),
                int(post_apply["mcp_servers"]),
            ),
        },
        "active_plan": dict(active_plan or {}),
        "searchable_history": {
            **_content_stats(history),
            "paths": sorted(history),
        },
        "duplicate_blocks": {
            "current": _normalized_blocks(current_files),
            "safe_post_apply": _normalized_blocks(safe_post_apply_files),
        },
    }


def render_context_footprint(footprint: Mapping[str, object]) -> str:
    current = footprint.get("current", {})
    post = footprint.get("safe_post_apply", {})
    current = current if isinstance(current, Mapping) else {}
    post = post if isinstance(post, Mapping) else {}

    def stats(snapshot: Mapping[str, object], name: str) -> Mapping[str, object]:
        value = snapshot.get(name, {})
        return value if isinstance(value, Mapping) else {}

    def comparison(name: str, label: str) -> str:
        before = stats(current, name)
        after = stats(post, name)
        return (
            f"- {label}: "
            f"{before.get('files', 0)} file(s), {before.get('lines', 0)} lines, "
            f"{before.get('bytes', 0)} bytes -> "
            f"{after.get('files', 0)} file(s), {after.get('lines', 0)} lines, "
            f"{after.get('bytes', 0)} bytes"
        )

    history = footprint.get("searchable_history", {})
    history = history if isinstance(history, Mapping) else {}
    duplicates = footprint.get("duplicate_blocks", {})
    duplicates = duplicates if isinstance(duplicates, Mapping) else {}
    current_duplicates = duplicates.get("current", [])
    post_duplicates = duplicates.get("safe_post_apply", [])
    changes = footprint.get("change", {})
    changes = changes if isinstance(changes, Mapping) else {}
    always_change = changes.get("always_on_bytes", {})
    always_change = (
        always_change if isinstance(always_change, Mapping) else {}
    )
    active_plan = footprint.get("active_plan", {})
    active_plan = active_plan if isinstance(active_plan, Mapping) else {}
    lines = [
        "Context footprint (deterministic proxy)",
        comparison("always_on", "Always-on"),
        (
            f"- Always-on byte change: {always_change.get('delta', 0):+} "
            f"({always_change.get('percent')}%)"
            if always_change.get("percent") is not None
            else f"- Always-on byte change: {always_change.get('delta', 0):+}"
        ),
        comparison("path_specific", "Path-specific"),
        comparison("on_demand", "On-demand workflow"),
        comparison("handoff", "Active handoff"),
        (
            f"- Configured MCP servers: {current.get('mcp_servers', 0)} -> "
            f"{post.get('mcp_servers', 0)}"
        ),
        (
            f"- Searchable history: {history.get('files', 0)} file(s), "
            f"{history.get('lines', 0)} lines, {history.get('bytes', 0)} bytes"
        ),
        (
            f"- Duplicate instruction blocks: "
            f"{len(current_duplicates) if isinstance(current_duplicates, list) else 0} -> "
            f"{len(post_duplicates) if isinstance(post_duplicates, list) else 0}"
        ),
    ]
    if active_plan:
        lines.append(
            f"- Active plan: {active_plan.get('value') or 'none'}; "
            f"{active_plan.get('lines') or 0} lines"
        )
    lines.append(f"- Unit: {footprint.get('unit', 'context proxy')}")
    return "\n".join(lines) + "\n"


def _mcp_finding(
    severity: str,
    code: str,
    message: str,
    *,
    scope: str,
    server: str | None = None,
) -> dict[str, str]:
    finding = {
        "severity": severity,
        "code": code,
        "scope": scope,
        "message": message,
    }
    if server is not None:
        finding["server"] = server
    return finding


def _has_secret_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_VALUES)


def _executable_name(command: str) -> str:
    return re.split(r"[\\/]", command)[-1].lower().removesuffix(".exe").removesuffix(".cmd")


def _package_argument(command: str, args: Sequence[object]) -> str | None:
    executable = _executable_name(command)
    if executable not in {"npx", "uvx"}:
        return None
    skip_value_flags = {
        "--extra-index-url",
        "--index-url",
        "--python",
        "--python-preference",
    }
    index = 0
    while index < len(args):
        value = args[index]
        if not isinstance(value, str):
            index += 1
            continue
        if executable == "uvx" and value == "--from":
            if index + 1 < len(args) and isinstance(args[index + 1], str):
                return str(args[index + 1])
            return None
        if value in skip_value_flags:
            index += 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        return value
    return None


def _package_is_pinned(command: str, package: str) -> bool:
    executable = _executable_name(command)
    if executable == "uvx":
        return "==" in package and not package.endswith("==")
    if executable == "npx":
        separator = package.rfind("@")
        if package.startswith("@") and separator <= package.find("/"):
            return False
        if separator <= 0:
            return False
        version = package[separator + 1 :]
        return bool(
            re.fullmatch(
                r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",
                version,
            )
        )
    return True


def audit_mcp_configuration(
    value: Mapping[str, object],
    *,
    scope: str,
    selected_servers: Sequence[str] = (),
    require_sandbox: bool = True,
    reviewed_servers: Sequence[str] = REVIEWED_MCP_SERVER_NAMES,
) -> dict[str, object]:
    """Return redacted findings for the actual VS Code MCP configuration schema."""

    findings: list[dict[str, str]] = []

    def add(severity: str, code: str, message: str, server: str | None = None) -> None:
        findings.append(
            _mcp_finding(severity, code, message, scope=scope, server=server)
        )

    servers = value.get("servers")
    if not isinstance(servers, Mapping):
        add("high", "mcp.schema.servers", "Configuration must contain a servers object.")
        return {"scope": scope, "server_count": 0, "findings": findings}

    inputs = {
        str(item["id"]): item.get("password") is True
        for item in value.get("inputs", [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    } if isinstance(value.get("inputs", []), list) else {}

    reviewed = set(reviewed_servers)
    for name, raw_server in servers.items():
        server = str(name)
        if not isinstance(raw_server, Mapping):
            add("high", "mcp.server.invalid", "Server configuration is not an object.", server)
            continue
        if server not in reviewed:
            add(
                "medium",
                "mcp.server.unreviewed",
                "Server is outside the reviewed Configurator catalog.",
                server,
            )
        command = raw_server.get("command")
        args = raw_server.get("args", [])
        if not isinstance(args, list):
            add("high", "mcp.args.invalid", "Server args must be a list.", server)
            args = []
        server_type = raw_server.get("type")
        is_stdio = server_type == "stdio" or isinstance(command, str)
        if is_stdio:
            if not isinstance(command, str) or not command.strip():
                add(
                    "high",
                    "mcp.command.missing",
                    "Local stdio server has no executable command.",
                    server,
                )
            else:
                executable = _executable_name(command)
                lowered_args = {item.lower() for item in args if isinstance(item, str)}
                if executable in _SHELL_COMMANDS and lowered_args & _SHELL_FLAGS:
                    add(
                        "high",
                        "mcp.command.shell-wrapper",
                        "Server invokes an explicit command shell; review injection and quoting boundaries.",
                        server,
                    )
                package = _package_argument(command, args)
                if package is not None and not _package_is_pinned(command, package):
                    add(
                        "medium",
                        "mcp.dependency.floating",
                        "Download-on-start package is not pinned to an exact version.",
                        server,
                    )
            if require_sandbox and raw_server.get("sandboxEnabled") is not True:
                add(
                    "high",
                    "mcp.sandbox.missing",
                    "Local stdio server is not explicitly sandboxed.",
                    server,
                )

        environment = raw_server.get("env", {})
        if isinstance(environment, Mapping):
            for key, raw in environment.items():
                if not isinstance(raw, str):
                    continue
                input_match = _INPUT_REFERENCE.fullmatch(raw)
                safe_reference = bool(input_match or _ENV_REFERENCE.fullmatch(raw))
                secret_key = bool(_SECRET_KEY.search(str(key)))
                if (
                    input_match
                    and secret_key
                    and not inputs.get(input_match.group(1), False)
                ):
                    add(
                        "high",
                        "mcp.input.unprotected",
                        "Credential input reference is missing or is not marked as a password.",
                        server,
                    )
                elif (secret_key and not safe_reference) or _has_secret_value(raw):
                    add(
                        "high",
                        "mcp.secret.literal",
                        "Possible plaintext credential appears in server environment configuration.",
                        server,
                    )

        if any(isinstance(raw, str) and _has_secret_value(raw) for raw in args):
            add(
                "high",
                "mcp.secret.argument",
                "Possible plaintext credential appears in server arguments.",
                server,
            )

        url = raw_server.get("url")
        if isinstance(url, str):
            parsed = urlparse(url)
            loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            if parsed.scheme != "https" and not (
                parsed.scheme == "http" and loopback
            ):
                add(
                    "high",
                    "mcp.transport.insecure",
                    "Remote MCP URL is not HTTPS.",
                    server,
                )

    missing = sorted(set(selected_servers) - {str(name) for name in servers})
    if missing:
        add(
            "medium",
            "mcp.selection.missing",
            "Selected server entries are absent: " + ", ".join(missing),
        )
    return {"scope": scope, "server_count": len(servers), "findings": findings}


def vscode_user_mcp_paths(
    *,
    home: Path | None = None,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    home = home or Path.home()
    platform = platform or sys.platform
    environ = environ or os.environ
    if platform.startswith("win"):
        appdata = environ.get("APPDATA")
        if not appdata:
            return ()
        base = Path(appdata)
        return (
            base / "Code" / "User" / "mcp.json",
            base / "Code - Insiders" / "User" / "mcp.json",
        )
    if platform == "darwin":
        base = home / "Library" / "Application Support"
        return (
            base / "Code" / "User" / "mcp.json",
            base / "Code - Insiders" / "User" / "mcp.json",
        )
    config = Path(environ.get("XDG_CONFIG_HOME", home / ".config"))
    return (
        config / "Code" / "User" / "mcp.json",
        config / "Code - Insiders" / "User" / "mcp.json",
        config / "VSCodium" / "User" / "mcp.json",
    )


def _load_mcp_file(
    path: Path,
    *,
    scope: str,
) -> tuple[Mapping[str, object] | None, list[dict[str, str]]]:
    if not path.exists():
        return None, []
    if path.is_symlink() or not path.is_file():
        return None, [
            _mcp_finding(
                "high",
                "mcp.file.unsafe",
                "MCP configuration path is not a regular non-symlink file.",
                scope=scope,
            )
        ]
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError("configuration exceeds the 1 MB inspection limit")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        return None, [
            _mcp_finding(
                "high",
                "mcp.file.invalid",
                f"MCP configuration cannot be inspected: {error}",
                scope=scope,
            )
        ]
    if not isinstance(value, Mapping):
        return None, [
            _mcp_finding(
                "high",
                "mcp.file.invalid",
                "MCP configuration root is not an object.",
                scope=scope,
            )
        ]
    return value, []


def collect_mcp_security(
    target: Path,
    *,
    proposed: Mapping[str, object] | None,
    selected_servers: Sequence[str],
    require_sandbox: bool,
    user_paths: Sequence[Path] | None = None,
) -> dict[str, object]:
    """Inspect proposed/workspace MCP configuration and duplicate user scope."""

    findings: list[dict[str, str]] = []
    proposed_result: dict[str, object] | None = None
    if proposed is not None:
        proposed_result = audit_mcp_configuration(
            proposed,
            scope="proposed",
            selected_servers=selected_servers,
            require_sandbox=require_sandbox,
        )
        findings.extend(proposed_result["findings"])  # type: ignore[arg-type]

    workspace_path = target / ".vscode" / "mcp.json"
    workspace, workspace_file_findings = _load_mcp_file(
        workspace_path, scope="workspace"
    )
    findings.extend(workspace_file_findings)
    workspace_result: dict[str, object] | None = None
    if workspace is not None:
        workspace_result = audit_mcp_configuration(
            workspace,
            scope="workspace",
            selected_servers=selected_servers,
            require_sandbox=require_sandbox,
        )
        findings.extend(workspace_result["findings"])  # type: ignore[arg-type]

    active_names = set(selected_servers)
    if not active_names and workspace is not None:
        raw_servers = workspace.get("servers")
        if isinstance(raw_servers, Mapping):
            active_names = {str(name) for name in raw_servers}

    profiles: list[dict[str, object]] = []
    paths = vscode_user_mcp_paths() if user_paths is None else user_paths
    for path in paths:
        value, file_findings = _load_mcp_file(path, scope="user-profile")
        findings.extend(file_findings)
        if value is None:
            continue
        raw_servers = value.get("servers")
        names = (
            sorted(str(name) for name in raw_servers)
            if isinstance(raw_servers, Mapping)
            else []
        )
        profiles.append({"path": str(path), "servers": names})
        profile_result = audit_mcp_configuration(
            value,
            scope=f"user-profile:{path.name}",
            require_sandbox=require_sandbox,
        )
        findings.extend(profile_result["findings"])  # type: ignore[arg-type]
        duplicates = sorted(active_names.intersection(names))
        if duplicates:
            findings.append(
                _mcp_finding(
                    "medium",
                    "mcp.scope.duplicate",
                    "Servers are registered in both workspace and user scope: "
                    + ", ".join(duplicates),
                    scope="workspace/user-profile",
                )
            )

    counts = {
        severity: sum(item["severity"] == severity for item in findings)
        for severity in ("high", "medium", "low")
    }
    return {
        "passed": not findings,
        "counts": counts,
        "findings": findings,
        "proposed": proposed_result,
        "workspace": workspace_result,
        "user_profiles": profiles,
    }


def _active_plan(target: Path, handoff: str, plan_tier: str) -> dict[str, object]:
    task = re.search(r"^\*\*Task tier:\*\*\s*([0-3])\s*$", handoff, re.MULTILINE)
    if task:
        plan_tier = TASK_TIERS[task.group(1)]
    match = re.search(r"^\*\*Active plan:\*\*\s*(.+?)\s*$", handoff, re.MULTILINE)
    value = match.group(1).strip().strip("`") if match else ""
    result: dict[str, object] = {
        "value": value or None,
        "valid": value.lower() == "none" if value else plan_tier in {"none", "mini"},
    }
    if value and value.lower() != "none":
        plan = _project_file(target, value)
        text = _read_text(plan, target=target) if plan is not None else None
        result["exists"] = plan is not None
        result["lines"] = len(text.splitlines()) if text is not None else None
        budget = PLAN_BUDGETS[plan_tier]
        result["budget"] = budget or None
        result["within_budget"] = (
            True
            if budget == 0
            else text is not None and len(text.splitlines()) <= budget
        )
        result["valid"] = bool(result["exists"] and result["within_budget"])
    return result


def collect_project_metrics(
    target: Path,
    paths: Iterable[Path],
    *,
    selected_files: Sequence[str],
    known_surface_files: Sequence[str],
    plan_tier: str,
    commands: Mapping[str, str],
    scan_complete: bool = True,
) -> dict[str, object]:
    """Collect bounded ratios and review triggers without changing the project."""

    totals = {
        "production": 0,
        "test": 0,
        "workflow": 0,
        "documentation": 0,
    }
    file_counts = {name: 0 for name in totals}
    large_files: list[dict[str, object]] = []
    large_functions: list[dict[str, object]] = []
    command_counts = {name: 0 for name in commands}
    workflow_paths: list[str] = []
    path_list = list(paths)
    for path in path_list:
        relative = _relative(target, path)
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "AGENTS.md":
            continue
        text = _read_text(path, target=target)
        if text is None:
            continue
        category = _category(relative, path)
        if category is None:
            continue
        lines = len(text.splitlines())
        totals[category] += lines
        file_counts[category] += 1
        if category == "workflow":
            workflow_paths.append(relative)
            for name, command in commands.items():
                if command and command.lower() != "none":
                    command_counts[name] += text.count(command)
        if lines >= 500:
            large_files.append({"path": relative, "lines": lines, "category": category})
        for function in _function_sizes(path, text):
            large_functions.append({"path": relative, **function})

    handoff_path = target / "docs" / "HANDOFF.md"
    handoff = _read_text(handoff_path, target=target) or ""
    selected = set(selected_files)
    legacy = [
        relative
        for relative in known_surface_files
        if relative not in selected and (target / relative).is_file()
    ]
    mcp_count = 0
    mcp_text = _read_text(target / ".vscode" / "mcp.json", target=target)
    if mcp_text:
        try:
            mcp = json.loads(mcp_text)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(mcp, dict) and isinstance(mcp.get("servers"), dict):
                mcp_count = len(mcp["servers"])

    production = totals["production"]
    return {
        "loc": totals,
        "files": file_counts,
        "ratios": {
            "test_to_production": round(totals["test"] / production, 3)
            if production
            else None,
            "workflow_to_production": round(totals["workflow"] / production, 3)
            if production
            else None,
        },
        "surface_counts": {
            "agents": sum("/agents/" in path for path in workflow_paths),
            "skills": sum("/skills/" in path and path.endswith("SKILL.md") for path in workflow_paths),
            "instructions": sum("/instructions/" in path for path in workflow_paths),
            "hooks": sum("/hooks/" in path for path in workflow_paths),
            "mcp_servers": mcp_count,
        },
        "handoff": {
            "present": handoff_path.is_file(),
            "lines": len(handoff.splitlines()) if handoff else 0,
            "bytes": len(handoff.encode("utf-8")),
            "within_budget": not handoff
            or (len(handoff.splitlines()) <= 40 and len(handoff.encode("utf-8")) <= 3_072),
        },
        "active_plan": _active_plan(target, handoff, plan_tier),
        "repeated_commands": {
            name: count for name, count in command_counts.items() if count > 1
        },
        "legacy_surface_candidates": legacy,
        "large_files": sorted(large_files, key=lambda item: int(item["lines"]), reverse=True)[:20],
        "large_python_functions": sorted(
            large_functions, key=lambda item: int(item["lines"]), reverse=True
        )[:20],
        "bounded": scan_complete,
    }


__all__ = [
    "audit_mcp_configuration",
    "collect_context_footprint",
    "collect_mcp_security",
    "collect_project_metrics",
    "render_context_footprint",
    "vscode_user_mcp_paths",
]
