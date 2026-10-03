#!/usr/bin/env python3
"""Install the GPT agent workflow template without overwriting project files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from workflow_configurator import core as configurator_core
except ModuleNotFoundError:  # Running this file directly from the template folder.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from workflow_configurator import core as configurator_core

# Public names are re-exported here for callers that historically imported the
# installer as a module rather than invoking the script.
WorkflowConfig = configurator_core.WorkflowConfig
AnalysisReport = configurator_core.AnalysisReport
analyze_project = configurator_core.analyze_project
apply_project = configurator_core.apply_project
rollback_project = configurator_core.rollback_project
restore_instructions = configurator_core.restore_instructions
install_legacy = configurator_core.install_legacy

CORE_FILES = configurator_core.CORE_FILES
PROFILE_FILES = configurator_core.PROFILE_FILES
MCP_NAMES = configurator_core.MCP_NAMES
OPTIONAL_INTEGRATION_NAMES = configurator_core.OPTIONAL_INTEGRATION_NAMES
LOCAL_CAPABILITY_FILES = configurator_core.LOCAL_CAPABILITY_FILES
SECURITY_HOOK_FILES = configurator_core.SECURITY_HOOK_FILES
PROTOCOL_GUARD_FILES = configurator_core.PROTOCOL_GUARD_FILES
CONTEXT_SETTINGS_FILES = configurator_core.CONTEXT_SETTINGS_FILES
DEFAULT_PROFILES = configurator_core.DEFAULT_PROFILES
DEFAULT_SUMMARY = configurator_core.DEFAULT_SUMMARY
DEFAULT_TEST_COMMAND = configurator_core.LEGACY_DEFAULT_COMMANDS["test"]
DEFAULT_LINT_COMMAND = configurator_core.LEGACY_DEFAULT_COMMANDS["lint"]
DEFAULT_TYPECHECK_COMMAND = configurator_core.LEGACY_DEFAULT_COMMANDS["typecheck"]
DEFAULT_RUN_COMMAND = configurator_core.LEGACY_DEFAULT_COMMANDS["run"]
GITIGNORE_ARTIFACT_BLOCK = configurator_core.GITIGNORE_ARTIFACT_BLOCK
LOCAL_MCP_NAMES = configurator_core.LOCAL_MCP_NAMES
MCP_SERVERS = {
    name: configurator_core.build_mcp_config([name])["servers"][name]
    for name in MCP_NAMES
}
POSTGRES_INPUT = configurator_core.build_mcp_config(["postgres"])["inputs"][0]


def command_value(value: str) -> str:
    return configurator_core.command_for_template(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, nargs="?", help="project directory to configure")
    parser.add_argument("--project-name", help="defaults to the target directory name")
    parser.add_argument("--memory-wing", help="canonical MemPalace project wing")
    parser.add_argument(
        "--codebase-project-id",
        help="persistent codebase-memory project identifier",
    )
    parser.add_argument(
        "--session-profile",
        choices=configurator_core.VALID_SESSION_PROFILES,
        help="task-scoped tool enable/disable guidance",
    )
    parser.add_argument(
        "--technology-stack",
        help="free-text technologies alongside any selected stack profiles (for example, Rust + React)",
    )
    parser.add_argument(
        "--execution-mode",
        choices=configurator_core.VALID_EXECUTION_MODES,
        help="balanced process or implementation-first velocity with manual checks and review",
    )
    parser.add_argument(
        "--task-details",
        help="optional initial task written to docs/CURRENT_TASK.md only on explicit Apply",
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--test-command")
    parser.add_argument("--lint-command")
    parser.add_argument("--typecheck-command")
    parser.add_argument("--run-command")
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(PROFILE_FILES),
        default=[],
        help="add an optional stack profile; repeat as needed",
    )
    parser.add_argument(
        "--no-default-profiles",
        action="store_true",
        help="omit the default Python and data-science profiles",
    )
    parser.add_argument(
        "--mcp",
        action="append",
        choices=MCP_NAMES,
        default=[],
        help="add an opt-in project-local VS Code MCP server; repeat as needed",
    )
    parser.add_argument(
        "--without-mcp-sandbox",
        action="store_true",
        help="disable VS Code sandboxing for selected local MCP servers; retain tool confirmations",
    )
    parser.add_argument(
        "--integration",
        action="append",
        choices=OPTIONAL_INTEGRATION_NAMES,
        default=[],
        help=(
            "add reviewed setup guidance for an optional tool/skill/MCP; "
            "nothing is installed automatically"
        ),
    )
    parser.add_argument(
        "--with-security-hooks",
        action="store_true",
        help="install reviewed opt-in PreToolUse security hooks",
    )
    parser.add_argument(
        "--with-context-settings",
        action="store_true",
        default=True,
        help="install .vscode/settings.json with artifact/search exclusions (default)",
    )
    parser.add_argument(
        "--without-context-settings",
        action="store_false",
        dest="with_context_settings",
        help="do not install .vscode/settings.json",
    )
    parser.add_argument(
        "--without-artifact-gitignore",
        action="store_false",
        dest="manage_artifact_gitignore",
        default=True,
        help="do not create or append the artifacts/ rule in .gitignore",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the installation plan only")
    parser.add_argument(
        "--workflow",
        choices=("new", "existing"),
        help="configurator mode: create a new project or safely adopt an existing one",
    )
    parser.add_argument(
        "--complexity",
        "--project-complexity",
        choices=configurator_core.VALID_COMPLEXITIES,
        help="workflow complexity policy",
    )
    parser.add_argument(
        "--project-size",
        "--size",
        "--scope",
        dest="project_size",
        choices=configurator_core.VALID_SIZES,
        help="project size/scope policy",
    )
    parser.add_argument(
        "--testing-level",
        "--testing",
        dest="testing_level",
        choices=configurator_core.VALID_TESTING_LEVELS,
        help="none, focused, or broad validation",
    )
    parser.add_argument(
        "--rigor",
        "--rigor-preset",
        "--engineering-rigor",
        dest="rigor_preset",
        choices=tuple(configurator_core.VALID_RIGOR_PRESETS)
        + ("low", "medium", "high", "governed", "strict"),
        help="named engineering-rigor preset",
    )
    parser.add_argument(
        "--stack-profile",
        dest="profile",
        action="append",
        choices=sorted(PROFILE_FILES),
        help="alias for --profile in configurator mode",
    )
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        metavar="NAME=COMMAND",
        help="override a command (test, lint, typecheck, or run); repeat as needed",
    )
    parser.add_argument(
        "--policy-override",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="deprecated v1 policy override; use --override and --override-reason",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help="set one typed process-policy override; repeat as needed",
    )
    parser.add_argument(
        "--override-reason",
        action="append",
        default=[],
        metavar="DIMENSION=TEXT",
        help="record the reason for an override; required when weakening policy",
    )
    parser.add_argument(
        "--protocol-guard",
        action="store_true",
        help="enable the reviewed local handoff/plan protocol guard",
    )
    parser.add_argument(
        "--without-protocol-guard",
        action="store_true",
        help="do not install the optional local protocol guard",
    )
    parser.add_argument(
        "--analyze",
        "--inspect",
        action="store_true",
        help="read-only existing-project analysis",
    )
    parser.add_argument("--preview", action="store_true", help="render a read-only apply preview")
    parser.add_argument(
        "--apply",
        "--safe-apply",
        action="store_true",
        help="apply missing files and safe merges",
    )
    parser.add_argument(
        "--rollback",
        nargs="?",
        const="",
        metavar="MANIFEST_OR_ID",
        help="deprecated; automatic rollback is removed",
    )
    parser.add_argument(
        "--restore-instructions",
        "--show-restore-instructions",
        nargs="?",
        const="",
        metavar="MANIFEST_OR_ID",
        help="show manual restoration guidance from an apply manifest",
    )
    parser.add_argument(
        "--import-config",
        "--import",
        "--config",
        dest="import_config",
        type=Path,
        help="load a versioned JSON configuration",
    )
    parser.add_argument(
        "--export-config",
        "--export",
        type=Path,
        metavar="PATH",
        help="export configuration JSON without modifying TARGET",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="explicit output path for a preview/analysis report",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable report/result JSON")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="launch the optional PySide6 configurator",
    )
    parser.add_argument(
        "--headless-smoke",
        action="store_true",
        help="exercise the GUI controller without opening a display",
    )
    return parser.parse_args()


def selected_files(
    profiles: list[str],
    *,
    with_security_hooks: bool = False,
    with_context_settings: bool = False,
) -> list[str]:
    """Compatibility view of the core selection contract."""

    overrides = (
        {
            "protocol_guard": {
                "value": "off",
                "reason": "Legacy selection helper preserves its prior no-guard behavior",
            }
        }
        if with_security_hooks
        else {}
    )
    config = configurator_core.WorkflowConfig(
        stack_profiles=tuple(dict.fromkeys(profiles)),
        execution_mode="balanced",
        with_security_hooks=with_security_hooks,
        with_context_settings=with_context_settings,
        policy_overrides=overrides,
    )
    return configurator_core.selected_files(config)


def replacements(args: argparse.Namespace) -> dict[str, str]:
    config = configurator_core.WorkflowConfig(
        project_name=args.project_name,
        summary=args.summary,
        commands={
            "test": args.test_command,
            "lint": args.lint_command,
            "typecheck": args.typecheck_command,
            "run": args.run_command,
        },
    )
    return {
        "{{PROJECT_NAME}}": config.project_name,
        "{{PROJECT_SUMMARY}}": config.summary,
        "{{TEST_COMMAND}}": command_value(config.commands["test"]),
        "{{LINT_COMMAND}}": command_value(config.commands["lint"]),
        "{{TYPECHECK_COMMAND}}": command_value(config.commands["typecheck"]),
        "{{RUN_COMMAND}}": command_value(config.commands["run"]),
    }



def render(source: Path, values: dict[str, str]) -> str:
    try:
        return configurator_core.render_values(source, values)
    except configurator_core.ApplyError as error:
        raise ValueError(str(error)) from error


build_mcp_config = configurator_core.build_mcp_config
gitignore_has_artifacts = configurator_core.gitignore_has_artifacts


def _legacy_main(args: argparse.Namespace) -> int:
    if args.target is None:
        print("installation aborted; a target directory is required", file=sys.stderr)
        return 2
    defaults = {
        "summary": args.summary or DEFAULT_SUMMARY,
        "test": args.test_command or DEFAULT_TEST_COMMAND,
        "lint": args.lint_command or DEFAULT_LINT_COMMAND,
        "typecheck": args.typecheck_command or DEFAULT_TYPECHECK_COMMAND,
        "run": args.run_command or DEFAULT_RUN_COMMAND,
    }
    target = args.target.expanduser()
    source_root = Path(__file__).resolve().parent
    try:
        target = configurator_core.validate_target(target, allow_missing=True)
        if target.resolve(strict=False) == source_root or source_root in target.resolve(strict=False).parents:
            raise configurator_core.SafetyError(
                "target cannot be the template directory or one of its children"
            )
        project_name = (args.project_name or target.name).strip()
        if not project_name:
            raise configurator_core.ConfigError("project name is empty")
        profiles = [] if args.no_default_profiles else list(DEFAULT_PROFILES)
        profiles.extend(args.profile or [])
        config = configurator_core.WorkflowConfig(
            project_name=project_name,
            summary=defaults["summary"],
            workflow="new",
            execution_mode="balanced",
            stack_profiles=tuple(dict.fromkeys(profiles)),
            mcp_servers=tuple(dict.fromkeys(args.mcp or [])),
            optional_integrations=tuple(dict.fromkeys(args.integration or [])),
            commands={
                "test": defaults["test"],
                "lint": defaults["lint"],
                "typecheck": defaults["typecheck"],
                "run": defaults["run"],
            },
            with_security_hooks=args.with_security_hooks,
            with_context_settings=args.with_context_settings,
            manage_artifact_gitignore=args.manage_artifact_gitignore,
            sandbox_local=not args.without_mcp_sandbox,
            policy_overrides=(
                {
                    "protocol_guard": {
                        "value": "off",
                        "reason": "Legacy installer preserves its prior no-guard behavior",
                    }
                }
                if args.with_security_hooks
                else {}
            ),
        )
        result = configurator_core.install_legacy(
            target,
            config,
            source_root=source_root,
            dry_run=args.dry_run,
        )
    except configurator_core.ApplyError as error:
        text = str(error)
        if "destination files already exist" in text:
            print("installation aborted; destination files already exist:", file=sys.stderr)
            for path in text.split(":", 1)[-1].split(";"):
                print(f"  {path.strip()}", file=sys.stderr)
            return 3
        if "unsafe destinations" in text or "unsafe" in text:
            print("installation aborted; unsafe destination paths:", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 2
    except (configurator_core.ConfigError, configurator_core.SafetyError) as error:
        print(f"installation aborted; {error}", file=sys.stderr)
        return 2

    for warning in configurator_core.runtime_warnings(config):
        print(f"warning: {warning}", file=sys.stderr)
    print(f"target: {target.resolve(strict=False)}")
    print("files:")
    for action in result.report.actions:
        if action.status in {"missing", "safe_merge"}:
            print(f"  {action.path}")
    if args.dry_run:
        print("dry run complete; no files written")
    else:
        print("installation complete")
    return 0


def _parse_key_values(values: list[str], field_name: str) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for item in values:
        if "=" not in item:
            raise configurator_core.ConfigError(
                f"{field_name} must use NAME=VALUE syntax: {item!r}"
            )
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            raise configurator_core.ConfigError(f"{field_name} name cannot be empty")
        if value.lower() in {"true", "false"}:
            parsed[name] = value.lower() == "true"
        else:
            parsed[name] = value
    return parsed


def _parse_text_key_values(values: list[str], field_name: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise configurator_core.ConfigError(
                f"{field_name} must use NAME=VALUE syntax: {item!r}"
            )
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise configurator_core.ConfigError(
                f"{field_name} requires a non-empty name and value"
            )
        if name in parsed and parsed[name] != value:
            raise configurator_core.ConfigError(
                f"{field_name} has conflicting values for {name!r}"
            )
        parsed[name] = value
    return parsed


def _typed_policy_overrides(
    *,
    values: list[str],
    reasons: list[str],
    legacy: list[str],
) -> dict[str, dict[str, str]]:
    reason_map = _parse_text_key_values(reasons, "--override-reason")
    selected = _parse_text_key_values(values, "--override")
    unknown_reasons = sorted(set(reason_map) - set(selected))
    if unknown_reasons:
        raise configurator_core.ConfigError(
            "--override-reason has no matching --override for: "
            + ", ".join(unknown_reasons)
        )
    result = {
        dimension: {
            "value": value,
            "reason": reason_map.get(dimension, ""),
        }
        for dimension, value in selected.items()
    }
    if legacy:
        legacy_values = _parse_key_values(legacy, "--policy-override")
        migrated = configurator_core.WorkflowConfig.from_dict(
            {
                "version": 1,
                "policy_overrides": legacy_values,
            }
        ).policy_overrides
        for dimension, decision in migrated.items():
            result.setdefault(dimension, dict(decision))
    return result


def _config_from_args(args: argparse.Namespace) -> configurator_core.WorkflowConfig:
    if args.protocol_guard and args.without_protocol_guard:
        raise configurator_core.ConfigError(
            "choose --protocol-guard or --without-protocol-guard, not both"
        )
    if args.policy_override:
        print(
            "warning: --policy-override is deprecated; use --override and "
            "--override-reason",
            file=sys.stderr,
        )
    target = args.target or Path(".")
    if args.import_config is not None:
        config = configurator_core.load_config(args.import_config)
        values: dict[str, object] = {}
        if args.project_name is not None:
            values["project_name"] = args.project_name
        if args.summary != DEFAULT_SUMMARY:
            values["summary"] = args.summary
        if args.memory_wing is not None:
            values["memory_wing"] = args.memory_wing
        if args.codebase_project_id is not None:
            values["codebase_project_id"] = args.codebase_project_id
        if args.session_profile is not None:
            values["session_profile"] = args.session_profile
        if args.technology_stack is not None:
            values["technology_stack"] = args.technology_stack
        if args.execution_mode is not None:
            values["execution_mode"] = args.execution_mode
        if args.task_details is not None:
            values["task_details"] = args.task_details
        if args.workflow is not None:
            values["workflow"] = args.workflow
        if args.complexity is not None:
            values["complexity"] = args.complexity
        if args.project_size is not None:
            values["project_size"] = args.project_size
        if args.testing_level is not None:
            values["testing_level"] = args.testing_level
        if args.rigor_preset is not None:
            values["rigor_preset"] = args.rigor_preset
        if args.command:
            commands = dict(config.commands)
            commands.update(_parse_key_values(args.command, "--command"))
            values["commands"] = commands
        for name, value in (
            ("test", args.test_command),
            ("lint", args.lint_command),
            ("typecheck", args.typecheck_command),
            ("run", args.run_command),
        ):
            if value is not None:
                commands = dict(values.get("commands", config.commands))
                commands[name] = value
                values["commands"] = commands
        if (
            args.policy_override
            or args.override
            or args.override_reason
            or args.protocol_guard
            or args.without_protocol_guard
        ):
            policy = dict(config.policy_overrides)
            override_values = list(args.override)
            if args.protocol_guard:
                override_values.append("protocol_guard=on")
            if args.without_protocol_guard:
                override_values.append("protocol_guard=off")
            policy.update(
                _typed_policy_overrides(
                    values=override_values,
                    reasons=args.override_reason,
                    legacy=args.policy_override,
                )
            )
            values["policy_overrides"] = policy
        if args.profile:
            values["stack_profiles"] = list(dict.fromkeys(args.profile))
        elif args.no_default_profiles:
            values["stack_profiles"] = []
        if args.mcp:
            values["mcp_servers"] = list(dict.fromkeys(args.mcp))
        if args.integration:
            values["optional_integrations"] = list(
                dict.fromkeys(args.integration)
            )
        if args.with_security_hooks:
            values["with_security_hooks"] = True
        if not args.with_context_settings:
            values["with_context_settings"] = False
        if not args.manage_artifact_gitignore:
            values["manage_artifact_gitignore"] = False
        if args.without_mcp_sandbox:
            values["sandbox_local"] = False
        if values:
            raw = config.to_dict()
            raw.update(values)
            config = configurator_core.WorkflowConfig.from_dict(raw)
        return config

    workflow = args.workflow or ("existing" if Path(target).exists() else "new")
    if args.no_default_profiles:
        profiles: list[str] = []
    elif workflow == "existing" and not args.profile:
        profiles = []
    elif workflow == "existing":
        profiles = list(args.profile or [])
    else:
        profiles = list(DEFAULT_PROFILES)
        profiles.extend(args.profile or [])
    commands = {
        "test": args.test_command or configurator_core.DEFAULT_COMMANDS["test"],
        "lint": args.lint_command or configurator_core.DEFAULT_COMMANDS["lint"],
        "typecheck": args.typecheck_command or configurator_core.DEFAULT_COMMANDS["typecheck"],
        "run": args.run_command or configurator_core.DEFAULT_COMMANDS["run"],
    }
    commands.update(_parse_key_values(args.command, "--command"))
    override_values = list(args.override)
    if args.protocol_guard:
        override_values.append("protocol_guard=on")
    if args.without_protocol_guard:
        override_values.append("protocol_guard=off")
    overrides = _typed_policy_overrides(
        values=override_values,
        reasons=args.override_reason,
        legacy=args.policy_override,
    )
    return configurator_core.WorkflowConfig(
        project_name=(args.project_name or Path(target).name or "project").strip(),
        summary=args.summary if args.summary is not None else DEFAULT_SUMMARY,
        workflow=workflow,
        complexity=args.complexity or "standard",
        project_size=args.project_size or "small",
        testing_level=args.testing_level or "focused",
        stack_profiles=tuple(dict.fromkeys(profiles)),
        technology_stack=args.technology_stack or "",
        mcp_servers=tuple(dict.fromkeys(args.mcp or [])),
        optional_integrations=tuple(dict.fromkeys(args.integration or [])),
        commands=commands,
        rigor_preset=configurator_core.RIGOR_ALIASES.get(
            (args.rigor_preset or "standard").lower(), args.rigor_preset or "standard"
        ),
        execution_mode=args.execution_mode or "velocity",
        task_details=args.task_details or "",
        policy_overrides=overrides,
        memory_wing=(
            args.memory_wing
            or configurator_core.canonical_memory_wing(
                args.project_name or Path(target).name or "project"
            )
        ),
        codebase_project_id=(
            args.codebase_project_id
            or configurator_core.canonical_codebase_project_id(
                args.project_name or Path(target).name or "project"
            )
        ),
        session_profile=args.session_profile or "auto",
        with_security_hooks=args.with_security_hooks,
        with_context_settings=args.with_context_settings,
        manage_artifact_gitignore=args.manage_artifact_gitignore,
        sandbox_local=not args.without_mcp_sandbox,
        protocol_guard=None,
    )


def _print_report(report: configurator_core.AnalysisReport, *, as_json: bool) -> None:
    if as_json:
        print(report.to_json(), end="")
        return
    print(f"target: {report.target}")
    print("detected:")
    for key in ("manifests", "languages", "environment_managers"):
        print(f"  {key}: {json.dumps(report.facts.get(key, {}), sort_keys=True)}")
    footprint = report.facts.get("context_footprint")
    if isinstance(footprint, dict):
        print(configurator_core.render_context_footprint(footprint), end="")
    print("actions:")
    for action in report.actions:
        print(f"  {action.status}: {action.path} — {action.reason}")
    if report.proposals:
        print(f"proposals: {len(report.proposals)} (conflicting files were not changed)")
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)


def _configurator_main(args: argparse.Namespace) -> int:
    operations = [
        name
        for name, enabled in (
            ("analyze", args.analyze),
            ("preview", args.preview),
            ("apply", args.apply),
            ("rollback", args.rollback is not None),
            ("restore-instructions", args.restore_instructions is not None),
        )
        if enabled
    ]
    if len(operations) > 1:
        print(
            "configurator error: choose exactly one operation "
            f"(received {', '.join(operations)})",
            file=sys.stderr,
        )
        return 2
    if args.gui or args.headless_smoke:
        if args.gui and args.dry_run:
            print("configurator error: --dry-run cannot launch a mutating GUI", file=sys.stderr)
            return 2
        if operations or args.export_config is not None or args.output is not None:
            print(
                "configurator error: GUI/headless-smoke cannot be combined with "
                "CLI operation or output flags",
                file=sys.stderr,
            )
            return 2
        try:
            from workflow_configurator import gui
        except ModuleNotFoundError:
            from . import gui  # pragma: no cover - package execution fallback
        return gui.main(
            [
                *(["--target", str(args.target)] if args.target else []),
                *(["--config", str(args.import_config)] if args.import_config else []),
                *(["--headless-smoke"] if args.headless_smoke else []),
            ]
        )
    try:
        if args.rollback is not None:
            raise configurator_core.RollbackError(
                "automatic rollback was removed; no project paths were changed. "
                "Use --restore-instructions to review the passive apply manifest "
                "and restore safe merges manually."
            )
        if args.restore_instructions is not None:
            plan = configurator_core.restore_instructions(
                args.restore_instructions,
                args.target,
                output=args.output,
            )
            if args.json:
                print(json.dumps(plan, indent=2, sort_keys=True))
            else:
                print(configurator_core.render_restore_instructions(plan), end="")
                if args.output is not None:
                    print(f"restore plan written: {args.output}")
            return 0

        config = _config_from_args(args)
        if args.export_config is not None:
            if str(args.export_config) == "-":
                print(configurator_core.config_json(config), end="")
            elif args.dry_run:
                if args.json:
                    print(configurator_core.config_json(config), end="")
                else:
                    print(f"dry run; configuration not written: {args.export_config}")
            else:
                configurator_core.save_config(config, args.export_config)
                if not args.json:
                    print(f"configuration exported: {args.export_config}")
            if not (args.analyze or args.preview or args.apply or args.rollback is not None):
                return 0

        if args.target is None:
            if args.analyze or args.preview or args.apply:
                raise configurator_core.ConfigError("a target directory is required for analysis or apply")
            print(configurator_core.config_json(config), end="")
            return 0
        if args.apply:
            result = configurator_core.apply_project(
                args.target,
                config,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                _print_report(result.report, as_json=args.json)
                if not args.json:
                    print("dry run complete; no files written")
                return 1 if result.report.errors else 0
            if args.json:
                print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
            else:
                print(
                    f"apply complete: {len(result.added_paths)} added, "
                    f"{len(result.merged_paths)} safely merged"
                )
                print(f"manifest: {result.manifest_path}")
                if result.proposals:
                    print(f"proposals left for review: {len(result.proposals)}")
            return 0
        report = configurator_core.preview_project(
            args.target,
            config,
            output=(
                args.output
                if (args.preview or args.analyze) and not args.dry_run
                else None
            ),
        )
        _print_report(report, as_json=args.json)
        if args.output is not None and not args.dry_run and not args.json:
            print(f"report written: {args.output}")
        return 1 if report.errors else 0
    except (configurator_core.ConfigError, configurator_core.SafetyError, configurator_core.ApplyError, configurator_core.RollbackError) as error:
        print(f"configurator error: {error}", file=sys.stderr)
        return 2


def _uses_configurator_mode(args: argparse.Namespace) -> bool:
    return any(
        (
            args.workflow is not None,
            args.complexity is not None,
            args.project_size is not None,
            args.testing_level is not None,
            args.rigor_preset is not None,
            args.memory_wing is not None,
            args.codebase_project_id is not None,
            args.session_profile is not None,
            args.technology_stack is not None,
            args.execution_mode is not None,
            args.task_details is not None,
            bool(args.command),
            bool(args.policy_override),
            bool(args.override),
            bool(args.override_reason),
            args.protocol_guard,
            args.without_protocol_guard,
            args.analyze,
            args.preview,
            args.apply,
            args.rollback is not None,
            args.restore_instructions is not None,
            args.import_config is not None,
            args.export_config is not None,
            args.output is not None,
            args.gui,
            args.headless_smoke,
        )
    )


def main() -> int:
    args = parse_args()
    if _uses_configurator_mode(args):
        return _configurator_main(args)
    return _legacy_main(args)


if __name__ == "__main__":
    raise SystemExit(main())