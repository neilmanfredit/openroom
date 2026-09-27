import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .cdp import ChromeController, get_chrome_controller
from .config import settings
from .state import MeetingState

logger = logging.getLogger("openroom.control")

router = APIRouter()

# One control service manages exactly one kiosk/browser instance, so a
# single module-level state object is simpler than threading shared state
# through FastAPI's dependency system.
meeting_state = MeetingState()

TEAMS_ORIGINS = ("https://teams.microsoft.com", "https://teams.live.com")


class JoinByIdRequest(BaseModel):
    meeting_id: str
    passcode: Optional[str] = None


@router.get("/api/today")
async def get_today():
    return {
        "room_name": settings.room_name,
        # Milestone 4 replaces this with real Graph calendar data.
        "meetings": [
            {"id": "demo", "subject": "Demo meeting", "join_url_available": True}
        ],
    }


@router.post("/api/join/{meeting_id}")
async def join_meeting(
    meeting_id: str,
    chrome: Annotated[ChromeController, Depends(get_chrome_controller)],
):
    if meeting_id != "demo":
        raise HTTPException(status_code=404, detail="unknown meeting")
    logger.info("joining meeting id=%s", meeting_id)
    await chrome.navigate(settings.demo_join_url)
    meeting_state.join(settings.demo_join_url)
    return {"status": meeting_state.status}


@router.post("/api/join-by-id")
async def join_by_id(
    body: JoinByIdRequest,
    chrome: Annotated[ChromeController, Depends(get_chrome_controller)],
):
    # Teams has no documented deep-link format for an ID+passcode join
    # (unlike onlineMeeting.joinUrl from Graph, Milestone 4) — navigate to
    # Teams' own join page and let the operator type it in. Best-effort,
    # unverified against a live Teams session. Never log the passcode.
    logger.info("join-by-id requested")
    await chrome.navigate(settings.join_by_id_url)
    meeting_state.join(settings.join_by_id_url)
    return {"status": meeting_state.status}


@router.post("/api/home")
async def go_home(
    chrome: Annotated[ChromeController, Depends(get_chrome_controller)],
):
    logger.info("returning to home screen")
    await chrome.clear_session_storage(TEAMS_ORIGINS)
    await chrome.navigate(settings.home_url)
    meeting_state.leave()
    return {"status": meeting_state.status}


@router.get("/health")
async def health():
    return {"status": "ok", "state": meeting_state.status}
