from flask import Blueprint, flash, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required

bp = Blueprint("ble_tags", __name__)


@bp.route("/ble-tags")
@login_required
@trust_level_required(TRUST_LEVELS["list_ble_tags"])
def ble_tags():
    hannah = get_hannah()
    users = [u for u in hannah.get_users() if u.active]
    return render_template("ble_tags.html", tags=hannah.get_ble_tags(), users=users)


@bp.route("/ble-tags/create", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_ble_tag"])
def create_ble_tag():
    hannah = get_hannah()
    mac_address = request.form.get("mac_address", "").strip()
    label = request.form.get("label", "").strip()
    user_id = int(request.form.get("user_id") or 0)
    if mac_address:
        ok, message = hannah.create_ble_tag(mac_address, label, user_id)
        if not ok:
            flash(message, "danger")
    return redirect(url_for("ble_tags.ble_tags"))


@bp.route("/ble-tags/<int:tag_id>/edit", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_ble_tag"])
def edit_ble_tag(tag_id: int):
    hannah = get_hannah()
    mac_address = request.form.get("mac_address", "").strip()
    label = request.form.get("label", "").strip()
    user_id = int(request.form.get("user_id") or 0)
    ok, message = hannah.update_ble_tag(tag_id, mac_address, label, user_id)
    if not ok:
        flash(message, "danger")
    return redirect(url_for("ble_tags.ble_tags"))


@bp.route("/ble-tags/<int:tag_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_ble_tag"])
def delete_ble_tag(tag_id: int):
    hannah = get_hannah()
    hannah.delete_ble_tag(tag_id)
    return redirect(url_for("ble_tags.ble_tags"))
