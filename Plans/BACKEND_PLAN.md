
Backend goal:
- Add a dedicated FastAPI backend to control bot behavior and expose web/admin APIs.
- Add website authentication using Discord OAuth2.
- Add web application-submission flow for recruitment.

## 1.1 Decisions Locked From Discussion
- Backend will be created inside this repository under `/backend`.
- Application submissions allow guest users (no login required to submit).
- Every submission must be persisted and assigned a unique identifier.
- Website read access can be public, but write/admin actions are restricted.
- Restricted actions require authenticated Discord users with required permissions.
- Initial owner Discord user ID is `757387358621532164` with full permissions.
- Additional owner Discord user ID is `1162165557647380542` with full permissions.
- Guild/role mapping will be expanded later when full role IDs are provided.
- Backend is the only source of truth for recruitment/application decisions, voting state, order decisions, blacklist state, patrol/training state, and vacation state.
- Voting system ownership moves to backend (all operations currently in bot voting cog).
- Voting is restricted to authorized users with required role level and permissions.
- Orders submission is a restricted action for authorized users only.
- Order `account_name` is resolved server-side from authenticated user mapping (`discord_user_id -> account_name`) and omitted from request payload.
- Orders and order decisions must persist in database with full audit history.
- Introduce a dedicated roster system for in-group members, ranks, participation, punishments, and linked domain records.
- Introduce a global playerbase model for all known players interacted with by the group.
- Introduce a dedicated blacklist subsystem with generated human-readable IDs (`BL001C-X`, `BL002C-X`, ...).
- Patrol/training/event entries are workflow-driven (`pending` -> `approved`/`rejected` -> forum publish -> completed).
- Vacation requests are workflow-driven and role-threshold controlled by owner configuration.
- Role thresholds and permission mappings are configurable by owners.
- Blacklist numbering is global and never reused, including removed records.
- `roots` supports flexible 2-letter codes (not strict ISO-only validation).
- Vacation return requires manual confirmation (no automatic return-state transition).
- Blacklist suffix pattern (`C-X`) is environment/group-aware and configurable for future multi-environment support.
- Authorization is Discord-native: backend uses actual Discord roles from the codeblack guild, synced and mapped to permissions by owners.
- No manually created backend role hierarchy; promotions/demotions in Discord immediately affect backend permissions after sync.
- Patrol/training activities can be approved before scheduling; forum posting is blocked until `scheduled_for` is set.
- Initial Discord role ID `1312800512139202732` receives the first permission bundle.
- Bot command acknowledgement timeout SLA is `5s`.
- Multiple applications per player are allowed, controlled by eligibility policy checks.
- Denied applications can enforce cooldown until a future date or permanent reapply block.
- Default denial cooldown is `7 days` (owner-configurable).
- Blacklisted players cannot apply or perform restricted actions, but can submit blacklist-removal requests.
- Blacklist entries include severity level (`1` lowest to `3` highest, extensible later).
- Blacklist levels are enabled now, but no level implies automatic permanent reapply block by default.
- File storage for uploads uses Bunny object storage.
- Voting closure supports both reviewer action and auto-close max duration policy (owner-configurable, default range 3-7 days).
- Critical configuration changes require two-step approval (editor + approver) by policy.

### 3.3 Proposed New Service Layout (inside this repo at `/backend`)

Deliverables:
- Discord OAuth2 login flow in FastAPI.
- Session/JWT issuance.
- Guild membership and role synchronization.
- Permission-based access control mapped from Discord guild roles.
- Public-read policy with restricted actions.
- Permission checks for `codeblack` role (once role ID is configured).

### Access Policy Decisions
- Public routes:
  - Read-only pages/endpoints (status pages, public stats, public application rules).
  - Blacklist-removal request submission endpoint (rate-limited + abuse-protected).
- Restricted routes:
  - Application review/decision actions.
  - Voting actions (cast/moderate/read voters based on permission).
  - Order submission and order decision actions.
  - Bot configuration and service toggles.
  - Channel routing and workflow settings.
- Restricted action rule (initial):
  - User must be authenticated via Discord OAuth2.
  - User must be in target guild.
  - User must have backend permission and required mapped role(s).
  - If user is actively blacklisted, deny restricted actions by default.
  - Exception: blacklisted users may create blacklist-removal requests.

Ack:
```json
{
  "type": "command_ack",
  "request_id": "uuid",
  "ok": true,
  "applied_at": "ISO-8601"
}
```

Order submit request (multipart/form-data):
- `ingame_name`: string
- `completed_orders`: string
- `proof_image`: file (required)

Order decision request (JSON):
```json
{
  "decision": "denied",
  "reason": "Proof image is unclear and does not show required fields."
}
```

Vote cast request (JSON):
```json
{
  "choice": "yes"
}
```

Application eligibility response (JSON):
```json
{
  "allowed": false,
  "status": "cooldown",
  "wait_until": "2026-03-01T00:00:00Z",
  "permanent_block": false,
  "reasons": ["DENIAL_COOLDOWN_ACTIVE"]
}
```

Blacklist removal request submit (JSON):
```json
{
  "account_name": "exampleAccount",
  "request_text": "I changed behavior and request blacklist removal."
}
```

### 6.3 Permissions System (Database-Backed RBAC)
Tables:
- `users`
  - `id`, `discord_user_id`, `username`, `is_active`, `created_at`
- `discord_roles`
  - `id`
  - `discord_role_id` (unique, from Discord guild)
  - `guild_id`
  - `name`
  - `position`
  - `is_active`
  - `synced_at`
- `permissions`
  - `id`, `key`, `description`
- `discord_role_permissions`
  - `discord_role_id`, `permission_id` (many-to-many)
- `user_discord_roles`
  - `user_id`, `discord_role_id` (cached snapshot of membership from guild)
- `user_permissions`
  - `user_id`, `permission_id`, `allow` (optional explicit override)
- `config_registry`
  - `id`
  - `key` (unique)
  - `value_json`
  - `schema_version`
  - `is_sensitive`
  - `updated_by_user_id`
  - `updated_at`
- `config_change_history`
  - `id`
  - `config_key`
  - `before_json`
  - `after_json`
  - `changed_by_user_id`
  - `approved_by_user_id` (nullable)
  - `change_reason`
  - `created_at`

Seed owner:
- Insert user with `discord_user_id = 757387358621532164`.
- Insert user with `discord_user_id = 1162165557647380542`.
- Grant `owner.override` via `user_permissions` (owner-level explicit override).
- Owners configure permission matrix for Discord roles from admin endpoints.
- Seed initial member bundle for Discord role ID `1312800512139202732`:
  - `applications.create_member`
  - `applications.read_public`
  - `voting.cast`
  - `orders.submit`
  - `activities.create`
  - `vacations.submit`

Initial permission catalog:
- `system.read`
- `system.manage`
- `auth.me`
- `auth.logout`
- `users.read`
- `users.manage_discord_roles_cache`
- `discord_roles.read`
- `discord_roles.sync`
- `discord_role_permissions.read`
- `discord_role_permissions.write`
- `permissions.read`
- `permissions.manage`
- `config_registry.read`
- `config_registry.write`
- `config_registry.rollback`
- `config_registry.preview`
- `config_change.approve`
- `applications.create_guest`
- `applications.create_member`
- `applications.eligibility.read`
- `applications.read_public`
- `applications.read_private`
- `applications.review`
- `applications.assign_reviewer`
- `applications.decision.accept`
- `applications.decision.decline`
- `applications.reapply_policy.write`
- `applications.policies.read`
- `applications.policies.write`
- `applications.comment`
- `applications.export`
- `voting.read`
- `voting.cast`
- `voting.list_voters`
- `voting.close`
- `voting.reopen`
- `voting.reset`
- `orders.submit`
- `orders.read`
- `orders.review`
- `orders.decision.accept`
- `orders.decision.deny`
- `orders.export`
- `user_account_link.read`
- `user_account_link.write`
- `playerbase.read`
- `playerbase.write`
- `roster.read`
- `roster.write`
- `ranks.read`
- `ranks.write`
- `blacklist.read`
- `blacklist.add`
- `blacklist.update`
- `blacklist.level.write`
- `blacklist.remove`
- `blacklist.restore`
- `blacklist_removal_requests.create`
- `blacklist_removal_requests.read`
- `blacklist_removal_requests.review`
- `punishments.read`
- `punishments.write`
- `activities.read`
- `activities.create`
- `activities.approve`
- `activities.reject`
- `activities.manage_participants`
- `activities.publish_forum`
- `vacations.read`
- `vacations.submit`
- `vacations.approve`
- `vacations.deny`
- `vacations.cancel`
- `vacations.configure_thresholds`
- `policies.configure_role_thresholds`
- `bot.read_status`
- `bot.configure_channels`
- `bot.toggle_features`
- `bot.trigger.forum_sync`
- `bot.trigger.cop_scores_refresh`
- `bot.manage.voting`
- `bot.manage.recruitment`
- `config.read`
- `config.write`
- `audit.read`
- `owner.override`

Initial role threshold policy:
- Voting cast: any Discord role granted `voting.cast` (default include `codeblack` role).
- Voting moderation (close/reopen/reset/list voters): roles granted `voting.close|reopen|reset|list_voters`.
- Voting auto-close: owner-configured duration policy (default operational window 3-7 days).
- Order submission: roles granted `orders.submit` (default include `codeblack` role).
- Order decisions: roles granted `orders.decision.accept|deny`.
- Blacklist operations: roles granted `blacklist.add|update|remove|restore`.
- Blacklist removal request review: roles granted `blacklist_removal_requests.review`.
- Patrol/training creation: roles granted `activities.create`.
- Patrol/training approval/rejection: roles granted `activities.approve|reject`.
- Vacation submission: roles granted `vacations.submit`.
- Vacation approval/denial: roles granted `vacations.approve|deny`.
- Configuration and permission management: roles granted `permissions.manage` and/or users with `owner.override`.
- Application reapply policy configuration: roles granted `applications.policies.write` and/or users with `owner.override`.
- Critical config changes: require `config_change.approve` in addition to write permission.
- Critical config approval must be performed by a different user than the editor.

Authorization resolution order:
- Check user is authenticated.
- Check guild membership in codeblack Discord server.
- Sync (or read cached) current Discord roles for the user.
- Resolve permissions from `discord_role_permissions`.
- Evaluate blacklist gate:
  - If active blacklist -> deny restricted actions.
  - Allow only whitelist exceptions (e.g., create blacklist-removal request).
- Apply user-level overrides.
- If user has `owner.override`, allow all restricted actions.

## 9. Open Questions To Finalize Before Coding
1. Define business meaning for blacklist levels (`1`, `2`, `3`) when you are ready.

## 10. Source of Truth for Decisions (Final)
Final decision:
- Backend is the only source of truth for application decisions, voting state, order decisions, blacklist state, patrol/training state, and vacation state.

Enforced flow:
- Reviewer decides in backend UI/API.
- Backend commits canonical decision state in DB.
- Backend triggers forum/Discord mirror actions through IPC.
- Any external sync failure is retried and logged; canonical decision does not move to forum/Discord state.

2. Configure Redirects
- Add redirect URIs:
  - Dev: `http://localhost:8000/api/v1/auth/discord/callback`
  - Prod: `https://your-domain.com/api/v1/auth/discord/callback`
### 6.1 Backend API (initial)
- `GET /api/v1/system/health`
- `GET /api/v1/system/bot-status`
- `GET /api/v1/config/channels`
- `PUT /api/v1/config/channels`
- `GET /api/v1/config/features`
- `PUT /api/v1/config/features`
- `POST /api/v1/applications`
- `GET /api/v1/applications/eligibility`
- `GET /api/v1/applications/eligibility/me`
- `GET /api/v1/applications`
- `GET /api/v1/applications/{id}`
- `POST /api/v1/applications/{id}/decision`
- `GET /api/v1/applications/policies`
- `PUT /api/v1/applications/policies`
- `GET /api/v1/voting/{context_type}/{context_id}`
- `POST /api/v1/voting/{context_type}/{context_id}/vote`
- `GET /api/v1/voting/{context_type}/{context_id}/voters`
- `POST /api/v1/voting/{context_type}/{context_id}/close`
- `POST /api/v1/voting/{context_type}/{context_id}/reopen`
- `POST /api/v1/voting/{context_type}/{context_id}/reset`
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{id}`
- `POST /api/v1/orders/{id}/decision`
- `POST /api/v1/users/{id}/account-link`
- `GET /api/v1/users/{id}/account-link`
- `GET /api/v1/discord/roles`
- `POST /api/v1/discord/roles/sync`
- `GET /api/v1/permissions/role-matrix`
- `PUT /api/v1/permissions/role-matrix/{discord_role_id}`
- `GET /api/v1/config/registry`
- `PUT /api/v1/config/registry/{key}`
- `POST /api/v1/config/registry/{key}/preview`
- `POST /api/v1/config/registry/{key}/rollback`
- `GET /api/v1/config/changes`
- `POST /api/v1/config/changes/{change_id}/approve`
- `GET /api/v1/roster`
- `POST /api/v1/roster`
- `PATCH /api/v1/roster/{membership_id}`
- `GET /api/v1/playerbase`
- `GET /api/v1/playerbase/{player_id}`
- `POST /api/v1/playerbase/{player_id}/punishments`
- `GET /api/v1/playerbase/{player_id}/punishments`
- `PATCH /api/v1/playerbase/{player_id}/punishments/{punishment_id}`
- `POST /api/v1/blacklist`
- `GET /api/v1/blacklist`
- `PATCH /api/v1/blacklist/{blacklist_id}`
- `POST /api/v1/blacklist/{blacklist_id}/remove`
- `POST /api/v1/blacklist/removal-requests`
- `GET /api/v1/blacklist/removal-requests`
- `GET /api/v1/blacklist/removal-requests/{request_id}`
- `POST /api/v1/blacklist/removal-requests/{request_id}/approve`
- `POST /api/v1/blacklist/removal-requests/{request_id}/deny`
- `POST /api/v1/activities`
- `GET /api/v1/activities`
- `GET /api/v1/activities/{activity_id}`
  - `stats_url`
  - `history_url`
  - `raw_text`
- `application_decisions`
  - `id`
  - `application_id` (FK -> applications.id)
  - `reviewer_user_id`
  - `decision` (`accepted`, `declined`)
  - `decision_reason`
  - `reapply_policy` (`allow_immediate`, `cooldown`, `permanent_block`)
  - `cooldown_days` (nullable, default `7` when `reapply_policy=cooldown`)
  - `reapply_allowed_at` (nullable)
  - `created_at`
- `application_eligibility_state`
  - `id`
  - `player_id` (FK -> playerbase.id, unique)
  - `account_name` (unique fallback when player_id missing)
  - `eligibility_status` (`allowed`, `cooldown`, `blocked_permanent`, `blocked_blacklist`)
  - `wait_until` (nullable)
  - `source` (`decision_policy`, `blacklist`, `owner_override`)
  - `source_ref_id` (nullable)
  - `updated_at`

Workflow:
- Submit form (guest/member) -> check eligibility -> generate `public_id` -> store record -> notify reviewers -> optional bot forum post -> attach voting context.
- Reviewer decision flow (canonical):
  - Reviewer accepts/declines in backend.
  - Backend writes decision in DB (source of truth).
  - Decision can update reapply policy (`cooldown` until date or `permanent_block`).
  - If cooldown is chosen and no custom value is provided, default to 7 days.
  - Eligibility state is recalculated and persisted.
  - Backend publishes IPC command for bot/forum mirror updates.
  - Mirror failures are retried asynchronously without changing canonical backend state.
- Multiple applications are allowed, subject to eligibility state checks.
- Blacklisted players are blocked from applying until blacklist status changes.

## Phase 3A: Orders Module (Backend-Owned)
Goal: implement persistent order submissions and reviewer moderation with strict RBAC.

Deliverables:
- Authorized endpoint for order submission.
- File upload handling for proof image (`UploadFile`) with persistent storage metadata.
- Reviewer decision workflow (accept/deny) with required reason.
- Optional mirror posting to Discord/forum after backend commit.
- Proof files stored in Bunny object storage with persisted object keys and URLs.

Request contract (submit order):
- `ingame_name` (str, required)
- `completed_orders` (str, required)
- `proof_image` (UploadFile, required)
- `account_name` is not accepted from client; backend derives it from authenticated user mapping.

Data model (minimum):
- `user_game_accounts`
  - `id`
  - `user_id` (FK -> users.id)
  - `discord_user_id` (unique)
  - `account_name` (unique)
  - `is_verified`
  - `created_at`, `updated_at`
- `orders`
  - `id` (internal PK)
  - `public_id` (unique immutable user-facing identifier)
  - `submitted_by_user_id` (FK -> users.id)
  - `discord_user_id`
  - `ingame_name`
  - `account_name` (server-resolved)
  - `completed_orders`
  - `proof_file_key` (storage key/path)
  - `proof_content_type`
  - `proof_size_bytes`
  - `status` (`submitted`, `accepted`, `denied`)
  - `submitted_at`, `updated_at`
- `order_reviews`
  - `id`
  - `order_id` (FK -> orders.id)
  - `reviewer_user_id` (FK -> users.id)
  - `decision` (`accepted`, `denied`)
  - `reason` (required for deny, optional for accept)
  - `reviewed_at`

Workflow:
- User (authorized) submits order -> backend resolves account name from mapping -> backend stores order + proof metadata -> backend emits event/notification.
- Higher role reviewer accepts/denies order -> backend persists decision/reason -> backend emits mirror command/event.
- Every transition is append-only audited.

## Phase 3B: Roster and Playerbase Core
Goal: model group members and related data with flexible relationships for long-term operations.

Deliverables:
- Separate roster table for current in-group members and rank state.
- Global playerbase table for all known players (group and non-group).
- Relationship model between group and playerbase records.
- Unified linking of applications, orders, punishments, activities, vacations to players.

Data model (minimum):
- `groups`
  - `id`
  - `code` (unique, e.g. `codeblack`)
  - `name`
  - `is_active`
- `playerbase`
  - `id` (internal PK)
  - `public_player_id` (optional human-facing code)
  - `ingame_name` (alias/current display)
  - `account_name` (unique identity)
  - `mta_serial` (nullable, unique when present)
  - `country_code` (ISO-like 2 chars)
  - `created_at`, `updated_at`
- `group_memberships`
  - `id`
  - `group_id` (FK -> groups.id)
  - `player_id` (FK -> playerbase.id)
  - `status` (`active`, `left`, `kicked`, `retired`)
  - `joined_at`, `left_at`
  - `current_rank_id` (FK -> group_ranks.id, nullable)
- `group_ranks`
  - `id`
  - `group_id`
  - `name`
  - `level` (higher number = higher authority)
  - `is_active`
- `group_roster`
  - `id`
  - `group_membership_id` (unique FK)
  - `display_rank`
  - `last_seen_at`
  - `is_on_leave`
  - `notes`
- `player_punishments`
  - `id`
  - `player_id` (FK -> playerbase.id)
  - `punishment_type` (`warning`, `suspension`, `strike`, `other`)
  - `severity`
  - `reason`
  - `issued_by_user_id`
  - `issued_at`
  - `expires_at` (nullable)
  - `status` (`active`, `expired`, `revoked`)

Associated records linked to `playerbase.id`:
- Applications (`applications.player_id`, nullable for legacy until linked).
- Orders (`orders.player_id`).
- Punishments (`player_punishments.player_id`).
- Activity participation (`activity_participants.player_id`).
- Vacations (`vacation_requests.player_id`).

Migration strategy:
- Keep existing bot tables operational initially.
- Add mapping layer from current `players` table to `playerbase`.
- Incrementally cut over read/write paths to new backend-owned tables.

## Phase 3C: Blacklist Subsystem
Goal: manage blacklisted players with strict authorization and auditable lifecycle.

Deliverables:
- Dedicated `blacklist_entries` table.
- Deterministic generated code format (`BL001C-X`, `BL002C-X`, ...).
- Add/remove/configure operations restricted by role + permission.
- Full audit history of changes.
- Blacklist-removal request workflow for blacklisted players.

Data model (minimum):
- `blacklist_entries`
  - `id` (internal PK, indexed)
  - `blacklist_player_id` (unique generated string, format baseline: `BL%03dC-X`)
  - `blacklist_sequence` (global increasing integer; never reused)
  - `suffix_key` (environment/group suffix source, configurable)
  - `player_id` (FK -> playerbase.id)
  - `blacklist_level` (integer, default `1`, where `1` is lowest and `3` is highest, extensible)
  - `alias` (in-game name snapshot)
  - `identity` (account name snapshot)
  - `serial` (MTA serial snapshot)
  - `roots` (2-letter country code, e.g. `BD`, `EG`, `PK`, `UK`)
  - `remarks` (reason/details)
  - `status` (`active`, `removed`)
  - `created_by_user_id`
  - `removed_by_user_id` (nullable)
  - `created_at`, `removed_at` (nullable)
- `blacklist_history`
  - `id`
  - `blacklist_entry_id`
  - `action` (`created`, `updated`, `removed`, `restored`)
  - `actor_user_id`
  - `change_set` (JSON diff)
  - `created_at`
- `blacklist_removal_requests`
  - `id`
  - `public_id`
  - `blacklist_entry_id` (FK -> blacklist_entries.id, nullable when unresolved by account)
  - `account_name` (required for lookup)
  - `request_text` (explanation of why removal is requested)
  - `status` (`pending`, `approved`, `denied`, `cancelled`)
  - `review_comment` (nullable)
  - `requested_at`
  - `reviewed_at` (nullable)
  - `reviewed_by_user_id` (nullable)

Behavior:
- Prefer soft-delete (`status=removed`) over hard delete.
- Preserve snapshots (`alias`, `identity`, `serial`, `roots`) even if playerbase changes later.
- ID generator uses one global sequence for all entries and never reuses consumed numbers.
- `roots` accepts any validated 2-letter code by policy (not ISO-strict).
- Blacklisted players cannot perform restricted actions except creating removal requests.

## Phase 3D: Patrol/Training/Event Activity System
Goal: track internal activities with approval workflow and forum publishing integration.

Deliverables:
- Activity creation by authorized members.
- Multi-phase moderation pipeline.
- Participant enrollment tracking.
- Bot forum-post integration after approval.
- Approval can occur without schedule; publish is gated by schedule existence.

Data model (minimum):
- `group_activities`
  - `id`
  - `public_id`
  - `group_id`
  - `activity_type` (`patrol`, `training`, `event`, extensible enum)
  - `title`
  - `duration_minutes`
  - `notes`
  - `status` (`pending`, `approved`, `rejected`, `scheduled`, `posted`, `completed`, `cancelled`)
  - `created_by_user_id`
  - `approved_by_user_id` (nullable)
  - `approval_comment` (nullable)
  - `scheduled_for` (nullable datetime)
  - `forum_topic_id` (nullable)
  - `forum_post_id` (nullable)
  - `created_at`, `updated_at`
- `activity_participants`
  - `id`
  - `activity_id` (FK -> group_activities.id)
  - `player_id` (FK -> playerbase.id)
  - `participant_role` (`host`, `participant`, `observer`)
  - `attendance_status` (`planned`, `attended`, `absent`)
  - `notes`

Workflow:
- Member creates activity -> `pending`.
- Higher role reviews and approves/rejects with comment.
- Approved activity may remain unscheduled (`status=approved`, `scheduled_for=null`).
- Publish transition requires `scheduled_for` to be set, then move to `scheduled`/`posted`.
- On approval, backend can schedule IPC command for bot forum publish once schedule exists.
- Posting result updates `forum_topic_id/forum_post_id`.
- Activity transitions to `completed` with participation results.

## Phase 3E: Vacation Request System
Goal: manage leave requests with approval workflow and role-threshold rules.

Deliverables:
- Vacation request submission for eligible roles.
- Approval/denial by higher role with comments.
- Optional sync actions (forum/Discord notices and roster leave flags).

Data model (minimum):
- `vacation_requests`
  - `id`
  - `public_id`
  - `player_id` (FK -> playerbase.id)
  - `requester_user_id` (FK -> users.id)
  - `leave_date`
  - `expected_return_date`
  - `target_group` (where player is moving during leave)
  - `status` (`pending`, `approved`, `denied`, `cancelled`, `returned`)
  - `reason` (nullable)
  - `review_comment` (nullable)
  - `reviewed_by_user_id` (nullable)
  - `reviewed_at` (nullable)
  - `created_at`, `updated_at`

Policy:
- Submit threshold role is owner-configurable.
- Review/decision threshold role is owner-configurable.
- Approval can toggle roster leave marker (`group_roster.is_on_leave=true`) until return.
- Return transition to `returned` is manual-confirmation only.

Move control policy to backend:
- Channel IDs and routing rules.
- Service on/off toggles.
- Recruitment workflow policy flags.
- Voting state and moderation operations.
- Orders submission/review policy and approval lifecycle.
- Roster state, rank hierarchy, and membership lifecycle.
- Blacklist lifecycle and moderation.
- Patrol/training activity lifecycle and participation tracking.
- Vacation request lifecycle.

Potentially disable in bot once backend controls exist:
- Hard-coded channel constants in cogs.
- Manual configuration commands replaced by backend admin panel.
- Voting slash commands in `bot/cogs/Voting.py` (`vote`, `enable_voting`, `disable_voting`, `reset_voting`, `voters`) after backend parity is deployed.
- Direct order ingestion paths that bypass backend order validation policy.
- Any direct in-bot mutation paths for blacklist, roster, and vacations once backend handlers are live.

## 8. Execution Order (Pragmatic)
1. Phase 0 contracts and env design.
2. Phase 1 Discord OAuth2 auth/authz.
3. Phase 2 backend bot-control APIs + IPC command handlers.
4. Phase 3 applications module.
5. Phase 3A orders module.
6. Phase 3B roster/playerbase core.
7. Phase 3C blacklist subsystem.
8. Phase 3D patrol/training activities.
9. Phase 3E vacation workflow.
10. Phase 4 reviewer/admin portal.
11. Phase 5 hardening and observability.

- Policy-based access control:
  - Discord-native RBAC: map Discord guild roles directly to backend permissions.

8. Role Mapping Strategy
- Persist `discord_user_id`, `username`, `avatar`, `guild_roles`.
- Sync real Discord roles from codeblack guild (role ID, name, position).
- Owners assign permission sets directly to Discord role IDs in DB.
- Effective permissions are computed from the user's current Discord roles.
- Promotions/demotions in Discord alter backend access automatically after role sync.
- Seed initial permission bundle to Discord role ID `1312800512139202732`.

5. Backend Env Vars
- `DISCORD_CLIENT_ID`
- `DISCORD_CLIENT_SECRET`
- `DISCORD_REDIRECT_URI`
- `DISCORD_GUILD_ID`
- `JWT_SECRET`
- `JWT_EXP_MINUTES`
- `BOT_COMMAND_ACK_TIMEOUT_SECONDS` (default `5`)
- `BUNNY_STORAGE_ENDPOINT`
- `BUNNY_STORAGE_ZONE`
- `BUNNY_STORAGE_ACCESS_KEY`
- `BUNNY_STORAGE_PUBLIC_BASE_URL`

- Policy toggles:
  - Require voting for approvals (on/off)
  - Auto-create review thread (on/off)
  - Voting eligibility policy (role threshold + permission keys)
  - Voting auto-close duration (owner-configurable, e.g. 3 to 7 days)

Voting migration scope (from existing bot features):
- Cast vote (`yes` / `no`) with one-vote-per-user enforcement.
- Show vote status (upvotes/downvotes/total).
- List voters and vote choices (authorized viewers only).
- Close voting manually by reviewer action.
- Auto-close voting when configured max duration is reached.
- Re-open voting.
- Reset voting counters and voter records.
- Persist all voting actions and moderation actions in DB audit tables.

### Data Model (minimum)
- `applications`
  - `id` (internal DB PK)
  - `public_id` (unique, immutable, user-facing ID, e.g. UUIDv7/ULID)
  - `status` (`submitted`, `under_review`, `accepted`, `declined`)
  - `submitted_at`
  - `applicant_discord_id` (nullable)
  - `player_id` (FK -> playerbase.id, nullable until linked)
  - `submitter_type` (`guest`, `member`)
  - `submitter_ip_hash` (for anti-abuse tracking)
  - `in_game_nickname`
  - `account_name`

- Denial policy handling (cooldown and permanent block) with owner-configurable rules.
- Default denial cooldown policy set to 7 days (owner-configurable).

Security controls (required baseline):

- Config versioning + rollback with signed change metadata.
- Mandatory two-step approval for critical config keys (separate editor and approver).
- Secrets never editable via general dashboard fields; secret values stored in secret manager/env only.
