from __future__ import annotations

from abc import ABC, abstractmethod


class CloudflareStrategy(ABC):
    """Strategy interface for obtaining a usable Cloudflare session."""

    @property
    @abstractmethod
    def name(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    async def solve(self, url: str, **kwargs) -> dict | None:  # pragma: no cover - interface
        raise NotImplementedError

    async def login_and_solve(
        self,
        login_url: str,
        username: str,
        password: str,
        **kwargs,
    ) -> dict | None:
        """Optional hook for strategies that can perform login during solve."""
        _ = (login_url, username, password, kwargs)
        return await self.solve(login_url)
