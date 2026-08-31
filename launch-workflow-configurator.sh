#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/workflow-configurator/python-interpreter"
LEGACY_CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/template-gpt/python-interpreter"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/workflow-configurator"
LOG_FILE="$LOG_DIR/configurator.log"

show_error() {
  local message="$1"
  message="${message//\\n/$'\n'}"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="Workflow Configurator" --width=560 --text="$message"
  else
    printf 'Workflow Configurator: %s\n' "$message" >&2
  fi
}

python_command=()
selection_source=""

use_executable() {
  local candidate="$1"
  local source="$2"
  if [[ -x "$candidate" ]]; then
    python_command=("$candidate")
    selection_source="$source"
    return 0
  fi
  return 1
}

if [[ -n "${WORKFLOW_CONFIGURATOR_PYTHON:-}" ]]; then
  if ! use_executable "$WORKFLOW_CONFIGURATOR_PYTHON" "WORKFLOW_CONFIGURATOR_PYTHON"; then
    show_error "The configured Python executable is unavailable:\n$WORKFLOW_CONFIGURATOR_PYTHON"
    exit 1
  fi
elif [[ -n "${VIRTUAL_ENV:-}" ]] && use_executable "$VIRTUAL_ENV/bin/python" "active virtual environment"; then
  :
elif [[ -n "${CONDA_PREFIX:-}" ]] && use_executable "$CONDA_PREFIX/bin/python" "active Conda environment"; then
  :
elif use_executable "$ROOT/.venv/bin/python" "repository .venv"; then
  :
elif use_executable "$ROOT/.conda/bin/python" "repository .conda"; then
  :
elif [[ -n "${WORKFLOW_CONFIGURATOR_ENV:-}" ]]; then
  conda_bin="${CONDA_EXE:-}"
  if [[ -z "$conda_bin" ]]; then
    conda_bin="$(command -v conda 2>/dev/null || true)"
  fi
  if [[ -z "$conda_bin" || ! -x "$conda_bin" ]]; then
    show_error "WORKFLOW_CONFIGURATOR_ENV is set, but Conda is unavailable.\n\nSet WORKFLOW_CONFIGURATOR_PYTHON to an executable path instead."
    exit 1
  fi
  python_command=("$conda_bin" run --no-capture-output -n "$WORKFLOW_CONFIGURATOR_ENV" python)
  selection_source="explicit Conda environment"
elif [[ -r "$CONFIG_FILE" ]]; then
  IFS= read -r saved_python <"$CONFIG_FILE"
  if ! use_executable "$saved_python" "saved desktop choice"; then
    show_error "The saved Python executable is unavailable:\n$saved_python\n\nRe-run install-workflow-configurator-launcher.sh from the environment you want to use."
    exit 1
  fi
elif [[ -r "$LEGACY_CONFIG_FILE" ]]; then
  IFS= read -r saved_python <"$LEGACY_CONFIG_FILE"
  if ! use_executable "$saved_python" "legacy saved desktop choice"; then
    show_error "The legacy saved Python executable is unavailable:\n$saved_python\n\nRe-run install-workflow-configurator-launcher.sh from the environment you want to use."
    exit 1
  fi
elif command -v python3 >/dev/null 2>&1; then
  python_command=("$(command -v python3)")
  selection_source="system python3"
elif command -v python >/dev/null 2>&1; then
  python_command=("$(command -v python)")
  selection_source="system python"
else
  show_error "No Python interpreter was found.\n\nActivate an environment or set WORKFLOW_CONFIGURATOR_PYTHON to its Python executable."
  exit 1
fi

if ! resolved_python="$("${python_command[@]}" -c 'import sys; print(sys.executable)' 2>/dev/null)"; then
  show_error "The selected Python command could not start (source: $selection_source)."
  exit 1
fi

if ! "$resolved_python" -c "import PySide6" >/dev/null 2>&1; then
  show_error "PySide6 is not installed in the selected environment.\n\nPython: $resolved_python\nSource: $selection_source\n\nInstall workflow_configurator/requirements-gui.txt in that environment, or select another interpreter with WORKFLOW_CONFIGURATOR_PYTHON."
  exit 1
fi

if [[ "${1:-}" == "--print-interpreter" ]]; then
  printf '%s\n' "$resolved_python"
  exit 0
fi

mkdir -p "$LOG_DIR"
cd "$ROOT"

if [[ "${1:-}" == "--headless-smoke" ]]; then
  exec "$resolved_python" "$ROOT/workflow_configurator/gui.py" \
    --headless-smoke "${2:-$ROOT}"
fi

TARGET="${1:-$ROOT}"
nohup "$resolved_python" "$ROOT/workflow_configurator/install.py" --gui "$TARGET" \
  >>"$LOG_FILE" 2>&1 &

disown 2>/dev/null || true
