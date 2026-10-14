from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.render import MANAGED_MARKER


@pytest.fixture
def conf_dir(tmp_path: Path) -> Path:
    return tmp_path / "dnsmasq.d"


@pytest.fixture
def client(tmp_path: Path, conf_dir: Path):
    settings = Settings(conf_dir=conf_dir, db_path=tmp_path / "db.json")
    with TestClient(create_app(settings)) as c:
        yield c


def test_dns_file_crud_and_render(client: TestClient, conf_dir: Path):
    r = client.post("/api/dns-files", json={"name": "home", "description": "Home LAN"})
    assert r.status_code == 201
    assert r.json()["filename"] == "webmin-dns-home.conf"
    assert client.post("/api/dns-files", json={"name": "home"}).status_code == 409

    r = client.post(
        "/api/dns-files/home/entries",
        json={"type": "host-record", "names": ["NAS.home.lan", "nas"], "ipv4": "192.168.1.10", "comment": "NAS"},
    )
    assert r.status_code == 201, r.text
    host = r.json()
    assert host["names"] == ["nas.home.lan", "nas"]

    client.post("/api/dns-files/home/entries", json={"type": "cname", "aliases": ["files.home.lan"], "target": "nas"})
    client.post("/api/dns-files/home/entries", json={"type": "address", "domains": ["ads.example"], "ip": "0.0.0.0"})

    # update
    r = client.put(
        f"/api/dns-files/home/entries/{host['id']}",
        json={"type": "host-record", "names": ["nas"], "ipv4": "192.168.1.11", "ipv6": "fd00::11", "ttl": 300},
    )
    assert r.status_code == 200 and r.json()["id"] == host["id"]

    expected = (
        f"{MANAGED_MARKER}\n# dns config: home\n# Home LAN\n\n"
        "host-record=nas,192.168.1.11,fd00::11,300\n"
        "cname=files.home.lan,nas\n"
        "address=/ads.example/0.0.0.0\n"
    )
    r = client.get("/api/dns-files/home/render")
    assert r.headers["content-type"].startswith("text/plain")
    assert r.text == expected
    assert (conf_dir / "webmin-dns-home.conf").read_text() == expected

    # delete entry
    assert client.delete(f"/api/dns-files/home/entries/{host['id']}").status_code == 204
    assert client.get(f"/api/dns-files/home/entries/{host['id']}").status_code == 404
    assert len(client.get("/api/dns-files/home/entries").json()) == 2

    # rename moves the file
    r = client.patch("/api/dns-files/home", json={"name": "lan"})
    assert r.json()["filename"] == "webmin-dns-lan.conf"
    assert not (conf_dir / "webmin-dns-home.conf").exists()
    assert (conf_dir / "webmin-dns-lan.conf").exists()

    # delete file
    assert client.delete("/api/dns-files/lan").status_code == 204
    assert not (conf_dir / "webmin-dns-lan.conf").exists()
    assert client.get("/api/dns-files/lan").status_code == 404


def test_dhcp_ranges(client: TestClient, conf_dir: Path):
    client.post("/api/dhcp-files", json={"name": "lan"})
    r = client.post(
        "/api/dhcp-files/lan/entries",
        json={"start": "192.168.1.100", "end": "192.168.1.200", "netmask": "255.255.255.0",
              "lease_time": "12h", "set_tag": "lan"},
    )
    assert r.status_code == 201, r.text
    client.post(
        "/api/dhcp-files/lan/entries",
        json={"start": "fd00::100", "end": "fd00::1ff", "prefix_length": 64, "match_tags": ["v6"]},
    )
    content = (conf_dir / "webmin-dhcp-lan.conf").read_text()
    assert "dhcp-range=set:lan,192.168.1.100,192.168.1.200,255.255.255.0,12h\n" in content
    assert "dhcp-range=tag:v6,fd00::100,fd00::1ff,64\n" in content


@pytest.mark.parametrize(
    "body",
    [
        {"start": "192.168.1.200", "end": "192.168.1.100"},  # start > end
        {"start": "192.168.1.1", "end": "fd00::1"},  # mixed versions
        {"start": "fd00::1", "end": "fd00::2", "netmask": "255.255.255.0"},
        {"start": "192.168.1.1", "end": "192.168.1.2", "lease_time": "12h\naddress=/x/1.2.3.4"},
        {"start": "192.168.1.1", "end": "192.168.1.2", "unknown": 1},
    ],
)
def test_dhcp_validation(client: TestClient, body: dict):
    client.post("/api/dhcp-files", json={"name": "lan"})
    assert client.post("/api/dhcp-files/lan/entries", json=body).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"type": "host-record", "names": ["nas"]},  # no address
        {"type": "host-record", "names": ["bad,name"], "ipv4": "10.0.0.1"},
        {"type": "address", "domains": ["a/b"], "ip": "10.0.0.1"},
        {"type": "cname", "aliases": ["x"], "target": "y", "comment": "multi\nline"},
        {"type": "mx", "name": "x"},
    ],
)
def test_dns_validation(client: TestClient, body: dict):
    client.post("/api/dns-files", json={"name": "home"})
    assert client.post("/api/dns-files/home/entries", json=body).status_code == 422


def test_invalid_file_name(client: TestClient):
    assert client.post("/api/dns-files", json={"name": "../etc/passwd"}).status_code == 422


def test_render_all_and_sync(client: TestClient, conf_dir: Path):
    client.post("/api/dns-files", json={"name": "a"})
    client.post("/api/dhcp-files", json={"name": "b"})

    rendered = client.get("/api/render").json()
    assert {r["filename"] for r in rendered} == {"webmin-dns-a.conf", "webmin-dhcp-b.conf"}
    assert [r["kind"] for r in client.get("/api/render", params={"kind": "dhcp"}).json()] == ["dhcp"]
    assert "### webmin-dns-a.conf" in client.get("/api/render/text").text

    # orphaned managed file is removed, foreign files stay untouched
    (conf_dir / "webmin-dns-old.conf").write_text(MANAGED_MARKER + "\n")
    (conf_dir / "webmin-foreign.conf").write_text("server=1.1.1.1\n")
    (conf_dir / "other.conf").write_text("server=8.8.8.8\n")
    result = client.post("/api/sync").json()
    assert result["removed"] == ["webmin-dns-old.conf"]
    assert (conf_dir / "webmin-foreign.conf").exists()
    assert (conf_dir / "other.conf").exists()


def test_does_not_overwrite_unmanaged_file(client: TestClient, conf_dir: Path):
    conf_dir.mkdir(parents=True)
    (conf_dir / "webmin-dns-x.conf").write_text("# hand written\n")
    r = client.post("/api/dns-files", json={"name": "x"})
    assert r.status_code == 500
    assert (conf_dir / "webmin-dns-x.conf").read_text() == "# hand written\n"


@pytest.fixture
def spa_client(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("secret")
    settings = Settings(conf_dir=tmp_path / "d", db_path=tmp_path / "db.json", frontend_dir=dist)
    with TestClient(create_app(settings)) as c:
        yield c


def test_spa_serving(spa_client: TestClient):
    assert spa_client.get("/").text == "<html>spa</html>"
    assert spa_client.get("/dns/home-lan").text == "<html>spa</html>"  # client-side route
    assert spa_client.get("/assets/app.js").text == "console.log(1)"
    assert spa_client.get("/api/unknown").status_code == 404
    assert spa_client.get("/api/dns-files").json() == []
    assert spa_client.get("/docs").status_code == 200


@pytest.mark.parametrize("path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/%2e%2e/%2e%2e/secret.txt"])
def test_spa_no_path_traversal(spa_client: TestClient, path: str):
    assert "secret" not in spa_client.get(path).text
