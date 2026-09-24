"""Shared app-level state for the blueprints in hannah_webui/blueprints/.

Blueprint modules are defined at import time, before create_app() runs — they
can't close over the HannahClient instance or config the way the old
monolithic app.py did. Instead they fetch everything through Flask's
current_app proxy at request time, which avoids circular imports between
app.py (which imports every blueprint to register it) and the blueprints
(which only import from here, never from app.py).
"""
from functools import wraps

import msal
from flask import current_app, flash, redirect, session, url_for

from hannah_webui.grpc_client import HannahClient
from hannah_webui.log_collector import LogCollectorClient

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
    "set_satellite_followup": 5,
    "enroll_other_voice": 10,
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
    "edit_presence_sources": 10,
    "list_activity_log": 0,
    "filter_activity_log": 10,
    "list_messages": 0,
    "export_logs": 10,
}


def get_hannah() -> HannahClient:
    return current_app.extensions["hannah"]


def get_telegram_config() -> tuple[str, str]:
    return current_app.config.get("TELEGRAM_BOT_TOKEN", ""), current_app.config.get("TELEGRAM_BOT_USERNAME", "")


def get_entra_tenant() -> str:
    return current_app.config.get("ENTRA_TENANT", "")


def get_entra_app():
    """MSAL-Client für die Entra-Verknüpfung in /me, oder None wenn nicht konfiguriert.
    Lazy gebaut und in app.extensions gecacht — der Konstruktor holt die OIDC-Discovery
    von login.microsoftonline.com, das soll weder beim App-Start noch pro Request passieren.
    Tests hängen hier ein Fake ein (app.extensions["entra_msal"])."""
    if "entra_msal" not in current_app.extensions:
        client_id = current_app.config.get("ENTRA_CLIENT_ID", "")
        client_secret = current_app.config.get("ENTRA_CLIENT_SECRET", "")
        tenant = get_entra_tenant()
        if not (client_id and client_secret and tenant):
            return None
        current_app.extensions["entra_msal"] = msal.ConfidentialClientApplication(
            client_id, client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant}",
        )
    return current_app.extensions["entra_msal"]


def entra_configured() -> bool:
    return "entra_msal" in current_app.extensions or all(
        current_app.config.get(k) for k in ("ENTRA_CLIENT_ID", "ENTRA_CLIENT_SECRET", "ENTRA_TENANT")
    )


def get_log_collector() -> LogCollectorClient | None:
    """Client für den aktuell von Hannah Core gemeldeten Log-Collector, oder None solange
    keiner bekannt ist. Die Adresse kommt aus der Discovery des Log-Shippings
    (app.extensions["log_shipping"]), neu pro Aufruf — der Collector kann umziehen.
    Aufrufer schließen den Client selbst. Tests hängen hier ein Fake ein
    (app.extensions["log_collector"])."""
    if "log_collector" in current_app.extensions:
        return current_app.extensions["log_collector"]
    address = _log_collector_address()
    return LogCollectorClient(address) if address else None


def log_collector_available() -> bool:
    """Ob gerade ein Log-Collector bekannt ist — ohne Channel-Aufbau, für die Nav in base.html."""
    return "log_collector" in current_app.extensions or bool(_log_collector_address())


def _log_collector_address() -> str | None:
    shipping = current_app.extensions.get("log_shipping")
    return shipping.collector_address if shipping is not None else None


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
