#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${CODEBLACK_TMUX_SESSION:-codeblack-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKEND_VENV_DEFAULT=""
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  BACKEND_VENV_DEFAULT="${REPO_ROOT}/.venv"
elif [[ -x "${REPO_ROOT}/venv/bin/python" ]]; then
  BACKEND_VENV_DEFAULT="${REPO_ROOT}/venv"
fi

BACKEND_VENV="${CODEBLACK_BACKEND_VENV:-${BACKEND_VENV_DEFAULT}}"
BACKEND_PY="${BACKEND_VENV}/bin/python"
CELERY_BIN="${BACKEND_VENV}/bin/celery"

BOT_VENV_DEFAULT=""
if [[ -x "${REPO_ROOT}/.venv-bot/bin/python" ]]; then
  BOT_VENV_DEFAULT="${REPO_ROOT}/.venv-bot"
elif [[ -n "${BACKEND_VENV_DEFAULT}" ]]; then
  BOT_VENV_DEFAULT="${BACKEND_VENV_DEFAULT}"
fi
BOT_VENV="${CODEBLACK_BOT_VENV:-${BOT_VENV_DEFAULT}}"
BOT_PY="${BOT_VENV}/bin/python"

usage() {
  cat <<EOF
Usage: $(basename "$0") [start|force-start|stop|restart|attach|status]

Commands:
  start    Start full local stack in tmux and attach (auto-recovers stale session)
  force-start  Always recreate session before starting services
  stop     Stop tmux session
  restart  Restart tmux session
  attach   Attach to running session (or start if missing)
  status   Show pane status for the session

Environment:
  CODEBLACK_TMUX_SESSION   Override tmux session name (default: ${SESSION_NAME})
  CODEBLACK_TMUX_NO_ATTACH Set to 1/true/yes to skip auto-attach on start
  CODEBLACK_BACKEND_VENV   Override backend/celery venv path (default: ${BACKEND_VENV_DEFAULT:-<not found>})
  CODEBLACK_BOT_VENV       Override bot venv path (default: ${BOT_VENV_DEFAULT:-<not found>})
EOF
}

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${port} )" | tail -n +2 | grep -q .
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi
  return 1
}

ensure_port_free() {
  local port="$1"
  local service="$2"
  if port_in_use "${port}"; then
    echo "Port ${port} is already in use; cannot start ${service}." >&2
    echo "Stop the conflicting process and retry." >&2
    exit 1
  fi
}

ensure_prereqs() {
  require_cmd tmux
  require_cmd npm
  require_cmd rg

  if [[ -z "${BACKEND_VENV}" || ! -x "${BACKEND_PY}" ]]; then
    echo "Missing backend venv python at ${BACKEND_PY}" >&2
    exit 1
  fi
  if [[ ! -x "${CELERY_BIN}" ]]; then
    echo "Missing Celery executable at ${CELERY_BIN}" >&2
    exit 1
  fi
  if [[ -z "${BOT_VENV}" || ! -x "${BOT_PY}" ]]; then
    echo "Missing bot venv python at ${BOT_PY}" >&2
    exit 1
  fi

  if ! "${BOT_PY}" -c "import discord" >/dev/null 2>&1; then
    echo "discord package is missing in bot venv (${BOT_VENV})." >&2
    exit 1
  fi

  if [[ -f "${REPO_ROOT}/old-bot/.env" ]] && ! "${BOT_PY}" -c "import socks" >/dev/null 2>&1; then
    echo "Warning: PySocks is missing in bot venv; IRC proxy mode will be disabled." >&2
  fi

  ensure_port_free 8000 "backend"
  ensure_port_free 5173 "frontend"
}

session_exists() {
  tmux has-session -t "${SESSION_NAME}" 2>/dev/null
}

session_has_active_services() {
  local pane_cmds
  pane_cmds="$(tmux list-panes -a -t "${SESSION_NAME}" -F "#{pane_current_command}" 2>/dev/null || true)"
  if [[ -z "${pane_cmds}" ]]; then
    return 1
  fi
  if echo "${pane_cmds}" | rg -q "python|celery|npm|node|vite"; then
    return 0
  fi
  return 1
}

load_env_into_session() {
  local tmp_env
  tmp_env="$(mktemp)"
  (
    cd "${REPO_ROOT}"
    "${BACKEND_PY}" - <<'PY'
from pathlib import Path
from dotenv import dotenv_values

merged = {}
for env_path in (Path('.env'), Path('old-bot/.env')):
    if not env_path.exists():
        continue
    for key, value in dotenv_values(env_path).items():
        if value is not None:
            merged[key] = str(value).replace("\n", " ")

for key, value in merged.items():
    print(f"{key}\t{value}")
PY
  ) >"${tmp_env}"

  while IFS=$'\t' read -r key value; do
    if [[ -z "${key}" ]]; then
      continue
    fi
    tmux set-environment -t "${SESSION_NAME}" "${key}" "${value}"
  done <"${tmp_env}"

  rm -f "${tmp_env}"
  tmux set-environment -t "${SESSION_NAME}" PYTHONPATH "${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
}

create_session() {
  ensure_prereqs

  tmux new-session -d -s "${SESSION_NAME}" -n api-web
  load_env_into_session

  tmux respawn-pane -k -t "${SESSION_NAME}:api-web.0" \
    "cd '${REPO_ROOT}' && '${BACKEND_PY}' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
  tmux split-window -h -t "${SESSION_NAME}:api-web.0" \
    "cd '${REPO_ROOT}/frontend' && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"
  tmux select-layout -t "${SESSION_NAME}:api-web" even-horizontal

  tmux new-window -t "${SESSION_NAME}" -n queue \
    "cd '${REPO_ROOT}' && '${CELERY_BIN}' -A celery_worker.celery_app worker --loglevel=info --pool=solo"
  tmux split-window -h -t "${SESSION_NAME}:queue.0" \
    "cd '${REPO_ROOT}' && '${CELERY_BIN}' -A celery_worker.celery_app beat --loglevel=info"
  tmux select-layout -t "${SESSION_NAME}:queue" even-horizontal

  tmux new-window -t "${SESSION_NAME}" -n bot \
    "cd '${REPO_ROOT}' && '${BOT_PY}' main.py"

  tmux select-window -t "${SESSION_NAME}:api-web"
  if is_truthy "${CODEBLACK_TMUX_NO_ATTACH:-0}"; then
    echo "Session '${SESSION_NAME}' started (no attach)."
  else
    tmux attach -t "${SESSION_NAME}"
  fi
}

start_session() {
  if session_exists; then
    if session_has_active_services; then
      echo "Session '${SESSION_NAME}' already running with active services."
      if is_truthy "${CODEBLACK_TMUX_NO_ATTACH:-0}"; then
        echo "Use attach to view it: $(basename "$0") attach"
      else
        tmux attach -t "${SESSION_NAME}"
      fi
      return
    fi
    echo "Session '${SESSION_NAME}' is stale. Recreating."
    tmux kill-session -t "${SESSION_NAME}"
  fi

  create_session
}

force_start_session() {
  ensure_prereqs
  if session_exists; then
    tmux kill-session -t "${SESSION_NAME}"
  fi
  create_session
}

stop_session() {
  if session_exists; then
    tmux kill-session -t "${SESSION_NAME}"
    echo "Session '${SESSION_NAME}' stopped."
  else
    echo "Session '${SESSION_NAME}' is not running."
  fi
}

attach_session() {
  if session_exists; then
    tmux attach -t "${SESSION_NAME}"
  else
    start_session
  fi
}

status_session() {
  if ! session_exists; then
    echo "Session '${SESSION_NAME}' is not running."
    return
  fi
  tmux list-windows -t "${SESSION_NAME}"
  tmux list-panes -a -t "${SESSION_NAME}" \
    -F "#{session_name}:#{window_name}.#{pane_index} pid=#{pane_pid} cmd=#{pane_current_command}"
}

main() {
  local action="${1:-start}"
  case "${action}" in
    start) start_session ;;
    force-start) force_start_session ;;
    stop) stop_session ;;
    restart)
      stop_session
      start_session
      ;;
    attach) attach_session ;;
    status) status_session ;;
    -h|--help|help) usage ;;
    *)
      echo "Unknown command: ${action}" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
