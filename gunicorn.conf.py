import os

from hannah_webui.config import load as load_config
from hannah_webui.tls import ensure_self_signed_certificate

bind         = "0.0.0.0:5000"
workers      = 2
# gthread instead of the default sync worker: with sync, one stalled connection
# (e.g. a client that opens a TLS socket and never sends a request) blocks an
# entire worker until `timeout` hits and the master SIGKILLs it (#72).
worker_class = "gthread"
threads      = 4
timeout      = 60
# gunicorn >= 25.1 creates a control socket under $HOME/.gunicorn/ by default;
# the container user has no home directory (Permission denied at startup) and
# nothing uses gunicornc here (#72).
control_socket_disable = True
accesslog    = "-"
errorlog     = "-"
loglevel     = "info"

# TLS (#61) — gunicorn binds the socket here, before wsgi.py imports the app,
# so this is the only place that can pass certfile/keyfile to it.
_cfg = load_config(os.environ.get("HANNAH_WEBUI_CONFIG", "config.yaml"))
if _cfg.tls.enabled:
    ensure_self_signed_certificate(_cfg.tls.cert_file, _cfg.tls.key_file)
    certfile = _cfg.tls.cert_file
    keyfile = _cfg.tls.key_file


def on_starting(server):
    # Make the effective TLS state visible in the log — "[SSL: HTTP_REQUEST]"
    # warnings otherwise leave no hint whether TLS was actually switched on, or
    # from where (env var vs. a config.yaml that overrides the env, #73).
    server.log.info(
        "hannah-webui TLS: %s (HANNAH_WEBUI_TLS_ENABLED=%r, config file %s)",
        "ENABLED" if _cfg.tls.enabled else "disabled",
        os.environ.get("HANNAH_WEBUI_TLS_ENABLED"),
        "present" if os.path.exists(os.environ.get("HANNAH_WEBUI_CONFIG", "config.yaml")) else "absent",
    )
