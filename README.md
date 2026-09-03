# Adaptive Workflow Configurator

A local-first desktop and command-line configurator for creating proportional,
reviewable GitHub Copilot workflows in new or existing repositories.

The configurator analyzes a project, recommends a minimal workflow surface,
previews every proposed change, and applies only missing files or documented
safe merges. Existing user-owned files remain review-only proposals.

## Highlights

- Adaptive minimal, standard, and governed workflow surfaces
- Native PySide6 desktop interface with readable, color-coded diffs
- Preview-gated additive Apply with no automatic overwrite or deletion
- Explicit project proposal review and manual merge workflow
- Review-gated Awesome Copilot metadata updates and selected-asset inspection
- Redacted MCP configuration auditing
- Current versus safe-post-Apply context-footprint proxies
- Policy-aware MemPalace and code-graph continuity summaries
- Project-scoped memory and code-intelligence guidance
- User-level Linux and Windows launchers that require no administrator access
- Cross-platform launcher contracts covered by the local test suite

## Requirements

- Python 3.10 or newer
- PySide6 6.11.1 for the desktop interface

Install the optional GUI dependency in your chosen environment:

```bash
python -m pip install -r workflow_configurator/requirements-gui.txt
```

## Run

Desktop interface:

```bash
python workflow_configurator/install.py --gui /path/to/project
```

Read-only CLI preview:

```bash
python workflow_configurator/install.py /path/to/project \
  --workflow existing \
  --preview
```

### Linux launcher

```bash
./install-workflow-configurator-launcher.sh
```

### Windows launcher

```powershell
.\install-workflow-configurator-launcher.ps1
```

Both installers are user-scoped. The Windows installer writes only to the
current user's LocalAppData, Start Menu, and optionally Desktop; it does not
request elevation, modify PATH or the registry, or install services.

## Safety model

1. Analyze is read-only.
2. Preview displays exact intended actions and diffs.
3. Apply revalidates the target and current hashes.
4. Only missing files and approved safe merges are written.
5. Conflicts remain untouched proposals.
6. Writes use containment, symlink, collision, and transactional safeguards.
7. Recovery is manual from passive manifests and exact safe-merge backups.

Repository discovery supports recommendations and maintenance metrics but is not
an Apply authorization boundary. Git projects use tracked plus non-ignored
relevant files; non-Git projects use a bounded fallback scan. Every intended
destination is validated independently.

Analyze and Preview report UTF-8 bytes and physical lines for always-on,
path-specific, and on-demand workflow context, plus MCP counts, handoff/plan
size, searchable history, and exact duplicate instruction blocks. These are
deterministic context proxies, not exact model-token forecasts.

## Documentation

- [Configurator guide](workflow_configurator/docs/CONFIGURATOR.md)
- [Developer AI workflow guide](AI_WORKFLOW_GUIDE_2026.md)
- [Package reference](workflow_configurator/README.md)

## Validation

```bash
QT_QPA_PLATFORM=offscreen \
python -m unittest discover -s workflow_configurator/tests

python workflow_configurator/gui.py --headless-smoke
```

## License

Licensed under the [MIT License](LICENSE).
