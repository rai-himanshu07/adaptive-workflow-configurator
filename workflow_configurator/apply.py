"""Transactional safe Apply implementation behind the public core facade."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import manifest as manifest_state
from .config_model import WorkflowConfig


@dataclass
class ApplyResult:
    report: Any
    manifest_path: Path | None
    added_paths: list[str]
    merged_paths: list[str]
    proposals: list[Any]
    recorded_directories: list[str] = field(default_factory=list)

    @property
    def manifest(self) -> Path | None:
        return self.manifest_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "added_paths": list(self.added_paths),
            "merged_paths": list(self.merged_paths),
            "recorded_directories": list(self.recorded_directories),
            "proposals": [item.to_dict() for item in self.proposals],
            "report": self.report.to_dict(),
        }


def _report_preconditions(report: Any) -> tuple[Any, ...]:
    actions = tuple(
        (
            item.path,
            item.status,
            item.current_sha256,
            item.intended_sha256,
            tuple(sorted(dict(item.metadata).items())),
        )
        for item in report.actions
    )
    directories = tuple(
        tuple(sorted(dict(item).items())) for item in report.directory_states
    )
    return (
        str(Path(report.target).expanduser().resolve(strict=False)),
        json.dumps(report.config.to_dict(), sort_keys=True),
        actions,
        directories,
    )


def apply_project(
    target: Path | str,
    config: WorkflowConfig | None = None,
    *,
    source_root: Path | str | None = None,
    fail_after: int | None = None,
    collision_policy: str = "proposal",
    dry_run: bool = False,
    write_manifest: bool = True,
    expected_report: Any | None = None,
) -> ApplyResult:
    """Apply missing files and safe merges with in-process transaction cleanup."""

    from . import core

    if collision_policy not in {"proposal", "refuse"}:
        raise core.ApplyError(
            f"unsupported collision policy {collision_policy!r}; choose proposal or refuse"
        )
    target_path = core._ensure_target_path(Path(target).expanduser(), allow_missing=True)
    config = config or core.config_for_target(target_path)
    report = core.analyze_project(target_path, config, source_root=source_root)
    if expected_report is not None and (
        _report_preconditions(expected_report) != _report_preconditions(report)
    ):
        raise core.ApplyError(
            "project actions changed after Preview; review a fresh Preview before applying"
        )
    if report.errors:
        raise core.ApplyError("; ".join(report.errors))
    unsafe = [action for action in report.actions if action.status == "unsafe"]
    if unsafe:
        details = "; ".join(f"{item.path}: {item.reason}" for item in unsafe)
        raise core.ApplyError(f"safe apply aborted due to unsafe destinations: {details}")
    if collision_policy == "refuse":
        collisions = [
            action
            for action in report.actions
            if action.status != "missing" and action.path != ".gitignore"
        ]
        if collisions:
            raise core.ApplyError(
                "destination files already exist: "
                + "; ".join(item.path for item in collisions)
            )
    if dry_run:
        return ApplyResult(report, None, [], [], report.proposals)

    source = core._source_root(source_root)
    manifest_id = manifest_state.new_id()
    created_dirs: list[Path] = []
    created_files: list[Path] = []
    modified: list[tuple[Path, bytes, int]] = []
    backup_files: list[Path] = []
    manifest_path = (
        target_path / core.MANIFESTS_DIRECTORY / f"{manifest_id}.json"
        if write_manifest
        else None
    )
    backup_root = target_path / core.BACKUPS_DIRECTORY / manifest_id
    write_count = 0
    manifest_written = False
    owned_writes: list[Path] = []
    owned_write_token = core._ACTIVE_OWNED_WRITES.set(owned_writes)

    def maybe_fail() -> None:
        nonlocal write_count
        write_count += 1
        if fail_after is not None and write_count > fail_after:
            raise core.ApplyError(f"injected failure after {fail_after} write(s)")

    try:
        core._ensure_directory(target_path, created_dirs)
        required_directories: list[dict[str, Any]] = []
        for relative in core.required_project_directories(config):
            directory = core._directory_path(target_path, relative)
            existed = directory.exists()
            core._ensure_directory(directory, created_dirs)
            required_directories.append(
                {
                    "path": relative,
                    "was_missing": not existed,
                    "mode": core._mode(directory),
                    "state": "existing",
                }
            )
        if write_manifest:
            core._ensure_directory(
                target_path / Path(core.MANIFESTS_DIRECTORY).parent,
                created_dirs,
            )
            core._ensure_directory(
                target_path / core.MANIFESTS_DIRECTORY, created_dirs
            )
            core._ensure_directory(target_path / core.BACKUPS_DIRECTORY, created_dirs)
            core._ensure_directory(backup_root, created_dirs)
            for action in report.actions:
                if action.status != "safe_merge":
                    continue
                destination = core._target_path(target_path, action.path)
                backup_path = backup_root / action.path
                core._ensure_directory(backup_path.parent, created_dirs)
                core._write_new_bytes(
                    backup_path, destination.read_bytes(), core._mode(destination)
                )
                backup_files.append(backup_path)

        intended_files = core._intended_files(config, source)
        created_entries: list[dict[str, Any]] = []
        merged_entries: list[dict[str, Any]] = []
        for action in report.actions:
            if action.status not in {"missing", "safe_merge"}:
                continue
            destination = core._target_path(target_path, action.path)
            if action.status == "missing":
                core._ensure_directory(destination.parent, created_dirs)
                mode = int(action.metadata.get("mode", 0o644))
                content = intended_files[action.path]
                core._write_new_bytes(destination, content, mode)
                created_files.append(destination)
                maybe_fail()
                created_entries.append(
                    {
                        "path": action.path,
                        "sha256": core._sha256_bytes(content),
                        "mode": mode,
                    }
                )
                continue

            before = destination.read_bytes()
            if (
                action.current_sha256
                and core._sha256_bytes(before) != action.current_sha256
            ):
                raise core.ApplyError(
                    f"{action.path} changed after preview; rerun analysis before applying"
                )
            before_mode = core._mode(destination)
            if action.path == ".gitignore":
                status, merged_content, reason = core._gitignore_forward_merge(before)
            elif action.path == ".vscode/settings.json":
                status, merged_content, reason = core._settings_merge(
                    before, intended_files[action.path]
                )
            else:
                raise core.ApplyError(f"unsupported safe merge action: {action.path}")
            if status != "safe_merge" or merged_content is None:
                raise core.ApplyError(f"{action.path} changed during apply: {reason}")
            modified.append((destination, before, before_mode))
            core._atomic_write(destination, merged_content, before_mode)
            maybe_fail()
            merged_entries.append(
                {
                    "path": action.path,
                    "before_sha256": core._sha256_bytes(before),
                    "after_sha256": core._sha256_bytes(merged_content),
                    "before_mode": before_mode,
                    "after_mode": core._mode(destination),
                    "backup": str(
                        (
                            Path(core.BACKUPS_DIRECTORY)
                            / manifest_id
                            / action.path
                        ).as_posix()
                    ),
                }
            )

        if write_manifest:
            manifest_data = manifest_state.build(
                target=target_path,
                config=config.to_dict(),
                created_files=created_entries,
                safe_merges=merged_entries,
                proposals=[proposal.to_dict() for proposal in report.proposals],
                required_directories=required_directories,
                manifest_id=manifest_id,
            )
            if manifest_path is None:
                raise core.ApplyError("internal error: manifest path was not prepared")
            core._write_new_bytes(
                manifest_path,
                (json.dumps(manifest_data, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
                0o644,
            )
            manifest_written = True
            maybe_fail()
    except Exception as error:
        try:
            restore_errors: list[str] = []
            for path, original, mode in reversed(modified):
                try:
                    core._atomic_write(path, original, mode)
                except Exception as restore_error:
                    restore_errors.append(f"{path}: {restore_error}")
            preserved = set(backup_files)
            if manifest_path is not None and manifest_path.exists():
                preserved.add(manifest_path)
            preserved_evidence = preserved if restore_errors else set()
            cleanup_errors: list[str] = []
            cleanup_paths = {
                *created_files,
                *owned_writes,
                *(backup_files if not restore_errors else ()),
            } - preserved_evidence
            if manifest_path is not None and manifest_written and not restore_errors:
                cleanup_paths.add(manifest_path)
            for path in sorted(
                cleanup_paths,
                key=lambda item: len(item.parts),
                reverse=True,
            ):
                try:
                    if path.is_symlink() or path.is_file():
                        path.unlink()
                except OSError as cleanup_error:
                    cleanup_errors.append(f"{path}: {cleanup_error}")
            for directory in sorted(
                created_dirs,
                key=lambda item: len(item.parts),
                reverse=True,
            ):
                if any(
                    directory == path or directory in path.parents
                    for path in preserved_evidence
                ):
                    continue
                try:
                    directory.rmdir()
                except OSError as cleanup_error:
                    try:
                        nonempty = directory.exists() and any(directory.iterdir())
                    except OSError as inspect_error:
                        cleanup_errors.append(f"{directory}: {inspect_error}")
                        continue
                    cleanup_errors.append(
                        f"{directory}: "
                        + (
                            "not empty after cleanup"
                            if nonempty
                            else str(cleanup_error)
                        )
                    )
            if restore_errors:
                evidence = ", ".join(
                    str(path) for path in sorted(preserved_evidence)
                )
                raise core.ApplyError(
                    f"{error}; transactional restoration incomplete: "
                    f"{'; '.join(restore_errors)}; recovery evidence preserved at "
                    f"{evidence or backup_root}"
                ) from error
            if cleanup_errors:
                raise core.ApplyError(
                    f"{error}; project changes were restored but cleanup was incomplete: "
                    f"{'; '.join(cleanup_errors)}"
                ) from error
            if isinstance(error, core.ApplyError):
                raise
            raise core.ApplyError(
                f"apply failed and was rolled back: {error}"
            ) from error
        finally:
            core._ACTIVE_OWNED_WRITES.reset(owned_write_token)

    core._ACTIVE_OWNED_WRITES.reset(owned_write_token)
    return ApplyResult(
        report=report,
        manifest_path=manifest_path,
        added_paths=[item["path"] for item in created_entries],
        merged_paths=[item["path"] for item in merged_entries],
        proposals=report.proposals,
        recorded_directories=[
            item["path"] for item in required_directories if item["was_missing"]
        ],
    )


__all__ = ["ApplyResult", "apply_project"]
