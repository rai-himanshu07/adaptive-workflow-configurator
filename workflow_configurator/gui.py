"""Optional PySide6 desktop adapter for the workflow configurator.

The controller and formatters remain display-independent. PySide6 is imported
only when a real window is created, so the core and headless smoke path keep
working without the optional GUI dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from . import core
except ImportError:  # Running ``python workflow_configurator/gui.py`` directly.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from workflow_configurator import core


USER_GUIDE = """# Workflow Configurator Guide

## Safe workflow

1. **Analyze** reads project conventions, workflow overhead, memory identity,
   code-graph state, and conflicts. It never changes the project.
2. **Preview** renders every proposed file or safe merge. Any setting change
   invalidates the preview.
3. **Review** selects an action to show its wrapped diff. For a user-owned
   conflict, copy the diff or open the existing file, then acknowledge the
   proposal while keeping the existing file. Added, removed, file-header, and
   hunk lines are palette-aware color coded while retaining their text markers.
   Manual edits require another Preview.
4. **Apply** adds only missing files and documented additive settings. Existing
   conflicting files remain untouched, whether acknowledged or not.
5. **Recovery** lists generated paths and exact backups for manual action. The
   configurator never restores or deletes files automatically.

## Installation surfaces

- **Minimal:** three compact files for small/low-risk or Velocity projects.
- **Standard:** adds compact agents, task state, context exclusions, and doctor.
- **Governed:** adds one specification workflow, selected guards, and stronger
  evidence for security, migration, regulated, or cross-service work.

Project size also selects a bounded scan budget: 25k entries for small, 100k for
medium, and 250k for large. Dependency environments and tool caches are skipped.
Discovery supports metrics and recommendations; Apply validates its exact
destinations independently.

## Execution mode and current task

1. On **Project**, choose the target folder and optionally enter an initial
    **Current task**. The desktop launcher opens this configurator repository by
    default, so select the project you actually want to configure.
2. On **Workflow**, **Execution mode: velocity** is the default for new
    projects. It keeps validation and review manual, with bounded project-memory
    and code-graph lookups. Choose `balanced` for adaptive checks and review;
    older imported configurations without an execution mode stay Balanced.
3. On **Tools & Profiles**, select any relevant stack profiles and describe
    other technologies such as Rust in **Other technologies**. New configurator
    projects leave test, lint, typecheck, and run commands unconfigured; supply
    the actual commands for each project.
4. On **Review & Apply**, choose **Preview changes** before **Apply safe changes**.
    Existing agent files are never overwritten: inspect their proposals and
    merge the new policy manually. Previously installed hooks also stay in place.

An initial task is written to `docs/CURRENT_TASK.md` only on explicit Apply.
A task in chat or an explicitly named file takes precedence; if none is clear,
the agent asks. Existing task files remain untouched proposals. Task text is
included in exported configuration, previews, and manifests; do not enter secrets.
Use **File > Export configuration** to keep form settings for a later launch.

## Task and testing tiers

In `balanced` mode, questions, research, documentation, and trivial configuration
need no plan or code tests. Low-risk edits use an inline/mini plan and the
smallest affected check. Coupled changes use a compact plan and focused checks
per coherent slice. Broad suites run once at a checkpoint or governed risk
boundary. In `velocity` mode, plans, tests, lint, typecheck, doctor, and review
are user-invoked; optional hooks are not installed unless selected. Explicit
policy overrides may require checks or review again. Hard Apply safety never
depends on the execution mode.

## Tools and profiles

Project MCP choices generate reviewed local configuration. Optional capabilities
are either bundled local templates or guidance only; external software is never
installed automatically. Session profiles explain what to enable, but cannot
change the tools of an already-running agent session.

## Updates and local plugin pilot

The desktop UI checks GitHub's Awesome Copilot metadata at most once per day.
Automatic checks compare the latest catalog with the local reviewed baseline and
download no asset bodies. Explicit inspection fetches only one selected,
size-capped text asset and renders a read-only untrusted diff. Record a
rationale-backed disposition for every item before advancing the local baseline.
The review queue lists upstream metadata differences, not installed product
updates or an instruction to install all listed assets. Monitored changes and
other catalog differences are shown separately; pending entries do not alter
configured projects. Nothing is installed, applied, or marked reviewed
automatically.

The optional local plugin export packages only the five already-reviewed generic
specialists. Preview shows every file and hash. Export refuses overwrite and
does not install, enable, update, or publish the plugin.

## Memory and code identity

Every project uses one explicit MemPalace wing. `wing_copilot` is reserved for
cross-project lessons. Mining updates source retrieval; explicit checkpoints
record decisions and session synthesis. codebase-memory is persistent locally,
but its freshness must be checked when the active tool surface supports it.

Concurrent writable MemPalace sessions can hold the palace lock and block manual
mining. A reviewed shared writable hub is the recommended multi-session
topology; this configurator diagnoses it but never upgrades or stops services.

Analyze and Preview show a deterministic context-footprint proxy for current and
safe-post-Apply workflow files. Memory & Code health summarizes continuity as
ready, limited, degraded, or deliberately disabled according to active policy.

## Advanced Overrides

Only workflow-process controls are overridable. Weaker values require a reason
and confirmation. Path, secret, sandbox, destructive-operation, preview,
collision, transactional, overwrite, deletion, and rollback protections are
permanent.
""" + "\n\n" + core.render_policy_override_guide()


def preview_signature(target: Path | str, config: core.WorkflowConfig) -> str:
    return json.dumps(
        {
            "target": str(Path(target).expanduser().resolve(strict=False)),
            "config": config.to_dict(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def guard_intent_for_config(config: core.WorkflowConfig) -> str:
    value = config.protocol_guard
    if value is None:
        decision = config.policy_overrides.get("protocol_guard", {})
        selected = decision.get("value") if isinstance(decision, dict) else None
        return selected if selected in {"on", "off"} else "auto"
    return "on" if value is True else "off" if value is False else "auto"


def protocol_guard_for_intent(intent: str) -> bool | None:
    if intent not in {"auto", "on", "off"}:
        raise core.ConfigError("protocol guard intent must be auto, on, or off")
    return {"auto": None, "on": True, "off": False}[intent]


def diff_line_kind(text: str) -> str | None:
    """Classify a unified-diff line without relying on color for meaning."""

    if text.startswith("@@"):
        return "hunk"
    if text.startswith(("+++ ", "--- ")):
        return "file"
    if text.startswith("+"):
        return "addition"
    if text.startswith("-") and text.strip("-").strip():
        return "deletion"
    if text.startswith("\\ No newline"):
        return "note"
    return None


def install_diff_highlighter(
    widget: Any,
    QtGui: Any,
) -> Any:
    """Install a palette-aware highlighter that activates after a diff marker."""

    dark = widget.palette().color(
        QtGui.QPalette.ColorRole.Base
    ).lightness() < 128
    colors = (
        {
            "addition": ("#153d2d", "#b7f7c7"),
            "deletion": ("#4a2024", "#ffc5c5"),
            "hunk": ("#1e3557", "#bfdbfe"),
            "file": ("#343a40", "#f1f3f5"),
            "note": ("#3b3445", "#e9d5ff"),
        }
        if dark
        else {
            "addition": ("#d8f3dc", "#14532d"),
            "deletion": ("#fde2e2", "#7f1d1d"),
            "hunk": ("#dbeafe", "#1e3a8a"),
            "file": ("#e9ecef", "#343a40"),
            "note": ("#f3e8ff", "#6b21a8"),
        }
    )

    class UnifiedDiffHighlighter(QtGui.QSyntaxHighlighter):
        IN_DIFF = 1

        def __init__(self, document: Any) -> None:
            super().__init__(document)
            self.formats: dict[str, Any] = {}
            for kind, (background, foreground) in colors.items():
                text_format = QtGui.QTextCharFormat()
                text_format.setBackground(QtGui.QColor(background))
                text_format.setForeground(QtGui.QColor(foreground))
                if kind in {"hunk", "file"}:
                    text_format.setFontWeight(QtGui.QFont.Weight.Bold)
                self.formats[kind] = text_format

        def highlightBlock(self, text: str) -> None:
            marker = text.strip() in {"Diff", "Diff:", "Unified diff"}
            active = marker or self.previousBlockState() == self.IN_DIFF
            self.setCurrentBlockState(self.IN_DIFF if active else -1)
            if marker or not active:
                return
            normalized = text.lstrip()
            kind = diff_line_kind(normalized)
            if kind is None:
                return
            offset = len(text) - len(normalized)
            self.setFormat(offset, len(normalized), self.formats[kind])

    return UnifiedDiffHighlighter(widget.document())


class ConfiguratorController:
    """Thin, display-free adapter over the shared core operations."""

    def __init__(
        self,
        target: Path | str | None = None,
        config: core.WorkflowConfig | None = None,
    ) -> None:
        self.target = Path(target).expanduser() if target is not None else Path.cwd()
        self._project_name_explicit = config is not None
        self._memory_wing_explicit = config is not None
        self._codebase_project_explicit = config is not None
        self.config = config or core.config_for_target(self.target)
        self.report: core.AnalysisReport | None = None
        self.last_result: core.ApplyResult | None = None
        self.last_restore_plan: dict[str, Any] | None = None

    def set_target(self, target: Path | str) -> core.WorkflowConfig:
        self.target = Path(target).expanduser()
        raw = self.config.to_dict()
        changed = False
        target_name = self.target.name or "project"
        if not self._project_name_explicit:
            raw["project_name"] = target_name
            changed = True
        if not self._memory_wing_explicit:
            raw["memory_wing"] = core.canonical_memory_wing(target_name)
            changed = True
        if not self._codebase_project_explicit:
            raw["codebase_project_id"] = core.canonical_codebase_project_id(
                target_name
            )
            changed = True
        if changed:
            self.config = core.WorkflowConfig.from_dict(raw)
        self.report = None
        return self.config

    def set_config(self, config: core.WorkflowConfig) -> None:
        self.config = config

    @property
    def identity_explicit(self) -> bool:
        return self._project_name_explicit

    def mark_identity_explicit(self) -> None:
        self._project_name_explicit = True

    def mark_memory_wing_explicit(self) -> None:
        self._memory_wing_explicit = True

    def mark_codebase_project_explicit(self) -> None:
        self._codebase_project_explicit = True

    def set_identity(self, project_name: str, summary: str | None = None) -> core.WorkflowConfig:
        raw = self.config.to_dict()
        raw["project_name"] = project_name
        if summary is not None:
            raw["summary"] = summary
        self.config = core.WorkflowConfig.from_dict(raw)
        self._project_name_explicit = True
        return self.config

    def update_config(self, **values: Any) -> core.WorkflowConfig:
        aliases = {
            "size": "project_size",
            "testing": "testing_level",
            "profiles": "stack_profiles",
            "mcp": "mcp_servers",
            "integrations": "optional_integrations",
            "rigor": "rigor_preset",
        }
        for source, destination in aliases.items():
            if source in values and destination not in values:
                values[destination] = values.pop(source)
        if "project_name" in values:
            self._project_name_explicit = True
        if "memory_wing" in values:
            self._memory_wing_explicit = True
        if "codebase_project_id" in values:
            self._codebase_project_explicit = True
        raw = self.config.to_dict()
        raw.update(values)
        self.config = core.WorkflowConfig.from_dict(raw)
        return self.config

    def analyze(self, *, include_health: bool = False) -> core.AnalysisReport:
        self.report = core.analyze_project(
            self.target, self.config, include_health=include_health
        )
        return self.report

    def preview(self) -> core.AnalysisReport:
        return self.analyze(include_health=False)

    def export_config(self, path: Path | str) -> Path:
        return core.save_config(self.config, path)

    def import_config(self, path: Path | str) -> core.WorkflowConfig:
        self.config = core.load_config(path)
        self._project_name_explicit = True
        self._memory_wing_explicit = True
        self._codebase_project_explicit = True
        self.report = None
        return self.config

    def apply(
        self,
        *,
        expected_report: core.AnalysisReport | None = None,
    ) -> core.ApplyResult:
        self.last_result = core.apply_project(
            self.target,
            self.config,
            expected_report=expected_report,
        )
        self.report = self.last_result.report
        return self.last_result

    def restore_instructions(
        self,
        manifest: Path | str | None = None,
        *,
        output: Path | str | None = None,
    ) -> dict[str, Any]:
        self.last_restore_plan = core.restore_instructions(manifest, self.target, output=output)
        self.report = None
        return self.last_restore_plan

    def policy(self) -> core.EngineeringPolicy:
        return core.derive_policy(self.config)

    def status(self) -> dict[str, Any]:
        return {
            "target": str(self.target),
            "identity_explicit": self.identity_explicit,
            "config": self.config.to_dict(),
            "policy": self.policy().to_dict(),
            "analysis": self.report.to_dict() if self.report is not None else None,
            "last_result": self.last_result.to_dict() if self.last_result is not None else None,
            "last_restore_plan": self.last_restore_plan,
        }


def headless_smoke(
    target: Path | str | None = None,
    config: core.WorkflowConfig | None = None,
) -> dict[str, Any]:
    controller = ConfiguratorController(target, config)
    report = controller.analyze()
    return {
        "ok": not report.errors,
        "controller": "loaded",
        "target": str(controller.target),
        "actions": len(report.actions),
        "proposals": len(report.proposals),
        "errors": report.errors,
    }


def format_project_overview(report: core.AnalysisReport) -> str:
    facts = report.facts
    scan_entries = facts.get("scan_entries")
    scan_limit = facts.get("scan_entry_limit")
    scan_detail = (
        f" ({scan_entries:,}/{scan_limit:,} entries"
        f"; {facts.get('scan_method', 'targeted')} discovery)"
        if isinstance(scan_entries, int) and isinstance(scan_limit, int)
        else ""
    )
    lines = [
        f"Target: {report.target}",
        f"Discovery: {'complete' if facts.get('scan_complete', True) else 'partial'}"
        f"{scan_detail}",
        f"Languages: {', '.join(facts.get('languages', {})) or 'none detected'}",
        f"Manifests: {', '.join(facts.get('manifests', [])) or 'none detected'}",
        "Environment: " + (", ".join(facts.get("environment_managers", [])) or "not detected"),
        f"Git repository: {'yes' if facts.get('git', {}).get('present') else 'no'}",
    ]
    metrics = facts.get("workflow_metrics", {})
    if metrics:
        loc = metrics.get("loc", {})
        ratios = metrics.get("ratios", {})
        lines.extend(
            [
                "",
                "Workflow audit",
                "- LOC: "
                + ", ".join(f"{name}={value}" for name, value in loc.items()),
                f"- Test/production ratio: {ratios.get('test_to_production')}",
                f"- Workflow/production ratio: {ratios.get('workflow_to_production')}",
                f"- Legacy surface candidates: {len(metrics.get('legacy_surface_candidates', []))}",
                f"- Large files/functions: {len(metrics.get('large_files', []))}/"
                f"{len(metrics.get('large_python_functions', []))}",
            ]
        )
    footprint = facts.get("context_footprint")
    if isinstance(footprint, Mapping):
        lines.extend(["", format_context_footprint(footprint).rstrip()])
    health = facts.get("external_health")
    if isinstance(health, Mapping):
        continuity = health.get("continuity")
        if isinstance(continuity, Mapping):
            lines.extend(
                [
                    "",
                    f"Continuity: {str(continuity.get('status', 'unknown')).upper()}",
                    str(continuity.get("summary", "")),
                ]
            )
    if report.recommendations:
        lines.extend(["", "Recommendations", *[f"- {item}" for item in report.recommendations]])
    mcp_security = facts.get("mcp_security", {})
    if isinstance(mcp_security, dict):
        counts = mcp_security.get("counts", {})
        findings = mcp_security.get("findings", [])
        if isinstance(counts, dict) and isinstance(findings, list):
            lines.extend(
                [
                    "",
                    "MCP configuration audit",
                    f"- high={counts.get('high', 0)}, "
                    f"medium={counts.get('medium', 0)}, "
                    f"low={counts.get('low', 0)}",
                ]
            )
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                server = (
                    f" ({finding['server']})"
                    if isinstance(finding.get("server"), str)
                    else ""
                )
                lines.append(
                    f"- [{finding.get('severity', 'review')}] "
                    f"{finding.get('code', 'mcp.review')}{server}: "
                    f"{finding.get('message', 'Review the MCP configuration.')}"
                )
    if report.diagnostics:
        lines.extend(
            [
                "",
                "Scan diagnostics",
                *[
                    f"- {item.get('path', 'project')}: {item.get('message', 'unavailable')}"
                    for item in report.diagnostics
                ],
            ]
        )
    return "\n".join(lines) + "\n"


def format_context_footprint(footprint: Mapping[str, Any]) -> str:
    return core.render_context_footprint(footprint)


def format_continuity_health(health: Mapping[str, Any]) -> str:
    continuity = health.get("continuity", {})
    continuity = continuity if isinstance(continuity, Mapping) else {}
    services = continuity.get("services", {})
    services = services if isinstance(services, Mapping) else {}
    lines = [
        f"Continuity: {str(continuity.get('status', 'unknown')).upper()}",
        str(continuity.get("summary", "No continuity summary is available.")),
        "",
        "Services",
        "--------",
    ]
    labels = {
        "mempalace": "MemPalace",
        "codebase_memory": "codebase-memory",
    }
    for name, label in labels.items():
        service = services.get(name, {})
        service = service if isinstance(service, Mapping) else {}
        lines.append(
            f"- {label}: policy={service.get('policy', 'unknown')}; "
            f"state={service.get('state', 'unknown')}; "
            f"identity={service.get('configured_identity', 'unknown')}"
        )
    effects = continuity.get("effects", [])
    if isinstance(effects, list) and effects:
        lines.extend(["", "Effect", "------", *[f"- {item}" for item in effects]])
    technical = {
        key: health[key]
        for key in ("mempalace", "codebase_memory")
        if key in health
    }
    lines.extend(
        [
            "",
            "Technical details",
            "-----------------",
            json.dumps(technical, indent=2, sort_keys=True),
        ]
    )
    return "\n".join(lines) + "\n"


def format_report(report: core.AnalysisReport, *, include_content: bool = True) -> str:
    lines = [format_project_overview(report).rstrip(), "", "Actions", "-------"]
    for action in report.actions:
        lines.append(f"[{action.status}] {action.path} - {action.reason}")
        if include_content and action.status in {"conflicting_proposal", "safe_merge"}:
            lines.extend(
                [
                    f"  Intended content for {action.path}:",
                    "  " + (action.intended_content or "<unavailable>").replace("\n", "\n  "),
                ]
            )
            if action.diff:
                lines.extend(["  Diff:", "  " + action.diff.replace("\n", "\n  ")])
    if report.warnings:
        lines.extend(["", "Warnings", "--------", *report.warnings])
    if report.errors:
        lines.extend(["", "Errors", "------", *report.errors])
    return "\n".join(lines) + "\n"


def apply_blockers(report: core.AnalysisReport) -> list[str]:
    blockers = [f"error: {message}" for message in report.errors]
    blockers.extend(
        f"unsafe path {action.path}: {action.reason}"
        for action in report.actions
        if action.status == "unsafe"
    )
    return blockers


def format_restore_instructions(plan: dict[str, Any]) -> str:
    return core.render_restore_instructions(plan)


class WorkflowConfiguratorApp:
    """Standard Qt settings window over the display-independent controller."""

    PAGE_NAMES = (
        "Project",
        "Workflow",
        "Memory & Code",
        "Tools & Profiles",
        "Review & Apply",
        "Updates & Plugins",
        "Recovery",
        "Guide",
    )
    ACTION_LABELS = {
        "missing": "Will add",
        "safe_merge": "Safe merge",
        "conflicting_proposal": "Needs review",
        "identical": "Already configured",
        "unsafe": "Blocked",
    }

    def __init__(
        self,
        controller: ConfiguratorController,
        root: Any = None,
        *,
        auto_check_updates: bool = True,
        upstream_service: core.UpstreamUpdateService | None = None,
    ) -> None:
        try:
            from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets
        except ImportError as error:
            raise ImportError(
                "PySide6 is required for the desktop UI. Install "
                "workflow_configurator/requirements-gui.txt in the selected environment."
            ) from error

        self.QtCore, self.QtGui, self.QtNetwork, self.QtWidgets = (
            QtCore,
            QtGui,
            QtNetwork,
            QtWidgets,
        )
        self.application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.controller = controller
        self.window = root or QtWidgets.QMainWindow()
        self.window.setWindowTitle("Workflow Configurator")
        self.window.resize(1120, 760)
        self.window.setMinimumSize(900, 640)
        self._center_window()

        font = self.application.font()
        if font.pointSize() < 10:
            font.setPointSize(10)
            self.application.setFont(font)
        self.body_font = self.application.font()
        self.mono_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._syncing = False
        self._busy = False
        self._preview_signature: str | None = None
        self._preview_report: core.AnalysisReport | None = None
        self._actions: list[core.FileAction] = []
        self._reviewed_proposals: set[str] = set()
        self._plugin_preview: core.PluginExportPlan | None = None
        self.upstream_service = upstream_service or core.UpstreamUpdateService()
        self._upstream_error = self.upstream_service.error
        self._update_payloads: dict[str, bytes] = {}
        self._update_replies: dict[Any, str] = {}
        self._update_errors: list[str] = []
        self._review_items_by_key: dict[str, core.UpstreamReviewItem] = {}
        self._asset_review: core.UpstreamAssetReview | None = None
        self._asset_item: core.UpstreamReviewItem | None = None
        self._asset_payloads: dict[str, bytes] = {}
        self._asset_replies: dict[Any, str] = {}
        self._asset_errors: list[str] = []
        self.profile_checks: dict[str, Any] = {}
        self.mcp_checks: dict[str, Any] = {}
        self.integration_checks: dict[str, Any] = {}
        self.safety_checks: dict[str, Any] = {}
        self.command_edits: dict[str, Any] = {}
        self.policy_overrides = {
            name: dict(value)
            for name, value in controller.config.policy_overrides.items()
        }
        self.network_manager = QtNetwork.QNetworkAccessManager(self.window)
        self._build()
        self._connect_form_signals()
        self._refresh_policy()
        self._refresh_recommendations()
        self._refresh_upstream_view()
        if auto_check_updates:
            self.QtCore.QTimer.singleShot(250, self._auto_check_upstream)

    def _center_window(self) -> None:
        screen = self.QtGui.QGuiApplication.screenAt(self.QtGui.QCursor.pos())
        screen = screen or self.QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.window.resize(
            min(1120, max(800, available.width() - 80)),
            min(760, max(600, available.height() - 80)),
        )
        frame = self.window.frameGeometry()
        frame.moveCenter(available.center())
        self.window.move(frame.topLeft())

    def _build(self) -> None:
        QW = self.QtWidgets
        central = QW.QWidget()
        outer = QW.QVBoxLayout(central)
        outer.setContentsMargins(18, 16, 18, 10)
        outer.setSpacing(12)
        self.window.setCentralWidget(central)

        header = QW.QHBoxLayout()
        heading = QW.QVBoxLayout()
        title = QW.QLabel("Workflow Configurator")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 6)
        title_font.setBold(True)
        title.setFont(title_font)
        heading.addWidget(title)
        heading.addWidget(
            QW.QLabel("Configure new or existing projects safely - preview first, apply only reviewed changes.")
        )
        header.addLayout(heading)
        header.addStretch()
        self.close_button = QW.QPushButton("Close")
        self.close_button.clicked.connect(self.window.close)
        header.addWidget(self.close_button)
        outer.addLayout(header)

        content = QW.QSplitter()
        self.navigation = QW.QListWidget()
        self.navigation.addItems(self.PAGE_NAMES)
        self.navigation.setFixedWidth(180)
        self.navigation.setSpacing(3)
        self.pages = QW.QStackedWidget()
        content.addWidget(self.navigation)
        content.addWidget(self.pages)
        content.setStretchFactor(1, 1)
        outer.addWidget(content, 1)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)

        self._build_project_page()
        self._build_workflow_page()
        self._build_memory_page()
        self._build_tools_page()
        self._build_review_page()
        self._build_updates_page()
        self._build_recovery_page()
        self._build_guide_page()
        self.navigation.setCurrentRow(0)

        self.progress = QW.QProgressBar()
        self.progress.setFixedWidth(120)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.hide()
        self.window.statusBar().addPermanentWidget(self.progress)
        self.window.statusBar().showMessage("Ready. Analyze and Preview are read-only.")
        self._build_menu()

    def _page(self, title: str, subtitle: str) -> tuple[Any, Any]:
        QW = self.QtWidgets
        page = QW.QWidget()
        layout = QW.QVBoxLayout(page)
        layout.setContentsMargins(14, 8, 8, 8)
        heading = QW.QLabel(title)
        font = heading.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)
        detail = QW.QLabel(subtitle)
        detail.setWordWrap(True)
        layout.addWidget(detail)
        self.pages.addWidget(page)
        return page, layout

    def _build_menu(self) -> None:
        menu = self.window.menuBar()
        file_menu = menu.addMenu("&File")
        actions = (
            ("Choose project...", self._choose_target),
            ("Import configuration...", self._import_config),
            ("Export configuration...", self._export_config),
        )
        for text, callback in actions:
            file_menu.addAction(text, callback)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("E&xit", self.window.close)
        exit_action.setShortcut("Ctrl+Q")
        help_menu = menu.addMenu("&Help")
        help_menu.addAction("User Guide", self._show_help)
        help_menu.addAction("About Workflow Configurator", self._show_about)

    def _build_project_page(self) -> None:
        QW = self.QtWidgets
        page, layout = self._page(
            "Project",
            "Choose a target and inspect its existing conventions. Analysis is read-only.",
        )
        form = QW.QFormLayout()
        form.setFieldGrowthPolicy(QW.QFormLayout.AllNonFixedFieldsGrow)
        self.target_edit = QW.QLineEdit(str(self.controller.target))
        target_row = QW.QWidget()
        target_layout = QW.QHBoxLayout(target_row)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.addWidget(self.target_edit, 1)
        browse = QW.QPushButton("Browse...")
        browse.clicked.connect(self._choose_target)
        target_layout.addWidget(browse)
        open_button = QW.QPushButton("Open folder")
        open_button.clicked.connect(self._open_target)
        target_layout.addWidget(open_button)
        form.addRow("Target folder", target_row)
        self.target_hint = QW.QLabel(
            "Confirm this is the repository to configure. The desktop shortcut "
            "initially selects the Configurator itself."
        )
        self.target_hint.setWordWrap(True)
        form.addRow("", self.target_hint)
        self.project_name_edit = QW.QLineEdit(self.controller.config.project_name)
        self.summary_edit = QW.QLineEdit(self.controller.config.summary)
        form.addRow("Project name", self.project_name_edit)
        form.addRow("Summary", self.summary_edit)
        self.task_details_edit = QW.QPlainTextEdit(self.controller.config.task_details)
        self.task_details_edit.setMaximumHeight(100)
        self.task_details_edit.setToolTip(
            "Optional initial task. Apply creates docs/CURRENT_TASK.md only if missing."
        )
        form.addRow("Current task (optional)", self.task_details_edit)

        workflow_row = QW.QWidget()
        workflow_layout = QW.QHBoxLayout(workflow_row)
        workflow_layout.setContentsMargins(0, 0, 0, 0)
        self.new_radio = QW.QRadioButton("New project")
        self.existing_radio = QW.QRadioButton("Existing project")
        (self.existing_radio if self.controller.config.workflow == "existing" else self.new_radio).setChecked(True)
        workflow_layout.addWidget(self.new_radio)
        workflow_layout.addWidget(self.existing_radio)
        workflow_layout.addStretch()
        form.addRow("Project type", workflow_row)
        layout.addLayout(form)

        self.project_text = QW.QPlainTextEdit()
        self.project_text.setReadOnly(True)
        self.project_text.setPlainText("Select Analyze project. The scan is read-only.")
        layout.addWidget(self.project_text, 1)

        buttons = QW.QHBoxLayout()
        analyze = QW.QPushButton("Analyze project")
        analyze.clicked.connect(self._analyze)
        buttons.addWidget(analyze)
        import_button = QW.QPushButton("Import configuration...")
        import_button.clicked.connect(self._import_config)
        buttons.addWidget(import_button)
        export_button = QW.QPushButton("Export configuration...")
        export_button.clicked.connect(self._export_config)
        buttons.addWidget(export_button)
        buttons.addStretch()
        launcher = QW.QPushButton("Install app launcher")
        launcher.clicked.connect(self._install_launcher)
        buttons.addWidget(launcher)
        layout.addLayout(buttons)

    def _combo(self, values: Iterable[str], selected: str) -> Any:
        combo = self.QtWidgets.QComboBox()
        combo.addItems(list(values))
        combo.setCurrentText(selected)
        return combo

    def _build_workflow_page(self) -> None:
        QW = self.QtWidgets
        page, layout = self._page(
            "Workflow",
            "Choose the amount of process the project actually needs. The effective policy updates live.",
        )
        splitter = QW.QSplitter()
        settings = QW.QGroupBox("Adaptive settings")
        form = QW.QFormLayout(settings)
        self.complexity_combo = self._combo(core.VALID_COMPLEXITIES, self.controller.config.complexity)
        self.size_combo = self._combo(core.VALID_SIZES, self.controller.config.project_size)
        self.size_combo.setToolTip(
            "Project scope and bounded inspection budget: "
            "small 25k, medium 100k, large 250k filesystem entries."
        )
        self.testing_combo = self._combo(core.VALID_TESTING_LEVELS, self.controller.config.testing_level)
        self.rigor_combo = self._combo(core.VALID_RIGOR_PRESETS, self.controller.config.rigor_preset)
        self.execution_mode_combo = self._combo(
            core.VALID_EXECUTION_MODES, self.controller.config.execution_mode
        )
        self.execution_mode_combo.setToolTip(
            "Velocity keeps bounded memory and graph lookups; checks and review "
            "are manual unless overridden. Hooks run only when selected."
        )
        self.execution_mode_detail = QW.QLabel()
        self.execution_mode_detail.setWordWrap(True)
        self.execution_mode_combo.currentTextChanged.connect(
            self._refresh_execution_mode_detail
        )
        form.addRow("Execution mode", self.execution_mode_combo)
        form.addRow("", self.execution_mode_detail)
        self._refresh_execution_mode_detail(self.execution_mode_combo.currentText())
        form.addRow("Complexity", self.complexity_combo)
        form.addRow("Project size", self.size_combo)
        form.addRow("Testing", self.testing_combo)
        form.addRow("Engineering rigor", self.rigor_combo)
        override_row = QW.QWidget()
        override_layout = QW.QHBoxLayout(override_row)
        override_layout.setContentsMargins(0, 0, 0, 0)
        self.override_summary_label = QW.QLabel()
        self.override_summary_label.setWordWrap(True)
        override_layout.addWidget(self.override_summary_label, 1)
        self.override_button = QW.QPushButton("Advanced overrides...")
        self.override_button.clicked.connect(self._edit_overrides)
        override_layout.addWidget(self.override_button)
        form.addRow("Expert policy", override_row)
        self._refresh_override_summary()
        splitter.addWidget(settings)

        policy = QW.QGroupBox("Resolved engineering policy")
        policy_layout = QW.QVBoxLayout(policy)
        self.policy_text = QW.QPlainTextEdit()
        self.policy_text.setReadOnly(True)
        policy_layout.addWidget(self.policy_text)
        splitter.addWidget(policy)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def _refresh_execution_mode_detail(self, mode: str) -> None:
        self.execution_mode_detail.setText(
            "Velocity: bounded project memory and code graph; plans, checks, doctor, "
            "and review on request. Hooks run only if selected; overrides can add requirements."
            if mode == "velocity"
            else "Balanced: planning, checks, and review follow project scope and rigor. "
            "See the resolved engineering policy."
        )

    def _refresh_override_summary(self) -> None:
        if not self.policy_overrides:
            self.override_summary_label.setText(
                "Automatic policy. Hard safety protections always remain active."
            )
            return
        names = ", ".join(
            name.replace("_", " ") for name in sorted(self.policy_overrides)
        )
        self.override_summary_label.setText(
            f"{len(self.policy_overrides)} active: {names}"
        )

    def _edit_overrides(self) -> None:
        QW = self.QtWidgets
        try:
            base = self._form_config(without_policy_overrides=True)
            derived = core.derive_policy(base)
        except core.ConfigError as error:
            self._show_error(error)
            return

        dialog = QW.QDialog(self.window)
        dialog.setWindowTitle("Advanced policy overrides")
        dialog.resize(900, 480)
        layout = QW.QVBoxLayout(dialog)
        note = QW.QLabel(
            "Only workflow-process controls are shown. Path, secret, sandbox, "
            "destructive-operation, preview, collision, and transactional safety "
            "cannot be overridden. A reason is required for every weaker value. "
            "Hover a dimension or option for its behavior; the complete reference "
            "is in Guide > Advanced override reference."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        table = QW.QTableWidget(len(core.POLICY_DIMENSION_VALUES), 5)
        table.setHorizontalHeaderLabels(
            ("Dimension", "Derived", "Override", "Effect", "Reason")
        )
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        controls: dict[str, tuple[Any, Any, Any, str]] = {}
        catalog = core.policy_override_catalog()

        def refresh_effect(
            dimension: str,
            combo: Any,
            effect: Any,
            derived_value: str,
        ) -> None:
            value = combo.currentText()
            effect.setText(
                "automatic"
                if value == "auto"
                else core.policy_override_strength(
                    dimension, derived_value, value
                )
            )
            option_descriptions = catalog[dimension]["options"]
            if isinstance(option_descriptions, dict):
                combo.setToolTip(
                    str(
                        option_descriptions.get(
                            value,
                            "Use the automatically derived value.",
                        )
                    )
                )

        for row, (dimension, values) in enumerate(
            core.POLICY_DIMENSION_VALUES.items()
        ):
            derived_value = str(getattr(derived, dimension))
            table.setItem(
                row,
                0,
                QW.QTableWidgetItem(dimension.replace("_", " ").title()),
            )
            dimension_item = table.item(row, 0)
            dimension_item.setToolTip(str(catalog[dimension]["summary"]))
            table.setItem(row, 1, QW.QTableWidgetItem(derived_value))
            combo = QW.QComboBox()
            combo.addItems(["auto", *values])
            combo.setItemData(
                0,
                "Use the automatically derived value and store no override.",
                self.QtCore.Qt.ItemDataRole.ToolTipRole,
            )
            option_descriptions = catalog[dimension]["options"]
            if isinstance(option_descriptions, dict):
                for index, value in enumerate(values, start=1):
                    combo.setItemData(
                        index,
                        str(option_descriptions[value]),
                        self.QtCore.Qt.ItemDataRole.ToolTipRole,
                    )
            decision = self.policy_overrides.get(dimension, {})
            selected = decision.get("value", "auto")
            combo.setCurrentText(selected if selected in values else "auto")
            table.setCellWidget(row, 2, combo)
            effect = QW.QLabel()
            table.setCellWidget(row, 3, effect)
            reason = QW.QLineEdit(str(decision.get("reason", "")))
            reason.setPlaceholderText("Required when weaker")
            table.setCellWidget(row, 4, reason)
            combo.currentTextChanged.connect(
                lambda _value, d=dimension, c=combo, e=effect, v=derived_value: refresh_effect(
                    d, c, e, v
                )
            )
            refresh_effect(dimension, combo, effect, derived_value)
            controls[dimension] = (combo, effect, reason, derived_value)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QW.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QW.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QW.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QW.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QW.QHeaderView.Stretch)
        layout.addWidget(table, 1)

        buttons = QW.QDialogButtonBox(
            QW.QDialogButtonBox.Save
            | QW.QDialogButtonBox.Cancel
            | QW.QDialogButtonBox.Reset
        )
        buttons.rejected.connect(dialog.reject)

        def reset() -> None:
            for combo, _effect, reason, _derived_value in controls.values():
                combo.setCurrentText("auto")
                reason.clear()

        def save() -> None:
            overrides: dict[str, dict[str, str]] = {}
            for dimension, (combo, _effect, reason, derived_value) in controls.items():
                value = combo.currentText()
                if value == "auto":
                    continue
                reason_text = reason.text().strip()
                if (
                    core.policy_override_strength(
                        dimension, derived_value, value
                    )
                    == "weaker"
                    and not reason_text
                ):
                    QW.QMessageBox.warning(
                        dialog,
                        "Reason required",
                        f"Explain why {dimension.replace('_', ' ')} may be weakened "
                        f"from {derived_value} to {value}.",
                    )
                    reason.setFocus()
                    return
                overrides[dimension] = {
                    "value": value,
                    "reason": reason_text,
                }
            candidate_raw = base.to_dict()
            candidate_raw["policy_overrides"] = overrides
            try:
                core.derive_policy(core.WorkflowConfig.from_dict(candidate_raw))
            except core.ConfigError as error:
                QW.QMessageBox.warning(dialog, "Invalid override", str(error))
                return
            self.policy_overrides = overrides
            self._refresh_override_summary()
            dialog.accept()
            self._form_changed()

        buttons.button(QW.QDialogButtonBox.Reset).clicked.connect(reset)
        buttons.button(QW.QDialogButtonBox.Save).clicked.connect(save)
        layout.addWidget(buttons)
        dialog.exec()

    def _check_group(self, title: str, values: Iterable[str], selected: Iterable[str]) -> tuple[Any, dict[str, Any]]:
        QW = self.QtWidgets
        group = QW.QGroupBox(title)
        box = QW.QVBoxLayout(group)
        checks = {}
        enabled = set(selected)
        for value in values:
            check = QW.QCheckBox(value)
            check.setChecked(value in enabled)
            box.addWidget(check)
            checks[value] = check
        box.addStretch()
        return group, checks

    def _build_memory_page(self) -> None:
        QW = self.QtWidgets
        _page, layout = self._page(
            "Memory & Code",
            "Use one explicit project identity for each persistent system. "
            "Health checks are read-only and never index, mine, migrate, or stop services.",
        )
        form = QW.QFormLayout()
        self.memory_wing_edit = QW.QLineEdit(self.controller.config.memory_wing)
        self.memory_wing_edit.setToolTip(
            "Canonical lowercase MemPalace wing used by all project reads and writes."
        )
        self.codebase_project_edit = QW.QLineEdit(
            self.controller.config.codebase_project_id
        )
        self.codebase_project_edit.setToolTip(
            "Exact persistent codebase-memory project identifier."
        )
        form.addRow("MemPalace project wing", self.memory_wing_edit)
        form.addRow("codebase-memory project", self.codebase_project_edit)
        layout.addLayout(form)
        self.memory_health_text = QW.QPlainTextEdit()
        self.memory_health_text.setReadOnly(True)
        self.memory_health_text.setFont(self.mono_font)
        self.memory_health_text.setPlainText(
            "Select Check memory and code health, or Analyze project."
        )
        layout.addWidget(self.memory_health_text, 1)
        buttons = QW.QHBoxLayout()
        health = QW.QPushButton("Check memory and code health")
        health.clicked.connect(self._check_external_health)
        buttons.addWidget(health)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _build_tools_page(self) -> None:
        QW = self.QtWidgets
        page, layout = self._page(
            "Tools & Profiles",
            "Project MCP entries are generated locally. Optional integrations add guidance only and are never installed automatically.",
        )
        scroll = QW.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        body = QW.QWidget()
        body.setMinimumWidth(0)
        body_layout = QW.QVBoxLayout(body)
        top = QW.QHBoxLayout()
        profiles, self.profile_checks = self._check_group(
            "Stack profiles",
            core.PROFILE_FILES,
            self.controller.config.stack_profiles,
        )
        mcp, self.mcp_checks = self._check_group(
            "Project MCP services",
            core.MCP_NAMES,
            self.controller.config.mcp_servers,
        )
        top.addWidget(profiles)
        top.addWidget(mcp)
        body_layout.addLayout(top)
        technology_form = QW.QFormLayout()
        self.technology_stack_edit = QW.QLineEdit(self.controller.config.technology_stack)
        self.technology_stack_edit.setPlaceholderText("Rust, React, Python")
        technology_form.addRow("Other technologies", self.technology_stack_edit)
        body_layout.addLayout(technology_form)

        session = QW.QGroupBox("Session guidance")
        session_form = QW.QFormLayout(session)
        self.session_profile_combo = self._combo(
            core.VALID_SESSION_PROFILES,
            self.controller.config.session_profile,
        )
        self.session_profile_detail = QW.QLabel()
        self.session_profile_detail.setWordWrap(True)
        session_form.addRow("Task profile", self.session_profile_combo)
        session_form.addRow("", self.session_profile_detail)
        body_layout.addWidget(session)

        integrations = QW.QGroupBox("Optional capabilities")
        integration_layout = QW.QVBoxLayout(integrations)
        self.recommendation_label = QW.QLabel()
        self.recommendation_label.setWordWrap(True)
        integration_layout.addWidget(self.recommendation_label)
        self.integration_search = QW.QLineEdit()
        self.integration_search.setPlaceholderText("Filter optional capabilities...")
        integration_layout.addWidget(self.integration_search)
        self.integration_splitter = QW.QSplitter()
        self.integration_splitter.setChildrenCollapsible(False)
        self.integration_tree = QW.QTreeWidget()
        self.integration_tree.setHeaderLabels(("Capability", "Type"))
        self.integration_tree.setRootIsDecorated(False)
        self.integration_tree.setAlternatingRowColors(True)
        self.integration_tree.setMinimumWidth(280)
        self.integration_tree.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        integration_header = self.integration_tree.header()
        integration_header.setSectionResizeMode(0, QW.QHeaderView.ResizeMode.Stretch)
        integration_header.setSectionResizeMode(
            1,
            QW.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.integration_splitter.addWidget(self.integration_tree)
        self.integration_detail = QW.QPlainTextEdit()
        self.integration_detail.setReadOnly(True)
        self.integration_detail.setMinimumWidth(280)
        self.integration_detail.setLineWrapMode(QW.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.integration_detail.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.integration_splitter.addWidget(self.integration_detail)
        self.integration_splitter.setStretchFactor(0, 1)
        self.integration_splitter.setStretchFactor(1, 1)
        self.integration_splitter.setSizes([400, 400])
        selected = set(self.controller.config.optional_integrations)
        for name, metadata in core.OPTIONAL_INTEGRATIONS.items():
            item = QW.QTreeWidgetItem((metadata["label"], metadata["kind"]))
            item.setData(0, self.QtCore.Qt.UserRole, name)
            item.setFlags(item.flags() | self.QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(
                0,
                self.QtCore.Qt.Checked
                if name in selected
                else self.QtCore.Qt.Unchecked,
            )
            item.setToolTip(0, metadata["guardrail"])
            self.integration_tree.addTopLevelItem(item)
            self.integration_checks[name] = item
        self.integration_tree.currentItemChanged.connect(
            lambda current, _previous: self._show_integration_detail(current)
        )
        self.integration_tree.itemChanged.connect(
            lambda *_args: self._form_changed()
        )
        self.integration_search.textChanged.connect(
            self._filter_integrations
        )
        self.session_profile_combo.currentTextChanged.connect(
            self._refresh_session_profile
        )
        self._refresh_session_profile()
        if self.integration_tree.topLevelItemCount():
            self.integration_tree.setCurrentItem(
                self.integration_tree.topLevelItem(0)
            )
        integration_layout.addWidget(self.integration_splitter, 1)
        body_layout.addWidget(integrations)

        bottom = QW.QHBoxLayout()
        commands = QW.QGroupBox("Project commands")
        command_form = QW.QFormLayout(commands)
        for name in ("test", "lint", "typecheck", "run"):
            edit = QW.QLineEdit(self.controller.config.commands[name])
            command_form.addRow(name.capitalize(), edit)
            self.command_edits[name] = edit
        bottom.addWidget(commands)

        safety_values = {
            "with_security_hooks": "Security hooks",
            "with_context_settings": "Context exclusions",
            "manage_artifact_gitignore": "Artifact ignore rule",
            "sandbox_local": "Sandbox local MCP",
        }
        safety, self.safety_checks = self._check_group(
            "Safety and workspace",
            safety_values,
            [
                name
                for name in safety_values
                if getattr(self.controller.config, name)
            ],
        )
        for name, check in self.safety_checks.items():
            check.setText(safety_values[name])
        bottom.addWidget(safety)
        body_layout.addLayout(bottom)
        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

    def _build_review_page(self) -> None:
        QW = self.QtWidgets
        _page, layout = self._page(
            "Review & Apply",
            "Preview lists safe changes and review-only proposals. Proposals are "
            "never overwritten automatically.",
        )
        self.preview_label = QW.QLabel("Preview required before Apply.")
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)
        self.review_progress_label = QW.QLabel(
            "Select Preview changes, then select a row to inspect its content or diff."
        )
        self.review_progress_label.setWordWrap(True)
        layout.addWidget(self.review_progress_label)

        self.review_splitter = QW.QSplitter()
        self.review_splitter.setChildrenCollapsible(False)
        self.action_tree = QW.QTreeWidget()
        self.action_tree.setHeaderLabels(("Path", "Status"))
        self.action_tree.setAlternatingRowColors(True)
        self.action_tree.setRootIsDecorated(False)
        self.action_tree.setMinimumWidth(330)
        self.action_tree.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        action_header = self.action_tree.header()
        action_header.setSectionResizeMode(0, QW.QHeaderView.ResizeMode.Stretch)
        action_header.setSectionResizeMode(
            1,
            QW.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.action_tree.currentItemChanged.connect(self._selected_action_changed)
        self.review_splitter.addWidget(self.action_tree)

        details = QW.QTabWidget()
        details.setMinimumWidth(360)
        self.review_text = QW.QPlainTextEdit()
        self.review_text.setReadOnly(True)
        self.review_text.setFont(self.mono_font)
        self.review_text.setLineWrapMode(QW.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.review_text.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.review_diff_highlighter = install_diff_highlighter(
            self.review_text,
            self.QtGui,
        )
        self.overview_text = QW.QPlainTextEdit()
        self.overview_text.setReadOnly(True)
        self.overview_text.setLineWrapMode(QW.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.overview_text.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.full_report_text = QW.QPlainTextEdit()
        self.full_report_text.setReadOnly(True)
        self.full_report_text.setFont(self.mono_font)
        self.full_report_text.setLineWrapMode(
            QW.QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.full_report_text.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        details.addTab(self.review_text, "Selected action")
        details.addTab(self.overview_text, "Project summary")
        details.addTab(self.full_report_text, "Full report")
        self.review_splitter.addWidget(details)
        self.review_splitter.setStretchFactor(0, 1)
        self.review_splitter.setStretchFactor(1, 1)
        self.review_splitter.setSizes([430, 500])
        layout.addWidget(self.review_splitter, 1)

        review_buttons = QW.QHBoxLayout()
        self.mark_proposal_reviewed_button = QW.QPushButton(
            "Acknowledge proposal (keep existing)"
        )
        self.mark_proposal_reviewed_button.setEnabled(False)
        self.mark_proposal_reviewed_button.clicked.connect(
            self._mark_selected_proposal_reviewed
        )
        review_buttons.addWidget(self.mark_proposal_reviewed_button)
        self.copy_action_button = QW.QPushButton("Copy selected diff")
        self.copy_action_button.setEnabled(False)
        self.copy_action_button.clicked.connect(self._copy_selected_action)
        review_buttons.addWidget(self.copy_action_button)
        self.open_action_button = QW.QPushButton("Open existing file")
        self.open_action_button.setEnabled(False)
        self.open_action_button.clicked.connect(self._open_selected_action)
        review_buttons.addWidget(self.open_action_button)
        review_buttons.addStretch()
        layout.addLayout(review_buttons)

        buttons = QW.QHBoxLayout()
        preview = QW.QPushButton("Preview changes")
        preview.clicked.connect(self._preview)
        buttons.addWidget(preview)
        export = QW.QPushButton("Export report...")
        export.clicked.connect(self._export_report)
        buttons.addWidget(export)
        buttons.addStretch()
        self.apply_button = QW.QPushButton("Apply safe changes")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)

    def _build_updates_page(self) -> None:
        QW = self.QtWidgets
        _page, layout = self._page(
            "Updates & Plugins",
            "Automatic checks fetch public GitHub metadata only. Upstream content "
            "never changes trusted behavior until it is reviewed and implemented locally.",
        )
        tabs = QW.QTabWidget()
        layout.addWidget(tabs, 1)

        upstream = QW.QWidget()
        upstream_layout = QW.QVBoxLayout(upstream)
        self.update_status_label = QW.QLabel()
        self.update_status_label.setWordWrap(True)
        upstream_layout.addWidget(self.update_status_label)
        self.upstream_text = QW.QPlainTextEdit()
        self.upstream_text.setReadOnly(True)
        self.upstream_text.setFont(self.mono_font)
        self.upstream_text.setLineWrapMode(
            QW.QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.upstream_text.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.upstream_text.setMaximumHeight(150)
        upstream_layout.addWidget(self.upstream_text)

        review_splitter = QW.QSplitter(self.QtCore.Qt.Orientation.Vertical)
        self.upstream_queue = QW.QTreeWidget()
        self.upstream_queue.setHeaderLabels(["Change", "Path", "Decision"])
        self.upstream_queue.setRootIsDecorated(False)
        self.upstream_queue.setAlternatingRowColors(True)
        self.upstream_queue.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        upstream_header = self.upstream_queue.header()
        upstream_header.setSectionResizeMode(
            0,
            QW.QHeaderView.ResizeMode.ResizeToContents,
        )
        upstream_header.setSectionResizeMode(1, QW.QHeaderView.ResizeMode.Stretch)
        upstream_header.setSectionResizeMode(
            2,
            QW.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.upstream_queue.itemSelectionChanged.connect(
            self._upstream_selection_changed
        )
        review_splitter.addWidget(self.upstream_queue)
        self.upstream_detail = QW.QPlainTextEdit()
        self.upstream_detail.setReadOnly(True)
        self.upstream_detail.setFont(self.mono_font)
        self.upstream_detail.setLineWrapMode(
            QW.QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.upstream_detail.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.upstream_diff_highlighter = install_diff_highlighter(
            self.upstream_detail,
            self.QtGui,
        )
        self.upstream_detail.setPlainText(
            "Select an item, then inspect its size-capped read-only diff. "
            "Treat all displayed upstream content as untrusted."
        )
        review_splitter.addWidget(self.upstream_detail)
        review_splitter.setStretchFactor(0, 1)
        review_splitter.setStretchFactor(1, 2)
        upstream_layout.addWidget(review_splitter, 1)

        update_buttons = QW.QHBoxLayout()
        self.update_check_button = QW.QPushButton("Check upstream now")
        self.update_check_button.clicked.connect(
            lambda: self._check_upstream_now()
        )
        update_buttons.addWidget(self.update_check_button)
        self.export_review_button = QW.QPushButton("Export review brief...")
        self.export_review_button.setEnabled(False)
        self.export_review_button.clicked.connect(self._export_upstream_review)
        update_buttons.addWidget(self.export_review_button)
        self.inspect_review_button = QW.QPushButton("Inspect selected")
        self.inspect_review_button.setEnabled(False)
        self.inspect_review_button.clicked.connect(self._inspect_upstream_item)
        update_buttons.addWidget(self.inspect_review_button)
        update_buttons.addStretch()
        upstream_layout.addLayout(update_buttons)

        decision_row = QW.QHBoxLayout()
        self.review_disposition_combo = QW.QComboBox()
        for value in core.REVIEW_DISPOSITIONS:
            self.review_disposition_combo.addItem(
                value.replace("-", " ").title(),
                value,
            )
        decision_row.addWidget(self.review_disposition_combo)
        self.review_note_edit = QW.QLineEdit()
        self.review_note_edit.setPlaceholderText(
            "Required rationale for this disposition"
        )
        decision_row.addWidget(self.review_note_edit, 1)
        self.save_review_button = QW.QPushButton("Save decision")
        self.save_review_button.setEnabled(False)
        self.save_review_button.clicked.connect(self._save_upstream_decision)
        decision_row.addWidget(self.save_review_button)
        self.advance_baseline_button = QW.QPushButton("Advance reviewed baseline")
        self.advance_baseline_button.setEnabled(False)
        self.advance_baseline_button.clicked.connect(
            self._advance_upstream_baseline
        )
        decision_row.addWidget(self.advance_baseline_button)
        upstream_layout.addLayout(decision_row)
        tabs.addTab(upstream, "Upstream review")

        plugin = QW.QWidget()
        plugin_layout = QW.QVBoxLayout(plugin)
        plugin_intro = QW.QLabel(
            "Export five already-reviewed local specialists as a standalone "
            "plugin. Export never installs or overwrites anything."
        )
        plugin_intro.setWordWrap(True)
        plugin_layout.addWidget(plugin_intro)
        destination_row = QW.QHBoxLayout()
        self.plugin_destination_edit = QW.QLineEdit(
            str(Path.home() / "genai-workflow-core-plugin")
        )
        self.plugin_destination_edit.textChanged.connect(
            self._invalidate_plugin_preview
        )
        destination_row.addWidget(self.plugin_destination_edit, 1)
        choose = QW.QPushButton("Choose parent...")
        choose.clicked.connect(self._choose_plugin_parent)
        destination_row.addWidget(choose)
        plugin_layout.addLayout(destination_row)
        self.plugin_text = QW.QPlainTextEdit()
        self.plugin_text.setReadOnly(True)
        self.plugin_text.setFont(self.mono_font)
        self.plugin_text.setLineWrapMode(QW.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.plugin_text.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.plugin_text.setPlainText(
            "Preview the local export. It contains five reviewed agents and no "
            "hooks, MCP servers, project identity, task state, or updater."
        )
        plugin_layout.addWidget(self.plugin_text)
        plugin_buttons = QW.QHBoxLayout()
        preview = QW.QPushButton("Preview plugin export")
        preview.clicked.connect(self._preview_plugin_export)
        plugin_buttons.addWidget(preview)
        self.export_plugin_button = QW.QPushButton("Export reviewed plugin")
        self.export_plugin_button.setEnabled(False)
        self.export_plugin_button.clicked.connect(self._export_plugin)
        plugin_buttons.addWidget(self.export_plugin_button)
        plugin_buttons.addStretch()
        plugin_layout.addLayout(plugin_buttons)
        tabs.addTab(plugin, "Local plugin export")

    def _build_recovery_page(self) -> None:
        QW = self.QtWidgets
        page, layout = self._page(
            "Recovery",
            "Recovery is manual by design. The configurator never restores or deletes project files automatically.",
        )
        self.recovery_text = QW.QPlainTextEdit()
        self.recovery_text.setReadOnly(True)
        self.recovery_text.setPlainText("Select Show restore instructions after Apply.")
        layout.addWidget(self.recovery_text, 1)
        buttons = QW.QHBoxLayout()
        show = QW.QPushButton("Show restore instructions")
        show.clicked.connect(self._restore_instructions)
        buttons.addWidget(show)
        export = QW.QPushButton("Export restore plan...")
        export.clicked.connect(self._export_restore_plan)
        buttons.addWidget(export)
        buttons.addStretch()
        open_backups = QW.QPushButton("Open backups")
        open_backups.clicked.connect(self._open_backups)
        buttons.addWidget(open_backups)
        layout.addLayout(buttons)

    def _build_guide_page(self) -> None:
        QW = self.QtWidgets
        _page, layout = self._page(
            "Guide",
            "How to choose a proportional workflow and apply it safely.",
        )
        self.guide_view = QW.QTextBrowser()
        self.guide_view.setMarkdown(USER_GUIDE)
        self.guide_view.setOpenExternalLinks(True)
        layout.addWidget(self.guide_view, 1)

    def _connect_form_signals(self) -> None:
        self.target_edit.textChanged.connect(self._target_changed)
        self.project_name_edit.textEdited.connect(self._identity_changed)
        self.summary_edit.textEdited.connect(self._form_changed)
        self.task_details_edit.textChanged.connect(self._form_changed)
        self.technology_stack_edit.textChanged.connect(self._form_changed)
        self.memory_wing_edit.textEdited.connect(
            self._memory_wing_changed
        )
        self.codebase_project_edit.textEdited.connect(
            self._codebase_project_changed
        )
        self.new_radio.toggled.connect(self._form_changed)
        for combo in (
            self.complexity_combo,
            self.size_combo,
            self.testing_combo,
            self.rigor_combo,
            self.execution_mode_combo,
            self.session_profile_combo,
        ):
            combo.currentTextChanged.connect(self._form_changed)
        for widget in (
            *self.profile_checks.values(),
            *self.mcp_checks.values(),
            *self.safety_checks.values(),
        ):
            widget.toggled.connect(self._form_changed)
        for edit in self.command_edits.values():
            edit.textChanged.connect(self._form_changed)

    def _target_changed(self, value: str) -> None:
        if self._syncing:
            return
        self.controller.set_target(value)
        self._syncing = True
        self.project_name_edit.setText(self.controller.config.project_name)
        self.memory_wing_edit.setText(self.controller.config.memory_wing)
        self.codebase_project_edit.setText(
            self.controller.config.codebase_project_id
        )
        self._syncing = False
        self._invalidate_preview()

    def _identity_changed(self) -> None:
        if not self._syncing:
            self.controller.mark_identity_explicit()
            self._invalidate_preview()

    def _memory_wing_changed(self) -> None:
        if not self._syncing:
            self.controller.mark_memory_wing_explicit()
            self._form_changed()

    def _codebase_project_changed(self) -> None:
        if not self._syncing:
            self.controller.mark_codebase_project_explicit()
            self._form_changed()

    def _form_changed(self) -> None:
        if self._syncing:
            return
        self._invalidate_preview()
        self._refresh_override_summary()
        self._refresh_policy()
        self._refresh_recommendations()

    def _invalidate_preview(self) -> None:
        self._preview_signature = None
        self._preview_report = None
        self._reviewed_proposals.clear()
        self.preview_label.setText("Settings changed. Preview again before applying.")
        self.apply_button.setEnabled(False)
        self.apply_button.setToolTip("Preview the current settings before applying.")
        if hasattr(self, "review_progress_label"):
            self.review_progress_label.setText(
                "Preview again before reviewing the proposed actions."
            )
            self.mark_proposal_reviewed_button.setEnabled(False)
            self.copy_action_button.setEnabled(False)
            self.open_action_button.setEnabled(False)

    def _form_config(
        self, *, commit_target: bool = False, without_policy_overrides: bool = False
    ) -> core.WorkflowConfig:
        if commit_target:
            self.controller.set_target(self.target_edit.text())
        raw = self.controller.config.to_dict()
        raw.update(
            {
                "project_name": self.project_name_edit.text(),
                "summary": self.summary_edit.text(),
                "task_details": self.task_details_edit.toPlainText(),
                "workflow": "new" if self.new_radio.isChecked() else "existing",
                "complexity": self.complexity_combo.currentText(),
                "project_size": self.size_combo.currentText(),
                "testing_level": self.testing_combo.currentText(),
                "rigor_preset": self.rigor_combo.currentText(),
                "execution_mode": self.execution_mode_combo.currentText(),
                "memory_wing": self.memory_wing_edit.text(),
                "codebase_project_id": self.codebase_project_edit.text(),
                "session_profile": self.session_profile_combo.currentText(),
                "protocol_guard": None,
                "policy_overrides": (
                    {} if without_policy_overrides else {
                        name: dict(value) for name, value in self.policy_overrides.items()
                    }
                ),
                "stack_profiles": [
                    name for name, check in self.profile_checks.items() if check.isChecked()
                ],
                "technology_stack": self.technology_stack_edit.text(),
                "mcp_servers": [
                    name for name, check in self.mcp_checks.items() if check.isChecked()
                ],
                "optional_integrations": [
                    name
                    for name, item in self.integration_checks.items()
                    if item.checkState(0) == self.QtCore.Qt.Checked
                ],
                "commands": {
                    name: edit.text() for name, edit in self.command_edits.items()
                },
                **{
                    name: check.isChecked()
                    for name, check in self.safety_checks.items()
                },
            }
        )
        return core.WorkflowConfig.from_dict(raw)

    def _collect(self) -> core.WorkflowConfig:
        config = self._form_config(commit_target=True)
        self.controller.set_config(config)
        return config

    def _refresh_policy(self) -> None:
        try:
            policy = core.derive_policy(self._form_config()).to_dict()
            text = "\n\n".join(
                f"{key.replace('_', ' ').title()}\n{value}"
                for key, value in policy.items()
            )
        except (core.ConfigError, ValueError, KeyError) as error:
            text = f"Configuration error\n{error}"
        self.policy_text.setPlainText(text)

    def _show_integration_detail(self, item: Any) -> None:
        if item is None:
            self.integration_detail.clear()
            return
        name = item.data(0, self.QtCore.Qt.UserRole)
        metadata = core.OPTIONAL_INTEGRATIONS.get(name, {})
        self.integration_detail.setPlainText(
            "\n\n".join(
                (
                    metadata.get("label", str(name)),
                    f"Type\n{metadata.get('kind', 'Optional capability')}",
                    f"Purpose\n{metadata.get('summary', '')}",
                    f"Guardrail\n{metadata.get('guardrail', '')}",
                    "Delivery\n"
                    + (
                        "Bundled local template files are previewed before Apply."
                        if name in core.LOCAL_CAPABILITY_FILES
                        else "Guidance only; nothing is installed automatically."
                    ),
                    "Context cost\nQualitative only; enable for the task that needs it.",
                )
            )
        )

    def _filter_integrations(self, value: str) -> None:
        query = value.strip().lower()
        for name, item in self.integration_checks.items():
            metadata = core.OPTIONAL_INTEGRATIONS[name]
            searchable = " ".join(
                (
                    name,
                    metadata["label"],
                    metadata["kind"],
                    metadata["summary"],
                    metadata["guardrail"],
                )
            ).lower()
            item.setHidden(bool(query and query not in searchable))

    def _refresh_session_profile(self) -> None:
        profile = self.session_profile_combo.currentText()
        metadata = core.SESSION_PROFILES.get(profile, {})
        self.session_profile_detail.setText(
            metadata.get("summary", "Select a bounded task profile.")
            + "\nThis generates guidance; it does not change the running agent session."
        )

    def _refresh_recommendations(self) -> None:
        try:
            config = self._form_config()
            facts = self.controller.report.facts if self.controller.report else None
            recommendations = core.recommended_integrations(config, facts)
            labels = [core.OPTIONAL_INTEGRATIONS[name]["label"] for name in recommendations]
            text = (
                "Suggested for these settings: " + ", ".join(labels)
                if labels
                else "No additional integration is suggested for these settings."
            )
            self.recommendation_label.setText(
                text + "\nSelections add guidance only; nothing is installed automatically."
            )
        except core.ConfigError as error:
            self.recommendation_label.setText(f"Configuration error: {error}")

    def _sync_from_config(self) -> None:
        config = self.controller.config
        self._syncing = True
        self.project_name_edit.setText(config.project_name)
        self.summary_edit.setText(config.summary)
        self.task_details_edit.setPlainText(config.task_details)
        self.technology_stack_edit.setText(config.technology_stack)
        self.memory_wing_edit.setText(config.memory_wing)
        self.codebase_project_edit.setText(config.codebase_project_id)
        self.new_radio.setChecked(config.workflow == "new")
        self.existing_radio.setChecked(config.workflow == "existing")
        for combo, value in (
            (self.complexity_combo, config.complexity),
            (self.size_combo, config.project_size),
            (self.testing_combo, config.testing_level),
            (self.rigor_combo, config.rigor_preset),
            (self.execution_mode_combo, config.execution_mode),
            (self.session_profile_combo, config.session_profile),
        ):
            combo.setCurrentText(value)
        for name, check in self.profile_checks.items():
            check.setChecked(name in config.stack_profiles)
        for name, check in self.mcp_checks.items():
            check.setChecked(name in config.mcp_servers)
        for name, item in self.integration_checks.items():
            item.setCheckState(
                0,
                self.QtCore.Qt.Checked
                if name in config.optional_integrations
                else self.QtCore.Qt.Unchecked,
            )
        for name, check in self.safety_checks.items():
            check.setChecked(getattr(config, name))
        for name, edit in self.command_edits.items():
            edit.setText(config.commands[name])
        self.policy_overrides = {
            name: dict(value) for name, value in config.policy_overrides.items()
        }
        self._refresh_override_summary()
        self._syncing = False
        self._invalidate_preview()
        self._refresh_policy()
        self._refresh_recommendations()

    def _set_busy(self, busy: bool, label: str = "") -> None:
        self._busy = busy
        if busy:
            self.progress.show()
            self.progress.setRange(0, 0)
            self.window.statusBar().showMessage(f"{label}...")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.hide()
        self.application.processEvents()

    def _run(
        self,
        operation: Callable[[], Any],
        label: str,
        *,
        authorize_apply: bool = False,
    ) -> Any:
        if self._busy:
            return None
        self._set_busy(True, label)
        try:
            result = operation()
            if isinstance(result, core.AnalysisReport):
                self.controller.report = result
                self._show_report(result, authorize_apply=authorize_apply)
                self.window.statusBar().showMessage(
                    f"{label}: {len(result.actions)} actions, {len(result.proposals)} proposals."
                )
            elif isinstance(result, core.ApplyResult):
                self._show_report(result.report, authorize_apply=False)
                self._invalidate_preview()
                message = (
                    f"Apply: {len(result.added_paths)} added, {len(result.merged_paths)} safely merged."
                )
                if result.proposals:
                    message += f" {len(result.proposals)} proposal(s) still require manual merge."
                self.preview_label.setText(message)
                self.window.statusBar().showMessage(message)
                try:
                    self._show_recovery(self.controller.restore_instructions())
                except (core.RollbackError, core.SafetyError):
                    pass
            elif isinstance(result, dict) and result.get("status") == "manual_restore":
                self._show_recovery(result)
                self.window.statusBar().showMessage("Manual recovery guidance loaded.")
            else:
                self.window.statusBar().showMessage(f"{label} complete.")
            return result
        except (
            core.ConfigError,
            core.SafetyError,
            core.ApplyError,
            core.RollbackError,
            core.PluginExportError,
            core.UpstreamError,
        ) as error:
            self._show_error(error)
            return None
        finally:
            self._set_busy(False)

    def _show_report(
        self,
        report: core.AnalysisReport,
        *,
        authorize_apply: bool = False,
    ) -> None:
        self._reviewed_proposals.clear()
        if not authorize_apply:
            self._preview_signature = None
            self._preview_report = None
            self.apply_button.setEnabled(False)
        self.project_text.setPlainText(format_project_overview(report))
        self.overview_text.setPlainText(format_project_overview(report))
        self.full_report_text.setPlainText(format_report(report))
        health = report.facts.get("external_health")
        if isinstance(health, Mapping):
            self.memory_health_text.setPlainText(
                format_continuity_health(health)
            )
        self.action_tree.clear()
        self._actions = list(report.actions)
        for index, action in enumerate(self._actions):
            item = self.QtWidgets.QTreeWidgetItem(
                (
                    action.path,
                    self._action_review_status(action),
                )
            )
            item.setData(0, self.QtCore.Qt.UserRole, index)
            self.action_tree.addTopLevelItem(item)
        if self._actions:
            self.action_tree.setCurrentItem(self.action_tree.topLevelItem(0))
        if authorize_apply:
            self._preview_signature = preview_signature(
                self.controller.target, self.controller.config
            )
            self._preview_report = report
        blockers = apply_blockers(report)
        has_safe = bool(report.safe_actions) or any(
            item.get("status") == "missing" for item in report.directory_states
        )
        self._update_project_review_progress(report)
        if blockers:
            extra = (
                f" (+{len(blockers) - 1} more; see Full report)"
                if len(blockers) > 1
                else ""
            )
            self.preview_label.setText(f"Apply blocked: {blockers[0]}{extra}")
            self.preview_label.setToolTip("\n".join(blockers))
            self.apply_button.setToolTip("\n".join(blockers))
            self.apply_button.setEnabled(False)
        elif has_safe and authorize_apply:
            discovery_note = (
                " Discovery metrics are partial, but every proposed destination "
                "was validated directly."
                if report.incomplete
                else ""
            )
            self.preview_label.setText(
                f"Ready: Apply safe changes will process "
                f"{len(report.safe_actions)} safe action(s). "
                f"{len(report.proposals)} proposal(s) remain untouched."
                f"{discovery_note}"
            )
            self.preview_label.setToolTip("")
            self.apply_button.setToolTip(
                "Apply only rows marked Will add or Safe merge. "
                "Review-only proposals remain untouched."
            )
            self.apply_button.setEnabled(True)
        else:
            self.preview_label.setText(
                "Preview required before Apply."
                if has_safe
                else (
                    f"Preview current: no automatic changes available; "
                    f"{len(report.proposals)} proposal(s) require manual merge."
                    if report.proposals
                    else "Preview current: no safe project changes are needed."
                )
            )
            self.preview_label.setToolTip("")
            self.apply_button.setToolTip(
                "Preview the current settings before applying."
                if has_safe
                else "There are no safe changes to apply."
            )
            self.apply_button.setEnabled(False)
        self._refresh_recommendations()

    def _proposal_key(self, action: core.FileAction) -> str:
        return ":".join(
            (
                action.path,
                action.current_sha256 or "missing",
                action.intended_sha256 or "missing",
            )
        )

    def _action_review_status(self, action: core.FileAction) -> str:
        if action.status == "conflicting_proposal":
            return (
                "Reviewed; untouched"
                if self._proposal_key(action) in self._reviewed_proposals
                else "Review manually"
            )
        return self.ACTION_LABELS.get(action.status, action.status)

    def _selected_action(self) -> core.FileAction | None:
        item = self.action_tree.currentItem()
        if item is None:
            return None
        index = item.data(0, self.QtCore.Qt.UserRole)
        if isinstance(index, int) and 0 <= index < len(self._actions):
            return self._actions[index]
        return None

    def _selected_action_changed(
        self,
        item: Any,
        _previous: Any = None,
    ) -> None:
        if item is None:
            self.mark_proposal_reviewed_button.setEnabled(False)
            self.copy_action_button.setEnabled(False)
            self.open_action_button.setEnabled(False)
            return
        index = item.data(0, self.QtCore.Qt.UserRole)
        if isinstance(index, int) and 0 <= index < len(self._actions):
            action = self._actions[index]
            self._show_action(action)
            proposal = action.status == "conflicting_proposal"
            reviewed = self._proposal_key(action) in self._reviewed_proposals
            self.mark_proposal_reviewed_button.setText(
                "Proposal acknowledged (existing kept)"
                if reviewed
                else "Acknowledge proposal (keep existing)"
            )
            self.mark_proposal_reviewed_button.setEnabled(proposal and not reviewed)
            self.copy_action_button.setEnabled(
                bool(action.diff or action.intended_content)
            )
            existing = Path(self.controller.target) / action.path
            self.open_action_button.setEnabled(
                existing.is_file() and not existing.is_symlink()
            )

    def _show_action(self, action: core.FileAction) -> None:
        lines = [
            f"Path: {action.path}",
            f"Action: {self.ACTION_LABELS.get(action.status, action.status)}",
            f"Reason: {action.reason}",
        ]
        if action.status == "conflicting_proposal":
            lines.extend(
                [
                    "",
                    "Review behavior",
                    "---------------",
                    "This proposal will not be applied automatically.",
                    "Inspect the diff, optionally copy it or open the existing file,",
                    "then acknowledge it as reviewed while keeping the existing file.",
                    "To adopt any part, merge it manually and run Preview again.",
                ]
            )
        if action.diff:
            lines.extend(["", "Diff", "----", action.diff.rstrip()])
        elif action.intended_content:
            lines.extend(["", "Intended content", "----------------", action.intended_content.rstrip()])
        self.review_text.setPlainText("\n".join(lines) + "\n")

    def _update_project_review_progress(
        self,
        report: core.AnalysisReport,
    ) -> None:
        reviewed = sum(
            self._proposal_key(action) in self._reviewed_proposals
            for action in report.proposals
        )
        if report.proposals:
            self.review_progress_label.setText(
                f"Proposal review: {reviewed}/{len(report.proposals)} acknowledged. "
                "Select a row to inspect its diff. Acknowledgement keeps the "
                "existing file and does not authorize overwrite or block safe Apply."
            )
        else:
            self.review_progress_label.setText(
                "No conflicting proposals. Select a row to inspect what safe Apply "
                "will add or merge."
            )

    def _mark_selected_proposal_reviewed(self) -> None:
        action = self._selected_action()
        if action is None or action.status != "conflicting_proposal":
            return
        self._reviewed_proposals.add(self._proposal_key(action))
        current = self.action_tree.currentItem()
        if current is not None:
            current.setText(1, self._action_review_status(action))
        self.mark_proposal_reviewed_button.setText(
            "Proposal acknowledged (existing kept)"
        )
        self.mark_proposal_reviewed_button.setEnabled(False)
        if self.controller.report is not None:
            self._update_project_review_progress(self.controller.report)
        self.window.statusBar().showMessage(
            f"Reviewed {action.path}; the existing file will remain untouched."
        )

    def _copy_selected_action(self) -> None:
        action = self._selected_action()
        if action is None:
            return
        content = action.diff or action.intended_content
        if not content:
            self.QtWidgets.QMessageBox.information(
                self.window,
                "Copy selected action",
                "The selected action has no diff or intended content to copy.",
            )
            return
        self.application.clipboard().setText(content)
        self.window.statusBar().showMessage(
            f"Copied review content for {action.path}."
        )

    def _open_selected_action(self) -> None:
        action = self._selected_action()
        if action is None:
            return
        target = Path(self.controller.target).resolve(strict=False)
        candidate = target / action.path
        if candidate.is_symlink():
            self._show_error(
                core.SafetyError(f"refusing to open symlink action path: {candidate}")
            )
            return
        try:
            candidate.resolve(strict=True).relative_to(target)
        except (OSError, ValueError) as error:
            self._show_error(
                core.SafetyError(f"cannot open action path {candidate}: {error}")
            )
            return
        self._open_path(candidate)

    def _show_recovery(self, plan: dict[str, Any]) -> None:
        self.recovery_text.setPlainText(format_restore_instructions(plan))

    def _choose_target(self) -> None:
        selected = self.QtWidgets.QFileDialog.getExistingDirectory(
            self.window,
            "Choose project directory",
            self.target_edit.text(),
        )
        if selected:
            self.target_edit.setText(selected)

    def _save_path(self, title: str, name: str) -> str | None:
        selected, _ = self.QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            title,
            str(Path(self.target_edit.text()).expanduser().parent / name),
            "JSON files (*.json);;All files (*)",
        )
        return selected or None

    def _analyze(self) -> None:
        self._invalidate_preview()
        result = self._run(
            lambda: (
                self._collect(),
                self.controller.analyze(include_health=True),
            )[1],
            "Analyze",
        )
        if result is not None:
            self.navigation.setCurrentRow(4)

    def _preview(self) -> None:
        result = self._run(
            lambda: (self._collect(), self.controller.preview())[1],
            "Preview",
            authorize_apply=True,
        )
        if result is not None:
            self.navigation.setCurrentRow(4)

    def _apply(self) -> None:
        QW = self.QtWidgets
        try:
            config = self._collect()
        except core.ConfigError as error:
            self._show_error(error)
            return
        if self._preview_signature != preview_signature(self.controller.target, config):
            QW.QMessageBox.warning(self.window, "Preview required", "Preview the current settings before applying.")
            self._invalidate_preview()
            return
        answer = QW.QMessageBox.question(
            self.window,
            "Confirm safe apply",
            "Apply only the previewed missing files and safe merges?\n"
            "Conflicts remain untouched proposals."
            + (
                "\n\nWeaker expert overrides are active:\n"
                + "\n".join(
                    f"- {item['dimension']}: {item['derived']} -> {item['value']} "
                    f"({item['reason']})"
                    for item in core.policy_override_details(config)
                    if item["strength"] == "weaker"
                )
                if any(
                    item["strength"] == "weaker"
                    for item in core.policy_override_details(config)
                )
                else ""
            ),
        )
        if answer == QW.QMessageBox.Yes:
            reviewed = self._preview_report
            self._run(
                lambda: self.controller.apply(expected_report=reviewed),
                "Apply",
            )

    def _import_config(self) -> None:
        selected, _ = self.QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Import configuration",
            str(Path(self.target_edit.text()).expanduser().parent),
            "JSON files (*.json);;All files (*)",
        )
        if selected and self._run(lambda: self.controller.import_config(selected), "Import"):
            self._sync_from_config()

    def _export_config(self) -> None:
        path = self._save_path("Export configuration", "workflow-config.json")
        if path:
            self._run(lambda: (self._collect(), self.controller.export_config(path))[1], "Export")

    def _export_report(self) -> None:
        path = self._save_path("Export preview report", "workflow-preview.json")
        if path:
            self._run(
                lambda: core.preview_project(self.controller.target, self._collect(), output=path),
                "Export report",
            )

    def _auto_check_upstream(self) -> None:
        if self.upstream_service.check_due():
            self._check_upstream_now(auto=True)

    def _check_upstream_now(self, *, auto: bool = False) -> None:
        if self._update_replies or self._asset_replies:
            return
        try:
            urls = self.upstream_service.catalog_request_urls()
        except core.UpstreamError as error:
            self._upstream_error = str(error)
            self._refresh_upstream_view()
            return
        self._asset_review = None
        self._asset_item = None
        self._update_payloads = {}
        self._update_errors = []
        self.update_check_button.setEnabled(False)
        self.update_status_label.setText(
            "Checking public GitHub catalog metadata..."
            + (" This automatic check does not send project data." if auto else "")
        )
        for key, url in urls.items():
            request = self.QtNetwork.QNetworkRequest(self.QtCore.QUrl(url))
            request.setRawHeader(b"Accept", b"application/vnd.github+json")
            request.setRawHeader(
                b"User-Agent",
                f"workflow-configurator/{core.TEMPLATE_VERSION}".encode(),
            )
            reply = self.network_manager.get(request)
            self._update_replies[reply] = key
            reply.finished.connect(
                lambda current=reply: self._upstream_reply_finished(current)
            )

    def _upstream_reply_finished(self, reply: Any) -> None:
        key = self._update_replies.pop(reply, None)
        if key is None:
            reply.deleteLater()
            return
        no_error = self.QtNetwork.QNetworkReply.NetworkError.NoError
        if reply.error() != no_error:
            self._update_errors.append(f"{key}: {reply.errorString()}")
        else:
            payload = bytes(reply.readAll())
            if len(payload) > 25_000_000:
                self._update_errors.append(f"{key}: response exceeds 25 MB")
            else:
                self._update_payloads[key] = payload
        reply.deleteLater()
        if self._update_replies:
            return
        self.update_check_button.setEnabled(True)
        if self._update_errors:
            self._upstream_error = "; ".join(self._update_errors)
            self._refresh_upstream_view()
            return
        try:
            self.upstream_service.accept_catalog_payloads(self._update_payloads)
        except core.UpstreamError as error:
            self._upstream_error = str(error)
        else:
            self._upstream_error = ""
        self._refresh_upstream_view()

    def _refresh_upstream_view(self) -> None:
        if not hasattr(self, "upstream_text"):
            return
        report = self.upstream_service.report
        self._review_items_by_key = {}
        self.upstream_queue.clear()
        self.inspect_review_button.setEnabled(False)
        self.save_review_button.setEnabled(False)
        self.export_review_button.setEnabled(report is not None)
        if report is None:
            self.upstream_text.setPlainText(
                "No cached update report exists yet. The next automatic or manual "
                "check reads only public GitHub commit and tree metadata."
            )
            status = "No update metadata cached."
        else:
            items = self.upstream_service.review_items()
            outstanding = self.upstream_service.review_items(
                outstanding_only=True
            )
            self.upstream_text.setPlainText(core.render_upstream_report(report))
            user_role = self.QtCore.Qt.ItemDataRole.UserRole
            for review_item in items:
                decision = self.upstream_service.decision_for(review_item)
                row = self.QtWidgets.QTreeWidgetItem(
                    [
                        (
                            "Monitored: " + review_item.change.title()
                            if review_item.label
                            else review_item.change.title()
                        ),
                        review_item.path,
                        decision.disposition if decision is not None else "Pending",
                    ]
                )
                row.setData(0, user_role, review_item.state_key)
                self.upstream_queue.addTopLevelItem(row)
                self._review_items_by_key[review_item.state_key] = review_item
            self.upstream_queue.resizeColumnToContents(0)
            self.upstream_queue.resizeColumnToContents(2)
            status = (
                f"Monitored changes: {len(report.monitored_changes)}. "
                f"Other catalog differences: {len(items) - len(report.monitored_changes)}. "
                f"Pending baseline decisions: {len(outstanding)}. "
                "Configured workflows are unchanged."
            )
        if self._upstream_error:
            status += " Update warning: " + self._upstream_error
        self.update_status_label.setText(status)
        self.advance_baseline_button.setEnabled(
            self.upstream_service.can_advance_baseline()
        )

    def _selected_upstream_item(self) -> core.UpstreamReviewItem | None:
        selected = self.upstream_queue.selectedItems()
        if not selected:
            return None
        key = selected[0].data(
            0,
            self.QtCore.Qt.ItemDataRole.UserRole,
        )
        return self._review_items_by_key.get(str(key))

    def _upstream_selection_changed(self) -> None:
        item = self._selected_upstream_item()
        self.inspect_review_button.setEnabled(
            item is not None and not self._asset_replies and not self._update_replies
        )
        if item is None:
            self._asset_review = None
            self.save_review_button.setEnabled(False)
            return
        if self._asset_review is None or self._asset_review.item != item:
            self._asset_review = None
            self.save_review_button.setEnabled(False)
            decision = self.upstream_service.decision_for(item)
            if decision is None:
                self.review_note_edit.clear()
                self.upstream_detail.setPlainText(
                    f"{item.path}\n\nSelect Inspect selected to fetch only this "
                    "asset's size-capped blobs and render a read-only diff."
                )
            else:
                index = self.review_disposition_combo.findData(
                    decision.disposition
                )
                if index >= 0:
                    self.review_disposition_combo.setCurrentIndex(index)
                self.review_note_edit.setText(decision.note)
                self.upstream_detail.setPlainText(
                    f"{item.path}\n\nRecorded decision: {decision.disposition}\n"
                    f"Rationale: {decision.note}\nReviewed: {decision.reviewed_at}\n\n"
                    "Inspect again before changing this decision."
                )

    def _inspect_upstream_item(self) -> None:
        item = self._selected_upstream_item()
        if item is None or self._asset_replies or self._update_replies:
            return
        try:
            urls = self.upstream_service.asset_request_urls(item)
        except core.UpstreamError as error:
            self._error(error)
            return
        if not urls:
            self._error(core.UpstreamError("the selected item has no reviewable blob"))
            return
        self._asset_review = None
        self._asset_item = item
        self._asset_payloads = {}
        self._asset_errors = []
        self.inspect_review_button.setEnabled(False)
        self.save_review_button.setEnabled(False)
        self.upstream_detail.setPlainText(
            "Fetching the selected untrusted asset only. Content is size-capped "
            "and will be displayed read-only."
        )
        for key, url in urls.items():
            request = self.QtNetwork.QNetworkRequest(self.QtCore.QUrl(url))
            request.setRawHeader(b"Accept", b"application/vnd.github+json")
            request.setRawHeader(
                b"User-Agent",
                f"workflow-configurator/{core.TEMPLATE_VERSION}".encode(),
            )
            reply = self.network_manager.get(request)
            self._asset_replies[reply] = key
            reply.finished.connect(
                lambda current=reply: self._asset_reply_finished(current)
            )

    def _asset_reply_finished(self, reply: Any) -> None:
        key = self._asset_replies.pop(reply, None)
        if key is None:
            reply.deleteLater()
            return
        no_error = self.QtNetwork.QNetworkReply.NetworkError.NoError
        if reply.error() != no_error:
            self._asset_errors.append(f"{key}: {reply.errorString()}")
        else:
            payload = bytes(reply.readAll())
            if len(payload) > core.MAX_BLOB_RESPONSE_BYTES:
                self._asset_errors.append(f"{key}: response exceeds the size limit")
            else:
                self._asset_payloads[key] = payload
        reply.deleteLater()
        if self._asset_replies:
            return
        self.inspect_review_button.setEnabled(
            self._selected_upstream_item() is not None
        )
        if self._asset_errors:
            self._asset_item = None
            message = "; ".join(self._asset_errors)
            self.upstream_detail.setPlainText(f"Asset review failed: {message}")
            self.QtWidgets.QMessageBox.warning(
                self.window,
                "Upstream asset review",
                message,
            )
            return
        item = self._asset_item
        self._asset_item = None
        if item is None or self._selected_upstream_item() != item:
            self.upstream_detail.setPlainText(
                "The selection changed before the asset review completed."
            )
            return
        try:
            review = self.upstream_service.build_asset_review(
                item,
                self._asset_payloads,
            )
        except core.UpstreamError as error:
            self._error(error)
            return
        self._asset_review = review
        self.upstream_detail.setPlainText(core.render_asset_review(review))
        self.save_review_button.setEnabled(True)

    def _save_upstream_decision(self) -> None:
        review = self._asset_review
        if review is None:
            self.QtWidgets.QMessageBox.information(
                self.window,
                "Upstream asset review",
                "Inspect the selected asset before recording a decision.",
            )
            return
        disposition = str(self.review_disposition_combo.currentData())
        note = self.review_note_edit.text()
        result = self._run(
            lambda: self.upstream_service.record_review(
                review,
                disposition,
                note,
            ),
            "Save upstream review decision",
        )
        if result is None:
            return
        self._asset_review = None
        self.review_note_edit.clear()
        self._refresh_upstream_view()
        self.window.statusBar().showMessage(
            f"Saved {disposition} decision for {review.item.path}."
        )

    def _advance_upstream_baseline(self) -> None:
        report = self.upstream_service.report
        if report is None or not self.upstream_service.can_advance_baseline():
            self.QtWidgets.QMessageBox.information(
                self.window,
                "Advance reviewed baseline",
                "Every changed item needs an inspected, recorded decision first.",
            )
            return
        answer = self.QtWidgets.QMessageBox.question(
            self.window,
            "Advance reviewed baseline",
            "Mark the current Awesome Copilot revision as reviewed?\n\n"
            f"{report.current_revision}\n\n"
            "This changes only local review state. It does not install or apply "
            "upstream content.",
            self.QtWidgets.QMessageBox.StandardButton.Yes
            | self.QtWidgets.QMessageBox.StandardButton.No,
            self.QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer != self.QtWidgets.QMessageBox.StandardButton.Yes:
            return
        baseline = self._run(
            self.upstream_service.advance_baseline,
            "Advance reviewed baseline",
        )
        if baseline is None:
            return
        self._asset_review = None
        self._refresh_upstream_view()
        self.window.statusBar().showMessage(
            f"Reviewed baseline advanced to {baseline}. Refreshing metadata..."
        )
        self._check_upstream_now()

    def _export_upstream_review(self) -> None:
        report = self.upstream_service.report
        if report is None:
            return
        selected, _ = self.QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Export upstream review brief",
            str(
                Path(self.target_edit.text()).expanduser().parent
                / "upstream-customization-review.md"
            ),
            "Markdown files (*.md);;All files (*)",
        )
        if not selected:
            return
        result = self._run(
            lambda: core.export_review_brief(report, selected),
            "Export update review",
        )
        if result is not None:
            self.window.statusBar().showMessage(
                f"Review brief exported to {result}. No upstream content was installed."
            )

    def _choose_plugin_parent(self) -> None:
        selected = self.QtWidgets.QFileDialog.getExistingDirectory(
            self.window,
            "Choose plugin export parent",
            str(Path(self.plugin_destination_edit.text()).expanduser().parent),
        )
        if selected:
            self.plugin_destination_edit.setText(
                str(Path(selected) / "genai-workflow-core")
            )

    def _invalidate_plugin_preview(self) -> None:
        self._plugin_preview = None
        if hasattr(self, "export_plugin_button"):
            self.export_plugin_button.setEnabled(False)

    def _preview_plugin_export(self) -> None:
        result = self._run(
            lambda: core.preview_local_plugin(self.plugin_destination_edit.text()),
            "Preview local plugin",
        )
        if isinstance(result, core.PluginExportPlan):
            self._plugin_preview = result
            self.plugin_text.setPlainText(core.render_plugin_preview(result))
            self.export_plugin_button.setEnabled(True)

    def _export_plugin(self) -> None:
        if self._plugin_preview is None:
            return
        answer = self.QtWidgets.QMessageBox.question(
            self.window,
            "Confirm local plugin export",
            "Export exactly the previewed reviewed local plugin files?\n\n"
            "This does not install, enable, update, or publish the plugin.",
        )
        if answer != self.QtWidgets.QMessageBox.Yes:
            return
        result = self._run(
            lambda: core.export_local_plugin(self._plugin_preview),
            "Export local plugin",
        )
        if isinstance(result, dict) and result.get("status") == "exported":
            self.plugin_text.setPlainText(
                json.dumps(result, indent=2, sort_keys=True)
            )
            self._invalidate_plugin_preview()

    def _restore_instructions(self) -> None:
        result = self._run(self.controller.restore_instructions, "Recovery guidance")
        if result is not None:
            self.navigation.setCurrentRow(self.PAGE_NAMES.index("Recovery"))

    def _check_external_health(self) -> None:
        result = self._run(
            lambda: core.external_health(self._collect(), self.controller.target),
            "Memory and code health",
        )
        if result is not None:
            self.memory_health_text.setPlainText(
                format_continuity_health(result)
            )

    def _export_restore_plan(self) -> None:
        path = self._save_path("Export restore plan", "restore-plan.json")
        if path:
            self._run(lambda: self.controller.restore_instructions(output=path), "Export recovery")

    def _open_target(self) -> None:
        self._open_path(self.target_edit.text())

    def _open_backups(self) -> None:
        target = Path(self.target_edit.text())
        current = target / core.BACKUPS_DIRECTORY
        legacy = target / core.LEGACY_BACKUPS_DIRECTORY
        self._open_path(current if current.exists() else legacy)

    def _open_path(self, path: Path | str) -> None:
        target = Path(path).expanduser().resolve(strict=False)
        if not target.exists():
            self._show_error(core.SafetyError(f"path does not exist: {target}"))
            return
        if not self.QtGui.QDesktopServices.openUrl(self.QtCore.QUrl.fromLocalFile(str(target))):
            self._show_error(core.SafetyError(f"cannot open path: {target}"))

    def _install_launcher(self) -> None:
        root = Path(__file__).resolve().parent.parent
        environment = {
            **os.environ,
            "WORKFLOW_CONFIGURATOR_PYTHON": sys.executable,
        }
        run_options: dict[str, Any] = {}
        if sys.platform.startswith("win"):
            script = root / "install-workflow-configurator-launcher.ps1"
            power_shell = shutil.which("pwsh") or shutil.which("powershell")
            if power_shell is None:
                self._show_error(
                    core.SafetyError(
                        "PowerShell is required to install the Windows user shortcut"
                    )
                )
                return
            command = [
                power_shell,
                "-NoLogo",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-File",
                str(script),
                "-Python",
                sys.executable,
                "-NoDialog",
            ]
            run_options["creationflags"] = getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            )
        else:
            script = root / "install-workflow-configurator-launcher.sh"
            command = [str(script)]
            environment["WORKFLOW_CONFIGURATOR_NO_DIALOG"] = "1"
        result = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            **run_options,
        )
        if result.returncode:
            self._show_error(core.SafetyError(result.stderr.strip() or "launcher installation failed"))
        else:
            self.window.statusBar().showMessage(
                "Application launcher installed. Search for Workflow Configurator."
            )

    def _show_help(self) -> None:
        self.navigation.setCurrentRow(self.PAGE_NAMES.index("Guide"))

    def _show_about(self) -> None:
        QW = self.QtWidgets
        dialog = QW.QDialog(self.window)
        dialog.setWindowTitle("About Workflow Configurator")
        dialog.resize(620, 430)
        layout = QW.QVBoxLayout(dialog)
        title = QW.QLabel("<h2>Workflow Configurator</h2>")
        layout.addWidget(title)
        details = QW.QTextBrowser()
        details.setOpenExternalLinks(True)
        research = Path(__file__).resolve().parent.parent / "docs" / "research"
        guide = Path(__file__).resolve().parent / "docs" / "CONFIGURATOR.md"
        details.setHtml(
            "<p>A local-first, adaptive GitHub Copilot workflow configurator.</p>"
            f"<p><b>Template:</b> {core.TEMPLATE_VERSION}<br>"
            f"<b>Configuration schema:</b> {core.CONFIG_VERSION}<br>"
            "<b>GUI:</b> PySide6 / Qt<br>"
            "<b>Telemetry:</b> none</p>"
            "<p>Automatic update checks read public GitHub commit/tree metadata "
            "at most once per day and create an unreviewed delta queue. They do "
            "not send project data, download asset contents, or alter trusted policy.</p>"
            "<p>It can preview and add missing workflow files plus narrowly "
            "documented additive settings. It never automatically overwrites "
            "conflicts, installs external tools, upgrades services, deletes "
            "project files, migrates memory, or rolls back a project.</p>"
            f'<p><a href="{guide.as_uri()}">Local configurator guide</a><br>'
            f'<a href="{research.as_uri()}">Research assessments</a></p>'
            "<p>External projects retain their own licenses. Generated local "
            "specialists are compact adaptations, not copied persona catalogs.</p>"
        )
        layout.addWidget(details, 1)
        buttons = QW.QDialogButtonBox(QW.QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _show_error(self, error: Exception) -> None:
        self.window.statusBar().showMessage(f"Error: {error}")
        self.QtWidgets.QMessageBox.critical(self.window, "Workflow Configurator", str(error))

    def show(self) -> None:
        self.window.show()

    def run(self) -> int:
        self.show()
        return self.application.exec()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_path", type=Path, nargs="?", help="project directory")
    parser.add_argument("--target", dest="target_option", type=Path, help="project directory")
    parser.add_argument("--config", type=Path, help="import a versioned JSON configuration")
    parser.add_argument("--headless-smoke", action="store_true")
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="disable the metadata-only Awesome Copilot check for this launch",
    )
    return parser


def main(
    argv: Iterable[str] | None = None,
    *,
    initial_config: core.WorkflowConfig | None = None,
) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    target = args.target_option or args.target_path or Path(".")
    if args.config is not None and initial_config is not None:
        print("GUI configuration error: choose a config file or an initial configuration", file=sys.stderr)
        return 2
    if args.headless_smoke:
        try:
            config = initial_config or (core.load_config(args.config) if args.config is not None else None)
            print(json.dumps(headless_smoke(target, config), indent=2, sort_keys=True))
            return 0
        except (core.ConfigError, core.SafetyError) as error:
            print(f"GUI headless smoke failed: {error}", file=sys.stderr)
            return 2
    controller = ConfiguratorController(target, initial_config)
    if args.config is not None:
        try:
            controller.import_config(args.config)
        except (core.ConfigError, core.SafetyError) as error:
            print(f"GUI configuration error: {error}", file=sys.stderr)
            return 2
    try:
        return WorkflowConfiguratorApp(
            controller,
            auto_check_updates=not args.no_update_check,
        ).run()
    except ImportError as error:
        print(f"GUI unavailable: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
