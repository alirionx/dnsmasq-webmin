"""CRUD router for config files and their entries.

DNS and DHCP files share the same API shape, so the router is built by a
factory that only differs in the entry models.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import PlainTextResponse

from app.dependencies import get_service
from app.models import ConfigFileCreate, ConfigFileUpdate, ConfigKind
from app.service import ConfigService

Service = Annotated[ConfigService, Depends(get_service)]


def build_router(
    kind: ConfigKind,
    *,
    entry_create_model: Any,
    entry_model: Any,
    file_model: Any,
    entry_label: str,
) -> APIRouter:
    router = APIRouter(prefix=f"/{kind.value}-files", tags=[f"{kind.value.upper()} config files"])

    # -- config files ------------------------------------------------------- #

    @router.get("", response_model=list[file_model], summary=f"List {kind.value} config files")
    def list_files(svc: Service):
        return svc.list_files(kind)

    @router.post(
        "", response_model=file_model, status_code=status.HTTP_201_CREATED,
        summary=f"Create {kind.value} config file",
    )
    def create_file(data: ConfigFileCreate, svc: Service):
        return svc.create_file(kind, data)

    @router.get("/{name}", response_model=file_model, summary=f"Get {kind.value} config file")
    def get_file(name: str, svc: Service):
        return svc.get_file(kind, name)

    @router.patch("/{name}", response_model=file_model, summary=f"Update/rename {kind.value} config file")
    def update_file(name: str, data: ConfigFileUpdate, svc: Service):
        return svc.update_file(kind, name, data)

    @router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete {kind.value} config file")
    def delete_file(name: str, svc: Service) -> Response:
        svc.delete_file(kind, name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/{name}/render", response_class=PlainTextResponse,
        summary=f"Render {kind.value} config file",
        responses={200: {"content": {"text/plain": {}}}},
    )
    def render_file(name: str, svc: Service) -> str:
        return svc.render(kind, name).content

    # -- entries ------------------------------------------------------------ #

    @router.get("/{name}/entries", response_model=list[entry_model], summary=f"List {entry_label}s")
    def list_entries(name: str, svc: Service):
        return svc.list_entries(kind, name)

    @router.post(
        "/{name}/entries", response_model=entry_model, status_code=status.HTTP_201_CREATED,
        summary=f"Add {entry_label}",
    )
    def add_entry(name: str, data: entry_create_model, svc: Service):
        return svc.add_entry(kind, name, data.model_dump(mode="json"))

    @router.get("/{name}/entries/{entry_id}", response_model=entry_model, summary=f"Get {entry_label}")
    def get_entry(name: str, entry_id: UUID, svc: Service):
        return svc.get_entry(kind, name, str(entry_id))

    @router.put("/{name}/entries/{entry_id}", response_model=entry_model, summary=f"Replace {entry_label}")
    def replace_entry(name: str, entry_id: UUID, data: entry_create_model, svc: Service):
        return svc.replace_entry(kind, name, str(entry_id), data.model_dump(mode="json"))

    @router.delete(
        "/{name}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete {entry_label}"
    )
    def delete_entry(name: str, entry_id: UUID, svc: Service) -> Response:
        svc.delete_entry(kind, name, str(entry_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
