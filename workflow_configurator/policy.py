"""Deterministic adaptive workflow policy and typed expert overrides."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Any

from .config_model import (
    ConfigError,
    POLICY_DIMENSION_VALUES,
    VALID_RIGOR_PRESETS,
)


@dataclass(frozen=True)
class EngineeringPolicy:
    preset: str
    installation_surface: str
    plan_tier: str
    validation_tier: str
    documentation_tier: str
    memory_policy: str
    code_intelligence_policy: str
    review_tier: str
    protocol_guard: str
    planning_gate: str
    validation_mode: str
    documentation_handoff: str
    memory_lifecycle: str
    code_intelligence: str
    change_isolation: str
    safety_approvals: str
    review_requirements: str
    test_path: str
    require_protocol_guard: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    planning = property(lambda self: self.planning_gate)
    validation = property(lambda self: self.validation_mode)
    documentation = property(lambda self: self.documentation_handoff)
    memory = property(lambda self: self.memory_lifecycle)
    safety = property(lambda self: self.safety_approvals)
    review = property(lambda self: self.review_requirements)


POLICY_OVERRIDE_FIELDS = frozenset(POLICY_DIMENSION_VALUES)
_POLICY_RANKS = {
    dimension: {value: index for index, value in enumerate(values)}
    for dimension, values in POLICY_DIMENSION_VALUES.items()
}
_POLICY_DESCRIPTIONS = {
    "installation_surface": {
        "minimal": (
            "install only compact always-on instructions and the generated workflow "
            "configuration; stronger plan, documentation, memory, code-intelligence, "
            "review, or guard choices can still promote the effective file set"
        ),
        "standard": (
            "add planner/executor/reviewer roles, compact handoff and resume skills, "
            "the project doctor, and context exclusions when enabled"
        ),
        "governed": (
            "add the Standard surface plus governed planning, memory, code-intelligence, "
            "environment, observability, MCP, and safety guidance"
        ),
    },
    "plan_tier": {
        "none": "no plan artifact for questions, research, docs, or trivial configuration",
        "mini": "inline or mini plan, at most 25 lines, for bounded low-risk edits",
        "compact": (
            "compact approved plan, at most 80 lines, for coupled or multi-session "
            "changes; ensures at least the Standard surface and a docs/plans directory"
        ),
        "governed": (
            "governed specification and risk record before implementation; promotes "
            "the Governed surface, while Spec Kit can own the plan artifacts"
        ),
    },
    "validation_tier": {
        "none": "no code tests for research/docs; use only the smallest applicable diagnostic",
        "focused": "run the smallest affected check after a coherent implementation slice",
        "broad": "run focused checks plus broad relevant tests or diagnostics at a logical checkpoint",
    },
    "documentation_tier": {
        "changed-only": "update only user-facing or operational documentation changed by the task",
        "handoff": (
            "keep a concise current-state handoff for work that spans sessions; "
            "ensures at least the Standard surface"
        ),
        "full": (
            "maintain governed handoff, recovery, and operator evidence without copied "
            "command output; promotes the Governed surface"
        ),
    },
    "memory_policy": {
        "off": "do not call project memory when history is explicitly irrelevant",
        "on-demand": "use the canonical project wing only when prior decisions or session history matter",
        "required": (
            "use project-scoped retrieval and an explicit-wing checkpoint for "
            "substantial work; promotes the Governed surface"
        ),
    },
    "code_intelligence_policy": {
        "off": "use live files and language/text search for the bounded task",
        "on-demand": "use available graph tools when architecture, callers, impact, or reuse discovery matters",
        "required": (
            "verify the available graph surface and use it for architecture and impact "
            "before editing; promotes the Governed surface"
        ),
    },
    "review_tier": {
        "self": "self-review the final diff and relevant evidence; do not manufacture findings",
        "independent": (
            "independent read-only review is required before completion or release; "
            "promotes the Governed surface"
        ),
    },
    "protocol_guard": {
        "off": (
            "do not install the optional workflow guard; hard path, secret, preview, "
            "collision, and transactional safeguards remain active"
        ),
        "on": (
            "install the reviewed local guard that checks handoff, plan, and "
            "change-isolation facts; promotes the Governed surface but cannot prove "
            "external memory, review, or test success"
        ),
    },
}
_POLICY_DIMENSION_GUIDANCE = {
    "installation_surface": (
        "Controls the generated workflow-file bundle. This is a floor, not an "
        "absolute cap: stronger choices in other dimensions can promote it."
    ),
    "plan_tier": (
        "Controls whether work needs no plan, a small inline plan, a compact persisted "
        "plan, or a governed specification."
    ),
    "validation_tier": (
        "Controls the expected verification scope. It does not install a test runner "
        "or weaken hard safety checks."
    ),
    "documentation_tier": (
        "Controls ongoing documentation and handoff obligations, not whether directly "
        "affected user-facing documentation may be skipped."
    ),
    "memory_policy": (
        "Controls MemPalace invocation. The project wing remains configured even when "
        "memory use is off."
    ),
    "code_intelligence_policy": (
        "Controls codebase-memory usage. The project identity remains configured and "
        "live files remain authoritative."
    ),
    "review_tier": (
        "Controls who must review completed work. It does not authorize overwriting "
        "conflicting project files."
    ),
    "protocol_guard": (
        "Controls the optional local workflow hook. It never replaces human review or "
        "the configurator's permanent safety boundaries."
    ),
}


def policy_override_strength(
    dimension: str, derived_value: str, override_value: str
) -> str:
    if dimension not in _POLICY_RANKS:
        raise ConfigError(f"unknown policy dimension {dimension!r}")
    ranks = _POLICY_RANKS[dimension]
    if derived_value not in ranks or override_value not in ranks:
        raise ConfigError(f"invalid value for policy dimension {dimension!r}")
    if ranks[override_value] < ranks[derived_value]:
        return "weaker"
    if ranks[override_value] > ranks[derived_value]:
        return "stronger"
    return "equal"


def policy_override_catalog() -> dict[str, dict[str, object]]:
    """Return the complete user-facing override reference in stable order."""

    return {
        dimension: {
            "label": dimension.replace("_", " ").title(),
            "summary": _POLICY_DIMENSION_GUIDANCE[dimension],
            "options": {
                value: _POLICY_DESCRIPTIONS[dimension][value]
                for value in values
            },
        }
        for dimension, values in POLICY_DIMENSION_VALUES.items()
    }


def render_policy_override_guide() -> str:
    """Render the authoritative override catalog as in-app Markdown."""

    lines = [
        "## Advanced override reference",
        "",
        "`auto` removes the explicit override and uses the value derived from "
        "complexity, project size, testing level, rigor, selected integrations, "
        "and security hooks.",
        "",
        "Options are ordered from lighter to stronger. A stronger choice increases "
        "process or generated workflow surface. A weaker choice requires a rationale "
        "and confirmation before Apply. Overrides never disable path, secret, sandbox, "
        "destructive-operation, preview, collision, overwrite, deletion, or "
        "transactional safeguards.",
        "",
    ]
    for dimension, metadata in policy_override_catalog().items():
        options = metadata["options"]
        if not isinstance(options, dict):
            raise ConfigError(f"override catalog options are invalid for {dimension}")
        lines.extend(
            [
                f"### {metadata['label']} (`{dimension}`)",
                "",
                str(metadata["summary"]),
                "",
                "| Option | Behavior |",
                "|---|---|",
                *[
                    f"| `{value}` | {description} |"
                    for value, description in options.items()
                ],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _base_policy_values(config: Any) -> dict[str, str]:
    risk = (
        {"minimal": 0, "standard": 1, "advanced": 2}[config.complexity]
        + {"small": 0, "medium": 1, "large": 2}[config.project_size]
        + {"none": 0, "focused": 1, "broad": 2}[config.testing_level]
    )
    if (
        config.rigor_preset == "strong"
        or risk >= 4
        or "spec-kit" in config.optional_integrations
        or getattr(config, "with_security_hooks", False)
    ):
        surface = "governed"
    elif (
        config.project_size == "small"
        and config.complexity != "advanced"
        and config.testing_level != "broad"
    ):
        surface = "minimal"
    else:
        surface = "standard"
    if surface == "governed":
        return {
            "installation_surface": surface,
            "plan_tier": "governed",
            "validation_tier": "broad",
            "documentation_tier": "full",
            "memory_policy": "required",
            "code_intelligence_policy": "required",
            "review_tier": "independent",
            "protocol_guard": "on",
        }
    if surface == "minimal":
        return {
            "installation_surface": surface,
            "plan_tier": "mini",
            "validation_tier": "none" if config.testing_level == "none" else "focused",
            "documentation_tier": "changed-only",
            "memory_policy": "on-demand",
            "code_intelligence_policy": "on-demand",
            "review_tier": "self",
            "protocol_guard": "off",
        }
    return {
        "installation_surface": surface,
        "plan_tier": "compact",
        "validation_tier": (
            "none"
            if config.testing_level == "none"
            else "broad"
            if config.testing_level == "broad"
            else "focused"
        ),
        "documentation_tier": "handoff",
        "memory_policy": "on-demand",
        "code_intelligence_policy": "on-demand",
        "review_tier": "self",
        "protocol_guard": "off",
    }


def policy_override_details(config: Any) -> list[dict[str, str]]:
    derived = _base_policy_values(config)
    details = []
    for dimension in sorted(config.policy_overrides):
        decision = config.policy_overrides[dimension]
        value = str(decision["value"])
        details.append(
            {
                "dimension": dimension,
                "derived": derived[dimension],
                "value": value,
                "reason": str(decision.get("reason", "")).strip(),
                "strength": policy_override_strength(
                    dimension, derived[dimension], value
                ),
            }
        )
    return details


def derive_policy(config: Any) -> EngineeringPolicy:
    derived = _base_policy_values(config)
    values = dict(derived)
    decisions = {
        dimension: dict(decision)
        for dimension, decision in config.policy_overrides.items()
    }
    for dimension, decision in decisions.items():
        override = str(decision["value"])
        strength = policy_override_strength(dimension, derived[dimension], override)
        reason = str(decision.get("reason", "")).strip()
        if strength == "weaker" and not reason:
            raise ConfigError(
                f"policy_overrides.{dimension}.reason is required when weakening "
                f"{derived[dimension]!r} to {override!r}"
            )
        values[dimension] = override
    surface = values["installation_surface"]
    return EngineeringPolicy(
        preset=config.rigor_preset,
        **values,
        planning_gate=_POLICY_DESCRIPTIONS["plan_tier"][values["plan_tier"]],
        validation_mode=_POLICY_DESCRIPTIONS["validation_tier"][
            values["validation_tier"]
        ],
        documentation_handoff=_POLICY_DESCRIPTIONS["documentation_tier"][
            values["documentation_tier"]
        ],
        memory_lifecycle=_POLICY_DESCRIPTIONS["memory_policy"][
            values["memory_policy"]
        ],
        code_intelligence=_POLICY_DESCRIPTIONS["code_intelligence_policy"][
            values["code_intelligence_policy"]
        ],
        change_isolation={
            "minimal": "single-purpose diff with explicit non-goals",
            "standard": "keep changed files and dependencies within the approved scope",
            "governed": "strict approved-scope review with transactional failure recovery",
        }[surface],
        safety_approvals=(
            "hard path, secret, sandbox, destructive-operation, preview, collision, "
            "and transactional safeguards remain active"
        ),
        review_requirements=_POLICY_DESCRIPTIONS["review_tier"][
            values["review_tier"]
        ],
        test_path=values["validation_tier"],
        require_protocol_guard=values["protocol_guard"] == "on",
    )


def rigor_presets() -> dict[str, dict[str, str]]:
    settings = {
        "light": ("minimal", "small", "none"),
        "standard": ("standard", "small", "focused"),
        "strong": ("advanced", "large", "broad"),
    }
    return {
        name: _base_policy_values(
            SimpleNamespace(
                rigor_preset=name,
                complexity=complexity,
                project_size=size,
                testing_level=testing,
                optional_integrations=(),
                with_security_hooks=False,
            )
        )
        for name, (complexity, size, testing) in settings.items()
        if name in VALID_RIGOR_PRESETS
    }


__all__ = [
    "EngineeringPolicy",
    "POLICY_OVERRIDE_FIELDS",
    "derive_policy",
    "policy_override_catalog",
    "policy_override_details",
    "policy_override_strength",
    "render_policy_override_guide",
    "rigor_presets",
]
