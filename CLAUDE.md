# Hannah WebUI — Projekt-Kontext

## Überblick

Flask-Verwaltungsoberfläche für [Hannah](https://dev.kernstock.net/gessinger/voice/hannah) — Räume/Gruppen-, Satelliten-, User-, Settings-, Routinen- und Trigger-Verwaltung. Spricht ausschließlich per gRPC mit Hannah Core, kein direkter DB-/Dateizugriff — Core bleibt alleiniger Owner aller Daten.

**Historie:** ursprünglich In-Process-Teil von Hannah Core (`hannah/webui.py`), dann eigener Service `webui/` im Hannah-Monorepo (#27), seit 2026-06-28 eigenständiges Repo (#106 im Monorepo). Architektur-Hintergrund zu Hannah Core/Protokoll/Satelliten: siehe `CLAUDE.md` im Hannah-Monorepo (`gessinger/voice/hannah`).

**Eigenständig, kein Submodule-Link zum Monorepo.** Einzige Abhängigkeit: `proto/hannah.proto` ist eine Kopie aus `core/proto/hannah.proto` (Source of Truth liegt im Monorepo) — bei Protokoll-Änderungen dort manuell synchronisieren, dann `scripts/gen_proto.sh` laufen lassen.

---

## Repository-Struktur

```
hannah-webui/
├── hannah_webui/
│   ├── app.py            ← Flask-App-Factory (create_app), alle Routen
│   ├── grpc_client.py    ← HannahClient — synchroner gRPC-Client (kein grpc.aio, Flask ist synchron)
│   ├── config.py         ← Config-Loader: config.yaml ODER Env-Vars (12-factor, für Container-Deploy)
│   ├── templates/         ← Jinja2-Templates (ein File pro Seite, bewusst keine Single-File/Vanilla-JS-Architektur)
│   └── proto/             ← generierte gRPC-Stubs (hannah_pb2.py, hannah_pb2_grpc.py)
├── proto/hannah.proto     ← Kopie aus core/proto/hannah.proto (Monorepo) — Source of Truth dort
├── scripts/
│   ├── gen_proto.sh       ← regeneriert hannah_webui/proto/* aus proto/hannah.proto
│   └── release.js
├── tests/                 ← pytest + FakeHannahClient (In-Memory-Stand-in, keine echte Core/kein Netzwerk nötig)
├── deploy/
│   ├── hannah-webui.service
│   └── install.sh         ← lädt Releases vom Hannah Update Server (Channel webui-stable)
├── Dockerfile / .dockerignore / gunicorn.conf.py   ← Container-Deployment
├── main.py                ← Flask-Dev-Server-Entrypoint (lokale Entwicklung)
├── wsgi.py                ← gunicorn-Entrypoint (Produktion)
└── config.example.yaml
```

---

## Architektur

**Flask-App-Factory** (`hannah_webui/app.py`): `create_app(hannah: HannahClient, secret_key: str)`. Session-basiertes Login gegen Core's `Login`-RPC. Alle Admin-/Personal-Seiten sind No-Code-Editoren (Zeilen-Builder-Pattern statt JSON-Textarea) für:

| Route | Funktion |
|---|---|
| `/login`, `/logout` | Auth |
| `/me`, `/me/password`, `/me/telegram/callback`, `/me/telegram/unlink` | Self-Service-Startseite (ersetzt die alte Index-Page): Begrüßung, eigenes Passwort ändern, Telegram-Konto verknüpfen/trennen — kein Trust-Level-Gate, wirkt nur auf die eigene `session["user_id"]`. `/` redirected dorthin. Telegram-Verknüpfung läuft über das [Login Widget](https://core.telegram.org/widgets/login); die WebUI verifiziert die HMAC-Signatur selbst (eigener `telegram_bot_token`/`telegram_bot_username` in der Config) und meldet Core nur die bereits verifizierte `account_id` per `LinkAccount` — Core/TelegramAdapter bekommen die Rohdaten nie zu Gesicht. |
| `/rooms` | Read-only Liste |
| `/groups`, `/groups/create`, `/groups/<id>/edit`, `/groups/<id>/delete` | Gruppen-CRUD |
| `/satellites`, `/satellites/<id>/room`, `/satellites/<id>/name` | Satelliten-Zuordnung (kein Delete — keine `DeleteSatellite`-RPC) |
| `/settings`, `.../update`, `.../create`, `.../delete` | generisches JSON-Textarea pro Setting (Werte zu heterogen für Feld-spezifische Formulare) |
| `/routines`, `/routines/new`, `/routines/create`, `/routines/<id>/edit`, `/routines/<id>/delete` | Personal, No-Code (Trigger-Phrasen als Zeilen, Aktionen als Typ+Wert-Zeilen) |
| `/triggers`, `/triggers/new`, `/triggers/create`, `/triggers/<id>/edit`, `/triggers/<id>/delete` | Wenn/Und/Außer-wenn/Dann-Builder; `ask`/`on_response_json`/`cancel_when` bleiben rohes JSON ("Erweitert") |
| `/users`, `/users/create`, `/users/<id>/edit`, `/users/<id>/delete`, `.../link-resident`, `.../unlink-resident` | User-CRUD + Resident-Verknüpfung |

**gRPC-Client** (`hannah_webui/grpc_client.py`, `HannahClient`): synchroner Wrapper um die generierten Stubs — `login`, `get_rooms`, `get_groups`/`create_group`/`update_group`/`delete_group`/`set_group_rooms`, `get_satellites`/`set_satellite_room`/`set_satellite_display_name`, `get_settings`/`update_setting`/`create_setting`/`delete_setting`, `get_users`/`get_residents`/`create_user`/`update_user`/`delete_user`/`set_trust_level`/`set_system_messages`/`link_account`/`unlink_account`, `get_routines`/`create_routine`/`update_routine`/`delete_routine`, `get_triggers`/`create_trigger`/`update_trigger`/`delete_trigger`.

**Tests** (`tests/`): `FakeHannahClient` ersetzt `HannahClient` durch einen In-Memory-Stand-in mit echten `hannah_pb2`-Messages — kein Netzwerk, keine echte Hannah Core nötig.

---

## Deployment

Zwei unabhängige Wege, **kein Auto-Update beim Container-Pfad**:

1. **systemd** (`deploy/install.sh` + `deploy/hannah-webui.service`) — lädt Releases vom [Hannah Update Server](https://hannah-update.sgessinger.de) (Channel `webui-stable`), Python-venv, gunicorn als User `hannah` (siehe Deploy-Konventionen im Monorepo — alle Services laufen als gemeinsamer User `hannah`). Bind-Adresse/Worker-Anzahl steht in der `.service`-Unit, nicht in `config.yaml` (gunicorn bindet den Socket vor dem WSGI-App-Import). `install.sh` ist nur für Erst-Install/manuelle Reinstalls — im laufenden Betrieb hält AutoDeploy (`hannah-autodeploy`, generischer Update-Agent für alle Hannah-Komponenten, siehe Monorepo) die Installation automatisch aktuell: pollt den Update Server auf Channel `webui-stable`, tauscht bei neuer Version die Dateien, führt den `post_install`-Hook (`pip install -r requirements.txt`) aus und restartet `hannah-webui.service`.
2. **Docker** — Multi-Arch-Image (amd64/arm64, Kaniko-Build in der CI), Push in die eigene Container Registry (`registry.dev.kernstock.net/gessinger/voice/hannah-webui`), getaggt mit Versionsnummer + `latest`. Konfiguration ausschließlich per Env-Vars (`HANNAH_WEBUI_HOST`/`PORT`/`SECRET_KEY`/`GRPC_HOST`/`GRPC_PORT`), da kein `config.yaml` im Image liegt.

`secret_key` muss über alle gunicorn-Worker und Neustarts hinweg stabil sein, sonst zufälliger Logout (siehe CHANGELOG, war ein Produktionsbug in der Monorepo-Phase).

---

## CI/CD-Pipeline (`.gitlab-ci.yml`)

```
test → container-build → upload → release
```

- **test** — pytest gegen `FakeHannahClient`
- **test:changelog** — nur in MR-Pipelines: bricht ab, wenn `hannah_webui/`, `proto/`, `main.py`, `wsgi.py`, `gunicorn.conf.py`, `config.example.yaml`, `deploy/` oder `Dockerfile` geändert wurden, aber `CHANGELOG.md` nicht — erzwingt Git-Workflow-Regel 2 (weiter unten)
- **container-build** — `.build-container` (Kaniko) als Matrix-Template für `build-container:amd64`/`:arm64`, dann `merge-manifests` (multi-arch Manifest). Läuft auf jedem Tag — **keine Change-Detection nötig**, jeder Commit in diesem Repo ist per Definition eine WebUI-Änderung (genau das war der Grund für die Extraktion aus dem Monorepo, siehe #105/#106 dort)
- **upload** — Tarball zum Update Server (Channel `webui-stable`) + Release-Notes aus `CHANGELOG.md`
- **release** — GitLab Release mit Changelog-Auszug

Versionsstand: Fresh Start bei `v1.0.0` (keine Fortführung der Monorepo-Versionsnummer `v0.46.1`, bewusste Entscheidung).

---

## Git-Workflow

Eigenständiges Repo, eigener Issue-Tracker (GitLab-Projekt `gessinger/voice/hannah-webui`) — **nicht** mehr Projekt 319 (das Hannah-Monorepo).

1. **Nie direkt auf `master` arbeiten.** Immer zuerst einen Feature-Branch anlegen.
2. **`CHANGELOG.md` parallel zu jeder Änderung pflegen** (Englisch, WIP-Sektion).
3. **Commits nur auf explizite Anfrage**, nie unaufgefordert.
4. **Pushen, wenn:** Arbeit abgeschlossen ist, eine Pause eingelegt wird, oder Arbeit gesichert werden soll.
5. **Landung auf `master` ausschließlich über Merge Request.** Nie direkt mergen.
6. **Für jede funktionale Änderung muss ein Work Item existieren** (GitLab Issue in diesem Projekt) — proaktiv vor Beginn der Umsetzung anlegen.
7. **Commit Messages referenzieren das Work Item** mit `Refs #ID`; **MR-Beschreibungen schließen es** mit `Closes #ID`.
8. Bezüge zum Monorepo (z.B. der Extraktions-Issue #106) per vollqualifizierter Referenz: `gessinger/voice/hannah#106`.

**Release-Tool:** `node scripts/release.js <major|minor|patch> [--dry-run] [--yes]` — automatisiert Versions-Bump anhand der `## **WORK IN PROGRESS**`-Sektion in `CHANGELOG.md`, Tag, Push, GitLab-API-Aufrufe (Projekt wird aus der Git-Remote-URL abgeleitet). Generisches Tool, nicht webui-spezifisch.

---

## Status

Aktueller Stand: siehe `CHANGELOG.md`. Offene Bugs/Features: GitLab Issues in diesem Projekt — nicht hier duplizieren.

---

## Bekannte Probleme & Workarounds

- **gunicorn ≥ 26 hat den `eventlet`-Worker entfernt** (`SUPPORTED_WORKERS` enthält ihn nicht mehr, eventlet selbst ist upstream deprecated). Falls async Worker mal nötig werden: `gevent`/`gevent_wsgi`/`gevent_pywsgi` sind noch unterstützt, `eventlet` nicht. Aktuell laufen sync-Worker — kein konkreter Bedarf für async identifiziert (keine SSE/Streaming-Seiten, kleiner Nutzerkreis).
- **Proto-Sync:** `proto/hannah.proto` muss nach Änderungen an `core/proto/hannah.proto` im Monorepo manuell kopiert werden, dann `scripts/gen_proto.sh`.
