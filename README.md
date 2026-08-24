# Hannah WebUI

[![pipeline status](https://dev.kernstock.net/gessinger/voice/hannah-webui/badges/master/pipeline.svg)](https://dev.kernstock.net/gessinger/voice/hannah-webui/-/commits/master)
[![Latest Release](https://dev.kernstock.net/gessinger/voice/hannah-webui/-/badges/release.svg)](https://dev.kernstock.net/gessinger/voice/hannah-webui/-/releases)

Flask-Verwaltungsoberfläche für [Hannah](https://dev.kernstock.net/gessinger/voice/hannah) — Räume/Gruppen-, Satelliten-, User-, Settings- und Trigger-Verwaltung, plus eine Self-Service-Startseite für alle Bewohner (Passwort, Telegram-Verknüpfung, Wecker, Nachrichten). Spricht ausschließlich per gRPC mit Hannah Core — kein direkter DB-/Dateizugriff, Core bleibt alleiniger Owner aller Daten.

Extrahiert aus dem Hannah-Monorepo (`webui/`), siehe `CHANGELOG.md`. Architektur-/Protokoll-Hintergrund zu Hannah Core: [CLAUDE.md](CLAUDE.md).

---

## Was kann die WebUI?

- **Räume & Gruppen** — Räume read-only anzeigen, Gruppen anlegen/bearbeiten/löschen und Satelliten zuweisen
- **Satelliten** — einem Raum zuordnen, Anzeigenamen setzen
- **Trigger** — Wenn/Und/Außer-wenn/Dann-Regelbuilder (Bedingungstyp `state`/`time`/`phrase`), löste die frühere separate Routinen-Verwaltung ab
- **Settings** — No-Code-Editor für Core-Settings, Render-Typ (Text/Zeilen-Builder/Key-Value/rohes JSON) wird automatisch aus der Werteform abgeleitet
- **BLE-Tags & Fahrzeuge** — CRUD inkl. Owner-Zuweisung
- **Nutzerverwaltung** — User anlegen/bearbeiten/löschen, Trust-Level setzen, mit Residents verknüpfen
- **Verlauf** — eigene geloggte Interaktionen (Transkript, Kanal, Intent, Antworttext) mit Audio-Wiedergabe; Trust-Level 10 sieht wahlweise den Verlauf anderer User
- **Nachrichten** — passive Mailbox mit Antwort-Flow, Badge mit ungelesener Anzahl in der Navigation
- **Self-Service (`/me`)** — eigenes Passwort ändern, Telegram-Konto verknüpfen/trennen (über das [Login Widget](https://core.telegram.org/widgets/login), WebUI verifiziert die Signatur selbst), Wecker verwalten

Ausführliche Bedienungsanleitung je Seite: [`docs/usage.md`](docs/usage.md).

---

## Seiten-Übersicht & Berechtigungen

Jeder Nutzer braucht einen Hannah-Core-Account; der Zugriff auf Admin-Seiten ist per Trust-Level gestaffelt (`hannah_webui/extensions.py: TRUST_LEVELS`). Self-Service-Seiten (`/me`, `/messages`) sind für jeden eingeloggten User offen.

| Seite | Route | Min. Trust-Level |
|---|---|---|
| Startseite / Self-Service | `/me` | jeder eingeloggte User |
| Nachrichten | `/messages` | jeder eingeloggte User |
| Verlauf (eigener) | `/activity-log` | jeder eingeloggte User |
| Verlauf (fremder, per Filter) | `/activity-log` | 10 |
| Räume | `/rooms` | 3 |
| Satelliten | `/satellites` | 5 |
| Trigger anzeigen | `/triggers` | 5 |
| Trigger anlegen/bearbeiten/löschen | `/triggers/...` | 7 |
| Gruppen, Settings, BLE-Tags, Fahrzeuge, User | `/groups`, `/settings`, `/ble-tags`, `/cars`, `/users` | 10 |

---

## Architektur

Flask-App-Factory (`create_app`, `hannah_webui/app.py`) registriert einen Blueprint je Routen-Gruppe (`hannah_webui/blueprints/`), hängt den gRPC-Client als `app.extensions["hannah"]` ein und rendert bei nicht erreichbarer Core eine eigene Fehlerseite statt eines 500ers. Session-basiertes Login gegen Core's `Login`-RPC. Details, gRPC-Client-Methoden, Blueprint-Liste: [CLAUDE.md](CLAUDE.md).

---

## Voraussetzungen

- Eine erreichbare Hannah-Core-Instanz (gRPC) — siehe [Hannah-Repo](https://dev.kernstock.net/gessinger/voice/hannah)
- Python 3.11+ (nur für lokale Entwicklung/systemd-Deployment, nicht für Docker nötig)

---

## Lokale Entwicklung

```sh
python -m venv venv
venv/Scripts/pip install -r requirements.txt -r tests/requirements-test.txt
cp config.example.yaml config.yaml   # secret_key + gRPC-Host anpassen
venv/Scripts/python main.py
```

Tests:

```sh
pytest tests/ -v
```

`tests/` nutzt `FakeHannahClient`, einen In-Memory-Stand-in mit echten `hannah_pb2`-Messages — keine echte Hannah Core nötig.

---

## Konfiguration

`config.yaml` (siehe `config.example.yaml`) oder Env-Vars — welcher Weg gilt, hängt davon ab, ob am gestarteten Pfad eine `config.yaml` existiert:

```yaml
host: "127.0.0.1"
port: 5000

# Signiert die Flask-Session-Cookie — muss über alle gunicorn-Worker und
# Neustarts hinweg stabil sein, sonst werden Nutzer zufällig ausgeloggt.
# Generieren mit: python3 -c "import secrets; print(secrets.token_hex(32))"
secret_key: "..."

# Telegram Login Widget (Account-Verknüpfung in /me) — Bot-Token via
# @BotFather, Domain muss dort per /setdomain auf diese WebUI-Instanz
# freigeschaltet sein.
telegram_bot_token: ""
telegram_bot_username: ""

grpc:
  host: "127.0.0.1"
  port: 50051
```

Äquivalente Env-Vars (Docker-Pfad, kein `config.yaml` im Image): `HANNAH_WEBUI_HOST`, `HANNAH_WEBUI_PORT`, `HANNAH_WEBUI_SECRET_KEY`, `HANNAH_WEBUI_TELEGRAM_BOT_TOKEN`, `HANNAH_WEBUI_TELEGRAM_BOT_USERNAME`, `HANNAH_WEBUI_GRPC_HOST`, `HANNAH_WEBUI_GRPC_PORT`.

---

## Deployment

Zwei unabhängige Wege, kein Auto-Update beim Container-Pfad:

### systemd

```bash
curl -fsSL https://dev.kernstock.net/gessinger/voice/hannah-webui/-/raw/master/deploy/install.sh | sudo bash
```

Lädt das aktuellste Release vom [Hannah Update Server](https://hannah-update.sgessinger.de) (Channel `webui-stable`), richtet venv, System-User `hannah` und den systemd-Service ein. Config danach unter `/etc/hannah-webui/config.yaml` ablegen und starten:

```bash
sudo systemctl enable --now hannah-webui
```

Erneuter Aufruf des Skripts aktualisiert auf die neueste Version; `--uninstall` entfernt den Service (Config bleibt erhalten). Im laufenden Betrieb hält **AutoDeploy** (`hannah-autodeploy`) die Installation automatisch aktuell: pollt den Update Server auf Channel `webui-stable`, tauscht Dateien, führt `pip install -r requirements.txt` aus und restartet den Service — `install.sh` ist nur für Erst-Install/manuelle Reinstalls nötig.

Bind-Adresse/Worker-Anzahl stehen in der `.service`-Unit, nicht in `config.yaml` (gunicorn bindet den Socket vor dem WSGI-App-Import).

### Docker

Multi-Arch-Image (amd64/arm64), Konfiguration ausschließlich per Env-Vars:

```bash
docker run -d \
  -p 5000:5000 \
  -e HANNAH_WEBUI_SECRET_KEY="..." \
  -e HANNAH_WEBUI_GRPC_HOST=hannah-core \
  -e HANNAH_WEBUI_GRPC_PORT=50051 \
  registry.dev.kernstock.net/gessinger/voice/hannah-webui:latest
```

Getaggt mit Versionsnummer und `latest`.

---

## Weiterführend

Aktueller Stand und Änderungshistorie: [`CHANGELOG.md`](CHANGELOG.md). Offene Bugs/Features werden als [GitLab Issues](https://dev.kernstock.net/gessinger/voice/hannah-webui/-/issues) geführt, nicht hier dupliziert. Architektur-/Entwicklungs-Details: [`CLAUDE.md`](CLAUDE.md).
