from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import require_permissions
from backend.api.schemas.bot_control import (
    BotControlUpdateResponse,
    ChannelConfigResponse,
    ChannelConfigUpdateRequest,
    CommandDispatchResponse,
    DeadLetterEntryResponse,
    DeadLetterReplayResponse,
    FeatureConfigResponse,
    FeatureConfigUpdateRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.bot_control_service import BotControlService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_bot_control_service() -> BotControlService:
    return BotControlService()


@router.get("/channels", response_model=ChannelConfigResponse)
async def get_channels(
    _: object = Depends(require_permissions("bot.read_status")),
    service: BotControlService = Depends(get_bot_control_service),
):
    config = await service.get_channels()
    return ChannelConfigResponse(**config)


@router.put("/channels", response_model=BotControlUpdateResponse)
async def update_channels(
    payload: ChannelConfigUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("bot.configure_channels")),
    service: BotControlService = Depends(get_bot_control_service),
):
    update_payload = payload.model_dump(exclude_unset=True)
    result = await service.update_channels(
        payload=update_payload,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("bot_control")
    return BotControlUpdateResponse(
        config=result["config"],
        dispatch_results=[
            CommandDispatchResponse(**item) for item in result["dispatch_results"]
        ],
    )


@router.get("/features", response_model=FeatureConfigResponse)
async def get_features(
    _: object = Depends(require_permissions("bot.read_status")),
    service: BotControlService = Depends(get_bot_control_service),
):
    config = await service.get_features()
    return FeatureConfigResponse(**config)


@router.put("/features", response_model=BotControlUpdateResponse)
async def update_features(
    payload: FeatureConfigUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("bot.toggle_features")),
    service: BotControlService = Depends(get_bot_control_service),
):
    update_payload = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    result = await service.update_features(
        payload=update_payload,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("bot_control")
    return BotControlUpdateResponse(
        config=result["config"],
        dispatch_results=[
            CommandDispatchResponse(**item) for item in result["dispatch_results"]
        ],
    )


@router.post("/triggers/forum-sync", response_model=CommandDispatchResponse)
async def trigger_forum_sync(
    principal: AuthenticatedPrincipal = Depends(require_permissions("bot.trigger.forum_sync")),
    service: BotControlService = Depends(get_bot_control_service),
):
    result = await service.trigger_forum_sync(actor_user_id=principal.user_id)
    await cache.invalidate_tags("bot_control")
    return CommandDispatchResponse(**result)


@router.post("/triggers/cop-scores-refresh", response_model=CommandDispatchResponse)
async def trigger_cop_scores_refresh(
    principal: AuthenticatedPrincipal = Depends(
        require_permissions("bot.trigger.cop_scores_refresh")
    ),
    service: BotControlService = Depends(get_bot_control_service),
):
    result = await service.trigger_cop_scores_refresh(actor_user_id=principal.user_id)
    await cache.invalidate_tags("bot_control")
    return CommandDispatchResponse(**result)


@router.get("/dead-letter", response_model=list[DeadLetterEntryResponse])
async def list_dead_letter_queue(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("bot.read_status")),
    service: BotControlService = Depends(get_bot_control_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "bot_dead_letter",
        {"limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [DeadLetterEntryResponse(**row) for row in cached]

    rows = await service.list_dead_letters(limit=limit, offset=offset)
    payload = [DeadLetterEntryResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"bot_control"},
    )
    return [DeadLetterEntryResponse(**row) for row in payload]


@router.post("/dead-letter/{dead_letter_id}/replay", response_model=DeadLetterReplayResponse)
async def replay_dead_letter(
    dead_letter_id: str,
    principal: AuthenticatedPrincipal = Depends(require_permissions("bot.replay_dead_letter")),
    service: BotControlService = Depends(get_bot_control_service),
):
    result = await service.replay_dead_letter(
        dead_letter_id=dead_letter_id,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("bot_control")
    return DeadLetterReplayResponse(**result)
