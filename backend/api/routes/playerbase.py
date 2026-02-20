from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.roster import (
    PlayerCreateRequest,
    PlayerResponse,
    PunishmentCreateRequest,
    PunishmentResponse,
    PunishmentUpdateRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.roster_service import RosterService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_roster_service() -> RosterService:
    return RosterService()


@router.post("", response_model=PlayerResponse)
async def create_player(
    payload: PlayerCreateRequest,
    _: object = Depends(require_permissions("playerbase.write")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.create_player(
        ingame_name=payload.ingame_name,
        account_name=payload.account_name,
        mta_serial=payload.mta_serial,
        country_code=payload.country_code,
    )
    await cache.invalidate_tags("playerbase", "public_metrics")
    return PlayerResponse(**row)


@router.get("", response_model=list[PlayerResponse])
async def list_players(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("playerbase.read")),
    service: RosterService = Depends(get_roster_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "playerbase_list",
        {"limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [PlayerResponse(**row) for row in cached]

    rows = await service.list_players(limit=limit, offset=offset)
    payload = [PlayerResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"playerbase"},
    )
    return [PlayerResponse(**row) for row in payload]


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(
    player_id: int,
    _: object = Depends(require_permissions("playerbase.read")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.get_player(player_id=player_id)
    return PlayerResponse(**row)


@router.post("/{player_id}/punishments", response_model=PunishmentResponse)
async def add_punishment(
    player_id: int,
    payload: PunishmentCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("punishments.write")),
    service: RosterService = Depends(get_roster_service),
):
    row = await service.add_punishment(
        player_id=player_id,
        punishment_type=payload.punishment_type,
        severity=payload.severity,
        reason=payload.reason,
        issued_by_user_id=principal.user_id,
        expires_at=payload.expires_at,
    )
    await cache.invalidate_tags("playerbase")
    return PunishmentResponse(**row)


@router.get("/{player_id}/punishments", response_model=list[PunishmentResponse])
async def list_punishments(
    player_id: int,
    _: object = Depends(require_permissions("punishments.read")),
    service: RosterService = Depends(get_roster_service),
):
    rows = await service.list_punishments(player_id=player_id)
    return [PunishmentResponse(**row) for row in rows]


@router.patch("/{player_id}/punishments/{punishment_id}", response_model=PunishmentResponse)
async def update_punishment(
    player_id: int,
    punishment_id: int,
    payload: PunishmentUpdateRequest,
    _: object = Depends(require_permissions("punishments.write")),
    service: RosterService = Depends(get_roster_service),
):
    _ = player_id
    row = await service.update_punishment(
        punishment_id=punishment_id,
        status=payload.status,
        expires_at=payload.expires_at,
    )
    await cache.invalidate_tags("playerbase")
    return PunishmentResponse(**row)
