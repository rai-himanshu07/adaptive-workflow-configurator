#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/workflow-configurator"
CONFIG_FILE="$CONFIG_DIR/python-interpreter"
ICON_NAME="applications-development"
DESKTOP_FILE="$APP_DIR/adaptive-workflow-configurator.desktop"
LEGACY_DESKTOP_FILE="$APP_DIR/template-gpt-workflow-configurator.desktop"

if ! selected_python="$("$ROOT/launch-workflow-configurator.sh" --print-interpreter)"; then
  exit 1
fi

mkdir -p "$APP_DIR" "$CONFIG_DIR"
if [[ -L "$CONFIG_FILE" ]]; then
  printf 'Refusing symlink interpreter configuration: %s\n' "$CONFIG_FILE" >&2
  exit 1
fi
temporary="$(mktemp "$CONFIG_DIR/.python-interpreter.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
printf '%s\n' "$selected_python" >"$temporary"
chmod 0600 "$temporary"
mv -- "$temporary" "$CONFIG_FILE"
trap - EXIT

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Workflow Configurator
Comment=Safely configure workflow_configurator for new or existing projects
Exec=$ROOT/launch-workflow-configurator.sh
Icon=$ICON_NAME
Terminal=false
Categories=Development;Utility;
StartupNotify=true
Path=$ROOT
EOF
chmod 0644 "$DESKTOP_FILE"
rm -f -- "$LEGACY_DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

message="Application launcher installed.\n\nPython: $selected_python\n\nTo change environments, activate the new environment or set WORKFLOW_CONFIGURATOR_PYTHON, then run this installer again."
if [[ "${WORKFLOW_CONFIGURATOR_NO_DIALOG:-}" != "1" ]] && command -v zenity >/dev/null 2>&1; then
  zenity --info --title="Workflow Configurator" --width=560 --text="$message"
else
  printf 'Installed: %s\nPython: %s\n' "$DESKTOP_FILE" "$selected_python"
fi
