"""Shared app-level state for the blueprints in hannah_webui/blueprints/.

Blueprint modules are defined at import time, before create_app() runs — they
can't close over the HannahClient instance or config the way the old
monolithic app.py did. Instead they fetch everything through Flask's
current_app proxy at request time, which avoids circular imports between
app.py (which imports every blueprint to register it) and the blueprints
(which only import from here, never from app.py).
"""
from functools import wraps

from flask import current_app, flash, redirect, session, url_for

from hannah_webui.grpc_client import HannahClient

TRUST_LEVELS = {
    "list_rooms": 3,
    "list_groups": 10,
    "create_group": 10,
    "edit_group": 10,
    "delete_group": 10,
    "list_satellites": 5,
    "set_satellite_room": 5,
    "set_satellite_name": 5,
    "delete_satellite": 10,
    "set_satellite_owner": 10,
    "trigger_firmware_update": 10,
    "list_settings": 10,
    "edit_setting": 10,
    "list_ble_tags": 10,
    "create_ble_tag": 10,
    "edit_ble_tag": 10,
    "delete_ble_tag": 10,
    "list_cars": 10,
    "create_car": 10,
    "edit_car": 10,
    "delete_car": 10,
    "list_triggers": 5,
    "create_trigger": 7,
    "edit_trigger": 7,
    "delete_trigger": 7,
    "list_users": 10,
    "create_user": 10,
    "edit_user": 10,
    "delete_user": 10,
    "link_resident": 10,
}


def get_hannah() -> HannahClient:
    return current_app.extensions["hannah"]


def get_telegram_config() -> tuple[str, str]:
    return current_app.config.get("TELEGRAM_BOT_TOKEN", ""), current_app.config.get("TELEGRAM_BOT_USERNAME", "")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def trust_level_required(min_level: int):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("trust_level", 0) < min_level:
                flash("Zugriff verweigert: unzureichende Berechtigungen.", "danger")
                return redirect(url_for("me.me"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
