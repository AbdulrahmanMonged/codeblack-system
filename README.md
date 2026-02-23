<div align="center">

<h1>CodeBlack System</h1>

<p><strong>A production-grade Discord guild management platform — built with FastAPI, Discord.py, React, PostgreSQL &amp; Redis.</strong></p>

<p>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Discord.py-async-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord.py" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PostgreSQL-asyncpg-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-IPC%20%2B%20Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Celery-Task%20Queue-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
</p>

<p>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" alt="Status" />
  <img src="https://img.shields.io/badge/Architecture-Async--First-blueviolet?style=flat-square" alt="Architecture" />
</p>

</div>

---

## Overview

**CodeBlack System** is an end-to-end guild management platform designed for large online gaming communities. It integrates a **Discord bot**, a **REST API backend**, and a **React SPA** into a single cohesive system — enabling recruitment, member management, activity tracking, voting, blacklisting, and full administrative control from both Discord and a web dashboard.

> Built from scratch with production concerns in mind: async-first, audit-trailed, permission-gated, and fully observable.

---

## Architecture

<pre>
┌─────────────────────────────────────────────────────────────────────┐
│                         CodeBlack System                            │
│                                                                     │
│   ┌──────────────┐    HTTP/REST    ┌──────────────────────────┐     │
│   │   React SPA  │◄──────────────►│    FastAPI Backend        │     │
│   │  (Vite + TS) │                │  (ASGI / Uvicorn)         │     │
│   └──────────────┘                └────────────┬─────────────┘     │
│                                                │                    │
│                                    ┌───────────┼──────────┐        │
│                                    │           │          │        │
│                               PostgreSQL     Redis     Celery      │
│                               (asyncpg)    (IPC+Cache) (Workers)   │
│                                    │           │                    │
│                                    └───────────┼──────────┘        │
│                                                │                    │
│                                   ┌────────────▼────────────┐      │
│                                   │     Discord Bot          │      │
│                                   │  (discord.py / async)   │      │
│                                   └─────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
</pre>

The bot and backend **share the same PostgreSQL schema** through async SQLAlchemy — eliminating data inconsistency at the architectural level. Real-time bot↔backend communication uses **Redis Streams** (persistent, ACK-based) and **Redis Pub/Sub** (fire-and-forget events).

---

## Tech Stack

<table>
<thead>
<tr>
<th>Layer</th>
<th>Technology</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>

<tr>
<td rowspan="8"><strong>Backend</strong></td>
<td>FastAPI 0.115+</td>
<td>ASGI REST framework — dependency injection, lifespan hooks, OpenAPI auto-docs</td>
</tr>
<tr>
<td>SQLAlchemy 2.0 (async)</td>
<td>ORM with async sessions, 17 relational models, unified schema ownership</td>
</tr>
<tr>
<td>asyncpg</td>
<td>High-performance async PostgreSQL driver</td>
</tr>
<tr>
<td>Alembic 1.13+</td>
<td>Schema versioning and migration management</td>
</tr>
<tr>
<td>Pydantic v2</td>
<td>Settings management, request/response validation, DTOs</td>
</tr>
<tr>
<td>PyJWT 2.8+</td>
<td>JWT token issuance and session validation</td>
</tr>
<tr>
<td>Uvicorn</td>
<td>Production ASGI server</td>
</tr>
<tr>
<td>httpx 0.27+</td>
<td>Async HTTP client for external integrations</td>
</tr>

<tr>
<td rowspan="4"><strong>Bot</strong></td>
<td>discord.py (modern async)</td>
<td>Event-driven Discord bot with 11 cog modules</td>
</tr>
<tr>
<td>Redis Streams + Pub/Sub</td>
<td>Bidirectional IPC with ACK guarantees and dead-letter queue</td>
</tr>
<tr>
<td>Capsolver API</td>
<td>Cloudflare bypass for automated scraping workflows</td>
</tr>
<tr>
<td>IRC Bridge</td>
<td>IRC-to-Discord relay for live game event streaming</td>
</tr>

<tr>
<td rowspan="3"><strong>Task Queue</strong></td>
<td>Celery 5.4+</td>
<td>Distributed task workers for async background operations</td>
</tr>
<tr>
<td>Celery Beat</td>
<td>Periodic scheduler — voting auto-close, forum refresh, activity publishing</td>
</tr>
<tr>
<td>Redis (broker + backend)</td>
<td>Task queue transport and result storage</td>
</tr>

<tr>
<td rowspan="8"><strong>Frontend</strong></td>
<td>React 19.2+</td>
<td>UI framework with concurrent rendering features</td>
</tr>
<tr>
<td>Vite (rolldown)</td>
<td>Next-gen build tooling with instant HMR</td>
</tr>
<tr>
<td>React Router 7.13+</td>
<td>SPA routing with protected and public route splits</td>
</tr>
<tr>
<td>Redux Toolkit 2.11+ + SWR 2.4+</td>
<td>Global state (Redux Persist) + server state with automatic revalidation</td>
</tr>
<tr>
<td>HeroUI v3 + Tailwind CSS v4</td>
<td>Component library with utility-first responsive styling</td>
</tr>
<tr>
<td>React Hook Form + Zod 4.3+</td>
<td>Form state management with schema validation</td>
</tr>
<tr>
<td>Framer Motion 12</td>
<td>Route and component-level animations</td>
</tr>
<tr>
<td>Lucide + Iconify</td>
<td>Comprehensive icon system across all UI surfaces</td>
</tr>

<tr>
<td rowspan="3"><strong>Infrastructure</strong></td>
<td>PostgreSQL 15+</td>
<td>Primary relational data store</td>
</tr>
<tr>
<td>Redis 7+</td>
<td>Multi-DB setup: app cache, Celery broker, Celery results</td>
</tr>
<tr>
<td>Bunny CDN</td>
<td>Object storage for file and image uploads</td>
</tr>

</tbody>
</table>

---

## Key Features

<table>
<tr>
<td width="50%" valign="top">

<h3>Discord Bot — 11 Cogs</h3>

- **Modular cog system** — events, tasks, guild management, voting, activity monitoring, player management, color commands, IRC relay, group chat watcher, and administration
- **Cloudflare-bypass scraper** via Capsolver for automated data collection from protected sites
- **IRC-to-Discord bridge** for live game score and event streaming
- **Real-time IPC** — listens on Redis Streams for backend-dispatched commands with a 5-second ACK SLA and dead-letter queue for failed/timeout commands

<h3>Recruitment System</h3>

- Public application submission with automated eligibility precheck (denial cooldown enforcement, blacklist block)
- Application decision workflow: accept / deny / cooldown
- Integrated voting on applications with per-voter comment support
- Voting auto-close with configurable maximum duration via Celery Beat

</td>
<td width="50%" valign="top">

<h3>Backend API — 21 Route Modules</h3>

- **Discord OAuth2** login flow with JWT + HttpOnly cookie session
- **RBAC** — Discord roles map to a permission catalog; every endpoint is guarded server-side
- **Verification gate** — non-owner members must complete verification before accessing restricted actions
- **Two-step config approval** — editor proposes change, approver confirms; full history with rollback
- **Tag-based Redis cache** with intelligent per-module TTL and invalidation strategies

<h3>Admin &amp; Observability</h3>

- **Full audit trail** — every mutation captured with actor, timestamp, and before/after snapshot in `audit_events`
- **Rate limiting** with token-bucket algorithm and anomaly detection
- **Request correlation IDs** propagated through every log line for full trace continuity
- **Health, deep-health, and metrics endpoints** for uptime monitoring and alerting

</td>
</tr>
<tr>
<td width="50%" valign="top">

<h3>Member Management</h3>

- **Global playerbase registry** — in-game names, account names, MTA serials
- **Roster and rank management** with activity participation tracking
- **Player punishments** (warnings, bans) per registry record
- **Vacation requests** with approval workflow and configurable role-threshold policies
- **Verification onboarding flow** for new members with admin review

</td>
<td width="50%" valign="top">

<h3>Blacklist System</h3>

- Human-readable entry IDs (`BL001C-X` format)
- Configurable severity levels
- Full audit history of every blacklist state change
- Public removal request submission portal
- Admin approval/denial workflow for removal requests

</td>
</tr>
<tr>
<td width="50%" valign="top">

<h3>Activity Tracking</h3>

- Workflow-driven lifecycle: <code>pending → approved → published</code>
- Participant tracking per activity instance
- Patrol, training, and event type support
- Celery-powered automatic publishing on configurable schedule

</td>
<td width="50%" valign="top">

<h3>React Dashboard</h3>

- Feature-first module structure (17 feature modules)
- Dark-mode UI with animated route transitions via Framer Motion
- Responsive sidebar (persistent desktop, drawer mobile)
- Notification center with unread badge and admin broadcast
- Permission matrix editor with multi-select role assignment

</td>
</tr>
</table>

---

## Project Structure

<pre>
codeblack-system/
├── backend/
│   ├── api/
│   │   ├── routes/          # 21 REST route modules
│   │   ├── deps/            # Auth, permission & context dependency injection
│   │   └── schemas/         # Pydantic request/response DTOs
│   ├── application/
│   │   ├── services/        # Business logic layer
│   │   └── dto/             # Internal data transfer objects
│   ├── core/                # Config, DB, auth, logging, observability, rate-limiting
│   ├── domain/              # RBAC permission catalog and domain policies
│   └── infrastructure/
│       ├── db/models/       # 17 SQLAlchemy ORM models
│       ├── repositories/    # Data access layer
│       ├── cache/           # Redis cache adapter (TTL + tag invalidation)
│       ├── storage/         # Bunny CDN uploader
│       └── ipc/             # Redis Streams IPC client
│
├── bot/
│   ├── cogs/                # 11 Discord cog modules
│   ├── core/                # DB, Redis, IPC manager
│   ├── services/            # Activity, event, forum, player, scraper services
│   ├── models/              # Bot-side ORM models
│   └── repositories/        # Bot-side data access
│
├── frontend/
│   └── src/
│       ├── app/             # Providers, router, Redux store
│       ├── core/            # API client, auth, permissions
│       ├── shared/          # Layout, UI components, hooks
│       └── features/        # 17 feature modules
│
├── shared/                  # Shared Celery configuration
├── migrations/              # Alembic revisions
├── main.py                  # Bot entry point
├── celery_worker.py         # Celery worker entry point
└── .env.example             # Environment variable template
</pre>

---

## Database Schema — 17 Models

<table>
<tr>
<td><strong>Auth &amp; Identity</strong></td>
<td><code>users</code>, <code>discord_roles</code>, <code>user_discord_roles</code>, <code>user_sessions</code>, <code>user_permissions</code>, <code>discord_role_permissions</code></td>
</tr>
<tr>
<td><strong>Recruitment</strong></td>
<td><code>applications</code>, <code>application_decisions</code>, <code>application_eligibility_state</code></td>
</tr>
<tr>
<td><strong>Guild</strong></td>
<td><code>playerbase</code>, <code>group_memberships</code>, <code>group_ranks</code>, <code>group_roster</code>, <code>player_punishments</code></td>
</tr>
<tr>
<td><strong>Workflows</strong></td>
<td><code>group_activities</code>, <code>activity_participants</code>, <code>orders</code>, <code>vacation_requests</code></td>
</tr>
<tr>
<td><strong>Voting</strong></td>
<td><code>voting_contexts</code>, <code>voting_votes</code>, <code>voting_events</code></td>
</tr>
<tr>
<td><strong>Blacklist</strong></td>
<td><code>blacklist_entries</code>, <code>blacklist_history</code>, <code>blacklist_removal_requests</code></td>
</tr>
<tr>
<td><strong>Config &amp; Audit</strong></td>
<td><code>config_registry</code>, <code>config_change_history</code>, <code>notifications</code>, <code>notification_deliveries</code>, <code>audit_events</code>, <code>verification_requests</code>, <code>landing_posts</code></td>
</tr>
</table>

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### 1. Clone and configure

```bash
git clone https://github.com/AbdulrahmanMonged/codeblack-system.git
cd codeblack-system
cp .env.example .env
# Edit .env — Discord credentials, database, Redis, JWT secret, etc.
```

### 2. Backend

```bash
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload
```

### 3. Bot

```bash
python main.py
```

### 4. Celery workers

```bash
# Worker
celery -A celery_worker.celery_app worker --loglevel=info

# Beat scheduler
celery -A celery_worker.celery_app beat --loglevel=info
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

<table>
<tr>
<th>Group</th>
<th>Key Variables</th>
</tr>
<tr>
<td><strong>Discord</strong></td>
<td><code>DISCORD_BOT_TOKEN</code>, <code>DISCORD_CLIENT_ID</code>, <code>DISCORD_CLIENT_SECRET</code>, <code>DISCORD_GUILD_ID</code>, <code>DISCORD_REDIRECT_URI</code></td>
</tr>
<tr>
<td><strong>Database</strong></td>
<td><code>POSTGRES_HOST</code>, <code>POSTGRES_PORT</code>, <code>POSTGRES_USER</code>, <code>POSTGRES_PASSWORD</code>, <code>POSTGRES_DB</code></td>
</tr>
<tr>
<td><strong>Redis</strong></td>
<td><code>REDIS_URL</code> (cache), <code>CELERY_BROKER_URL</code> (queue), <code>CELERY_RESULT_BACKEND</code> (results)</td>
</tr>
<tr>
<td><strong>Auth</strong></td>
<td><code>JWT_SECRET</code>, <code>JWT_ALGORITHM</code>, <code>JWT_EXP_MINUTES</code></td>
</tr>
<tr>
<td><strong>CDN</strong></td>
<td><code>BUNNY_STORAGE_*</code></td>
</tr>
<tr>
<td><strong>Scraping</strong></td>
<td><code>CAPSOLVER_API_KEY</code>, <code>CF_PROXY</code></td>
</tr>
<tr>
<td><strong>Forum</strong></td>
<td><code>CIT_USERNAME</code>, <code>CIT_PASSWORD</code></td>
</tr>
<tr>
<td><strong>IRC</strong></td>
<td><code>IRC_SERVER</code>, <code>IRC_PORT</code>, <code>IRC_CHANNEL</code>, <code>IRC_NICKNAME</code></td>
</tr>
</table>

See [`.env.example`](.env.example) for the full reference.

---

## Design Principles

<table>
<tr>
<td><strong>Async-first</strong></td>
<td>FastAPI + SQLAlchemy 2.0 async + asyncpg throughout — no blocking I/O on any hot path</td>
</tr>
<tr>
<td><strong>Unified schema</strong></td>
<td>Bot and backend share the same PostgreSQL schema through a single ORM layer, eliminating data sync bugs by design</td>
</tr>
<tr>
<td><strong>Reliable IPC</strong></td>
<td>Redis Streams with ACK timeout and dead-letter queue — no bot command is silently dropped</td>
</tr>
<tr>
<td><strong>Audit everything</strong></td>
<td>Every state mutation is recorded in <code>audit_events</code> with before/after snapshots and the acting user identity</td>
</tr>
<tr>
<td><strong>Defense in depth</strong></td>
<td>RBAC + verification gate + rate limiting + anomaly detection all stack independently</td>
</tr>
<tr>
<td><strong>Observable by default</strong></td>
<td>Structured logging, correlation IDs, health endpoints, and metrics built in from day one — not bolted on</td>
</tr>
</table>

---

## License

Released under the [MIT License](LICENSE).

---

<div align="center">
<sub>Built with precision for large-scale Discord communities.</sub>
</div>
