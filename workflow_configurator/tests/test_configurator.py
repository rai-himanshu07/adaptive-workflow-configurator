from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from workflow_configurator import core
from workflow_configurator.gui import (
    ConfiguratorController,
    USER_GUIDE,
    WorkflowConfiguratorApp,
    apply_blockers,
    diff_line_kind,
    format_context_footprint,
    format_continuity_health,
    format_report,
    format_project_overview,
    format_restore_instructions,
    guard_intent_for_config,
    headless_smoke,
    preview_signature,
    protocol_guard_for_intent,
)


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.py"


def snapshot(root: Path, *, include_metadata: bool = False) -> dict[Path, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
        and (include_metadata or ".workflow_configurator" not in path.parts)
    }


class ConfigModelTests(unittest.TestCase):
    def test_round_trip_and_policy_dimensions(self) -> None:
        config = core.WorkflowConfig(
            project_name="Example",
            summary="A small service.",
            workflow="existing",
            complexity="advanced",
            project_size="large",
            testing_level="broad",
            stack_profiles=("python", "fastapi"),
            execution_mode="balanced",
            mcp_servers=("context7",),
            optional_integrations=("serena", "affected-tests"),
            commands={
                "test": "python -m unittest",
                "lint": "none",
                "typecheck": "pyright",
                "run": "python -m app",
            },
            rigor_preset="strong",
            policy_overrides={
                "review_tier": {
                    "value": "independent",
                    "reason": "Public API boundary",
                }
            },
            memory_wing="example",
            codebase_project_id="Example",
            session_profile="large-code",
        )
        restored = core.WorkflowConfig.from_dict(json.loads(core.config_json(config)))
        self.assertEqual(config.to_dict(), restored.to_dict())
        policy = core.derive_policy(restored)
        self.assertEqual("strong", policy.preset)
        self.assertEqual("governed", policy.installation_surface)
        self.assertEqual("broad", policy.validation_tier)
        self.assertTrue(policy.require_protocol_guard)
        self.assertIn("serena", restored.optional_integrations)
        self.assertIn(
            "speculative abstractions",
            " ".join(core.LEAN_CHANGE_CONTRACT).lower(),
        )

    def test_invalid_configuration_is_actionable(self) -> None:
        with self.assertRaisesRegex(core.ConfigError, "unsupported configuration version"):
            core.WorkflowConfig.from_dict({"version": 99})
        with self.assertRaisesRegex(core.ConfigError, "unknown configuration field"):
            core.WorkflowConfig.from_dict({"version": 1, "future": True})
        with self.assertRaisesRegex(core.ConfigError, "unsupported mcp_servers"):
            core.WorkflowConfig.from_dict({"version": 1, "mcp_servers": ["unknown"]})
        config = core.WorkflowConfig.from_dict(
            {
                "version": 1,
                "commands": {
                    "test": "pytest",
                    "lint": "ruff",
                    "typecheck": "pyright",
                    "run": "none",
                    "build": "make",
                },
            }
        )
        self.assertEqual("make", config.commands["build"])
        with self.assertRaisesRegex(core.ConfigError, "choose one specification workflow"):
            core.WorkflowConfig(
                optional_integrations=("openspec", "spec-kit"),
            )
        with self.assertRaisesRegex(core.ConfigError, "reason is required"):
            core.derive_policy(
                core.WorkflowConfig(
                    rigor_preset="strong",
                    execution_mode="balanced",
                    complexity="advanced",
                    project_size="large",
                    policy_overrides={
                        "validation_tier": {"value": "focused", "reason": ""}
                    },
                )
            )
        with self.assertRaisesRegex(core.ConfigError, "no longer overridable"):
            core.WorkflowConfig.from_dict(
                {
                    "version": 1,
                    "policy_overrides": {"require_approval": False},
                }
            )

    def test_override_catalog_covers_every_dimension_and_guide(self) -> None:
        catalog = core.policy_override_catalog()
        self.assertEqual(
            list(core.POLICY_DIMENSION_VALUES),
            list(catalog),
        )
        rendered = core.render_policy_override_guide()
        documentation = (
            ROOT / "docs" / "CONFIGURATOR.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("`auto` removes the explicit override", rendered)
        self.assertIn("permanent safety boundaries", USER_GUIDE)
        self.assertIn("Execution mode: velocity", USER_GUIDE)
        self.assertIn("is the default for new", USER_GUIDE)
        self.assertIn("docs/CURRENT_TASK.md", USER_GUIDE)
        self.assertIn("Previously installed hooks also stay in place", USER_GUIDE)
        self.assertIn("not installed product", USER_GUIDE)
        for dimension, values in core.POLICY_DIMENSION_VALUES.items():
            metadata = catalog[dimension]
            self.assertTrue(str(metadata["summary"]).strip())
            options = metadata["options"]
            self.assertEqual(list(values), list(options))
            self.assertIn(f"`{dimension}`", rendered)
            for value in values:
                description = str(options[value])
                self.assertGreater(len(description), 20)
                self.assertIn(f"| `{value}` | {description} |", rendered)
                self.assertIn(description[:45].lower(), documentation)
        self.assertIn(
            core.render_policy_override_guide().strip(),
            USER_GUIDE,
        )

    def test_v1_migration_is_conservative_and_exports_v2(self) -> None:
        migrated = core.WorkflowConfig.from_dict(
            {
                "version": 1,
                "project_name": "Legacy App",
                "policy_overrides": {
                    "require_review": True,
                    "require_memory": False,
                    "install_guard": True,
                },
            }
        )
        self.assertEqual(core.CONFIG_VERSION, migrated.version)
        self.assertEqual("legacy_app", migrated.memory_wing)
        self.assertEqual("Legacy_App", migrated.codebase_project_id)
        self.assertEqual("independent", migrated.policy_overrides["review_tier"]["value"])
        self.assertEqual("off", migrated.policy_overrides["memory_policy"]["value"])
        self.assertEqual("on", migrated.policy_overrides["protocol_guard"]["value"])
        defaults = core.WorkflowConfig.from_dict({"version": 1})
        self.assertEqual(
            ("python", "data-science"),
            defaults.stack_profiles,
        )
        self.assertEqual("pytest -x -q", defaults.commands["test"])
        self.assertEqual(
            {"test": "none", "lint": "none", "typecheck": "none", "run": "none"},
            core.WorkflowConfig.from_dict({"version": 2}).commands,
        )
        self.assertEqual("none", core.WorkflowConfig().commands["test"])
        self.assertIn("experiment-runner", defaults.optional_integrations)
        self.assertIn("Python and data-science", defaults.summary)
        legacy_guard = core.WorkflowConfig.from_dict(
            {"version": 1, "protocol_guard": False}
        )
        self.assertEqual(
            "off",
            legacy_guard.policy_overrides["protocol_guard"]["value"],
        )
        with self.assertRaisesRegex(core.ConfigError, "manual review"):
            core.WorkflowConfig.from_dict(
                {
                    "version": 1,
                    "policy_overrides": {"require_plan": True},
                }
            )
        with self.assertRaisesRegex(core.ConfigError, "reserved"):
            core.WorkflowConfig(memory_wing="wing_copilot")

    def test_new_cli_commands_are_neutral_and_legacy_defaults_remain_python(self) -> None:
        command = subprocess.run(
            [sys.executable, str(INSTALLER), "--workflow", "new", "--export-config", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, command.returncode, command.stderr)
        self.assertEqual("none", json.loads(command.stdout)["commands"]["test"])
        self.assertEqual("velocity", json.loads(command.stdout)["execution_mode"])
        balanced = subprocess.run(
            [
                sys.executable, str(INSTALLER), "--workflow", "new",
                "--execution-mode", "balanced", "--export-config", "-",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, balanced.returncode, balanced.stderr)
        self.assertEqual("balanced", json.loads(balanced.stdout)["execution_mode"])
        from workflow_configurator import install

        self.assertEqual("pytest -x -q", install.DEFAULT_TEST_COMMAND)

    def test_cli_exports_mixed_stack_velocity_and_initial_task(self) -> None:
        command = subprocess.run(
            [
                sys.executable, str(INSTALLER), "--workflow", "existing",
                "--profile", "python", "--profile", "react",
                "--technology-stack", "Rust, React, Python",
                "--execution-mode", "velocity",
                "--task-details", "Implement the API first.",
                "--command", "test=cargo test && npm test && python -m unittest",
                "--export-config", "-",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, command.returncode, command.stderr)
        config = core.WorkflowConfig.from_dict(json.loads(command.stdout))
        self.assertEqual(("python", "react"), config.stack_profiles)
        self.assertEqual("Rust, React, Python", config.technology_stack)
        self.assertEqual("velocity", config.execution_mode)
        self.assertEqual("Implement the API first.", config.task_details)
        self.assertEqual("cargo test && npm test && python -m unittest", config.commands["test"])

    def test_mixed_stack_velocity_and_task_round_trip(self) -> None:
        config = core.WorkflowConfig(
            stack_profiles=("python", "react"),
            technology_stack="Rust, React, Python",
            execution_mode="velocity",
            task_details="Implement the API\nKeep the UI usable.",
        )
        self.assertEqual(config.to_dict(), core.WorkflowConfig.from_dict(config.to_dict()).to_dict())
        fresh = core.config_for_target("example-project", workflow="new")
        self.assertEqual("velocity", fresh.execution_mode)
        self.assertEqual("manual", core.derive_policy(fresh).validation_tier)
        self.assertEqual(
            ["AGENTS.md", ".github/copilot-instructions.md"],
            core.selected_files(fresh),
        )
        self.assertEqual("balanced", core.WorkflowConfig.from_dict({"version": 2}).execution_mode)
        with self.assertRaisesRegex(core.ConfigError, "execution_mode"):
            core.WorkflowConfig(execution_mode="unsafe")
        with self.assertRaisesRegex(core.ConfigError, "single line"):
            core.WorkflowConfig(technology_stack="Rust\nReact")
        literal = core.WorkflowConfig(technology_stack="Rust {{FEATURE}}")
        self.assertIn("Rust {{FEATURE}}", core.render_template(ROOT / "AGENTS.md", literal))
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "unknown.md"
            source.write_text("{{UNKNOWN_TOKEN}}", encoding="utf-8")
            with self.assertRaisesRegex(core.ApplyError, "unresolved template tokens"):
                core.render_template(source, literal)

    def test_velocity_mode_keeps_memory_and_graph_without_automatic_process(self) -> None:
        config = core.WorkflowConfig(
            execution_mode="velocity",
            complexity="advanced",
            project_size="large",
            testing_level="broad",
            rigor_preset="strong",
        )
        policy = core.derive_policy(config)
        self.assertEqual("manual", policy.validation_tier)
        self.assertEqual("manual", policy.review_tier)
        self.assertEqual("none", policy.plan_tier)
        self.assertEqual("required", policy.memory_policy)
        self.assertEqual("required", policy.code_intelligence_policy)
        self.assertFalse(policy.require_protocol_guard)
        self.assertIn("hard path, secret", policy.safety_approvals)
        files = core.selected_files(config)
        self.assertEqual(["AGENTS.md", ".github/copilot-instructions.md"], files)
        steps = " ".join(core.guidance(config)["steps"])
        self.assertIn("bounded code-graph", steps)
        self.assertIn(
            "run self-review or an independent reviewer only when the user requests it",
            steps,
        )
        self.assertNotIn("broad diagnostics", steps)
        agents = core.render_template(ROOT / "AGENTS.md", config)
        copilot = core.render_template(ROOT / ".github/copilot-instructions.md", config)
        executor = core.render_template(ROOT / ".github/agents/executor.agent.md", config)
        self.assertIn("one code-graph lookup", agents)
        self.assertIn("only when the user requests them", agents)
        self.assertNotIn("Run the smallest affected check", agents)
        self.assertIn("one bounded project-memory lookup", copilot)
        self.assertIn("only when a policy detail is needed", copilot)
        self.assertNotIn("Read `AGENTS.md` and `docs/WORKFLOW_CONFIG.md`", copilot)
        self.assertNotIn("Test changed behavior", copilot)
        self.assertIn("only on user request", executor)
        plan = core.render_template(ROOT / "docs/PLAN.template.md", config)
        memory = core.render_template(ROOT / "docs/MEMORY_PROTOCOL.md", config)
        code = core.render_template(ROOT / "docs/CODE_INTELLIGENCE.md", config)
        resume = core.render_template(ROOT / ".github/skills/resume-session/SKILL.md", config)
        self.assertIn("record unrun checks in Velocity mode", plan)
        self.assertIn("only when they are installed", memory)
        self.assertIn("one\n   bounded graph lookup", code)
        self.assertIn("only when the resolved validation", resume)

    def test_velocity_explicit_overrides_update_generated_instructions(self) -> None:
        config = core.WorkflowConfig(
            execution_mode="velocity",
            policy_overrides={
                "validation_tier": {"value": "focused", "reason": ""},
                "review_tier": {"value": "independent", "reason": ""},
                "memory_policy": {"value": "on-demand", "reason": "Only when relevant"},
                "code_intelligence_policy": {"value": "on-demand", "reason": "Only when relevant"},
                "protocol_guard": {"value": "on", "reason": ""},
            },
        )
        self.assertIn(".github/agents/reviewer.agent.md", core.selected_files(config))
        self.assertIn(".github/hooks/workflow_guard.json", core.selected_files(config))
        agents = core.render_template(ROOT / "AGENTS.md", config)
        copilot = core.render_template(ROOT / ".github/copilot-instructions.md", config)
        executor = core.render_template(ROOT / ".github/agents/executor.agent.md", config)
        self.assertIn("Run the smallest affected check", agents)
        self.assertIn("independent read-only review is required", agents)
        self.assertIn("selected hooks run automatically", agents)
        self.assertNotIn("project-memory lookup", agents)
        self.assertIn("Skip it for known-file/literal lookups", copilot)
        self.assertIn("smallest affected check", executor)
        self.assertNotIn("project memory and a bounded code-graph", " ".join(core.guidance(config)["steps"]))

    def test_manual_validation_override_is_not_undone_by_balanced_routing(self) -> None:
        config = core.WorkflowConfig(
            testing_level="none",
            execution_mode="balanced",
            policy_overrides={
                "validation_tier": {"value": "manual", "reason": "User runs checks"}
            },
        )
        agents = core.render_template(ROOT / "AGENTS.md", config)
        self.assertIn("checks run only on user request", agents)
        self.assertNotIn("smallest affected check", agents)
        self.assertNotIn("smallest format/diagnostic check", " ".join(core.guidance(config)["steps"]))

    def test_optional_integration_guidance_is_explicit_and_non_installing(self) -> None:
        config = core.WorkflowConfig(
            workflow="existing",
            complexity="advanced",
            project_size="large",
            testing_level="broad",
            rigor_preset="strong",
            optional_integrations=("rtk", "serena", "jscpd", "affected-tests"),
        )
        rendered = core.render_guidance(config, {"manifests": ["pyproject.toml"]})
        self.assertIn("## Optional integrations", rendered)
        self.assertIn("Serena symbolic editing", rendered)
        self.assertIn("nothing is installed automatically", rendered.lower())
        recommended = core.recommended_integrations(config, {"manifests": ["pyproject.toml"]})
        self.assertIn("spec-kit", recommended)
        self.assertIn("otel-metadata", recommended)

    def test_adaptive_surfaces_and_optional_experiment_runner(self) -> None:
        cases = (
            (
                core.WorkflowConfig(
                    complexity="minimal",
                    project_size="small",
                    testing_level="none",
                    execution_mode="balanced",
                    stack_profiles=(),
                    with_context_settings=True,
                ),
                "minimal",
            ),
            (
                core.WorkflowConfig(
                    complexity="standard",
                    project_size="medium",
                    execution_mode="balanced",
                    stack_profiles=(),
                ),
                "standard",
            ),
            (
                core.WorkflowConfig(
                    rigor_preset="strong",
                    project_size="large",
                    execution_mode="balanced",
                    stack_profiles=(),
                ),
                "governed",
            ),
        )
        for config, surface in cases:
            with self.subTest(surface=surface):
                self.assertEqual(surface, core.derive_policy(config).installation_surface)
                files = core.selected_files(config)
                if surface == "minimal":
                    self.assertEqual(
                        ["AGENTS.md", ".github/copilot-instructions.md"],
                        files,
                    )
                    self.assertEqual((), core.required_project_directories(config))
                elif surface == "standard":
                    self.assertIn(".github/agents/executor.agent.md", files)
                    self.assertNotIn("docs/MEMORY_PROTOCOL.md", files)
                else:
                    self.assertIn("docs/MEMORY_PROTOCOL.md", files)
                    self.assertEqual(
                        ("docs/plans",),
                        core.required_project_directories(config),
                    )

        data_only = core.WorkflowConfig(
            stack_profiles=("data-science",),
            optional_integrations=(),
        )
        self.assertNotIn(
            ".github/skills/experiment-runner/scripts/experiment_tools.py",
            core.selected_files(data_only),
        )
        with_runner = core.WorkflowConfig(
            stack_profiles=("data-science",),
            optional_integrations=("experiment-runner",),
        )
        self.assertIn(
            ".github/skills/experiment-runner/scripts/experiment_tools.py",
            core.selected_files(with_runner),
        )
        governed_spec = core.WorkflowConfig(
            rigor_preset="strong",
            project_size="large",
            execution_mode="balanced",
            stack_profiles=(),
            optional_integrations=("spec-kit",),
        )
        files = core.selected_files(governed_spec)
        self.assertNotIn(".github/skills/plan-task/SKILL.md", files)
        self.assertNotIn("docs/PLAN.template.md", files)
        self.assertNotIn(".github/agents/planner.agent.md", files)
        self.assertEqual((), core.required_project_directories(governed_spec))
        guidance = core.render_guidance(governed_spec)
        self.assertIn("## Installed file contract", guidance)
        self.assertIn("Spec Kit owns specification", guidance)
        weakened_surface = core.WorkflowConfig(
            rigor_preset="strong",
            project_size="large",
            execution_mode="balanced",
            stack_profiles=(),
            policy_overrides={
                "installation_surface": {
                    "value": "minimal",
                    "reason": "Keep generated base small",
                }
            },
        )
        self.assertIn("docs/HANDOFF.md", core.selected_files(weakened_surface))

    def test_named_presets_and_override_directions_are_effective(self) -> None:
        expected_surfaces = {
            "light": "minimal",
            "standard": "minimal",
            "strong": "governed",
        }
        for preset, expected_surface in expected_surfaces.items():
            config = core.WorkflowConfig(
                rigor_preset=preset,
                execution_mode="balanced",
                complexity="minimal",
                project_size="small",
                testing_level="none",
                stack_profiles=(),
            )
            policy = core.derive_policy(config)
            self.assertEqual(preset, policy.preset)
            self.assertEqual(expected_surface, policy.installation_surface)

        strengthened = core.derive_policy(
            core.WorkflowConfig(
                rigor_preset="light",
                execution_mode="balanced",
                complexity="minimal",
                project_size="small",
                testing_level="none",
                stack_profiles=(),
                policy_overrides={
                    "plan_tier": {"value": "compact", "reason": ""},
                    "review_tier": {"value": "independent", "reason": ""},
                    "memory_policy": {"value": "required", "reason": ""},
                    "code_intelligence_policy": {
                        "value": "required",
                        "reason": "",
                    },
                    "protocol_guard": {"value": "on", "reason": ""},
                },
            )
        )
        self.assertEqual("compact", strengthened.plan_tier)
        self.assertEqual("independent", strengthened.review_tier)
        self.assertEqual("required", strengthened.memory_policy)
        self.assertTrue(strengthened.require_protocol_guard)
        weakened = core.derive_policy(
            core.WorkflowConfig(
                rigor_preset="strong",
                execution_mode="balanced",
                complexity="advanced",
                project_size="large",
                testing_level="broad",
                stack_profiles=(),
                policy_overrides={
                    "plan_tier": {
                        "value": "mini",
                        "reason": "Bounded implementation",
                    },
                    "review_tier": {
                        "value": "self",
                        "reason": "Private prototype",
                    },
                },
            )
        )
        self.assertEqual("mini", weakened.plan_tier)
        self.assertEqual("self", weakened.review_tier)
        details = core.policy_override_details(
            core.WorkflowConfig(
                rigor_preset="strong",
                execution_mode="balanced",
                complexity="advanced",
                project_size="large",
                policy_overrides={
                    "plan_tier": {
                        "value": "mini",
                        "reason": "Bounded implementation",
                    }
                },
            )
        )
        self.assertEqual("weaker", details[0]["strength"])
        self.assertEqual(
            set(core.VALID_RIGOR_PRESETS),
            set(core.rigor_presets()),
        )

    def test_codebase_health_rejects_project_root_mismatch(self) -> None:
        config = core.WorkflowConfig(
            project_name="Expected",
            codebase_project_id="Expected",
        )
        response = {
            "status": "ok",
            "stdout": json.dumps(
                {
                    "project": "Expected",
                    "root_path": "/different/project",
                    "status": "ready",
                }
            ),
            "stderr": "",
        }
        with (
            mock.patch.object(core, "_find_local_command", return_value="/tool"),
            mock.patch.object(core, "_command_result", return_value=response),
        ):
            health = core.codebase_memory_health(config, "/expected/project")
        self.assertEqual("identity-mismatch", health["status"])
        self.assertEqual("/expected/project", health["expected_root"])

    def test_continuity_summary_respects_adaptive_policy(self) -> None:
        unavailable = {
            "mempalace": {"status": "unavailable"},
            "codebase_memory": {"status": "identity-mismatch"},
        }
        limited = core.continuity_summary(
            core.WorkflowConfig(stack_profiles=(), execution_mode="balanced"),
            unavailable,
        )
        self.assertEqual("limited", limited["status"])
        self.assertEqual(
            "on-demand",
            limited["services"]["mempalace"]["policy"],
        )

        required_config = core.WorkflowConfig(
            rigor_preset="strong",
            execution_mode="balanced",
            stack_profiles=(),
        )
        degraded = core.continuity_summary(required_config, unavailable)
        self.assertEqual("degraded", degraded["status"])
        self.assertIn("required", degraded["summary"].lower())

        ready = core.continuity_summary(
            required_config,
            {
                "mempalace": {
                    "status": "healthy",
                    "wing_present": True,
                    "writer": {"status": "writable"},
                },
                "codebase_memory": {"status": "current"},
            },
        )
        self.assertEqual("ready", ready["status"])

        disabled_config = core.WorkflowConfig(
            stack_profiles=(),
            policy_overrides={
                "memory_policy": {
                    "value": "off",
                    "reason": "History is irrelevant to this bounded task",
                },
                "code_intelligence_policy": {
                    "value": "off",
                    "reason": "Only supplied known files are in scope",
                },
            },
        )
        disabled = core.continuity_summary(disabled_config, unavailable)
        self.assertEqual("disabled", disabled["status"])
        rendered = format_continuity_health(
            {**unavailable, "continuity": degraded}
        )
        self.assertIn("Continuity: DEGRADED", rendered)
        self.assertIn("policy=required", rendered)
        self.assertIn("Technical details", rendered)

    def test_dry_run_and_export_never_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--workflow",
                    "new",
                    "--apply",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(target.exists())
            config_path = root / "config.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--workflow",
                    "new",
                    "--export-config",
                    str(config_path),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(config_path.exists())

    def test_export_round_trip_does_not_require_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            config_path = root / "nested" / "workflow.json"
            config = core.config_for_target(target, workflow="new")
            core.save_config(config, config_path)
            self.assertFalse(target.exists())
            self.assertEqual(config.to_dict(), core.load_config(config_path).to_dict())

    def test_cli_exports_optional_integration_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "workflow.json"
            target = root / "project"
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--workflow",
                    "existing",
                    "--integration",
                    "serena",
                    "--integration",
                    "affected-tests",
                    "--memory-wing",
                    "project_memory",
                    "--codebase-project-id",
                    "ProjectGraph",
                    "--session-profile",
                    "large-code",
                    "--override",
                    "validation_tier=none",
                    "--override-reason",
                    "validation_tier=Documentation-only setup",
                    "--export-config",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(target.exists())
            loaded = core.load_config(output)
            self.assertEqual(
                ("serena", "affected-tests"),
                loaded.optional_integrations,
            )
            self.assertEqual("project_memory", loaded.memory_wing)
            self.assertEqual("ProjectGraph", loaded.codebase_project_id)
            self.assertEqual("large-code", loaded.session_profile)
            self.assertEqual(
                "Documentation-only setup",
                loaded.policy_overrides["validation_tier"]["reason"],
            )


class ProjectLifecycleTests(unittest.TestCase):
    def test_analysis_is_read_only_and_emits_conflict_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / "pyproject.toml").write_text("[project]\nname='demo'\n")
            (target / "AGENTS.md").write_text("user-owned\n")
            before = snapshot(target)
            config = core.WorkflowConfig(
                project_name="Demo",
                workflow="existing",
                project_size="medium",
                stack_profiles=("python", "data-science"),
                testing_level="none",
                rigor_preset="light",
            )
            report = core.analyze_project(target, config)
            self.assertEqual(before, snapshot(target))
            proposal = next(item for item in report.actions if item.path == "AGENTS.md")
            self.assertEqual("conflicting_proposal", proposal.status)
            self.assertIn("user-owned", proposal.reason)
            self.assertIn("Python", report.facts["languages"])
            self.assertIn("python", report.recommendations)

    def test_optional_current_task_is_previewed_and_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            config = core.WorkflowConfig(
                workflow="existing",
                execution_mode="velocity",
                task_details="Implement {{FEATURE}} safely.\nKeep the current API.",
            )
            task_path = target / "docs/CURRENT_TASK.md"
            preview = core.preview_project(target, config)
            self.assertFalse(task_path.exists())
            self.assertEqual(
                "missing",
                next(action.status for action in preview.actions if action.path == "docs/CURRENT_TASK.md"),
            )
            result = core.apply_project(target, config, expected_report=preview)
            self.assertIn("docs/CURRENT_TASK.md", result.added_paths)
            content = task_path.read_text(encoding="utf-8")
            self.assertIn("{{FEATURE}}", content)
            updated = core.WorkflowConfig.from_dict({
                **config.to_dict(), "task_details": "A different task"
            })
            later = core.preview_project(target, updated)
            self.assertEqual(
                "conflicting_proposal",
                next(action.status for action in later.actions if action.path == "docs/CURRENT_TASK.md"),
            )
            core.apply_project(target, updated, expected_report=later)
            self.assertEqual(content, task_path.read_text(encoding="utf-8"))

    def test_apply_rejects_project_actions_changed_after_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            agents = target / "AGENTS.md"
            agents.write_text("user-owned\n")
            config = core.WorkflowConfig(
                project_name="Demo",
                workflow="existing",
                stack_profiles=(),
                with_context_settings=False,
            )
            preview = core.analyze_project(target, config)
            self.assertEqual(
                "conflicting_proposal",
                next(item for item in preview.actions if item.path == "AGENTS.md").status,
            )
            agents.unlink()
            with self.assertRaisesRegex(core.ApplyError, "changed after Preview"):
                core.apply_project(target, config, expected_report=preview)
            self.assertFalse(agents.exists())

    def test_safe_apply_is_idempotent_and_writes_passive_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / ".gitignore").write_text("data/\n")
            (target / ".vscode").mkdir()
            settings = target / ".vscode/settings.json"
            settings.write_text('{"editor.tabSize": 2}\n')
            config = core.WorkflowConfig(
                project_name="Demo",
                workflow="existing",
                project_size="medium",
                execution_mode="balanced",
                stack_profiles=("python", "data-science"),
                testing_level="focused",
            )
            result = core.apply_project(target, config)
            self.assertTrue(result.manifest_path.is_file())
            self.assertIn(".gitignore", result.merged_paths)
            self.assertIn(".vscode/settings.json", result.merged_paths)
            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual("manual-only", manifest["recovery_policy"])
            self.assertEqual(str(target.resolve()), manifest["target"])
            self.assertEqual(config.to_dict(), manifest["config"])
            self.assertTrue(manifest["created_files"])
            self.assertEqual(2, len(manifest["safe_merges"]))
            for merge in manifest["safe_merges"]:
                backup = target / merge["backup"]
                self.assertTrue(backup.is_file())
                self.assertEqual(64, len(merge["before_sha256"]))
                self.assertEqual(64, len(merge["after_sha256"]))
                self.assertIn("before_mode", merge)
                self.assertIn("after_mode", merge)

            before = snapshot(target)
            second = core.apply_project(target, config)
            self.assertNotEqual(result.manifest_path, second.manifest_path)
            self.assertEqual(before, snapshot(target))
            self.assertEqual([], second.merged_paths)
            self.assertEqual([], second.added_paths)
            self.assertTrue(second.manifest_path.is_file())
            plan = core.restore_instructions(target=target)
            self.assertEqual(sorted(result.added_paths), plan["generated_paths"])
            self.assertEqual(2, len(plan["safe_merges"]))
            (target / result.added_paths[0]).unlink()
            (target / result.added_paths[1]).write_text("manual edit\n")
            changed_plan = core.restore_instructions(target=target)
            states = {
                item["path"]: item["state"]
                for item in changed_plan["created_files"]
            }
            self.assertEqual("missing", states[result.added_paths[0]])
            self.assertEqual("manual", states[result.added_paths[1]])

    def test_manual_restore_plan_lists_generated_paths_and_exact_backups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            target.mkdir()
            (target / ".gitignore").write_text("project/\n")
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                stack_profiles=("data-science",),
                with_context_settings=False,
            )
            result = core.apply_project(target, config)
            plan = core.restore_instructions(result.manifest_path, target)
            self.assertEqual("manual_restore", plan["status"])
            self.assertEqual(sorted(result.added_paths), plan["generated_paths"])
            self.assertEqual(1, len(plan["safe_merges"]))
            merge = plan["safe_merges"][0]
            self.assertEqual(".gitignore", merge["path"])
            self.assertTrue((target / merge["backup"]).is_file())
            self.assertTrue(
                any("manually copy" in instruction for instruction in plan["instructions"])
            )
            output = root / "restore-plan.json"
            exported = core.restore_instructions(
                result.manifest_path,
                target,
                output=output,
            )
            self.assertTrue(output.is_file())
            self.assertEqual(str(output), exported["output_path"])
            self.assertEqual(exported, json.loads(output.read_text()))
            before = snapshot(target)
            with self.assertRaisesRegex(core.RollbackError, "automatic rollback was removed"):
                core.rollback_project(result.manifest_path, target)
            self.assertEqual(before, snapshot(target))

    def test_analysis_reports_workflow_overhead_and_legacy_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "src").mkdir(parents=True)
            (target / "tests").mkdir()
            (target / "docs").mkdir()
            (target / ".github" / "agents").mkdir(parents=True)
            (target / "src" / "app.py").write_text("def run():\n    return 1\n")
            (target / "tests" / "test_app.py").write_text(
                "def test_run():\n    assert True\n"
            )
            (target / "docs" / "HANDOFF.md").write_text(
                "# Handoff\n\n**Active plan:** none\n"
            )
            (target / ".github" / "agents" / "planner.agent.md").write_text(
                "# Legacy planner\n"
            )
            outside = Path(temporary) / "outside.py"
            outside.write_text(
                "def leaked():\n" + "    value = 1\n" * 120 + "    return value\n"
            )
            (target / "src" / "outside.py").symlink_to(outside)
            report = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                    with_context_settings=False,
                ),
            )
            metrics = report.facts["workflow_metrics"]
            self.assertGreater(metrics["loc"]["production"], 0)
            self.assertGreater(metrics["loc"]["test"], 0)
            self.assertIn(
                ".github/agents/planner.agent.md",
                metrics["legacy_surface_candidates"],
            )
            self.assertTrue(metrics["handoff"]["within_budget"])
            self.assertFalse(
                any(
                    item["path"] == "src/outside.py"
                    for item in metrics["large_python_functions"]
                )
            )

    def test_context_footprint_uses_safe_post_apply_and_detects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / ".github").mkdir(parents=True)
            (target / "docs" / "research").mkdir(parents=True)
            repeated = (
                "Use the current repository as authoritative evidence.\n"
                "Verify historical context before relying on it in a decision.\n"
            )
            (target / "AGENTS.md").write_text(repeated, encoding="utf-8")
            (target / ".github" / "copilot-instructions.md").write_text(
                repeated,
                encoding="utf-8",
            )
            (target / "docs" / "research" / "old.md").write_text(
                "# Historical note\n\nThis is not current policy.\n",
                encoding="utf-8",
            )
            report = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                    mcp_servers=("context7",),
                    with_context_settings=False,
                ),
            )
            footprint = report.facts["context_footprint"]
            current = footprint["current"]
            post = footprint["safe_post_apply"]
            self.assertEqual(2, current["always_on"]["files"])
            self.assertEqual(
                current["always_on"]["bytes"],
                post["always_on"]["bytes"],
            )
            self.assertEqual(0, current["mcp_servers"])
            self.assertEqual(1, post["mcp_servers"])
            self.assertEqual(1, footprint["searchable_history"]["files"])
            self.assertEqual(
                ["docs/research/old.md"],
                footprint["searchable_history"]["paths"],
            )
            self.assertEqual(
                1,
                len(footprint["duplicate_blocks"]["current"]),
            )
            self.assertIn("not an exact token forecast", footprint["unit"])
            rendered = format_context_footprint(footprint)
            self.assertIn("Context footprint", rendered)
            self.assertIn("Configured MCP servers: 0 -> 1", rendered)
            self.assertIn("Duplicate instruction blocks: 1", rendered)
            command = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--workflow",
                    "existing",
                    "--no-default-profiles",
                    "--preview",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, command.returncode, command.stderr)
            self.assertIn(
                "Context footprint (deterministic proxy)",
                command.stdout,
            )

    def test_restore_plan_can_select_latest_manifest_without_mutating_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            config = core.WorkflowConfig(
                workflow="new",
                project_name="project",
                stack_profiles=(),
                with_context_settings=False,
            )
            first = core.apply_project(target, config)
            second = core.apply_project(target, config)
            self.assertNotEqual(first.manifest_path, second.manifest_path)
            before = snapshot(target)
            plan = core.restore_instructions(target=target)
            self.assertEqual([str(first.manifest_path)], plan["manifest_paths"])
            self.assertEqual(sorted(first.added_paths), plan["generated_paths"])
            self.assertEqual(before, snapshot(target))

    def test_cli_default_restore_plan_aggregates_material_after_noop_reapply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            target.mkdir()
            (target / ".gitignore").write_text("project/\n")
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                stack_profiles=("data-science",),
                with_context_settings=False,
            )
            first = core.apply_project(target, config)
            core.apply_project(target, config)
            command = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--restore-instructions",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, command.returncode, command.stderr)
            self.assertIn(first.added_paths[0], command.stdout)
            self.assertIn(".gitignore", command.stdout)
            self.assertIn(".workflow_configurator/backups/", command.stdout)

    def test_repeated_merge_prefers_current_mapping_and_keeps_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            target.mkdir()
            gitignore = target / ".gitignore"
            gitignore.write_text("project/\n")
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                stack_profiles=("data-science",),
                with_context_settings=False,
            )
            first = core.apply_project(target, config)
            first_manifest = json.loads(first.manifest_path.read_text())
            first_backup = target / first_manifest["safe_merges"][0]["backup"]
            gitignore.write_bytes(first_backup.read_bytes())
            with gitignore.open("a", encoding="utf-8") as handle:
                handle.write("user-added/\n")
            second = core.apply_project(target, config)
            second_manifest = json.loads(second.manifest_path.read_text())
            second_backup = target / second_manifest["safe_merges"][0]["backup"]

            plan = core.restore_instructions(target=target)
            self.assertEqual([str(first.manifest_path), str(second.manifest_path)], plan["manifest_paths"])
            active = plan["safe_merges"]
            self.assertEqual(1, len(active))
            self.assertEqual(str(second.manifest_path), active[0]["manifest_path"])
            self.assertEqual(str(second_backup.relative_to(target)), active[0]["backup"])
            self.assertEqual("ready", active[0]["state"])
            self.assertEqual(1, len(plan["history"]))
            self.assertEqual(str(first.manifest_path), plan["history"][0]["manifest_path"])
            self.assertEqual("safe_merge", plan["history"][0]["kind"])
            rendered = core.render_restore_instructions(plan)
            self.assertIn(str(second_backup.relative_to(target)), rendered)
            self.assertIn(str(first.manifest_path), rendered)
            self.assertIn("Older material history", rendered)
            command = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--restore-instructions",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, command.returncode, command.stderr)
            self.assertIn(str(second_backup.relative_to(target)), command.stdout)
            self.assertIn(str(first.manifest_path), command.stdout)
            controller = ConfiguratorController(target, config)
            controller_plan = controller.restore_instructions()
            visible = format_restore_instructions(controller_plan)
            self.assertIn(str(second_backup.relative_to(target)), visible)
            self.assertIn(str(first.manifest_path), visible)

            explicit = core.restore_instructions(second.manifest_path, target)
            self.assertEqual([str(second.manifest_path)], explicit["manifest_paths"])
            self.assertEqual(str(second_backup.relative_to(target)), explicit["safe_merges"][0]["backup"])
            self.assertEqual([], explicit["history"])

    def test_recreated_generated_file_prefers_new_configuration_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            first_config = core.WorkflowConfig(
                workflow="new",
                project_name="Alpha",
                stack_profiles=(),
                with_context_settings=False,
            )
            first = core.apply_project(target, first_config)
            generated = target / "AGENTS.md"
            generated.unlink()
            second_config = core.WorkflowConfig(
                workflow="new",
                project_name="Beta",
                stack_profiles=("python",),
                with_context_settings=False,
            )
            second = core.apply_project(target, second_config)
            plan = core.restore_instructions(target=target)
            active = next(item for item in plan["created_files"] if item["path"] == "AGENTS.md")
            second_manifest = json.loads(second.manifest_path.read_text())
            expected = next(
                item for item in second_manifest["created_files"] if item["path"] == "AGENTS.md"
            )
            self.assertEqual(str(second.manifest_path), active["manifest_path"])
            self.assertEqual(expected["sha256"], active["sha256"])
            self.assertEqual("present", active["state"])
            history = [
                item for item in plan["history"]
                if item["path"] == "AGENTS.md"
            ]
            self.assertEqual(1, len(history))
            self.assertEqual(str(first.manifest_path), history[0]["manifest_path"])
            self.assertEqual(sorted(plan["generated_paths"]), plan["generated_paths"])

    def test_required_directory_drift_is_recreated_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            config = core.WorkflowConfig(
                workflow="new",
                project_name="project",
                project_size="medium",
                execution_mode="balanced",
                stack_profiles=(),
                with_context_settings=False,
            )
            first = core.apply_project(target, config)
            self.assertTrue((target / "docs/plans").is_dir())
            (target / "docs/plans").rmdir()
            second = core.apply_project(target, config)
            self.assertTrue((target / "docs/plans").is_dir())
            self.assertEqual(["docs/plans"], second.recorded_directories)
            manifest = json.loads(second.manifest_path.read_text())
            self.assertEqual(
                ["docs/plans"],
                [item["path"] for item in manifest["required_directories"] if item["was_missing"]],
            )
            self.assertNotEqual(first.manifest_path, second.manifest_path)

    def test_transactional_apply_failure_restores_pre_apply_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / ".gitignore").write_text("project/\n")
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                stack_profiles=("data-science",),
                with_context_settings=False,
            )
            before = snapshot(target)
            missing_count = sum(
                item.status == "missing"
                for item in core.analyze_project(target, config).actions
            )
            with self.assertRaises(core.ApplyError):
                core.apply_project(target, config, fail_after=missing_count + 1)
            self.assertEqual(before, snapshot(target))
            self.assertFalse((target / ".workflow_configurator").exists())

    def test_failed_restoration_preserves_recovery_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            gitignore = target / ".gitignore"
            original = b"project/\n"
            gitignore.write_bytes(original)
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                stack_profiles=("data-science",),
                with_context_settings=False,
            )
            missing_count = sum(
                item.status == "missing"
                for item in core.analyze_project(target, config).actions
            )
            original_atomic = core._atomic_write

            def fail_restore(path: Path, content: bytes, mode: int = 0o644) -> None:
                if path == gitignore and content == original:
                    raise OSError("injected restoration failure")
                original_atomic(path, content, mode)

            with mock.patch.object(core, "_atomic_write", side_effect=fail_restore):
                with self.assertRaisesRegex(
                    core.ApplyError,
                    "recovery evidence preserved",
                ):
                    core.apply_project(
                        target,
                        config,
                        fail_after=missing_count + 1,
                    )
            self.assertIn("artifacts/", gitignore.read_text(encoding="utf-8"))
            self.assertTrue(
                any((target / ".workflow_configurator" / "backups").rglob(".gitignore"))
            )
            self.assertTrue(
                any((target / ".workflow_configurator" / "manifests").glob("*.json"))
            )

    def test_legacy_template_gpt_recovery_state_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / ".gitignore").write_text("project/\n", encoding="utf-8")
            result = core.apply_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=("data-science",),
                    with_context_settings=False,
                ),
            )
            self.assertIsNotNone(result.manifest_path)
            current = target / ".workflow_configurator"
            legacy = target / ".template_gpt"
            current.rename(legacy)
            for manifest_path in (legacy / "manifests").glob("*.json"):
                content = manifest_path.read_text(encoding="utf-8").replace(
                    ".workflow_configurator/",
                    ".template_gpt/",
                )
                manifest_path.write_text(content, encoding="utf-8")

            plan = core.restore_instructions(target=target)
            self.assertIn(".template_gpt/manifests/", plan["manifest_path"])
            self.assertTrue(plan["safe_merges"])
            self.assertIn(
                ".template_gpt/backups/",
                str(plan["safe_merges"][0]["backup"]),
            )

    def test_cleanup_failure_is_reported_without_false_rollback_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            generated = target / "AGENTS.md"
            config = core.WorkflowConfig(
                workflow="new",
                project_name="project",
                stack_profiles=(),
            )
            original_unlink = Path.unlink

            def fail_generated_unlink(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> None:
                if path == generated:
                    raise OSError("injected cleanup failure")
                original_unlink(path, *args, **kwargs)

            with mock.patch.object(Path, "unlink", new=fail_generated_unlink):
                with self.assertRaisesRegex(
                    core.ApplyError,
                    "cleanup was incomplete",
                ):
                    core.apply_project(target, config, fail_after=0)
            self.assertTrue(generated.is_file())

    def test_post_write_raise_cleans_backup_generated_and_manifest_destinations(self) -> None:
        cases = (
            ("backup", True),
            ("generated", False),
            ("manifest", False),
        )
        for category, existing in cases:
            with self.subTest(category=category), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "project"
                if existing:
                    target.mkdir()
                    (target / ".gitignore").write_text("project/\n")
                config = core.WorkflowConfig(
                    workflow="existing" if existing else "new",
                    project_name="project",
                    stack_profiles=("data-science",) if existing else (),
                    with_context_settings=False,
                )
                before = snapshot(target, include_metadata=True)
                original_write = core._write_new_bytes
                raised = [False]

                def write_then_raise(
                    path: Path,
                    content: bytes,
                    mode: int = 0o644,
                ) -> None:
                    original_write(path, content, mode)
                    relative = path.relative_to(target).as_posix()
                    matches = (
                        category == "backup"
                        and ".workflow_configurator/backups/" in relative
                    ) or (
                        category == "generated"
                        and relative == "AGENTS.md"
                    ) or (
                        category == "manifest"
                        and ".workflow_configurator/manifests/" in relative
                    )
                    if matches and not raised[0]:
                        raised[0] = True
                        raise OSError("injected post-write failure")

                core._write_new_bytes = write_then_raise
                try:
                    with self.assertRaises(core.ApplyError):
                        core.apply_project(target, config)
                finally:
                    core._write_new_bytes = original_write
                self.assertTrue(raised[0])
                self.assertEqual(before, snapshot(target, include_metadata=True))

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_symlink_destination_is_reported_and_apply_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / ".github").symlink_to(outside, target_is_directory=True)
            config = core.WorkflowConfig(
                project_name="Demo",
                workflow="existing",
                stack_profiles=("python",),
            )
            report = core.analyze_project(target, config)
            self.assertTrue(any(item.status == "unsafe" for item in report.actions))
            with self.assertRaises(core.ApplyError):
                core.apply_project(target, config)
            self.assertEqual([], list(outside.iterdir()))

    def test_incomplete_discovery_is_advisory_for_targeted_safe_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            blocked = target / "unreadable"
            blocked.mkdir(parents=True)
            (blocked / "package.json").write_text('{"scripts":{"test":"npm test"}}')
            blocked.chmod(0)
            try:
                config = core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                )
                report = core.analyze_project(target, config)
                self.assertFalse(report.facts["scan_complete"])
                self.assertTrue(report.diagnostics)
                self.assertFalse(report.facts["workflow_metrics"]["bounded"])
                self.assertEqual([], apply_blockers(report))
                result = core.apply_project(target, config)
                self.assertTrue(result.added_paths)
                self.assertFalse(result.report.facts["scan_complete"])
            finally:
                blocked.chmod(0o700)

    def test_project_local_conda_and_tool_caches_are_excluded_from_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / ".conda" / "lib").mkdir(parents=True)
            (target / ".conda" / "lib" / "dependency.py").write_text(
                "ignored = True\n",
                encoding="utf-8",
            )
            (target / ".pytest_cache").mkdir()
            (target / ".pytest_cache" / "state.py").write_text(
                "ignored = True\n",
                encoding="utf-8",
            )
            (target / "app.py").write_text("active = True\n", encoding="utf-8")
            report = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                ),
            )
            self.assertTrue(report.facts["scan_complete"])
            self.assertEqual({"Python": 1}, report.facts["languages"])
            self.assertEqual(1, report.facts["scan_entries"])
            self.assertEqual(25_000, report.facts["scan_entry_limit"])
            self.assertTrue(report.facts["workflow_metrics"]["bounded"])
            self.assertTrue(core.GENERATED_SEARCH_EXCLUDES["**/.conda/**"])

            medium = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    project_size="medium",
                    stack_profiles=(),
                ),
            )
            self.assertEqual(100_000, medium.facts["scan_entry_limit"])
            large = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    project_size="large",
                    stack_profiles=(),
                ),
            )
            self.assertEqual(250_000, large.facts["scan_entry_limit"])
            self.assertIn("1/25,000 entries", format_project_overview(report))

    def test_scan_limit_remains_bounded_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for name in ("a.py", "b.py", "c.py"):
                (target / name).write_text("value = 1\n", encoding="utf-8")
            paths, diagnostics, visited = core._walk_project(
                target,
                max_entries=2,
            )
            self.assertEqual(2, visited)
            self.assertEqual(2, len(paths))
            self.assertEqual("traversal.limit", diagnostics[0]["code"])
            self.assertIn("2-entry budget", diagnostics[0]["message"])
            self.assertIn("larger Project size", diagnostics[0]["message"])

    @unittest.skipUnless(shutil.which("git"), "Git is unavailable")
    def test_git_discovery_uses_tracked_and_non_ignored_relevant_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            subprocess.run(
                ["git", "init", "-q", str(target)],
                check=True,
            )
            (target / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (target / "tracked.py").write_text("tracked = True\n", encoding="utf-8")
            (target / "untracked.ts").write_text(
                "export const active = true;\n",
                encoding="utf-8",
            )
            (target / "binary.dat").write_bytes(b"\x00\x01")
            (target / "ignored").mkdir()
            (target / "ignored" / "dependency.py").write_text(
                "ignored = True\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(target), "add", ".gitignore", "tracked.py"],
                check=True,
            )

            report = core.analyze_project(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                ),
            )
            self.assertEqual("git", report.facts["scan_method"])
            self.assertEqual(
                {"Python": 1, "TypeScript": 1},
                report.facts["languages"],
            )
            self.assertEqual(4, report.facts["scan_entries"])
            self.assertTrue(report.facts["scan_complete"])

    def test_rollback_flag_is_a_non_mutating_migration_message(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            config = core.WorkflowConfig(
                workflow="new",
                project_name="project",
                stack_profiles=(),
                with_context_settings=False,
            )
            result = core.apply_project(target, config)
            before = snapshot(target)
            command = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--rollback",
                    str(result.manifest_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, command.returncode)
            self.assertIn("automatic rollback was removed", command.stderr)
            self.assertIn("--restore-instructions", command.stderr)
            self.assertEqual(before, snapshot(target))


class GuiControllerTests(unittest.TestCase):
    def test_diff_line_classifier_preserves_unified_diff_markers(self) -> None:
        self.assertEqual("file", diff_line_kind("--- a/example.py"))
        self.assertEqual("file", diff_line_kind("+++ b/example.py"))
        self.assertEqual("hunk", diff_line_kind("@@ -1,2 +1,2 @@"))
        self.assertEqual("deletion", diff_line_kind("-old value"))
        self.assertEqual("addition", diff_line_kind("+new value"))
        self.assertEqual("note", diff_line_kind("\\ No newline at end of file"))
        self.assertIsNone(diff_line_kind("---------------"))
        self.assertIsNone(diff_line_kind("normal context"))

    def test_launcher_scripts_are_executable_and_dependency_is_pinned(self) -> None:
        repository = ROOT.parent
        launcher = repository / "launch-workflow-configurator.sh"
        installer = repository / "install-workflow-configurator-launcher.sh"
        requirements = ROOT / "requirements-gui.txt"
        self.assertTrue(os.access(launcher, os.X_OK))
        self.assertTrue(os.access(installer, os.X_OK))
        self.assertIn("PySide6==6.11.1", requirements.read_text())
        launcher_text = launcher.read_text()
        installer_text = installer.read_text()
        self.assertIn("WORKFLOW_CONFIGURATOR_PYTHON", launcher_text)
        self.assertIn('"$VIRTUAL_ENV/bin/python"', launcher_text)
        self.assertIn('"$ROOT/.venv/bin/python"', launcher_text)
        self.assertIn('"$ROOT/.conda/bin/python"', launcher_text)
        self.assertIn('"$resolved_python" -c "import PySide6"', launcher_text)
        self.assertIn("--headless-smoke", launcher_text)
        self.assertNotIn("WORKFLOW_CONFIGURATOR_ENV:-py311", launcher_text)
        self.assertIn("python-interpreter", installer_text)

    def test_windows_launchers_are_user_scoped_and_never_elevate(self) -> None:
        repository = ROOT.parent
        launcher = (
            repository / "launch-workflow-configurator.ps1"
        ).read_text(encoding="utf-8")
        installer = (
            repository / "install-workflow-configurator-launcher.ps1"
        ).read_text(encoding="utf-8")
        launch_cmd = (
            repository / "launch-workflow-configurator.cmd"
        ).read_text(encoding="utf-8")
        install_cmd = (
            repository / "install-workflow-configurator-launcher.cmd"
        ).read_text(encoding="utf-8")

        self.assertIn("LocalApplicationData", launcher)
        self.assertIn(r".venv\Scripts\python.exe", launcher)
        self.assertIn(r".conda\python.exe", launcher)
        self.assertIn("import PySide6", launcher)
        self.assertIn("Start-Process", launcher)
        self.assertIn("RedirectStandardError", launcher)
        self.assertIn("ApplicationData", installer)
        self.assertIn(r"Microsoft\Windows\Start Menu\Programs", installer)
        self.assertIn("WScript.Shell", installer)
        self.assertIn("ReparsePoint", installer)
        self.assertIn("$Uninstall", installer)

        combined = "\n".join(
            (launcher, installer, launch_cmd, install_cmd)
        ).lower()
        for forbidden in (
            "-verb runas",
            "runas.exe",
            "hkey_local_machine",
            "hklm:",
            "programfiles",
            "commonstartmenu",
            "allusers",
            "executionpolicy bypass",
            "new-service",
            "register-scheduledtask",
        ):
            self.assertNotIn(forbidden, combined)

    def test_preview_signature_and_project_overview_are_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            config = core.WorkflowConfig(
                workflow="new",
                project_name="project",
                stack_profiles=(),
            )
            changed = core.WorkflowConfig.from_dict(
                dict(config.to_dict(), testing_level="broad")
            )
            self.assertNotEqual(
                preview_signature(target, config),
                preview_signature(target, changed),
            )
            report = core.analyze_project(target, config)
            overview = format_project_overview(report)
            self.assertIn("Target:", overview)
            self.assertIn("Discovery: complete", overview)
            self.assertIn("Recommendations", overview)

    def test_controller_and_headless_smoke_are_display_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            controller = ConfiguratorController(target)
            report = controller.analyze()
            self.assertIsInstance(report, core.AnalysisReport)
            self.assertEqual("loaded", headless_smoke(target)["controller"])
            self.assertEqual("standard", controller.policy().preset)
            exported = Path(temporary) / "config.json"
            controller.export_config(exported)
            controller.import_config(exported)
            self.assertEqual("project", controller.config.project_name)

    def test_report_formatter_exposes_proposals_and_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / "AGENTS.md").write_text("owned by project\n")
            report = ConfiguratorController(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=(),
                ),
            ).analyze()
            rendered = format_report(report)
            self.assertIn("[conflicting_proposal] AGENTS.md", rendered)
            self.assertIn("Intended content for AGENTS.md", rendered)
            self.assertIn("Diff:", rendered)

    def test_restore_formatter_lists_every_manual_follow_up(self) -> None:
        rendered = format_restore_instructions(
            {
                "status": "manual_restore",
                "manifest_path": "manifest.json",
                "target": "project",
                "generated_paths": ["AGENTS.md"],
                "safe_merges": [{"path": ".gitignore", "backup": "backups/.gitignore"}],
                "instructions": [
                    "Review/remove manually if desired: AGENTS.md.",
                    "Review backup backups/.gitignore and manually copy it to .gitignore.",
                ],
            }
        )
        for path in ("AGENTS.md", ".gitignore", "backups/.gitignore"):
            self.assertIn(path, rendered)
        self.assertIn("Manual restore instructions", rendered)
        self.assertIn("no project file or directory is restored", rendered)

    def test_controller_restore_instructions_is_read_only_and_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            (target / ".gitignore").write_text("project/\n")
            controller = ConfiguratorController(
                target,
                core.WorkflowConfig(
                    workflow="existing",
                    project_name="project",
                    stack_profiles=("data-science",),
                    with_context_settings=False,
                ),
            )
            applied = controller.apply()
            controller.apply()
            before = snapshot(target)
            plan = controller.restore_instructions()
            self.assertEqual("manual_restore", plan["status"])
            report = format_restore_instructions(plan)
            for path in applied.added_paths:
                self.assertIn(path, report)
            self.assertIn(".workflow_configurator/backups/", report)
            self.assertEqual(before, snapshot(target))
            self.assertEqual([str(applied.manifest_path)], plan["manifest_paths"])
            exported = controller.restore_instructions(
                applied.manifest_path,
                output=Path(temporary) / "restore-plan.json",
            )
            self.assertTrue(Path(exported["output_path"]).is_file())
            self.assertEqual(exported, controller.status()["last_restore_plan"])

    def test_gui_guard_identity_and_rows_remain_usable(self) -> None:
        base = core.WorkflowConfig(
            workflow="new",
            project_name="project",
            execution_mode="balanced",
            stack_profiles=(),
            rigor_preset="standard",
            protocol_guard=None,
        )
        self.assertEqual("auto", guard_intent_for_config(base))
        self.assertIsNone(protocol_guard_for_intent("auto"))
        strong = core.WorkflowConfig.from_dict(
            dict(base.to_dict(), rigor_preset="strong")
        )
        self.assertTrue(core.derive_policy(strong).require_protocol_guard)
        on_raw = strong.to_dict()
        on_raw["policy_overrides"] = {
            "protocol_guard": {"value": "on", "reason": ""}
        }
        on = core.WorkflowConfig.from_dict(
            on_raw
        )
        off_raw = strong.to_dict()
        off_raw["policy_overrides"] = {
            "protocol_guard": {
                "value": "off",
                "reason": "Host does not expose the Stop hook",
            }
        }
        off = core.WorkflowConfig.from_dict(
            off_raw
        )
        self.assertEqual("on", guard_intent_for_config(on))
        self.assertEqual("off", guard_intent_for_config(off))
        self.assertTrue(core.derive_policy(on).require_protocol_guard)
        self.assertFalse(core.derive_policy(off).require_protocol_guard)

    def test_target_change_updates_derived_identity_but_not_explicit_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first-project"
            second = root / "selected-new-project"
            third = root / "third-project"
            fourth = root / "fourth-project"
            controller = ConfiguratorController(first)
            self.assertEqual("first-project", controller.config.project_name)
            self.assertEqual("first_project", controller.config.memory_wing)
            controller.set_target(second)
            self.assertEqual("selected-new-project", controller.config.project_name)
            self.assertEqual("selected_new_project", controller.config.memory_wing)
            self.assertFalse(controller.identity_explicit)
            controller.set_identity("Imported Name", "Explicit summary")
            controller.set_target(third)
            self.assertEqual("Imported Name", controller.config.project_name)
            self.assertEqual("third_project", controller.config.memory_wing)
            self.assertEqual("third-project", controller.config.codebase_project_id)
            self.assertEqual("Explicit summary", controller.config.summary)
            controller.update_config(memory_wing="custom_wing")
            controller.set_target(fourth)
            self.assertEqual("Imported Name", controller.config.project_name)
            self.assertEqual("custom_wing", controller.config.memory_wing)
            self.assertEqual("fourth-project", controller.config.codebase_project_id)

    @unittest.skipUnless(
        os.environ.get("DISPLAY")
        or os.environ.get("QT_QPA_PLATFORM") == "offscreen",
        "a real or offscreen Qt display is unavailable",
    )
    def test_real_gui_is_readable_tabbed_and_preview_gates_apply(self) -> None:
        from PySide6.QtWidgets import QCheckBox, QRadioButton

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "new-project"
            cache = root / "cache" / "upstream.json"
            ledger = root / "state" / "reviews.json"
            update_service = core.UpstreamUpdateService(
                cache_path=cache,
                ledger_path=ledger,
            )
            app = WorkflowConfiguratorApp(
                ConfiguratorController(target),
                auto_check_updates=False,
                upstream_service=update_service,
            )
            app.show()
            app.application.processEvents()
            self.assertGreaterEqual(app.window.width(), 900)
            self.assertGreaterEqual(app.window.height(), 640)
            self.assertEqual(
                list(WorkflowConfiguratorApp.PAGE_NAMES),
                [
                    app.navigation.item(index).text()
                    for index in range(app.navigation.count())
                ],
            )
            self.assertEqual(set(core.MCP_NAMES), set(app.mcp_checks))
            self.assertEqual(
                set(core.OPTIONAL_INTEGRATION_NAMES),
                set(app.integration_checks),
            )
            self.assertIn("Guide", WorkflowConfiguratorApp.PAGE_NAMES)
            self.assertEqual("velocity", app.execution_mode_combo.currentText())
            self.assertIn("Updates & Plugins", WorkflowConfiguratorApp.PAGE_NAMES)
            self.assertEqual("new_project", app.memory_wing_edit.text())
            self.assertEqual("new-project", app.codebase_project_edit.text())
            self.assertGreater(app.integration_tree.topLevelItemCount(), 5)
            self.assertIn("Analyze", app.guide_view.toPlainText())
            self.assertTrue(hasattr(app, "_show_about"))
            self.assertFalse(app.export_plugin_button.isEnabled())
            self.assertFalse(app.export_review_button.isEnabled())
            self.assertFalse(app.inspect_review_button.isEnabled())
            self.assertFalse(app.advance_baseline_button.isEnabled())
            self.assertTrue(
                all(isinstance(check, QCheckBox) for check in app.mcp_checks.values())
            )
            self.assertIsInstance(app.new_radio, QRadioButton)
            self.assertIsInstance(app.existing_radio, QRadioButton)
            self.assertEqual("Close", app.close_button.text())
            self.assertFalse(app.apply_button.isEnabled())
            analyzed = core.analyze_project(target, app._form_config())
            app._run(lambda: analyzed, "Analyze")
            self.assertFalse(app.apply_button.isEnabled())
            app._preview()
            app.application.processEvents()
            self.assertFalse(target.exists())
            self.assertGreater(app.action_tree.topLevelItemCount(), 0)
            self.assertTrue(app.apply_button.isEnabled())
            app.execution_mode_combo.setCurrentText("velocity")
            app.technology_stack_edit.setText("Rust, React, Python")
            app.task_details_edit.setPlainText("Implement the API first.")
            app.application.processEvents()
            self.assertFalse(app.apply_button.isEnabled())
            self.assertEqual("velocity", app._form_config().execution_mode)
            self.assertEqual("Rust, React, Python", app._form_config().technology_stack)
            self.assertEqual("Implement the API first.", app._form_config().task_details)
            app._preview()
            app.application.processEvents()
            self.assertTrue(app.apply_button.isEnabled())
            self.assertIn(
                "docs/CURRENT_TASK.md",
                [action.path for action in app._preview_report.actions],
            )
            app.complexity_combo.setCurrentText("advanced")
            app.application.processEvents()
            self.assertFalse(app.apply_button.isEnabled())
            self.assertIn("preview again", app.preview_label.text().lower())
            app.controller.report = None
            exported_preview = core.analyze_project(target, app._form_config())
            app._run(lambda: exported_preview, "Report export")
            self.assertIs(exported_preview, app.controller.report)
            app.close_button.click()
            app.application.processEvents()
            self.assertFalse(app.window.isVisible())

            current = update_service.baseline_revision
            core.save_cached_report(
                core.UpstreamReport(
                    checked_at="2026-08-31T00:00:00+00:00",
                    reviewed_revision=current,
                    current_revision="b" * 40,
                    current_commit_time="2026-08-31T00:00:00Z",
                    status="review-required",
                    reviewed_counts={},
                    current_counts={},
                    added=(),
                    removed=(),
                    changed=(
                        {
                            "path": "agents/example.agent.md",
                            "category": "agents",
                            "reviewed_sha": "1" * 40,
                            "current_sha": "2" * 40,
                            "url": "https://example.invalid/review",
                        },
                    ),
                    monitored_changes=(),
                ),
                cache,
            )
            cached_app = WorkflowConfiguratorApp(
                ConfiguratorController(target),
                auto_check_updates=False,
                upstream_service=core.UpstreamUpdateService(
                    cache_path=cache,
                    ledger_path=ledger,
                ),
            )
            self.assertTrue(cached_app.export_review_button.isEnabled())
            self.assertEqual(1, cached_app.upstream_queue.topLevelItemCount())
            cached_app.upstream_queue.setCurrentItem(
                cached_app.upstream_queue.topLevelItem(0)
            )
            cached_app.application.processEvents()
            self.assertTrue(cached_app.inspect_review_button.isEnabled())
            self.assertFalse(cached_app.save_review_button.isEnabled())
            cached_app.close_button.click()

    @unittest.skipUnless(
        os.environ.get("DISPLAY")
        or os.environ.get("QT_QPA_PLATFORM") == "offscreen",
        "a real or offscreen Qt display is unavailable",
    )
    def test_existing_project_review_is_explicit_and_responsive(self) -> None:
        from PySide6.QtCore import Qt

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            target.mkdir()
            (target / "AGENTS.md").write_text(
                "# Existing project instructions\n",
                encoding="utf-8",
            )
            config = core.WorkflowConfig(
                workflow="existing",
                project_name="project",
                execution_mode="balanced",
                stack_profiles=(),
                with_context_settings=False,
            )
            app = WorkflowConfiguratorApp(
                ConfiguratorController(target, config),
                auto_check_updates=False,
                upstream_service=core.UpstreamUpdateService(
                    cache_path=root / "cache" / "upstream.json",
                    ledger_path=root / "state" / "reviews.json",
                ),
            )
            app.window.resize(1088, 760)
            app.show()
            app.application.processEvents()

            app.review_text.setPlainText(
                "Diff\n----\n--- a/example.py\n+++ b/example.py\n"
                "@@ -1 +1 @@\n-old value\n+new value\n context\n"
            )
            app.review_diff_highlighter.rehighlight()
            app.application.processEvents()
            formatted_colors: dict[int, str] = {}
            block = app.review_text.document().firstBlock()
            while block.isValid():
                formats = block.layout().formats()
                if formats:
                    formatted_colors[block.blockNumber()] = (
                        formats[0].format.background().color().name()
                    )
                block = block.next()
            self.assertIn(2, formatted_colors)
            self.assertIn(4, formatted_colors)
            self.assertIn(5, formatted_colors)
            self.assertIn(6, formatted_colors)
            self.assertNotEqual(formatted_colors[5], formatted_colors[6])
            self.assertIsNotNone(app.upstream_diff_highlighter)

            app.navigation.setCurrentRow(3)
            app.application.processEvents()
            integration_sizes = app.integration_splitter.sizes()
            self.assertGreaterEqual(integration_sizes[0], 280)
            self.assertGreaterEqual(integration_sizes[1], 280)
            self.assertEqual(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
                app.integration_tree.horizontalScrollBarPolicy(),
            )

            app._preview()
            app.application.processEvents()
            self.assertTrue(app.apply_button.isEnabled())
            self.assertIn("Ready:", app.preview_label.text())
            self.assertIn(
                "Context footprint (deterministic proxy)",
                app.overview_text.toPlainText(),
            )
            self.assertEqual(2, app.action_tree.columnCount())
            review_sizes = app.review_splitter.sizes()
            self.assertGreaterEqual(review_sizes[0], 330)
            self.assertGreaterEqual(review_sizes[1], 360)
            self.assertEqual(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
                app.action_tree.horizontalScrollBarPolicy(),
            )
            self.assertEqual(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
                app.review_text.horizontalScrollBarPolicy(),
            )

            proposal_index = next(
                index
                for index, action in enumerate(app._actions)
                if action.status == "conflicting_proposal"
            )
            proposal_item = app.action_tree.topLevelItem(proposal_index)
            app.action_tree.setCurrentItem(proposal_item)
            app.application.processEvents()
            self.assertTrue(app.mark_proposal_reviewed_button.isEnabled())
            self.assertTrue(app.copy_action_button.isEnabled())
            self.assertIn(
                "will not be applied automatically",
                app.review_text.toPlainText(),
            )
            app.mark_proposal_reviewed_button.click()
            app.application.processEvents()
            self.assertEqual("Reviewed; untouched", proposal_item.text(1))
            self.assertIn("1/", app.review_progress_label.text())
            self.assertTrue(app.apply_button.isEnabled())
            health = {
                "mempalace": {"status": "unavailable"},
                "codebase_memory": {"status": "identity-mismatch"},
            }
            health["continuity"] = core.continuity_summary(config, health)
            report = core.analyze_project(target, config)
            report.facts["external_health"] = health
            app._show_report(report)
            self.assertIn(
                "Continuity: LIMITED",
                app.memory_health_text.toPlainText(),
            )
            self.assertIn(
                "Technical details",
                app.memory_health_text.toPlainText(),
            )
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="installed",
                stderr="",
            )
            with (
                mock.patch.object(sys, "platform", "win32"),
                mock.patch(
                    "workflow_configurator.gui.shutil.which",
                    return_value=r"C:\Program Files\PowerShell\7\pwsh.exe",
                ),
                mock.patch(
                    "workflow_configurator.gui.subprocess.run",
                    return_value=completed,
                ) as run_installer,
            ):
                app._install_launcher()
            install_command = run_installer.call_args.args[0]
            self.assertIn(
                "install-workflow-configurator-launcher.ps1",
                install_command[install_command.index("-File") + 1],
            )
            self.assertEqual(
                sys.executable,
                install_command[install_command.index("-Python") + 1],
            )
            self.assertIn("-NoDialog", install_command)
            self.assertNotIn("RunAs", install_command)
            app.close_button.click()


if __name__ == "__main__":
    unittest.main()
