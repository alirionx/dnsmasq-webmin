"""Restart dnsmasq via systemd - only offered when dnsmasq actually runs as a systemd unit."""

import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from app.models import ServiceStatus

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)


class ServiceUnavailableError(Exception):
    """dnsmasq is not managed by systemd (or the feature is disabled)."""


class ConfigTestError(Exception):
    """``dnsmasq --test`` rejected the configuration."""


class CommandError(Exception):
    """systemctl failed, e.g. missing permissions."""


class DnsmasqService:
    def __init__(
        self,
        unit: str | None,
        *,
        runner: Runner = _run,
        systemd_booted: bool | None = None,
        systemctl: str | None = None,
        dnsmasq: str | None = None,
    ) -> None:
        self.unit = unit
        self._run = runner
        # same check as sd_booted(3): systemd is PID 1 if this directory exists
        self._booted = Path("/run/systemd/system").is_dir() if systemd_booted is None else systemd_booted
        self._systemctl = systemctl or shutil.which("systemctl")
        self._dnsmasq = dnsmasq or shutil.which("dnsmasq") or (
            "/usr/sbin/dnsmasq" if Path("/usr/sbin/dnsmasq").is_file() else None
        )

    def _show(self) -> dict[str, str]:
        props = "LoadState,ActiveState,SubState,ActiveEnterTimestamp"
        res = self._run([self._systemctl, "show", self.unit, f"--property={props}"])
        if res.returncode != 0:
            return {}
        return dict(line.split("=", 1) for line in res.stdout.splitlines() if "=" in line)

    def status(self) -> ServiceStatus:
        if not self.unit:
            return ServiceStatus(available=False, reason="Restart via systemd is disabled.")
        if not (self._booted and self._systemctl):
            return ServiceStatus(available=False, unit=self.unit, reason="System is not running systemd.")
        props = self._show()
        if props.get("LoadState") != "loaded":
            return ServiceStatus(
                available=False, unit=self.unit, reason=f"Unit {self.unit} is not installed in systemd."
            )
        return ServiceStatus(
            available=True,
            unit=self.unit,
            active_state=props.get("ActiveState"),
            sub_state=props.get("SubState"),
            since=props.get("ActiveEnterTimestamp") or None,
        )

    def test_config(self) -> str:
        """Run ``dnsmasq --test`` on the system config (incl. conf-dir). Skipped if dnsmasq is not found."""
        if not self._dnsmasq:
            return "dnsmasq binary not found, config test skipped"
        res = self._run([self._dnsmasq, "--test"])
        output = (res.stderr or res.stdout).strip()
        if res.returncode != 0:
            raise ConfigTestError(output or "dnsmasq --test failed")
        return output

    def restart(self) -> ServiceStatus:
        """Validate the config first - a broken config must not take down DNS/DHCP."""
        current = self.status()
        if not current.available:
            raise ServiceUnavailableError(current.reason)
        self.test_config()
        res = self._run([self._systemctl, "--no-ask-password", "restart", self.unit])
        if res.returncode != 0:
            raise CommandError((res.stderr or res.stdout).strip() or f"systemctl restart {self.unit} failed")
        return self.status()
