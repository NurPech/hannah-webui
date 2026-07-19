from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required

bp = Blueprint("satellites", __name__)


@bp.route("/satellites")
@login_required
@trust_level_required(TRUST_LEVELS["list_satellites"])
def satellites():
    hannah = get_hannah()
    rooms = hannah.get_rooms()
    room_display_names = {r.room_id: r.display_name for r in rooms}
    sats = hannah.get_satellites()
    sats_view = [{
        "sat": sat,
        "live_room_display": room_display_names.get(sat.room, sat.room),
    } for sat in sats
    if session.get("trust_level", 0) >= TRUST_LEVELS["delete_satellite"]
        or sat.owner_user_id == session.get("user_id", 0)]
    sats_view.sort(key=lambda v: v["sat"].device_id)
    users = [u for u in hannah.get_users() if u.active]
    return render_template("satellites.html", satellites=sats_view, rooms=rooms, users=users)


@bp.route("/satellites/<device_id>/room", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["set_satellite_room"])
def set_satellite_room(device_id: str):
    hannah = get_hannah()
    ok, message = hannah.set_satellite_room(device_id, request.form.get("room_id", ""), session["user_id"])
    if not ok:
        flash(message or "Raum konnte nicht gesetzt werden.", "danger")
    return redirect(url_for("satellites.satellites"))


@bp.route("/satellites/<device_id>/name", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["set_satellite_name"])
def set_satellite_name(device_id: str):
    hannah = get_hannah()
    display_name = request.form.get("display_name", "").strip()
    if display_name:
        ok, message = hannah.set_satellite_display_name(device_id, display_name, session["user_id"])
        if not ok:
            flash(message or "Anzeigename konnte nicht gesetzt werden.", "danger")
    return redirect(url_for("satellites.satellites"))


@bp.route("/satellites/<device_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_satellite"])
def delete_satellite(device_id: str):
    hannah = get_hannah()
    ok, message = hannah.delete_satellite(device_id=device_id, requestor_id=session["user_id"])
    if ok:
        flash("Satellit gelöscht.", "success")
    else:
        flash(message or "Satellit konnte nicht gelöscht werden.", "danger")
    return redirect(url_for("satellites.satellites"))


@bp.route("/satellites/<device_id>/owner", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["set_satellite_owner"])
def set_satellite_owner(device_id: str):
    hannah = get_hannah()
    user_id = int(request.form.get("user_id") or 0)
    ok, message = hannah.set_satellite_owner(device_id, user_id, session["user_id"])
    if not ok:
        flash(message or "Besitzer konnte nicht gesetzt werden.", "danger")
    return redirect(url_for("satellites.satellites"))


@bp.route("/satellites/<device_id>/followup", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["set_satellite_followup"])
def set_satellite_followup(device_id: str):
    hannah = get_hannah()
    enabled = request.form.get("enabled") == "1"
    ok, message = hannah.set_satellite_followup(device_id, enabled, session["user_id"])
    if not ok:
        flash(message or "FollowUp-Einstellung konnte nicht gesetzt werden.", "danger")
    return redirect(url_for("satellites.satellites"))


@bp.route("/satellites/<device_id>/update-firmware", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["trigger_firmware_update"])
def trigger_firmware_update(device_id: str):
    hannah = get_hannah()
    ok, message = hannah.trigger_firmware_update(device_id)
    if ok:
        flash("Firmware-Update angestoßen.", "success")
    else:
        flash(message or "Firmware-Update konnte nicht angestoßen werden.", "danger")
    return redirect(url_for("satellites.satellites"))
