import asyncio

from app.calendar import CalendarCache, CalendarPoller


class FakeGraphClient:
    def __init__(self, events=None, fail=False):
        self._events = events or []
        self._fail = fail

    def fetch_today_events(self, start_iso, end_iso):
        if self._fail:
            raise RuntimeError("simulated Graph outage")
        return self._events


def run(coro):
    return asyncio.run(coro)


def test_factory_returning_none_does_not_mark_offline(tmp_path):
    cache = CalendarCache(tmp_path / "cache.json")
    poller = CalendarPoller(lambda: None, cache)
    run(poller.poll_once())
    assert cache.offline is False
    assert cache.meetings == []


def test_factory_raising_marks_offline_without_crashing(tmp_path):
    # Regression test: msal's ConfidentialClientApplication construction
    # makes a network call (OIDC discovery), so a transient failure here
    # must be handled exactly like a fetch failure — not propagate and
    # take the whole poll loop (and app) down.
    cache = CalendarCache(tmp_path / "cache.json")

    def failing_factory():
        raise RuntimeError("simulated network failure during client setup")

    poller = CalendarPoller(failing_factory, cache)
    run(poller.poll_once())  # must not raise
    assert cache.offline is True


def test_successful_poll_populates_cache(tmp_path):
    cache = CalendarCache(tmp_path / "cache.json")
    event = {
        "id": "evt-1",
        "subject": "Standup",
        "start": {"dateTime": "2026-09-30T09:00:00"},
        "end": {"dateTime": "2026-09-30T09:15:00"},
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/x"},
    }
    poller = CalendarPoller(lambda: FakeGraphClient(events=[event]), cache)
    run(poller.poll_once())
    assert cache.offline is False
    assert cache.find("evt-1") is not None


def test_client_is_rebuilt_after_a_fetch_failure(tmp_path):
    cache = CalendarCache(tmp_path / "cache.json")
    calls = []

    def factory():
        calls.append(1)
        return FakeGraphClient(fail=True)

    poller = CalendarPoller(factory, cache)
    run(poller.poll_once())
    run(poller.poll_once())
    # Each poll rebuilds the client after the previous failure, in case
    # the credential itself (e.g. a rotated certificate) was the problem.
    assert len(calls) == 2
    assert cache.offline is True
