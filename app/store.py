"""TinyDB backed document store.

One document per config file::

    {"kind": "dns", "name": "home", "description": "...", "entries": [{"id": "...", ...}]}
"""

import threading
import uuid
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB

from app.models import ConfigKind

Document = dict[str, Any]


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ConfigStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = TinyDB(db_path, indent=2, ensure_ascii=False)
        self._table = self._db.table("config_files")
        # TinyDB is not thread-safe; FastAPI runs sync endpoints in a thread pool.
        self._lock = threading.RLock()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _q(kind: ConfigKind, name: str):
        f = Query()
        return (f.kind == kind.value) & (f.name == name)

    # -- config files ------------------------------------------------------- #

    def list_files(self, kind: ConfigKind | None = None) -> list[Document]:
        with self._lock:
            docs = self._table.all() if kind is None else self._table.search(Query().kind == kind.value)
            return sorted((dict(d) for d in docs), key=lambda d: (d["kind"], d["name"]))

    def get_file(self, kind: ConfigKind, name: str) -> Document:
        with self._lock:
            doc = self._table.get(self._q(kind, name))
            if doc is None:
                raise NotFoundError(f"{kind.value} config file '{name}' not found")
            return dict(doc)

    def create_file(self, kind: ConfigKind, name: str, description: str | None) -> Document:
        with self._lock:
            if self._table.contains(self._q(kind, name)):
                raise ConflictError(f"{kind.value} config file '{name}' already exists")
            doc = {"kind": kind.value, "name": name, "description": description, "entries": []}
            self._table.insert(doc)
            return doc

    def update_file(self, kind: ConfigKind, name: str, changes: Document) -> Document:
        with self._lock:
            doc = self.get_file(kind, name)
            new_name = changes.get("name", name)
            if new_name != name and self._table.contains(self._q(kind, new_name)):
                raise ConflictError(f"{kind.value} config file '{new_name}' already exists")
            doc.update(changes)
            self._table.update(doc, self._q(kind, name))
            return doc

    def delete_file(self, kind: ConfigKind, name: str) -> None:
        with self._lock:
            if not self._table.remove(self._q(kind, name)):
                raise NotFoundError(f"{kind.value} config file '{name}' not found")

    # -- entries ------------------------------------------------------------ #

    def _save_entries(self, kind: ConfigKind, name: str, entries: list[Document]) -> None:
        self._table.update({"entries": entries}, self._q(kind, name))

    @staticmethod
    def _index(doc: Document, entry_id: str) -> int:
        for i, entry in enumerate(doc["entries"]):
            if entry["id"] == entry_id:
                return i
        raise NotFoundError(f"entry '{entry_id}' not found in '{doc['name']}'")

    def get_entry(self, kind: ConfigKind, name: str, entry_id: str) -> Document:
        with self._lock:
            doc = self.get_file(kind, name)
            return doc["entries"][self._index(doc, entry_id)]

    def add_entry(self, kind: ConfigKind, name: str, data: Document) -> Document:
        with self._lock:
            doc = self.get_file(kind, name)
            entry = {"id": str(uuid.uuid4()), **data}
            self._save_entries(kind, name, [*doc["entries"], entry])
            return entry

    def replace_entry(self, kind: ConfigKind, name: str, entry_id: str, data: Document) -> Document:
        with self._lock:
            doc = self.get_file(kind, name)
            entries = doc["entries"]
            entries[self._index(doc, entry_id)] = entry = {"id": entry_id, **data}
            self._save_entries(kind, name, entries)
            return entry

    def delete_entry(self, kind: ConfigKind, name: str, entry_id: str) -> None:
        with self._lock:
            doc = self.get_file(kind, name)
            entries = doc["entries"]
            del entries[self._index(doc, entry_id)]
            self._save_entries(kind, name, entries)
