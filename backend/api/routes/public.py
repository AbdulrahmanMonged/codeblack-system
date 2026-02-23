from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.schemas.landing import (
    LandingPostResponse,
    PublicMetricsResponse,
    PublicRosterEntryResponse,
)
from backend.application.services.landing_service import LandingService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_landing_service() -> LandingService:
    return LandingService()


@router.get("/posts", response_model=list[LandingPostResponse])
async def list_public_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: LandingService = Depends(get_landing_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "public_posts",
        {"limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [LandingPostResponse(**row) for row in cached]

    rows = await service.list_posts(
        published_only=True,
        limit=limit,
        offset=offset,
    )
    payload = [LandingPostResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_PUBLIC_TTL_SECONDS,
        tags={"public_posts"},
    )
    return [LandingPostResponse(**row) for row in payload]


@router.get("/posts/{public_id}", response_model=LandingPostResponse)
async def get_public_post(
    public_id: str,
    service: LandingService = Depends(get_landing_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "public_post_detail",
        {"public_id": public_id},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return LandingPostResponse(**cached)

    row = await service.get_post(public_id=public_id, published_only=True)
    payload = LandingPostResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_PUBLIC_TTL_SECONDS,
        tags={"public_posts"},
    )
    return LandingPostResponse(**payload)


@router.get("/metrics", response_model=PublicMetricsResponse)
async def get_public_metrics(
    service: LandingService = Depends(get_landing_service),
):
    settings = get_settings()
    cache_key = cache.build_key("public_metrics")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return PublicMetricsResponse(**cached)

    row = await service.get_public_metrics()
    payload = PublicMetricsResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_PUBLIC_TTL_SECONDS,
        tags={"public_metrics"},
    )
    return PublicMetricsResponse(**payload)


@router.get("/roster", response_model=list[PublicRosterEntryResponse])
async def list_public_roster(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: LandingService = Depends(get_landing_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "public_roster",
        {"limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [PublicRosterEntryResponse(**row) for row in cached]

    rows = await service.list_public_roster(limit=limit, offset=offset)
    payload = [PublicRosterEntryResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_PUBLIC_TTL_SECONDS,
        tags={"public_roster"},
    )
    return [PublicRosterEntryResponse(**row) for row in payload]
