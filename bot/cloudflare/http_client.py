from __future__ import annotations

import asyncio
import logging
from typing import Any

from curl_cffi import requests as curl_requests

CHROME_IMPERSONATE = "chrome120"

logger = logging.getLogger(__name__)


class HttpClient:
    """Async wrapper around curl_cffi requests with optional CF session cookies."""

    def __init__(self, session_manager):
        self._session_manager = session_manager
        self._proxy: str | None = None

    def set_proxy(self, proxy: str | None) -> None:
        self._proxy = proxy or None

    async def get(self, url: str, **kwargs):
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, data: dict[str, Any] | None = None, **kwargs):
        return await self.request("POST", url, data=data, **kwargs)

    async def request(
        self,
        method: str,
        url: str,
        data: dict[str, Any] | None = None,
        **kwargs,
    ):
        session_data = None
        if self._session_manager is not None:
            try:
                session_data = await self._session_manager.get_session_data(url)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Session manager error: %s", exc)

        if not session_data:
            logger.error("No session data available")
            return None

        cookies = session_data.get("cookies", {})
        user_agent = session_data.get("user_agent")
        proxies = {"https": self._proxy, "http": self._proxy} if self._proxy else None

        method_upper = method.upper()
        if method_upper not in {"GET", "POST"}:
            logger.error("Unsupported method: %s", method)
            return None

        def _perform_request_sync():
            session = curl_requests.Session()
            try:
                common: dict[str, Any] = {
                    "cookies": cookies,
                    "impersonate": CHROME_IMPERSONATE,
                    "timeout": 30,
                }
                if user_agent:
                    common["headers"] = {"User-Agent": user_agent}
                if proxies:
                    common["proxies"] = proxies
                common.update(kwargs)

                if method_upper == "GET":
                    return session.get(url, **common)
                return session.post(url, data=data, allow_redirects=False, **common)
            finally:
                try:
                    session.close()
                except Exception:
                    pass

        try:
            response = await asyncio.to_thread(_perform_request_sync)
            logger.info("%s %s -> %s", method_upper, url, response.status_code)
            return response
        except Exception as exc:  # pragma: no cover - network/provider variability
            logger.error("HTTP request failed: %s", exc)
            return None
