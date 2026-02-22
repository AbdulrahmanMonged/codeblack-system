from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.landing import (
    LandingPostCreateRequest,
    LandingPostMediaUploadResponse,
    LandingPostPublishRequest,
    LandingPostResponse,
    LandingPostUpdateRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.landing_service import LandingService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache
from backend.infrastructure.storage.uploader import StorageUploader

router = APIRouter()


def get_landing_service() -> LandingService:
    return LandingService()


@router.get("", response_model=list[LandingPostResponse])
async def list_posts(
    published_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("posts.read")),
    service: LandingService = Depends(get_landing_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "posts",
        {"published_only": published_only, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [LandingPostResponse(**row) for row in cached]

    rows = await service.list_posts(
        published_only=published_only,
        limit=limit,
        offset=offset,
    )
    payload = [LandingPostResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"posts"},
    )
    return [LandingPostResponse(**row) for row in payload]


@router.post("", response_model=LandingPostResponse)
async def create_post(
    payload: LandingPostCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("posts.write")),
    service: LandingService = Depends(get_landing_service),
):
    row = await service.create_post(
        title=payload.title,
        content=payload.content,
        media_url=payload.media_url,
        created_by_user_id=principal.user_id,
    )
    await cache.invalidate_tags("posts", "public_posts")
    return LandingPostResponse(**row)


@router.patch("/{public_id}", response_model=LandingPostResponse)
async def update_post(
    public_id: str,
    payload: LandingPostUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("posts.write")),
    service: LandingService = Depends(get_landing_service),
):
    row = await service.update_post(
        public_id=public_id,
        title=payload.title,
        content=payload.content,
        media_url=payload.media_url,
        updated_by_user_id=principal.user_id,
    )
    await cache.invalidate_tags("posts", "public_posts")
    return LandingPostResponse(**row)


@router.post("/{public_id}/publish", response_model=LandingPostResponse)
async def set_post_publish_state(
    public_id: str,
    payload: LandingPostPublishRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("posts.publish")),
    service: LandingService = Depends(get_landing_service),
):
    row = await service.set_post_publish_state(
        public_id=public_id,
        is_published=payload.is_published,
        updated_by_user_id=principal.user_id,
    )
    await cache.invalidate_tags("posts", "public_posts")
    return LandingPostResponse(**row)


@router.post("/media/upload", response_model=LandingPostMediaUploadResponse)
async def upload_post_media(
    media_file: UploadFile = File(...),
    principal: AuthenticatedPrincipal = Depends(require_permissions("posts.write")),
):
    data, content_type, ext = await _validate_post_media_upload(media_file)
    uploader = StorageUploader()
    uploaded = await uploader.upload_bytes(
        key=f"posts/{principal.discord_user_id}/{uuid4().hex}_attachment.{ext}",
        data=data,
        content_type=content_type,
    )
    return LandingPostMediaUploadResponse(
        media_url=uploaded.url,
        media_key=uploaded.key,
        content_type=uploaded.content_type,
        size_bytes=uploaded.size_bytes,
    )


async def _validate_post_media_upload(upload: UploadFile) -> tuple[bytes, str, str]:
    allowed = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    content_type = upload.content_type or ""
    if content_type not in allowed:
        raise ApiException(
            status_code=422,
            error_code="INVALID_POST_MEDIA_TYPE",
            message="media_file must be png, jpeg, webp, or gif",
        )
    data = await upload.read()
    if not data:
        raise ApiException(
            status_code=422,
            error_code="EMPTY_POST_MEDIA",
            message="media_file cannot be empty",
        )
    if len(data) > 12 * 1024 * 1024:
        raise ApiException(
            status_code=422,
            error_code="POST_MEDIA_TOO_LARGE",
            message="media_file must be <= 12MB",
        )
    return data, content_type, allowed[content_type]
