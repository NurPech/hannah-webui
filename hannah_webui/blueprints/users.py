import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import (
    _PRESENCE_SOURCE_NEW_ROWS,
    _PRESENCE_SOURCE_TYPES,
    _USER_TYPES,
    _blank_presence_source_row,
    _parse_presence_source_rows,
    _presence_source_to_row,
)

bp = Blueprint("users", __name__)


@bp.route("/users")
@login_required
@trust_level_required(TRUST_LEVELS["list_users"])
def users():
    hannah = get_hannah()
    residents_by_id = {r.id: r for r in hannah.get_residents()}
    users_view = [
        {"user": u, "resident": residents_by_id.get(u.linked_accounts.get("residents", ""))}
        for u in hannah.get_users()
    ]
    return render_template("users.html", users=users_view, residents=hannah.get_residents())


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_user"])
def create_user():
    hannah = get_hannah()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        display_name = request.form.get("display_name", "").strip()
        user_type = request.form.get("type", "roomie")
        if not (username and password and email):
            flash("Username, Passwort und E-Mail sind Pflicht.", "danger")
            return redirect(url_for("users.create_user"))
        ok, message = hannah.create_user(username, password, email, display_name, user_type)
        if not ok:
            flash(message, "danger")
            return redirect(url_for("users.create_user"))
        return redirect(url_for("users.users"))
    return render_template("user_create.html", types=_USER_TYPES)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_user"])
def edit_user(user_id: int):
    hannah = get_hannah()
    user = next((u for u in hannah.get_users() if u.id == user_id), None)
    if user is None:
        return redirect(url_for("users.users"))
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip()
        user_type = request.form.get("type", user.type)
        is_active = bool(request.form.get("is_active"))
        password = request.form.get("password", "").strip()
        trust_level = int(request.form.get("trust_level") or user.trust_level)
        system_messages = bool(request.form.get("system_messages"))
        ok, message = hannah.update_user(user_id, display_name, email, user_type, is_active, password)
        if not ok:
            flash(message, "danger")
        hannah.set_trust_level(user_id, trust_level)
        hannah.set_system_messages(user_id, system_messages)
        return redirect(url_for("users.users"))
    return render_template("user_edit.html", user=user, types=_USER_TYPES)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_user"])
def delete_user(user_id: int):
    hannah = get_hannah()
    hannah.delete_user(user_id)
    return redirect(url_for("users.users"))


@bp.route("/users/<int:user_id>/link-resident", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["link_resident"])
def link_resident(user_id: int):
    hannah = get_hannah()
    resident_id = request.form.get("resident_id", "")
    resident = next((r for r in hannah.get_residents() if r.id == resident_id), None)
    if resident:
        payload = json.dumps({"resident_type": resident.type, "roomie_id": resident.roomie_id})
        hannah.link_account(user_id, "residents", resident.id, payload)
    return redirect(url_for("users.users"))


@bp.route("/users/<int:user_id>/unlink-resident", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["link_resident"])
def unlink_resident(user_id: int):
    hannah = get_hannah()
    hannah.unlink_account(user_id, "residents", session.get("user_id"))
    return redirect(url_for("users.users"))


@bp.route("/users/<int:user_id>/presence-sources", methods=["GET", "POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_presence_sources"])
def presence_sources(user_id: int):
    hannah = get_hannah()
    user = next((u for u in hannah.get_users() if u.id == user_id), None)
    if user is None:
        return redirect(url_for("users.users"))
    if request.method == "POST":
        for row in _parse_presence_source_rows(request.form):
            if row.get("delete"):
                hannah.delete_presence_source(row["id"])
            elif "id" in row:
                ok, message = hannah.update_presence_source(
                    row["id"], user_id, row["source_type"], row["reference"],
                    row["home_confidence"], row["away_confidence"], row["enabled"],
                )
                if not ok:
                    flash(message, "danger")
            else:
                ok, message = hannah.create_presence_source(
                    user_id, row["source_type"], row["reference"],
                    row["home_confidence"], row["away_confidence"], row["enabled"],
                )
                if not ok:
                    flash(message, "danger")
        return redirect(url_for("users.presence_sources", user_id=user_id))
    sources = hannah.get_presence_sources(user_id)
    ble_tags = [t for t in hannah.get_ble_tags() if t.user_id == user_id]
    return render_template(
        "presence_sources.html", user=user,
        source_rows=[_presence_source_to_row(s) for s in sources]
        + [_blank_presence_source_row() for _ in range(_PRESENCE_SOURCE_NEW_ROWS)],
        source_types=_PRESENCE_SOURCE_TYPES,
        ble_tags=ble_tags,
    )
