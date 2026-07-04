from flask import Blueprint, flash, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required

bp = Blueprint("cars", __name__)


@bp.route("/cars")
@login_required
@trust_level_required(TRUST_LEVELS["list_cars"])
def cars():
    hannah = get_hannah()
    users_by_id = {u.id: u for u in hannah.get_users()}
    cars_view = [
        {"car": c, "owners": [users_by_id[uid] for uid in c.owner_user_ids if uid in users_by_id]}
        for c in hannah.get_cars()
    ]
    return render_template("cars.html", cars=cars_view)


@bp.route("/cars/create", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["create_car"])
def create_car():
    hannah = get_hannah()
    topic_prefix = request.form.get("topic_prefix", "").strip()
    home_address = request.form.get("home_address", "").strip()
    name = request.form.get("name", "").strip()
    if topic_prefix:
        ok, message = hannah.create_car(topic_prefix, home_address, [], name)
        if not ok:
            flash(message, "danger")
    return redirect(url_for("cars.cars"))


@bp.route("/cars/<int:car_id>/edit")
@login_required
@trust_level_required(TRUST_LEVELS["edit_car"])
def edit_car(car_id: int):
    hannah = get_hannah()
    car = next((c for c in hannah.get_cars() if c.id == car_id), None)
    if car is None:
        return redirect(url_for("cars.cars"))
    users = [u for u in hannah.get_users() if u.active]
    return render_template("car_edit.html", car=car, users=users, selected_owner_ids=set(car.owner_user_ids))


@bp.route("/cars/<int:car_id>/edit", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_car"])
def save_car(car_id: int):
    hannah = get_hannah()
    topic_prefix = request.form.get("topic_prefix", "").strip()
    home_address = request.form.get("home_address", "").strip()
    name = request.form.get("name", "").strip()
    owner_user_ids = [int(uid) for uid in request.form.getlist("owner_user_ids")]
    ok, message = hannah.update_car(car_id, topic_prefix, home_address, owner_user_ids, name)
    if not ok:
        flash(message, "danger")
    return redirect(url_for("cars.cars"))


@bp.route("/cars/<int:car_id>/delete", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["delete_car"])
def delete_car(car_id: int):
    hannah = get_hannah()
    hannah.delete_car(car_id)
    return redirect(url_for("cars.cars"))
