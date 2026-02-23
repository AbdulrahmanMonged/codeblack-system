from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.application.services.notification_service import NotificationService
from backend.infrastructure.ipc.stream_client import BackendIPCClient
from backend.infrastructure.repositories.activity_repository import ActivityRepository
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)
from backend.infrastructure.repositories.roster_repository import RosterRepository


class ActivityService:
    PUBLISH_QUEUE_ENABLED_KEY = "activities.publish_queue_enabled"
    PUBLISH_QUEUE_BATCH_LIMIT_KEY = "activities.publish_batch_limit"
    PUBLISH_QUEUE_RETRY_DELAY_SECONDS_KEY = "activities.publish_retry_delay_seconds"
    PUBLISH_QUEUE_MAX_ATTEMPTS_KEY = "activities.publish_max_attempts"

    DEFAULT_PUBLISH_QUEUE_ENABLED = True
    DEFAULT_PUBLISH_QUEUE_BATCH_LIMIT = 25
    DEFAULT_PUBLISH_QUEUE_RETRY_DELAY_SECONDS = 300
    DEFAULT_PUBLISH_QUEUE_MAX_ATTEMPTS = 5

    def __init__(self):
        self.settings = get_settings()

    async def create_activity(
        self,
        *,
        activity_type: str,
        title: str,
        duration_minutes: int,
        notes: str | None,
        created_by_user_id: int,
        scheduled_for,
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            row = await repo.create_activity(
                public_id=self._public_id(),
                activity_type=activity_type,
                title=title,
                duration_minutes=duration_minutes,
                notes=notes,
                status="pending",
                created_by_user_id=created_by_user_id,
                approved_by_user_id=None,
                approval_comment=None,
                scheduled_for=scheduled_for,
                forum_topic_id=None,
                forum_post_id=None,
                publish_attempts=0,
                last_publish_error=None,
                last_publish_attempt_at=None,
            )
            return await self._activity_to_dict(repo, row)

    async def list_activities(
        self,
        *,
        status: str | None,
        activity_type: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = ActivityRepository(session)
            rows = await repo.list_activities(
                status=status,
                activity_type=activity_type,
                limit=limit,
                offset=offset,
            )
            result = []
            for row in rows:
                result.append(await self._activity_to_dict(repo, row))
            return result

    async def get_activity(self, *, public_id: str) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACTIVITY_NOT_FOUND",
                    message=f"Activity {public_id} not found",
                )
            return await self._activity_to_dict(repo, row)

    async def approve_activity(
        self,
        *,
        public_id: str,
        approver_user_id: int,
        approval_comment: str | None,
        scheduled_for,
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            notification_service = NotificationService()
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACTIVITY_NOT_FOUND",
                    message=f"Activity {public_id} not found",
                )
            if row.status not in {"pending", "approved", "scheduled"}:
                raise ApiException(
                    status_code=409,
                    error_code="ACTIVITY_INVALID_STATE",
                    message=f"Cannot approve activity in status={row.status}",
                )
            row.approved_by_user_id = approver_user_id
            row.approval_comment = approval_comment
            if scheduled_for is not None:
                row.scheduled_for = scheduled_for
            row.status = "scheduled" if row.scheduled_for else "approved"

            title = (
                f"Activity scheduled: {row.title}"
                if row.status == "scheduled"
                else f"Activity approved: {row.title}"
            )
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=approver_user_id,
                event_type=f"activities.{row.status}",
                category="activities",
                severity="success",
                title=title,
                body=(
                    f"Activity {row.public_id} was {row.status}."
                    if not approval_comment
                    else f"Activity {row.public_id} was {row.status}. Reviewer comment: {approval_comment}"
                ),
                entity_type="activity",
                entity_public_id=row.public_id,
                metadata_json={
                    "status": row.status,
                    "activity_type": row.activity_type,
                    "scheduled_for": row.scheduled_for.isoformat()
                    if row.scheduled_for
                    else None,
                },
            )
            return await self._activity_to_dict(repo, row, refresh=True)

    async def publish_to_forum(
        self,
        *,
        public_id: str,
        actor_user_id: int | None,
        forum_topic_id: str | None,
        force_retry: bool,
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            notification_service = NotificationService()
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACTIVITY_NOT_FOUND",
                    message=f"Activity {public_id} not found",
                )
            return await self._publish_row_to_forum(
                session=session,
                repo=repo,
                notification_service=notification_service,
                row=row,
                actor_user_id=actor_user_id,
                forum_topic_id=forum_topic_id,
                force_retry=force_retry,
                strict=True,
            )

    async def process_publish_queue_tick(self) -> dict:
        now = self._now_utc()
        async with get_session() as session:
            config_repo = ConfigRegistryRepository(session)
            queue_policy = await self._resolve_publish_queue_policy(config_repo)
            if not queue_policy["enabled"]:
                return {
                    "enabled": False,
                    "processed_count": 0,
                    "scheduled_due_count": 0,
                    "retry_candidates_count": 0,
                    "processed": [],
                }

            repo = ActivityRepository(session)
            notification_service = NotificationService()
            batch_limit = queue_policy["batch_limit"]
            scheduled_due = list(
                await repo.list_due_scheduled_for_publish(
                    now=now,
                    limit=batch_limit,
                )
            )
            remaining_capacity = max(0, batch_limit - len(scheduled_due))

            retry_before = now - timedelta(seconds=queue_policy["retry_delay_seconds"])
            retry_candidates = (
                list(
                    await repo.list_retryable_publish_failures(
                        retry_before=retry_before,
                        max_attempts=queue_policy["max_attempts"],
                        limit=remaining_capacity,
                    )
                )
                if remaining_capacity > 0
                else []
            )

            processed: list[dict] = []
            for row in [*scheduled_due, *retry_candidates]:
                result = await self._publish_row_to_forum(
                    session=session,
                    repo=repo,
                    notification_service=notification_service,
                    row=row,
                    actor_user_id=None,
                    forum_topic_id=None,
                    force_retry=True,
                    strict=False,
                )
                processed.append(
                    {
                        "public_id": row.public_id,
                        "status": result["activity"]["status"],
                        "dispatch_acknowledged": bool(result["dispatch"].get("acknowledged")),
                        "dispatch_error": result["dispatch"].get("error"),
                    }
                )

            return {
                "enabled": True,
                "processed_count": len(processed),
                "scheduled_due_count": len(scheduled_due),
                "retry_candidates_count": len(retry_candidates),
                "queue_policy": queue_policy,
                "processed": processed,
            }

    async def reject_activity(
        self,
        *,
        public_id: str,
        approver_user_id: int,
        approval_comment: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            notification_service = NotificationService()
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACTIVITY_NOT_FOUND",
                    message=f"Activity {public_id} not found",
                )
            row.approved_by_user_id = approver_user_id
            row.approval_comment = approval_comment
            row.status = "rejected"

            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=approver_user_id,
                event_type="activities.rejected",
                category="activities",
                severity="warning",
                title=f"Activity rejected: {row.title}",
                body=(
                    f"Activity {row.public_id} was rejected."
                    if not approval_comment
                    else f"Activity {row.public_id} was rejected. Reviewer comment: {approval_comment}"
                ),
                entity_type="activity",
                entity_public_id=row.public_id,
                metadata_json={
                    "status": row.status,
                    "activity_type": row.activity_type,
                },
            )
            return await self._activity_to_dict(repo, row, refresh=True)

    async def add_participant(
        self,
        *,
        public_id: str,
        player_id: int,
        participant_role: str,
        attendance_status: str,
        notes: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            roster_repo = RosterRepository(session)
            activity = await repo.get_by_public_id(public_id)
            if activity is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACTIVITY_NOT_FOUND",
                    message=f"Activity {public_id} not found",
                )
            player = await roster_repo.get_player_by_id(player_id)
            if player is None:
                raise ApiException(
                    status_code=404,
                    error_code="PLAYER_NOT_FOUND",
                    message=f"Player {player_id} not found",
                )
            participant = await repo.add_participant(
                activity_id=activity.id,
                player_id=player.id,
                participant_role=participant_role,
                attendance_status=attendance_status,
                notes=notes,
            )
            return {
                "id": participant.id,
                "activity_id": participant.activity_id,
                "player_id": participant.player_id,
                "participant_role": participant.participant_role,
                "attendance_status": participant.attendance_status,
                "notes": participant.notes,
                "created_at": participant.created_at,
            }

    @staticmethod
    def _public_id() -> str:
        return f"ACT-{uuid4().hex[:12].upper()}"

    async def _activity_to_dict(
        self, repo: ActivityRepository, row, *, refresh: bool = False
    ) -> dict:
        if refresh:
            await repo.session.flush()
            await repo.session.refresh(row)
        participants = await repo.list_participants(row.id)
        return {
            "public_id": row.public_id,
            "activity_type": row.activity_type,
            "title": row.title,
            "duration_minutes": row.duration_minutes,
            "notes": row.notes,
            "status": row.status,
            "created_by_user_id": row.created_by_user_id,
            "approved_by_user_id": row.approved_by_user_id,
            "approval_comment": row.approval_comment,
            "scheduled_for": row.scheduled_for,
            "forum_topic_id": row.forum_topic_id,
            "forum_post_id": row.forum_post_id,
            "publish_attempts": row.publish_attempts,
            "last_publish_error": row.last_publish_error,
            "last_publish_attempt_at": row.last_publish_attempt_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "participants": [
                {
                    "id": item.id,
                    "player_id": item.player_id,
                    "participant_role": item.participant_role,
                    "attendance_status": item.attendance_status,
                    "notes": item.notes,
                }
                for item in participants
            ],
        }

    async def _publish_row_to_forum(
        self,
        *,
        session,
        repo: ActivityRepository,
        notification_service: NotificationService,
        row,
        actor_user_id: int | None,
        forum_topic_id: str | None,
        force_retry: bool,
        strict: bool,
    ) -> dict:
        if row.status not in {"approved", "scheduled", "publish_failed"}:
            if strict:
                raise ApiException(
                    status_code=409,
                    error_code="ACTIVITY_INVALID_PUBLISH_STATE",
                    message=f"Cannot publish activity in status={row.status}",
                )
            return {
                "activity": await self._activity_to_dict(repo, row, refresh=True),
                "dispatch": {
                    "acknowledged": False,
                    "error": f"invalid_status:{row.status}",
                    "response": None,
                    "dead_lettered": False,
                    "dead_letter_id": None,
                },
            }

        if row.forum_post_id and not force_retry:
            if strict:
                raise ApiException(
                    status_code=409,
                    error_code="ACTIVITY_ALREADY_PUBLISHED",
                    message="Activity already has forum_post_id. Use force_retry=true to republish.",
                )
            return {
                "activity": await self._activity_to_dict(repo, row, refresh=True),
                "dispatch": {
                    "acknowledged": False,
                    "error": "already_published",
                    "response": None,
                    "dead_lettered": False,
                    "dead_letter_id": None,
                },
            }

        target_topic_id = forum_topic_id.strip() if forum_topic_id else row.forum_topic_id
        if not target_topic_id:
            if strict:
                raise ApiException(
                    status_code=422,
                    error_code="ACTIVITY_FORUM_TOPIC_REQUIRED",
                    message="forum_topic_id is required to publish activity",
                )
            row.publish_attempts += 1
            row.status = "publish_failed"
            row.last_publish_attempt_at = self._now_utc()
            row.last_publish_error = "forum_topic_id is required to publish activity"
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type="activities.publish_failed",
                category="activities",
                severity="warning",
                title=f"Activity publish failed: {row.title}",
                body=f"Activity {row.public_id} publish attempt failed due to missing forum topic.",
                entity_type="activity",
                entity_public_id=row.public_id,
                metadata_json={
                    "error_code": "ACTIVITY_FORUM_TOPIC_REQUIRED",
                    "publish_attempts": row.publish_attempts,
                },
            )
            return {
                "activity": await self._activity_to_dict(repo, row, refresh=True),
                "dispatch": {
                    "acknowledged": False,
                    "error": "ACTIVITY_FORUM_TOPIC_REQUIRED",
                    "response": None,
                    "dead_lettered": False,
                    "dead_letter_id": None,
                },
            }

        row.publish_attempts += 1
        row.last_publish_attempt_at = self._now_utc()
        row.last_publish_error = None

        dispatch = await self._dispatch_publish_command(
            actor_user_id=actor_user_id,
            activity=row,
            forum_topic_id=target_topic_id,
        )
        response_payload = dispatch.get("response") if isinstance(dispatch, dict) else None
        result_payload = response_payload.get("result") if isinstance(response_payload, dict) else None
        published_ok = bool(dispatch.get("acknowledged")) and bool(
            isinstance(result_payload, dict) and result_payload.get("success")
        )

        if published_ok:
            row.status = "posted"
            row.forum_topic_id = str(result_payload.get("topic_number") or target_topic_id)
            post_id = result_payload.get("post_id")
            row.forum_post_id = str(post_id) if post_id is not None else row.forum_post_id
            row.last_publish_error = None
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type="activities.posted",
                category="activities",
                severity="success",
                title=f"Activity posted: {row.title}",
                body=f"Activity {row.public_id} was posted to forum topic {row.forum_topic_id}.",
                entity_type="activity",
                entity_public_id=row.public_id,
                metadata_json={
                    "forum_topic_id": row.forum_topic_id,
                    "forum_post_id": row.forum_post_id,
                    "publish_attempts": row.publish_attempts,
                },
            )
        else:
            row.status = "publish_failed"
            row.last_publish_error = str(dispatch.get("error") or "publish_failed")
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type="activities.publish_failed",
                category="activities",
                severity="warning",
                title=f"Activity publish failed: {row.title}",
                body=f"Activity {row.public_id} publish attempt failed.",
                entity_type="activity",
                entity_public_id=row.public_id,
                metadata_json={
                    "dispatch": dispatch,
                    "publish_attempts": row.publish_attempts,
                },
            )

        activity_payload = await self._activity_to_dict(repo, row, refresh=True)
        return {
            "activity": activity_payload,
            "dispatch": dispatch,
        }

    async def _resolve_publish_queue_policy(self, config_repo: ConfigRegistryRepository) -> dict:
        enabled_row = await config_repo.get_by_key(self.PUBLISH_QUEUE_ENABLED_KEY)
        batch_limit_row = await config_repo.get_by_key(self.PUBLISH_QUEUE_BATCH_LIMIT_KEY)
        retry_delay_row = await config_repo.get_by_key(self.PUBLISH_QUEUE_RETRY_DELAY_SECONDS_KEY)
        max_attempts_row = await config_repo.get_by_key(self.PUBLISH_QUEUE_MAX_ATTEMPTS_KEY)

        enabled = self.DEFAULT_PUBLISH_QUEUE_ENABLED
        if enabled_row and isinstance(enabled_row.value_json, bool):
            enabled = enabled_row.value_json

        batch_limit = self.DEFAULT_PUBLISH_QUEUE_BATCH_LIMIT
        if batch_limit_row and isinstance(batch_limit_row.value_json, int):
            batch_limit = max(1, min(200, batch_limit_row.value_json))

        retry_delay_seconds = self.DEFAULT_PUBLISH_QUEUE_RETRY_DELAY_SECONDS
        if retry_delay_row and isinstance(retry_delay_row.value_json, int):
            retry_delay_seconds = max(5, min(86400, retry_delay_row.value_json))

        max_attempts = self.DEFAULT_PUBLISH_QUEUE_MAX_ATTEMPTS
        if max_attempts_row and isinstance(max_attempts_row.value_json, int):
            max_attempts = max(1, min(50, max_attempts_row.value_json))

        return {
            "enabled": enabled,
            "batch_limit": batch_limit,
            "retry_delay_seconds": retry_delay_seconds,
            "max_attempts": max_attempts,
        }

    async def _dispatch_publish_command(
        self,
        *,
        actor_user_id: int | None,
        activity,
        forum_topic_id: str,
    ) -> dict:
        ipc = BackendIPCClient()
        try:
            return await ipc.dispatch_command_with_retry(
                command_type="publish_activity_forum",
                actor_user_id=actor_user_id if actor_user_id is not None else 0,
                payload={
                    "activity_public_id": activity.public_id,
                    "activity_type": activity.activity_type,
                    "title": activity.title,
                    "duration_minutes": activity.duration_minutes,
                    "notes": activity.notes,
                    "scheduled_for": activity.scheduled_for.isoformat()
                    if activity.scheduled_for
                    else None,
                    "forum_topic_id": forum_topic_id,
                },
                timeout_seconds=self.settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
            )
        finally:
            await ipc.close()

    @staticmethod
    def _now_utc():
        return datetime.now(timezone.utc)
