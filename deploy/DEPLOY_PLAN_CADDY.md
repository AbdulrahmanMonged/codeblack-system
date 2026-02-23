# CodeBlack Deployment Plan (Caddy + systemd)

## Target Architecture
- Reverse proxy and static delivery: **Caddy**
- Frontend static files: **`/var/www/REDACTED`** (`index.html` + assets from `frontend/dist`)
- Backend API: **FastAPI/Uvicorn** on `127.0.0.1:8000`
- Queue workers: **Celery worker + Celery beat**
- Bot runtime: **PyCord bot service**
- Process supervisor: **systemd**
- Cache/broker: **Redis**

## Services
- `REDACTED-backend.service` -> FastAPI API
- `REDACTED-celery.service` -> Celery worker
- `REDACTED-celery-beat.service` -> Celery beat scheduler
- `REDACTED-bot.service` -> Discord bot

All unit templates are in `deploy/systemd/` and are rendered by `deploy/scripts/install_systemd.sh`.

## Caddy Routing
- Static SPA files served from `/var/www/REDACTED`
- API requests (`/api/*`) reverse-proxied to `127.0.0.1:8000`
- SPA fallback: `try_files {path} /index.html`

Template file: `deploy/caddy/Caddyfile.example`

## Phase Plan
1. Prepare server packages
- Install: `python3-venv`, `python3-pip`, `redis-server`, `caddy`, `nodejs`, `npm`, `rsync`
- Ensure Redis and Caddy are running.

2. Configure environment
- Copy and fill project `.env`
- Confirm DB/Redis/Celery/Discord/Bunny credentials.

3. Create Python virtualenvs and dependencies
- Run `deploy/scripts/install_venvs.sh`
- Backend venv default: `.venv`
- Bot venv default: `.venv-bot`

4. Build and publish frontend
- Run `deploy/scripts/publish_frontend.sh`
- Output synced to `/var/www/REDACTED`

5. Install Caddy site config
- Render and install from template:
  - `DOMAIN=your-domain.com WEB_ROOT=/var/www/REDACTED deploy/scripts/install_caddy_site.sh`
- Validate/reload Caddy.

6. Install systemd services
- Run `deploy/scripts/install_systemd.sh`
- Optionally start services immediately with `START_SERVICES=1`.

7. Run migrations and health verification
- Run Alembic migration from backend venv.
- Validate:
  - `systemctl status REDACTED-backend REDACTED-celery REDACTED-celery-beat REDACTED-bot`
  - `curl http://127.0.0.1:8000/api/v1/system/health`
  - `curl -I https://your-domain.com`

## Operational Notes
- Keep backend and bot in separate venvs to avoid dependency conflicts.
- Caddy serves only built frontend files from `/var/www/REDACTED`.
- Any frontend deploy should re-run `deploy/scripts/publish_frontend.sh`.
- If you change unit templates, re-run `deploy/scripts/install_systemd.sh` and restart impacted services.

## Rollback Basics
- Caddy: restore previous site config and reload Caddy.
- Frontend: restore previous `/var/www/REDACTED` backup.
- Backend/bot: restart previous git revision, then restart systemd services.
