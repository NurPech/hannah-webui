"""Launch hannah-webui against FakeHannahClient — no real Hannah Core needed.

Run from anywhere:
    venv/Scripts/python .claude/skills/run-hannah-webui/serve_fake.py [--host 127.0.0.1] [--port 5099]

Prints "READY on http://<host>:<port>" once the Flask dev server is listening.
Logins: admin/admin (trust_level 10, sees every page) or claude/claude (trust_level 7).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from hannah_webui.app import create_app  # noqa: E402
from tests.fake_hannah_client import FakeHannahClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5099)
    args = parser.parse_args()

    hannah = FakeHannahClient()
    app = create_app(hannah, secret_key="driver-dev-secret-not-for-prod")

    print(f"READY on http://{args.host}:{args.port}", flush=True)
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
