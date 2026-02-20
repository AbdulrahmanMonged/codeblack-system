from __future__ import annotations

import hashlib

from fastapi import Request

from backend.infrastructure.cache.redis_cache import cache


def normalize_account_name(account_name: str) -> str:
    return str(account_name or "").strip().lower()


def resolve_precheck_actor_key(
    request: Request,
    *,
    user_id: int | None = None,
) -> str:
    if user_id is not None:
        return f"user:{user_id}"

    forwarded_for = request.headers.get("x-forwarded-for", "")
    forwarded_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    client_ip = forwarded_ip
    if not client_ip:
        client_ip = request.client.host if request.client and request.client.host else "unknown"

    user_agent = request.headers.get("user-agent", "").strip()
    user_agent_hash = (
        hashlib.sha256(user_agent.encode("utf-8")).hexdigest()[:16]
        if user_agent
        else "no-ua"
    )
    return f"anon:{client_ip}:{user_agent_hash}"


def build_precheck_cache_key(
    *,
    scope: str,
    account_name: str,
    actor_key: str,
) -> str:
    return cache.build_key(
        scope,
        {
            "account_name": normalize_account_name(account_name),
            "actor": actor_key,
        },
    )

