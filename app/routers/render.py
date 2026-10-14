from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.dependencies import get_service
from app.models import ConfigKind, RenderedFile, SyncResult
from app.service import ConfigService

Service = Annotated[ConfigService, Depends(get_service)]

router = APIRouter(tags=["Rendering"])


@router.get("/render", response_model=list[RenderedFile], summary="Render all config files")
def render_all(svc: Service, kind: ConfigKind | None = None):
    return svc.render_all(kind)


@router.get(
    "/render/text", response_class=PlainTextResponse, summary="Render all config files as one text",
    responses={200: {"content": {"text/plain": {}}}},
)
def render_all_text(svc: Service, kind: ConfigKind | None = None) -> str:
    return "\n".join(f"### {r.filename}\n{r.content}" for r in svc.render_all(kind))


@router.post("/sync", response_model=SyncResult, summary="Write all files to the dnsmasq conf dir")
def sync(svc: Service):
    """Rewrites every managed file and removes managed files that no longer exist in the store."""
    return svc.sync()
