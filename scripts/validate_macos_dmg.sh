#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Agent Orchestrator"
DMG_PATH="${DMG_PATH:-${ROOT_DIR}/dist/macos/${APP_NAME}.dmg}"
MOUNT_DIR="$(mktemp -d "/tmp/agent-orchestrator-dmg-mount.XXXXXX")"
ATTACHED=0

cleanup() {
  if [[ "${ATTACHED}" == "1" ]]; then
    hdiutil detach "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
  rm -rf "${MOUNT_DIR}"
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Usage: bash scripts/validate_macos_dmg.sh

Validate that the generated macOS DMG preview verifies cleanly and mounts with
the expected app bundle and Applications shortcut.

Environment overrides:
  DMG_PATH   Path to the .dmg file. Defaults to dist/macos/Agent Orchestrator.dmg
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This validation script currently targets macOS only."
  exit 1
fi

if [[ ! -f "${DMG_PATH}" ]]; then
  echo "DMG not found: ${DMG_PATH}"
  exit 1
fi

hdiutil verify "${DMG_PATH}"
hdiutil attach "${DMG_PATH}" -nobrowse -readonly -mountpoint "${MOUNT_DIR}" >/dev/null
ATTACHED=1

required_paths=(
  "${MOUNT_DIR}/${APP_NAME}.app"
  "${MOUNT_DIR}/Applications"
)

for required_path in "${required_paths[@]}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "Required mounted path is missing: ${required_path}"
    exit 1
  fi
done

if [[ ! -L "${MOUNT_DIR}/Applications" ]]; then
  echo "Applications shortcut is not a symlink: ${MOUNT_DIR}/Applications"
  exit 1
fi

echo "Validated macOS DMG preview:"
echo "  ${DMG_PATH}"
