from app.join_link import extract_join_url


def test_prefers_online_meeting_join_url():
    event = {
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/real"},
        "body": {"content": "https://teams.microsoft.com/l/meetup-join/fallback"},
    }
    assert extract_join_url(event) == "https://teams.microsoft.com/l/meetup-join/real"


def test_falls_back_to_teams_microsoft_link_in_body():
    event = {
        "body": {
            "content": '<p>Join here: <a href="https://teams.microsoft.com/l/meetup-join/abc123">link</a></p>'
        }
    }
    assert extract_join_url(event) == "https://teams.microsoft.com/l/meetup-join/abc123"


def test_falls_back_to_teams_live_link_in_body():
    event = {"body": {"content": "Join: https://teams.live.com/meet/123456789"}}
    assert extract_join_url(event) == "https://teams.live.com/meet/123456789"


def test_unescapes_html_entities_in_body_link():
    event = {
        "body": {
            "content": "https://teams.microsoft.com/l/meetup-join/abc?p=1&amp;q=2"
        }
    }
    assert extract_join_url(event) == "https://teams.microsoft.com/l/meetup-join/abc?p=1&q=2"


def test_ignores_non_teams_links():
    event = {"body": {"content": "Zoom link: https://zoom.us/j/123456789"}}
    assert extract_join_url(event) is None


def test_no_body_or_online_meeting_returns_none():
    assert extract_join_url({}) is None
