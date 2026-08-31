"""No-overwrite export of the reviewed generic Copilot specialist plugin."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PLUGIN_NAME = "genai-workflow-core"
PLUGIN_AGENT_SOURCES = (
    ".github/agents/accessibility-reviewer.agent.md",
    ".github/agents/appsec-reviewer.agent.md",
    ".github/agents/tool-evaluator.agent.md",
    ".github/agents/research-synthesist.agent.md",
    ".github/agents/lean-code-reviewer.agent.md",
)


class PluginExportError(RuntimeError):
    """Raised when a local plugin cannot be previewed or exported safely."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class PluginFile:
    path: str
    content: bytes

    @property
    def sha256(self) -> str:
        return _sha256(self.content)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "bytes": len(self.content),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class PluginExportPlan:
    destination: str
    plugin_name: str
    plugin_version: str
    files: tuple[PluginFile, ...]

    @property
    def signature(self) -> str:
        payload = {
            "destination": self.destination,
            "plugin_name": self.plugin_name,
            "plugin_version": self.plugin_version,
            "files": [item.to_dict() for item in self.files],
        }
        return _sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "plugin_name": self.plugin_name,
            "plugin_version": self.plugin_version,
            "signature": self.signature,
            "files": [item.to_dict() for item in self.files],
            "install_working_directory": self.destination,
            "install_command": "copilot plugin install .",
            "notice": (
                "This exports reviewed local files only. It does not install, enable, "
                "update, or publish the plugin."
            ),
        }


def _validate_destination(path: Path) -> Path:
    destination = path.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise PluginExportError(
            f"plugin destination already exists; refusing overwrite: {destination}"
        )
    if destination == destination.parent or destination == Path.home():
        raise PluginExportError(f"unsafe plugin destination: {destination}")
    parent = destination.parent
    if parent.is_symlink() or not parent.is_dir():
        raise PluginExportError(
            f"plugin destination parent must be an existing directory: {parent}"
        )
    current = parent
    while current != current.parent:
        if current.is_symlink():
            raise PluginExportError(f"plugin path component is a symlink: {current}")
        current = current.parent
    try:
        parent.resolve(strict=True)
    except OSError as error:
        raise PluginExportError(f"cannot resolve plugin destination parent: {parent}") from error
    return destination


def _read_agent(source_root: Path, relative: str) -> bytes:
    source = source_root / relative
    if source.is_symlink() or not source.is_file():
        raise PluginExportError(f"missing or unsafe plugin source: {relative}")
    try:
        source.resolve(strict=True).relative_to(source_root.resolve(strict=True))
        return source.read_bytes()
    except (OSError, ValueError) as error:
        raise PluginExportError(f"cannot read plugin source {relative}: {error}") from error


def _plugin_files(source_root: Path, version: str) -> tuple[PluginFile, ...]:
    manifest = {
        "name": PLUGIN_NAME,
        "description": (
            "Five compact, read-only specialist reviewers from the local adaptive "
            "workflow configurator."
        ),
        "version": version,
        "author": {"name": "Workflow Configurator"},
        "keywords": [
            "github-copilot",
            "review",
            "accessibility",
            "appsec",
            "lean-code",
        ],
        "agents": "agents/",
    }
    readme = f"""# {PLUGIN_NAME}

This local Copilot plugin contains only the five generic specialist agents
already reviewed in the Workflow Configurator. It contains no hooks, MCP
servers, project policy, memory identity, task state, installer, or updater.

Preview and export are separate. Export never installs or enables the plugin.
After reviewing the exported files, test it manually:

```bash
copilot plugin install .
copilot plugin list
```

Uninstall with `copilot plugin uninstall {PLUGIN_NAME}`.
"""
    files = [
        PluginFile(
            "plugin.json",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        ),
        PluginFile("README.md", readme.encode("utf-8")),
    ]
    for relative in PLUGIN_AGENT_SOURCES:
        files.append(
            PluginFile(
                f"agents/{Path(relative).name}",
                _read_agent(source_root, relative),
            )
        )
    integrity = {
        "schema": 1,
        "plugin": PLUGIN_NAME,
        "version": version,
        "files": [item.to_dict() for item in files],
        "notice": (
            "Hashes detect drift from this reviewed export; they do not prove "
            "authorship or upstream trust."
        ),
    }
    files.append(
        PluginFile(
            "INTEGRITY.json",
            (json.dumps(integrity, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    )
    return tuple(sorted(files, key=lambda item: item.path))


def preview_plugin_export(
    destination: Path | str,
    *,
    source_root: Path | str,
    version: str,
) -> PluginExportPlan:
    target = _validate_destination(Path(destination))
    root = Path(source_root).resolve(strict=True)
    return PluginExportPlan(
        destination=str(target),
        plugin_name=PLUGIN_NAME,
        plugin_version=version,
        files=_plugin_files(root, version),
    )


def apply_plugin_export(
    expected: PluginExportPlan,
    *,
    source_root: Path | str,
) -> Mapping[str, object]:
    current = preview_plugin_export(
        expected.destination,
        source_root=source_root,
        version=expected.plugin_version,
    )
    if current.signature != expected.signature:
        raise PluginExportError(
            "plugin sources or destination changed after Preview; preview again"
        )
    destination = Path(current.destination)
    destination_created = False
    try:
        try:
            destination.mkdir(mode=0o700)
        except FileExistsError as error:
            raise PluginExportError(
                f"plugin destination appeared after Preview: {destination}"
            ) from error
        destination_created = True
        for item in current.files:
            output = destination / item.path
            output.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(output, flags, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(item.content)
                handle.flush()
                os.fsync(handle.fileno())
    except Exception:
        if (
            destination_created
            and destination.exists()
            and destination.is_dir()
            and not destination.is_symlink()
        ):
            shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        "status": "exported",
        "destination": str(destination),
        "signature": current.signature,
        "files": [item.to_dict() for item in current.files],
        "install_command": current.to_dict()["install_command"],
        "notice": "Plugin exported but not installed or enabled.",
    }


def render_plugin_preview(plan: PluginExportPlan) -> str:
    lines = [
        f"Plugin: {plan.plugin_name}",
        f"Version: {plan.plugin_version}",
        f"Destination: {plan.destination}",
        f"Preview signature: {plan.signature}",
        "",
        "Files",
    ]
    for item in plan.files:
        lines.append(
            f"- {item.path} ({len(item.content)} bytes, sha256 {item.sha256})"
        )
    lines.extend(["", "Content"])
    for item in plan.files:
        lines.extend(
            [
                "",
                f"--- {item.path} ---",
                item.content.decode("utf-8", errors="strict").rstrip(),
            ]
        )
    lines.extend(
        [
            "",
            "Export is no-overwrite and does not install, enable, publish, or update",
            "the plugin. Review the exported files before running the displayed",
            "Copilot CLI install command.",
        ]
    )
    return "\n".join(lines) + "\n"


__all__ = [
    "PLUGIN_AGENT_SOURCES",
    "PLUGIN_NAME",
    "PluginExportError",
    "PluginExportPlan",
    "PluginFile",
    "apply_plugin_export",
    "preview_plugin_export",
    "render_plugin_preview",
]
