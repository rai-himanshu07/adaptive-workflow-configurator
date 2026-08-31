---
name: Python Engineering
description: Python implementation, dependency, validation, typing, logging, and pytest conventions.
applyTo: '**/*.py'
---

# Python Engineering

- Use exactly one environment manager per project; never mix managers within a
  project. Choose deterministically:
  1. Existing project: `environment.yml`/`conda-lock.yml` means Conda;
    `uv.lock` or uv-configured `pyproject.toml` means uv. If both exist, stop
    and ask which declaration is authoritative.
  2. New ML/data project: default to Miniforge/Conda with Python 3.12. Commit
    `environment.yml`; put PyPI-only dependencies in its `pip:` section.
  3. New pure-Python tool or CLI: uv is acceptable. Commit `pyproject.toml` and
    `uv.lock`; use `uv sync`, `uv add`, and `uv run`.
  Record the chosen manager, environment name, and setup/activation commands in
  `AGENTS.md`.
- Do not install dependencies with ad-hoc `pip install` commands. Update the
  declared project metadata and lockfile.
- Use type hints on public boundaries and where they prevent ambiguous data flow.
- Use `pathlib.Path` for filesystem paths and explicit encodings for text files.
- Use module loggers in library code; reserve `print` for intentional CLI output.
- Raise specific exceptions with actionable context. Never use a bare `except`.
- Do not use `assert` for input, data, or runtime validation because optimized
  Python removes assertions.
- Prefer typed models or dataclasses when structured data crosses module
  boundaries; do not replace a simple local mapping without a concrete benefit.
- Add dependencies through the project's declared package manager and update its
  lockfile. Do not add packages solely to avoid a small standard-library solution.
- Tests must be deterministic, isolated from real networks and production data,
  and focused on observable behavior.
