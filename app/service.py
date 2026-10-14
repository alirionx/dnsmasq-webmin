"""Glue between store, renderer and file writer."""

from typing import Any

from pydantic import TypeAdapter

from app.models import (
    ConfigFileCreate,
    ConfigFileUpdate,
    ConfigKind,
    DhcpRange,
    DnsEntry,
    RenderedFile,
    SyncResult,
)
from app.render import render_file
from app.store import ConfigStore, Document
from app.writer import ConfWriter

_ENTRY_ADAPTERS: dict[ConfigKind, TypeAdapter[Any]] = {
    ConfigKind.dns: TypeAdapter(DnsEntry),
    ConfigKind.dhcp: TypeAdapter(DhcpRange),
}


class ConfigService:
    def __init__(self, store: ConfigStore, writer: ConfWriter, write_on_change: bool = True) -> None:
        self.store = store
        self.writer = writer
        self.write_on_change = write_on_change

    # -- helpers ------------------------------------------------------------ #

    def _view(self, doc: Document) -> Document:
        kind = ConfigKind(doc["kind"])
        return {**doc, "filename": self.writer.filename(kind, doc["name"])}

    def _render_doc(self, doc: Document) -> RenderedFile:
        kind = ConfigKind(doc["kind"])
        adapter = _ENTRY_ADAPTERS[kind]
        entries = [adapter.validate_python(e) for e in doc["entries"]]
        return RenderedFile(
            name=doc["name"],
            kind=kind,
            filename=self.writer.filename(kind, doc["name"]),
            content=render_file(doc["name"], kind, doc.get("description"), entries),
        )

    def _sync_one(self, kind: ConfigKind, name: str) -> None:
        if self.write_on_change:
            rendered = self._render_doc(self.store.get_file(kind, name))
            self.writer.write(rendered.filename, rendered.content)

    # -- config files ------------------------------------------------------- #

    def list_files(self, kind: ConfigKind) -> list[Document]:
        return [self._view(d) for d in self.store.list_files(kind)]

    def get_file(self, kind: ConfigKind, name: str) -> Document:
        return self._view(self.store.get_file(kind, name))

    def create_file(self, kind: ConfigKind, data: ConfigFileCreate) -> Document:
        doc = self.store.create_file(kind, data.name, data.description)
        self._sync_one(kind, data.name)
        return self._view(doc)

    def update_file(self, kind: ConfigKind, name: str, data: ConfigFileUpdate) -> Document:
        changes = data.model_dump(exclude_unset=True)
        if changes.get("name") is None:
            changes.pop("name", None)  # an explicit null must not clear the name
        doc = self.store.update_file(kind, name, changes)
        if doc["name"] != name and self.write_on_change:
            self.writer.remove(self.writer.filename(kind, name))
        self._sync_one(kind, doc["name"])
        return self._view(doc)

    def delete_file(self, kind: ConfigKind, name: str) -> None:
        self.store.delete_file(kind, name)
        if self.write_on_change:
            self.writer.remove(self.writer.filename(kind, name))

    # -- entries ------------------------------------------------------------ #

    def list_entries(self, kind: ConfigKind, name: str) -> list[Document]:
        return self.store.get_file(kind, name)["entries"]

    def get_entry(self, kind: ConfigKind, name: str, entry_id: str) -> Document:
        return self.store.get_entry(kind, name, entry_id)

    def add_entry(self, kind: ConfigKind, name: str, data: Document) -> Document:
        entry = self.store.add_entry(kind, name, data)
        self._sync_one(kind, name)
        return entry

    def replace_entry(self, kind: ConfigKind, name: str, entry_id: str, data: Document) -> Document:
        entry = self.store.replace_entry(kind, name, entry_id, data)
        self._sync_one(kind, name)
        return entry

    def delete_entry(self, kind: ConfigKind, name: str, entry_id: str) -> None:
        self.store.delete_entry(kind, name, entry_id)
        self._sync_one(kind, name)

    # -- rendering / sync ----------------------------------------------------- #

    def render(self, kind: ConfigKind, name: str) -> RenderedFile:
        return self._render_doc(self.store.get_file(kind, name))

    def render_all(self, kind: ConfigKind | None = None) -> list[RenderedFile]:
        return [self._render_doc(d) for d in self.store.list_files(kind)]

    def sync(self) -> SyncResult:
        """Write all files from the store and remove managed files no longer in the store."""
        rendered = self.render_all()
        for r in rendered:
            self.writer.write(r.filename, r.content)
        expected = {r.filename for r in rendered}
        removed = [f for f in self.writer.managed_files() if f not in expected and self.writer.remove(f)]
        return SyncResult(written=sorted(expected), removed=removed)
