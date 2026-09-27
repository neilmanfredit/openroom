import html
import re
from typing import Optional

_TEAMS_LINK_RE = re.compile(
    r"https://(?:teams\.microsoft\.com/l/meetup-join/[^\s\"'<>]+"
    r"|teams\.live\.com/meet/[^\s\"'<>]+)"
)


def extract_join_url(event: dict) -> Optional[str]:
    """Prefer onlineMeeting.joinUrl; fall back to a Teams link found in
    the event body. Ignores any non-Teams link, per spec."""
    online_meeting = event.get("onlineMeeting") or {}
    join_url = online_meeting.get("joinUrl")
    if join_url:
        return join_url

    body = (event.get("body") or {}).get("content", "")
    match = _TEAMS_LINK_RE.search(html.unescape(body))
    return match.group(0) if match else None
