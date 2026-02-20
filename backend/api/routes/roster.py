from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.roster import (
    MembershipCreateRequest,
    MembershipUpdateRequest,
    RankCreateRequest,
    RankResponse,
    RosterMembershipResponse,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.roster_service import RosterService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_roster_service() -> RosterService:
    return RosterService()


@router.get("", response_model=list[RosterMembershipResponse])
async def list_roster(
    _: object = Depends(require_permissions("roster.read")),
    service: RosterService = Depends(get_roster_service),
):
    settings = get_settings()
    cache_key = cache.build_key("roster_list")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [RosterMembershipResponse(**row) for row in cached]

    rows = await service.list_roster()
    payload = [RosterMembershipResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"roster", "public_roster", "public_metrics"},
    )
    return [RosterMembershipResponse(**row) for row in payload]


@router.post("", response_model=RosterMembershipResponse)
async def create_membership(
    payload: MembershipCreateRequest,
    _: object = Depends(require_permissions("roster.write")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.create_membership(
        player_id=payload.player_id,
        status=payload.status,
        joined_at=payload.joined_at,
        current_rank_id=payload.current_rank_id,
        display_rank=payload.display_rank,
        is_on_leave=payload.is_on_leave,
        notes=payload.notes,
    )
    await cache.invalidate_tags("roster", "public_roster", "public_metrics")
    return RosterMembershipResponse(**row)


@router.patch("/{membership_id}", response_model=RosterMembershipResponse)
async def update_membership(
    membership_id: int,
    payload: MembershipUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("roster.write")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.update_membership(
        membership_id=membership_id,
        status=payload.status,
        left_at=payload.left_at,
        current_rank_id=payload.current_rank_id,
        display_rank=payload.display_rank,
        is_on_leave=payload.is_on_leave,
        notes=payload.notes,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("roster", "public_roster", "public_metrics")
    return RosterMembershipResponse(**row)


@router.get("/ranks", response_model=list[RankResponse])
async def list_ranks(
    _: object = Depends(require_permissions("ranks.read")),
    service: RosterService = Depends(get_roster_service),
):
    settings = get_settings()
    cache_key = cache.build_key("roster_ranks")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [RankResponse(**row) for row in cached]

    rows = await service.list_ranks()
    payload = [RankResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"roster"},
    )
    return [RankResponse(**row) for row in payload]


@router.post("/ranks", response_model=RankResponse)
async def create_rank(
    payload: RankCreateRequest,
    _: object = Depends(require_permissions("ranks.write")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.create_rank(
        name=payload.name,
        level=payload.level,
    )
    await cache.invalidate_tags("roster", "public_roster", "public_metrics")
    return RankResponse(**row)
