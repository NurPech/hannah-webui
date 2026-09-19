"""Configuration loader for hannah-webui."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GrpcConfig:
    host: str = "127.0.0.1"
    port: int = 50051


@dataclass
class TlsConfig:
    enabled: bool = False
    # Leer = selbstsigniertes Zertifikat wird beim ersten Start generiert und
    # unter diesem Pfad persistiert (nie neu erzeugt, solange die Datei existiert
    # — siehe #61). Explizit gesetzt = eigenes Cert/Key wird verwendet.
    cert_file: str = ""
    key_file: str = ""


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 5000
    secret_key: str = ""
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    grpc: GrpcConfig = field(default_factory=GrpcConfig)
    tls: TlsConfig = field(default_factory=TlsConfig)


def _load_from_env() -> Config:
    """No config.yaml on disk — read from env vars instead (12-factor style,
    for a future containerized deployment)."""
    return Config(
        host=os.environ.get("HANNAH_WEBUI_HOST", "127.0.0.1"),
        port=int(os.environ.get("HANNAH_WEBUI_PORT", "5000")),
        secret_key=os.environ.get("HANNAH_WEBUI_SECRET_KEY", ""),
        telegram_bot_token=os.environ.get("HANNAH_WEBUI_TELEGRAM_BOT_TOKEN", ""),
        telegram_bot_username=os.environ.get("HANNAH_WEBUI_TELEGRAM_BOT_USERNAME", ""),
        grpc=GrpcConfig(
            host=os.environ.get("HANNAH_WEBUI_GRPC_HOST", "127.0.0.1"),
            port=int(os.environ.get("HANNAH_WEBUI_GRPC_PORT", "50051")),
        ),
        tls=TlsConfig(
            enabled=_env_flag("HANNAH_WEBUI_TLS_ENABLED"),
            # /data ist das im Dockerfile deklarierte Volume — der einzige Pfad im
            # Image, der einen Container-Neustart übersteht.
            cert_file=os.environ.get("HANNAH_WEBUI_TLS_CERT_FILE", "") or "/data/tls/cert.pem",
            key_file=os.environ.get("HANNAH_WEBUI_TLS_KEY_FILE", "") or "/data/tls/key.pem",
        ),
    )


def load(path: str | Path = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        return _load_from_env()

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    def _section(cls, key: str):
        data = raw.get(key, {}) or {}
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in fields})

    tls = _section(TlsConfig, "tls")
    if not tls.cert_file:
        # /var/lib/hannah-webui persistiert über AutoDeploy-Updates hinweg (die den
        # Code unter /opt/hannah/webui austauschen) und über /etc/hannah-webui hinaus
        # (das im systemd-Unit read-only ist) — siehe #61.
        tls.cert_file = "/var/lib/hannah-webui/tls/cert.pem"
    if not tls.key_file:
        tls.key_file = "/var/lib/hannah-webui/tls/key.pem"

    return Config(
        host=raw.get("host", "127.0.0.1"),
        port=raw.get("port", 5000),
        secret_key=raw.get("secret_key", ""),
        telegram_bot_token=raw.get("telegram_bot_token", ""),
        telegram_bot_username=raw.get("telegram_bot_username", ""),
        grpc=_section(GrpcConfig, "grpc"),
        tls=tls,
    )
