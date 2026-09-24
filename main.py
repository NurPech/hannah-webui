"""hannah-webui – entry point.

Flask app for the standalone Hannah WebUI service. Talks to Hannah Core
exclusively via gRPC (no direct DB/file access, see #27).

Usage:
  python main.py [--config path/to/config.yaml]
"""
from __future__ import annotations

import argparse
import logging

from hannah_webui import log_shipping
from hannah_webui.app import create_app
from hannah_webui.config import load as load_config
from hannah_webui.grpc_client import HannahClient
from hannah_webui.tls import ensure_self_signed_certificate

log = logging.getLogger("hannah_webui")


def main(config_path: str) -> None:
    cfg = load_config(config_path)
    # Logging + log shipping (buffers from here, ships once Hannah announces a collector).
    shipping = log_shipping.setup(cfg)

    hannah = HannahClient(cfg.grpc.host, cfg.grpc.port)
    hannah.connect()

    app = create_app(
        hannah, cfg.secret_key, cfg.telegram_bot_token, cfg.telegram_bot_username,
        cfg.entra_client_id, cfg.entra_client_secret, cfg.entra_tenant,
        log_shipping=shipping,
    )

    ssl_context = None
    if cfg.tls.enabled:
        ensure_self_signed_certificate(cfg.tls.cert_file, cfg.tls.key_file)
        ssl_context = (cfg.tls.cert_file, cfg.tls.key_file)

    log.info(
        "hannah-webui starting on %s:%d (gRPC=%s:%d, tls=%s)",
        cfg.host, cfg.port, cfg.grpc.host, cfg.grpc.port, cfg.tls.enabled,
    )
    try:
        app.run(host=cfg.host, port=cfg.port, ssl_context=ssl_context)
    finally:
        hannah.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hannah WebUI")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()
    main(args.config)
