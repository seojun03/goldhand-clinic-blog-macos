#!/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd -P)"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
MANAGED_PYTHON="$CODEX_ROOT/state/goldhand-clinic-blog/bin/python3"
SETUP_SCRIPT="$ROOT/plugins/goldhand-clinic-blog/skills/goldhand-clinic-blog/scripts/setup_image_host.py"

if [ ! -f "$SETUP_SCRIPT" ]; then
  printf '\nThe Goldhand image setup script is missing. Run the Mac installer again.\n' >&2
  exit 1
fi

if [ -x "$MANAGED_PYTHON" ]; then
  PYTHON="$MANAGED_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf '\nThe managed Python runtime is missing. Run the Mac installer again.\n' >&2
  exit 1
fi

export PATH="$CODEX_ROOT/state/goldhand-clinic-blog/bin:$PATH"
"$PYTHON" "$SETUP_SCRIPT"
printf '\nAUTOMATIC IMAGE SETUP COMPLETE\n'
if [ "${GOLDHANDBLOG_SKIP_PAUSE:-0}" != "1" ] && [ -t 0 ]; then
  printf '\nPress Return to close this window.'
  IFS= read -r _ || true
fi
