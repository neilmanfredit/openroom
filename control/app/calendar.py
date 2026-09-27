import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .config import settings
from .graph_client import GraphCalendarClient, build_graph_client
from .join_link import extract_join_url

logger = logging.getLogger("openroom.control.calendar")


@dataclass
class Meeting:
    id: str
    display_subject: str
    start: str
    end: str
    join_url: Optional[str]

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.display_subject,
            "start": self.start,
            "end": self.end,
            "join_url_available": self.join_url is not None,
        }


def _display_subject(event: dict, show_subject: bool) -> str:
    sensitivity = (event.get("sensitivity") or "normal").lower()
    if sensitivity == "private":
        return "Private"
    if show_subject:
        return event.get("subject") or "(no subject)"
    organizer_name = ((event.get("organizer") or {}).get("emailAddress") or {}).get("name")
    return organizer_name or "Busy"


def transform_event(event: dict, show_subject: bool) -> Meeting:
    return Meeting(
        id=event["id"],
        display_subject=_display_subject(event, show_subject),
        start=(event.get("start") or {}).get("dateTime", ""),
        end=(event.get("end") or {}).get("dateTime", ""),
        join_url=extract_join_url(event),
    )


def today_range(tz_name: str) -> tuple[str, str]:
    tz = ZoneInfo(tz_name)
    start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(days=1)).isoformat()


class CalendarCache:
    """Holds the last-known-good meeting list and keeps showing it if
    Graph is unreachable, per spec — persisted to disk so a service
    restart during an outage doesn't blank the home screen either."""

    def __init__(self, cache_path: Path):
        self._cache_path = cache_path
        self.meetings: list[Meeting] = []
        self.offline: bool = False
        self.last_success: Optional[float] = None
        self._load()

    def _load(self) -> None:
        if not self._cache_path.exists():
            return
        try:
            data = json.loads(self._cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("could not read calendar cache at %s", self._cache_path)
            return
        self.meetings = [
            Meeting(
                id=m["id"],
                display_subject=m["subject"],
                start=m["start"],
                end=m["end"],
                join_url=m.get("join_url"),
            )
            for m in data.get("meetings", [])
        ]
        self.last_success = data.get("last_success")

    def _save(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "last_success": self.last_success,
                "meetings": [
                    {
                        "id": m.id,
                        "subject": m.display_subject,
                        "start": m.start,
                        "end": m.end,
                        "join_url": m.join_url,
                    }
                    for m in self.meetings
                ],
            }
            self._cache_path.write_text(json.dumps(payload))
        except OSError:
            logger.warning("could not write calendar cache at %s", self._cache_path)

    def update_success(self, meetings: list[Meeting]) -> None:
        self.meetings = meetings
        self.offline = False
        self.last_success = time.time()
        self._save()

    def mark_offline(self) -> None:
        self.offline = True

    def find(self, meeting_id: str) -> Optional[Meeting]:
        return next((m for m in self.meetings if m.id == meeting_id), None)


class CalendarPoller:
    """Builds the Graph client lazily, inside the poll loop, rather than
    at startup: constructing msal's ConfidentialClientApplication makes a
    network call (OIDC tenant discovery), so doing that eagerly at import
    time could crash the whole app if the network isn't up yet at boot.
    A construction failure is treated the same as a fetch failure —
    logged, marked offline, retried next interval."""

    def __init__(self, client_factory, cache: CalendarCache):
        self._client_factory = client_factory
        self._client: Optional[GraphCalendarClient] = None
        self._logged_disabled = False
        self._cache = cache
        self._task: Optional[asyncio.Task] = None

    async def poll_once(self) -> None:
        if self._client is None:
            try:
                self._client = await asyncio.to_thread(self._client_factory)
            except Exception:
                logger.exception("failed to set up the Graph client; will retry next interval")
                self._cache.mark_offline()
                return
            if self._client is None:
                if not self._logged_disabled:
                    logger.info(
                        "Graph app registration not configured; calendar polling disabled"
                    )
                    self._logged_disabled = True
                return

        try:
            start_iso, end_iso = today_range(settings.calendar_timezone)
            raw_events = await asyncio.to_thread(
                self._client.fetch_today_events, start_iso, end_iso
            )
            meetings = [
                transform_event(event, settings.show_meeting_subject) for event in raw_events
            ]
            self._cache.update_success(meetings)
        except Exception:
            # A background resilience loop must never die from a
            # transient Graph outage — log it, keep the last-known data,
            # and try again next interval. Drop the client too, in case
            # the problem is the credential itself (e.g. cert rotated).
            logger.exception("calendar poll failed; keeping last known data")
            self._cache.mark_offline()
            self._client = None

    async def _loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(settings.calendar_poll_interval_seconds)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


calendar_cache = CalendarCache(Path(settings.calendar_cache_path))
calendar_poller = CalendarPoller(lambda: build_graph_client(settings), calendar_cache)
