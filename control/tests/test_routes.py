from fastapi.testclient import TestClient

from app import routes
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


def teardown_function(_):
    app.dependency_overrides.clear()
    routes.meeting_state.leave()


def test_health():
    client, _ = make_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_today_returns_demo_meeting():
    client, _ = make_client()
    resp = client.get("/api/today")
    assert resp.status_code == 200
    assert resp.json()["meetings"][0]["id"] == "demo"


def test_join_navigates_and_sets_state():
    client, fake = make_client()
    resp = client.post("/api/join/demo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_meeting"
    assert fake.navigated_to == [routes.settings.demo_join_url]


def test_join_unknown_meeting_404():
    client, _ = make_client()
    resp = client.post("/api/join/does-not-exist")
    assert resp.status_code == 404


def test_home_clears_storage_and_navigates():
    client, fake = make_client()
    client.post("/api/join/demo")
    resp = client.post("/api/home")
    assert resp.status_code == 200
    assert resp.json()["status"] == "home"
    assert "https://teams.microsoft.com" in fake.cleared_origins
    assert "https://teams.live.com" in fake.cleared_origins
    assert fake.navigated_to[-1] == routes.settings.home_url
