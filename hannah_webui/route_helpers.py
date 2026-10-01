"""No-Code-Parsing/Formatting-Helfer für die Blueprints — reine Funktionen ohne
Abhängigkeit auf den Flask-App-Kontext, deshalb als eigenes Modul statt in
extensions.py (das ist für app-gebundenen State)."""
import hashlib
import hmac
import json
import re
import time

from hannah_proto.v2 import hannah_pb2

_TELEGRAM_AUTH_MAX_AGE = 300  # Sekunden, gegen Replay alter Callback-URLs

K = hannah_pb2.SlotKind
C = hannah_pb2.DeviceClass

# Slot-Art -> Widget im Trigger-Editor (Wertfeld der Bedingung/Aktion). Alles Numerische ist
# "numeric", Text und Farbe bleiben Freitext; MODE/FAN_SPEED werden nur mit Slot.options "enum".
_BOOLEAN_KINDS = {K.SLOT_KIND_ON, K.SLOT_KIND_OPEN, K.SLOT_KIND_MOTION, K.SLOT_KIND_STOP, K.SLOT_KIND_GENERIC_BOOL}
_ENUM_KINDS = {K.SLOT_KIND_MODE, K.SLOT_KIND_FAN_SPEED}
_TEXT_KINDS = {K.SLOT_KIND_COLOR, K.SLOT_KIND_GENERIC_TEXT, K.SLOT_KIND_UNSPECIFIED}

_SLOT_KIND_LABELS = {
    K.SLOT_KIND_ON: "An/Aus",
    K.SLOT_KIND_BRIGHTNESS: "Helligkeit",
    K.SLOT_KIND_COLOR: "Farbe",
    K.SLOT_KIND_COLOR_TEMPERATURE: "Farbtemperatur",
    K.SLOT_KIND_POWER: "Leistung",
    K.SLOT_KIND_ENERGY: "Energie",
    K.SLOT_KIND_VOLTAGE: "Spannung",
    K.SLOT_KIND_CURRENT: "Strom",
    K.SLOT_KIND_TARGET_TEMPERATURE: "Solltemperatur",
    K.SLOT_KIND_TEMPERATURE: "Temperatur",
    K.SLOT_KIND_HUMIDITY: "Luftfeuchtigkeit",
    K.SLOT_KIND_VALVE: "Ventil",
    K.SLOT_KIND_MODE: "Modus",
    K.SLOT_KIND_FAN_SPEED: "Lüfterstufe",
    K.SLOT_KIND_POSITION: "Position",
    K.SLOT_KIND_TILT: "Neigung",
    K.SLOT_KIND_STOP: "Stopp",
    K.SLOT_KIND_OPEN: "Offen",
    K.SLOT_KIND_MOTION: "Bewegung",
    K.SLOT_KIND_ILLUMINANCE: "Helligkeit (Sensor)",
    K.SLOT_KIND_PRESSURE: "Luftdruck",
    K.SLOT_KIND_CO2: "CO₂",
    K.SLOT_KIND_IAQ: "Luftqualität",
    K.SLOT_KIND_VOC: "VOC",
    K.SLOT_KIND_GENERIC_NUMBER: "Zahl",
    K.SLOT_KIND_GENERIC_BOOL: "Ja/Nein",
    K.SLOT_KIND_GENERIC_TEXT: "Text",
    K.SLOT_KIND_UNSPECIFIED: "?",
}

_DEVICE_CLASS_LABELS = {
    C.DEVICE_CLASS_LIGHT: "Licht",
    C.DEVICE_CLASS_SOCKET: "Steckdose",
    C.DEVICE_CLASS_GENERIC_BINARY_SWITCH: "Schalter",
    C.DEVICE_CLASS_THERMOSTAT: "Thermostat",
    C.DEVICE_CLASS_COVER: "Rollladen/Jalousie",
    C.DEVICE_CLASS_SENSOR: "Sensor",
    C.DEVICE_CLASS_CONTACT: "Kontakt",
    C.DEVICE_CLASS_GENERIC: "Sonstiges",
    C.DEVICE_CLASS_CLIMATE: "Klimagerät",
    C.DEVICE_CLASS_UNSPECIFIED: "?",
}

_DEVICE_SUBTYPE_LABELS = {
    hannah_pb2.DEVICE_SUBTYPE_WINDOW: "Fenster",
    hannah_pb2.DEVICE_SUBTYPE_DOOR: "Tür",
}

_SETTINGS_NEW_ROWS = 2
_USER_TYPES = ("roomie", "guest", "pet")
_PRESENCE_STATES = (("home", "Zuhause"), ("away", "Abwesend"), ("asleep", "Schläft"), ("awake", "Wach"))
_WEEKDAY_NAMES = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

_TRIGGER_NEW_WHEN_ROWS = 2
_TRIGGER_NEW_ALSO_ROWS = 2
_TRIGGER_NEW_ACTION_ROWS = 2
_CMP_KEYS = ("value", "above", "below")

_PRESENCE_SOURCE_TYPES = (("iobroker_state", "ioBroker-State"), ("ble_tag", "BLE-Tag"))
_PRESENCE_SOURCE_NEW_ROWS = 2

_ACTIVITY_LOG_PAGE_SIZE = 30
_ACTIVITY_LOG_CHANNEL_LABELS = {
    "telegram": "Telegram",
    "iobroker": "ioBroker",
    "grpc_text": "gRPC (Text)",
    "grpc_voice": "gRPC (Voice)",
}


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


def _slot_widget(slot) -> str:
    if slot.kind in _BOOLEAN_KINDS:
        return "boolean"
    if slot.kind in _ENUM_KINDS and slot.options:
        return "enum"
    if slot.kind in _TEXT_KINDS or slot.kind in _ENUM_KINDS:
        return "text"
    return "numeric"


def _slot_label(slot) -> str:
    """Name eines Slots für Menschen: bei Standard-Arten die deutsche Bezeichnung, bei
    generischen Slots deren Label (sonst die Slot-ID)."""
    if slot.kind in (K.SLOT_KIND_GENERIC_NUMBER, K.SLOT_KIND_GENERIC_BOOL, K.SLOT_KIND_GENERIC_TEXT):
        return slot.label or slot.slot_id
    return _SLOT_KIND_LABELS.get(slot.kind, slot.slot_id)


def _slot_value_text(slot) -> str:
    if not slot.HasField("value"):
        return ""
    which = slot.value.WhichOneof("value")
    if which == "boolean":
        return "true" if slot.value.boolean else "false"
    if which == "number":
        number = slot.value.number
        return str(int(number)) if number == int(number) else str(number)
    if which == "rgb":
        return f"#{slot.value.rgb & 0xFFFFFF:06X}"
    if which == "text":
        return slot.value.text
    return ""


def _device_category_label(device) -> str:
    label = _DEVICE_CLASS_LABELS.get(device.device_class, "?")
    subtype = _DEVICE_SUBTYPE_LABELS.get(device.subtype)
    return f"{label} ({subtype})" if subtype else label


def _device_state_options(rooms, writable_only: bool = False) -> list[dict]:
    """Flacht GetDevices() (RoomInfo -> DeviceInfo) zu einer Liste von Dropdown-Optionen
    fürs Trigger-Editor-Zustands-Widget ab (#16). Der Options-'value' ist der Bezeichner
    (Slot.identifier), den der Adapter für den Wert hinter dem Slot vergibt — bei ioBroker die
    volle State-ID, exakt das Format, das das Freitext-Feld schon immer erwartet hat, damit
    alte/manuell eingetragene States unverändert weiter funktionieren. Ein Slot ohne
    Bezeichner ist für Trigger nicht adressierbar und erscheint nicht (#71).

    writable_only blendet nicht beschreibbare Slots aus (z.B. Fenster-/Tür-/Temperatur-
    Sensoren) — fürs Aktions-Dropdown ("Dann"), da dort nur Geräte gesetzt werden können.

    Trigger vergleichen gegen den Rohwert des Adapters, nicht gegen den normalisierten
    Slot-Wert, den die Geräteübersicht zeigt."""
    options = []
    for room in rooms:
        for device in room.devices:
            for slot in device.slots:
                if not slot.identifier:
                    continue
                if writable_only and not slot.writable:
                    continue
                widget = _slot_widget(slot)
                options.append({
                    "value": slot.identifier,
                    "room": room.name,
                    "device": device.name,
                    "state": _slot_label(slot),
                    "widget": widget,
                    "enum_values": {o: o for o in slot.options} if widget == "enum" else {},
                })
    return options


def _device_overview_rooms(rooms) -> list[dict]:
    """Baut die Zeilen für die Device-Overview (#68): pro Raum -> Gerät -> Slots, so wie
    Hannah Core sie über GetDevices sieht (Debugging-Ansicht, rein lesend). Der Bezeichner pro
    Slot ist derselbe, den der Trigger-Editor als Zustand anbietet (_device_state_options)."""
    result = []
    for room in rooms:
        devices = []
        for device in room.devices:
            rows = []
            for slot in device.slots:
                rows.append({
                    "key": slot.slot_id,
                    "identifier": slot.identifier,
                    "type_label": _slot_label(slot),
                    "value": _slot_value_text(slot) + (f" {slot.unit}" if slot.unit and slot.HasField("value") else ""),
                    "writable": slot.writable,
                })
            devices.append({"device": device, "category": _device_category_label(device), "rows": rows})
        result.append({"room": room, "devices": devices})
    return result


def _blank_when_row() -> dict:
    return {"type": "state", "state": "", "cmp": "value", "value": "", "time": "", "days": "", "phrase": ""}


def _blank_state_row() -> dict:
    return {"state": "", "cmp": "value", "value": ""}


def _blank_action_row() -> dict:
    return {"type": "say", "say": "", "target": "", "state_id": "", "state_value": "",
            "roomie": "", "presence_state": ""}


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
        return {"type": "state", "say": "", "target": "", "state_id": set_state.get("id", ""),
                "state_value": str(set_state.get("value", "")), "roomie": "", "presence_state": ""}
    if "set_presence" in action:
        set_presence = action.get("set_presence") or {}
        return {"type": "presence", "say": "", "target": "", "state_id": "", "state_value": "",
                "roomie": set_presence.get("roomie", ""), "presence_state": set_presence.get("state", "")}
    return {"type": "say", "say": action.get("say", ""), "target": action.get("target", ""),
            "state_id": "", "state_value": "", "roomie": "", "presence_state": ""}


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
    'außer wenn'-Block ab, der für alle 'wenn'-Zeilen gelten soll. Gilt auch für
    Uhrzeit-Bedingungen: _check_time_triggers() wertet 'also' inzwischen ebenfalls
    aus, Zeit wirkt damit immer als zusätzliches AND-Gate."""
    result = []
    for cond in conditions:
        cond = dict(cond)
        if unless:
            cond["unless"] = unless
        if also:
            cond["also"] = also
        result.append(cond)
    return result


def _parse_trigger_action_rows(form) -> list[dict]:
    """Wie _parse_action_rows, aber die Geräte-Variante setzt einen ioBroker-State direkt
    (set_state) statt ein MQTT-Topic zu publishen (#101). set_presence (#54) setzt den
    Anwesenheits-Status eines Residents, ist keine gRPC-Erweiterung, sondern nur ein
    weiterer von Core interpretierter Action-Key."""
    types = form.getlist("action_type")
    says = form.getlist("action_say")
    targets = form.getlist("action_target")
    state_ids = form.getlist("action_state_id")
    state_values = form.getlist("action_state_value")
    roomies = form.getlist("action_roomie")
    presence_states = form.getlist("action_presence_state")
    actions = []
    for i, action_type in enumerate(types):
        if action_type == "say":
            say = says[i].strip() if i < len(says) else ""
            if say:
                target = targets[i].strip() if i < len(targets) else ""
                actions.append({"say": say, "target": target or "all"})
        elif action_type == "presence":
            roomie = roomies[i].strip() if i < len(roomies) else ""
            if roomie:
                state = presence_states[i].strip() if i < len(presence_states) else ""
                actions.append({"set_presence": {"roomie": roomie, "state": state or _PRESENCE_STATES[0][0]}})
        else:
            state_id = state_ids[i].strip() if i < len(state_ids) else ""
            if state_id:
                value = state_values[i].strip() if i < len(state_values) else ""
                actions.append({"set_state": {"id": state_id, "value": value or "true"}})
    return actions


def _blank_presence_source_row() -> dict:
    return {"id": "", "source_type": _PRESENCE_SOURCE_TYPES[0][0], "reference": "",
            "home_confidence": "0.8", "away_confidence": "0.8", "enabled": True}


def _presence_source_to_row(ps) -> dict:
    """round() rundet gegen die Präzisionsartefakte von Core's single-precision
    'float' (z.B. 0.9 -> 0.8999999761581421 auf dem Wire) — ungerundet verletzt der
    Wert das step="0.05" des Zahlenfelds, was die native Browser-Validierung beim
    Speichern lautlos blockiert, ohne dass der Request überhaupt abgeschickt wird."""
    return {"id": str(ps.id), "source_type": ps.source_type, "reference": ps.reference,
            "home_confidence": str(round(ps.home_confidence, 2)), "away_confidence": str(round(ps.away_confidence, 2)),
            "enabled": ps.enabled}


def _parse_presence_source_rows(form) -> list[dict]:
    """Zeilen-Builder für die Presence-Quellen eines Users (#59): eine leere Referenz
    markiert eine Zeile als unbenutzt (neue Blanko-Zeile) oder, falls sie eine 'id' trägt,
    als zu löschen — dieselbe Konvention wie bei den Trigger-Zeilen (leer = überspringen),
    ergänzt um die Löschen-Erkennung, weil Core hier (anders als bei Triggern) einzelne
    Zeilen per ID adressiert statt einen ganzen JSON-Blob zu ersetzen.

    Die Referenz kommt je nach Typ aus einem von zwei Feldern (ps_reference_text
    fürs Freitext-State-ID, ps_reference_ble fürs Dropdown über die BLE-Tags des
    Users aus der bestehenden BLE-Tag-Verwaltung) — beide werden unabhängig vom
    sichtbaren Feld immer mitgeschickt, das JS blendet nur die Anzeige um."""
    ids = form.getlist("ps_id")
    types = form.getlist("ps_source_type")
    ref_texts = form.getlist("ps_reference_text")
    ref_bles = form.getlist("ps_reference_ble")
    home_confidences = form.getlist("ps_home_confidence")
    away_confidences = form.getlist("ps_away_confidence")
    rows = []
    for i, source_type in enumerate(types):
        source_type = source_type.strip() or _PRESENCE_SOURCE_TYPES[0][0]
        if source_type == "ble_tag":
            reference = ref_bles[i].strip() if i < len(ref_bles) else ""
        else:
            reference = ref_texts[i].strip() if i < len(ref_texts) else ""
        row_id = ids[i].strip() if i < len(ids) else ""
        if not reference:
            if row_id:
                rows.append({"id": int(row_id), "delete": True})
            continue
        try:
            home_confidence = float(home_confidences[i]) if i < len(home_confidences) and home_confidences[i].strip() else 0.8
        except ValueError:
            home_confidence = 0.8
        try:
            away_confidence = float(away_confidences[i]) if i < len(away_confidences) and away_confidences[i].strip() else 0.8
        except ValueError:
            away_confidence = 0.8
        row = {
            "delete": False,
            "source_type": source_type,
            "reference": reference,
            "home_confidence": home_confidence,
            "away_confidence": away_confidence,
            "enabled": form.get(f"ps_enabled_{i}") == "on",
        }
        if row_id:
            row["id"] = int(row_id)
        rows.append(row)
    return rows


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


def _parse_activity_log_history(raw: str) -> list[int]:
    """Liest den 'history'-Query-Param der Verlauf-Seite: eine kommagetrennte Liste
    bereits besuchter before_id-Cursor (älteste zuerst), damit "Vorherige Einträge"
    zur exakt vorherigen Seite zurückspringen kann. ListActivityLogRequest kennt nur
    einen Vorwärts-Cursor (before_id) — der Rückweg wird hier als Breadcrumb im
    Query-String nachgebaut, nicht von Core geliefert."""
    return [int(x) for x in raw.split(",") if x.strip().lstrip("-").isdigit()]


def _resolve_activity_channel(entry, satellite_display_names: dict) -> dict:
    """Formatiert das 'wo' eines Activity-Log-Eintrags: 'satellite' wird auf den
    Satelliten-Anzeigenamen aufgelöst (Fallback auf die rohe channel_id, falls der
    Satellit inzwischen gelöscht wurde). Andere channel_types (telegram/iobroker/
    grpc_text/grpc_voice) bekommen ein festes Label statt Auflösung — ihre channel_id
    ist typspezifisch (bei telegram z.B. die Konto-ID, die ohnehin schon über user_id
    einem User zugeordnet ist) und wird nur als Zusatzinfo mitgegeben."""
    if entry.channel_type == "satellite":
        return {"label": satellite_display_names.get(entry.channel_id, entry.channel_id), "detail": ""}
    label = _ACTIVITY_LOG_CHANNEL_LABELS.get(entry.channel_type, entry.channel_type or "?")
    return {"label": label, "detail": entry.channel_id}


def _build_wav(pcm: bytes, sample_rate: int, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Baut einen minimalen WAV-Header um die rohen PCM-Daten (16-bit signed, mono —
    siehe ActivityAudioChunk in activity_log.proto). StreamActivityAudio liefert nur
    die Samples, ein <audio>-Element im Browser braucht aber einen Container mit Header."""
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm)
    header = b"RIFF" + (36 + data_size).to_bytes(4, "little") + b"WAVE"
    header += b"fmt " + (16).to_bytes(4, "little")
    header += (1).to_bytes(2, "little")  # PCM
    header += channels.to_bytes(2, "little")
    header += sample_rate.to_bytes(4, "little")
    header += byte_rate.to_bytes(4, "little")
    header += block_align.to_bytes(2, "little")
    header += bits_per_sample.to_bytes(2, "little")
    header += b"data" + data_size.to_bytes(4, "little")
    return header + pcm
