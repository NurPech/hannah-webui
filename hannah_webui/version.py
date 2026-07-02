"""Reads the CI-stamped VERSION file. Written by the `container-build`/`upload`
CI jobs (see .gitlab-ci.yml) next to main.py/wsgi.py — present in both deploy
layouts (Docker's /app, the systemd tarball's /opt/hannah/webui) but not in a
local dev checkout, where get_version() falls back to "dev"."""
from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


def get_version() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except FileNotFoundError:
        return "dev"
