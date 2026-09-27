from app.calendar import CalendarCache, Meeting, transform_event


def make_event(**overrides):
    event = {
        "id": "evt-1",
        "subject": "Budget review",
        "organizer": {"emailAddress": {"name": "Jane Smith"}},
        "start": {"dateTime": "2026-09-30T10:00:00"},
        "end": {"dateTime": "2026-09-30T10:30:00"},
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/x"},
        "sensitivity": "normal",
    }
    event.update(overrides)
    return event


def test_shows_subject_when_allowed():
    meeting = transform_event(make_event(), show_subject=True)
    assert meeting.display_subject == "Budget review"


def test_shows_organizer_instead_of_subject_when_disallowed():
    meeting = transform_event(make_event(), show_subject=False)
    assert meeting.display_subject == "Jane Smith"


def test_private_sensitivity_always_shows_private():
    meeting = transform_event(make_event(sensitivity="private"), show_subject=True)
    assert meeting.display_subject == "Private"


def test_join_url_extracted_onto_meeting():
    meeting = transform_event(make_event(), show_subject=True)
    assert meeting.join_url == "https://teams.microsoft.com/l/meetup-join/x"


def test_no_join_url_when_not_a_teams_meeting():
    event = make_event(onlineMeeting=None, body={"content": "in person"})
    meeting = transform_event(event, show_subject=True)
    assert meeting.join_url is None


def test_cache_persists_across_instances(tmp_path):
    cache_path = tmp_path / "calendar-cache.json"
    cache = CalendarCache(cache_path)
    cache.update_success(
        [Meeting(id="evt-1", display_subject="Test", start="s", end="e", join_url="u")]
    )
    assert cache_path.exists()

    reloaded = CalendarCache(cache_path)
    assert reloaded.last_success == cache.last_success
    assert reloaded.find("evt-1").display_subject == "Test"


def test_mark_offline_keeps_last_known_meetings(tmp_path):
    cache = CalendarCache(tmp_path / "calendar-cache.json")
    cache.update_success(
        [Meeting(id="evt-1", display_subject="Test", start="s", end="e", join_url=None)]
    )
    cache.mark_offline()
    assert cache.offline is True
    assert cache.find("evt-1") is not None


def test_cache_survives_corrupt_file(tmp_path):
    cache_path = tmp_path / "calendar-cache.json"
    cache_path.write_text("not json")
    cache = CalendarCache(cache_path)
    assert cache.meetings == []
