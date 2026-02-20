# Recovery Report (2026-02-20)

## Source of recovery
- Disk remnant base: `/media/test_recovery/coding-projectes/REDACTED-bot`
- Codex session replay source: `/home/bodyy/.codex/sessions/2026/02/18/rollout-2026-02-18T17-58-12-019c7179-2c2f-7a43-82b1-b8965a94deeb.jsonl`

## Recovery output
- Recovered working copy: `/home/bodyy/REDACTED-bot-recovered-20260220`
- Archive backup: `/home/bodyy/REDACTED-bot-recovered-20260220.tar.gz`
- Replay failure log: `/home/bodyy/REDACTED-bot-recovered-20260220/codex_recovery_apply_failures.log`

## Replay stats
- `apply_patch` operations found: `920`
- Replayed successfully: `759`
- Failed: `161`

## What was restored well
- Full `backend/` tree reconstructed (routes, services, models, repositories, schemas, core).
- `frontend/src/` app/features/layout tree reconstructed.
- Updated `bot/` modules and deployment/config support files reconstructed.
- Python syntax check passed:
  - `python3 -m compileall backend bot`

## Known gaps after recovery
- Some patch steps could not be replayed due context mismatch from missing original intermediate files.
- Most repeated failures were planning docs and a subset of frontend final refinements.
- `frontend` root scaffolding files are likely incomplete/missing (e.g. package manager manifests) because they were not present in disk remnant and were not modified via `apply_patch` in the recorded session.

## Immediate recommendation
1. Use this recovered directory as the new working base.
2. Recreate frontend package manifests if missing, then reinstall deps.
3. Diff this tree against any remote/other-machine copy if available, and backfill remaining gaps.
4. Keep the archive before making any new edits.

