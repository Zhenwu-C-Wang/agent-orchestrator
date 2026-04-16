#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Agent Orchestrator"
APP_PATH="${APP_PATH:-${ROOT_DIR}/dist/macos/${APP_NAME}.app}"
DIST_DIR="${ROOT_DIR}/dist/macos"
DMG_PATH="${DMG_PATH:-${DIST_DIR}/${APP_NAME}.dmg}"
STAGING_DIR="$(mktemp -d "/tmp/agent-orchestrator-dmg.XXXXXX")"

cleanup() {
  rm -rf "${STAGING_DIR}"
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Usage: bash scripts/build_macos_dmg.sh

Build a shareable macOS DMG preview that contains the Agent Orchestrator app
bundle plus an Applications shortcut.

Environment overrides:
  APP_PATH   Path to the .app bundle. Defaults to dist/macos/Agent Orchestrator.app
  DMG_PATH   Output DMG path. Defaults to dist/macos/Agent Orchestrator.dmg
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script currently targets macOS only."
  exit 1
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App bundle not found at ${APP_PATH}."
  echo "Build it first with: bash scripts/build_macos_app.sh"
  exit 1
fi

mkdir -p "${DIST_DIR}"
rm -f "${DMG_PATH}"

cp -R "${APP_PATH}" "${STAGING_DIR}/${APP_NAME}.app"
ln -s /Applications "${STAGING_DIR}/Applications"

hdiutil create \
  -volname "${APP_NAME}" \
  -srcfolder "${STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"

echo
echo "Built macOS DMG preview at:"
echo "  ${DMG_PATH}"

bash "${ROOT_DIR}/scripts/validate_macos_dmg.sh"
