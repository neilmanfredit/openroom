import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from .calendar import CalendarCache, calendar_cache
from .cdp import ChromeController, get_chrome_controller
from .config import settings
from .routes import TEAMS_ORIGINS, meeting_state
from .state import MeetingState

logger = logging.getLogger("openroom.control.resilience")

_TEAMS_DOMAINS = tuple(origin.split("//", 1)[1] for origin in TEAMS_ORIGINS)


class ResilienceWatcher:
    """Auto-returns to the home screen when a meeting ends, per spec:
    either the tab navigates away from Teams entirely, or the meeting's
    scheduled end time plus a grace period has passed.

    Detecting "nobody in the call" specifically (the spec's other stated
    condition) would need Teams-specific DOM/participant signals this
    project has no live tenant to verify against — see
    docs/OPERATIONS.md. The time-based path here is unconditional
    (best-effort): it returns home once a meeting has overrun by the
    grace period regardless of whether the room is still in use.
    """

    def __init__(
        self,
        chrome_factory: Callable[[], ChromeController],
        state: MeetingState,
        cache: CalendarCache,
    ):
        self._chrome_factory = chrome_factory
        self._state = state
        self._cache = cache
        self._task: Optional[asyncio.Task] = None

    def _meeting_overran(self) -> bool:
        if not self._state.current_meeting_id:
            return False
        meeting = self._cache.find(self._state.current_meeting_id)
        if meeting is None or not meeting.end:
            return False
        try:
            end_dt = datetime.fromisoformat(meeting.end)
        except ValueError:
            return False
        # Graph's calendarView with Prefer: outlook.timezone returns
        # naive local times in the requested zone, not UTC — compare
        # against "now" in that same zone rather than assuming UTC.
        now = (
            datetime.now(end_dt.tzinfo)
            if end_dt.tzinfo
            else datetime.now(ZoneInfo(settings.calendar_timezone)).replace(tzinfo=None)
        )
        return now > end_dt + timedelta(minutes=settings.meeting_ended_grace_minutes)

    async def check_once(self) -> None:
        if self._state.status != "in_meeting":
            return

        chrome = self._chrome_factory()
        try:
            current_url = await chrome.current_url()
            left_teams = not any(domain in current_url for domain in _TEAMS_DOMAINS)
        except Exception:
            logger.exception("could not read the current tab URL")
            left_teams = False

        if not (left_teams or self._meeting_overran()):
            return

        logger.info("auto-returning to home screen (meeting ended)")
        try:
            await chrome.clear_session_storage(TEAMS_ORIGINS)
            await chrome.navigate(settings.home_url)
        except Exception:
            logger.exception("failed to navigate home during auto-return")
        self._state.leave()

    async def _loop(self) -> None:
        while True:
            try:
                await self.check_once()
            except Exception:
                logger.exception("resilience check failed")
            await asyncio.sleep(settings.resilience_poll_interval_seconds)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


resilience_watcher = ResilienceWatcher(get_chrome_controller, meeting_state, calendar_cache)
