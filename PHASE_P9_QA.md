# Phase P9 QA and Release Hardening

## Executed Verification

1. Backend and bot syntax checks
- Command: `python3 -m compileall backend bot migrations`
- Result: success

2. Frontend production build
- Command: `npm --prefix frontend run build`
- Result: success

3. Alembic graph integrity
- Command: `.venv/bin/alembic heads`
- Result: `9c1a2e74e6b3 (head)`

4. Alembic current revision check (live DB)
- Command: `.venv/bin/alembic current`
- Environment: Postgres credentials loaded from `old-bot/.env`
- Result: `9c1a2e74e6b3 (head)`

5. Alembic migration apply check (live DB)
- Command: `.venv/bin/alembic upgrade head`
- Environment: Postgres credentials loaded from `old-bot/.env`
- Result: success (no pending migrations)

6. Backend runtime smoke test
- Command: start uvicorn on `127.0.0.1:8011`, then request `GET /api/v1/public/metrics`
- Result: success (`200 OK`)
- Observation: startup is non-blocking for bootstrap seed (`Starting bootstrap seed in background` appears before app ready)

7. Celery worker startup smoke test
- Command: `timeout 12s .venv/bin/celery -A shared.celery_shared.celery_app worker --pool=solo --loglevel=warning`
- Result: worker booted successfully and performed warm shutdown on timeout

## Notes

1. Alembic dependency is now included in `backend/requirements.txt`.
2. Missing revision link was repaired with placeholder revision `0e3a4ca576e6` to restore chain integrity.
3. Migration env now uses backend settings directly and no longer requires bot runtime auth config to run Alembic.
4. Bot package import path was made tooling-safe with lazy runtime imports in `bot/__init__.py`.
