from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import require_any_permissions, require_permissions
from backend.api.schemas.orders import OrderDecisionRequest, OrderResponse
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.order_service import OrderService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache
from backend.infrastructure.storage.uploader import StorageUploader

router = APIRouter()


def get_order_service() -> OrderService:
    return OrderService()


@router.post("", response_model=OrderResponse)
async def submit_order(
    ingame_name: str = Form(min_length=2, max_length=255),
    completed_orders: str = Form(min_length=1),
    proof_image: UploadFile = File(...),
    principal: AuthenticatedPrincipal = Depends(require_permissions("orders.submit")),
    service: OrderService = Depends(get_order_service),
):
    proof_bytes, proof_content_type, proof_ext = await _validate_proof_image(proof_image)
    uploader = StorageUploader()
    uploaded = await uploader.upload_bytes(
        key=f"orders/{principal.discord_user_id}/{uuid4().hex}_proof.{proof_ext}",
        data=proof_bytes,
        content_type=proof_content_type,
    )
    row = await service.submit_order(
        principal=principal,
        ingame_name=ingame_name,
        completed_orders=completed_orders,
        proof_upload=uploaded,
    )
    await cache.invalidate_tags("orders", "review_queue", f"orders_user:{principal.user_id}")
    return OrderResponse(**row)


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AuthenticatedPrincipal = Depends(require_permissions("orders.read")),
    service: OrderService = Depends(get_order_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "orders_list",
        {"status": status, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [OrderResponse(**row) for row in cached]

    rows = await service.list_orders(status=status, limit=limit, offset=offset)
    payload = [OrderResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"orders"},
    )
    return [OrderResponse(**row) for row in payload]


@router.get("/mine", response_model=list[OrderResponse])
async def list_my_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(require_any_permissions("orders.submit", "orders.read")),
    service: OrderService = Depends(get_order_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "orders_mine_list",
        {
            "user_id": principal.user_id,
            "status": status,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [OrderResponse(**row) for row in cached]

    rows = await service.list_orders_by_submitter(
        submitted_by_user_id=principal.user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    payload = [OrderResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"orders", f"orders_user:{principal.user_id}"},
    )
    return [OrderResponse(**row) for row in payload]


@router.get("/{public_id}", response_model=OrderResponse)
async def get_order(
    public_id: str,
    _: AuthenticatedPrincipal = Depends(require_permissions("orders.read")),
    service: OrderService = Depends(get_order_service),
):
    row = await service.get_order(public_id=public_id)
    return OrderResponse(**row)


@router.post("/{public_id}/decision", response_model=OrderResponse)
async def decide_order(
    public_id: str,
    payload: OrderDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("orders.review")),
    service: OrderService = Depends(get_order_service),
):
    if payload.decision == "accepted" and not principal.is_owner:
        if "orders.decision.accept" not in principal.permissions:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="Missing orders.decision.accept permission",
            )
    if payload.decision == "denied" and not principal.is_owner:
        if "orders.decision.deny" not in principal.permissions:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="Missing orders.decision.deny permission",
            )

    row = await service.decide_order(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        decision=payload.decision,
        reason=payload.reason,
    )
    await cache.invalidate_tags("orders", "review_queue", f"orders_user:{row['submitted_by_user_id']}")
    return OrderResponse(**row)


async def _validate_proof_image(upload: UploadFile) -> tuple[bytes, str, str]:
    allowed = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }
    content_type = upload.content_type or ""
    if content_type not in allowed:
        raise ApiException(
            status_code=422,
            error_code="INVALID_PROOF_IMAGE_TYPE",
            message="proof_image must be png, jpeg, or webp",
        )
    data = await upload.read()
    if not data:
        raise ApiException(
            status_code=422,
            error_code="EMPTY_PROOF_IMAGE",
            message="proof_image cannot be empty",
        )
    if len(data) > 10 * 1024 * 1024:
        raise ApiException(
            status_code=422,
            error_code="PROOF_IMAGE_TOO_LARGE",
            message="proof_image must be <= 10MB",
        )
    return data, content_type, allowed[content_type]
