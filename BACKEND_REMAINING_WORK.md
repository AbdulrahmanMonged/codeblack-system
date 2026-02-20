# Backend Remaining Work Checklist

This file tracks what is still pending after the latest backend cutover pass.

## Current Snapshot
- Backend-owned voting module is implemented and routed.
- Legacy bot voting writes are deprecated; bot now mirrors/delegates.
- Guest application CAPTCHA support is implemented with policy config.
- Activity forum publish flow is implemented, including:
  - manual publish endpoint
  - bot IPC publish command
  - persisted `forum_topic_id` / `forum_post_id`
  - periodic queue task for scheduled publish + failed publish retries
- Legacy forum topic watcher task has been removed from bot Celery tasks.

## Still Remaining

## 1) Apply DB Migrations in Live Environment (Operational)
- [ ] Run `venv/bin/alembic upgrade head` on the target deployment environment.
- [ ] Verify `venv/bin/alembic current` points to `b6e8dcb19a40` (current head).
- [ ] Validate backend startup with `BACKEND_AUTO_CREATE_TABLES=false` in production.

Local recovery note:
- In the recovered local workspace used for reconstruction (`/home/bodyy/REDACTED-bot-recovered-20260220`), Alembic CLI/module is not installed in the active Python runtime, so `alembic heads/current` could not be executed locally.

Acceptance:
- Production schema matches migration head and backend runs without relying on runtime `create_all`.

## 2) Blacklist Level Policy Semantics (Deferred By Decision)
- [ ] Define and enforce business semantics for blacklist levels (`1/2/3`) beyond baseline blocking.
- [ ] Document level-based behavior for application/reapply restrictions.

Acceptance:
- Level semantics are explicit, documented, and enforced in policy checks.

## Optional Follow-Ups
- [ ] Expand frontend staff dashboard coverage for all backend workflows.
- [ ] Add integration tests for activity publish queue and voting transitions.
