from fastapi import APIRouter

from backend.api.routes import (
    admin,
    applications,
    activities,
    auth,
    blacklist,
    bot_control,
    config_registry,
    discord,
    notifications,
    orders,
    playerbase,
    permissions,
    posts,
    public,
    roster,
    system,
    user_accounts,
    verification_requests,
    vacations,
    voting,
)

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(blacklist.router, prefix="/blacklist", tags=["blacklist"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(
    verification_requests.router,
    prefix="/verification-requests",
    tags=["verification-requests"],
)
api_router.include_router(user_accounts.router, prefix="/users", tags=["user-accounts"])
api_router.include_router(roster.router, prefix="/roster", tags=["roster"])
api_router.include_router(playerbase.router, prefix="/playerbase", tags=["playerbase"])
api_router.include_router(vacations.router, prefix="/vacations", tags=["vacations"])
api_router.include_router(voting.router, prefix="/voting", tags=["voting"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(discord.router, prefix="/discord", tags=["discord"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(bot_control.router, prefix="/bot", tags=["bot-control"])
api_router.include_router(config_registry.router, prefix="/config", tags=["config"])

