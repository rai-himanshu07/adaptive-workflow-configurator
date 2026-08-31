#!/usr/bin/env python3
"""Append, validate, compare, and register reproducible experiment results."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


REQUIRED_METRIC_FIELDS = {
    "metric",
    "value",
    "split",
    "step",
    "timestamp",
    "sample_count",
}
REGISTRY_HEADER = (
    "# Experiment Registry\n\n"
    "Record accepted evidence here; keep large artifacts outside Git.\n\n"
    "| Run ID | Data version | Config | Key result | Baseline | Decision |\n"
    "|---|---|---|---|---|---|\n"
)


class ExperimentError(ValueError):
    """Raised when experiment evidence violates the file contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_symlink():
        raise ExperimentError(f"data path must not be a symbolic link: {path}")
    if path.is_file():
        return sha256_file(path)
    if not path.is_dir():
        raise ExperimentError(f"data path is neither a file nor directory: {path}")
    digest = hashlib.sha256()
    candidates = sorted(path.rglob("*"))
    symlinks = [candidate for candidate in candidates if candidate.is_symlink()]
    if symlinks:
        raise ExperimentError(f"data directory contains a symbolic link: {symlinks[0]}")
    files = [candidate for candidate in candidates if candidate.is_file()]
    if not files:
        raise ExperimentError(f"data directory contains no files: {path}")
    for candidate in files:
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(candidate)))
    return digest.hexdigest()


def metadata_fingerprint(metadata: dict[str, Any]) -> str:
    git = metadata.get("git") if isinstance(metadata.get("git"), dict) else {}
    data_inputs = metadata.get("data_inputs") if isinstance(metadata.get("data_inputs"), list) else []
    dependencies = metadata.get("dependencies") if isinstance(metadata.get("dependencies"), list) else []
    payload = {
        "name": metadata.get("name"),
        "seed": metadata.get("seed"),
        "config_sha256": metadata.get("config_sha256"),
        "data_version": metadata.get("data_version"),
        "data_sha256": sorted(
            item.get("sha256") for item in data_inputs if isinstance(item, dict) and isinstance(item.get("sha256"), str)
        ),
        "git_sha": git.get("sha"),
        "git_diff_sha256": git.get("diff_sha256"),
        "dependencies": sorted(
            (
                {"path": item.get("path"), "sha256": item.get("sha256")}
                for item in dependencies
                if isinstance(item, dict)
            ),
            key=lambda item: str(item["path"]),
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_timestamp(value: Any, *, context: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ExperimentError(f"{context}: timestamp must be a non-empty ISO 8601 string")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ExperimentError(f"{context}: invalid timestamp {value!r}") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExperimentError(f"{context}: timestamp must be timezone-aware UTC")
    return parsed


def validate_record(record: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ExperimentError(f"{context}: metric record must be a JSON object")
    missing = sorted(REQUIRED_METRIC_FIELDS.difference(record))
    if missing:
        raise ExperimentError(f"{context}: missing fields: {', '.join(missing)}")
    if not isinstance(record["metric"], str) or not record["metric"].strip():
        raise ExperimentError(f"{context}: metric must be a non-empty string")
    value = record["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ExperimentError(f"{context}: value must be a finite number")
    if not isinstance(record["split"], str) or not record["split"].strip():
        raise ExperimentError(f"{context}: split must be a non-empty string")
    step = record["step"]
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ExperimentError(f"{context}: step must be a non-negative integer")
    sample_count = record["sample_count"]
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count <= 0:
        raise ExperimentError(f"{context}: sample_count must be a positive integer")
    parse_timestamp(record["timestamp"], context=context)
    if "fold" in record:
        fold = record["fold"]
        if isinstance(fold, bool) or not isinstance(fold, (int, str)):
            raise ExperimentError(f"{context}: fold must be an integer or string")
        if isinstance(fold, int) and fold < 0:
            raise ExperimentError(f"{context}: integer fold must be non-negative")
        if isinstance(fold, str) and not fold.strip():
            raise ExperimentError(f"{context}: string fold must be non-empty")
    if "tags" in record and not isinstance(record["tags"], dict):
        raise ExperimentError(f"{context}: tags must be a JSON object")
    return record


def metric_key(record: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        record["metric"],
        record["split"],
        record["step"],
        str(record.get("fold", "")),
    )


def load_metrics(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ExperimentError(f"metrics file not found: {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ExperimentError(f"metrics file must not contain a UTF-8 byte order mark: {path}")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExperimentError(f"metrics file is not UTF-8: {path}") from error

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()
    previous_timestamp: datetime | None = None
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise ExperimentError(f"{path}:{line_number}: blank lines are not valid JSON Lines records")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ExperimentError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
        record = validate_record(record, context=f"{path}:{line_number}")
        key = metric_key(record)
        if key in seen:
            raise ExperimentError(f"{path}:{line_number}: duplicate metric/split/step/fold key: {key}")
        seen.add(key)
        timestamp = parse_timestamp(record["timestamp"], context=f"{path}:{line_number}")
        if previous_timestamp is not None and timestamp < previous_timestamp:
            raise ExperimentError(f"{path}:{line_number}: timestamps are not monotonic")
        previous_timestamp = timestamp
        records.append(record)
    return records


def load_metadata(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "meta.json"
    if not path.is_file():
        raise ExperimentError(f"metadata file not found: {path}")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExperimentError(f"invalid metadata JSON: {path}") from error
    if not isinstance(metadata, dict):
        raise ExperimentError(f"metadata must be a JSON object: {path}")
    return metadata


def inferred_project_root(run_dir: Path) -> Path:
    return run_dir.parent.parent if run_dir.parent.name == "artifacts" else run_dir.parent


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def allowed_data_roots(run_dir: Path, extra_roots: list[Path] | None) -> list[Path]:
    roots = [inferred_project_root(run_dir).resolve()]
    roots.extend(path.expanduser().resolve() for path in (extra_roots or []))
    return list(dict.fromkeys(roots))


def validate_run(
    run_dir: Path,
    extra_data_roots: list[Path] | None = None,
    *,
    verify_source_data: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    run_dir = run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        raise ExperimentError(f"run directory not found: {run_dir}")
    metadata = load_metadata(run_dir)
    required = {
        "schema_version",
        "run_id",
        "seed",
        "frozen_config",
        "config_sha256",
        "data_inputs",
        "data_version",
        "provenance_fingerprint",
    }
    missing = sorted(required.difference(metadata))
    if missing:
        raise ExperimentError(f"meta.json missing fields: {', '.join(missing)}")
    if metadata["run_id"] != run_dir.name:
        raise ExperimentError("meta.json run_id does not match the run directory name")
    fingerprint = metadata["provenance_fingerprint"]
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ExperimentError("meta.json provenance_fingerprint must be a SHA-256 hex digest")
    try:
        int(fingerprint, 16)
    except ValueError as error:
        raise ExperimentError("meta.json provenance_fingerprint is not hexadecimal") from error
    if metadata_fingerprint(metadata) != fingerprint:
        raise ExperimentError("meta.json provenance_fingerprint does not match recorded inputs")

    frozen_config = (run_dir / str(metadata["frozen_config"])).resolve()
    if not is_within(frozen_config, run_dir):
        raise ExperimentError("meta.json frozen_config points outside the run directory")
    if not frozen_config.is_file():
        raise ExperimentError(f"frozen config not found: {frozen_config}")
    if sha256_file(frozen_config) != metadata["config_sha256"]:
        raise ExperimentError("frozen config hash does not match meta.json")
    data_inputs = metadata["data_inputs"]
    if not isinstance(data_inputs, list):
        raise ExperimentError("meta.json data_inputs must be an array")
    if not data_inputs and not metadata["data_version"]:
        raise ExperimentError("meta.json must identify data by hash or data_version")

    warnings: list[str] = []
    permitted_roots = allowed_data_roots(run_dir, extra_data_roots)
    for item in data_inputs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise ExperimentError("every data_inputs item must contain path and sha256 strings")
        if not verify_source_data:
            continue
        source = Path(item["path"]).expanduser().resolve()
        if not source.exists():
            warnings.append(f"source data is unavailable for re-hashing: {source}")
        elif not any(is_within(source, root) for root in permitted_roots):
            roots = ", ".join(str(root) for root in permitted_roots)
            raise ExperimentError(
                f"source data is outside allowed roots: {source}; allowed: {roots}. "
                "Pass --allow-data-root only after reviewing the external path."
            )
        elif sha256_path(source) != item["sha256"]:
            raise ExperimentError(f"source data hash changed: {source}")

    records = load_metrics(run_dir / "metrics.jsonl")
    return metadata, records, warnings


@contextmanager
def exclusive_lock(target: Path) -> Iterator[None]:
    lock_path = target.with_name(f".{target.name}.lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ExperimentError(
            f"lock exists: {lock_path}; another writer may be active, or remove a verified stale lock"
        ) from error
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def command_append(args: argparse.Namespace) -> int:
    run_dir = args.run.expanduser().resolve()
    validate_run(run_dir)
    metrics_path = run_dir / "metrics.jsonl"
    tags: dict[str, str] = {}
    for item in args.tag:
        if "=" not in item:
            raise ExperimentError(f"tag must use KEY=VALUE: {item!r}")
        key, value = item.split("=", 1)
        if not key.strip():
            raise ExperimentError("tag key must not be empty")
        tags[key.strip()] = value
    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    record: dict[str, Any] = {
        "metric": args.metric,
        "value": args.value,
        "split": args.split,
        "step": args.step,
        "timestamp": timestamp,
        "sample_count": args.sample_count,
    }
    if args.fold is not None:
        record["fold"] = args.fold
    if tags:
        record["tags"] = tags
    validate_record(record, context="new record")

    with exclusive_lock(metrics_path):
        existing = load_metrics(metrics_path)
        if any(metric_key(item) == metric_key(record) for item in existing):
            raise ExperimentError(f"metric key already exists: {metric_key(record)}")
        if existing:
            last_timestamp = parse_timestamp(existing[-1]["timestamp"], context="last record")
            new_timestamp = parse_timestamp(record["timestamp"], context="new record")
            if new_timestamp < last_timestamp:
                raise ExperimentError("new timestamp precedes the final metrics record")
        line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        with metrics_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
    print(json.dumps(record, sort_keys=True))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    metadata, records, warnings = validate_run(
        args.run,
        args.allow_data_root,
        verify_source_data=args.verify_source_data,
    )
    result = {
        "run_id": metadata["run_id"],
        "provenance_fingerprint": metadata["provenance_fingerprint"],
        "metric_records": len(records),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"valid run: {result['run_id']}")
        print(f"provenance fingerprint: {result['provenance_fingerprint']}")
        print(f"metric records: {result['metric_records']}")
        for warning in warnings:
            print(f"warning: {warning}")
    return 0


def matching_records(records: list[dict[str, Any]], metric: str, split: str) -> list[dict[str, Any]]:
    matches = [record for record in records if record["metric"] == metric and record["split"] == split]
    if not matches:
        raise ExperimentError(f"no records match metric={metric!r}, split={split!r}")
    return matches


def aggregate(records: list[dict[str, Any]], mode: str) -> float:
    if mode == "latest":
        latest = max(records, key=lambda item: (parse_timestamp(item["timestamp"], context="metric"), item["step"]))
        return float(latest["value"])
    if mode == "mean-final-folds":
        if any("fold" not in record for record in records):
            raise ExperimentError("mean-final-folds requires fold on every matching record")
        final_by_fold: dict[str, dict[str, Any]] = {}
        for record in records:
            fold = str(record["fold"])
            current = final_by_fold.get(fold)
            if current is None or (
                record["step"],
                parse_timestamp(record["timestamp"], context="metric"),
            ) > (
                current["step"],
                parse_timestamp(current["timestamp"], context="metric"),
            ):
                final_by_fold[fold] = record
        return statistics.fmean(float(record["value"]) for record in final_by_fold.values())
    raise ExperimentError(f"unknown aggregation: {mode}")


def metrics_for_source(
    path: Path,
    extra_data_roots: list[Path] | None,
    verify_source_data: bool,
) -> tuple[str, list[dict[str, Any]]]:
    path = path.expanduser().resolve()
    if path.is_dir():
        metadata, records, _ = validate_run(
            path,
            extra_data_roots,
            verify_source_data=verify_source_data,
        )
        return str(metadata["run_id"]), records
    return str(path), load_metrics(path)


def command_compare(args: argparse.Namespace) -> int:
    candidate_name, candidate_records = metrics_for_source(
        args.candidate,
        args.allow_data_root,
        args.verify_source_data,
    )
    baseline_name, baseline_records = metrics_for_source(
        args.baseline,
        args.allow_data_root,
        args.verify_source_data,
    )
    candidate_value = aggregate(matching_records(candidate_records, args.metric, args.split), args.aggregation)
    baseline_value = aggregate(matching_records(baseline_records, args.metric, args.split), args.aggregation)
    regression = candidate_value - baseline_value if args.direction == "lower" else baseline_value - candidate_value

    threshold_value = (
        args.max_regression_percent
        if args.max_regression_percent is not None
        else args.max_regression_absolute
    )
    if threshold_value is None or not math.isfinite(threshold_value) or threshold_value < 0:
        raise ExperimentError("regression threshold must be a finite non-negative number")
    if args.max_regression_percent is not None:
        if baseline_value == 0:
            raise ExperimentError("percentage threshold is undefined for a zero baseline; use --max-regression-absolute")
        regression_measure = regression / abs(baseline_value) * 100.0
        threshold = args.max_regression_percent
        threshold_kind = "percent"
    else:
        regression_measure = regression
        threshold = args.max_regression_absolute
        threshold_kind = "absolute"
    passed = regression_measure <= threshold
    result = {
        "aggregation": args.aggregation,
        "baseline": baseline_name,
        "baseline_value": baseline_value,
        "candidate": candidate_name,
        "candidate_value": candidate_value,
        "direction": args.direction,
        "metric": args.metric,
        "passed": passed,
        "regression": regression,
        "regression_measure": regression_measure,
        "split": args.split,
        "threshold": threshold,
        "threshold_kind": threshold_kind,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        verdict = "PASS" if passed else "REGRESSION"
        print(f"{verdict}: {args.metric} on {args.split}")
        print(f"baseline={baseline_value:g} candidate={candidate_value:g}")
        print(f"regression={regression_measure:g} threshold={threshold:g} ({threshold_kind})")
    return 0 if passed else 4


def escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def command_register(args: argparse.Namespace) -> int:
    run_dir = args.run.expanduser().resolve()
    metadata, _, _ = validate_run(
        run_dir,
        args.allow_data_root,
        verify_source_data=args.verify_source_data,
    )
    registry = args.registry.expanduser().resolve()
    data_version = metadata.get("data_version") or ",".join(
        str(item.get("sha256", ""))[:12] for item in metadata.get("data_inputs", [])
    )
    config = f"{metadata['frozen_config']}@{str(metadata['config_sha256'])[:12]}"
    row = (
        f"| {escape_table(metadata['run_id'])} | {escape_table(data_version)} | "
        f"{escape_table(config)} | {escape_table(args.key_result)} | "
        f"{escape_table(args.baseline)} | {escape_table(args.decision)} |\n"
    )
    with exclusive_lock(registry):
        content = registry.read_text(encoding="utf-8") if registry.exists() else REGISTRY_HEADER
        if "| Run ID | Data version | Config | Key result | Baseline | Decision |" not in content:
            raise ExperimentError(f"registry does not contain the expected table header: {registry}")
        existing_id = f"| {metadata['run_id']} |"
        if existing_id in content:
            print(f"already registered: {metadata['run_id']}")
            return 0
        if content and not content.endswith("\n"):
            content += "\n"
        atomic_write_text(registry, content + row)
    print(f"registered: {metadata['run_id']} -> {registry}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    append = subparsers.add_parser("append", help="append one validated metric record")
    append.add_argument("--run", required=True, type=Path)
    append.add_argument("--metric", required=True)
    append.add_argument("--value", required=True, type=float)
    append.add_argument("--split", required=True)
    append.add_argument("--step", required=True, type=int)
    append.add_argument("--sample-count", required=True, type=int)
    append.add_argument("--fold")
    append.add_argument("--timestamp")
    append.add_argument("--tag", action="append", default=[], help="KEY=VALUE; repeat as needed")
    append.set_defaults(handler=command_append)

    validate = subparsers.add_parser("validate", help="validate run provenance and metrics")
    validate.add_argument("--run", required=True, type=Path)
    validate.add_argument("--json", action="store_true")
    validate.add_argument("--allow-data-root", action="append", type=Path, default=[])
    validate.add_argument("--verify-source-data", action="store_true")
    validate.set_defaults(handler=command_validate)

    compare = subparsers.add_parser("compare", help="compare explicit candidate and baseline evidence")
    compare.add_argument("--candidate", required=True, type=Path)
    compare.add_argument("--baseline", required=True, type=Path)
    compare.add_argument("--metric", required=True)
    compare.add_argument("--split", required=True)
    compare.add_argument("--direction", required=True, choices=("lower", "higher"))
    compare.add_argument("--aggregation", required=True, choices=("latest", "mean-final-folds"))
    threshold = compare.add_mutually_exclusive_group(required=True)
    threshold.add_argument("--max-regression-percent", type=float)
    threshold.add_argument("--max-regression-absolute", type=float)
    compare.add_argument("--json", action="store_true")
    compare.add_argument("--allow-data-root", action="append", type=Path, default=[])
    compare.add_argument("--verify-source-data", action="store_true")
    compare.set_defaults(handler=command_compare)

    register = subparsers.add_parser("register", help="idempotently append a run to the experiment registry")
    register.add_argument("--run", required=True, type=Path)
    register.add_argument("--registry", type=Path, default=Path("docs/experiments.md"))
    register.add_argument("--key-result", required=True)
    register.add_argument("--baseline", required=True)
    register.add_argument(
        "--decision",
        required=True,
        choices=("accepted", "rejected", "inconclusive", "candidate"),
    )
    register.add_argument("--allow-data-root", action="append", type=Path, default=[])
    register.add_argument("--verify-source-data", action="store_true")
    register.set_defaults(handler=command_register)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except (ExperimentError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())