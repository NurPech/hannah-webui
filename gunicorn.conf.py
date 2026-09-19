import os

from hannah_webui.config import load as load_config
from hannah_webui.tls import ensure_self_signed_certificate

bind         = "0.0.0.0:5000"
workers      = 2
timeout      = 60
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
