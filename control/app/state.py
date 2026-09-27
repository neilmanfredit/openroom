import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeetingState:
    """Home vs. in-meeting only for Milestone 3 — no calendar yet, and
    auto-detecting a meeting ending is Milestone 5 (Resilience)."""

    status: str = "home"
    current_join_url: Optional[str] = None
    since: float = field(default_factory=time.monotonic)

    def join(self, join_url: str) -> None:
        self.status = "in_meeting"
        self.current_join_url = join_url
        self.since = time.monotonic()

    def leave(self) -> None:
        self.status = "home"
        self.current_join_url = None
        self.since = time.monotonic()
