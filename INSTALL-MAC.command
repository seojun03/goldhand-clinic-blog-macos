#!/bin/bash
set -Eeuo pipefail

REPOSITORY="seojun03/goldhand-clinic-blog-macos"
RELEASE_ASSET="goldhand-clinic-blog-macos.zip"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
TEMP_ROOT=""

log() {
  printf '\n[Goldhand Clinic Blog macOS installer] %s\n' "$1"
}

cleanup() {
  if [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ]; then
    /bin/rm -rf -- "$TEMP_ROOT" 2>/dev/null || true
  fi
}

pause_if_needed() {
  if [ "${GOLDHANDBLOG_SKIP_PAUSE:-0}" != "1" ] && [ -t 0 ]; then
    printf '\nPress Return to close this window.'
    IFS= read -r _ || true
  fi
}

fail() {
  printf '\n[INSTALLATION FAILED] %s\n' "$1" >&2
  pause_if_needed
  exit 1
}

trap cleanup EXIT

[ "$(uname -s)" = "Darwin" ] || fail "This installer is only for Apple Mac computers."

INSTALLER="$SCRIPT_DIR/install-from-download-macos.sh"
RELEASE_TAG="${GOLDHANDBLOG_RELEASE_TAG:-}"

if [ ! -f "$INSTALLER" ]; then
  command -v curl >/dev/null 2>&1 || fail "macOS curl is unavailable."
  TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/ghm.XXXXXX")"
  ARCHIVE="$TEMP_ROOT/release.zip"
  if [ -n "${GOLDHANDBLOG_MAC_SOURCE_ARCHIVE:-}" ]; then
    /bin/cp -- "$GOLDHANDBLOG_MAC_SOURCE_ARCHIVE" "$ARCHIVE"
    if [ -z "$RELEASE_TAG" ]; then
      RELEASE_TAG="local-$(/usr/bin/shasum -a 256 "$ARCHIVE" | /usr/bin/awk '{print $1}')"
    fi
  else
    log "Downloading the latest validated macOS release."
    RELEASE_JSON="$(curl -fsSL --retry 3 --connect-timeout 15 -H 'Accept: application/vnd.github+json' -H 'User-Agent: GoldhandClinicBlogMacInstaller' "https://api.github.com/repos/$REPOSITORY/releases/latest")" || fail "Could not read the latest macOS release."
    if [ -z "$RELEASE_TAG" ]; then
      RELEASE_TAG="$(printf '%s' "$RELEASE_JSON" | /usr/bin/sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | /usr/bin/head -1)"
    fi
    curl -fL --retry 3 --connect-timeout 15 -o "$ARCHIVE" "https://github.com/$REPOSITORY/releases/latest/download/$RELEASE_ASSET" || fail "Could not download the complete macOS release."
  fi
  EXTRACTED="$TEMP_ROOT/extracted"
  /bin/mkdir -p "$EXTRACTED"
  if command -v ditto >/dev/null 2>&1; then
    /usr/bin/ditto -x -k "$ARCHIVE" "$EXTRACTED" || fail "The macOS release archive could not be extracted."
  else
    /usr/bin/unzip -q "$ARCHIVE" -d "$EXTRACTED" || fail "The macOS release archive could not be extracted."
  fi
  INSTALLER="$(/usr/bin/find "$EXTRACTED" -maxdepth 4 -type f -name install-from-download-macos.sh -print -quit)"
  [ -n "$INSTALLER" ] || fail "The macOS release is missing its installer."
fi

/bin/chmod +x "$INSTALLER"
log "Starting the isolated macOS installation."
if GOLDHANDBLOG_RELEASE_TAG="$RELEASE_TAG" /bin/bash "$INSTALLER"; then
  log "INSTALLATION COMPLETE"
  pause_if_needed
  exit 0
fi

fail "The macOS installation did not finish. Keep this window open and send a screenshot to the plugin author."
