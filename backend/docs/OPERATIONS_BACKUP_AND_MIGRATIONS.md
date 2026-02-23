# Backend Operations: Backup and Migration Plan

## Scope
This document defines the baseline production plan for backups, restore drills, and schema migrations for the CodeBlack backend.

## Backup Strategy
1. PostgreSQL logical backup:
   - Run `pg_dump` at least every 6 hours.
   - Keep compressed dumps for 14 days.
   - Store backups in off-server object storage.
2. PostgreSQL base backup / snapshot:
   - Daily full snapshot.
   - Keep 7 daily snapshots and 4 weekly snapshots.
3. Redis backup:
   - Enable RDB snapshots.
   - Persist `appendonly yes` for command/audit durability.
   - Copy Redis backup files off-server daily.
4. Object storage:
   - Enable bucket/versioning policy for uploaded proofs/images.
   - Retain deleted objects for minimum 30 days.

## Restore Procedure (Minimum)
1. Restore PostgreSQL into isolated staging first.
2. Run integrity checks:
   - Row counts for critical tables (`applications`, `orders`, `blacklist_entries`, `config_change_history`).
   - Last 24h inserts and audit records.
3. Validate app startup and deep health endpoint:
   - `GET /api/v1/system/health/deep`
4. Cut over to production only after staging verification.

## Migration Workflow
1. Every schema change must be tracked by migration file in `migrations/versions`.
2. Deployment order:
   - Put app in maintenance mode for writes (if destructive migration).
   - Run migrations (`venv/bin/alembic upgrade head`).
   - Verify revision (`venv/bin/alembic current`) matches current head (`b6e8dcb19a40` at time of this document update).
   - Run backend startup checks and `/api/v1/system/health/deep`.
   - Re-enable writes.
3. Rollback policy:
   - Use reversible migrations for all non-destructive changes.
   - For destructive migrations, require full backup checkpoint before apply.

## Change Safety Gates
1. Critical config keys require two-step approval in backend API.
2. Sensitive keys are blocked from dashboard mutation and must remain in env/secret manager.
3. All config changes are signed in API responses and audited in `config_change_history`.

## Recovery Drills
1. Run monthly restore drill in staging.
2. Measure:
   - Recovery Point Objective (RPO)
   - Recovery Time Objective (RTO)
3. Record drill output and action items.
