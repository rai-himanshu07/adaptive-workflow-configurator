"""Reusable workflow configurator core.

The module deliberately contains no command-line or GUI code.  It provides the
typed configuration model, deterministic policy derivation, read-only project
analysis, preview/proposal generation, transactional safe apply, and passive
manual recovery guidance used by the CLI and the optional desktop adapter.
"""

from __future__ import annotations

import contextvars
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import manifest as manifest_state
from .analysis import (
    audit_mcp_configuration,
    collect_context_footprint,
    collect_mcp_security,
    collect_project_metrics,
    render_context_footprint,
)
from .apply import ApplyResult, apply_project
from .catalog import (
    LOCAL_CAPABILITY_FILES,
    LOCAL_MCP_NAMES,
    MCP_NAMES,
    OPTIONAL_INTEGRATIONS,
    OPTIONAL_INTEGRATION_NAMES,
    PROFILE_FILES,
    SESSION_PROFILES,
)
from .config_model import (
    CONFIG_VERSION,
    DEFAULT_COMMANDS,
    DEFAULT_PROFILES,
    DEFAULT_SUMMARY,
    LEGACY_DEFAULT_COMMANDS,
    POLICY_DIMENSION_VALUES,
    RIGOR_ALIASES,
    VALID_COMPLEXITIES,
    VALID_EXECUTION_MODES,
    VALID_RIGOR_PRESETS,
    VALID_SESSION_PROFILES,
    VALID_SIZES,
    VALID_TESTING_LEVELS,
    VALID_WORKFLOWS,
    ConfigError,
    WorkflowConfig,
    canonical_codebase_project_id,
    canonical_memory_wing,
    validate_config,
)
from .policy import (
    POLICY_OVERRIDE_FIELDS,
    EngineeringPolicy,
    derive_policy,
    policy_override_catalog,
    policy_override_details,
    policy_override_strength,
    render_policy_override_guide,
    rigor_presets,
)
from .plugin_export import (
    PluginExportError,
    PluginExportPlan,
    apply_plugin_export as _apply_plugin_export,
    preview_plugin_export as _preview_plugin_export,
    render_plugin_preview,
)
from .recovery import (
    render_restore_instructions,
    restore_instructions,
    rollback_project,
)
from .upstream import (
    MAX_BLOB_RESPONSE_BYTES,
    REVIEW_DISPOSITIONS,
    UpstreamAssetReview,
    UpstreamError,
    UpstreamReport,
    UpstreamReviewItem,
    asset_request_urls as upstream_asset_request_urls,
    build_asset_review,
    build_upstream_report,
    export_review_brief,
    load_cached_report,
    render_asset_review,
    render_review_brief,
    render_upstream_report,
    request_urls as upstream_request_urls,
    review_items as upstream_review_items,
    save_cached_report,
    update_check_due,
)
from .upstream_service import UpstreamUpdateService


TEMPLATE_VERSION = "3.2"
CONFIG_FILENAME = ".workflow_configurator/config.json"
LEGACY_CONFIG_FILENAME = ".template_gpt/config.json"
MANIFESTS_DIRECTORY = manifest_state.MANIFESTS_DIRECTORY
BACKUPS_DIRECTORY = manifest_state.BACKUPS_DIRECTORY
LEGACY_MANIFESTS_DIRECTORY = manifest_state.LEGACY_MANIFESTS_DIRECTORY
LEGACY_BACKUPS_DIRECTORY = manifest_state.LEGACY_BACKUPS_DIRECTORY
GUIDANCE_PATH = "docs/WORKFLOW_CONFIG.md"
CURRENT_TASK_PATH = "docs/CURRENT_TASK.md"
KNOWN_REQUIRED_DIRECTORIES = ("docs/plans",)
_ACTIVE_OWNED_WRITES: contextvars.ContextVar[list[Path] | None] = (
    contextvars.ContextVar("workflow_configurator_active_owned_writes", default=None)
)

MINIMAL_FILES = (
    "AGENTS.md",
    ".github/copilot-instructions.md",
)
STANDARD_FILES = MINIMAL_FILES + (
    ".github/agents/planner.agent.md",
    ".github/agents/executor.agent.md",
    ".github/agents/reviewer.agent.md",
    ".github/skills/handoff-session/SKILL.md",
    ".github/skills/resume-session/SKILL.md",
    ".github/skills/project-doctor/SKILL.md",
    ".github/skills/project-doctor/scripts/doctor.py",
    "docs/HANDOFF.md",
)
GOVERNED_FILES = STANDARD_FILES + (
    ".github/skills/plan-task/SKILL.md",
    ".github/skills/memory-health/SKILL.md",
    "docs/PLAN.template.md",
    "docs/MEMORY_PROTOCOL.md",
    "docs/CODE_INTELLIGENCE.md",
    "docs/ENVIRONMENT_POLICY.md",
    "docs/AGENT_SURFACES.md",
    "docs/AGENT_CONTEXT.md",
    "docs/AGENT_OBSERVABILITY.md",
    "docs/MCP_SECURITY.md",
)
CORE_FILES = GOVERNED_FILES
LOCAL_PLAN_FILES = (
    ".github/skills/plan-task/SKILL.md",
    "docs/PLAN.template.md",
)

SECURITY_HOOK_FILES = (
    ".github/hooks/security.json",
    ".github/hooks/scripts/security_guard.py",
    "docs/SECURITY_HOOKS.md",
)
PROTOCOL_GUARD_FILES = (
    ".github/hooks/workflow_guard.json",
    ".github/hooks/scripts/workflow_guard.py",
    "docs/WORKFLOW_GUARD.md",
)
CONTEXT_SETTINGS_FILES = (".vscode/settings.json",)
GITIGNORE_ARTIFACT_BLOCK = "# workflow_configurator: generated experiment outputs\nartifacts/\n"
GENERATED_SEARCH_EXCLUDES = {
    "**/artifacts/**": True,
    "**/.conda/**": True,
    "**/.venv/**": True,
    "**/.mypy_cache/**": True,
    "**/.pytest_cache/**": True,
    "**/.ruff_cache/**": True,
    "**/.tox/**": True,
    "**/__pycache__/**": True,
    "**/node_modules/**": True,
    "**/dist/**": True,
    "**/build/**": True,
    "**/.next/**": True,
    "**/coverage/**": True,
    "**/.codebase-memory/**": True,
}

class SafetyError(RuntimeError):
    """Raised when a path or file cannot be handled without unsafe writes."""


class ApplyError(RuntimeError):
    """Raised when a safe apply cannot complete transactionally."""


class RollbackError(RuntimeError):
    """Compatibility error for the removed automatic rollback command."""


def config_for_target(
    target: Path | str,
    *,
    workflow: str | None = None,
    **overrides: Any,
) -> WorkflowConfig:
    """Create backward-compatible defaults with a target-derived project name."""

    target_path = Path(target).expanduser()
    name = target_path.name or "project"
    selected_workflow = workflow or ("existing" if target_path.exists() else "new")
    aliases = {
        "size": "project_size",
        "scope": "project_size",
        "testing": "testing_level",
        "profiles": "stack_profiles",
        "mcp": "mcp_servers",
        "integrations": "optional_integrations",
        "rigor": "rigor_preset",
    }
    for source_name, destination_name in aliases.items():
        if source_name in overrides and destination_name not in overrides:
            overrides[destination_name] = overrides.pop(source_name)
    values: dict[str, Any] = {
        "project_name": name,
        "workflow": selected_workflow,
        "stack_profiles": DEFAULT_PROFILES if selected_workflow == "new" else (),
    }
    values.update(overrides)
    return WorkflowConfig(**values)


def load_config(path: Path | str) -> WorkflowConfig:
    config_path = Path(path).expanduser()
    if config_path.is_symlink():
        raise ConfigError(f"refusing symlink configuration file: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"configuration file does not exist: {config_path}") from error
    except (OSError, UnicodeError) as error:
        raise ConfigError(f"cannot read configuration {config_path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"configuration is not valid JSON at {config_path}: line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error
    try:
        return WorkflowConfig.from_dict(raw)
    except ConfigError as error:
        raise ConfigError(f"invalid configuration {config_path}: {error}") from error


def _reject_symlink_or_nonregular(path: Path, *, allow_missing: bool = True) -> None:
    if path.is_symlink():
        raise SafetyError(f"refusing symlink path: {path}")
    if path.exists() and not path.is_file():
        raise SafetyError(f"path is not a regular file: {path}")
    if not allow_missing and not path.exists():
        raise SafetyError(f"required file is missing: {path}")


def _atomic_write(path: Path, content: bytes, mode: int = 0o644) -> None:
    """Write a file through a sibling, no-follow temporary and replace."""

    _reject_symlink_or_nonregular(path)
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise SafetyError(f"unsafe output directory: {parent}")
    temporary = parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, mode)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        if path.is_symlink():
            raise SafetyError(f"destination became a symlink: {path}")
        os.replace(temporary, path)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise


def _ensure_output_parent(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise SafetyError(f"unsafe output directory: {current}")
        if current.exists() and not current.is_dir():
            raise SafetyError(f"unsafe output directory: {current}")
        if current == current.parent:
            break
        current = current.parent
    missing: list[Path] = []
    current = path
    while not current.exists() and current != current.parent:
        missing.append(current)
        current = current.parent
    if missing:
        path.mkdir(parents=True, exist_ok=True)


def save_config(config: WorkflowConfig, path: Path | str) -> Path:
    """Export configuration without touching a project target."""

    validate_config(config)
    output = Path(path).expanduser()
    if str(output) == "-":
        raise ConfigError("save_config requires a file path; use config_json for stdout")
    if output.exists() and output.is_symlink():
        raise SafetyError(f"refusing symlink configuration output: {output}")
    _ensure_output_parent(output.parent)
    mode = output.stat().st_mode & 0o777 if output.exists() else 0o644
    _atomic_write(output, (json.dumps(config.to_dict(), indent=2) + "\n").encode("utf-8"), mode)
    return output


def config_json(config: WorkflowConfig) -> str:
    validate_config(config)
    return json.dumps(config.to_dict(), indent=2) + "\n"


# Descriptive aliases keep the public API easy to discover without another
# adapter layer.
import_config = load_config
export_config = save_config


def recommended_integrations(
    config: WorkflowConfig,
    facts: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return a small, non-binding shortlist based on the selected workflow."""

    facts = dict(facts or {})
    recommendations: list[str] = []
    if config.project_size in {"medium", "large"} or config.complexity == "advanced":
        recommendations.extend(("rtk", "serena"))
    if config.complexity == "advanced" or config.project_size == "large":
        recommendations.append("jscpd")
    if config.testing_level == "broad" or config.project_size == "large":
        recommendations.append("affected-tests")
    if config.rigor_preset == "strong" or config.project_size == "large":
        recommendations.append("otel-metadata")
    languages = set(facts.get("languages", {}))
    if "Python" in languages and config.project_size == "large":
        recommendations.append("vulture")
    if languages.intersection({"JavaScript", "TypeScript"}) and config.project_size == "large":
        recommendations.append("knip")
    if "data-science" in config.stack_profiles and config.complexity == "advanced":
        recommendations.append("experiment-runner")
    if "react" in config.stack_profiles:
        recommendations.append("specialist-accessibility")
    if config.with_security_hooks:
        recommendations.append("specialist-appsec")
    if config.complexity == "advanced":
        recommendations.append(
            "spec-kit" if config.rigor_preset == "strong" else "openspec"
        )
    elif config.workflow == "existing" and config.project_size != "small":
        recommendations.append("openspec")
    if not facts.get("manifests") and config.workflow == "existing":
        recommendations = [
            name for name in recommendations if name not in {"openspec", "spec-kit"}
        ]
    return tuple(dict.fromkeys(recommendations))


LEAN_CHANGE_CONTRACT = (
    "Search and reuse existing code before adding a new helper or abstraction.",
    "State explicit non-goals so plausible future work is not implemented.",
    "Do not add speculative abstractions, configuration, dependencies, or extension points.",
    "Keep the public API and file surface minimal while preserving clarity.",
    "Protect correctness, security, operational, accessibility, and recovery boundaries.",
    "Treat size or complexity signals as review triggers, never as universal hard LOC limits.",
)


def guidance(config: WorkflowConfig, facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    policy = derive_policy(config)
    facts = dict(facts or {})
    risk_score = (
        {"minimal": 0, "standard": 1, "advanced": 2}[config.complexity]
        + {"small": 0, "medium": 1, "large": 2}[config.project_size]
        + {"none": 0, "focused": 1, "broad": 2}[config.testing_level]
    )
    steps = [
        "Inspect the live project and reuse existing patterns before editing.",
        policy.planning_gate,
        policy.validation_mode,
        policy.documentation_handoff,
        policy.review_requirements,
    ]
    if config.execution_mode == "velocity":
        if policy.memory_policy == "required" and policy.code_intelligence_policy == "required":
            steps.insert(
                0,
                "Retrieve concise project memory and a bounded code-graph view before "
                "implementation; confirm behavior in live files.",
            )
        elif policy.memory_policy == "required":
            steps.insert(0, "Retrieve concise project memory before implementation.")
        elif policy.code_intelligence_policy == "required":
            steps.insert(0, "Check a bounded code-graph view before implementation.")
    elif policy.validation_tier != "manual" and config.testing_level == "none" and risk_score < 4:
        steps.insert(
            2,
            "For research, documentation, analysis, or configuration-only work, record "
            "the no-code-test reason and run only the smallest format/diagnostic check.",
        )
    elif policy.validation_tier != "manual" and config.testing_level == "none":
        steps.insert(
            2,
            "Testing was not selected, but this high-risk configuration still requires "
            "broad diagnostics, explicit limitations, and independent review.",
        )
    return {
        "configuration": config.to_dict(),
        "policy": policy.to_dict(),
        "risk_score": risk_score,
        "steps": steps,
        "optional_integrations": [
            {
                "name": name,
                **OPTIONAL_INTEGRATIONS[name],
            }
            for name in config.optional_integrations
        ],
        "recommended_integrations": list(recommended_integrations(config, facts)),
        "lean_change_contract": list(LEAN_CHANGE_CONTRACT),
        "non_goals": [
            "Do not replace Copilot, MemPalace, codebase-memory, or project package managers.",
            "Do not auto-install external integrations; review and install selected guidance separately.",
            "Do not rewrite conflicting user-owned guidance, hooks, MCP, or source files.",
        ],
        "facts": facts,
    }


def render_guidance(config: WorkflowConfig, facts: Mapping[str, Any] | None = None) -> str:
    data = guidance(config, facts)
    policy = data["policy"]
    lines = [
        "# Workflow Configuration",
        "",
        "This file is generated by `workflow_configurator` and is safe to review or delete.",
        "It describes policy; live source files and project commands remain authoritative.",
        "",
        "## Selected configuration",
        "",
        f"- Complexity: `{config.complexity}`",
        f"- Project size/scope: `{config.project_size}`",
        f"- Testing level: `{config.testing_level}`",
        f"- Stack profiles: {', '.join(config.stack_profiles) or 'none'}",
        f"- Other technologies: {config.technology_stack.strip() or 'inspect project manifests'}",
        f"- Execution mode: `{config.execution_mode}`",
        f"- Initial task: {'`' + CURRENT_TASK_PATH + '`' if config.task_details.strip() else 'none'}",
        f"- MCP choices: {', '.join(config.mcp_servers) or 'none'}",
        f"- Optional integration guidance: {', '.join(config.optional_integrations) or 'none'}",
        f"- Engineering rigor: `{config.rigor_preset}`",
        f"- Installation surface: `{policy['installation_surface']}`",
        f"- Plan tier: `{policy['plan_tier']}`",
        f"- Validation tier: `{policy['validation_tier']}`",
        f"- Memory policy: `{policy['memory_policy']}`",
        f"- Code-intelligence policy: `{policy['code_intelligence_policy']}`",
        f"- Memory wing: `{config.memory_wing}`",
        f"- codebase-memory project: `{config.codebase_project_id}`",
        f"- Session profile: `{config.session_profile}`",
        f"- Policy overrides: {json.dumps(dict(config.policy_overrides), sort_keys=True) if config.policy_overrides else 'none'}",
        "",
        "## Command overrides",
        "",
    ]
    lines.extend(
        f"- `{name}`: {command_for_template(value)}"
        for name, value in sorted(config.commands.items())
    )
    lines.extend(["", "## Concrete policy", ""])
    labels = (
        ("Planning gate", "planning_gate"),
        ("Validation", "validation_mode"),
        ("Documentation and handoff", "documentation_handoff"),
        ("Memory lifecycle", "memory_lifecycle"),
        ("Code intelligence", "code_intelligence"),
        ("Change isolation", "change_isolation"),
        ("Safety and approvals", "safety_approvals"),
        ("Review", "review_requirements"),
        ("Test path", "test_path"),
    )
    lines.extend(f"- {label}: {policy[key]}" for label, key in labels)
    lines.extend(
        [
            f"- Reviewed local protocol guard: {'enabled' if policy['require_protocol_guard'] else 'not enabled'}",
            "",
            "## Deterministic workflow",
            "",
        ]
    )
    lines.extend(f"{index}. {step}" for index, step in enumerate(data["steps"], 1))
    lines.extend(
        [
            "",
            "## Installed file contract",
            "",
            (
                "These generated paths can be audited on request:"
                if config.execution_mode == "velocity"
                else "The surface-aware project doctor treats only these generated paths as required:"
            ),
            "",
            *[f"- `{path}`" for path in selected_project_paths(config)],
        ]
    )
    session = SESSION_PROFILES[config.session_profile]
    lines.extend(
        [
            "",
            "## Session tool profile",
            "",
            f"- {session['label']}: {session['summary']}",
            "- This is enable/disable guidance only; it does not change an already-running agent session.",
        ]
    )
    if "spec-kit" in config.optional_integrations:
        lines.extend(
            [
                "",
                "## Specification ownership",
                "",
                "Spec Kit owns specification, plan, and task state. The local "
                "handoff is pointer-only; no parallel local plan skill or template "
                "is installed.",
            ]
        )
    lines.extend(["", "## Optional integrations", ""])
    if data["optional_integrations"]:
        for item in data["optional_integrations"]:
            lines.extend(
                [
                    f"### {item['label']} ({item['kind']})",
                    "",
                    f"- Purpose: {item['summary']}",
                    f"- Guardrail: {item['guardrail']}",
                    (
                        "- Delivery: bundled local template files are shown in Preview "
                        "and added only by explicit Apply."
                        if item["name"] in LOCAL_CAPABILITY_FILES
                        else "- Delivery: guidance only; nothing is installed automatically. "
                        "Verify current upstream instructions before adopting it."
                    ),
                    "",
                ]
            )
    else:
        lines.append(
            "None selected. Keep optional tools disabled until a measured project need justifies them."
        )
    if data["recommended_integrations"]:
        lines.extend(
            [
                "",
                "Non-binding recommendations for this project:",
                *[
                    f"- `{name}` — {OPTIONAL_INTEGRATIONS[name]['label']}"
                    for name in data["recommended_integrations"]
                    if name not in config.optional_integrations
                ],
            ]
        )
    lines.extend(["", "## Maintenance-first lean-change contract", ""])
    lines.extend(f"- {item}" for item in LEAN_CHANGE_CONTRACT)
    lines.extend(["", "## Explicit non-goals", ""])
    lines.extend(f"- {item}" for item in data["non_goals"])
    if facts:
        lines.extend(
            [
                "",
                "## Detected project facts",
                "",
                "Facts are recommendations only; existing declarations and conventions win.",
                "",
                "```json",
                json.dumps(dict(facts), indent=2, sort_keys=True),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def command_for_template(value: str) -> str:
    return "Not configured for this project." if value.strip().lower() == "none" else value.strip()


def _template_values(config: WorkflowConfig) -> dict[str, str]:
    policy = derive_policy(config)
    velocity = config.execution_mode == "velocity"
    manual_validation = policy.validation_tier == "manual"
    required_context = tuple(
        name
        for name, enabled in (
            ("one bounded project-memory lookup", policy.memory_policy == "required"),
            ("one code-graph lookup", policy.code_intelligence_policy == "required"),
        )
        if enabled
    )
    task_intake = (
        "- If chat has no concrete task, read `docs/CURRENT_TASK.md`; a new chat "
        "request or explicitly named file takes precedence. Ask if still unclear."
        if config.task_details.strip()
        else "- If no task is supplied, ask for it; accept details in chat or a named file."
    )
    routing = (
        (
            (
                "- Start with " + " and ".join(required_context)
                + ", then implement the concrete task."
                if required_context
                else "- Implement the concrete task using live project sources."
            ),
            "- Follow the resolved plan tier; keep project doctor manual.",
            (
                "- Run review only on user request."
                if policy.review_tier == "manual"
                else "- " + policy.review_requirements + "."
            ),
            (
                "- Explicitly selected hooks run automatically."
                if config.with_security_hooks or policy.require_protocol_guard
                else "- Optional hooks are not installed without explicit selection."
            ),
        )
        if velocity
        else (
            "- Questions, research, docs, and trivial configuration need no plan artifact and no code tests.",
            (
                "- Bounded low-risk edits use an inline/mini plan; checks run only on user request."
                if manual_validation
                else "- Bounded low-risk edits use an inline/mini plan and the smallest affected check."
            ),
            "- Coupled or multi-session changes use a compact plan and concise handoff.",
            "- Security, migration, regulated, or cross-service work uses the governed specification path selected in `docs/WORKFLOW_CONFIG.md`.",
        )
    )
    return {
        "{{PROJECT_NAME}}": config.project_name.strip(),
        "{{PROJECT_SUMMARY}}": config.summary.strip(),
        "{{TEST_COMMAND}}": command_for_template(config.commands["test"]),
        "{{LINT_COMMAND}}": command_for_template(config.commands["lint"]),
        "{{TYPECHECK_COMMAND}}": command_for_template(config.commands["typecheck"]),
        "{{RUN_COMMAND}}": command_for_template(config.commands["run"]),
        "{{MEMORY_WING}}": config.memory_wing,
        "{{CODEBASE_PROJECT_ID}}": config.codebase_project_id,
        "{{INSTALLATION_SURFACE}}": policy.installation_surface,
        "{{PLAN_TIER}}": policy.plan_tier,
        "{{VALIDATION_TIER}}": policy.validation_tier,
        "{{MEMORY_POLICY}}": policy.memory_policy,
        "{{CODE_INTELLIGENCE_POLICY}}": policy.code_intelligence_policy,
        "{{REVIEW_TIER}}": policy.review_tier,
        "{{STARTUP_FILES_RULE}}": (
            "Read `AGENTS.md`; open `docs/WORKFLOW_CONFIG.md` only when a policy detail is needed."
            if velocity
            else "Read `AGENTS.md` and `docs/WORKFLOW_CONFIG.md`; do not duplicate their commands."
        ),
        "{{TECHNOLOGY_STACK}}": config.technology_stack.strip() or ", ".join(config.stack_profiles) or "inspect project manifests",
        "{{VALIDATION_RULE}}": (
            "- Run tests, lint, typecheck, and project doctor only when the user "
            "requests them; state which checks were not run."
            if manual_validation
            else "- Run the smallest affected check after a coherent slice; broaden once at the configured checkpoint rather than after every edit."
        ),
        "{{TASK_ROUTING_RULES}}": "\n".join((*routing, task_intake)),
        "{{COPILOT_VALIDATION_RULE}}": (
            "- Tests, lint, typecheck, and project doctor are manual; report unrun "
            "checks without claiming success."
            if manual_validation
            else "- Test changed behavior or a named risk with the smallest affected check after a coherent slice. Broaden only at the configured checkpoint."
        ),
        "{{CODE_INTELLIGENCE_RULE}}": (
            "At task start, use " + " and ".join(required_context)
            + "; verify against live files."
            if velocity and required_context
            else "Name only tools exposed in the active session and verify current behavior in live files. Skip it for known-file/literal lookups; use Scout for orientation, Verify for task claims, and Auditor only for bounded exhaustive/security claims."
        ),
        "{{EXECUTOR_VALIDATION_RULES}}": (
            "5. Run tests, lint, and typecheck only on user request.\n"
            "6. Follow the resolved review and guard policy; report checks not run."
            if manual_validation
            else "5. After a coherent implementation slice, run the smallest affected check. Fix failures caused by the change and rerun that check.\n"
            "6. Run broader validation only at the configured checkpoint."
        ),
    }


def render_template(source: Path, config: WorkflowConfig) -> str:
    return render_values(source, _template_values(config))


def render_values(source: Path, values: Mapping[str, str]) -> str:
    try:
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ApplyError(f"cannot read template source {source}: {error}") from error
    unresolved = sorted(
        {
            "{{" + part.split("}}", 1)[0] + "}}"
            for part in content.split("{{")[1:]
            if "}}" in part
        }
        - set(values)
    )
    if unresolved:
        raise ApplyError(f"unresolved template tokens in {source}: {', '.join(unresolved)}")
    for token, value in values.items():
        content = content.replace(token, value)
    return content


def build_mcp_config(names: Sequence[str], *, sandbox_local: bool = True) -> dict[str, Any]:
    """Build the existing pinned VS Code MCP schema without adding services."""

    servers: dict[str, dict[str, Any]] = {}
    definitions: dict[str, dict[str, Any]] = {
        "duckdb": {
            "type": "stdio",
            "command": "uvx",
            "args": [
                "mcp-server-motherduck==1.0.7",
                "--db-path",
                ":memory:",
                "--read-write",
                "--query-timeout",
                "30",
                "--max-rows",
                "1000",
                "--max-chars",
                "50000",
            ],
            "cwd": "${workspaceFolder}",
            "sandboxEnabled": True,
        },
        "postgres": {
            "type": "stdio",
            "command": "uvx",
            "args": ["--python", "3.12", "postgres-mcp==0.3.0", "--access-mode=restricted"],
            "cwd": "${workspaceFolder}",
            "env": {"DATABASE_URI": "${input:postgres-uri}"},
            "sandboxEnabled": True,
        },
        "markitdown": {
            "type": "stdio",
            "command": "uvx",
            "args": ["markitdown-mcp==0.0.1a4"],
            "cwd": "${workspaceFolder}",
            "sandboxEnabled": True,
        },
        "context7": {"type": "http", "url": "https://mcp.context7.com/mcp"},
        "huggingface": {"type": "http", "url": "https://huggingface.co/mcp"},
    }
    for name in dict.fromkeys(names):
        servers[name] = dict(definitions[name])
    if not sandbox_local:
        for name in LOCAL_MCP_NAMES.intersection(servers):
            servers[name]["sandboxEnabled"] = False
    result: dict[str, Any] = {"servers": servers}
    if "postgres" in servers:
        result["inputs"] = [
            {
                "id": "postgres-uri",
                "type": "promptString",
                "description": "Read-only Postgres URI for a development database or replica",
                "password": True,
            }
        ]
    if sandbox_local and LOCAL_MCP_NAMES.intersection(servers):
        result["sandbox"] = {
            "filesystem": {
                "allowWrite": ["${userHome}/.cache/uv"],
                "denyRead": [
                    "${workspaceFolder}/.env",
                    "${userHome}/.ssh",
                    "${userHome}/.aws",
                    "${userHome}/.azure",
                ],
                "denyWrite": ["${workspaceFolder}"],
            },
            "network": {
                "allowedDomains": [
                    "localhost",
                    "127.0.0.1",
                    "pypi.org",
                    "files.pythonhosted.org",
                ]
            },
        }
    return result


def runtime_warnings(config: WorkflowConfig) -> list[str]:
    """Return local MCP/sandbox diagnostics without starting any service."""

    warnings: list[str] = []
    local = LOCAL_MCP_NAMES.intersection(config.mcp_servers)
    if not local:
        return warnings
    if shutil.which("uvx") is None:
        warnings.append("local MCP servers require uvx on PATH before they can start")
    if not config.sandbox_local:
        warnings.append(
            "selected local MCP servers will run unsandboxed; retain normal tool "
            "confirmations and review every file/data access"
        )
    if sys.platform.startswith("linux") and config.sandbox_local:
        missing = [
            command
            for command in ("bwrap", "socat", "rg")
            if shutil.which(command) is None
        ]
        if missing:
            warnings.append(
                "sandboxed local MCP servers require Linux commands: "
                + ", ".join(missing)
            )
        restriction = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
        try:
            restricted = restriction.read_text(encoding="utf-8").strip() == "1"
        except OSError:
            restricted = False
        if restricted:
            warnings.append(
                "AppArmor (kernel.apparmor_restrict_unprivileged_userns=1) restricts "
                "capability-bearing user namespaces; the VS Code MCP seccomp helper "
                "may fail. Prefer --without-mcp-sandbox with reviewed servers and "
                "normal tool confirmations."
            )
    return warnings


def preview_local_plugin(destination: Path | str) -> PluginExportPlan:
    return _preview_plugin_export(
        destination,
        source_root=Path(__file__).resolve().parent,
        version=TEMPLATE_VERSION,
    )


def export_local_plugin(expected: PluginExportPlan) -> Mapping[str, object]:
    return _apply_plugin_export(
        expected,
        source_root=Path(__file__).resolve().parent,
    )


def _command_result(command: Sequence[str], *, timeout: float = 8.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"status": "unavailable", "error": f"{command[0]} is not installed"}
    except subprocess.TimeoutExpired:
        return {"status": "degraded", "error": f"{command[0]} timed out after {timeout:g}s"}
    except OSError as error:
        return {"status": "degraded", "error": str(error)}
    return {
        "status": "ok" if result.returncode == 0 else "degraded",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _find_local_command(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    executable_name = f"{name}.exe" if os.name == "nt" else name
    candidates = [Path.home() / ".local" / "bin" / executable_name]
    conda_executable = os.environ.get("CONDA_EXE")
    if conda_executable:
        candidates.append(
            Path(conda_executable).expanduser().resolve(strict=False).parent.parent
            / "bin"
            / executable_name
        )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _live_pid(pid: Any) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _palace_key(palace_path: Path) -> str:
    resolved = os.path.normcase(os.path.realpath(os.path.expanduser(palace_path)))
    return hashlib.sha256(resolved.encode()).hexdigest()


def _mempalace_lock_state(palace_path: Path) -> dict[str, Any]:
    lock_path = (
        Path.home()
        / ".mempalace"
        / "locks"
        / f"mine_palace_{_palace_key(palace_path)[:16]}.lock"
    )
    if os.name == "nt":
        return {
            "status": "unknown",
            "lock_path": str(lock_path),
            "detail": "portable non-mutating lock probe is unavailable on Windows",
        }
    if not lock_path.is_file():
        return {"status": "writable", "lock_path": str(lock_path)}
    try:
        import fcntl

        with lock_path.open("r+b") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.seek(1)
                holder = handle.read().decode("utf-8", errors="replace").strip()
                pid_match = re.match(r"(\d+)", holder)
                return {
                    "status": "blocked",
                    "lock_path": str(lock_path),
                    "holder_pid": (
                        int(pid_match.group(1)) if pid_match else None
                    ),
                }
            finally:
                try:
                    fcntl.flock(handle, fcntl.LOCK_UN)
                except OSError:
                    pass
    except OSError as error:
        return {
            "status": "unknown",
            "lock_path": str(lock_path),
            "detail": str(error),
        }
    return {"status": "writable", "lock_path": str(lock_path)}


def mempalace_health(config: WorkflowConfig) -> dict[str, Any]:
    """Inspect local MemPalace availability, aliases, hub, and writer state."""

    executable = _find_local_command("mempalace")
    if executable is None:
        return {"status": "unavailable", "wing": config.memory_wing}
    version = _command_result((executable, "--version"))
    palace_path = Path.home() / ".mempalace" / "palace"
    key = _palace_key(palace_path)
    server_info_path = (
        Path.home() / ".mempalace" / "server" / key[:24] / "serverinfo.json"
    )
    hub: dict[str, Any] = {"status": "absent"}
    if server_info_path.is_file():
        try:
            info = json.loads(server_info_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            hub = {"status": "degraded", "error": str(error)}
        else:
            if isinstance(info, dict) and _live_pid(info.get("pid")):
                hub = {
                    "status": "read-only" if info.get("read_only") else "writable",
                    "pid": info.get("pid"),
                    "url": f"{info.get('scheme', 'http')}://{info.get('host')}:{info.get('port')}",
                }
            else:
                hub = {"status": "stale"}

    status_result = _command_result((executable, "status"), timeout=12.0)
    wings: list[str] = []
    if status_result["status"] == "ok":
        wings = [
            match.group(1).strip()
            for line in status_result.get("stdout", "").splitlines()
            if (match := re.match(r"\s*WING:\s*(.+?)\s*$", line))
        ]
    canonical = canonical_memory_wing(config.memory_wing.removeprefix("wing_"))
    aliases = [
        wing
        for wing in wings
        if canonical_memory_wing(wing.removeprefix("wing_")) == canonical
        and wing != config.memory_wing
    ]
    return {
        "status": (
            "healthy"
            if version["status"] == "ok" and status_result["status"] == "ok"
            else "degraded"
        ),
        "version": version.get("stdout") or version.get("error", "unknown"),
        "palace_path": str(palace_path),
        "wing": config.memory_wing,
        "wing_present": config.memory_wing in wings,
        "aliases": aliases,
        "hub": hub,
        "writer": _mempalace_lock_state(palace_path),
        "diagnostic": status_result.get("error")
        or status_result.get("stderr")
        or "",
    }


def _json_from_command_output(result: Mapping[str, Any]) -> dict[str, Any] | None:
    if result.get("status") != "ok":
        return None
    for line in reversed(str(result.get("stdout", "")).splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def codebase_memory_health(
    config: WorkflowConfig,
    target: Path | str | None = None,
) -> dict[str, Any]:
    """Inspect the persistent local code graph without indexing or mutating it."""

    executable = _find_local_command("codebase-memory-mcp")
    if executable is None:
        return {
            "status": "unavailable",
            "project": config.codebase_project_id,
        }
    status = _command_result(
        (
            executable,
            "cli",
            "index_status",
            json.dumps({"project": config.codebase_project_id}),
        ),
        timeout=12.0,
    )
    parsed = _json_from_command_output(status)
    if parsed is None:
        return {
            "status": "missing-or-degraded",
            "project": config.codebase_project_id,
            "diagnostic": status.get("stderr") or status.get("stdout") or status.get("error", ""),
        }
    indexed_root = parsed.get("root_path")
    expected_root = (
        str(Path(target).expanduser().resolve(strict=False))
        if target is not None
        else None
    )
    if expected_root is None:
        identity_status = "identity-unverified"
    elif not isinstance(indexed_root, str) or (
        Path(indexed_root).expanduser().resolve(strict=False)
        != Path(expected_root)
    ):
        return {
            "status": "identity-mismatch",
            "project": config.codebase_project_id,
            "expected_root": expected_root,
            "indexed_root": indexed_root,
            "index": parsed,
        }
    else:
        identity_status = "verified"
    changes = _command_result(
        (
            executable,
            "cli",
            "detect_changes",
            json.dumps({"project": config.codebase_project_id}),
        ),
        timeout=12.0,
    )
    change_data = _json_from_command_output(changes)
    change_summary = None
    if change_data is not None:
        changed_files = list(
            dict.fromkeys(
                str(path) for path in change_data.get("changed_files", [])
            )
        )
        change_summary = {
            "changed_count": int(
                change_data.get("changed_count", len(changed_files))
            ),
            "changed_files": changed_files[:20],
            "truncated": len(changed_files) > 20,
        }
    return {
        "status": "current"
        if change_summary is not None and not change_summary["changed_count"]
        else "stale"
        if change_summary is not None
        else "freshness-unverified",
        "project": config.codebase_project_id,
        "identity": identity_status,
        "expected_root": expected_root,
        "index": parsed,
        "changes": change_summary,
        "mcp_surface": "verify in the active agent session before naming optional tools",
    }


def continuity_summary(
    config: WorkflowConfig,
    health: Mapping[str, Any],
) -> dict[str, Any]:
    """Interpret continuity health according to the resolved adaptive policy."""

    policy = derive_policy(config)
    memory = health.get("mempalace", {})
    code = health.get("codebase_memory", {})
    memory = memory if isinstance(memory, Mapping) else {}
    code = code if isinstance(code, Mapping) else {}

    def memory_state() -> str:
        if policy.memory_policy == "off":
            return "disabled"
        if memory.get("status") != "healthy":
            return str(memory.get("status", "unavailable"))
        if memory.get("wing_present") is not True:
            return "identity-missing"
        writer = memory.get("writer", {})
        if isinstance(writer, Mapping) and writer.get("status") == "blocked":
            return "write-blocked"
        return "ready"

    def code_state() -> str:
        if policy.code_intelligence_policy == "off":
            return "disabled"
        status = str(code.get("status", "unavailable"))
        return "ready" if status == "current" else status

    services = {
        "mempalace": {
            "policy": policy.memory_policy,
            "state": memory_state(),
            "configured_identity": config.memory_wing,
        },
        "codebase_memory": {
            "policy": policy.code_intelligence_policy,
            "state": code_state(),
            "configured_identity": config.codebase_project_id,
        },
    }
    required_failures = [
        name
        for name, item in services.items()
        if item["policy"] == "required" and item["state"] != "ready"
    ]
    optional_limitations = [
        name
        for name, item in services.items()
        if item["policy"] == "on-demand" and item["state"] != "ready"
    ]
    enabled = [
        item for item in services.values() if item["policy"] != "off"
    ]
    if required_failures:
        status = "degraded"
    elif optional_limitations:
        status = "limited"
    elif not enabled:
        status = "disabled"
    else:
        status = "ready"

    effects: list[str] = []
    if "mempalace" in required_failures:
        effects.append(
            "Required historical continuity or durable checkpointing is incomplete."
        )
    elif "mempalace" in optional_limitations:
        effects.append(
            "Historical context may need reconstruction when the task requires it."
        )
    if "codebase_memory" in required_failures:
        effects.append(
            "Required structural retrieval or impact analysis is incomplete."
        )
    elif "codebase_memory" in optional_limitations:
        effects.append(
            "Structural retrieval may fall back to targeted live-file searches."
        )
    if status in {"degraded", "limited"}:
        effects.append(
            "Live repository inspection and safe configuration remain available."
        )
    if status == "disabled":
        effects.append(
            "Continuity services are deliberately disabled by the active policy."
        )
    return {
        "status": status,
        "summary": {
            "ready": "Configured continuity services are ready.",
            "limited": "Optional continuity is unavailable when requested.",
            "degraded": "A continuity service required by policy is not ready.",
            "disabled": "Continuity services are disabled by policy.",
        }[status],
        "services": services,
        "effects": effects,
    }


def external_health(
    config: WorkflowConfig,
    target: Path | str | None = None,
) -> dict[str, Any]:
    health = {
        "mempalace": mempalace_health(config),
        "codebase_memory": codebase_memory_health(config, target),
    }
    health["continuity"] = continuity_summary(config, health)
    return health


def selected_files(config: WorkflowConfig) -> list[str]:
    policy = derive_policy(config)
    ranks = {"minimal": 0, "standard": 1, "governed": 2}
    artifact_rank = ranks[policy.installation_surface]
    if policy.plan_tier == "compact" or policy.documentation_tier == "handoff":
        artifact_rank = max(artifact_rank, ranks["standard"])
    if (
        policy.plan_tier == "governed"
        or policy.documentation_tier == "full"
        or (
            config.execution_mode != "velocity"
            and (policy.memory_policy == "required" or policy.code_intelligence_policy == "required")
        )
        or policy.review_tier == "independent"
        or policy.protocol_guard == "on"
    ):
        artifact_rank = ranks["governed"]
    surface = ("minimal", "standard", "governed")[artifact_rank]
    files = list(
        {
            "minimal": MINIMAL_FILES,
            "standard": STANDARD_FILES,
            "governed": GOVERNED_FILES,
        }[surface]
    )
    for profile in config.stack_profiles:
        files.extend(PROFILE_FILES[profile])
    for capability in config.optional_integrations:
        files.extend(LOCAL_CAPABILITY_FILES.get(capability, ()))
    if config.task_details.strip():
        files.append(CURRENT_TASK_PATH)
    if config.with_security_hooks:
        files.extend(SECURITY_HOOK_FILES)
    if derive_policy(config).require_protocol_guard:
        files.extend(PROTOCOL_GUARD_FILES)
    if config.with_context_settings and surface != "minimal":
        files.extend(CONTEXT_SETTINGS_FILES)
    if "spec-kit" in config.optional_integrations:
        files = [
            path
            for path in files
            if path not in (*LOCAL_PLAN_FILES, ".github/agents/planner.agent.md")
        ]
    return list(dict.fromkeys(files))


def required_project_directories(config: WorkflowConfig) -> tuple[str, ...]:
    """Return generated directories needed by the selected task policy."""

    return (
        KNOWN_REQUIRED_DIRECTORIES
        if derive_policy(config).plan_tier in {"compact", "governed"}
        and "spec-kit" not in config.optional_integrations
        else ()
    )


def selected_project_paths(config: WorkflowConfig) -> list[str]:
    """Return the complete generated-file contract for one configuration."""

    paths = [*selected_files(config), GUIDANCE_PATH]
    if config.mcp_servers:
        paths.append(".vscode/mcp.json")
    if config.manage_artifact_gitignore and "data-science" in config.stack_profiles:
        paths.append(".gitignore")
    return list(dict.fromkeys(paths))


def all_known_surface_files() -> tuple[str, ...]:
    paths = [
        *GOVERNED_FILES,
        *sum(PROFILE_FILES.values(), ()),
        *sum(LOCAL_CAPABILITY_FILES.values(), ()),
        *SECURITY_HOOK_FILES,
        *PROTOCOL_GUARD_FILES,
        GUIDANCE_PATH,
        ".vscode/mcp.json",
    ]
    return tuple(dict.fromkeys(paths))


def _safe_relative(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    if normalized.startswith("//") or re.match(r"^[A-Za-z]:/", normalized):
        return False
    candidate = Path(normalized)
    return (
        not candidate.is_absolute()
        and relative not in ("", ".")
        and ".." not in candidate.parts
        and all(part not in ("", ".") for part in candidate.parts)
    )


def _target_path(target: Path, relative: str) -> Path:
    if not _safe_relative(relative):
        raise SafetyError(f"unsafe relative path: {relative!r}")
    relative = relative.replace("\\", "/")
    destination = target / relative
    current = target
    for part in Path(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise SafetyError(f"path component is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise SafetyError(f"path component is not a directory: {current}")
    if destination.is_symlink():
        raise SafetyError(f"destination is a symlink: {destination}")
    if destination.exists() and not destination.is_file():
        raise SafetyError(f"destination is not a regular file: {destination}")
    try:
        destination.parent.resolve(strict=False).relative_to(target.resolve(strict=False))
    except ValueError as error:
        raise SafetyError(f"destination parent escapes target: {destination}") from error
    return destination


def _directory_path(target: Path, relative: str) -> Path:
    """Return a directory destination after checking every path component."""

    if not _safe_relative(relative):
        raise SafetyError(f"unsafe relative directory: {relative!r}")
    relative = relative.replace("\\", "/")
    destination = target / relative
    current = target
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise SafetyError(f"path component is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise SafetyError(f"path component is not a directory: {current}")
    try:
        destination.resolve(strict=False).relative_to(target.resolve(strict=False))
    except ValueError as error:
        raise SafetyError(f"directory escapes target: {destination}") from error
    return destination


def _ensure_target_path(target: Path, *, allow_missing: bool = True) -> Path:
    target = Path(target).expanduser()
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            raise SafetyError(f"target is a symlink: {target}")
        if not target.is_dir():
            raise SafetyError(f"target is not a directory: {target}")
    elif not allow_missing:
        raise SafetyError(f"target directory does not exist: {target}")
    parent = target.parent
    current = parent
    while True:
        if current.is_symlink():
            raise SafetyError(f"target path component is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise SafetyError(f"target path component is not a directory: {current}")
        if current == current.parent:
            break
        current = current.parent
    try:
        target.resolve(strict=False)
    except OSError as error:
        raise SafetyError(f"cannot resolve target path: {target}: {error}") from error
    return target


def validate_target(target: Path | str, *, allow_missing: bool = True) -> Path:
    """Validate a target without creating it."""

    return _ensure_target_path(Path(target).expanduser(), allow_missing=allow_missing)


def _ensure_directory(path: Path, created: list[Path]) -> None:
    if path.is_symlink():
        raise SafetyError(f"refusing symlinked directory: {path}")
    if path.exists():
        if not path.is_dir():
            raise SafetyError(f"path is not a directory: {path}")
        return
    missing: list[Path] = []
    current = path
    while not current.exists() and current != current.parent:
        if current.is_symlink():
            raise SafetyError(f"refusing symlinked directory: {current}")
        missing.append(current)
        current = current.parent
    if current.is_symlink() or (current.exists() and not current.is_dir()):
        raise SafetyError(f"unsafe directory parent: {current}")
    for directory in reversed(missing):
        directory.mkdir(exist_ok=False)
        created.append(directory)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        data = path.read_bytes()
    except (OSError, UnicodeError) as error:
        raise SafetyError(f"cannot hash {path}: {error}") from error
    return _sha256_bytes(data)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _unified_diff(path: str, before: bytes | None, after: bytes) -> str:
    if before is None:
        before_lines: list[str] = []
    else:
        try:
            before_lines = before.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return "Binary or non-UTF-8 existing content; review the intended file manually."
    after_lines = after.decode("utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}" if before is not None else "/dev/null",
            tofile=f"b/{path}",
        )
    )


@dataclass(frozen=True)
class FileAction:
    path: str
    status: str
    reason: str
    intended_sha256: str | None = None
    current_sha256: str | None = None
    intended_content: str | None = None
    diff: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def kind(self) -> str:
        return self.status

    @property
    def classification(self) -> str:
        return self.status

    @property
    def safe(self) -> bool:
        return self.status in {"missing", "safe_merge", "identical"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "kind": self.status,
            "action": self.status,
            "type": self.status,
            "reason": self.reason,
            "intended_sha256": self.intended_sha256,
            "current_sha256": self.current_sha256,
            "intended_hash": self.intended_sha256,
            "current_hash": self.current_sha256,
            "intended_content": self.intended_content,
            "diff": self.diff,
            "metadata": dict(self.metadata),
        }


@dataclass
class AnalysisReport:
    target: str
    config: WorkflowConfig
    facts: dict[str, Any]
    actions: list[FileAction]
    directories: list[str]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    generated_guidance: str = ""
    directory_states: list[Mapping[str, Any]] = field(default_factory=list)

    @property
    def proposals(self) -> list[FileAction]:
        return [action for action in self.actions if action.status == "conflicting_proposal"]

    @property
    def conflicts(self) -> list[FileAction]:
        return self.proposals

    @property
    def collisions(self) -> list[FileAction]:
        return [
            action
            for action in self.actions
            if action.status in {"conflicting_proposal", "unsafe"}
        ]

    @property
    def safe_actions(self) -> list[FileAction]:
        return [action for action in self.actions if action.status in {"missing", "safe_merge"}]

    @property
    def identical(self) -> list[FileAction]:
        return [action for action in self.actions if action.status == "identical"]

    @property
    def diagnostics(self) -> list[Mapping[str, Any]]:
        return list(self.facts.get("scan_diagnostics", []))

    @property
    def incomplete(self) -> bool:
        return not bool(self.facts.get("scan_complete", True))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "config": self.config.to_dict(),
            "facts": self.facts,
            "actions": [action.to_dict() for action in self.actions],
            "directories": list(self.directories),
            "directory_states": [dict(item) for item in self.directory_states],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendations": list(self.recommendations),
            "guidance": self.generated_guidance,
            "diagnostics": [dict(item) for item in self.diagnostics],
            "proposals": [action.to_dict() for action in self.proposals],
            "collisions": [action.to_dict() for action in self.collisions],
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


MANIFEST_NAMES = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "environment.yml",
    "environment.yaml",
    "conda-lock.yml",
    "conda-lock.yaml",
    "uv.lock",
    "poetry.lock",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yaml",
)
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".sql": "SQL",
    ".ipynb": "Jupyter Notebook",
}
SKIP_DIRECTORIES = {
    ".conda",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "artifacts",
    ".codebase-memory",
    ".workflow_configurator",
    ".template_gpt",
    ".rev_arch",
}
SCAN_ENTRY_LIMITS = {
    "small": 25_000,
    "medium": 100_000,
    "large": 250_000,
}
DISCOVERY_SUFFIXES = set(LANGUAGE_EXTENSIONS) | {
    ".json",
    ".md",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
DISCOVERY_FILE_NAMES = set(MANIFEST_NAMES) | {
    ".gitignore",
    "Makefile",
    "Taskfile.yml",
    "justfile",
}


def _add_scan_diagnostic(
    diagnostics: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    path: Path,
    message: str,
) -> None:
    diagnostics.append(
        {
            "severity": severity,
            "code": code,
            "path": str(path),
            "message": message,
        }
    )


def _safe_file_text(
    path: Path,
    limit: int = 250_000,
    diagnostics: list[dict[str, Any]] | None = None,
) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    try:
        if path.is_symlink() or not path.is_file():
            return None
        mode = path.stat().st_mode
        if mode & 0o444 == 0:
            if diagnostics is not None:
                _add_scan_diagnostic(
                    diagnostics,
                    severity="warning",
                    code="read.permission-denied",
                    path=path,
                    message="file has no readable permission bits",
                )
            return None
        if path.stat().st_size > limit:
            if diagnostics is not None:
                _add_scan_diagnostic(
                    diagnostics,
                    severity="warning",
                    code="read.size-limit",
                    path=path,
                    message=f"file exceeds the {limit}-byte inspection limit",
                )
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        if diagnostics is not None:
            _add_scan_diagnostic(
                diagnostics,
                severity="warning",
                code="read.unavailable",
                path=path,
                message=f"cannot read UTF-8 text: {error}",
            )
        return None


def _discovery_candidate(path: Path, mode: int) -> bool:
    if not stat.S_ISREG(mode):
        return True
    return (
        path.suffix.lower() in DISCOVERY_SUFFIXES
        or path.name in DISCOVERY_FILE_NAMES
        or path.name.startswith(
            ("Dockerfile", "conda-lock", "environment", "requirements")
        )
    )


def _skipped_relative_path(relative: Path) -> bool:
    return any(part in SKIP_DIRECTORIES for part in relative.parts[:-1])


def _scan_limit_diagnostic(target: Path, max_entries: int) -> dict[str, Any]:
    return {
        "severity": "warning",
        "code": "traversal.limit",
        "path": str(target),
        "message": (
            f"discovery reached the {max_entries:,}-entry budget; "
            "select a larger Project size if broader metrics are required"
        ),
    }


def _git_project_paths(
    target: Path,
    *,
    max_entries: int,
) -> tuple[list[Path], list[dict[str, Any]], int] | None:
    git = shutil.which("git")
    if git is None or not (
        (target / ".git").exists() or (target / ".git").is_symlink()
    ):
        return None
    try:
        result = subprocess.run(
            [
                git,
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-C",
                str(target),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None

    paths: list[Path] = []
    diagnostics: list[dict[str, Any]] = []
    visited_entries = 0
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        if visited_entries >= max_entries:
            diagnostics.append(_scan_limit_diagnostic(target, max_entries))
            break
        visited_entries += 1
        relative = Path(os.fsdecode(raw))
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or _skipped_relative_path(relative)
        ):
            continue
        path = target / relative
        try:
            mode = path.lstat().st_mode
        except OSError:
            continue
        if _discovery_candidate(path, mode):
            paths.append(path)
    return paths, diagnostics, visited_entries


def _walk_project(
    target: Path,
    *,
    max_entries: int,
) -> tuple[list[Path], list[dict[str, Any]], int]:
    if not target.is_dir():
        return [], [], 0
    if max_entries < 1:
        raise ValueError("scan entry limit must be positive")
    paths: list[Path] = []
    diagnostics: list[dict[str, Any]] = []
    visited_entries = 0

    def limit_reached() -> bool:
        if visited_entries < max_entries:
            return False
        diagnostics.append(_scan_limit_diagnostic(target, max_entries))
        return True

    def onerror(error: OSError) -> None:
        filename = getattr(error, "filename", None)
        if isinstance(filename, bytes):
            filename = filename.decode(errors="replace")
        _add_scan_diagnostic(
            diagnostics,
            severity="warning",
            code="traversal.unavailable",
            path=Path(filename or target),
            message=f"cannot traverse project area: {error}",
        )

    try:
        for root, directories, files in os.walk(
            target, followlinks=False, onerror=onerror
        ):
            directories[:] = sorted(
                name for name in directories if name not in SKIP_DIRECTORIES
            )
            accessible_directories: list[str] = []
            for name in directories:
                if limit_reached():
                    return paths, diagnostics, visited_entries
                visited_entries += 1
                directory = Path(root) / name
                try:
                    mode = directory.lstat().st_mode
                except OSError as error:
                    _add_scan_diagnostic(
                        diagnostics,
                        severity="warning",
                        code="traversal.stat-failed",
                        path=directory,
                        message=str(error),
                    )
                    continue
                if stat.S_ISLNK(mode):
                    paths.append(directory)
                    continue
                if stat.S_ISDIR(mode) and (
                    mode & 0o444 == 0 or mode & 0o111 == 0
                ):
                    _add_scan_diagnostic(
                        diagnostics,
                        severity="warning",
                        code="traversal.permission-denied",
                        path=directory,
                        message="directory lacks readable/searchable permission bits",
                    )
                    continue
                accessible_directories.append(name)
            directories[:] = accessible_directories
            for name in sorted(files):
                if limit_reached():
                    return paths, diagnostics, visited_entries
                visited_entries += 1
                file_path = Path(root) / name
                try:
                    mode = file_path.lstat().st_mode
                    if not _discovery_candidate(file_path, mode):
                        continue
                    paths.append(file_path)
                    if stat.S_ISREG(mode) and mode & 0o444 == 0:
                        _add_scan_diagnostic(
                            diagnostics,
                            severity="warning",
                            code="read.permission-denied",
                            path=file_path,
                            message="file has no readable permission bits",
                        )
                except OSError as error:
                    _add_scan_diagnostic(
                        diagnostics,
                        severity="warning",
                        code="read.stat-failed",
                        path=file_path,
                        message=str(error),
                    )
    except OSError as error:
        onerror(error)
    return paths, diagnostics, visited_entries


def _discover_project(
    target: Path,
    *,
    max_entries: int,
) -> tuple[list[Path], list[dict[str, Any]], int, str]:
    git_result = _git_project_paths(target, max_entries=max_entries)
    if git_result is not None:
        paths, diagnostics, visited = git_result
        return paths, diagnostics, visited, "git"
    paths, diagnostics, visited = _walk_project(
        target,
        max_entries=max_entries,
    )
    return paths, diagnostics, visited, "filesystem"


def _detect_facts(
    target: Path, config: WorkflowConfig | None = None
) -> dict[str, Any]:
    project_size = config.project_size if config is not None else "small"
    scan_entry_limit = SCAN_ENTRY_LIMITS[project_size]
    if not target.is_dir():
        return {
            "exists": False,
            "manifests": [],
            "languages": {},
            "environment_managers": [],
            "commands": {},
            "git": {"present": False},
            "customizations": {},
            "customization_files": [],
            "known_template_files": [],
            "partial_installations": [],
            "symlinks": [],
            "non_regular_files": [],
            "recommendations": [],
            "scan_complete": True,
            "scan_entries": 0,
            "scan_entry_limit": scan_entry_limit,
            "scan_method": "none",
            "scan_diagnostics": [],
            "incomplete_areas": [],
        }
    paths, scan_diagnostics, scan_entries, discovery_method = _discover_project(
        target,
        max_entries=scan_entry_limit,
    )
    top_level = {path.name: path for path in paths if path.parent == target}
    def is_manifest(name: str) -> bool:
        return (
            name in MANIFEST_NAMES
            or name.startswith("requirements")
            or name.startswith("environment")
            or name.startswith("conda-lock")
            or name.startswith("Dockerfile")
        )

    manifests = sorted(
        {
            path.relative_to(target).as_posix()
            for path in paths
            if not path.is_symlink() and path.is_file() and is_manifest(path.name)
        }
    )
    language_counts: dict[str, int] = {}
    for path in paths:
        language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    managers: list[str] = []
    if any(
        path.name in ("environment.yml", "environment.yaml", "conda-lock.yml", "conda-lock.yaml")
        for path in paths
    ):
        managers.append("conda")
    pyproject = _safe_file_text(
        target / "pyproject.toml", diagnostics=scan_diagnostics
    ) or ""
    if any(path.name == "pyproject.toml" for path in paths) or any(
        path.name.startswith(("requirements", "environment", "conda-lock"))
        for path in paths
    ):
        language_counts.setdefault("Python", 0)
    if any(path.name == "uv.lock" for path in paths) or re.search(
        r"(?m)^\s*\[tool\.uv(?:\.|\])", pyproject
    ):
        managers.append("uv")
    if "package.json" in top_level:
        package = _safe_file_text(
            target / "package.json", diagnostics=scan_diagnostics
        ) or ""
        if "pnpm-lock.yaml" in top_level:
            managers.append("pnpm")
        elif "yarn.lock" in top_level:
            managers.append("yarn")
        elif "package-lock.json" in top_level:
            managers.append("npm")
        elif package:
            managers.append("npm")
    if "poetry.lock" in top_level or "[tool.poetry]" in pyproject:
        managers.append("poetry")
    if any(path.name.startswith("requirements") for path in paths):
        managers.append("pip")

    commands: dict[str, str] = {}
    package_text = _safe_file_text(
        target / "package.json", diagnostics=scan_diagnostics
    )
    if package_text:
        try:
            package = json.loads(package_text)
            scripts = package.get("scripts", {})
            if isinstance(scripts, Mapping):
                commands.update(
                    {f"npm:{key}": value for key, value in scripts.items() if isinstance(value, str)}
                )
        except json.JSONDecodeError:
            pass
    for build_file in ("Makefile", "justfile", "Taskfile.yml"):
        content = _safe_file_text(
            target / build_file, diagnostics=scan_diagnostics
        )
        if content:
            commands[build_file] = "targets detected; inspect before executing"
    for command_name in ("test", "lint", "typecheck", "run"):
        match = re.search(
            rf"(?m)^\s*{re.escape(command_name)}\s*=\s*[\"']([^\"']+)",
            pyproject,
        )
        if match:
            commands[f"pyproject:{command_name}"] = match.group(1)

    customization_paths = (
        "AGENTS.md",
        ".github/copilot-instructions.md",
        ".github/agents",
        ".github/instructions",
        ".github/skills",
        ".github/hooks",
        ".vscode/mcp.json",
        ".vscode/settings.json",
        ".mcp.json",
        ".github/mcp.json",
        "docs/HANDOFF.md",
        "docs/plans",
    )
    customizations = {
        relative: bool((target / relative).exists() or (target / relative).is_symlink())
        for relative in customization_paths
    }
    customization_files = sorted(
        path.relative_to(target).as_posix()
        for path in paths
        if (
            path.relative_to(target).as_posix() == "AGENTS.md"
            or path.relative_to(target).as_posix().startswith(
                (".github/", ".vscode/", "docs/HANDOFF.md", "docs/plans/")
            )
            or path.relative_to(target).as_posix() in {".mcp.json", ".github/mcp.json"}
        )
    )
    searchable_history_files = sorted(
        path.relative_to(target).as_posix()
        for path in paths
        if path.relative_to(target).as_posix().startswith(
            (".goals/", "docs/research/")
        )
    )

    symlinks: list[str] = []
    non_regular: list[str] = []
    for path in paths:
        try:
            mode = path.lstat().st_mode
        except OSError:
            continue
        relative = path.relative_to(target).as_posix()
        if stat.S_ISLNK(mode):
            symlinks.append(relative)
        elif not stat.S_ISREG(mode):
            non_regular.append(relative)
    known_template_files = all_known_surface_files()
    existing_template_files = [
        relative
        for relative in known_template_files
        if (target / relative).is_file()
    ]
    partial = []
    if config is not None and (target / GUIDANCE_PATH).is_file():
        expected = selected_project_paths(config)
        missing = [
            relative for relative in expected if not (target / relative).is_file()
        ]
        if missing:
            partial.append(
                f"selected {derive_policy(config).installation_surface} surface is "
                f"missing {len(missing)}/{len(expected)} generated files"
            )
    recommendations: list[str] = []
    if "Python" in language_counts or any(name.endswith((".toml", ".txt")) for name in manifests):
        recommendations.append("python")
    if (
        any(path.suffix.lower() == ".ipynb" for path in paths)
        or any(word in pyproject.lower() for word in ("pandas", "polars", "numpy", "scikit"))
        or "data" in {path.name.lower() for path in paths}
    ):
        recommendations.append("data-science")
    fastapi_signal = "fastapi" in pyproject.lower() or any(
        "fastapi" in (path.name.lower()) for path in paths
    )
    if fastapi_signal:
        recommendations.append("fastapi")
    package_signal = "package.json" in top_level and "react" in (
        _safe_file_text(target / "package.json") or ""
    ).lower()
    if package_signal:
        recommendations.append("react")
    recommendations = list(dict.fromkeys(recommendations))

    result = {
        "exists": True,
        "manifests": manifests,
        "languages": dict(sorted(language_counts.items())),
        "environment_managers": list(dict.fromkeys(managers)),
        "commands": commands,
        "git": {
            "present": (target / ".git").exists() or (target / ".git").is_symlink(),
            "worktree": (target / ".git").is_dir(),
        },
        "customizations": customizations,
        "customization_files": customization_files,
        "searchable_history_files": searchable_history_files,
        "known_template_files": existing_template_files,
        "partial_installations": partial,
        "apply_manifests_present": any(
            (target / relative).is_dir()
            for relative in (
                MANIFESTS_DIRECTORY,
                LEGACY_MANIFESTS_DIRECTORY,
            )
        ),
        "symlinks": sorted(set(symlinks)),
        "non_regular_files": sorted(set(non_regular)),
        "recommendations": recommendations,
        "scan_complete": not bool(scan_diagnostics),
        "scan_entries": scan_entries,
        "scan_entry_limit": scan_entry_limit,
        "scan_method": discovery_method,
        "scan_diagnostics": scan_diagnostics,
        "incomplete_areas": scan_diagnostics,
    }
    if config is not None:
        result["workflow_metrics"] = collect_project_metrics(
            target,
            paths,
            selected_files=selected_project_paths(config),
            known_surface_files=all_known_surface_files(),
            plan_tier=derive_policy(config).plan_tier,
            commands=config.commands,
            scan_complete=not bool(scan_diagnostics),
        )
    return result


def _read_context_file(target: Path, relative: str) -> bytes | None:
    try:
        path = _target_path(target, relative)
        if not path.is_file() or path.stat().st_size > 1_000_000:
            return None
        return path.read_bytes()
    except (OSError, SafetyError):
        return None


def _context_footprint(
    target: Path,
    facts: Mapping[str, Any],
    intended_files: Mapping[str, bytes],
    actions: Sequence[FileAction],
) -> dict[str, object]:
    candidates = {
        str(path)
        for path in facts.get("customization_files", [])
        if isinstance(path, str)
    }
    candidates.update(
        str(path)
        for path in facts.get("known_template_files", [])
        if isinstance(path, str)
    )
    candidates.update(intended_files)
    candidates.update((".vscode/mcp.json", GUIDANCE_PATH))
    current_files = {
        relative: content
        for relative in sorted(candidates)
        if (content := _read_context_file(target, relative)) is not None
    }
    safe_post_apply_files = dict(current_files)
    for action in actions:
        if action.status not in {"missing", "safe_merge"}:
            continue
        content = action.intended_content
        if content is not None:
            safe_post_apply_files[action.path] = content.encode("utf-8")
        elif action.path in intended_files:
            safe_post_apply_files[action.path] = intended_files[action.path]

    history_paths = [
        str(path)
        for path in facts.get("searchable_history_files", [])
        if isinstance(path, str)
    ]
    history_files = {
        relative: content
        for relative in history_paths
        if (content := _read_context_file(target, relative)) is not None
    }
    metrics = facts.get("workflow_metrics", {})
    active_plan = (
        metrics.get("active_plan", {})
        if isinstance(metrics, Mapping)
        else {}
    )
    return collect_context_footprint(
        current_files,
        safe_post_apply_files,
        active_plan=active_plan if isinstance(active_plan, Mapping) else {},
        searchable_history_files=history_files,
    )


def _source_root(source_root: Path | str | None) -> Path:
    root = Path(source_root) if source_root is not None else Path(__file__).resolve().parent
    if not root.is_dir():
        raise ApplyError(f"template source directory does not exist: {root}")
    return root


def _reject_template_target(target: Path, source: Path) -> None:
    try:
        target_resolved = target.resolve(strict=False)
        source_resolved = source.resolve(strict=True)
        if target_resolved == source_resolved or source_resolved in target_resolved.parents:
            raise SafetyError("target cannot be the template directory or one of its children")
    except OSError as error:
        raise SafetyError(f"cannot validate target/template boundary: {error}") from error


def _intended_files(config: WorkflowConfig, source_root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for relative in selected_files(config):
        if relative == CURRENT_TASK_PATH:
            files[relative] = ("# Current Task\n\n" + config.task_details.strip() + "\n").encode("utf-8")
            continue
        source = source_root / relative
        if not source.is_file():
            raise ApplyError(f"template is incomplete; missing source file: {relative}")
        files[relative] = render_template(source, config).encode("utf-8")

    if config.mcp_servers:
        files[".vscode/mcp.json"] = (
            json.dumps(
                build_mcp_config(config.mcp_servers, sandbox_local=config.sandbox_local),
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
    if (
        config.with_context_settings
        and derive_policy(config).installation_surface != "minimal"
    ):
        # Keep source settings authoritative for the generated exclusion set.
        settings_path = source_root / ".vscode/settings.json"
        if settings_path.is_file():
            files[".vscode/settings.json"] = render_template(settings_path, config).encode("utf-8")
    # Keep the installed guidance stable across re-analysis; volatile detected
    # facts remain in the in-memory report rather than causing drift.
    files[GUIDANCE_PATH] = render_guidance(config).encode("utf-8")
    if config.manage_artifact_gitignore and "data-science" in config.stack_profiles:
        # The merge is computed against the current target during analysis.
        files[".gitignore"] = GITIGNORE_ARTIFACT_BLOCK.encode("utf-8")
    return files


def _settings_merge(current: bytes, intended: bytes) -> tuple[str, bytes | None, str]:
    try:
        existing = json.loads(current.decode("utf-8"))
        generated = json.loads(intended.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return "conflicting_proposal", None, f"settings JSON is malformed: {error}"
    if not isinstance(existing, dict) or not isinstance(generated, dict):
        return "conflicting_proposal", None, "settings root must be a JSON object"
    generated_search = generated.get("search")
    generated_excludes = generated.get("search.exclude")
    if generated_excludes is None and isinstance(generated_search, Mapping):
        generated_excludes = generated_search.get("exclude")
    if generated_excludes is None:
        return "identical", current, "no artifact/search exclusions are defined"
    if not isinstance(generated_excludes, Mapping):
        return "conflicting_proposal", None, "artifact/search exclusions are not an object"
    existing_excludes = existing.get("search.exclude")
    if existing_excludes is None and isinstance(existing.get("search"), Mapping):
        existing_excludes = existing["search"].get("exclude")
    if existing_excludes is None:
        existing_excludes = {}
    if not isinstance(existing_excludes, dict):
        return "conflicting_proposal", None, "existing search exclusions are not an object"
    merged = json.loads(json.dumps(existing))
    if "search.exclude" in merged:
        destination = merged["search.exclude"]
    elif (
        isinstance(merged.get("search"), dict)
        and "exclude" in merged["search"]
    ):
        destination = merged["search"]["exclude"]
    elif "search.exclude" in generated:
        destination = merged.setdefault("search.exclude", {})
    else:
        search = merged.setdefault("search", {})
        if not isinstance(search, dict):
            return "conflicting_proposal", None, "existing search setting is not an object"
        destination = search.setdefault("exclude", {})
    if not isinstance(destination, dict):
        return "conflicting_proposal", None, "existing search exclusions are not an object"
    changed = False
    for key, value in generated_excludes.items():
        if key in destination and destination[key] != value:
            return "conflicting_proposal", None, f"existing exclusion conflicts for {key}"
        if key not in destination:
            destination[key] = value
            changed = True
    if not changed:
        return "identical", current, "all generated search exclusions already exist"
    return "safe_merge", (json.dumps(merged, indent=2) + "\n").encode("utf-8"), "added absent artifact/search exclusions only"


def gitignore_has_artifacts(content: str) -> bool:
    ignored = False
    probe = "artifacts/run/meta.json"
    for line in content.splitlines():
        pattern = line.strip().replace("\\", "/")
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        if negated:
            pattern = pattern[1:]
        pattern = pattern.lstrip("/").rstrip("/")
        variants = {pattern}
        while pattern.startswith("**/"):
            pattern = pattern[3:]
            variants.add(pattern)
        matches = any(
            fnmatch.fnmatchcase(probe, variant) or probe.startswith(f"{variant}/")
            for variant in variants
            if variant
        )
        if matches:
            ignored = not negated
    return ignored


def _gitignore_forward_merge(current: bytes) -> tuple[str, bytes | None, str]:
    try:
        content = current.decode("utf-8")
    except UnicodeDecodeError as error:
        return "unsafe", None, f"gitignore cannot be read as UTF-8: {error}"
    if gitignore_has_artifacts(content):
        return "identical", current, "an equivalent artifacts/ rule already exists"
    separator = "" if not content or content.endswith("\n") else "\n"
    return (
        "safe_merge",
        (content + separator + GITIGNORE_ARTIFACT_BLOCK).encode("utf-8"),
        "append the labeled artifacts/ rule without replacing existing rules",
    )


def _documented_settings_bytes() -> bytes:
    return (
        json.dumps({"search.exclude": GENERATED_SEARCH_EXCLUDES}, indent=2) + "\n"
    ).encode("utf-8")


SAFE_MERGE_PATHS = (".gitignore", ".vscode/settings.json")


def _allowed_merge_paths(config: WorkflowConfig) -> set[str]:
    allowed: set[str] = set()
    if config.manage_artifact_gitignore and "data-science" in config.stack_profiles:
        allowed.add(".gitignore")
    if (
        config.with_context_settings
        and derive_policy(config).installation_surface != "minimal"
    ):
        allowed.add(".vscode/settings.json")
    return allowed


def _action_for(
    target: Path,
    relative: str,
    intended: bytes,
    *,
    source_mode: int = 0o644,
) -> FileAction:
    destination = _target_path(target, relative)
    intended_hash = _sha256_bytes(intended)
    if not destination.exists():
        return FileAction(
            relative,
            "missing",
            "destination does not exist and can be added",
            intended_hash,
            None,
            intended.decode("utf-8", errors="replace"),
            _unified_diff(relative, None, intended),
            {"mode": source_mode},
        )
    if destination.is_symlink():
        return FileAction(relative, "unsafe", "destination is a symlink", intended_hash, None, intended.decode("utf-8", errors="replace"))
    if not destination.is_file():
        return FileAction(relative, "unsafe", "destination is not a regular file", intended_hash, None, intended.decode("utf-8", errors="replace"))
    try:
        current = destination.read_bytes()
    except OSError as error:
        return FileAction(relative, "unsafe", f"cannot read destination: {error}", intended_hash, None, intended.decode("utf-8", errors="replace"))
    current_hash = _sha256_bytes(current)
    if current == intended:
        return FileAction(
            relative,
            "identical",
            "destination already matches rendered content",
            intended_hash,
            current_hash,
            intended.decode("utf-8", errors="replace"),
            "",
            {"mode": _mode(destination)},
        )
    return FileAction(
        relative,
        "conflicting_proposal",
        "destination is user-owned and differs; review the rendered proposal manually",
        intended_hash,
        current_hash,
        intended.decode("utf-8", errors="replace"),
        _unified_diff(relative, current, intended),
        {"mode": _mode(destination)},
    )


def analyze_project(
    target: Path | str,
    config: WorkflowConfig | None = None,
    *,
    source_root: Path | str | None = None,
    include_health: bool = False,
) -> AnalysisReport:
    """Inspect a target without creating files, directories, or metadata."""

    target_path = _ensure_target_path(Path(target).expanduser(), allow_missing=True)
    config = config or config_for_target(target_path)
    validate_config(config)
    source = _source_root(source_root)
    _reject_template_target(target_path, source)
    facts = _detect_facts(target_path, config)
    proposed_mcp = (
        build_mcp_config(
            config.mcp_servers,
            sandbox_local=config.sandbox_local,
        )
        if config.mcp_servers
        else None
    )
    facts["mcp_security"] = collect_mcp_security(
        target_path,
        proposed=proposed_mcp,
        selected_servers=config.mcp_servers,
        require_sandbox=config.sandbox_local,
    )
    if include_health:
        facts["external_health"] = external_health(config, target_path)
    actions: list[FileAction] = []
    warnings: list[str] = []
    errors: list[str] = []
    recommendations: list[str] = list(facts.get("recommendations", []))
    if not target_path.exists():
        recommendations.append("target does not exist; new-project apply will create it")
    if len(facts.get("environment_managers", [])) > 1 and {"conda", "uv"}.issubset(
        facts["environment_managers"]
    ):
        warnings.append("Conda and uv markers both exist; preserve declarations and resolve ownership before dependency changes")
    if facts.get("symlinks"):
        warnings.append("symlinks were detected; destinations are never followed during apply")
    if facts.get("non_regular_files"):
        warnings.append("non-regular files were detected; affected destinations are not writable")
    for diagnostic in facts.get("scan_diagnostics", []):
        message = (
            f"{diagnostic.get('code', 'scan.incomplete')}: "
            f"{diagnostic.get('path', target_path)}: {diagnostic.get('message', 'inspection incomplete')}"
        )
        if diagnostic.get("severity") == "error":
            errors.append(message)
        else:
            warnings.append(message)
    warnings.extend(runtime_warnings(config))
    mcp_security = facts.get("mcp_security", {})
    if isinstance(mcp_security, Mapping):
        counts = mcp_security.get("counts", {})
        if isinstance(counts, Mapping) and any(
            isinstance(value, int) and value
            for value in counts.values()
        ):
            warnings.append(
                "MCP security audit found review items "
                f"(high={counts.get('high', 0)}, medium={counts.get('medium', 0)}, "
                f"low={counts.get('low', 0)}); values are redacted in facts.mcp_security"
            )
    metrics = facts.get("workflow_metrics", {})
    handoff = metrics.get("handoff", {}) if isinstance(metrics, Mapping) else {}
    if handoff and not handoff.get("within_budget", True):
        warnings.append(
            "active handoff exceeds the configured 40-line/3 KB budget; rewrite "
            "current state instead of appending history"
        )
    plan = metrics.get("active_plan", {}) if isinstance(metrics, Mapping) else {}
    if plan and not plan.get("valid", True):
        warnings.append(
            "active plan pointer or tier budget is invalid; review task state before resuming"
        )
    legacy = (
        metrics.get("legacy_surface_candidates", [])
        if isinstance(metrics, Mapping)
        else []
    )
    if legacy:
        recommendations.append(
            f"{len(legacy)} previous workflow files are outside the selected "
            "surface; review the manual cleanup list (nothing is deleted)"
        )
    ratios = metrics.get("ratios", {}) if isinstance(metrics, Mapping) else {}
    if isinstance(ratios, Mapping):
        workflow_ratio = ratios.get("workflow_to_production")
        if isinstance(workflow_ratio, (int, float)) and workflow_ratio >= 0.5:
            recommendations.append(
                "workflow guidance is large relative to production code; prefer "
                "the smaller installation surface unless risk justifies it"
            )

    try:
        intended_files = _intended_files(config, source)
    except (ApplyError, ConfigError) as error:
        errors.append(str(error))
        intended_files = {}

    for relative, intended in intended_files.items():
        if relative == ".gitignore":
            destination = target_path / relative
            if destination.is_symlink():
                actions.append(FileAction(relative, "unsafe", "destination is a symlink", _sha256_bytes(intended), None, GITIGNORE_ARTIFACT_BLOCK))
                continue
            if not destination.exists():
                actions.append(FileAction(relative, "missing", "artifact ignore rule can be added", _sha256_bytes(intended), None, GITIGNORE_ARTIFACT_BLOCK, _unified_diff(relative, None, intended)))
                continue
            if not destination.is_file():
                actions.append(FileAction(relative, "unsafe", "gitignore is not a regular file", _sha256_bytes(intended), None, GITIGNORE_ARTIFACT_BLOCK))
                continue
            try:
                current = destination.read_bytes()
            except OSError as error:
                actions.append(
                    FileAction(
                        relative,
                        "unsafe",
                        f"cannot read gitignore: {error}",
                        _sha256_bytes(intended),
                        None,
                        GITIGNORE_ARTIFACT_BLOCK,
                    )
                )
                continue
            status, merged, reason = _gitignore_forward_merge(current)
            if status == "unsafe" or merged is None:
                actions.append(
                    FileAction(
                        relative,
                        "unsafe",
                        reason,
                        _sha256_bytes(intended),
                        _sha256_bytes(current),
                        GITIGNORE_ARTIFACT_BLOCK,
                    )
                )
            elif status == "identical":
                actions.append(
                    FileAction(
                        relative,
                        status,
                        reason,
                        _sha256_bytes(intended),
                        _sha256_bytes(current),
                        current.decode("utf-8"),
                        "",
                        {"mode": _mode(destination)},
                    )
                )
            else:
                actions.append(
                    FileAction(
                        relative,
                        status,
                        reason,
                        _sha256_bytes(merged),
                        _sha256_bytes(current),
                        merged.decode("utf-8"),
                        _unified_diff(relative, current, merged),
                        {"mode": _mode(destination), "merge": "additive-artifacts-rule"},
                    )
                )
            continue
        if relative == ".vscode/settings.json":
            try:
                settings_destination = _target_path(target_path, relative)
            except SafetyError as error:
                actions.append(
                    FileAction(
                        relative,
                        "unsafe",
                        str(error),
                        _sha256_bytes(intended),
                        None,
                        intended.decode("utf-8", errors="replace"),
                    )
                )
                continue
        else:
            settings_destination = None
        if relative == ".vscode/settings.json" and settings_destination is not None and settings_destination.is_symlink():
            actions.append(
                FileAction(
                    relative,
                    "unsafe",
                    "destination is a symlink",
                    _sha256_bytes(intended),
                    None,
                    intended.decode("utf-8", errors="replace"),
                )
            )
            continue
        if (
            relative == ".vscode/settings.json"
            and settings_destination is not None
            and settings_destination.exists()
        ):
            try:
                current = settings_destination.read_bytes()
            except OSError as error:
                actions.append(FileAction(relative, "unsafe", f"cannot read settings: {error}", None, None, intended.decode("utf-8")))
                continue
            status, merged, reason = _settings_merge(current, intended)
            if status == "safe_merge" and merged is not None:
                actions.append(FileAction(relative, status, reason, _sha256_bytes(merged), _sha256_bytes(current), merged.decode("utf-8"), _unified_diff(relative, current, merged), {"mode": _mode(settings_destination), "merge": "absent-search-exclusions-only"}))
            elif status == "identical":
                actions.append(FileAction(relative, status, reason, _sha256_bytes(intended), _sha256_bytes(current), intended.decode("utf-8"), "", {"mode": _mode(settings_destination)}))
            else:
                actions.append(FileAction(relative, "conflicting_proposal", reason, _sha256_bytes(intended), _sha256_bytes(current), intended.decode("utf-8"), _unified_diff(relative, current, intended), {"mode": _mode(settings_destination)}))
            continue
        try:
            mode = (source / relative).stat().st_mode & 0o777 if (source / relative).exists() else 0o644
            actions.append(_action_for(target_path, relative, intended, source_mode=mode))
        except SafetyError as error:
            actions.append(FileAction(relative, "unsafe", str(error), _sha256_bytes(intended), None, intended.decode("utf-8", errors="replace")))

    directories = list(required_project_directories(config))
    directory_states: list[dict[str, Any]] = []
    for relative in directories:
        directory = target_path / relative
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            errors.append(f"unsafe required directory {relative}")
            directory_states.append({"path": relative, "status": "unsafe"})
        elif directory.exists():
            directory_states.append({"path": relative, "status": "existing"})
        else:
            directory_states.append({"path": relative, "status": "missing"})
    if not facts["exists"] and config.workflow == "existing":
        errors.append("existing-project workflow requires a target directory that already exists")
    if policy_requires_guard := derive_policy(config).require_protocol_guard:
        if not config.protocol_guard and config.rigor_preset != "strong":
            recommendations.append("strong risk policy enabled the reviewed local protocol guard")
        if policy_requires_guard:
            recommendations.append("protocol guard checks only local handoff/plan/change-isolation facts; it cannot claim external memory success")
    facts["context_footprint"] = _context_footprint(
        target_path,
        facts,
        intended_files,
        actions,
    )
    recommendations = list(dict.fromkeys(recommendations))
    return AnalysisReport(
        target=str(target_path),
        config=config,
        facts=facts,
        actions=actions,
        directories=directories,
        directory_states=directory_states,
        warnings=warnings,
        errors=errors,
        recommendations=recommendations,
        generated_guidance=render_guidance(config, facts),
    )


def _write_new_bytes(path: Path, content: bytes, mode: int) -> None:
    _reject_symlink_or_nonregular(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    owned_writes = _ACTIVE_OWNED_WRITES.get()
    if owned_writes is not None:
        owned_writes.append(path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(path, mode)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)
        raise


def _cleanup_created(paths: Iterable[Path], directories: Iterable[Path]) -> None:
    for path in sorted(paths, key=lambda item: len(item.parts), reverse=True):
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
        except OSError:
            pass
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def install_legacy(
    target: Path | str,
    config: WorkflowConfig,
    *,
    source_root: Path | str | None = None,
    dry_run: bool = False,
) -> ApplyResult:
    """Preserve the original collision-refusing installer through core paths."""

    return apply_project(
        target,
        config,
        source_root=source_root,
        collision_policy="refuse",
        dry_run=dry_run,
        write_manifest=False,
    )


def _resolve_manifest(
    manifest: Path | str | None,
    target: Path | str | None,
) -> tuple[Path, Path | None]:
    target_path = (
        _ensure_target_path(Path(target).expanduser(), allow_missing=False)
        if target is not None
        else None
    )
    value = "" if manifest is None else str(manifest)
    if value in {"", "."}:
        if target_path is None:
            raise RollbackError(
                "a target or manifest path is required for restore instructions"
            )
        candidates = [
            (created_at, path)
            for created_at, path, _data in _material_manifests(target_path)
        ]
        if not candidates:
            raise RollbackError(
                "no apply manifests found under "
                f"{target_path / MANIFESTS_DIRECTORY} or "
                f"{target_path / LEGACY_MANIFESTS_DIRECTORY}"
            )
        newest_created = max(item[0] for item in candidates)
        newest = [item for item in candidates if item[0] == newest_created]
        if len(newest) > 1:
            raise RollbackError(
                "apply manifests have an ambiguous latest timestamp; "
                "specify MANIFEST_OR_ID explicitly"
            )
        return newest[0][1], target_path

    candidate = Path(value).expanduser()
    if not candidate.is_file() and target_path is not None:
        normalized = value.replace("\\", "/")
        if (
            not normalized.startswith(("/", "//"))
            and ".." not in Path(normalized).parts
            and not re.match(r"^[A-Za-z]:/", normalized)
        ):
            filename = (
                normalized if normalized.endswith(".json") else f"{normalized}.json"
            )
            for relative in (
                MANIFESTS_DIRECTORY,
                LEGACY_MANIFESTS_DIRECTORY,
            ):
                possible = target_path / relative / filename
                if possible.is_file() and not possible.is_symlink():
                    candidate = possible
                    break
    if not candidate.is_file() or candidate.is_symlink():
        raise RollbackError(f"apply manifest does not exist or is unsafe: {manifest}")
    return candidate, target_path


def _manifest_time(path: Path) -> datetime:
    try:
        value = manifest_state.load(path).get("created_at")
        if not isinstance(value, str):
            raise ValueError
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp.astimezone(timezone.utc)
    except (ValueError, manifest_state.ManifestError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _material_manifests(target: Path) -> list[tuple[datetime, Path, dict[str, Any]]]:
    manifests: list[tuple[datetime, Path, dict[str, Any]]] = []
    for relative in (
        MANIFESTS_DIRECTORY,
        LEGACY_MANIFESTS_DIRECTORY,
    ):
        directory = target / relative
        if directory.is_symlink() or not directory.is_dir():
            continue
        for path in directory.glob("*.json"):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                data = manifest_state.load(path)
            except manifest_state.ManifestError:
                continue
            created = data.get("created_files", [])
            merges = data.get("safe_merges", [])
            if not (
                isinstance(created, list)
                and isinstance(merges, list)
                and (created or merges)
            ):
                continue
            manifest_target = data.get("target")
            if (
                not isinstance(manifest_target, str)
                or Path(manifest_target).expanduser().resolve(strict=False)
                != target.resolve(strict=False)
            ):
                continue
            manifests.append((_manifest_time(path), path, data))
    return sorted(manifests, key=lambda item: (item[0], item[1].name))


def _manual_path_state(target: Path, entry: Mapping[str, Any]) -> str:
    relative = entry.get("path")
    if not isinstance(relative, str) or not _safe_relative(relative):
        return "manual"
    path = target / relative
    if path.is_symlink() or not path.is_file():
        return "missing"
    expected = entry.get("sha256")
    try:
        current = _sha256_file(path)
        mode = _mode(path)
    except (OSError, SafetyError):
        return "manual"
    return (
        "present"
        if current == expected and mode == entry.get("mode")
        else "manual"
    )


def _manual_merge_state(target: Path, entry: Mapping[str, Any]) -> str:
    destination = entry.get("path")
    backup = entry.get("backup")
    if (
        not isinstance(destination, str)
        or not isinstance(backup, str)
        or not _safe_relative(destination)
        or not _safe_relative(backup)
    ):
        return "manual"
    destination_path = target / destination
    backup_path = target / backup
    if (
        destination_path.is_symlink()
        or backup_path.is_symlink()
        or not destination_path.is_file()
        or not backup_path.is_file()
    ):
        return "missing"
    try:
        current = _sha256_file(destination_path)
        original = _sha256_file(backup_path)
        destination_mode = _mode(destination_path)
        backup_mode = _mode(backup_path)
    except (OSError, SafetyError):
        return "manual"
    if (
        current == entry.get("after_sha256")
        and original == entry.get("before_sha256")
        and destination_mode == entry.get("after_mode")
        and backup_mode == entry.get("before_mode")
    ):
        return "ready"
    if (
        current == entry.get("before_sha256")
        and original == entry.get("before_sha256")
        and destination_mode == entry.get("before_mode")
        and backup_mode == entry.get("before_mode")
    ):
        return "already-restored"
    return "manual"


def _current_after_matches(
    target: Path,
    entry: Mapping[str, Any],
    *,
    merge: bool,
) -> bool:
    relative = entry.get("path")
    expected_hash = entry.get("after_sha256" if merge else "sha256")
    expected_mode = entry.get("after_mode" if merge else "mode")
    if (
        not isinstance(relative, str)
        or not _safe_relative(relative)
        or not isinstance(expected_hash, str)
        or not isinstance(expected_mode, int)
    ):
        return False
    path = target / relative
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return _sha256_file(path) == expected_hash and _mode(path) == expected_mode
    except (OSError, SafetyError):
        return False


def _aggregate_restore_material(
    manifests: Sequence[tuple[datetime, Path, dict[str, Any]]],
    target: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    created_by_path: dict[
        str, list[tuple[datetime, Path, int, dict[str, Any]]]
    ] = {}
    merges_by_path: dict[
        str, list[tuple[datetime, Path, int, dict[str, Any]]]
    ] = {}
    directories_by_path: dict[str, dict[str, Any]] = {}
    for created_at, manifest_path, data in manifests:
        for index, entry in enumerate(data.get("created_files", [])):
            if isinstance(entry, Mapping) and isinstance(entry.get("path"), str):
                created_by_path.setdefault(entry["path"], []).append(
                    (created_at, manifest_path, index, dict(entry))
                )
        for index, entry in enumerate(data.get("safe_merges", [])):
            if isinstance(entry, Mapping) and isinstance(entry.get("path"), str):
                merges_by_path.setdefault(entry["path"], []).append(
                    (created_at, manifest_path, index, dict(entry))
                )
        for entry in data.get("required_directories", []):
            if isinstance(entry, Mapping) and isinstance(entry.get("path"), str):
                directories_by_path.setdefault(entry["path"], dict(entry))

    history: list[dict[str, Any]] = []

    def choose(
        grouped: dict[str, list[tuple[datetime, Path, int, dict[str, Any]]]],
        *,
        merge: bool,
    ) -> list[dict[str, Any]]:
        active: list[dict[str, Any]] = []
        for path in sorted(grouped):
            entries = sorted(grouped[path], key=lambda item: (item[0], item[1].name, item[2]))
            matching = [
                item for item in entries if _current_after_matches(target, item[3], merge=merge)
            ]
            selected = (matching or entries)[-1]
            for item in entries:
                state = (
                    _manual_merge_state(target, item[3])
                    if merge
                    else _manual_path_state(target, item[3])
                )
                rendered = dict(
                    item[3],
                    manifest_path=str(item[1]),
                    state=state,
                )
                if item is selected:
                    active.append(rendered)
                else:
                    history.append(
                        dict(
                            rendered,
                            kind="safe_merge" if merge else "generated",
                            history=True,
                        )
                    )
        return active

    created = choose(created_by_path, merge=False)
    merges = choose(merges_by_path, merge=True)
    history.sort(
        key=lambda item: (
            str(item.get("kind")),
            str(item.get("path")),
            str(item.get("manifest_path")),
        )
    )
    return (
        created,
        merges,
        [directories_by_path[path] for path in sorted(directories_by_path)],
        history,
    )


def preview_project(
    target: Path | str,
    config: WorkflowConfig | None = None,
    *,
    source_root: Path | str | None = None,
    output: Path | str | None = None,
) -> AnalysisReport:
    """Analyze and optionally write a report only to an explicit output path."""

    report = analyze_project(target, config, source_root=source_root)
    if output is not None:
        output_path = Path(output).expanduser()
        if output_path.is_symlink():
            raise SafetyError(f"refusing symlink preview output: {output_path}")
        _ensure_output_parent(output_path.parent)
        _atomic_write(output_path, report.to_json().encode("utf-8"), 0o644)
    return report


# Concise names are convenient for embedders while the longer names remain the
# canonical documentation API.
Config = WorkflowConfig
ConfigModel = WorkflowConfig
analyze = analyze_project
preview = preview_project
safe_apply = apply_project
rollback = rollback_project


__all__ = [
    "AnalysisReport",
    "Config",
    "ConfigModel",
    "analyze",
    "ApplyError",
    "ApplyResult",
    "BACKUPS_DIRECTORY",
    "MANIFESTS_DIRECTORY",
    "LEGACY_BACKUPS_DIRECTORY",
    "LEGACY_MANIFESTS_DIRECTORY",
    "CONFIG_FILENAME",
    "LEGACY_CONFIG_FILENAME",
    "CONFIG_VERSION",
    "ConfigError",
    "CORE_FILES",
    "EngineeringPolicy",
    "FileAction",
    "GUIDANCE_PATH",
    "GENERATED_SEARCH_EXCLUDES",
    "KNOWN_REQUIRED_DIRECTORIES",
    "LEAN_CHANGE_CONTRACT",
    "MCP_NAMES",
    "MAX_BLOB_RESPONSE_BYTES",
    "OPTIONAL_INTEGRATIONS",
    "OPTIONAL_INTEGRATION_NAMES",
    "PluginExportError",
    "PluginExportPlan",
    "PROFILE_FILES",
    "RIGOR_ALIASES",
    "RollbackError",
    "SCAN_ENTRY_LIMITS",
    "SAFE_MERGE_PATHS",
    "SafetyError",
    "TEMPLATE_VERSION",
    "VALID_COMPLEXITIES",
    "VALID_SIZES",
    "VALID_TESTING_LEVELS",
    "VALID_WORKFLOWS",
    "VALID_RIGOR_PRESETS",
    "WorkflowConfig",
    "REVIEW_DISPOSITIONS",
    "UpstreamAssetReview",
    "UpstreamError",
    "UpstreamReport",
    "UpstreamReviewItem",
    "UpstreamUpdateService",
    "analyze_project",
    "audit_mcp_configuration",
    "apply_project",
    "build_asset_review",
    "build_upstream_report",
    "build_mcp_config",
    "config_for_target",
    "config_json",
    "continuity_summary",
    "derive_policy",
    "export_config",
    "export_local_plugin",
    "export_review_brief",
    "gitignore_has_artifacts",
    "guidance",
    "load_config",
    "load_cached_report",
    "import_config",
    "install_legacy",
    "preview_project",
    "preview_local_plugin",
    "preview",
    "policy_override_catalog",
    "recommended_integrations",
    "render_asset_review",
    "render_context_footprint",
    "render_guidance",
    "render_plugin_preview",
    "render_policy_override_guide",
    "render_review_brief",
    "render_values",
    "render_upstream_report",
    "runtime_warnings",
    "save_cached_report",
    "rigor_presets",
    "render_restore_instructions",
    "restore_instructions",
    "rollback_project",
    "rollback",
    "safe_apply",
    "save_config",
    "selected_files",
    "update_check_due",
    "upstream_asset_request_urls",
    "upstream_review_items",
    "upstream_request_urls",
    "validate_config",
    "validate_target",
]
