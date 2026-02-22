from __future__ import annotations

import asyncio
import logging
from typing import Any

from curl_cffi import requests as curl_requests

CHROME_IMPERSONATE = "chrome120"

logger = logging.getLogger(__name__)


class HttpClient:
    """Async wrapper around curl_cffi with optional CF session cookies."""

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
        *,
        force_refresh: bool = False,
        **kwargs,
    ):
        session_data = None
        if self._session_manager is not None:
            try:
                session_data = await self._session_manager.get_session_data(url)
                if not session_data and hasattr(self._session_manager, "get_session"):
                    session_data = await self._session_manager.get_session(
                        force_refresh=force_refresh,
                        url=url,
                    )
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Session manager error: %s", exc)

        cookies = {}
        user_agent = None
        if isinstance(session_data, dict):
            cookies = session_data.get("cookies") or {}
            user_agent = session_data.get("user_agent")

        if not cookies:
            logger.warning(
                "No session data available for %s; attempting request without cached cookies",
                url,
            )

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

            if self._session_manager is not None and hasattr(
                self._session_manager, "set_session_data"
            ):
                try:
                    response_cookies = {
                        str(k): str(v) for k, v in getattr(response, "cookies", {}).items()
                    }
                    if response_cookies:
                        await self._session_manager.set_session_data(
                            url,
                            {
                                "cookies": response_cookies,
                                "user_agent": user_agent or "",
                            },
                        )
                except Exception as exc:
                    logger.debug("Failed to persist response cookies: %s", exc)

            is_login_page = False
            if response.status_code == 200:
                text = response.text or ""
                is_login_page = (
                    "<title>Login</title>" in text
                    or ("Please <a href=" in text and "action=login" in text)
                )

            should_retry = response.status_code in {403, 503} or is_login_page
            if (
                should_retry
                and not force_refresh
                and self._session_manager is not None
                and hasattr(self._session_manager, "get_session")
            ):
                reason = "login page detected" if is_login_page else f"status {response.status_code}"
                logger.warning("Refreshing session and retrying %s due to %s", url, reason)
                try:
                    await self._session_manager.get_session(force_refresh=True, url=url)
                except Exception as exc:
                    logger.debug("Session refresh failed: %s", exc)
                return await self.request(
                    method=method_upper,
                    url=url,
                    data=data,
                    force_refresh=True,
                    **kwargs,
                )

            return response
        except Exception as exc:  # pragma: no cover - network/provider variability
            logger.error("HTTP request failed: %s", exc)
            return None
