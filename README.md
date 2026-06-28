# Hannah WebUI

Flask-Verwaltungsoberfläche für [Hannah](https://dev.kernstock.net/gessinger/voice/hannah) — Räume/Gruppen-, Satelliten-, User-, Trigger- und Routinen-Verwaltung, per gRPC an Hannah Core angebunden (synchroner `HannahClient`, kein `grpc.aio`).

Extrahiert aus dem Hannah-Monorepo (`webui/`), siehe `CHANGELOG.md`.

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

## Deployment

Zwei unabhängige Wege, kein Auto-Update beim Container-Pfad:

- **systemd** (`deploy/install.sh`) — lädt Releases vom [Hannah Update Server](https://hannah-update.sgessinger.de) (Channel `webui-stable`), Python-venv + gunicorn.
- **Docker** — Multi-Arch-Image (amd64/arm64) in dieser Projekt-Registry (`registry.dev.kernstock.net/gessinger/voice/hannah-webui`), getaggt mit Versionsnummer und `latest`. Konfiguration per Env-Vars (`HANNAH_WEBUI_HOST`/`PORT`/`SECRET_KEY`/`GRPC_HOST`/`GRPC_PORT`) statt `config.yaml`.
