import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.systemd import DnsmasqService

SHOW_ACTIVE = "LoadState=loaded\nActiveState=active\nSubState=running\nActiveEnterTimestamp=Wed 2026-10-14 23:46:11 CEST\n"


class FakeRunner:
    """Records commands and answers like systemctl/dnsmasq would."""

    def __init__(self, show: str = SHOW_ACTIVE, test_rc: int = 0, restart_rc: int = 0) -> None:
        self.show, self.test_rc, self.restart_rc = show, test_rc, restart_rc
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
        cmd = list(cmd)
        self.calls.append(cmd)
        if cmd[1] == "show":
            return subprocess.CompletedProcess(cmd, 0, self.show, "")
        if cmd[1] == "--test":
            err = "dnsmasq: syntax check OK." if self.test_rc == 0 else "dnsmasq: bad option at line 3"
            return subprocess.CompletedProcess(cmd, self.test_rc, "", err)
        if "restart" in cmd:
            err = "" if self.restart_rc == 0 else "Interactive authentication required."
            return subprocess.CompletedProcess(cmd, self.restart_rc, "", err)
        raise AssertionError(f"unexpected command {cmd}")

    @property
    def restarted(self) -> bool:
        return any("restart" in c for c in self.calls)


@pytest.fixture
def make_client(tmp_path: Path):
    clients = []

    def factory(runner: FakeRunner, *, booted: bool = True, unit: str | None = "dnsmasq.service") -> TestClient:
        settings = Settings(conf_dir=tmp_path / "d", db_path=tmp_path / "db.json", frontend_dir=tmp_path / "none")
        client = TestClient(create_app(settings)).__enter__()
        client.app.state.dnsmasq = DnsmasqService(
            unit, runner=runner, systemd_booted=booted, systemctl="systemctl", dnsmasq="dnsmasq"
        )
        clients.append(client)
        return client

    yield factory
    for c in clients:
        c.__exit__(None, None, None)


def test_status_available(make_client):
    body = make_client(FakeRunner()).get("/api/service").json()
    assert body["available"] is True
    assert body["active_state"] == "active" and body["sub_state"] == "running"


@pytest.mark.parametrize(
    ("runner", "booted", "unit", "reason"),
    [
        (FakeRunner(), False, "dnsmasq.service", "not running systemd"),
        (FakeRunner(show="LoadState=not-found\n"), True, "dnsmasq.service", "not installed"),
        (FakeRunner(), True, None, "disabled"),
    ],
)
def test_status_unavailable(make_client, runner, booted, unit, reason):
    client = make_client(runner, booted=booted, unit=unit)
    body = client.get("/api/service").json()
    assert body["available"] is False and reason in body["reason"]
    r = client.post("/api/service/restart")
    assert r.status_code == 503
    assert not runner.restarted


def test_restart_runs_config_test_first(make_client):
    runner = FakeRunner()
    r = make_client(runner).post("/api/service/restart")
    assert r.status_code == 200
    commands = [c[1] for c in runner.calls]
    assert commands.index("--test") < commands.index("--no-ask-password")
    assert ["systemctl", "--no-ask-password", "restart", "dnsmasq.service"] in runner.calls


def test_restart_aborted_on_invalid_config(make_client):
    runner = FakeRunner(test_rc=1)
    r = make_client(runner).post("/api/service/restart")
    assert r.status_code == 422
    assert "bad option at line 3" in r.json()["detail"]
    assert not runner.restarted


def test_restart_permission_error(make_client):
    r = make_client(FakeRunner(restart_rc=1)).post("/api/service/restart")
    assert r.status_code == 502
    assert "Interactive authentication required" in r.json()["detail"]


def test_invalid_unit_setting():
    with pytest.raises(ValueError):
        Settings(systemd_unit="dnsmasq; rm -rf /")
