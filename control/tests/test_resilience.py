import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.calendar import CalendarCache, Meeting
from app.config import settings
from app.resilience import ResilienceWatcher
from app.state import MeetingState


class FakeChromeController:
    def __init__(self, url="https://teams.microsoft.com/v2/meeting"):
        self.url = url
        self.navigated_to = []
        self.cleared_origins = []

    async def current_url(self):
        return self.url

    async def navigate(self, url):
        self.navigated_to.append(url)

    async def clear_session_storage(self, origins):
        self.cleared_origins.extend(origins)


def run(coro):
    return asyncio.run(coro)


def make_watcher(chrome, state, cache):
    return ResilienceWatcher(lambda: chrome, state, cache)


def test_does_nothing_when_not_in_a_meeting(tmp_path):
    chrome = FakeChromeController()
    state = MeetingState()  # status == "home"
    cache = CalendarCache(tmp_path / "c.json")
    watcher = make_watcher(chrome, state, cache)

    run(watcher.check_once())

    assert chrome.navigated_to == []
    assert state.status == "home"


def test_stays_in_meeting_while_still_on_teams_and_not_overrun(tmp_path):
    chrome = FakeChromeController(url="https://teams.microsoft.com/v2/some-call")
    cache = CalendarCache(tmp_path / "c.json")
    future_end = (
        datetime.now(ZoneInfo(settings.calendar_timezone)) + timedelta(hours=1)
    ).replace(tzinfo=None).isoformat()
    cache.update_success(
        [Meeting(id="evt-1", display_subject="x", start="s", end=future_end, join_url="u")]
    )
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/x", "evt-1")
    watcher = make_watcher(chrome, state, cache)

    run(watcher.check_once())

    assert state.status == "in_meeting"
    assert chrome.navigated_to == []


def test_auto_returns_home_when_tab_leaves_teams(tmp_path):
    chrome = FakeChromeController(url="http://127.0.0.1:8080/")
    cache = CalendarCache(tmp_path / "c.json")
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/x", "evt-1")
    watcher = make_watcher(chrome, state, cache)

    run(watcher.check_once())

    assert state.status == "home"
    assert chrome.navigated_to == [settings.home_url]
    assert set(chrome.cleared_origins) == {
        "https://teams.microsoft.com",
        "https://teams.live.com",
    }


def test_auto_returns_home_when_meeting_overran_past_grace(tmp_path):
    chrome = FakeChromeController(url="https://teams.microsoft.com/v2/some-call")
    cache = CalendarCache(tmp_path / "c.json")
    overran_end = (
        datetime.now(ZoneInfo(settings.calendar_timezone))
        - timedelta(minutes=settings.meeting_ended_grace_minutes + 1)
    ).replace(tzinfo=None).isoformat()
    cache.update_success(
        [Meeting(id="evt-1", display_subject="x", start="s", end=overran_end, join_url="u")]
    )
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/x", "evt-1")
    watcher = make_watcher(chrome, state, cache)

    run(watcher.check_once())

    assert state.status == "home"


def test_missing_meeting_in_cache_does_not_crash(tmp_path):
    chrome = FakeChromeController(url="https://teams.microsoft.com/v2/some-call")
    cache = CalendarCache(tmp_path / "c.json")  # empty — meeting not found
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/x", "evt-missing")
    watcher = make_watcher(chrome, state, cache)

    run(watcher.check_once())

    assert state.status == "in_meeting"
