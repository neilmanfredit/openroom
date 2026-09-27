from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from .config import settings

router = APIRouter(prefix="/extension")

_UPDATE_MANIFEST = """<?xml version='1.0' encoding='UTF-8'?>
<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>
  <app appid='{extension_id}'>
    <updatecheck codebase='{codebase}' version='{version}' />
  </app>
</gupdate>
"""


def _read_extension_id() -> str:
    path = Path(settings.extension_id_path)
    if not path.exists():
        raise HTTPException(status_code=503, detail="extension not packed yet")
    return path.read_text().strip()


@router.get("/update.xml")
async def update_manifest() -> Response:
    extension_id = _read_extension_id()
    codebase = f"{settings.external_base_url}/extension/leavehome.crx"
    xml = _UPDATE_MANIFEST.format(
        extension_id=extension_id,
        codebase=codebase,
        version=settings.extension_version,
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/leavehome.crx")
async def crx() -> FileResponse:
    path = Path(settings.extension_crx_path)
    if not path.exists():
        raise HTTPException(status_code=503, detail="extension not packed yet")
    return FileResponse(path, media_type="application/x-chrome-extension")
