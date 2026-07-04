from flask import Blueprint, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import _slugify

bp = Blueprint("groups", __name__)


@bp.route("/groups")
@login_required
@trust_level_required(TRUST_LEVELS["list_groups"])
def groups():
    hannah = get_hannah()
    return render_template("groups.html", groups=hannah.get_groups(), rooms=hannah.get_rooms())


@bp.route("/groups/create", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_group"])
def create_group():
    hannah = get_hannah()
    display_name = request.form.get("display_name", "").strip()
    if display_name:
        hannah.create_group(_slugify(display_name), display_name)
    return redirect(url_for("groups.groups"))


@bp.route("/groups/<group_id>/edit")
@login_required
@trust_level_required(TRUST_LEVELS["edit_group"])
def edit_group(group_id: str):
    hannah = get_hannah()
    group = hannah.get_group(group_id)
    if group is None:
        return redirect(url_for("groups.groups"))
    selected_room_ids = {r.room_id for r in group.rooms}
    return render_template(
        "group_edit.html",
        group=group,
        rooms=hannah.get_rooms(),
        selected_room_ids=selected_room_ids,
    )


@bp.route("/groups/<group_id>/edit", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_group"])
def save_group(group_id: str):
    hannah = get_hannah()
    display_name = request.form.get("display_name", "").strip()
    room_ids = request.form.getlist("room_ids")
    if display_name:
        hannah.update_group(group_id, display_name)
    hannah.set_group_rooms(group_id, room_ids)
    return redirect(url_for("groups.groups"))


@bp.route("/groups/<group_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_group"])
def delete_group(group_id: str):
    hannah = get_hannah()
    hannah.delete_group(group_id)
    return redirect(url_for("groups.groups"))
