"""Passive apply manifest serialization for manual recovery guidance."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
MANIFESTS_DIRECTORY = ".workflow_configurator/manifests"
BACKUPS_DIRECTORY = ".workflow_configurator/backups"
LEGACY_MANIFESTS_DIRECTORY = ".template_gpt/manifests"
LEGACY_BACKUPS_DIRECTORY = ".template_gpt/backups"


class ManifestError(ValueError):
    """Raised when a passive apply manifest cannot be read."""


def new_id() -> str:
    return (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid.uuid4().hex[:8]
    )


def build(
    *,
    target: Path,
    config: Mapping[str, Any],
    created_files: Sequence[Mapping[str, Any]],
    safe_merges: Sequence[Mapping[str, Any]],
    proposals: Sequence[Mapping[str, Any]],
    required_directories: Sequence[Mapping[str, Any]],
    manifest_id: str,
) -> dict[str, Any]:
    target = target.resolve(strict=False)
    target_stat = target.stat()
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "target": str(target),
        "target_identity": {
            "device": target_stat.st_dev,
            "inode": target_stat.st_ino,
        },
        "config": dict(config),
        "created_files": [dict(item) for item in created_files],
        "safe_merges": [dict(item) for item in safe_merges],
        "proposals": [dict(item) for item in proposals],
        "required_directories": [dict(item) for item in required_directories],
        "recovery_policy": "manual-only",
    }


def load(path: Path | str) -> dict[str, Any]:
    path = Path(path).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"manifest is unreadable or malformed: {path}: {error}") from error
    if not isinstance(data, dict):
        raise ManifestError(f"manifest root must be an object: {path}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported manifest schema in {path}; re-run apply to create a current manifest"
        )
    return data


__all__ = [
    "BACKUPS_DIRECTORY",
    "LEGACY_BACKUPS_DIRECTORY",
    "LEGACY_MANIFESTS_DIRECTORY",
    "MANIFESTS_DIRECTORY",
    "ManifestError",
    "SCHEMA_VERSION",
    "build",
    "load",
    "new_id",
]
