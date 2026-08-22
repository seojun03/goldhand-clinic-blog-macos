#!/bin/bash
set -Eeuo pipefail

REPOSITORY="seojun03/goldhand-clinic-blog-macos"
RELEASE_ASSET="goldhand-clinic-blog-macos.zip"
PLUGIN_NAME="goldhand-clinic-blog"
CODEX_PATH="${GOLDHANDBLOG_CODEX_PATH:-}"
EDITABLE_ROOT="${GOLDHANDBLOG_MAC_EDITABLE_ROOT:-$HOME/GoldhandBlogMac}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --codex) CODEX_PATH="$2"; shift 2 ;;
    --root) EDITABLE_ROOT="$2"; shift 2 ;;
    *) printf '[Goldhand Clinic Blog macOS updater] Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

STATE_FILE="$EDITABLE_ROOT/.goldhand-clinic-blog-macos-managed-release"
LOCK_DIR="${TMPDIR:-/tmp}/goldhand-clinic-blog-macos-update-$(id -u).lock"
TEMP_ROOT=""

log() {
  printf '[Goldhand Clinic Blog macOS updater] %s\n' "$1"
}

release_lock() {
  if [ -d "$LOCK_DIR" ]; then
    /bin/rm -rf -- "$LOCK_DIR" 2>/dev/null || true
  fi
  if [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ]; then
    /bin/rm -rf -- "$TEMP_ROOT" 2>/dev/null || true
  fi
}

acquire_lock() {
  if /bin/mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    return 0
  fi
  local old_pid=""
  if [ -f "$LOCK_DIR/pid" ]; then
    old_pid="$(/bin/cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  fi
  if [ -n "$old_pid" ] && ! /bin/kill -0 "$old_pid" 2>/dev/null; then
    /bin/rm -rf -- "$LOCK_DIR" 2>/dev/null || true
    /bin/mkdir "$LOCK_DIR" 2>/dev/null || return 1
    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    return 0
  fi
  return 1
}

trap release_lock EXIT
acquire_lock || { log "Another macOS update is already running."; exit 0; }

if [ -n "${GOLDHANDBLOG_MAC_UPDATE_ARCHIVE:-}" ]; then
  LATEST_TAG="${GOLDHANDBLOG_MAC_UPDATE_TAG:-local-$(/usr/bin/shasum -a 256 "$GOLDHANDBLOG_MAC_UPDATE_ARCHIVE" | /usr/bin/awk '{print $1}')}"
else
  RELEASE_JSON="$(curl -fsSL --retry 3 --connect-timeout 15 -H 'Accept: application/vnd.github+json' -H 'User-Agent: GoldhandClinicBlogMacUpdater' "https://api.github.com/repos/$REPOSITORY/releases/latest")"
  LATEST_TAG="$(printf '%s' "$RELEASE_JSON" | /usr/bin/sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | /usr/bin/head -1)"
  [ -n "$LATEST_TAG" ] || { log "The latest validated macOS release tag is unavailable."; exit 1; }
fi
CURRENT_TAG=""
[ -f "$STATE_FILE" ] && CURRENT_TAG="$(/bin/cat "$STATE_FILE" 2>/dev/null || true)"
if [ "${GOLDHANDBLOG_FORCE_UPDATE:-0}" != "1" ] && [ "$CURRENT_TAG" = "$LATEST_TAG" ]; then
  log "Already current: $CURRENT_TAG"
  exit 0
fi

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/ghmu.XXXXXX")"
ARCHIVE="$TEMP_ROOT/release.zip"
if [ -n "${GOLDHANDBLOG_MAC_UPDATE_ARCHIVE:-}" ]; then
  /bin/cp "$GOLDHANDBLOG_MAC_UPDATE_ARCHIVE" "$ARCHIVE"
else
  curl -fL --retry 3 --connect-timeout 15 -o "$ARCHIVE" "https://github.com/$REPOSITORY/releases/latest/download/$RELEASE_ASSET"
fi
EXTRACTED="$TEMP_ROOT/extracted"
/bin/mkdir -p "$EXTRACTED"
/usr/bin/ditto -x -k "$ARCHIVE" "$EXTRACTED"
INSTALLER="$(/usr/bin/find "$EXTRACTED" -maxdepth 4 -type f -name install-from-download-macos.sh -print -quit)"
[ -n "$INSTALLER" ] || { log "The validated macOS release is missing its installer."; exit 1; }

GOLDHANDBLOG_RELEASE_TAG="$LATEST_TAG" \
GOLDHANDBLOG_CODEX_PATH="$CODEX_PATH" \
GOLDHANDBLOG_MAC_EDITABLE_ROOT="$EDITABLE_ROOT" \
GOLDHANDBLOG_SKIP_AUTO_UPDATE_REGISTRATION=1 \
GOLDHANDBLOG_SKIP_IMAGE_HOST_SETUP=1 \
GOLDHANDBLOG_SKIP_DESKTOP_SHORTCUT=1 \
/bin/bash "$INSTALLER"

INSTALLED_TAG=""
[ -f "$STATE_FILE" ] && INSTALLED_TAG="$(/bin/cat "$STATE_FILE" 2>/dev/null || true)"
[ "$INSTALLED_TAG" = "$LATEST_TAG" ] || { log "The managed release state did not update to $LATEST_TAG."; exit 1; }
log "UPDATED TO $LATEST_TAG"
