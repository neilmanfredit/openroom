from fastapi.testclient import TestClient

from app import routes
from app.calendar import Meeting, calendar_cache
from app.cdp import get_chrome_controller
from app.main import app


class FakeChromeController:
    def __init__(self):
        self.navigated_to = []
        self.cleared_origins = []

    async def navigate(self, url):
        self.navigated_to.append(url)

    async def clear_session_storage(self, origins):
        self.cleared_origins.extend(origins)

    async def current_url(self):
        return self.navigated_to[-1] if self.navigated_to else "http://127.0.0.1:8080/"


def make_client():
    fake = FakeChromeController()
    app.dependency_overrides[get_chrome_controller] = lambda: fake
    return TestClient(app), fake


def seed_meeting(join_url="https://teams.microsoft.com/l/meetup-join/test"):
    meeting = Meeting(
        id="evt-1",
        display_subject="Test meeting",
        start="2026-09-30T10:00:00",
        end="2026-09-30T10:30:00",
        join_url=join_url,
    )
    calendar_cache.meetings = [meeting]
    return meeting


def teardown_function(_):
    app.dependency_overrides.clear()
    routes.meeting_state.leave()
    calendar_cache.meetings = []
    calendar_cache.offline = False


def test_health():
    client, _ = make_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "calendar_offline" in body


def test_today_returns_seeded_meeting():
    client, _ = make_client()
    seed_meeting()
    resp = client.get("/api/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meetings"][0]["id"] == "evt-1"
    assert body["meetings"][0]["join_url_available"] is True


def test_today_reports_offline_flag():
    client, _ = make_client()
    calendar_cache.offline = True
    resp = client.get("/api/today")
    assert resp.json()["offline"] is True


def test_join_navigates_and_sets_state():
    client, fake = make_client()
    meeting = seed_meeting()
    resp = client.post("/api/join/evt-1")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_meeting"
    assert fake.navigated_to == [meeting.join_url]


def test_join_unknown_meeting_404():
    client, _ = make_client()
    resp = client.post("/api/join/does-not-exist")
    assert resp.status_code == 404


def test_join_meeting_without_join_url_400():
    client, _ = make_client()
    seed_meeting(join_url=None)
    resp = client.post("/api/join/evt-1")
    assert resp.status_code == 400


def test_home_clears_storage_and_navigates():
    client, fake = make_client()
    seed_meeting()
    client.post("/api/join/evt-1")
    resp = client.post("/api/home")
    assert resp.status_code == 200
    assert resp.json()["status"] == "home"
    assert "https://teams.microsoft.com" in fake.cleared_origins
    assert "https://teams.live.com" in fake.cleared_origins
    assert fake.navigated_to[-1] == routes.settings.home_url
