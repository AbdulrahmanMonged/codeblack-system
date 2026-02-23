#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_VENV="${BACKEND_VENV:-${REPO_ROOT}/.venv}"
BOT_VENV="${BOT_VENV:-${REPO_ROOT}/.venv-bot}"
BACKEND_REQUIREMENTS="${BACKEND_REQUIREMENTS:-${REPO_ROOT}/backend/requirements.txt}"

if [[ -n "${BOT_REQUIREMENTS:-}" ]]; then
  BOT_REQUIREMENTS_PATH="${BOT_REQUIREMENTS}"
elif [[ -f "${REPO_ROOT}/requirements.txt" ]]; then
  BOT_REQUIREMENTS_PATH="${REPO_ROOT}/requirements.txt"
elif [[ -f "${REPO_ROOT}/old-bot/requirements.txt" ]]; then
  BOT_REQUIREMENTS_PATH="${REPO_ROOT}/old-bot/requirements.txt"
else
  echo "Unable to locate bot requirements file." >&2
  echo "Set BOT_REQUIREMENTS=/path/to/requirements.txt and retry." >&2
  exit 1
fi

if [[ ! -f "${BACKEND_REQUIREMENTS}" ]]; then
  echo "Missing backend requirements file: ${BACKEND_REQUIREMENTS}" >&2
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python binary not found: ${PYTHON_BIN}" >&2
  exit 1
fi

install_env() {
  local env_path="$1"
  local req_file="$2"
  local env_name="$3"

  echo "[${env_name}] Creating venv at ${env_path}"
  "${PYTHON_BIN}" -m venv "${env_path}"

  echo "[${env_name}] Upgrading pip/setuptools/wheel"
  "${env_path}/bin/python" -m pip install --upgrade pip setuptools wheel

  echo "[${env_name}] Installing dependencies from ${req_file}"
  "${env_path}/bin/pip" install -r "${req_file}"
}

install_env "${BACKEND_VENV}" "${BACKEND_REQUIREMENTS}" "backend"
install_env "${BOT_VENV}" "${BOT_REQUIREMENTS_PATH}" "bot"

echo "[verify] Checking backend imports"
"${BACKEND_VENV}/bin/python" - <<'PY'
import fastapi  # noqa: F401
import celery  # noqa: F401
import sqlalchemy  # noqa: F401
print("backend imports OK")
PY

echo "[verify] Checking bot imports"
"${BOT_VENV}/bin/python" - <<'PY'
import discord  # noqa: F401
print("bot imports OK")
PY

echo "Done."
echo "Backend venv: ${BACKEND_VENV}"
echo "Bot venv: ${BOT_VENV}"
echo "Bot requirements file used: ${BOT_REQUIREMENTS_PATH}"
