import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import (
    _TRIGGER_NEW_ACTION_ROWS,
    _TRIGGER_NEW_ALSO_ROWS,
    _TRIGGER_NEW_WHEN_ROWS,
    _action_to_row,
    _as_or_list,
    _attach_also_unless,
    _blank_action_row,
    _blank_state_row,
    _blank_when_row,
    _condition_to_row,
    _device_state_options,
    _extract_also_unless,
    _parse_also,
    _parse_state_condition_rows,
    _parse_trigger_action_rows,
    _parse_when_rows,
    _slugify,
    _state_condition_to_row,
)

bp = Blueprint("triggers", __name__)


@bp.route("/triggers")
@login_required
@trust_level_required(TRUST_LEVELS["list_triggers"])
def triggers():
    hannah = get_hannah()
    triggers_view = []
    for t in hannah.get_triggers():
        try:
            actions = json.loads(t.actions_json) if t.actions_json else []
        except json.JSONDecodeError:
            actions = []
        try:
            when = json.loads(t.when_json) if t.when_json else {}
        except json.JSONDecodeError:
            when = {}
        triggers_view.append({"trigger": t, "actions": actions, "when": _as_or_list(when)})
    return render_template("triggers.html", triggers=triggers_view)


@bp.route("/triggers/new")
@login_required
@trust_level_required(TRUST_LEVELS["create_trigger"])
def new_trigger():
    hannah = get_hannah()
    return render_template(
        "trigger_edit.html", trigger=None,
        when_rows=[_blank_when_row() for _ in range(_TRIGGER_NEW_WHEN_ROWS)],
        also_rows=[_blank_state_row() for _ in range(_TRIGGER_NEW_ALSO_ROWS)], also_op="and",
        unless_rows=[_blank_state_row() for _ in range(_TRIGGER_NEW_ALSO_ROWS)],
        action_rows=[_blank_action_row() for _ in range(_TRIGGER_NEW_ACTION_ROWS)],
        on_response_text="",
        device_options=_device_state_options(hannah.get_devices()),
        rooms=hannah.get_rooms(),
    )


@bp.route("/triggers/create", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_trigger"])
def create_trigger():
    hannah = get_hannah()
    trigger_id = _slugify(request.form.get("id", ""))
    if trigger_id:
        also = _parse_also(request.form)
        unless = _parse_state_condition_rows(request.form, "unless") or None
        when = _attach_also_unless(_parse_when_rows(request.form), also, unless)
        actions = _parse_trigger_action_rows(request.form)
        ask = request.form.get("ask", "").strip()
        rephrase = request.form.get("rephrase") == "on"
        room = request.form.get("room", "").strip() or "all"
        cooldown = int(request.form.get("cooldown") or 3600)
        delay = request.form.get("delay", "").strip()
        on_response_text = request.form.get("on_response_json", "").strip()
        try:
            on_response = json.loads(on_response_text) if on_response_text else []
        except json.JSONDecodeError as e:
            flash(f"Ungültiges JSON in 'Erweitert: Antwortregeln': {e}", "danger")
            return redirect(url_for("triggers.new_trigger"))
        ok, message = hannah.create_trigger(
            trigger_id, when, None, on_response, actions, "", ask, rephrase, room, cooldown, delay,
        )
        if not ok:
            flash(message, "danger")
            return redirect(url_for("triggers.new_trigger"))
    return redirect(url_for("triggers.triggers"))


@bp.route("/triggers/<trigger_id>/edit")
@login_required
@trust_level_required(TRUST_LEVELS["edit_trigger"])
def edit_trigger(trigger_id: str):
    hannah = get_hannah()
    trigger = next((t for t in hannah.get_triggers() if t.id == trigger_id), None)
    if trigger is None:
        return redirect(url_for("triggers.triggers"))
    try:
        conditions = _as_or_list(json.loads(trigger.when_json) if trigger.when_json else {})
    except json.JSONDecodeError:
        conditions = []
    also_conditions, also_op, unless_conditions = _extract_also_unless(conditions)
    try:
        actions = json.loads(trigger.actions_json) if trigger.actions_json else []
    except json.JSONDecodeError:
        actions = []
    try:
        on_response = json.loads(trigger.on_response_json) if trigger.on_response_json else []
        on_response_text = json.dumps(on_response, indent=2, ensure_ascii=False) if on_response else ""
    except json.JSONDecodeError:
        on_response_text = trigger.on_response_json
    return render_template(
        "trigger_edit.html", trigger=trigger,
        when_rows=[_condition_to_row(c) for c in conditions]
        + [_blank_when_row() for _ in range(_TRIGGER_NEW_WHEN_ROWS)],
        also_rows=[_state_condition_to_row(c) for c in also_conditions]
        + [_blank_state_row() for _ in range(_TRIGGER_NEW_ALSO_ROWS)],
        also_op=also_op,
        unless_rows=[_state_condition_to_row(c) for c in unless_conditions]
        + [_blank_state_row() for _ in range(_TRIGGER_NEW_ALSO_ROWS)],
        action_rows=[_action_to_row(a) for a in actions]
        + [_blank_action_row() for _ in range(_TRIGGER_NEW_ACTION_ROWS)],
        on_response_text=on_response_text,
        device_options=_device_state_options(hannah.get_devices()),
        rooms=hannah.get_rooms(),
    )


@bp.route("/triggers/<trigger_id>/edit", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_trigger"])
def save_trigger(trigger_id: str):
    hannah = get_hannah()
    also = _parse_also(request.form)
    unless = _parse_state_condition_rows(request.form, "unless") or None
    when = _attach_also_unless(_parse_when_rows(request.form), also, unless)
    actions = _parse_trigger_action_rows(request.form)
    ask = request.form.get("ask", "").strip()
    rephrase = request.form.get("rephrase") == "on"
    room = request.form.get("room", "").strip() or "all"
    cooldown = int(request.form.get("cooldown") or 3600)
    delay = request.form.get("delay", "").strip()
    on_response_text = request.form.get("on_response_json", "").strip()
    try:
        on_response = json.loads(on_response_text) if on_response_text else []
    except json.JSONDecodeError as e:
        flash(f"Ungültiges JSON in 'Erweitert: Antwortregeln': {e}", "danger")
        return redirect(url_for("triggers.edit_trigger", trigger_id=trigger_id))
    ok, message = hannah.update_trigger(
        trigger_id, when, None, on_response, actions, "", ask, rephrase, room, cooldown, delay,
    )
    if not ok:
        flash(message, "danger")
    return redirect(url_for("triggers.triggers"))


@bp.route("/triggers/<trigger_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_trigger"])
def delete_trigger(trigger_id: str):
    hannah = get_hannah()
    hannah.delete_trigger(trigger_id)
    return redirect(url_for("triggers.triggers"))
