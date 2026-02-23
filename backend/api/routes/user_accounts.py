from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps.auth import require_permissions
from backend.api.schemas.orders import AccountLinkResponse, AccountLinkUpsertRequest
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.order_service import OrderService

router = APIRouter()


def get_order_service() -> OrderService:
    return OrderService()


@router.post("/{user_id}/account-link", response_model=AccountLinkResponse)
async def upsert_account_link(
    user_id: int,
    payload: AccountLinkUpsertRequest,
    _: AuthenticatedPrincipal = Depends(require_permissions("user_account_link.write")),
    service: OrderService = Depends(get_order_service),
):
    row = await service.link_user_account(
        user_id=user_id,
        discord_user_id=payload.discord_user_id,
        account_name=payload.account_name,
        is_verified=payload.is_verified,
    )
    return AccountLinkResponse(**row)


@router.get("/{user_id}/account-link", response_model=AccountLinkResponse)
async def get_account_link(
    user_id: int,
    _: AuthenticatedPrincipal = Depends(require_permissions("user_account_link.read")),
    service: OrderService = Depends(get_order_service),
):
    row = await service.get_user_account_link(user_id=user_id)
    return AccountLinkResponse(**row)
