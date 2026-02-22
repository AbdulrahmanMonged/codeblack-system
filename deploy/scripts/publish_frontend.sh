#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

FRONTEND_DIR="${FRONTEND_DIR:-${REPO_ROOT}/frontend}"
WEB_ROOT="${WEB_ROOT:-/var/www/codeblack}"
NPM_BIN="${NPM_BIN:-npm}"

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "Frontend directory not found: ${FRONTEND_DIR}" >&2
  exit 1
fi

if ! command -v "${NPM_BIN}" >/dev/null 2>&1; then
  echo "npm binary not found: ${NPM_BIN}" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required." >&2
  exit 1
fi

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to write to ${WEB_ROOT}" >&2
    exit 1
  fi
  SUDO="sudo"
fi

pushd "${FRONTEND_DIR}" >/dev/null
if [[ -f package-lock.json ]]; then
  "${NPM_BIN}" ci
else
  "${NPM_BIN}" install
fi
"${NPM_BIN}" run build
popd >/dev/null

${SUDO} mkdir -p "${WEB_ROOT}"
${SUDO} rsync -a --delete "${FRONTEND_DIR}/dist/" "${WEB_ROOT}/"
${SUDO} find "${WEB_ROOT}" -type d -exec chmod 755 {} \;
${SUDO} find "${WEB_ROOT}" -type f -exec chmod 644 {} \;

echo "Frontend published to ${WEB_ROOT}"
