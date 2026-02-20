from __future__ import annotations

import inspect
import logging

import capsolver

from .base import CloudflareStrategy

logger = logging.getLogger(__name__)


class CapsolverStrategy(CloudflareStrategy):
    """Fallback Cloudflare bypass using the Capsolver Python library."""

    @property
    def name(self) -> str:
        return "capsolver"

    def __init__(self, api_key: str, proxy: str = ""):
        self._api_key = api_key
        self._proxy = proxy
        capsolver.api_key = self._api_key

    async def solve(self, url: str, **kwargs) -> dict | None:
        _ = kwargs
        if not self._api_key:
            logger.error("CAPSOLVER_API_KEY not configured")
            return None

        try:
            maybe_solution = capsolver.solve(
                {
                    "type": "AntiCloudflareTask",
                    "websiteURL": url,
                    "proxy": self._proxy,
                }
            )
            solution = (
                await maybe_solution
                if inspect.isawaitable(maybe_solution)
                else maybe_solution
            )

            cookies: dict[str, str] = {}
            if isinstance(solution, dict):
                if "token" in solution:
                    cookies["cf_clearance"] = str(solution["token"])
                if isinstance(solution.get("cookies"), dict):
                    for key, value in solution["cookies"].items():
                        cookies[str(key)] = str(value)
                if "cookie" in solution:
                    raw_cookie = str(solution["cookie"])
                    for part in raw_cookie.split(";"):
                        if "=" in part:
                            key, value = part.strip().split("=", 1)
                            cookies[key] = value

            logger.info("Capsolver task completed successfully")
            return {
                "cookies": cookies,
                "user_agent": str(solution.get("userAgent", ""))
                if isinstance(solution, dict)
                else "",
            }
        except Exception as exc:  # pragma: no cover - network/provider variability
            logger.error("Capsolver library error: %s", exc)
            return None
