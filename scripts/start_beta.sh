#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/start_beta.sh [options]

Start the beta-friendly Streamlit UI with the recommended local setup path.

Options:
  --with-dev       Also install dev dependencies.
  --skip-install   Reuse the existing virtualenv without running pip install.
  --port PORT      Streamlit port. Default: 8501.
  --help           Show this help message.
EOF
}

WITH_DEV=0
SKIP_INSTALL=0
PORT=8501

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-dev)
      WITH_DEV=1
      shift
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --port)
      if [[ $# -lt 2 ]]; then
        echo "error: --port requires a value" >&2
        usage
        exit 2
      fi
      PORT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required but was not found in PATH" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ ! -d ".venv" ]]; then
  echo "Creating local virtual environment in .venv ..."
  python3 -m venv .venv
fi

VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
VENV_PIP="${REPO_ROOT}/.venv/bin/pip"
STREAMLIT="${REPO_ROOT}/.venv/bin/streamlit"

if [[ ! -x "${VENV_PYTHON}" || ! -x "${VENV_PIP}" ]]; then
  echo "error: .venv exists but is missing python or pip executables" >&2
  exit 1
fi

if [[ "${SKIP_INSTALL}" -eq 0 ]]; then
  echo "Installing beta UI dependencies ..."
  "${VENV_PIP}" install -e '.[ui]'
  if [[ "${WITH_DEV}" -eq 1 ]]; then
    echo "Installing dev dependencies ..."
    "${VENV_PIP}" install -e '.[dev]'
  fi
else
  echo "Skipping dependency installation because --skip-install was provided."
fi

if [[ ! -x "${STREAMLIT}" ]]; then
  echo "error: streamlit is not available in .venv. Try rerunning without --skip-install." >&2
  exit 1
fi

cat <<EOF

Starting Agent Orchestrator beta UI ...

Recommended first-run path:
  1. Leave Guided mode on.
  2. Keep Runner on fake.
  3. Start with "Research quickstart" or "CSV analysis quickstart".

If your browser does not open automatically, visit:
  http://localhost:${PORT}

EOF

exec "${STREAMLIT}" run app.py --server.port "${PORT}"
