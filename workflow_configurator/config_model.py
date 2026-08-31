"""Versioned workflow configuration and conservative legacy migration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalog import MCP_NAMES, OPTIONAL_INTEGRATION_NAMES, PROFILE_FILES


CONFIG_VERSION = 2
LEGACY_CONFIG_VERSION = 1
DEFAULT_PROFILES: tuple[str, ...] = ()
DEFAULT_SUMMARY = "Project using Himanshu's adaptive local agent workflow."
LEGACY_DEFAULT_PROFILES = ("python", "data-science")
LEGACY_DEFAULT_SUMMARY = (
    "Personal Python and data-science project using Himanshu's agent workflow."
)
DEFAULT_COMMANDS = {
    "test": "pytest -x -q",
    "lint": "ruff check .",
    "typecheck": "pyright",
    "run": "none",
}
VALID_COMPLEXITIES = ("minimal", "standard", "advanced")
VALID_SIZES = ("small", "medium", "large")
VALID_TESTING_LEVELS = ("none", "focused", "broad")
VALID_WORKFLOWS = ("new", "existing")
VALID_RIGOR_PRESETS = ("light", "standard", "strong")
VALID_SESSION_PROFILES = (
    "auto",
    "quick-docs",
    "resume-history",
    "large-code",
    "symbol-refactor",
    "data-analysis",
    "document-ingestion",
    "ml-model",
    "pr-issues",
)
POLICY_DIMENSION_VALUES: dict[str, tuple[str, ...]] = {
    "installation_surface": ("minimal", "standard", "governed"),
    "plan_tier": ("none", "mini", "compact", "governed"),
    "validation_tier": ("none", "focused", "broad"),
    "documentation_tier": ("changed-only", "handoff", "full"),
    "memory_policy": ("off", "on-demand", "required"),
    "code_intelligence_policy": ("off", "on-demand", "required"),
    "review_tier": ("self", "independent"),
    "protocol_guard": ("off", "on"),
}
RIGOR_ALIASES = {
    "low": "light",
    "minimal": "light",
    "medium": "standard",
    "normal": "standard",
    "high": "strong",
    "governed": "strong",
    "strict": "strong",
}


class ConfigError(ValueError):
    """Raised when a configuration is malformed or violates its contract."""


def canonical_memory_wing(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "project"


def canonical_codebase_project_id(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_.-")
    return identifier or "project"


def _require_string(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string")
    result = value.strip()
    if not result and not allow_empty:
        raise ConfigError(f"{field_name} must not be empty")
    return result


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a boolean")
    return value


def _unique_strings(value: Any, field_name: str, allowed: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"{field_name} must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(f"{field_name} must contain non-empty strings")
        item = item.strip()
        if item not in allowed:
            raise ConfigError(
                f"unsupported {field_name} value {item!r}; choose from {', '.join(allowed)}"
            )
        if item not in result:
            result.append(item)
    return tuple(result)


def _structured_override(
    dimension: str, value: Any, *, reason: Any = ""
) -> dict[str, str]:
    if dimension not in POLICY_DIMENSION_VALUES:
        raise ConfigError(
            f"unknown policy override {dimension!r}; choose from "
            + ", ".join(POLICY_DIMENSION_VALUES)
        )
    if not isinstance(value, str) or value not in POLICY_DIMENSION_VALUES[dimension]:
        raise ConfigError(
            f"policy_overrides.{dimension}.value must be one of: "
            + ", ".join(POLICY_DIMENSION_VALUES[dimension])
        )
    if not isinstance(reason, str):
        raise ConfigError(f"policy_overrides.{dimension}.reason must be a string")
    return {"value": value, "reason": reason.strip()}


def _migrate_v1_policy_overrides(raw: Any) -> dict[str, dict[str, str]]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ConfigError("policy_overrides must be a JSON object")
    migrated: dict[str, dict[str, str]] = {}
    unresolved: list[str] = []
    for name, value in raw.items():
        reason = f"Migrated from config v1 override {name}"
        if name == "install_guard" and isinstance(value, bool):
            migrated["protocol_guard"] = _structured_override(
                "protocol_guard", "on" if value else "off", reason=reason
            )
        elif name == "require_review" and isinstance(value, bool):
            migrated["review_tier"] = _structured_override(
                "review_tier", "independent" if value else "self", reason=reason
            )
        elif name == "require_memory" and isinstance(value, bool):
            migrated["memory_policy"] = _structured_override(
                "memory_policy", "required" if value else "off", reason=reason
            )
        elif name == "require_code_intelligence" and isinstance(value, bool):
            migrated["code_intelligence_policy"] = _structured_override(
                "code_intelligence_policy",
                "required" if value else "off",
                reason=reason,
            )
        elif name == "require_plan" and value is False:
            migrated["plan_tier"] = _structured_override(
                "plan_tier", "none", reason=reason
            )
        elif name == "require_approval" and value is True:
            continue
        elif name == "require_approval" and value is False:
            raise ConfigError(
                "legacy policy_overrides.require_approval=false cannot be migrated; "
                "approval and destructive-operation safeguards are no longer overridable"
            )
        else:
            unresolved.append(str(name))
    if unresolved:
        raise ConfigError(
            "legacy policy override(s) require manual review before config v2 import: "
            + ", ".join(sorted(unresolved))
        )
    return migrated


@dataclass(frozen=True)
class WorkflowConfig:
    version: int = CONFIG_VERSION
    project_name: str = "project"
    summary: str = DEFAULT_SUMMARY
    workflow: str = "new"
    complexity: str = "standard"
    project_size: str = "small"
    testing_level: str = "focused"
    stack_profiles: tuple[str, ...] = DEFAULT_PROFILES
    mcp_servers: tuple[str, ...] = ()
    optional_integrations: tuple[str, ...] = ()
    commands: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_COMMANDS))
    rigor_preset: str = "standard"
    policy_overrides: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    memory_wing: str = ""
    codebase_project_id: str = ""
    session_profile: str = "auto"
    with_security_hooks: bool = False
    with_context_settings: bool = True
    manage_artifact_gitignore: bool = True
    sandbox_local: bool = True
    protocol_guard: bool | None = None

    def __post_init__(self) -> None:
        if not self.memory_wing:
            object.__setattr__(self, "memory_wing", canonical_memory_wing(self.project_name))
        if not self.codebase_project_id:
            object.__setattr__(
                self,
                "codebase_project_id",
                canonical_codebase_project_id(self.project_name),
            )
        validate_config(self)

    @property
    def size(self) -> str:
        return self.project_size

    @property
    def testing(self) -> str:
        return self.testing_level

    @property
    def profiles(self) -> tuple[str, ...]:
        return self.stack_profiles

    @property
    def mcp(self) -> tuple[str, ...]:
        return self.mcp_servers

    @property
    def rigor(self) -> str:
        return self.rigor_preset

    @property
    def policy(self):
        from .policy import derive_policy

        return derive_policy(self)

    rigor_policy = policy

    def validate(self) -> "WorkflowConfig":
        validate_config(self)
        return self

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2) + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_name": self.project_name,
            "summary": self.summary,
            "workflow": self.workflow,
            "complexity": self.complexity,
            "project_size": self.project_size,
            "testing_level": self.testing_level,
            "stack_profiles": list(self.stack_profiles),
            "mcp_servers": list(self.mcp_servers),
            "optional_integrations": list(self.optional_integrations),
            "commands": {name: self.commands[name] for name in sorted(self.commands)},
            "rigor_preset": self.rigor_preset,
            "policy_overrides": {
                name: dict(self.policy_overrides[name])
                for name in sorted(self.policy_overrides)
            },
            "memory_wing": self.memory_wing,
            "codebase_project_id": self.codebase_project_id,
            "session_profile": self.session_profile,
            "with_security_hooks": self.with_security_hooks,
            "with_context_settings": self.with_context_settings,
            "manage_artifact_gitignore": self.manage_artifact_gitignore,
            "sandbox_local": self.sandbox_local,
            "protocol_guard": self.protocol_guard,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "WorkflowConfig":
        if not isinstance(raw, Mapping):
            raise ConfigError("configuration root must be a JSON object")
        allowed = {
            "version",
            "project_name",
            "summary",
            "workflow",
            "complexity",
            "project_size",
            "size",
            "scope",
            "testing_level",
            "testing",
            "stack_profiles",
            "profiles",
            "mcp_servers",
            "mcp",
            "mcp_choices",
            "optional_integrations",
            "integrations",
            "commands",
            "command_overrides",
            "rigor_preset",
            "rigor",
            "engineering_rigor",
            "policy_overrides",
            "memory_wing",
            "codebase_project_id",
            "session_profile",
            "with_security_hooks",
            "with_context_settings",
            "manage_artifact_gitignore",
            "sandbox_local",
            "protocol_guard",
        }
        unknown = sorted(str(key) for key in set(raw) - allowed)
        if unknown:
            raise ConfigError(f"unknown configuration field(s): {', '.join(unknown)}")
        if "version" not in raw:
            raise ConfigError("configuration version is required")
        version = raw.get("version")
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version not in {LEGACY_CONFIG_VERSION, CONFIG_VERSION}
        ):
            raise ConfigError(
                f"unsupported configuration version {version!r}; expected "
                f"{LEGACY_CONFIG_VERSION} or {CONFIG_VERSION}"
            )

        def choose(name: str, aliases: Sequence[str], default: Any) -> Any:
            present = [candidate for candidate in (name, *aliases) if candidate in raw]
            if len(present) > 1:
                first = raw[present[0]]
                if any(raw[candidate] != first for candidate in present[1:]):
                    raise ConfigError(
                        f"conflicting configuration aliases: {', '.join(present)}"
                    )
            return raw[present[0]] if present else default

        commands_raw = choose("commands", ("command_overrides",), DEFAULT_COMMANDS)
        if not isinstance(commands_raw, Mapping):
            raise ConfigError("commands must be a JSON object")
        commands = {
            str(name).strip(): _require_string(
                value, f"commands.{name}", allow_empty=True
            )
            or "none"
            for name, value in commands_raw.items()
            if isinstance(name, str) and name.strip()
        }
        if len(commands) != len(commands_raw):
            raise ConfigError("commands keys must be non-empty strings")
        for name in ("test", "lint", "typecheck", "run"):
            commands.setdefault(name, DEFAULT_COMMANDS[name])

        overrides_raw = raw.get("policy_overrides", {})
        overrides = (
            _migrate_v1_policy_overrides(overrides_raw)
            if version == LEGACY_CONFIG_VERSION
            else overrides_raw
        )
        if not isinstance(overrides, Mapping):
            raise ConfigError("policy_overrides must be a JSON object")
        rigor = choose("rigor_preset", ("rigor", "engineering_rigor"), "standard")
        rigor = _require_string(rigor, "rigor_preset").lower()
        rigor = RIGOR_ALIASES.get(rigor, rigor)
        project_name = _require_string(raw.get("project_name", "project"), "project_name")
        if version == LEGACY_CONFIG_VERSION and raw.get("protocol_guard") is not None:
            guard = _require_bool(raw.get("protocol_guard"), "protocol_guard")
            migrated_guard = _structured_override(
                "protocol_guard",
                "on" if guard else "off",
                reason="Migrated from config v1 protocol_guard",
            )
            existing_guard = overrides.get("protocol_guard")
            if (
                existing_guard is not None
                and existing_guard.get("value") != migrated_guard["value"]
            ):
                raise ConfigError(
                    "conflicting config v1 protocol_guard and install_guard values"
                )
            if existing_guard is None:
                overrides = {**overrides, "protocol_guard": migrated_guard}
        if version == CONFIG_VERSION and raw.get("protocol_guard") is not None:
            raise ConfigError(
                "top-level protocol_guard is a config v1 field; use the structured "
                "policy_overrides.protocol_guard value and reason"
            )
        default_summary = (
            LEGACY_DEFAULT_SUMMARY
            if version == LEGACY_CONFIG_VERSION
            else DEFAULT_SUMMARY
        )
        default_profiles = (
            LEGACY_DEFAULT_PROFILES
            if version == LEGACY_CONFIG_VERSION
            else DEFAULT_PROFILES
        )
        profiles = _unique_strings(
            choose("stack_profiles", ("profiles",), list(default_profiles)),
            "stack_profiles",
            tuple(PROFILE_FILES),
        )
        integrations = list(
            _unique_strings(
                choose("optional_integrations", ("integrations",), []),
                "optional_integrations",
                OPTIONAL_INTEGRATION_NAMES,
            )
        )
        if (
            version == LEGACY_CONFIG_VERSION
            and "data-science" in profiles
            and "experiment-runner" not in integrations
        ):
            integrations.append("experiment-runner")
        return cls(
            version=CONFIG_VERSION,
            project_name=project_name,
            summary=_require_string(
                raw.get("summary", default_summary), "summary", allow_empty=True
            ),
            workflow=_require_string(raw.get("workflow", "new"), "workflow").lower(),
            complexity=_require_string(raw.get("complexity", "standard"), "complexity").lower(),
            project_size=_require_string(
                choose("project_size", ("size", "scope"), "small"), "project_size"
            ).lower(),
            testing_level=_require_string(
                choose("testing_level", ("testing",), "focused"), "testing_level"
            ).lower(),
            stack_profiles=profiles,
            mcp_servers=_unique_strings(
                choose("mcp_servers", ("mcp", "mcp_choices"), []),
                "mcp_servers",
                MCP_NAMES,
            ),
            optional_integrations=tuple(integrations),
            commands=commands,
            rigor_preset=rigor,
            policy_overrides={
                str(name): dict(value) if isinstance(value, Mapping) else value
                for name, value in overrides.items()
            },
            memory_wing=_require_string(
                raw.get("memory_wing", canonical_memory_wing(project_name)),
                "memory_wing",
            ),
            codebase_project_id=_require_string(
                raw.get(
                    "codebase_project_id",
                    canonical_codebase_project_id(project_name),
                ),
                "codebase_project_id",
            ),
            session_profile=_require_string(
                raw.get("session_profile", "auto"), "session_profile"
            ).lower(),
            with_security_hooks=_require_bool(
                raw.get("with_security_hooks", False), "with_security_hooks"
            ),
            with_context_settings=_require_bool(
                raw.get("with_context_settings", True), "with_context_settings"
            ),
            manage_artifact_gitignore=_require_bool(
                raw.get("manage_artifact_gitignore", True),
                "manage_artifact_gitignore",
            ),
            sandbox_local=_require_bool(raw.get("sandbox_local", True), "sandbox_local"),
            protocol_guard=None,
        )


def validate_config(config: WorkflowConfig) -> None:
    if config.version != CONFIG_VERSION or isinstance(config.version, bool):
        raise ConfigError(f"unsupported configuration version {config.version!r}")
    if not isinstance(config.project_name, str) or not config.project_name.strip():
        raise ConfigError("project_name must not be empty")
    if not isinstance(config.summary, str):
        raise ConfigError("summary must be a string")
    for name, value, allowed in (
        ("workflow", config.workflow, VALID_WORKFLOWS),
        ("complexity", config.complexity, VALID_COMPLEXITIES),
        ("project_size", config.project_size, VALID_SIZES),
        ("testing_level", config.testing_level, VALID_TESTING_LEVELS),
        ("rigor_preset", config.rigor_preset, VALID_RIGOR_PRESETS),
        ("session_profile", config.session_profile, VALID_SESSION_PROFILES),
    ):
        if value not in allowed:
            raise ConfigError(f"{name} must be one of: {', '.join(allowed)}")
    _unique_strings(config.stack_profiles, "stack_profiles", tuple(PROFILE_FILES))
    _unique_strings(config.mcp_servers, "mcp_servers", MCP_NAMES)
    _unique_strings(
        config.optional_integrations,
        "optional_integrations",
        OPTIONAL_INTEGRATION_NAMES,
    )
    if {"openspec", "spec-kit"} <= set(config.optional_integrations):
        raise ConfigError("choose one specification workflow: openspec or spec-kit, not both")
    if not isinstance(config.commands, Mapping):
        raise ConfigError("commands must be a mapping")
    for name, value in config.commands.items():
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("commands keys must be non-empty strings")
        if not isinstance(value, str):
            raise ConfigError(f"commands.{name} must be a string")
    for name in ("test", "lint", "typecheck", "run"):
        if name not in config.commands:
            raise ConfigError(f"commands.{name} is required")
    if canonical_memory_wing(config.memory_wing) != config.memory_wing:
        raise ConfigError(
            "memory_wing must be a canonical lowercase identifier using letters, "
            "numbers, and underscores"
        )
    if config.memory_wing == "wing_copilot":
        raise ConfigError(
            "memory_wing 'wing_copilot' is reserved for cross-project lessons; "
            "choose a distinct canonical project wing"
        )
    if canonical_codebase_project_id(config.codebase_project_id) != config.codebase_project_id:
        raise ConfigError(
            "codebase_project_id must use letters, numbers, dots, dashes, or underscores"
        )
    if not isinstance(config.policy_overrides, Mapping):
        raise ConfigError("policy_overrides must be a mapping")
    for name, decision in config.policy_overrides.items():
        if not isinstance(decision, Mapping):
            raise ConfigError(
                f"policy_overrides.{name} must be an object with value and reason"
            )
        unknown = sorted(set(decision) - {"value", "reason"})
        if unknown:
            raise ConfigError(
                f"unknown policy_overrides.{name} field(s): {', '.join(unknown)}"
            )
        _structured_override(name, decision.get("value"), reason=decision.get("reason", ""))
    if config.policy_overrides:
        from .policy import _base_policy_values, policy_override_strength

        derived = _base_policy_values(config)
        for name, decision in config.policy_overrides.items():
            value = str(decision["value"])
            if (
                policy_override_strength(name, derived[name], value) == "weaker"
                and not str(decision.get("reason", "")).strip()
            ):
                raise ConfigError(
                    f"policy_overrides.{name}.reason is required when weakening "
                    f"{derived[name]!r} to {value!r}"
                )
    for name in (
        "with_security_hooks",
        "with_context_settings",
        "manage_artifact_gitignore",
        "sandbox_local",
    ):
        if not isinstance(getattr(config, name), bool):
            raise ConfigError(f"{name} must be a boolean")
    if config.protocol_guard is not None:
        raise ConfigError(
            "protocol_guard must be represented by a structured policy override"
        )


__all__ = [
    "CONFIG_VERSION",
    "ConfigError",
    "DEFAULT_COMMANDS",
    "DEFAULT_PROFILES",
    "DEFAULT_SUMMARY",
    "LEGACY_CONFIG_VERSION",
    "POLICY_DIMENSION_VALUES",
    "RIGOR_ALIASES",
    "VALID_COMPLEXITIES",
    "VALID_RIGOR_PRESETS",
    "VALID_SESSION_PROFILES",
    "VALID_SIZES",
    "VALID_TESTING_LEVELS",
    "VALID_WORKFLOWS",
    "WorkflowConfig",
    "canonical_codebase_project_id",
    "canonical_memory_wing",
    "validate_config",
]
