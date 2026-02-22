# Deploy Toolkit

This folder contains production deployment helpers for CodeBlack using:
- Caddy for reverse proxy + static frontend serving
- systemd for backend/celery/bot process management
- separate Python venvs for backend and bot

## Files
- `DEPLOY_PLAN_CADDY.md` - end-to-end deployment phases and checks
- `caddy/Caddyfile.example` - Caddy template (SPA + API reverse proxy)
- `systemd/*.service` - unit templates
- `scripts/install_venvs.sh` - create/install backend + bot venvs
- `scripts/publish_frontend.sh` - build frontend and publish to `/var/www/REDACTED`
- `scripts/install_systemd.sh` - render/install systemd services from templates
- `scripts/install_caddy_site.sh` - render/install Caddy config from template

## Quick Run (Typical Order)
1. Create and install Python environments
```bash
deploy/scripts/install_venvs.sh
```

2. Build and publish frontend static files
```bash
WEB_ROOT=/var/www/REDACTED deploy/scripts/publish_frontend.sh
```

3. Install Caddy config
```bash
DOMAIN=REDACTED.example.com WEB_ROOT=/var/www/REDACTED deploy/scripts/install_caddy_site.sh
```

4. Install and enable systemd services
```bash
APP_DIR=/path/to/REDACTED-bot-recovered-20260220 APP_USER=root APP_GROUP=root START_SERVICES=1 deploy/scripts/install_systemd.sh
```

## Notes
- Service templates rely on `.env` in the project root.
- Backend runs on `127.0.0.1:8000`; Caddy proxies `/api/*` to it.
- The frontend is SPA-routed by Caddy with `try_files {path} /index.html`.
