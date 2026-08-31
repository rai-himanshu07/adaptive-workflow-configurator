"""Passive manifest reading and manual-only recovery guidance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from . import manifest as manifest_state


def render_restore_instructions(plan: Mapping[str, Any]) -> str:
    manifests = plan.get("manifest_paths", [])
    lines = [
        "Manual restore instructions",
        "---------------------------",
        f"Manifest: {plan.get('manifest_path', '(unknown)')}",
        f"Target: {plan.get('target', '(unknown)')}",
        "",
        "Material manifests",
        "------------------",
        *([f"  {path}" for path in manifests] or ["  (none)"]),
        "",
        "Generated paths for manual review/removal",
        "------------------------------------------",
    ]
    created = plan.get("created_files", [])
    if created:
        lines.extend(
            f"  {item.get('path', '(unknown)')} ({item.get('state', 'manual')})"
            if isinstance(item, Mapping)
            else "  (invalid generated-file entry; inspect manually)"
            for item in created
        )
    else:
        lines.extend(
            f"  {path} (manual)"
            for path in plan.get("generated_paths", []) or ["(none)"]
        )
    lines.extend(
        [
            "",
            "Safe merge backups for manual restoration",
            "------------------------------------------",
        ]
    )
    merges = plan.get("safe_merges", [])
    if not merges:
        lines.append("  (none)")
    else:
        lines.extend(
            (
                f"  Review backup {item.get('backup', '(unknown)')} and manually "
                f"copy it to {item.get('path', '(unknown)')} "
                f"({item.get('state', 'manual')})."
                if isinstance(item, Mapping)
                else "  (invalid merge entry; inspect the manifest manually)"
            )
            for item in merges
        )
    lines.extend(
        [
            "",
            "Older material history (not active mappings)",
            "--------------------------------------------",
        ]
    )
    history = plan.get("history", [])
    if not history:
        lines.append("  (none)")
    else:
        lines.extend(
            (
                f"  {item.get('kind', 'material')} "
                f"{item.get('path', '(unknown)')} from "
                f"{item.get('manifest_path', '(unknown)')} "
                f"({item.get('state', 'manual')})"
                if isinstance(item, Mapping)
                else "  (invalid history entry; inspect the manifest manually)"
            )
            for item in history
        )
    directories = plan.get("required_directories", [])
    lines.extend(
        [
            "",
            "Required directories (preserved)",
            "--------------------------------",
            *(
                [
                    f"  {item.get('path', '(unknown)')}"
                    for item in directories
                    if isinstance(item, Mapping)
                ]
                or ["  (none)"]
            ),
            "",
            "Policy: no project file or directory is restored or removed automatically.",
        ]
    )
    return "\n".join(lines) + "\n"


def restore_instructions(
    manifest: Path | str | None = None,
    target: Path | str | None = None,
    *,
    output: Path | str | None = None,
) -> dict[str, Any]:
    from . import core

    value = "" if manifest is None else str(manifest)
    if value in {"", "."} and target is not None:
        target_path = core._ensure_target_path(
            Path(target).expanduser(), allow_missing=False
        )
        material = core._material_manifests(target_path)
        if material:
            manifest_path, data = material[-1][1], material[-1][2]
            manifests = material
        else:
            manifest_path, target_path = core._resolve_manifest(manifest, target_path)
            try:
                data = manifest_state.load(manifest_path)
            except manifest_state.ManifestError as error:
                raise core.RollbackError(str(error)) from error
            manifests = [(core._manifest_time(manifest_path), manifest_path, data)]
    else:
        manifest_path, target_path = core._resolve_manifest(manifest, target)
        try:
            data = manifest_state.load(manifest_path)
        except manifest_state.ManifestError as error:
            raise core.RollbackError(str(error)) from error
        manifests = [(core._manifest_time(manifest_path), manifest_path, data)]

    manifest_target = data.get("target")
    if target_path is not None and (
        not isinstance(manifest_target, str)
        or Path(manifest_target).expanduser().resolve(strict=False)
        != target_path.resolve(strict=False)
    ):
        raise core.RollbackError("apply manifest target does not match requested target")
    if target_path is None and isinstance(manifest_target, str):
        target_path = Path(manifest_target).expanduser().resolve(strict=False)
    if target_path is None:
        raise core.RollbackError(
            "manifest does not identify a target for restore guidance"
        )
    created, merges, directories, history = core._aggregate_restore_material(
        manifests, target_path
    )
    plan: dict[str, Any] = {
        "status": "manual_restore",
        "policy": "manual-only",
        "manifest_path": str(manifest_path),
        "manifest_paths": [str(item[1]) for item in manifests],
        "target": manifest_target,
        "generated_paths": [
            item.get("path")
            for item in created
            if isinstance(item, Mapping) and isinstance(item.get("path"), str)
        ],
        "created_files": created,
        "safe_merges": merges,
        "required_directories": directories,
        "history": history,
        "missing_paths": [
            item["path"]
            for item in [*created, *merges]
            if item.get("state") == "missing"
        ],
        "manual_paths": [
            item["path"]
            for item in [*created, *merges]
            if item.get("state") == "manual"
        ],
        "instructions": [],
    }
    instructions = plan["instructions"]
    instructions.extend(
        f"Review/remove manually if desired: {item.get('path')} "
        f"({item.get('state', 'manual')})."
        for item in created
        if isinstance(item, Mapping)
    )
    instructions.extend(
        f"Review backup {item.get('backup')} and manually copy it to "
        f"{item.get('path')} ({item.get('state', 'manual')})."
        for item in merges
        if isinstance(item, Mapping)
    )
    instructions.extend(
        f"Keep required directory present for review: {item.get('path')}."
        for item in directories
        if isinstance(item, Mapping)
    )
    instructions.append(
        "No project path is modified automatically; verify every manual action first."
    )
    if output is not None:
        output_path = Path(output).expanduser()
        if output_path.is_symlink():
            raise core.SafetyError(
                f"refusing symlink restore-plan output: {output_path}"
            )
        core._ensure_output_parent(output_path.parent)
        plan["output_path"] = str(output_path)
        core._atomic_write(
            output_path,
            (json.dumps(plan, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o644,
        )
    return plan


def rollback_project(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    from .core import RollbackError

    raise RollbackError(
        "automatic rollback was removed; no project paths were changed. "
        "Use --restore-instructions to review the passive apply manifest and "
        "restore safe merges manually."
    )


__all__ = [
    "render_restore_instructions",
    "restore_instructions",
    "rollback_project",
]
