import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .calendar import calendar_poller
from .extension import router as extension_router
from .routes import router as api_router

# journald captures a systemd service's stdout/stderr directly, so plain
# logging to stdout is already "structured logging to journald" here.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    calendar_poller.start()
    try:
        yield
    finally:
        await calendar_poller.stop()


app = FastAPI(title="OpenRoom control service", lifespan=lifespan)

# Loopback-only service (bound to 127.0.0.1, restricted further by the
# kiosk's browser policy URLAllowlist) — no non-kiosk browser can reach
# this, so permissive CORS just sidesteps extension-fetch edge cases
# without weakening anything that actually matters here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(extension_router)


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
