#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Agent Orchestrator"
DIST_DIR="${ROOT_DIR}/dist/macos"
BUILD_DIR="${ROOT_DIR}/build/pyinstaller"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"

usage() {
  cat <<'EOF'
Usage: bash scripts/build_macos_app.sh

Build the first macOS app-bundle preview for Agent Orchestrator.

Environment overrides:
  PYTHON_BIN   Python interpreter to use for PyInstaller. Defaults to .venv/bin/python
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

if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "Python 3 was not found. Set PYTHON_BIN or create .venv first."
    exit 1
  fi
fi

if ! "${PYTHON_BIN}" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller is not installed for ${PYTHON_BIN}."
  echo "Install packaging dependencies with: pip install -e '.[ui,packaging]'"
  exit 1
fi

mkdir -p "${DIST_DIR}" "${BUILD_DIR}"

"${PYTHON_BIN}" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "${APP_NAME}" \
  --distpath "${DIST_DIR}" \
  --workpath "${BUILD_DIR}" \
  --specpath "${BUILD_DIR}" \
  --collect-data streamlit \
  --collect-submodules streamlit \
  --add-data "${ROOT_DIR}/app.py:." \
  --add-data "${ROOT_DIR}/docs:docs" \
  "${ROOT_DIR}/desktop_launcher.py"

echo
echo "Built macOS app preview at:"
echo "  ${DIST_DIR}/${APP_NAME}.app"

bash "${ROOT_DIR}/scripts/validate_macos_app.sh"
