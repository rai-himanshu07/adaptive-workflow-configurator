#!/usr/bin/env python3
"""Create an atomic, provenance-rich experiment run directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEPENDENCY_FILES = (
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "pdm.lock",
    "requirements.txt",
    "environment.yml",
    "environment.yaml",
    "conda-lock.yml",
    "conda-lock.yaml",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"data path must not be a symbolic link: {path}")
    if path.is_file():
        return sha256_file(path)
    if not path.is_dir():
        raise ValueError(f"data path is neither a file nor directory: {path}")

    digest = hashlib.sha256()
    candidates = sorted(path.rglob("*"))
    symlinks = [candidate for candidate in candidates if candidate.is_symlink()]
    if symlinks:
        raise ValueError(f"data directory contains a symbolic link: {symlinks[0]}")
    files = [candidate for candidate in candidates if candidate.is_file()]
    if not files:
        raise ValueError(f"data directory contains no files: {path}")
    for candidate in files:
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(candidate)))
    return digest.hexdigest()


def git_output(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_metadata() -> dict[str, object]:
    status = git_output("status", "--porcelain")
    diff = git_output("diff", "--binary", "HEAD")
    return {
        "sha": git_output("rev-parse", "HEAD"),
        "branch": git_output("branch", "--show-current"),
        "dirty": None if status is None else bool(status),
        "diff_sha256": None if diff is None else hashlib.sha256(diff.encode("utf-8")).hexdigest(),
    }


def dependency_metadata(root: Path) -> list[dict[str, str]]:
    metadata = []
    for name in DEPENDENCY_FILES:
        path = root / name
        if path.is_file():
            metadata.append({"path": name, "sha256": sha256_file(path)})
    return metadata


def provenance_fingerprint(
    *,
    name: str,
    seed: int,
    config_sha256: str,
    data_version: str | None,
    data_inputs: list[dict[str, str]],
    git: dict[str, object],
    dependencies: list[dict[str, str]],
) -> str:
    """Hash reproducibility inputs without machine-specific absolute paths."""
    payload = {
        "name": name,
        "seed": seed,
        "config_sha256": config_sha256,
        "data_version": data_version,
        "data_sha256": sorted(item["sha256"] for item in data_inputs),
        "git_sha": git.get("sha"),
        "git_diff_sha256": git.get("diff_sha256"),
        "dependencies": sorted(
            ({"path": item["path"], "sha256": item["sha256"]} for item in dependencies),
            key=lambda item: item["path"],
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="short experiment name")
    parser.add_argument("--config", required=True, type=Path, help="configuration file to freeze")
    parser.add_argument("--data", action="append", type=Path, default=[], help="input file or directory; repeat as needed")
    parser.add_argument("--data-version", help="stable external dataset or snapshot identifier")
    parser.add_argument(
        "--allow-external-data",
        action="store_true",
        help="allow --data paths outside the project root; validation later requires --allow-data-root",
    )
    parser.add_argument("--baseline-metrics", type=Path, help="explicit baseline metrics file")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--artifacts-root", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path.cwd().resolve()
    config = args.config.expanduser().resolve()
    if not config.is_file():
        raise SystemExit(f"config not found: {args.config}")
    if not args.data and not args.data_version:
        raise SystemExit("identify the dataset with --data or --data-version")

    data_paths = [path.expanduser().resolve() for path in args.data]
    missing_data = [path for path in data_paths if not path.exists()]
    if missing_data:
        raise SystemExit(f"data path not found: {missing_data[0]}")
    external_data = []
    for path in data_paths:
        try:
            path.relative_to(project_root)
        except ValueError:
            external_data.append(path)
    if external_data and not args.allow_external_data:
        raise SystemExit(
            f"data path is outside the project root: {external_data[0]} "
            "(pass --allow-external-data after reviewing the path)"
        )

    baseline = args.baseline_metrics.expanduser().resolve() if args.baseline_metrics else None
    if baseline is not None and not baseline.is_file():
        raise SystemExit(f"baseline metrics not found: {args.baseline_metrics}")

    slug = re.sub(r"[^a-z0-9]+", "-", args.name.lower()).strip("-")
    if not slug:
        raise SystemExit("experiment name must contain at least one letter or number")

    created = datetime.now(timezone.utc)
    run_id = f"{created.strftime('%Y%m%dT%H%M%SZ')}-{slug}-{uuid.uuid4().hex[:8]}"
    artifacts_root = args.artifacts_root.expanduser().resolve()
    run_dir = artifacts_root / run_id
    staging_dir = artifacts_root / f".{run_id}.tmp"
    frozen_name = f"config{config.suffix.lower()}" if config.suffix else "config"

    data_metadata = [
        {"path": str(path), "sha256": sha256_path(path)} for path in data_paths
    ]
    baseline_metadata = (
        {"path": str(baseline), "sha256": sha256_file(baseline)}
        if baseline is not None
        else None
    )
    config_sha256 = sha256_file(config)
    git = git_metadata()
    dependencies = dependency_metadata(project_root)
    metadata = {
        "schema_version": 2,
        "run_id": run_id,
        "created_utc": created.isoformat(timespec="seconds"),
        "name": slug,
        "seed": args.seed,
        "frozen_config": frozen_name,
        "source_config": str(config),
        "config_sha256": config_sha256,
        "data_version": args.data_version,
        "data_inputs": data_metadata,
        "baseline_metrics": baseline_metadata,
        "git": git,
        "dependencies": dependencies,
        "provenance_fingerprint": provenance_fingerprint(
            name=slug,
            seed=args.seed,
            config_sha256=config_sha256,
            data_version=args.data_version,
            data_inputs=data_metadata,
            git=git,
            dependencies=dependencies,
        ),
        "runtime": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
    }

    artifacts_root.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir()
    try:
        shutil.copy2(config, staging_dir / frozen_name)
        (staging_dir / "meta.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging_dir / "metrics.jsonl").write_text("", encoding="utf-8")
        staging_dir.rename(run_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    print(f"run directory: {run_dir}")
    print(f"frozen config: {run_dir / frozen_name}")
    print(f"metadata: {run_dir / 'meta.json'}")
    print(f"metrics: {run_dir / 'metrics.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
