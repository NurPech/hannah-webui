"""No-Code-Parsing/Formatting-Helfer für die Blueprints — reine Funktionen ohne
Abhängigkeit auf den Flask-App-Kontext, deshalb als eigenes Modul statt in
extensions.py (das ist für app-gebundenen State)."""
import hashlib
import hmac
import json
import re
import time

from hannah_proto import hannah_pb2

_TELEGRAM_AUTH_MAX_AGE = 300  # Sekunden, gegen Replay alter Callback-URLs

_STATE_TYPE_WIDGET = {
    hannah_pb2.BOOLEAN: "boolean",
    hannah_pb2.NUMERIC: "numeric",
    hannah_pb2.ENUM: "enum",
    hannah_pb2.COLOR: "enum",  # gleiche Widget-Logik wie ENUM: Dropdown aus den erlaubten Werten
}

_SETTINGS_NEW_ROWS = 2
_USER_TYPES = ("roomie", "guest", "pet")
_WEEKDAY_NAMES = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

_TRIGGER_NEW_WHEN_ROWS = 2
_TRIGGER_NEW_ALSO_ROWS = 2
_TRIGGER_NEW_ACTION_ROWS = 2
_CMP_KEYS = ("value", "above", "below")


def _slugify(s: str) -> str:
    """Einfacher Slug: Kleinbuchstaben, Leerzeichen -> Bindestrich, Sonderzeichen entfernen."""
    s = s.lower().strip()
    s = re.sub(r"[äöü]", lambda m: {"ä": "ae", "ö": "oe", "ü": "ue"}[m.group()], s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Verifiziert die Signatur eines Telegram-Login-Widget-Callbacks.
    https://core.telegram.org/widgets/login#checking-authorization"""
    received_hash = data.get("hash", "")
    if not received_hash or not bot_token:
        return False
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if k != "hash")
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        return False
    auth_date = int(data.get("auth_date", 0))
    return time.time() - auth_date < _TELEGRAM_AUTH_MAX_AGE


def _as_or_list(when) -> list[dict]:
    """Normalisiert 'when' auf eine Liste von Bedingungs-Dicts — Pendant zu
    TriggerEngine._as_or_list() (core/hannah/trigger_engine.py), hier ohne Core-Import
    nachgebaut, da webui/ ausschließlich über gRPC mit Core spricht (#101)."""
    if isinstance(when, list):
        return when
    return [when] if when else []


def _as_condition_list(also_or_unless) -> tuple[list[dict], str]:
    """Liest 'also'/'unless' (Dict, Liste, oder {"op",  "conditions"}) auf eine
    einheitliche (Bedingungsliste, op)-Form zurück, fürs Vorausfüllen des Formulars."""
    if not also_or_unless:
        return [], "and"
    if isinstance(also_or_unless, dict) and "conditions" in also_or_unless:
        return list(also_or_unless.get("conditions") or []), also_or_unless.get("op", "and")
    if isinstance(also_or_unless, list):
        return also_or_unless, "and"
    return [also_or_unless], "and"


def _device_state_options(rooms, writable_only: bool = False) -> list[dict]:
    """Flacht GetDevices() (RoomInfo -> DeviceInfo) zu einer Liste von Dropdown-Optionen
    fürs Trigger-Editor-Zustands-Widget ab (#16). Der Options-'value' ist die volle
    ioBroker-State-ID (device.id + '.' + state-key) — exakt das Format, das das
    Freitext-Feld schon immer erwartet hat, damit alte/manuell eingetragene States
    unverändert weiter funktionieren.

    writable_only blendet nicht beschreibbare States aus (z.B. Fenster-/Tür-/Temperatur-
    Sensoren) — fürs Aktions-Dropdown ("Dann"), da dort nur Geräte gesetzt werden können.
    Fehlt ein State in state_writable (ältere Core-Version ohne das Feld), gilt er als
    schreibbar, damit die Auswahl nicht grundlos leerläuft."""
    options = []
    for room in rooms:
        for device in room.devices:
            for state_key in device.states:
                if writable_only and not device.state_writable.get(state_key, True):
                    continue
                state_type = device.state_types.get(state_key, hannah_pb2.STATE_TYPE_UNSPECIFIED)
                enum_values = (
                    dict(device.state_enum_values[state_key].values)
                    if state_key in device.state_enum_values else {}
                )
                options.append({
                    "value": f"{device.id}.{state_key}",
                    "room": room.name,
                    "device": device.name,
                    "state": state_key,
                    "widget": _STATE_TYPE_WIDGET.get(state_type, "text"),
                    "enum_values": enum_values,
                })
    return options


def _blank_when_row() -> dict:
    return {"type": "state", "state": "", "cmp": "value", "value": "", "time": "", "days": "", "phrase": ""}


def _blank_state_row() -> dict:
    return {"state": "", "cmp": "value", "value": ""}


def _blank_action_row() -> dict:
    return {"type": "say", "say": "", "room": "", "state_id": "", "state_value": ""}


def _condition_to_row(cond: dict) -> dict:
    if "time" in cond:
        return {"type": "time", "state": "", "cmp": "value", "value": "",
                "time": cond.get("time", ""), "days": ",".join(cond.get("days") or []), "phrase": ""}
    if "phrase" in cond:
        return {"type": "phrase", "state": "", "cmp": "value", "value": "",
                "time": "", "days": "", "phrase": cond.get("phrase", "")}
    cmp = next((k for k in _CMP_KEYS if k in cond), "value")
    return {"type": "state", "state": cond.get("state", ""), "cmp": cmp,
            "value": str(cond.get(cmp, "")), "time": "", "days": "", "phrase": ""}


def _state_condition_to_row(cond: dict) -> dict:
    cmp = next((k for k in _CMP_KEYS if k in cond), "value")
    return {"state": cond.get("state", ""), "cmp": cmp, "value": str(cond.get(cmp, ""))}


def _action_to_row(action: dict) -> dict:
    if "set_state" in action:
        set_state = action.get("set_state") or {}
        return {"type": "state", "say": "", "room": "", "state_id": set_state.get("id", ""),
                "state_value": str(set_state.get("value", ""))}
    return {"type": "say", "say": action.get("say", ""), "room": action.get("room", ""),
            "state_id": "", "state_value": ""}


def _extract_also_unless(conditions: list[dict]) -> tuple[list[dict], str, list[dict]]:
    """Liest aus den (ggf. auf jede Wenn-Bedingung dupliziert abgelegten) also/unless die
    gemeinsame 'und'/'außer wenn'-Konfiguration zurück — Inverse von _attach_also_unless(),
    fürs Vorausfüllen des Bearbeiten-Formulars. Nimmt die erste Bedingung, die jeweils
    etwas trägt (sie sind laut _attach_also_unless ohnehin identisch)."""
    also_conditions, also_op, unless_conditions = [], "and", []
    for cond in conditions:
        if not also_conditions and cond.get("also"):
            also_conditions, also_op = _as_condition_list(cond["also"])
        if not unless_conditions and cond.get("unless"):
            unless_conditions, _ = _as_condition_list(cond["unless"])
    return also_conditions, also_op, unless_conditions


def _parse_when_rows(form) -> list[dict]:
    """No-Code 'Wenn'-Zeilen (OR-verknüpft): pro Zeile per Typ-Auswahl ein Zustand
    (State + Vergleich + Wert), eine Uhrzeit (HH:MM + optionale, kommagetrennte Wochentage)
    oder eine Sprachphrase (Substring-Match, ersetzt seit #28/hannah#139 die frühere
    separate Routinen-Verwaltung). Genutzt für "wenn" (#101)."""
    types = form.getlist("when_type")
    states = form.getlist("when_state")
    cmps = form.getlist("when_cmp")
    values = form.getlist("when_value")
    times = form.getlist("when_time")
    days = form.getlist("when_days")
    phrases = form.getlist("when_phrase")
    conditions = []
    for i, row_type in enumerate(types):
        if row_type == "time":
            time_str = times[i].strip() if i < len(times) else ""
            if not time_str:
                continue
            cond = {"time": time_str}
            days_str = days[i].strip() if i < len(days) else ""
            if days_str:
                cond["days"] = [d.strip().lower() for d in days_str.split(",") if d.strip()]
            conditions.append(cond)
        elif row_type == "phrase":
            phrase = phrases[i].strip() if i < len(phrases) else ""
            if not phrase:
                continue
            conditions.append({"phrase": phrase})
        else:
            state_id = states[i].strip() if i < len(states) else ""
            if not state_id:
                continue
            cmp = cmps[i].strip() if i < len(cmps) else "value"
            if cmp not in _CMP_KEYS:
                cmp = "value"
            value = values[i].strip() if i < len(values) else ""
            conditions.append({"state": state_id, cmp: value or "true"})
    return conditions


def _parse_state_condition_rows(form, prefix: str) -> list[dict]:
    """No-Code-Zustandsbedingungen (kein Uhrzeit-Typ) — gemeinsamer Zeilen-Builder für
    "und" und "außer wenn" (#101)."""
    states = form.getlist(f"{prefix}_state")
    cmps = form.getlist(f"{prefix}_cmp")
    values = form.getlist(f"{prefix}_value")
    conditions = []
    for i, raw_state in enumerate(states):
        state_id = raw_state.strip()
        if not state_id:
            continue
        cmp = cmps[i].strip() if i < len(cmps) else "value"
        if cmp not in _CMP_KEYS:
            cmp = "value"
        value = values[i].strip() if i < len(values) else ""
        conditions.append({"state": state_id, cmp: value or "true"})
    return conditions


def _parse_also(form) -> dict | list | None:
    conditions = _parse_state_condition_rows(form, "also")
    if not conditions:
        return None
    if form.get("also_op") == "or":
        return {"op": "or", "conditions": conditions}
    return conditions


def _attach_also_unless(conditions: list[dict], also, unless) -> list[dict]:
    """Hängt 'und'/'außer wenn' an jede Wenn-Bedingung — die Engine prüft sie pro
    OR-Branch (trigger_engine.py), die No-Code-UI bildet aber EINEN globalen 'und'/
    'außer wenn'-Block ab, der für alle 'wenn'-Zeilen gelten soll. 'und' gilt nur für
    Zustands-, nicht für Uhrzeit-Bedingungen (die Engine prüft 'also' nie bei
    Zeit-Triggern, siehe _check_time_triggers())."""
    result = []
    for cond in conditions:
        cond = dict(cond)
        if unless:
            cond["unless"] = unless
        if also and "state" in cond:
            cond["also"] = also
        result.append(cond)
    return result


def _parse_trigger_action_rows(form) -> list[dict]:
    """Wie _parse_action_rows, aber die Geräte-Variante setzt einen ioBroker-State direkt
    (set_state) statt ein MQTT-Topic zu publishen (#101)."""
    types = form.getlist("action_type")
    says = form.getlist("action_say")
    rooms = form.getlist("action_room")
    state_ids = form.getlist("action_state_id")
    state_values = form.getlist("action_state_value")
    actions = []
    for i, action_type in enumerate(types):
        if action_type == "say":
            say = says[i].strip() if i < len(says) else ""
            if say:
                room = rooms[i].strip() if i < len(rooms) else ""
                actions.append({"say": say, "room": room or "all"})
        else:
            state_id = state_ids[i].strip() if i < len(state_ids) else ""
            if state_id:
                value = state_values[i].strip() if i < len(state_values) else ""
                actions.append({"set_state": {"id": state_id, "value": value or "true"}})
    return actions


def _prepare_setting_row(s) -> dict:
    """Leitet den No-Code-Render-Typ aus der Form des JSON-decodierten Werts ab, ohne dass
    Core einen Typ mitschicken muss: ein String wird zum Text-Editor, eine Liste von Strings
    zum Zeilen-Builder, ein Objekt mit String-Values zum Key-Value-Grid. Alles andere
    (verschachtelt, gemischte Typen) fällt auf das rohe JSON-Textarea zurück."""
    try:
        parsed = json.loads(s.value)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    if isinstance(parsed, str):
        return {"setting": s, "value_type": "text", "text_value": parsed}

    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
        return {"setting": s, "value_type": "list", "list_rows": parsed + [""] * _SETTINGS_NEW_ROWS}

    if isinstance(parsed, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()):
        rows = list(parsed.items()) + [("", "")] * _SETTINGS_NEW_ROWS
        return {"setting": s, "value_type": "keyvalue", "kv_rows": rows}

    pretty_value = s.value
    try:
        pretty_value = json.dumps(json.loads(s.value), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pass
    return {"setting": s, "value_type": "json", "pretty_value": pretty_value}
