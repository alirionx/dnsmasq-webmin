# dnsmasq-webmin

FastAPI-App mit Vue-Weboberfläche zum Verwalten von dnsmasq-Sub-Configs (DNS-Einträge und DHCP-Ranges) in `/etc/dnsmasq.d/`.
Die Grundconfig (`/etc/dnsmasq.conf`) wird nie angefasst.

## Funktionsweise

- Datastore: [TinyDB](https://tinydb.readthedocs.io) (JSON-Dokumente, eine Datei). Ein Dokument pro Config-File.
- Jede Änderung schreibt die betroffene Datei sofort und atomar (Temp-Datei + Rename) nach
  `<conf_dir>/<prefix><kind>-<name>.conf`, z.B. `/etc/dnsmasq.d/webmin-dns-home.conf`.
- Die App ändert oder löscht nur Dateien, die mit dem Prefix beginnen **und** in der ersten Zeile den
  Marker `# Managed by dnsmasq-webmin ...` tragen. Fremde Dateien bleiben unberührt.
- Alle Felder, die in der Config landen, werden über Pydantic-Patterns validiert (keine Kommas,
  Slashes oder Zeilenumbrüche), damit sich nichts in die Config einschleusen lässt.

dnsmasq muss das Verzeichnis einlesen (Debian/Ubuntu: Standard), in `/etc/dnsmasq.conf`:

```
conf-dir=/etc/dnsmasq.d/,*.conf
```

Nach Änderungen muss dnsmasq neu gestartet werden. Läuft dnsmasq als systemd-Unit (Standard), geht das
über die Weboberfläche bzw. `POST /api/service/restart` – siehe [dnsmasq neu starten](#dnsmasq-neu-starten).

## Installation & Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# Weboberfläche bauen (Node.js >= 20)
(cd frontend && npm ci && npm run build)

.venv/bin/python -m app.main
```

- Weboberfläche: http://127.0.0.1:5000/
- API-Doku: http://127.0.0.1:5000/docs

Existiert `frontend/dist/` nicht, läuft nur die API.

### Konfiguration (Umgebungsvariablen oder `.env`)

| Variable                          | Default                             |
|-----------------------------------|-------------------------------------|
| `DNSMASQ_WEBMIN_CONF_DIR`         | `/etc/dnsmasq.d`                    |
| `DNSMASQ_WEBMIN_DB_PATH`          | `/tmp/dnsmasq-webmin/db.json`       |
| `DNSMASQ_WEBMIN_FILE_PREFIX`      | `webmin-`                           |
| `DNSMASQ_WEBMIN_WRITE_ON_CHANGE`  | `true`                              |
| `APP_DEBUG`                       | `false` (Auto-Reload, nur bei `python -m app.main`) |
| `APP_HOST`                        | `0.0.0.0` (nur bei `python -m app.main`) |
| `APP_PORT`                        | `5000` (nur bei `python -m app.main`) |
| `DNSMASQ_WEBMIN_FRONTEND_DIR`     | `frontend/dist` im Projekt          |
| `DNSMASQ_WEBMIN_SYSTEMD_UNIT`     | `dnsmasq.service` (leer = Restart deaktiviert) |

Zum lokalen Testen ohne root:

```bash
DNSMASQ_WEBMIN_CONF_DIR=./data/dnsmasq.d DNSMASQ_WEBMIN_DB_PATH=./data/db.json APP_DEBUG=true .venv/bin/python -m app.main
```

## Weboberfläche

Vue 3 + [Vuetify](https://vuetifyjs.com), gebaut mit Vite. Optik wie cloudinit-nocloud-configurator: dunkles Theme
als Standard, Akzent Mint/Lachs, feste Sidebar, Schrift Inter (lokal gebündelt), Icons von Lucide.
Quellcode in `frontend/src/`:

| Datei | Inhalt |
|---|---|
| `views/ConfigFilesView.vue` | Config-Files und deren Einträge (für DNS und DHCP) |
| `views/RenderView.vue` | Gerenderte Configs, „Sync to disk“ |
| `components/*Dialog.vue` | Formulare (Anlegen/Bearbeiten/Löschen) |
| `kinds.js` | Tabellenspalten und Texte je Typ (dns/dhcp) |
| `rules.js` | Client-Validierung (Backend bleibt maßgeblich) |
| `plugins/vuetify.js` | Farbpalette (hell/dunkel) und Komponenten-Defaults |
| `styles/app.css` | globale Styles (Schrift, Seitenlayout, Tabellen) |
| `theme.js` | Theme-Umschaltung, gespeichert im Browser |
| `api.js` | Fetch-Wrapper für `/api` |

Entwicklung mit Hot-Reload: Backend auf Port 5000 starten, dann

```bash
cd frontend && npm run dev   # http://localhost:5173, /api wird an :5000 weitergeleitet
```

Anderes Backend: `API_URL=http://127.0.0.1:8080 npm run dev`.

## Endpoints

Alle API-Pfade liegen unter `/api`. `{kind}` ist `dns` oder `dhcp`.

| Methode | Pfad                                   | Beschreibung                                |
|---------|----------------------------------------|---------------------------------------------|
| GET/POST| `/{kind}-files`                        | Config-Files auflisten / anlegen            |
| GET/PATCH/DELETE | `/{kind}-files/{name}`        | Lesen / Beschreibung ändern, umbenennen / löschen |
| GET     | `/{kind}-files/{name}/render`          | Einzelnes File als `text/plain`             |
| GET/POST| `/{kind}-files/{name}/entries`         | Einträge auflisten / hinzufügen             |
| GET/PUT/DELETE | `/{kind}-files/{name}/entries/{id}` | Eintrag lesen / ersetzen / löschen     |
| GET     | `/render[?kind=dns]`                   | Alle Files gerendert (JSON)                 |
| GET     | `/render/text[?kind=dns]`              | Alle Files gerendert als ein Text           |
| POST    | `/sync`                                | Alle Files neu schreiben, verwaiste entfernen |
| GET     | `/service`                             | systemd-Status von dnsmasq                  |
| POST    | `/service/restart`                     | `dnsmasq --test`, dann `systemctl restart`  |

## dnsmasq neu starten

Der Restart wird nur angeboten, wenn alle Bedingungen erfüllt sind:

1. Das System läuft mit systemd (`/run/systemd/system` existiert),
2. die Unit (`DNSMASQ_WEBMIN_SYSTEMD_UNIT`, Default `dnsmasq.service`) ist in systemd geladen.

Sonst liefert `GET /api/service` `"available": false` mit Begründung, und die Weboberfläche blendet Status und
Restart-Button aus.

Vor jedem Restart läuft `dnsmasq --test` gegen die komplette System-Config. Schlägt der Test fehl, wird **nicht**
neu gestartet (HTTP 422 mit der Ausgabe von dnsmasq), damit eine kaputte Config DNS/DHCP nicht lahmlegt.

`systemctl restart` braucht root-Rechte (oder eine passende polkit-Regel). Ohne Rechte kommt HTTP 502 mit der
Meldung von systemctl; es wird nie interaktiv nach einem Passwort gefragt (`--no-ask-password`).

## Beispiele

```bash
API=http://127.0.0.1:5000/api

curl -X POST $API/dns-files -H 'content-type: application/json' \
  -d '{"name": "home", "description": "Heimnetz"}'

# A/AAAA + PTR:  host-record=nas.home.lan,nas,192.168.1.10
curl -X POST $API/dns-files/home/entries -H 'content-type: application/json' \
  -d '{"type": "host-record", "names": ["nas.home.lan", "nas"], "ipv4": "192.168.1.10"}'

# Domain inkl. Subdomains:  address=/ads.example/0.0.0.0
curl -X POST $API/dns-files/home/entries -H 'content-type: application/json' \
  -d '{"type": "address", "domains": ["ads.example"], "ip": "0.0.0.0"}'

# cname=files.home.lan,nas.home.lan
curl -X POST $API/dns-files/home/entries -H 'content-type: application/json' \
  -d '{"type": "cname", "aliases": ["files.home.lan"], "target": "nas.home.lan"}'

curl -X POST $API/dhcp-files -H 'content-type: application/json' -d '{"name": "lan"}'

# dhcp-range=set:lan,192.168.1.100,192.168.1.200,255.255.255.0,12h
curl -X POST $API/dhcp-files/lan/entries -H 'content-type: application/json' \
  -d '{"start": "192.168.1.100", "end": "192.168.1.200", "netmask": "255.255.255.0", "lease_time": "12h", "set_tag": "lan"}'

curl $API/dns-files/home/render
curl $API/render/text
```

## Debian-Paket (systemd-Service)

```bash
PY=3.13 packaging/deb/build-deb.sh   # Debian 13 trixie  → dist/dnsmasq-webmin_0.1.0-1+py313_amd64.deb
PY=3.12 packaging/deb/build-deb.sh   # Ubuntu 24.04      → dist/dnsmasq-webmin_0.1.0-1+py312_amd64.deb

sudo apt install ./dist/dnsmasq-webmin_0.1.0-1+py313_amd64.deb
```

- App unter `/opt/dnsmasq-webmin`, Python-Abhängigkeiten gebündelt in `/opt/dnsmasq-webmin/lib`,
  läuft mit dem System-`python3`. Die nativen Module sind an die Python-Version gebunden, daher gibt es je
  Ziel-Distribution ein eigenes Paket (`PY`, nur amd64). Debian 12 (Python 3.11) wird nicht unterstützt.
- Service `dnsmasq-webmin.service` wird bei der Installation aktiviert und gestartet.
- Konfiguration: `/etc/dnsmasq-webmin/dnsmasq-webmin.env` (conffile, bleibt bei Updates erhalten),
  danach `sudo systemctl restart dnsmasq-webmin`.
- Datenbank: `/var/lib/dnsmasq-webmin/db.json`.
- Der Service läuft als root (Schreibzugriff auf `/etc/dnsmasq.d`, Restart von dnsmasq), ist aber per systemd
  gehärtet: Dateisystem read-only bis auf `/etc/dnsmasq.d` und das State-Dir, kein Home, private `/tmp` und
  `/dev`, `NoNewPrivileges`, `MemoryDenyWriteExecute` u.a.
- `apt purge` löscht Datenbank und Config, die generierten Dateien in `/etc/dnsmasq.d` bleiben bewusst liegen.

## Docker

Multi-Stage-Build auf Alpine-Basis: Node baut die SPA, Python installiert die Abhängigkeiten (nur fertige
Wheels, kein Compiler), das Runtime-Image enthält nur Python, venv, App und `dist/`. Läuft als User `app` (uid 10001).

```bash
docker build -t dnsmasq-webmin .

docker run -d --name dnsmasq-webmin \
  -p 5000:5000 \
  -v /etc/dnsmasq.d:/etc/dnsmasq.d \
  -v dnsmasq-webmin-data:/data \
  dnsmasq-webmin
```

- `/etc/dnsmasq.d`: Conf-Dir des Hosts. Der Container-User (uid 10001) braucht Schreibrechte, z.B.
  `sudo setfacl -m u:10001:rwx /etc/dnsmasq.d` – oder den Container mit `--user 0` starten.
- `/data`: TinyDB (`/data/db.json`). Als Named Volume persistent über Container-Updates hinweg.
- Im Container gibt es kein systemd, daher ist der dnsmasq-Restart dort nicht verfügbar (Button ausgeblendet).
  dnsmasq auf dem Host danach selbst neu starten: `sudo systemctl restart dnsmasq`.

## CI (GitHub Actions)

Beide Workflows laufen nur bei Push auf `main` und testen vorher mit `pytest`.

| Workflow | Ergebnis |
|---|---|
| `.github/workflows/docker.yml` | `ghcr.io/<owner>/dnsmasq-webmin:latest` und `:sha-<commit>` |
| `.github/workflows/deb.yml` | GitHub-Release `v<version>-<run>` mit den `.deb` für Python 3.12 und 3.13 |

Die Debian-Revision ist die Workflow-Laufnummer, jede neue Version ist damit ein Upgrade der vorherigen.

## Tests

```bash
.venv/bin/pytest
```
