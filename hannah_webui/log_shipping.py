"""WebUI-Logs zusätzlich an den Log-Collector senden, über die Lib hannah-logging.

Die bestehende Ausgabe (stdout/journald) bleibt unverändert. Die Lib puffert ab install()
und schickt, sobald Hannah Core einen Collector meldet (Discovery über die gRPC-Adresse
aus der Config).

Die WebUI loggt nur Technisches (TLS, gRPC, Fehler) ohne Personenbezug, deshalb gibt es
keine METADATA-/TRANSCRIPT-Zuordnung — alles läuft als GENERAL.
"""
from __future__ import annotations

import dataclasses
import logging
import re
import sys
from typing import Any, Iterator

import hannah_logging

from hannah_webui.version import get_version

# Config-Schlüssel, deren Wert ein Secret ist. Der Name muss auf eines dieser Wörter enden.
_SECRET_KEY = re.compile(r"(password|passwd|secret|secret_key|api_key|azure_key|access_key|token|psk)$", re.I)


def setup(cfg: Any) -> hannah_logging.LogShipping:
    """Logging-Grundkonfiguration plus Log-Shipping. Einziger Einstieg für beide Startwege:
    wsgi.py (gunicorn, Produktion) und main.py (Flask-Dev-Server)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    version = get_version()
    shipping = install(version, hannah_address=f"{cfg.grpc.host}:{cfg.grpc.port}", cfg=cfg)
    logging.getLogger("hannah_webui").info("hannah-webui %s starting", version)
    return shipping


def install(version: str, *, hannah_address: str | None = None, cfg: Any = None) -> hannah_logging.LogShipping:
    """Hängt den Handler an den Root-Logger und aktiviert, falls `hannah_address` gesetzt
    ist, die Discovery über Hannah Core."""
    return hannah_logging.install(
        component="webui",
        version=version,
        hannah_address=hannah_address or None,
        secrets=list(config_secrets(cfg)) if cfg is not None else [],
    )


def config_secrets(cfg: Any) -> Iterator[str]:
    """Alle Secret-Werte aus der Config (Dataclasses, Dicts, Listen, verschachtelt)."""
    if dataclasses.is_dataclass(cfg) and not isinstance(cfg, type):
        cfg = {field.name: getattr(cfg, field.name) for field in dataclasses.fields(cfg)}
    if isinstance(cfg, dict):
        for key, value in cfg.items():
            if isinstance(value, str) and _SECRET_KEY.search(str(key)):
                if value:
                    yield value
            else:
                yield from config_secrets(value)
    elif isinstance(cfg, (list, tuple)):
        for item in cfg:
            yield from config_secrets(item)
