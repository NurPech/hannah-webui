"""
Hannah WebUI

Flask app, talks to Hannah Core exclusively via gRPC (no direct DB/file access —
Core stays the sole owner of all data, see #27).
"""
import logging
import os

import grpc
from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException

from hannah_webui.blueprints import (
    auth,
    ble_tags,
    cars,
    groups,
    me,
    rooms,
    satellites,
    settings,
    triggers,
    users,
)
from hannah_webui.extensions import TRUST_LEVELS
from hannah_webui.grpc_client import HannahClient
from hannah_webui.version import get_version

log = logging.getLogger(__name__)

_TEMPLATES = os.path.join(os.path.dirname(__file__), "templates")


def create_app(hannah: HannahClient, secret_key: str = "", telegram_bot_token: str = "", telegram_bot_username: str = "") -> Flask:
    app = Flask(__name__, template_folder=_TEMPLATES)
    if not secret_key:
        log.warning(
            "No secret_key configured — falling back to a random one. Sessions won't "
            "survive a restart or work across multiple gunicorn workers."
        )
        secret_key = os.urandom(24)
    app.secret_key = secret_key
    # Error handlers below must run even with TESTING=True (used by the test suite's
    # fixtures) — otherwise Flask re-raises instead of rendering error.html.
    app.config["PROPAGATE_EXCEPTIONS"] = False

    app.extensions["hannah"] = hannah
    app.config["TELEGRAM_BOT_TOKEN"] = telegram_bot_token
    app.config["TELEGRAM_BOT_USERNAME"] = telegram_bot_username

    app_version = get_version()

    @app.context_processor
    def inject_trust_levels():
        return {"trust_levels": TRUST_LEVELS, "app_version": app_version}

    @app.route("/version")
    def version():
        return jsonify({"version": app_version})

    @app.errorhandler(grpc.RpcError)
    def handle_grpc_error(error):
        log.error("gRPC error: %s", error)
        return render_template(
            "error.html", title="Hannah Core nicht erreichbar",
            message="Hannah Core antwortet gerade nicht. Bitte versuche es in Kürze erneut.",
        ), 503

    @app.errorhandler(404)
    def handle_not_found(error):
        return render_template(
            "error.html", title="Seite nicht gefunden",
            message="Diese Seite gibt es nicht (mehr).",
        ), 404

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Other HTTPExceptions (405, 400, …) already render sensibly via Werkzeug —
        # only truly unexpected exceptions get the generic error page.
        if isinstance(error, HTTPException):
            return error
        log.exception("Unhandled error: %s", error)
        return render_template(
            "error.html", title="Unerwarteter Fehler",
            message="Da ist etwas schiefgelaufen. Bitte versuche es erneut.",
        ), 500

    for blueprint_module in (auth, me, rooms, groups, satellites, settings, ble_tags, cars, triggers, users):
        app.register_blueprint(blueprint_module.bp)

    return app
