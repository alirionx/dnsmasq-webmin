from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse

from app.config import Settings, get_settings
from app.models import ConfigKind, DhcpConfigFile, DhcpRange, DhcpRangeCreate, DnsConfigFile, DnsEntry, DnsEntryCreate
from app.routers import render, service
from app.routers.config_files import build_router
from app.service import ConfigService
from app.store import ConfigStore, ConflictError, NotFoundError
from app.systemd import CommandError, ConfigTestError, DnsmasqService, ServiceUnavailableError
from app.writer import ConfWriter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        store = ConfigStore(settings.db_path)
        writer = ConfWriter(settings.conf_dir, settings.file_prefix)
        app.state.service = ConfigService(store, writer, settings.write_on_change)
        app.state.dnsmasq = DnsmasqService(settings.systemd_unit or None)
        try:
            yield
        finally:
            store.close()

    app = FastAPI(
        title="dnsmasq-webmin",
        description="Manage dnsmasq sub config files (DNS entries and DHCP ranges) in the conf dir.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(PermissionError)
    async def _permission(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)})

    @app.exception_handler(ConfigTestError)
    async def _config_test(_: Request, exc: ConfigTestError) -> JSONResponse:
        detail = f"dnsmasq --test failed, dnsmasq was not restarted: {exc}"
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": detail})

    @app.exception_handler(CommandError)
    async def _command(_: Request, exc: CommandError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": str(exc)})

    @app.exception_handler(ServiceUnavailableError)
    async def _unavailable(_: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)})

    api = APIRouter(prefix="/api")
    api.include_router(
        build_router(
            ConfigKind.dns,
            entry_create_model=DnsEntryCreate,
            entry_model=DnsEntry,
            file_model=DnsConfigFile,
            entry_label="DNS entry",
        )
    )
    api.include_router(
        build_router(
            ConfigKind.dhcp,
            entry_create_model=DhcpRangeCreate,
            entry_model=DhcpRange,
            file_model=DhcpConfigFile,
            entry_label="DHCP range",
        )
    )
    api.include_router(render.router)
    api.include_router(service.router)
    app.include_router(api)

    if (settings.frontend_dir / "index.html").is_file():
        _mount_spa(app, settings.frontend_dir.resolve())
    return app


def _mount_spa(app: FastAPI, dist: Path) -> None:
    """Serve the built Vue SPA; unknown paths fall back to index.html for client-side routing."""

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):
            return FileResponse(file)
        return FileResponse(dist / "index.html")


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    # reload needs the app as import string so the reloader can re-import it
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
