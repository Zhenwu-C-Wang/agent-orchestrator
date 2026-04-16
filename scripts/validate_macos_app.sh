#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${APP_PATH:-${ROOT_DIR}/dist/macos/Agent Orchestrator.app}"
EXECUTABLE_PATH="${APP_PATH}/Contents/MacOS/Agent Orchestrator"
RESOURCE_ROOT="${APP_PATH}/Contents/Resources"

usage() {
  cat <<'EOF'
Usage: bash scripts/validate_macos_app.sh

Validate that the generated macOS app preview contains the expected bundle
layout and packaged resources.

Environment overrides:
  APP_PATH   Path to the .app bundle. Defaults to dist/macos/Agent Orchestrator.app
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

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App bundle not found: ${APP_PATH}"
  exit 1
fi

if [[ ! -x "${EXECUTABLE_PATH}" ]]; then
  echo "App executable is missing or not executable: ${EXECUTABLE_PATH}"
  exit 1
fi

required_paths=(
  "${APP_PATH}/Contents/Info.plist"
  "${RESOURCE_ROOT}/app.py"
  "${RESOURCE_ROOT}/docs/project_status.json"
  "${RESOURCE_ROOT}/docs/sample_data/quarterly_metrics.csv"
  "${RESOURCE_ROOT}/docs/sample_data/quarterly_metrics.json"
  "${RESOURCE_ROOT}/docs/sample_data/quarterly_metrics_baseline.csv"
)

for required_path in "${required_paths[@]}"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "Required packaged path is missing: ${required_path}"
    exit 1
  fi
done

if command -v codesign >/dev/null 2>&1; then
  codesign --verify --deep --strict "${APP_PATH}"
fi

echo "Validated macOS app preview:"
echo "  ${APP_PATH}"
