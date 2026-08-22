#!/bin/bash
set -Eeuo pipefail

SOURCE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
PLUGIN_NAME="goldhand-clinic-blog"
MARKETPLACE_NAME="goldhand-clinic-macos"
PLUGIN_SELECTOR="$PLUGIN_NAME@$MARKETPLACE_NAME"
EDITABLE_ROOT="${GOLDHANDBLOG_MAC_EDITABLE_ROOT:-$HOME/GoldhandBlogMac}"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
STATE_ROOT="$CODEX_ROOT/state/goldhand-clinic-blog"
STATE_BIN="$STATE_ROOT/bin"
PYTHON_VENV="$STATE_ROOT/python-macos"
NODE_RUNTIME_ROOT="$STATE_ROOT/node-macos"
NPM_PREFIX="$STATE_ROOT/npm-macos"
RELEASE_STATE_NAME=".goldhand-clinic-blog-macos-managed-release"
RELEASE_STATE="$EDITABLE_ROOT/$RELEASE_STATE_NAME"
BACKUP_ROOT=""
REPLACED=0
INSTALL_COMMITTED=0
PYTHON=""
CODEX=""

log() {
  printf '\n[Goldhand Clinic Blog macOS installer] %s\n' "$1"
}

die() {
  printf '\n[INSTALLATION FAILED] %s\n' "$1" >&2
  exit 1
}

safe_remove_dir() {
  local target="${1:-}"
  [ -n "$target" ] || return 0
  [ -e "$target" ] || return 0
  case "$target" in
    "$EDITABLE_ROOT".installing.*|"$EDITABLE_ROOT".backup.*|"$EDITABLE_ROOT".failed.*|"$STATE_ROOT/python-macos"|"$STATE_ROOT/node-macos"/*|"${TMPDIR:-/tmp}"/*)
      /bin/rm -rf -- "$target" 2>/dev/null || true
      ;;
    *)
      printf '[Goldhand Clinic Blog macOS installer] Refused unsafe cleanup target: %s\n' "$target" >&2
      ;;
  esac
}

valid_python() {
  local candidate="${1:-}"
  [ -x "$candidate" ] || return 1
  "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

find_base_python() {
  local from_path=""
  from_path="$(command -v python3 2>/dev/null || true)"
  for candidate in \
    "${GOLDHANDBLOG_MAC_PYTHON:-}" \
    "$from_path" \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /usr/bin/python3; do
    if valid_python "$candidate"; then
      BASE_PYTHON="$candidate"
      return 0
    fi
  done
  return 1
}

install_private_python() {
  log "Python 3 is missing. Installing a private Python runtime for this plugin only."
  local bootstrap="$STATE_ROOT/bootstrap-bin"
  local installer=""
  /bin/mkdir -p "$bootstrap"
  installer="$(mktemp "${TMPDIR:-/tmp}/ghm-uv.XXXXXX")"
  curl -fsSL --retry 3 --connect-timeout 15 -o "$installer" https://astral.sh/uv/install.sh || die "Could not download the private Python bootstrapper."
  UV_INSTALL_DIR="$bootstrap" UV_NO_MODIFY_PATH=1 /bin/sh "$installer" >/dev/null || die "Could not install the private Python bootstrapper."
  /bin/rm -f -- "$installer" 2>/dev/null || true
  [ -x "$bootstrap/uv" ] || die "The private Python bootstrapper did not install correctly."
  "$bootstrap/uv" python install 3.12 >/dev/null || die "Could not install the private Python runtime."
  BASE_PYTHON="$("$bootstrap/uv" python find 3.12)"
  valid_python "$BASE_PYTHON" || die "The private Python runtime could not be executed."
}

ensure_python_runtime() {
  /bin/mkdir -p "$STATE_ROOT" "$STATE_BIN"
  if ! find_base_python; then
    install_private_python
  fi
  if ! valid_python "$PYTHON_VENV/bin/python3"; then
    log "Creating the plugin's isolated Python runtime."
    safe_remove_dir "$PYTHON_VENV"
    "$BASE_PYTHON" -m venv "$PYTHON_VENV" || die "Could not create the isolated Python runtime."
  fi
  PYTHON="$PYTHON_VENV/bin/python3"
  valid_python "$PYTHON" || die "The isolated Python runtime is not executable."
  log "Installing the plugin's pinned Python requirements."
  "$PYTHON" -m pip install --disable-pip-version-check --quiet --requirement "$SOURCE_ROOT/requirements-macos.txt" || die "Could not install the plugin's Python requirements."
  /bin/ln -sfn "$PYTHON" "$STATE_BIN/python3"
}

valid_node_pair() {
  local node_candidate="${1:-}"
  local npm_candidate="${2:-}"
  [ -x "$node_candidate" ] && [ -x "$npm_candidate" ] || return 1
  "$node_candidate" -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)' >/dev/null 2>&1 || return 1
  PATH="$(dirname "$node_candidate"):$PATH" "$npm_candidate" --version >/dev/null 2>&1
}

find_node_pair() {
  local path_node="$(command -v node 2>/dev/null || true)"
  local path_npm="$(command -v npm 2>/dev/null || true)"
  local directory=""
  if valid_node_pair "$path_node" "$path_npm"; then
    NODE_EXEC="$path_node"
    NPM_EXEC="$path_npm"
    return 0
  fi
  for directory in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin"; do
    if valid_node_pair "$directory/node" "$directory/npm"; then
      NODE_EXEC="$directory/node"
      NPM_EXEC="$directory/npm"
      return 0
    fi
  done
  return 1
}

install_private_node() {
  local machine_arch="$(uname -m)"
  local node_arch=""
  case "$machine_arch" in
    arm64) node_arch="arm64" ;;
    x86_64) node_arch="x64" ;;
    *) die "Unsupported Mac processor architecture: $machine_arch" ;;
  esac
  log "Node.js is missing. Installing a private Node.js LTS runtime for this plugin only."
  local index="$(mktemp "${TMPDIR:-/tmp}/ghm-node-index.XXXXXX")"
  curl -fsSL --retry 3 --connect-timeout 15 -o "$index" https://nodejs.org/dist/index.tab || die "Could not read the Node.js release index."
  local version="$(/usr/bin/awk -F '\t' -v target="osx-$node_arch-tar" 'NR > 1 && $10 != "-" && index($3, target) { print $1; exit }' "$index")"
  /bin/rm -f -- "$index" 2>/dev/null || true
  [ -n "$version" ] || die "Could not select a compatible Node.js LTS release."
  local archive="$(mktemp "${TMPDIR:-/tmp}/ghm-node.XXXXXX.tar.gz")"
  local unpack="$(mktemp -d "${TMPDIR:-/tmp}/ghm-node-x.XXXXXX")"
  curl -fL --retry 3 --connect-timeout 15 -o "$archive" "https://nodejs.org/dist/$version/node-$version-darwin-$node_arch.tar.gz" || die "Could not download Node.js $version."
  /usr/bin/tar -xzf "$archive" -C "$unpack" || die "Could not extract Node.js $version."
  local source="$unpack/node-$version-darwin-$node_arch"
  local destination="$NODE_RUNTIME_ROOT/node-$version-darwin-$node_arch"
  [ -d "$source" ] || die "The downloaded Node.js archive is incomplete."
  /bin/mkdir -p "$NODE_RUNTIME_ROOT"
  safe_remove_dir "$destination"
  /bin/mv "$source" "$destination"
  /bin/rm -f -- "$archive" 2>/dev/null || true
  safe_remove_dir "$unpack"
  NODE_EXEC="$destination/bin/node"
  NPM_EXEC="$destination/bin/npm"
  valid_node_pair "$NODE_EXEC" "$NPM_EXEC" || die "The private Node.js runtime could not be executed."
}

ensure_vercel_cli() {
  if ! find_node_pair; then
    install_private_node
  fi
  /bin/ln -sfn "$NODE_EXEC" "$STATE_BIN/node"
  /bin/ln -sfn "$NPM_EXEC" "$STATE_BIN/npm"
  if [ -x "$STATE_BIN/vercel" ] && "$STATE_BIN/vercel" --version >/dev/null 2>&1; then
    log "The managed Vercel CLI is ready."
    return 0
  fi
  log "Installing the managed Vercel CLI."
  /bin/mkdir -p "$NPM_PREFIX"
  PATH="$STATE_BIN:$PATH" NPM_CONFIG_PREFIX="$NPM_PREFIX" "$STATE_BIN/npm" install --global vercel --no-fund --no-audit >/dev/null || die "Could not install the Vercel CLI."
  [ -x "$NPM_PREFIX/bin/vercel" ] || die "The Vercel CLI installation is incomplete."
  {
    printf '%s\n' '#!/bin/sh'
    printf 'PATH="%s:$PATH"\n' "$STATE_BIN"
    printf '%s\n' 'export PATH'
    printf 'exec "%s" "$@"\n' "$NPM_PREFIX/bin/vercel"
  } > "$STATE_BIN/vercel"
  /bin/chmod 755 "$STATE_BIN/vercel"
  "$STATE_BIN/vercel" --version >/dev/null 2>&1 || die "The managed Vercel CLI could not be executed."
}

valid_codex() {
  local candidate="${1:-}"
  [ -x "$candidate" ] || return 1
  "$candidate" plugin --help >/dev/null 2>&1
}

find_codex() {
  local from_path="$(command -v codex 2>/dev/null || true)"
  for candidate in \
    "${GOLDHANDBLOG_CODEX_PATH:-}" \
    "$from_path" \
    /Applications/ChatGPT.app/Contents/Resources/codex \
    /Applications/Codex.app/Contents/Resources/codex \
    "$HOME/Applications/ChatGPT.app/Contents/Resources/codex" \
    "$HOME/Applications/Codex.app/Contents/Resources/codex" \
    "$HOME/.local/bin/codex" \
    /opt/homebrew/bin/codex \
    /usr/local/bin/codex; do
    if valid_codex "$candidate"; then
      CODEX="$candidate"
      return 0
    fi
  done
  return 1
}

ensure_codex() {
  if find_codex; then
    log "Found a functional Codex plugin command."
    return 0
  fi
  log "Installing the official Codex command-line tool."
  local installer="$(mktemp "${TMPDIR:-/tmp}/ghm-codex.XXXXXX")"
  curl -fsSL --retry 3 --connect-timeout 15 -o "$installer" https://chatgpt.com/codex/install.sh || die "Could not download the official Codex installer."
  /bin/bash "$installer" >/dev/null || die "The official Codex command-line tool could not be installed."
  /bin/rm -f -- "$installer" 2>/dev/null || true
  find_codex || die "A functional Codex plugin command was not found. Install or open ChatGPT, then run the Mac installer again."
}

test_plugin_tree() {
  local root="$1"
  [ -f "$root/.agents/plugins/marketplace.json" ] &&
  [ -f "$root/plugins/$PLUGIN_NAME/.codex-plugin/plugin.json" ] &&
  [ -f "$root/plugins/$PLUGIN_NAME/skills/$PLUGIN_NAME/SKILL.md" ] &&
  [ -f "$root/plugins/$PLUGIN_NAME/skills/$PLUGIN_NAME/scripts/setup_image_host.py" ] &&
  [ -f "$root/INSTALL-MAC.command" ] &&
  [ -f "$root/SETUP-IMAGES-MAC.command" ] &&
  [ -f "$root/install-from-download-macos.sh" ] &&
  [ -f "$root/scripts/update-macos.sh" ] &&
  [ -f "$root/scripts/validate_distribution.py" ] &&
  [ -f "$root/requirements-macos.txt" ] &&
  [ ! -e "$root/INSTALL-WINDOWS.cmd" ] &&
  [ ! -e "$root/SETUP-IMAGES-WINDOWS.cmd" ]
}

copy_managed_tree() {
  test_plugin_tree "$SOURCE_ROOT" || die "The complete macOS release was not extracted."
  if [ "$SOURCE_ROOT" = "$EDITABLE_ROOT" ]; then
    log "The managed macOS folder is already in place. Reconnecting it."
    return 0
  fi
  local parent="$(dirname "$EDITABLE_ROOT")"
  local staging="$EDITABLE_ROOT.installing.$$.${RANDOM:-0}"
  BACKUP_ROOT="$EDITABLE_ROOT.backup.$(date -u +%Y%m%d%H%M%S).$$"
  /bin/mkdir -p "$parent" "$staging"
  for directory in .agents plugins scripts; do
    [ -d "$SOURCE_ROOT/$directory" ] || die "The macOS release is missing $directory."
    /usr/bin/ditto "$SOURCE_ROOT/$directory" "$staging/$directory"
  done
  for file in README.md INSTALL-MAC.command SETUP-IMAGES-MAC.command install-from-download-macos.sh requirements-macos.txt; do
    [ -f "$SOURCE_ROOT/$file" ] || die "The macOS release is missing $file."
    /bin/cp -p "$SOURCE_ROOT/$file" "$staging/$file"
  done
  /bin/chmod 755 "$staging/INSTALL-MAC.command" "$staging/SETUP-IMAGES-MAC.command" "$staging/install-from-download-macos.sh" "$staging/scripts/update-macos.sh"
  test_plugin_tree "$staging" || die "The staged macOS plugin tree is incomplete."
  PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$staging/scripts/validate_distribution.py" >/dev/null || die "The staged macOS plugin tree failed validation."
  if [ -e "$EDITABLE_ROOT" ]; then
    /bin/mv "$EDITABLE_ROOT" "$BACKUP_ROOT"
  else
    BACKUP_ROOT=""
  fi
  if ! /bin/mv "$staging" "$EDITABLE_ROOT"; then
    if [ -n "$BACKUP_ROOT" ] && [ -e "$BACKUP_ROOT" ] && [ ! -e "$EDITABLE_ROOT" ]; then
      /bin/mv "$BACKUP_ROOT" "$EDITABLE_ROOT"
    fi
    die "Could not replace the managed macOS plugin folder."
  fi
  REPLACED=1
  log "Installed the isolated macOS plugin tree at $EDITABLE_ROOT"
}

set_unique_local_version() {
  local release_id="${GOLDHANDBLOG_RELEASE_TAG:-}"
  LOCAL_VERSION="$("$PYTHON" - "$EDITABLE_ROOT/plugins/$PLUGIN_NAME/.codex-plugin/plugin.json" "$RELEASE_STATE" "$release_id" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
release_id = sys.argv[3]
payload = json.loads(manifest_path.read_text(encoding="utf-8"))
source_version = str(payload["version"])
base = source_version.split("+", 1)[0]
stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
payload["version"] = f"{base}+codex.managed.macos.{stamp}.{os.getpid()}"
temporary = manifest_path.with_name(manifest_path.name + f".tmp.{os.getpid()}")
temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, manifest_path)
state_path.write_text((release_id or source_version) + "\n", encoding="utf-8")
print(payload["version"])
PY
)" || die "Could not prepare a cache-safe macOS plugin version."
  [ -n "$LOCAL_VERSION" ] || die "The managed macOS plugin version is empty."
}

register_plugin() {
  "$CODEX" plugin remove "$PLUGIN_SELECTOR" --json >/dev/null 2>&1 || true
  "$CODEX" plugin marketplace remove "$MARKETPLACE_NAME" --json >/dev/null 2>&1 || true
  "$CODEX" plugin marketplace add "$EDITABLE_ROOT" --json >/dev/null || return 1
  "$CODEX" plugin add "$PLUGIN_SELECTOR" --json >/dev/null || return 1
  local listing="$(mktemp "${TMPDIR:-/tmp}/ghm-plugin-list.XXXXXX")"
  "$CODEX" plugin list --json > "$listing" || return 1
  if ! "$PYTHON" - "$listing" "$PLUGIN_SELECTOR" "$LOCAL_VERSION" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
selector = sys.argv[2]
version = sys.argv[3]
matches = [item for item in payload.get("installed", []) if item.get("pluginId") == selector]
if len(matches) != 1:
    raise SystemExit("installed plugin selector mismatch")
item = matches[0]
if not item.get("enabled"):
    raise SystemExit("installed plugin is disabled")
if item.get("version") != version:
    raise SystemExit("installed plugin version mismatch")
source = item.get("marketplaceSource", {})
if source.get("sourceType") != "local":
    raise SystemExit("installed plugin is not using a local marketplace")
PY
  then
    /bin/rm -f -- "$listing" 2>/dev/null || true
    return 1
  fi
  /bin/rm -f -- "$listing" 2>/dev/null || true
  return 0
}

restore_previous_tree() {
  [ "$REPLACED" -eq 1 ] || return 0
  if [ -e "$EDITABLE_ROOT" ]; then
    local failed="$EDITABLE_ROOT.failed.$$.${RANDOM:-0}"
    /bin/mv "$EDITABLE_ROOT" "$failed" 2>/dev/null || true
    safe_remove_dir "$failed"
  fi
  if [ -n "$BACKUP_ROOT" ] && [ -e "$BACKUP_ROOT" ]; then
    /bin/mv "$BACKUP_ROOT" "$EDITABLE_ROOT"
    "$CODEX" plugin marketplace remove "$MARKETPLACE_NAME" --json >/dev/null 2>&1 || true
    "$CODEX" plugin marketplace add "$EDITABLE_ROOT" --json >/dev/null 2>&1 || true
    "$CODEX" plugin add "$PLUGIN_SELECTOR" --json >/dev/null 2>&1 || true
    log "Restored the previous macOS plugin tree."
  fi
}

on_exit() {
  local status=$?
  trap - EXIT
  if [ "$status" -ne 0 ] && [ "$INSTALL_COMMITTED" -ne 1 ]; then
    restore_previous_tree || true
  fi
  exit "$status"
}

trap on_exit EXIT

write_desktop_retry() {
  [ "${GOLDHANDBLOG_SKIP_DESKTOP_SHORTCUT:-0}" = "1" ] && return 0
  local desktop="${GOLDHANDBLOG_MAC_DESKTOP:-$HOME/Desktop}"
  [ -d "$desktop" ] || return 0
  /bin/ln -sfn "$EDITABLE_ROOT/SETUP-IMAGES-MAC.command" "$desktop/Goldhand Image Setup.command"
  log "Created the image setup retry launcher on the Desktop."
}

register_auto_update() {
  [ "${GOLDHANDBLOG_SKIP_AUTO_UPDATE_REGISTRATION:-0}" = "1" ] && return 0
  local label="com.goldhand.clinic-blog.macos.update"
  local agents="$HOME/Library/LaunchAgents"
  local plist="$agents/$label.plist"
  local updater="$EDITABLE_ROOT/scripts/update-macos.sh"
  /bin/mkdir -p "$agents" "$STATE_ROOT/logs"
  "$PYTHON" - "$plist" "$label" "$updater" "$CODEX" "$EDITABLE_ROOT" "$CODEX_ROOT" "$STATE_ROOT/logs/update.out.log" "$STATE_ROOT/logs/update.err.log" <<'PY'
import plistlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "Label": sys.argv[2],
    "ProgramArguments": ["/bin/bash", sys.argv[3], "--codex", sys.argv[4], "--root", sys.argv[5]],
    "RunAtLoad": True,
    "StartInterval": 21600,
    "StandardOutPath": sys.argv[7],
    "StandardErrorPath": sys.argv[8],
    "EnvironmentVariables": {"CODEX_HOME": sys.argv[6]},
}
path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
PY
  /bin/chmod 600 "$plist"
  /bin/launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
  if /bin/launchctl bootstrap "gui/$(id -u)" "$plist" >/dev/null 2>&1; then
    log "Automatic macOS updates are enabled at sign-in and every six hours."
  elif /bin/launchctl load "$plist" >/dev/null 2>&1; then
    log "Automatic macOS updates are enabled with the compatibility loader."
  else
    printf '[Goldhand Clinic Blog macOS installer] Automatic update registration was skipped. Rerunning the installer remains safe.\n' >&2
  fi
}

setup_images_best_effort() {
  [ "${GOLDHANDBLOG_SKIP_IMAGE_HOST_SETUP:-0}" = "1" ] && return 0
  local setup="$EDITABLE_ROOT/plugins/$PLUGIN_NAME/skills/$PLUGIN_NAME/scripts/setup_image_host.py"
  log "One-time image setup is starting. Approve the Vercel login in the browser if it opens."
  if PATH="$STATE_BIN:$PATH" "$PYTHON" "$setup"; then
    log "Automatic GPT image hosting is connected."
  else
    printf '[Goldhand Clinic Blog macOS installer] Automatic images are not connected yet. Double-click Goldhand Image Setup.command on the Desktop after signing in to Vercel.\n' >&2
  fi
}

main() {
  [ "$(uname -s)" = "Darwin" ] || die "This installer is only for Apple Mac computers."
  [ -f "$SOURCE_ROOT/requirements-macos.txt" ] || die "The macOS release is missing requirements-macos.txt."
  /bin/mkdir -p "$CODEX_ROOT" "$STATE_ROOT" "$STATE_BIN"
  ensure_python_runtime
  ensure_vercel_cli
  ensure_codex
  copy_managed_tree
  set_unique_local_version
  if ! register_plugin; then
    restore_previous_tree
    die "The macOS plugin could not be registered."
  fi
  register_auto_update
  write_desktop_retry
  setup_images_best_effort
  if [ -n "$BACKUP_ROOT" ] && [ -e "$BACKUP_ROOT" ]; then
    safe_remove_dir "$BACKUP_ROOT"
  fi
  INSTALL_COMMITTED=1
  log "INSTALLATION COMPLETE"
  log "Reopen ChatGPT and select Goldhand Clinic Blog for macOS in a new task."
}

main "$@"
