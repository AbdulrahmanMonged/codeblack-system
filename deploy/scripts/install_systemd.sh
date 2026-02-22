#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/../systemd"

APP_DIR="${APP_DIR:-${REPO_ROOT}}"
APP_USER="${APP_USER:-$(id -un)}"
APP_GROUP="${APP_GROUP:-$(id -gn)}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"

UNITS=(
  codeblack-backend.service
  codeblack-celery.service
  codeblack-celery-beat.service
  codeblack-bot.service
)

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install systemd units." >&2
    exit 1
  fi
  SUDO="sudo"
fi

for unit in "${UNITS[@]}"; do
  src="${TEMPLATE_DIR}/${unit}"
  dst="${SYSTEMD_DIR}/${unit}"
  if [[ ! -f "${src}" ]]; then
    echo "Missing unit template: ${src}" >&2
    exit 1
  fi

  tmp_file="$(mktemp)"
  sed \
    -e "s|__APP_DIR__|${APP_DIR}|g" \
    -e "s|__APP_USER__|${APP_USER}|g" \
    -e "s|__APP_GROUP__|${APP_GROUP}|g" \
    "${src}" > "${tmp_file}"

  ${SUDO} install -m 0644 "${tmp_file}" "${dst}"
  rm -f "${tmp_file}"
  echo "Installed ${dst}"
done

${SUDO} systemctl daemon-reload
${SUDO} systemctl enable "${UNITS[@]}"

if [[ "${START_SERVICES:-0}" == "1" ]]; then
  ${SUDO} systemctl restart "${UNITS[@]}"
fi

echo "Systemd units installed."
echo "App dir: ${APP_DIR}"
echo "User/Group: ${APP_USER}:${APP_GROUP}"
