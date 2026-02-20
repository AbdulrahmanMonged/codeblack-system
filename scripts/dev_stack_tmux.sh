#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${CODEBLACK_TMUX_SESSION:-REDACTED-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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

ensure_prereqs() {
  require_cmd tmux
  require_cmd npm
  if [[ ! -x "${REPO_ROOT}/venv/bin/python" ]]; then
    echo "Missing Python venv at ${REPO_ROOT}/venv/bin/python" >&2
    exit 1
  fi
  if [[ ! -x "${REPO_ROOT}/venv/bin/celery" ]]; then
    echo "Missing Celery executable at ${REPO_ROOT}/venv/bin/celery" >&2
    exit 1
  fi
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

create_session() {
  ensure_prereqs

  tmux new-session -d -s "${SESSION_NAME}" -n api-web
  tmux send-keys -t "${SESSION_NAME}:api-web.0" \
    "cd '${REPO_ROOT}' && venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000" C-m
  tmux split-window -h -t "${SESSION_NAME}:api-web.0"
  tmux send-keys -t "${SESSION_NAME}:api-web.1" \
    "cd '${REPO_ROOT}/frontend' && npm run dev -- --host 127.0.0.1 --port 5173" C-m
  tmux select-layout -t "${SESSION_NAME}:api-web" even-horizontal

  tmux new-window -t "${SESSION_NAME}" -n queue
  tmux send-keys -t "${SESSION_NAME}:queue.0" \
    "cd '${REPO_ROOT}' && venv/bin/celery -A celery_worker.celery_app worker --loglevel=info --pool=solo" C-m
  tmux split-window -h -t "${SESSION_NAME}:queue.0"
  tmux send-keys -t "${SESSION_NAME}:queue.1" \
    "cd '${REPO_ROOT}' && venv/bin/celery -A celery_worker.celery_app beat --loglevel=info" C-m
  tmux select-layout -t "${SESSION_NAME}:queue" even-horizontal

  tmux new-window -t "${SESSION_NAME}" -n bot
  tmux send-keys -t "${SESSION_NAME}:bot.0" \
    "cd '${REPO_ROOT}' && venv/bin/python main.py" C-m

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
