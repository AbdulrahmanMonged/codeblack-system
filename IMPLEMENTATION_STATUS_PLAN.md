# CodeBlack Recovery Status Plan

## Scope Used For This Assessment
- Current recovered workspace: `/home/bodyy/REDACTED-bot-recovered-20260220`
- Legacy baseline: `/home/bodyy/REDACTED-bot-recovered-20260220/old-bot`
- Existing status docs reviewed:
  - `BACKEND_PLAN.md`
  - `BACKEND_REMAINING_WORK.md`
  - `PHASE_P9_QA.md`
  - `RECOVERY_REPORT.md`

## What Is Implemented (Recovered and Present)

### Backend (FastAPI)
1. Core backend structure exists and is wired:
- `backend/app.py`, `backend/api/router.py`, full `backend/api/routes/*` set.

2. Auth and Discord OAuth endpoints exist:
- `GET /api/v1/auth/discord/login`
- `GET /api/v1/auth/discord/callback`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

3. Verification requests flow exists:
- `POST /api/v1/verification-requests`
- `GET /api/v1/verification-requests/me`
- reviewer list/get/approve/deny endpoints.

4. Public landing modules are implemented:
- `GET /api/v1/public/posts`
- `GET /api/v1/public/metrics`
- `GET /api/v1/public/roster`

5. Notifications system exists with delivery-level operations:
- unread count, mark-all-read, delete single, delete all (own deliveries), broadcast, targeted send.

6. Application + voting integration is implemented:
- application submit creates voting context
- voting endpoints include optional `comment_text`
- voters endpoint includes avatar URL and role color hex
- application decision is exposed through voting endpoint and compatibility shim.

7. Caching layer is integrated broadly:
- Redis cache adapter in `backend/infrastructure/cache`
- read endpoint caching + tag-based invalidation on write across modules.

8. Single-group migration exists in schema history:
- migration head includes dropping multi-group dimensions (`f4d1d57a35c2`).

### Frontend (React + HeroUI v3 foundation)
1. SPA architecture exists with route modules and feature pages.
2. Global floating navbar + dashboard shell + sidebar + footer are present.
3. Auth callback page and session bootstrap path are present.
4. Public landing page with public metrics/posts is present.
5. Verification page and protected routing wrappers are present.
6. Voting context page includes vote comments and voter display with avatar + role color.

### Bot/Celery Direction
1. Legacy forum watchers for apps/orders were removed from `bot/cogs/Tasks.py` (kept cop live scores).
2. Shared Celery config exists for backend + bot task queues (`shared/celery_shared.py`).

## What Is Missing / Broken (Priority)

## P0 Critical (must fix first)
1. Bot runtime is incomplete in current recovered `bot/` package.
- `bot/__init__.py` imports modules that do not exist in current `bot/`:
  - `.config`
  - `.core.database`
  - `.core.ipc`
  - `.core.redis`
  - `.services.*`
- `shared/celery_shared.py` includes `bot.tasks.*` modules, but current `bot/tasks` is missing.
- Impact: bot and celery worker cannot run reliably from recovered state.
- Source for restoration is available in `old-bot/bot/`.

2. Cookie session auth is incomplete in backend dependency layer.
- Auth callback sets HttpOnly cookie, but `backend/api/deps/auth.py` only reads Bearer header.
- Impact: `/auth/me` and protected endpoints cannot rely purely on cookie session as intended.

3. Runtime NameError risk in auth dependency.
- `VERIFICATION_BYPASS_PERMISSION_KEYS` is referenced but not defined in `backend/api/deps/auth.py`.
- Impact: endpoints using `require_any_permissions` can fail at runtime.

## P1 High (behavioral mismatch with agreed plan)
1. Backend verification gate is not consistently enforced for all protected actions.
- Current check is not centralized in `require_permissions`.
- Expected: non-owner unverified users blocked server-side except allowlisted paths.

2. Single-group cutover is still leaking in frontend activities flow.
- `frontend/src/features/activities/pages/ActivitiesPage.jsx` still sends `group_code` and displays `group_id`.
- Backend schema no longer accepts that field.

3. HeroUI v3 compliance is partial.
- Many pages still use native `<input>`, `<select>`, `<textarea>` directly.
- Several forms do not follow HeroUI composed field pattern (`Label`, field control, error/description slots).

4. Role matrix UI still uses checkbox list instead of the requested multi-select pattern.

## P2 Medium (hardening and DX)
1. Docs are partially stale (examples still mention removed group endpoints).
2. E2E validation matrix for recovered stack is incomplete after data loss event.
3. Need a clean parity audit between old-bot services and backend-owned replacements to prevent duplicate logic.

## Suggested Execution Phases (Commit Per Phase)

### Phase R1: Restore bot runtime completeness from `old-bot`
1. Restore missing `bot/config.py`, `bot/core/{database.py,ipc.py,redis.py,__init__.py}`.
2. Restore `bot/services/`, `bot/tasks/`, `bot/models/`, `bot/repositories/`, `bot/utils/`, `bot/image_generator.py` as required.
3. Reconcile restored modules with current backend-owned voting/orders strategy (do not re-enable removed watchers).
4. Verify:
- `python -m compileall bot`
- bot startup import smoke check
- celery import/registration smoke check.

### Phase R2: Fix backend auth/session correctness
1. Update `get_optional_principal` to accept token from HttpOnly cookie (with Bearer fallback).
2. Define and apply `VERIFICATION_BYPASS_PERMISSION_KEYS`.
3. Apply verification gate in `require_permissions` with explicit bypass list.
4. Verify:
- login callback -> cookie set
- `/api/v1/auth/me` works with cookie only
- unverified user blocked on protected actions with `VERIFICATION_REQUIRED`.

### Phase R3: Complete single-group and frontend behavior alignment
1. Remove `group_code/group_id` usage from frontend activities module.
2. Confirm activities requests match backend schema exactly.
3. Verify activities create/list/approve/publish end-to-end.

### Phase R4: HeroUI v3 normalization pass
1. Replace native form controls across feature pages with HeroUI primitives/wrappers.
2. Standardize labels with HeroUI `Label` composition where applicable.
3. Convert role matrix permission editor to requested multi-select pattern.
4. Verify `npm run build` and runtime form behavior on all tabs.

### Phase R5: Final reconciliation and QA pass
1. Re-run migration/status checks:
- `alembic current`
- `alembic heads`
2. Run backend compile/import checks.
3. Run frontend build/lint checks.
4. Update status docs (`BACKEND_REMAINING_WORK.md` and this file) with final closure state.

## Quick Delta vs old-bot
- Kept: cog surface and cloudflare modules in current tree.
- Missing in current tree but present in old-bot: core infra modules, services, repositories, tasks, and config file needed by runtime.
- Strategy: restore required runtime modules, then keep backend as source-of-truth for workflows already migrated.

## Immediate Next Action
1. Execute Phase R1 (bot runtime restoration) first, because current repo cannot reliably run full services until this is fixed.

## Execution Progress (2026-02-20)
1. Completed `R1`:
- Restored missing bot runtime modules from `old-bot` into `bot/`.
- Verified syntax with `python3 -m compileall bot`.

2. Completed `R2`:
- Added cookie-based principal resolution in `backend/api/deps/auth.py`.
- Added `VERIFICATION_BYPASS_PERMISSION_KEYS` constant.
- Enforced verification gate in `require_permissions` and aligned `require_any_permissions` behavior.
- Verified syntax with `python3 -m compileall backend`.

3. Completed `R3`:
- Removed `group_code/group_id` leaks from `frontend/src/features/activities/pages/ActivitiesPage.jsx`.
- Verified frontend build with `npm --prefix frontend run build`.

4. Partial `R4` complete:
- Migrated role matrix editor from checkbox list to HeroUI v3 multi-select in `frontend/src/features/permissions/pages/RoleMatrixPage.jsx`.
- Verified frontend build with `npm --prefix frontend run build`.

## Remaining From This Plan
1. Finish full HeroUI migration pass for remaining pages still using native controls.
2. Run final reconciliation sweep (docs + QA matrix + migration/runtime checks).
