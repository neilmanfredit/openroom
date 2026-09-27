import itertools
import json
from typing import Iterable, Optional

import httpx
import websockets

from .config import settings


class ChromeController:
    """Drives the kiosk's single Chromium tab over the DevTools Protocol.

    Reads (current URL) go via the plain HTTP /json/list endpoint — just as
    valid as a websocket round-trip for that, and avoids holding a
    long-lived websocket open. Writes (navigate, clear storage) open a
    short-lived websocket per command.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9222):
        self._http_base = f"http://{host}:{port}"
        self._id_counter = itertools.count(1)

    async def _targets(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._http_base}/json/list", timeout=5)
            resp.raise_for_status()
            return resp.json()

    async def _page_target(self) -> dict:
        pages = [t for t in await self._targets() if t.get("type") == "page"]
        if not pages:
            raise RuntimeError("no Chromium page target found")
        return pages[0]

    async def current_url(self) -> str:
        target = await self._page_target()
        return target["url"]

    async def _send(self, ws_url: str, method: str, params: Optional[dict] = None) -> dict:
        message_id = next(self._id_counter)
        async with websockets.connect(ws_url, max_size=None) as ws:
            await ws.send(
                json.dumps({"id": message_id, "method": method, "params": params or {}})
            )
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == message_id:
                    return message

    async def navigate(self, url: str) -> None:
        target = await self._page_target()
        await self._send(target["webSocketDebuggerUrl"], "Page.navigate", {"url": url})

    async def clear_session_storage(self, origins: Iterable[str]) -> None:
        # sessionStorage only — matches the spec's literal wording ("clear
        # session storage... without logging the room account out"). Teams'
        # sign-in (MSAL) can cache tokens in cookies or localStorage, so
        # those are deliberately left alone.
        target = await self._page_target()
        ws_url = target["webSocketDebuggerUrl"]
        for origin in origins:
            await self._send(
                ws_url,
                "Storage.clearDataForOrigin",
                {"origin": origin, "storageTypes": "session_storage"},
            )


def get_chrome_controller() -> ChromeController:
    return ChromeController(host=settings.cdp_host, port=settings.cdp_port)
