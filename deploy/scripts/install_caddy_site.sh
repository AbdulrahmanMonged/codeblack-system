#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="${SCRIPT_DIR}/../caddy/Caddyfile.example"

DOMAIN="${DOMAIN:-}"
WEB_ROOT="${WEB_ROOT:-/var/www/REDACTED}"
CADDY_OUTPUT="${CADDY_OUTPUT:-/etc/caddy/Caddyfile}"

if [[ -z "${DOMAIN}" ]]; then
  echo "DOMAIN is required. Example: DOMAIN=REDACTED.example.com" >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "Missing template: ${TEMPLATE_FILE}" >&2
  exit 1
fi

if ! command -v caddy >/dev/null 2>&1; then
  echo "caddy binary not found." >&2
  exit 1
fi

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to write ${CADDY_OUTPUT}" >&2
    exit 1
  fi
  SUDO="sudo"
fi

rendered="$(mktemp)"
sed \
  -e "s|__DOMAIN__|${DOMAIN}|g" \
  -e "s|__WEB_ROOT__|${WEB_ROOT}|g" \
  "${TEMPLATE_FILE}" > "${rendered}"

${SUDO} mkdir -p "$(dirname -- "${CADDY_OUTPUT}")"
${SUDO} install -m 0644 "${rendered}" "${CADDY_OUTPUT}"
rm -f "${rendered}"

${SUDO} caddy validate --config "${CADDY_OUTPUT}"
${SUDO} systemctl reload caddy

echo "Caddy site installed to ${CADDY_OUTPUT}"
