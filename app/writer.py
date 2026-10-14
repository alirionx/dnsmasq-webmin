"""Writes rendered config files into the dnsmasq conf dir.

Only files carrying the configured prefix *and* the managed marker are ever
modified or removed, so the base config and foreign files stay untouched.
"""

import os
import tempfile
from pathlib import Path

from app.models import ConfigKind
from app.render import MANAGED_MARKER


class ConfWriter:
    def __init__(self, conf_dir: Path, prefix: str) -> None:
        self.conf_dir = conf_dir
        self.prefix = prefix

    def filename(self, kind: ConfigKind, name: str) -> str:
        return f"{self.prefix}{kind.value}-{name}.conf"

    def _is_managed(self, path: Path) -> bool:
        if not (path.is_file() and path.name.startswith(self.prefix) and path.suffix == ".conf"):
            return False
        with path.open(encoding="utf-8", errors="replace") as fh:
            return fh.readline().rstrip("\n") == MANAGED_MARKER

    def write(self, filename: str, content: str) -> None:
        """Atomically write a file (temp file + rename), so dnsmasq never reads half a file."""
        self.conf_dir.mkdir(parents=True, exist_ok=True)
        target = self.conf_dir / filename
        if target.exists() and not self._is_managed(target):
            raise PermissionError(f"refusing to overwrite unmanaged file {target}")
        fd, tmp = tempfile.mkstemp(dir=self.conf_dir, prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.chmod(tmp, 0o644)
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def remove(self, filename: str) -> bool:
        target = self.conf_dir / filename
        if self._is_managed(target):
            target.unlink()
            return True
        return False

    def managed_files(self) -> list[str]:
        if not self.conf_dir.is_dir():
            return []
        return sorted(p.name for p in self.conf_dir.iterdir() if self._is_managed(p))
