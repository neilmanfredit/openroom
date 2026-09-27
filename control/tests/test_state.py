from app.state import MeetingState


def test_initial_state_is_home():
    state = MeetingState()
    assert state.status == "home"
    assert state.current_join_url is None


def test_join_sets_in_meeting():
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/demo")
    assert state.status == "in_meeting"
    assert state.current_join_url == "https://teams.microsoft.com/l/meetup-join/demo"


def test_leave_returns_home():
    state = MeetingState()
    state.join("https://teams.microsoft.com/l/meetup-join/demo")
    state.leave()
    assert state.status == "home"
    assert state.current_join_url is None
