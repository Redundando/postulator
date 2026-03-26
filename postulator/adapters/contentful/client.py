"""Contentful CMA HTTP client — self-contained, no project dependencies."""

import asyncio
import logging
import time
import httpx
from typing import Any, Callable

from ._reader import _ReaderMixin
from ._writer import _WriterMixin

logger = logging.getLogger(__name__)

_RETRYABLE = {429, 500, 502, 503, 504}


def _raise_for_status(resp: httpx.Response) -> None:
    if not resp.is_success:
        raise httpx.HTTPStatusError(
            f"{resp.status_code} {resp.text}",
            request=resp.request,
            response=resp,
        )


class ContentfulClient(_ReaderMixin, _WriterMixin):
    def __init__(
        self,
        space_id: str,
        environment: str,
        token: str,
        batch_size: int = 200,
        asset_poll_attempts: int = 10,
        asset_poll_interval: float = 1.0,
        on_progress: Callable | None = None,
    ):
        self._space_id = space_id
        self._base_url = f"https://api.contentful.com/spaces/{space_id}/environments/{environment}"
        self._token = token
        self._batch_size = batch_size
        self._asset_poll_attempts = asset_poll_attempts
        self._asset_poll_interval = asset_poll_interval
        self._on_progress = on_progress
        self._http: httpx.AsyncClient | None = None

    def _emit(self, event: str, **kwargs) -> None:
        if self._on_progress:
            self._on_progress({"event": event, "ts": time.time(), **kwargs})

    async def __aenter__(self) -> "ContentfulClient":
        self._http = httpx.AsyncClient(headers={"Authorization": f"Bearer {self._token}"})
        return self

    async def __aexit__(self, *_) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _request(self, method: str, url: str, extra_headers: dict | None = None, **kwargs) -> httpx.Response:
        if self._http is None:
            raise RuntimeError("ContentfulClient must be used as an async context manager: async with client:")
        headers = extra_headers or {}
        for attempt in range(4):
            resp = await getattr(self._http, method)(url, headers=headers, **kwargs)
            if resp.status_code not in _RETRYABLE:
                if not resp.is_success:
                    logger.error("%s %s → %s %s", method.upper(), url, resp.status_code, resp.text)
                    self._emit("request_failed", method=method.upper(), url=url, status_code=resp.status_code)
                return resp
            if attempt < 3:
                logger.warning("%s %s → %s, retrying (attempt %d)", method.upper(), url, resp.status_code, attempt + 1)
                await asyncio.sleep(2 ** attempt)
        logger.error("%s %s → %s after retries", method.upper(), url, resp.status_code)
        self._emit("request_failed", method=method.upper(), url=url, status_code=resp.status_code)
        return resp

    async def get_entry(self, entry_id: str) -> dict[str, Any]:
        resp = await self._request("get", f"{self._base_url}/entries/{entry_id}")
        _raise_for_status(resp)
        return resp.json()

    async def get_entries(self, entry_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not entry_ids:
            return {}
        results = {}
        for i in range(0, len(entry_ids), self._batch_size):
            batch = entry_ids[i:i + self._batch_size]
            resp = await self._request(
                "get",
                f"{self._base_url}/entries",
                params={"sys.id[in]": ",".join(batch), "limit": self._batch_size},
            )
            _raise_for_status(resp)
            for item in resp.json().get("items", []):
                results[item["sys"]["id"]] = item
        return results

    async def update_entry(self, entry_id: str, version: int, fields: dict) -> dict[str, Any]:
        resp = await self._request(
            "put",
            f"{self._base_url}/entries/{entry_id}",
            extra_headers={"X-Contentful-Version": str(version), "Content-Type": "application/vnd.contentful.management.v1+json"},
            json={"fields": fields},
        )
        _raise_for_status(resp)
        return resp.json()

    async def publish_entry(self, entry_id: str, version: int) -> dict[str, Any]:
        resp = await self._request(
            "put",
            f"{self._base_url}/entries/{entry_id}/published",
            extra_headers={"X-Contentful-Version": str(version)},
        )
        _raise_for_status(resp)
        return resp.json()

    async def upload_file(self, data: bytes, content_type: str) -> str:
        resp = await self._request(
            "post",
            f"https://upload.contentful.com/spaces/{self._space_id}/uploads",
            extra_headers={"Content-Type": "application/octet-stream"},
            content=data,
        )
        _raise_for_status(resp)
        return resp.json()["sys"]["id"]

    async def create_asset(self, fields: dict) -> dict:
        resp = await self._request(
            "post",
            f"{self._base_url}/assets",
            extra_headers={"Content-Type": "application/vnd.contentful.management.v1+json"},
            json={"fields": fields},
        )
        _raise_for_status(resp)
        return resp.json()

    async def process_asset(self, asset_id: str, locale: str) -> None:
        resp = await self._request("put", f"{self._base_url}/assets/{asset_id}/files/{locale}/process")
        _raise_for_status(resp)

    async def get_asset(self, asset_id: str) -> dict:
        resp = await self._request("get", f"{self._base_url}/assets/{asset_id}")
        _raise_for_status(resp)
        return resp.json()

    async def publish_asset(self, asset_id: str, version: int) -> dict:
        resp = await self._request(
            "put",
            f"{self._base_url}/assets/{asset_id}/published",
            extra_headers={"X-Contentful-Version": str(version)},
        )
        _raise_for_status(resp)
        return resp.json()

    async def get_assets(self, asset_ids: list[str]) -> dict[str, dict]:
        if not asset_ids:
            return {}
        results = {}
        for i in range(0, len(asset_ids), self._batch_size):
            batch = asset_ids[i:i + self._batch_size]
            resp = await self._request(
                "get",
                f"{self._base_url}/assets",
                params={"sys.id[in]": ",".join(batch), "limit": self._batch_size},
            )
            _raise_for_status(resp)
            for item in resp.json().get("items", []):
                results[item["sys"]["id"]] = item
        return results

    async def get_content_type(self, content_type_id: str) -> dict[str, Any]:
        resp = await self._request("get", f"{self._base_url}/content_types/{content_type_id}")
        _raise_for_status(resp)
        return resp.json()

    async def find_entries(self, content_type: str, filters: dict, limit: int = 1) -> list[dict]:
        params = {"content_type": content_type, "limit": min(limit, self._batch_size), **filters}
        if limit == 1:
            resp = await self._request("get", f"{self._base_url}/entries", params=params)
            _raise_for_status(resp)
            return resp.json().get("items", [])
        items: list[dict] = []
        skip = 0
        while True:
            resp = await self._request("get", f"{self._base_url}/entries", params={**params, "skip": skip})
            _raise_for_status(resp)
            data = resp.json()
            page = data.get("items", [])
            items.extend(page)
            if len(items) >= data.get("total", 0) or not page:
                break
            skip += len(page)
        return items

    async def create_entry(self, content_type: str, fields: dict) -> dict[str, Any]:
        resp = await self._request(
            "post",
            f"{self._base_url}/entries",
            extra_headers={"X-Contentful-Content-Type": content_type, "Content-Type": "application/vnd.contentful.management.v1+json"},
            json={"fields": fields},
        )
        _raise_for_status(resp)
        return resp.json()

    async def create_entry_with_id(self, entry_id: str, content_type: str, fields: dict) -> dict[str, Any]:
        resp = await self._request(
            "put",
            f"{self._base_url}/entries/{entry_id}",
            extra_headers={"X-Contentful-Content-Type": content_type, "Content-Type": "application/vnd.contentful.management.v1+json"},
            json={"fields": fields},
        )
        _raise_for_status(resp)
        return resp.json()

    async def delete_entry(self, entry_id: str, version: int) -> None:
        resp = await self._request(
            "delete",
            f"{self._base_url}/entries/{entry_id}",
            extra_headers={"X-Contentful-Version": str(version)},
        )
        _raise_for_status(resp)

