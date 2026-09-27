import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeetingState:
    """Home vs. in-meeting. current_meeting_id lets the resilience
    watcher look the joined meeting back up in the calendar cache to
    check its scheduled end time."""

    status: str = "home"
    current_join_url: Optional[str] = None
    current_meeting_id: Optional[str] = None
    since: float = field(default_factory=time.monotonic)

    def join(self, join_url: str, meeting_id: Optional[str] = None) -> None:
        self.status = "in_meeting"
        self.current_join_url = join_url
        self.current_meeting_id = meeting_id
        self.since = time.monotonic()

    def leave(self) -> None:
        self.status = "home"
        self.current_join_url = None
        self.current_meeting_id = None
        self.since = time.monotonic()
