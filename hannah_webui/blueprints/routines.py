import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import _ROUTINE_NEW_ACTION_ROWS, _parse_action_rows, _parse_lines

bp = Blueprint("routines", __name__)


@bp.route("/routines")
@login_required
@trust_level_required(TRUST_LEVELS["list_routines"])
def routines():
    hannah = get_hannah()
    routines_view = []
    for r in hannah.get_routines():
        try:
            actions = json.loads(r.actions_json) if r.actions_json else []
        except json.JSONDecodeError:
            actions = []
        routines_view.append({"routine": r, "actions": actions})
    return render_template("routines.html", routines=routines_view)


@bp.route("/routines/new")
@login_required
@trust_level_required(TRUST_LEVELS["create_routine"])
def new_routine():
    return render_template(
        "routine_edit.html", routine=None, actions=[], triggers_text="",
        action_rows=range(_ROUTINE_NEW_ACTION_ROWS),
    )


@bp.route("/routines/create", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_routine"])
def create_routine():
    hannah = get_hannah()
    name = request.form.get("name", "").strip()
    if name:
        triggers = _parse_lines(request.form.get("triggers", ""))
        actions = _parse_action_rows(request.form)
        reply = request.form.get("reply", "").strip()
        ok, message = hannah.create_routine(name, triggers, actions, reply)
        if not ok:
            flash(message, "danger")
            return redirect(url_for("routines.new_routine"))
    return redirect(url_for("routines.routines"))


@bp.route("/routines/<int:routine_id>/edit")
@login_required
@trust_level_required(TRUST_LEVELS["edit_routine"])
def edit_routine(routine_id: int):
    hannah = get_hannah()
    routine = next((r for r in hannah.get_routines() if r.id == routine_id), None)
    if routine is None:
        return redirect(url_for("routines.routines"))
    try:
        actions = json.loads(routine.actions_json) if routine.actions_json else []
    except json.JSONDecodeError:
        actions = []
    action_rows = range(max(len(actions) + 2, _ROUTINE_NEW_ACTION_ROWS))
    return render_template(
        "routine_edit.html", routine=routine, actions=actions,
        triggers_text="\n".join(routine.triggers), action_rows=action_rows,
    )


@bp.route("/routines/<int:routine_id>/edit", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_routine"])
def save_routine(routine_id: int):
    hannah = get_hannah()
    name = request.form.get("name", "").strip()
    triggers = _parse_lines(request.form.get("triggers", ""))
    actions = _parse_action_rows(request.form)
    reply = request.form.get("reply", "").strip()
    ok, message = hannah.update_routine(routine_id, name, triggers, actions, reply)
    if not ok:
        flash(message, "danger")
    return redirect(url_for("routines.routines"))


@bp.route("/routines/<int:routine_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_routine"])
def delete_routine(routine_id: int):
    hannah = get_hannah()
    hannah.delete_routine(routine_id)
    return redirect(url_for("routines.routines"))
