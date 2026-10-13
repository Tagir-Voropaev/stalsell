import asyncio
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OAUTH_URL = "https://exbo.net/oauth/token"
API_URL = "https://eapi.stalcraft.net"
REGION = "ru"


class StalzoneAPI:
    def __init__(self):
        self.client_id = os.getenv("STALZONE_CLIENT_ID")
        self.client_secret = os.getenv("STALZONE_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError("Не найдены STALZONE_CLIENT_ID / STALZONE_CLIENT_SECRET в .env")

        self._token: Optional[str] = None
        self._token_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,       # было 20
            ),
        )

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        async with self._token_lock:
            if self._token:
                return self._token

            r = await self._http.post(
                OAUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            r.raise_for_status()
            self._token = r.json()["access_token"]
            return self._token

    async def _get(self, path: str, params: dict | None = None) -> dict:
        token = await self._get_token()
        url = f"{API_URL}/{REGION}/{path}"
        r = await self._http.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
        )
        r.raise_for_status()
        return r.json()

    async def get_item_history(self, item_id: str, limit: int = 100, offset: int = 0):
        data = await self._get(
            f"auction/{item_id}/history",
            params={"limit": limit, "offset": offset, "additional": "true"},
        )
        return data.get("prices", [])

    async def get_item_history_page(self, item_id: str, offset: int = 0, limit: int = 500):
        """Параллельная загрузка истории (до 10 одновременных запросов)."""
        PAGE_SIZE = 200
        CONCURRENT = 20   # Максимальная параллельность

        pages = []
        remaining = limit
        current_offset = offset
        while remaining > 0:
            page_size = min(PAGE_SIZE, remaining)
            pages.append((current_offset, page_size))
            current_offset += page_size
            remaining -= page_size

        if not pages:
            return []

        sem = asyncio.Semaphore(CONCURRENT)

        async def fetch_page(page_offset: int, page_size: int):
            async with sem:
                try:
                    data = await self._get(
                        f"auction/{item_id}/history",
                        params={
                            "limit": page_size,
                            "offset": page_offset,
                            "additional": "true",
                        },
                    )
                    return page_offset, data.get("prices", [])
                except Exception:
                    return page_offset, []

        results = await asyncio.gather(*[fetch_page(off, size) for off, size in pages])
        results.sort(key=lambda x: x[0])
        combined = []
        for _, prices in results:
            if not prices:
                break
            combined.extend(prices)

        return combined[:limit]

    async def get_active_lots(self, item_id: str, limit: int = 200, offset: int = 0):
        data = await self._get(
            f"auction/{item_id}/lots",
            params={"limit": limit, "offset": offset, "additional": "true"},
        )
        return data.get("lots", [])

    async def close(self):
        await self._http.aclose()