from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from backend.core.config import get_settings
from backend.core.errors import ApiException


@dataclass(frozen=True)
class StorageUploadResult:
    key: str
    url: str
    size_bytes: int
    content_type: str


class StorageUploader:
    def __init__(self):
        self.settings = get_settings()

    async def upload_bytes(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StorageUploadResult:
        size = len(data)
        if self._is_bunny_configured():
            return await self._upload_to_bunny(
                key=key,
                data=data,
                content_type=content_type,
                size=size,
            )
        return self._upload_local_fallback(
            key=key,
            data=data,
            content_type=content_type,
            size=size,
        )

    def _is_bunny_configured(self) -> bool:
        return (
            bool(self.settings.BUNNY_STORAGE_ENDPOINT)
            and bool(self.settings.BUNNY_STORAGE_ZONE)
            and bool(self.settings.BUNNY_STORAGE_ACCESS_KEY)
        )

    async def _upload_to_bunny(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        size: int,
    ) -> StorageUploadResult:
        endpoint = self._normalize_http_base_url(
            self.settings.BUNNY_STORAGE_ENDPOINT,
            field_name="BUNNY_STORAGE_ENDPOINT",
        )
        zone = self.settings.BUNNY_STORAGE_ZONE
        upload_url = f"{endpoint}/{zone}/{key.lstrip('/')}"
        headers = {
            "AccessKey": self.settings.BUNNY_STORAGE_ACCESS_KEY,
            "Content-Type": content_type,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(upload_url, content=data, headers=headers)
        if response.status_code >= 400:
            raise ApiException(
                status_code=502,
                error_code="OBJECT_STORAGE_UPLOAD_FAILED",
                message=f"Bunny upload failed with status {response.status_code}",
            )

        public_base = self._normalize_http_base_url(
            self.settings.BUNNY_STORAGE_PUBLIC_BASE_URL,
            field_name="BUNNY_STORAGE_PUBLIC_BASE_URL",
            allow_empty=True,
        )
        if public_base:
            public_url = f"{public_base}/{key.lstrip('/')}"
        else:
            public_url = upload_url
        return StorageUploadResult(
            key=key,
            url=public_url,
            size_bytes=size,
            content_type=content_type,
        )

    @staticmethod
    def _upload_local_fallback(
        *,
        key: str,
        data: bytes,
        content_type: str,
        size: int,
    ) -> StorageUploadResult:
        target = Path("media/backend_uploads") / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StorageUploadResult(
            key=key,
            url=str(target),
            size_bytes=size,
            content_type=content_type,
        )

    @staticmethod
    def _normalize_http_base_url(
        value: str,
        *,
        field_name: str,
        allow_empty: bool = False,
    ) -> str:
        raw = str(value or "").strip()
        if not raw:
            if allow_empty:
                return ""
            raise ApiException(
                status_code=500,
                error_code="OBJECT_STORAGE_CONFIG_INVALID",
                message=f"{field_name} is not configured",
            )

        parsed = urlparse(raw)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return raw.rstrip("/")

        if not parsed.scheme and parsed.path and "." in parsed.path:
            normalized = f"https://{parsed.path.lstrip('/')}"
            reparsed = urlparse(normalized)
            if reparsed.scheme in {"http", "https"} and reparsed.netloc:
                return normalized.rstrip("/")

        raise ApiException(
            status_code=500,
            error_code="OBJECT_STORAGE_CONFIG_INVALID",
            message=f"{field_name} must be a valid http(s) URL",
            details={"configured_value": raw},
        )
