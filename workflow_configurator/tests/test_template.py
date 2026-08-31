from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.py"
CORE = ROOT / "core.py"
MANIFEST = ROOT / "manifest.py"
GUI = ROOT / "gui.py"
PLUGIN_EXPORT = ROOT / "plugin_export.py"
UPSTREAM = ROOT / "upstream.py"
WORKFLOW_GUARD = ROOT / ".github/hooks/scripts/workflow_guard.py"
SCAFFOLD = (
    ROOT
    / ".github/skills/experiment-runner/scripts/scaffold_experiment.py"
)
EXPERIMENT_TOOLS = (
    ROOT
    / ".github/skills/experiment-runner/scripts/experiment_tools.py"
)
DOCTOR = ROOT / ".github/skills/project-doctor/scripts/doctor.py"
SECURITY_GUARD = ROOT / ".github/hooks/scripts/security_guard.py"
TOKEN_PATTERN = re.compile(r"\{\{[A-Z0-9_]+\}\}")
EXPECTED_TOKENS = {
    "{{PROJECT_NAME}}",
    "{{PROJECT_SUMMARY}}",
    "{{TEST_COMMAND}}",
    "{{LINT_COMMAND}}",
    "{{TYPECHECK_COMMAND}}",
    "{{RUN_COMMAND}}",
    "{{MEMORY_WING}}",
    "{{CODEBASE_PROJECT_ID}}",
    "{{INSTALLATION_SURFACE}}",
    "{{PLAN_TIER}}",
    "{{VALIDATION_TIER}}",
    "{{MEMORY_POLICY}}",
    "{{CODE_INTELLIGENCE_POLICY}}",
    "{{REVIEW_TIER}}",
}
CURRENT_TOOL_ALIASES = {"read", "search", "edit", "execute", "web", "agent", "todo"}


def load_installer():
    spec = importlib.util.spec_from_file_location("template_installer", INSTALLER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load installer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frontmatter(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise AssertionError(f"missing frontmatter: {path}")
    try:
        return content.split("---\n", 2)[1]
    except IndexError as error:
        raise AssertionError(f"unclosed frontmatter: {path}") from error


def apply_to_patterns(header: str, path: Path) -> list[str]:
    match = re.search(r"(?m)^applyTo:\s*(.+)$", header)
    if match is None:
        raise AssertionError(f"missing applyTo: {path}")
    value = match.group(1).strip()
    if value.startswith("["):
        try:
            items = ast.literal_eval(value)
        except (SyntaxError, ValueError) as error:
            raise AssertionError(f"invalid applyTo array: {path}") from error
        if (
            not isinstance(items, list)
            or not items
            or any(not isinstance(item, str) or not item for item in items)
        ):
            raise AssertionError(f"applyTo array must contain non-empty strings: {path}")
        return items
    pattern = value.strip("'\"")
    if not pattern:
        raise AssertionError(f"empty applyTo string: {path}")
    return [pattern]


def run(
    command: list[str],
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        input=input_text,
        check=False,
    )


def installer_command(target: Path) -> list[str]:
    return [
        sys.executable,
        str(INSTALLER),
        str(target),
        "--project-name",
        "Installed Project",
        "--summary",
        "Installed by the template test.",
        "--test-command",
        "pytest -q",
        "--lint-command",
        "ruff check .",
        "--typecheck-command",
        "pyright",
        "--run-command",
        "python -m app",
        "--profile",
        "python",
        "--profile",
        "data-science",
        "--profile",
        "fastapi",
        "--profile",
        "react",
        "--mcp",
        "duckdb",
        "--mcp",
        "postgres",
        "--mcp",
        "markitdown",
        "--mcp",
        "context7",
        "--mcp",
        "huggingface",
        "--with-context-settings",
        "--with-security-hooks",
    ]


class TemplateStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_installer()

    def test_manifest_sources_exist(self) -> None:
        files = set(self.installer.CORE_FILES)
        for profile_files in self.installer.PROFILE_FILES.values():
            files.update(profile_files)
        for capability_files in self.installer.LOCAL_CAPABILITY_FILES.values():
            files.update(capability_files)
        files.update(self.installer.SECURITY_HOOK_FILES)
        files.update(self.installer.CONTEXT_SETTINGS_FILES)
        missing = [relative for relative in sorted(files) if not (ROOT / relative).is_file()]
        self.assertEqual([], missing)

    def test_gitignore_artifact_matching_respects_negation(self) -> None:
        matches = self.installer.gitignore_has_artifacts
        self.assertTrue(matches("artifacts/\n"))
        self.assertTrue(matches("**/artifacts/**\n"))
        self.assertFalse(matches("artifacts/\n!artifacts/run/meta.json\n"))
        self.assertTrue(matches("artifacts/\n!artifacts/run/meta.json\nartifacts/\n"))

    def test_only_known_template_tokens_are_used(self) -> None:
        found = set()
        for path in ROOT.rglob("*"):
            if path.is_file() and "tests" not in path.parts and "__pycache__" not in path.parts:
                found.update(TOKEN_PATTERN.findall(path.read_text(encoding="utf-8")))
        self.assertEqual(EXPECTED_TOKENS, found)

    def test_customization_frontmatter(self) -> None:
        for path in (ROOT / ".github/agents").glob("*.agent.md"):
            header = frontmatter(path)
            self.assertRegex(header, r"(?m)^description: .+")
            self.assertRegex(header, r"(?m)^model: .+")
            tools_match = re.search(r"(?m)^tools: \[(.*)\]$", header)
            self.assertIsNotNone(tools_match, path)
            tools = {
                tool.strip().strip("'\"")
                for tool in tools_match.group(1).split(",")
                if tool.strip()
            }
            self.assertLessEqual(tools, CURRENT_TOOL_ALIASES, path)

        for path in (ROOT / ".github/skills").glob("*/SKILL.md"):
            header = frontmatter(path)
            name_match = re.search(r"(?m)^name: ([a-z0-9-]+)$", header)
            self.assertIsNotNone(name_match, path)
            self.assertEqual(path.parent.name, name_match.group(1), path)
            self.assertRegex(header, r"(?m)^description: .+")

        for path in (ROOT / ".github/instructions").glob("*.instructions.md"):
            header = frontmatter(path)
            self.assertRegex(header, r"(?m)^description: .+")
            patterns = apply_to_patterns(header, path)
            self.assertTrue(all(isinstance(pattern, str) and pattern for pattern in patterns))

        self.assertEqual([], list(ROOT.rglob("*.prompt.md")))

    def test_python_sources_compile(self) -> None:
        for path in (
            INSTALLER,
            CORE,
            MANIFEST,
            GUI,
            PLUGIN_EXPORT,
            UPSTREAM,
            WORKFLOW_GUARD,
            SCAFFOLD,
            EXPERIMENT_TOOLS,
            DOCTOR,
            SECURITY_GUARD,
        ):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_researched_contract_docs_are_present(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        surfaces = (ROOT / "docs/AGENT_SURFACES.md").read_text(encoding="utf-8")
        context = (ROOT / "docs/AGENT_CONTEXT.md").read_text(encoding="utf-8")
        environment = (ROOT / "docs/ENVIRONMENT_POLICY.md").read_text(encoding="utf-8")
        observability = (ROOT / "docs/AGENT_OBSERVABILITY.md").read_text(encoding="utf-8")
        mcp = (ROOT / "docs/MCP_SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("Copilot CLI does not read either VS Code MCP file", surfaces)
        self.assertIn("Agent Host", surfaces)
        self.assertIn("search.exclude", context)
        self.assertIn("artifacts/", context)
        self.assertIn("Use exactly one manager per project", environment)
        self.assertIn("New ML, LLM, analytics, or data-engineering project", environment)
        self.assertIn("`uv tool` And `uvx` Are Separate Plumbing", environment)
        self.assertIn("persistent isolated environment", environment)
        self.assertIn("MCP: Open User Configuration", readme)
        self.assertIn("folder-independent services", readme)
        self.assertIn("must not contain `${workspaceFolder}`", readme)
        self.assertIn("state disappears when the server stops", readme)
        for dependency in ("`bwrap`", "`socat`", "`rg`"):
            self.assertIn(dependency, readme)
        self.assertIn("--without-mcp-sandbox", readme)
        self.assertIn("kernel.apparmor_restrict_unprivileged_userns", mcp)
        self.assertIn("VS Code user-profile `mcp.json`", surfaces)
        self.assertIn("windows with no folder", surfaces)
        self.assertIn("Do not register the same", surfaces)
        self.assertIn("Cache Explorer", observability)
        self.assertIn("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", observability)
        for server in (
            "MemPalace",
            "codebase-memory-mcp",
            "DuckDB",
            "Postgres",
            "MarkItDown",
            "Context7",
            "Hugging Face",
        ):
            self.assertIn(server, mcp)
        self.assertIn("An in-memory database requires `--read-write`", mcp)
        self.assertIn("persistent isolated `uv tool`", mcp)

    def test_memory_and_code_intelligence_are_scoped_and_capability_detected(self) -> None:
        memory = (ROOT / "docs/MEMORY_PROTOCOL.md").read_text(encoding="utf-8")
        intelligence = (ROOT / "docs/CODE_INTELLIGENCE.md").read_text(encoding="utf-8")
        copilot = (ROOT / ".github/copilot-instructions.md").read_text(encoding="utf-8")
        planner = (ROOT / ".github/agents/planner.agent.md").read_text(encoding="utf-8")
        executor = (ROOT / ".github/agents/executor.agent.md").read_text(encoding="utf-8")
        reviewer = (ROOT / ".github/agents/reviewer.agent.md").read_text(encoding="utf-8")
        resume = (ROOT / ".github/skills/resume-session/SKILL.md").read_text(encoding="utf-8")
        handoff = (ROOT / ".github/skills/handoff-session/SKILL.md").read_text(encoding="utf-8")
        plan_task = (ROOT / ".github/skills/plan-task/SKILL.md").read_text(encoding="utf-8")
        memory_health = (ROOT / ".github/skills/memory-health/SKILL.md").read_text(encoding="utf-8")
        project_doctor = (ROOT / ".github/skills/project-doctor/SKILL.md").read_text(encoding="utf-8")
        python_rules = (ROOT / ".github/instructions/python.instructions.md").read_text(encoding="utf-8")
        for marker in (
            "mempalace_status",
            "mempalace_diary_read",
            "mempalace_diary_write",
            "{{MEMORY_WING}}",
            "MEMORY DEGRADED",
        ):
            self.assertIn(marker, memory)
        for marker in (
            "Scout",
            "Verify",
            "Auditor",
            "get_architecture",
            "trace_path",
            "{{CODEBASE_PROJECT_ID}}",
            "actually exposed",
            "CODE GRAPH DEGRADED",
            "known file",
        ):
            self.assertIn(marker, intelligence)
        self.assertIn("{{MEMORY_POLICY}}", copilot)
        self.assertIn("codebase-memory", copilot)
        self.assertIn("{{MEMORY_WING}}", copilot)
        self.assertIn("mempalace_diary_read", resume)
        self.assertIn("{{MEMORY_WING}}", resume)
        self.assertIn("mempalace_diary_write", handoff)
        self.assertIn("{{MEMORY_WING}}", plan_task)
        for marker in (
            "mempalace_status",
            "mempalace_diary_read",
            "mempalace_search",
            "mempalace_memories_filed_away",
        ):
            self.assertIn(marker, memory_health)
        for marker in ("mempalace_status", "mempalace_diary_read", "codebase-memory"):
            self.assertIn(marker, project_doctor)
        for agent in (planner, executor, reviewer):
            for marker in ("{{MEMORY_WING}}", "{{CODEBASE_PROJECT_ID}}", "codebase-memory"):
                self.assertIn(marker, agent)
        for marker in (
            "exactly one environment manager per project",
            "environment.yml",
            "conda-lock.yml",
            "uv.lock",
            "New ML/data project",
            "Miniforge/Conda",
            "New pure-Python tool or CLI",
            "never mix",
        ):
            self.assertIn(marker, python_rules)


class InstallerBehaviorTests(unittest.TestCase):
    def test_minimal_command_installs_personal_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "personal-project"
            result = run([sys.executable, str(INSTALLER), str(target)])
            self.assertEqual(0, result.returncode, result.stderr)
            installed = {
                path.relative_to(target).as_posix()
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                {
                    "AGENTS.md",
                    ".github/copilot-instructions.md",
                    "docs/WORKFLOW_CONFIG.md",
                },
                installed,
            )
            self.assertFalse((target / ".vscode/mcp.json").exists())
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# personal-project Agent Guide", agents)
            self.assertIn("`pytest -x -q`", agents)
            self.assertIn("`ruff check .`", agents)
            self.assertIn("`pyright`", agents)
            self.assertIn("Surface: `minimal`", agents)
            self.assertIn("wing `personal_project`", agents)

    def test_existing_gitignore_is_preserved_and_extended_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            gitignore = target / ".gitignore"
            original = "data/\n# project-specific rule\n"
            gitignore.write_text(original, encoding="utf-8")
            gitignore.chmod(0o640)

            result = run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--profile",
                    "data-science",
                ]
            )
            self.assertEqual(0, result.returncode, result.stderr)
            updated = gitignore.read_text(encoding="utf-8")
            self.assertTrue(updated.startswith(original))
            self.assertEqual(1, updated.count("artifacts/"))
            self.assertEqual(0o640, gitignore.stat().st_mode & 0o777)

    def test_standalone_local_capability_selection_is_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            result = run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--integration",
                    "experiment-runner",
                ]
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(
                (
                    target
                    / ".github/skills/experiment-runner/scripts/experiment_tools.py"
                ).is_file()
            )

    def test_explicit_unsandboxed_mcp_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            result = run(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(target),
                    "--mcp",
                    "duckdb",
                    "--mcp",
                    "markitdown",
                    "--without-mcp-sandbox",
                ]
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("will run unsandboxed", result.stderr)

            config = json.loads((target / ".vscode/mcp.json").read_text(encoding="utf-8"))
            self.assertNotIn("sandbox", config)
            self.assertFalse(config["servers"]["duckdb"]["sandboxEnabled"])
            self.assertFalse(config["servers"]["markitdown"]["sandboxEnabled"])

    def test_complete_install_and_collision_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            first = run(installer_command(target))
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertTrue((target / "docs/plans").is_dir())

            for path in target.rglob("*"):
                if path.is_file():
                    self.assertIsNone(TOKEN_PATTERN.search(path.read_text(encoding="utf-8")), path)

            config = json.loads((target / ".vscode/mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                ["duckdb", "postgres", "markitdown", "context7", "huggingface"],
                list(config["servers"]),
            )
            self.assertIn("--read-write", config["servers"]["duckdb"]["args"])
            self.assertEqual("${input:postgres-uri}", config["servers"]["postgres"]["env"]["DATABASE_URI"])
            self.assertTrue(config["inputs"][0]["password"])
            self.assertIn("${workspaceFolder}", config["sandbox"]["filesystem"]["denyWrite"])
            settings = json.loads((target / ".vscode/settings.json").read_text(encoding="utf-8"))
            self.assertTrue(settings["search.exclude"]["**/artifacts/**"])
            hooks = json.loads((target / ".github/hooks/security.json").read_text(encoding="utf-8"))
            self.assertIn("PreToolUse", hooks["hooks"])

            before = {
                path.relative_to(target): path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }
            second = run(installer_command(target))
            self.assertEqual(3, second.returncode)
            after = {
                path.relative_to(target): path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            result = run([*installer_command(target), "--dry-run"])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(target.exists())

    def test_symlinked_destination_directory_is_rejected(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / ".github").symlink_to(outside, target_is_directory=True)
            result = run(installer_command(target))
            self.assertEqual(2, result.returncode)
            self.assertIn("unsafe destination paths", result.stderr)
            self.assertEqual([], list(outside.rglob("*")))


class DoctorBehaviorTests(unittest.TestCase):
    def test_clean_install_and_broken_state_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            self.assertEqual(0, run(installer_command(target)).returncode)
            (target / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
            clean = run(
                [sys.executable, str(target / DOCTOR.relative_to(ROOT)), "--root", str(target), "--strict", "--json"]
            )
            self.assertEqual(0, clean.returncode, clean.stderr)
            report = json.loads(clean.stdout)
            self.assertEqual(0, report["errors"])
            self.assertEqual(0, report["warnings"])

            handoff = target / "docs/HANDOFF.md"
            handoff.write_text(
                handoff.read_text(encoding="utf-8").replace(
                    "**Active plan:** none",
                    "**Active plan:** docs/plans/missing.md",
                ),
                encoding="utf-8",
            )
            instructions = target / ".github/copilot-instructions.md"
            instructions.write_text(
                instructions.read_text(encoding="utf-8") + "\n{{BROKEN_TOKEN}}\n",
                encoding="utf-8",
            )
            broken = run(
                [sys.executable, str(target / DOCTOR.relative_to(ROOT)), "--root", str(target), "--json"]
            )
            self.assertEqual(1, broken.returncode)
            codes = {item["code"] for item in json.loads(broken.stdout)["findings"]}
            self.assertIn("plan.missing", codes)
            self.assertIn("template.unresolved", codes)

    def test_malformed_mcp_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            self.assertEqual(0, run(installer_command(target)).returncode)
            doctor = target / DOCTOR.relative_to(ROOT)
            (target / ".vscode/mcp.json").write_text("{not json}\n", encoding="utf-8")
            malformed = run([sys.executable, str(doctor), "--root", str(target), "--json"])
            self.assertEqual(1, malformed.returncode)
            malformed_codes = {item["code"] for item in json.loads(malformed.stdout)["findings"]}
            self.assertIn("mcp.json", malformed_codes)
            (target / ".vscode/mcp.json").write_text(
                '{"servers": {}}\n',
                encoding="utf-8",
            )
            missing = run(
                [sys.executable, str(doctor), "--root", str(target), "--json"]
            )
            missing_codes = {
                item["code"] for item in json.loads(missing.stdout)["findings"]
            }
            self.assertIn("mcp.selected-missing", missing_codes)

    def test_task_tier_requires_matching_plan_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            self.assertEqual(0, run(installer_command(target)).returncode)
            handoff = target / "docs/HANDOFF.md"
            handoff.write_text(
                handoff.read_text(encoding="utf-8").replace(
                    "**Task tier:** 0", "**Task tier:** 2"
                ),
                encoding="utf-8",
            )
            doctor = target / DOCTOR.relative_to(ROOT)
            result = run([sys.executable, str(doctor), "--root", str(target), "--json"])
            self.assertEqual(1, result.returncode)
            codes = {item["code"] for item in json.loads(result.stdout)["findings"]}
            self.assertIn("plan.required", codes)
            handoff.write_text(
                handoff.read_text(encoding="utf-8").replace(
                    "**Active plan:** none", "**Active plan:** /etc/hosts"
                ),
                encoding="utf-8",
            )
            escaped = run(
                [sys.executable, str(doctor), "--root", str(target), "--json"]
            )
            escaped_codes = {
                item["code"] for item in json.loads(escaped.stdout)["findings"]
            }
            self.assertIn("plan.path", escaped_codes)

    def test_handoff_budget_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            self.assertEqual(0, run(installer_command(target)).returncode)
            handoff = target / "docs/HANDOFF.md"
            handoff.write_text(
                handoff.read_text(encoding="utf-8") + "\n".join(["history"] * 50),
                encoding="utf-8",
            )
            doctor = target / DOCTOR.relative_to(ROOT)
            result = run(
                [sys.executable, str(doctor), "--root", str(target), "--strict", "--json"]
            )
            self.assertEqual(1, result.returncode)
            codes = {item["code"] for item in json.loads(result.stdout)["findings"]}
            self.assertIn("handoff.budget", codes)


class WorkflowGuardTests(unittest.TestCase):
    def invoke(self, root: Path) -> dict[str, object]:
        result = run(
            [sys.executable, str(WORKFLOW_GUARD)],
            cwd=root,
            input_text=json.dumps(
                {"cwd": str(root), "hook_event_name": "Stop"}
            ),
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_change_isolation_and_plan_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/WORKFLOW_CONFIG.md").write_text(
                "# Workflow Configuration\n\n- Plan tier: `mini`\n",
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text("baseline\n", encoding="utf-8")
            self.assertEqual(0, run(["git", "init"], cwd=root).returncode)
            self.assertEqual(0, run(["git", "add", "."], cwd=root).returncode)
            committed = run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-m",
                    "baseline",
                ],
                cwd=root,
            )
            self.assertEqual(0, committed.returncode, committed.stderr)
            self.assertEqual({}, self.invoke(root))

            (root / "AGENTS.md").write_text("changed\n", encoding="utf-8")
            changed = self.invoke(root)
            self.assertEqual("ask", changed["permissionDecision"])
            self.assertIn(
                "workflow-control files changed",
                changed["permissionDecisionReason"],
            )

            (root / "docs/HANDOFF.md").write_text(
                "# Handoff\n\n**Task tier:** 2\n**Active plan:** /etc/hosts\n",
                encoding="utf-8",
            )
            escaped = self.invoke(root)
            self.assertEqual("ask", escaped["permissionDecision"])
            self.assertIn(
                "project-relative",
                escaped["permissionDecisionReason"],
            )


class SecurityHookTests(unittest.TestCase):
    def invoke(self, payload: dict[str, object]) -> dict[str, object]:
        result = run(
            [sys.executable, str(SECURITY_GUARD)],
            input_text=json.dumps(payload),
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_safe_calls_fall_through_and_risky_calls_use_dual_envelopes(self) -> None:
        safe = self.invoke(
            {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest -q"}}
        )
        self.assertEqual({}, safe)

        review = self.invoke(
            {"sessionId": "s", "toolName": "bash", "toolArgs": {"command": "git reset --hard HEAD~1"}}
        )
        self.assertEqual("ask", review["permissionDecision"])
        self.assertEqual("ask", review["hookSpecificOutput"]["permissionDecision"])

        patch = self.invoke(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "functions.apply_patch",
                "tool_input": {"input": "*** Update File: /repo/.github/hooks/security.json\n-old\n+new"},
            }
        )
        self.assertEqual("deny", patch["permissionDecision"])
        self.assertEqual("PreToolUse", patch["hookSpecificOutput"]["hookEventName"])

        catastrophic = self.invoke(
            {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        )
        self.assertEqual("deny", catastrophic["permissionDecision"])

        powershell = self.invoke(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "powershell",
                "tool_input": {"command": "Remove-Item -Recurse -Force artifacts"},
            }
        )
        self.assertEqual("ask", powershell["permissionDecision"])

        redirect = self.invoke(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "cat replacement.json > .github/hooks/security.json"
                },
            }
        )
        self.assertEqual("deny", redirect["permissionDecision"])

        traversal_patch = self.invoke(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "functions.apply_patch",
                "tool_input": {
                    "input": "*** Update File: /repo/.github/../.github/./hooks/security.json\n-old\n+new"
                },
            }
        )
        self.assertEqual("deny", traversal_patch["permissionDecision"])

        traversal_shell = self.invoke(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "cat replacement.json > .github/../.github/./hooks/security.json"
                },
            }
        )
        self.assertEqual("deny", traversal_shell["permissionDecision"])


class ExperimentScaffoldTests(unittest.TestCase):
    def test_unique_atomic_runs_and_invalid_input_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            config = project / "config.yaml"
            data = project / "data.csv"
            config.write_text("depth: 4\n", encoding="utf-8")
            data.write_text("x,y\n1,2\n", encoding="utf-8")
            (project / "environment.yaml").write_text(
                "name: experiment\ndependencies:\n  - python=3.12\n",
                encoding="utf-8",
            )
            (project / "conda-lock.yaml").write_text(
                "version: 1\nmetadata: {}\npackage: []\n",
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(SCAFFOLD),
                "--name",
                "same-name",
                "--config",
                str(config),
                "--data",
                str(data),
                "--seed",
                "7",
            ]

            self.assertEqual(0, run(command, cwd=project).returncode)
            self.assertEqual(0, run(command, cwd=project).returncode)
            runs = sorted((project / "artifacts").glob("20*"))
            self.assertEqual(2, len(runs))
            self.assertNotEqual(runs[0].name, runs[1].name)
            fingerprints = set()
            for run_dir in runs:
                metadata = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
                self.assertEqual(7, metadata["seed"])
                self.assertEqual("config.yaml", metadata["frozen_config"])
                self.assertEqual(2, metadata["schema_version"])
                dependency_paths = {item["path"] for item in metadata["dependencies"]}
                self.assertIn("environment.yaml", dependency_paths)
                self.assertIn("conda-lock.yaml", dependency_paths)
                fingerprints.add(metadata["provenance_fingerprint"])
                self.assertEqual("", (run_dir / "metrics.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(1, len(fingerprints))

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            result = run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--name",
                    "invalid",
                    "--config",
                    "missing.yaml",
                    "--data-version",
                    "snapshot-1",
                ],
                cwd=project,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((project / "artifacts").exists())

    def test_evidence_lifecycle_and_integrity_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            config = project / "config.yaml"
            data = project / "data"
            data.mkdir()
            config.write_text("depth: 4\n", encoding="utf-8")
            (data / "part.csv").write_text("x,y\n1,2\n", encoding="utf-8")
            scaffold = [
                sys.executable,
                str(SCAFFOLD),
                "--name",
                "comparison",
                "--config",
                str(config),
                "--data",
                str(data),
            ]
            self.assertEqual(0, run(scaffold, cwd=project).returncode)
            self.assertEqual(0, run(scaffold, cwd=project).returncode)
            baseline, candidate = sorted((project / "artifacts").glob("20*"))

            def append(run_dir: Path, value: str) -> subprocess.CompletedProcess[str]:
                return run(
                    [
                        sys.executable,
                        str(EXPERIMENT_TOOLS),
                        "append",
                        "--run",
                        str(run_dir),
                        "--metric",
                        "rmse",
                        "--value",
                        value,
                        "--split",
                        "validation",
                        "--step",
                        "1",
                        "--sample-count",
                        "100",
                        "--fold",
                        "0",
                    ]
                )

            self.assertEqual(0, append(baseline, "1.0").returncode)
            self.assertEqual(0, append(candidate, "1.005").returncode)
            comparison = [
                sys.executable,
                str(EXPERIMENT_TOOLS),
                "compare",
                "--candidate",
                str(candidate),
                "--baseline",
                str(baseline),
                "--metric",
                "rmse",
                "--split",
                "validation",
                "--direction",
                "lower",
                "--aggregation",
                "mean-final-folds",
            ]
            self.assertEqual(0, run([*comparison, "--max-regression-percent", "1"]).returncode)
            self.assertEqual(4, run([*comparison, "--max-regression-percent", "0.1"]).returncode)
            self.assertEqual(2, run([*comparison, "--max-regression-percent", "-1"]).returncode)

            registry = project / "experiments.md"
            register = [
                sys.executable,
                str(EXPERIMENT_TOOLS),
                "register",
                "--run",
                str(candidate),
                "--registry",
                str(registry),
                "--key-result",
                "rmse=1.005",
                "--baseline",
                baseline.name,
                "--decision",
                "candidate",
            ]
            self.assertEqual(0, run(register).returncode)
            self.assertEqual(0, run(register).returncode)
            self.assertEqual(1, registry.read_text(encoding="utf-8").count(f"| {candidate.name} |"))

            lock = candidate / ".metrics.jsonl.lock"
            lock.touch()
            locked = run(
                [
                    sys.executable,
                    str(EXPERIMENT_TOOLS),
                    "append",
                    "--run",
                    str(candidate),
                    "--metric",
                    "mae",
                    "--value",
                    "0.5",
                    "--split",
                    "validation",
                    "--step",
                    "1",
                    "--sample-count",
                    "100",
                ]
            )
            self.assertEqual(2, locked.returncode)
            lock.unlink()

            (data / "part.csv").write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
            ordinary_validation = run(
                [sys.executable, str(EXPERIMENT_TOOLS), "validate", "--run", str(candidate)]
            )
            self.assertEqual(0, ordinary_validation.returncode)
            drift = run(
                [
                    sys.executable,
                    str(EXPERIMENT_TOOLS),
                    "validate",
                    "--run",
                    str(candidate),
                    "--verify-source-data",
                ]
            )
            self.assertEqual(2, drift.returncode)

    def test_malformed_jsonl_and_fingerprint_tampering_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            config = project / "config.yaml"
            config.write_text("depth: 4\n", encoding="utf-8")
            created = run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--name",
                    "tamper",
                    "--config",
                    str(config),
                    "--data-version",
                    "snapshot-1",
                ],
                cwd=project,
            )
            self.assertEqual(0, created.returncode)
            run_dir = next((project / "artifacts").glob("20*"))
            (run_dir / "metrics.jsonl").write_text("\n", encoding="utf-8")
            malformed = run([sys.executable, str(EXPERIMENT_TOOLS), "validate", "--run", str(run_dir)])
            self.assertEqual(2, malformed.returncode)

            (run_dir / "metrics.jsonl").write_text("", encoding="utf-8")
            meta_path = run_dir / "meta.json"
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            metadata["provenance_fingerprint"] = "0" * 64
            meta_path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            tampered = run([sys.executable, str(EXPERIMENT_TOOLS), "validate", "--run", str(run_dir)])
            self.assertEqual(2, tampered.returncode)

    def test_external_data_requires_explicit_scaffold_and_validation_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            external = root / "external"
            project.mkdir()
            external.mkdir()
            config = project / "config.yaml"
            data = external / "data.csv"
            config.write_text("depth: 4\n", encoding="utf-8")
            data.write_text("x,y\n1,2\n", encoding="utf-8")
            command = [
                sys.executable,
                str(SCAFFOLD),
                "--name",
                "external",
                "--config",
                str(config),
                "--data",
                str(data),
            ]
            rejected = run(command, cwd=project)
            self.assertNotEqual(0, rejected.returncode)
            self.assertFalse((project / "artifacts").exists())

            accepted = run([*command, "--allow-external-data"], cwd=project)
            self.assertEqual(0, accepted.returncode, accepted.stderr)
            run_dir = next((project / "artifacts").glob("20*"))
            ordinary = run(
                [sys.executable, str(EXPERIMENT_TOOLS), "validate", "--run", str(run_dir)]
            )
            self.assertEqual(0, ordinary.returncode)
            blocked_rehash = run(
                [
                    sys.executable,
                    str(EXPERIMENT_TOOLS),
                    "validate",
                    "--run",
                    str(run_dir),
                    "--verify-source-data",
                ]
            )
            self.assertEqual(2, blocked_rehash.returncode)
            allowed_rehash = run(
                [
                    sys.executable,
                    str(EXPERIMENT_TOOLS),
                    "validate",
                    "--run",
                    str(run_dir),
                    "--verify-source-data",
                    "--allow-data-root",
                    str(external),
                ]
            )
            self.assertEqual(0, allowed_rehash.returncode, allowed_rehash.stderr)

            metadata_path = run_dir / "meta.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["frozen_config"] = "../../config.yaml"
            metadata_path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            escaped_config = run(
                [sys.executable, str(EXPERIMENT_TOOLS), "validate", "--run", str(run_dir)]
            )
            self.assertEqual(2, escaped_config.returncode)

    def test_dataset_directory_rejects_embedded_symlinks(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            data = project / "data"
            data.mkdir()
            config = project / "config.yaml"
            external = project / "external.csv"
            config.write_text("depth: 4\n", encoding="utf-8")
            external.write_text("x,y\n1,2\n", encoding="utf-8")
            (data / "linked.csv").symlink_to(external)
            result = run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--name",
                    "symlink-data",
                    "--config",
                    str(config),
                    "--data",
                    str(data),
                ],
                cwd=project,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((project / "artifacts").exists())


if __name__ == "__main__":
    unittest.main()