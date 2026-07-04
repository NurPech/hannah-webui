import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import _prepare_setting_row

bp = Blueprint("settings", __name__)


@bp.route("/settings")
@login_required
@trust_level_required(TRUST_LEVELS["list_settings"])
def settings():
    hannah = get_hannah()
    categories, settings_list = hannah.get_settings()
    categories_sorted = sorted(categories, key=lambda c: c.name)
    settings_by_cat: dict[int, list] = {c.id: [] for c in categories}
    for s in settings_list:
        settings_by_cat.setdefault(s.category_id, []).append(_prepare_setting_row(s))
    for items in settings_by_cat.values():
        items.sort(key=lambda v: v["setting"].name)
    return render_template("settings.html", categories=categories_sorted, settings_by_cat=settings_by_cat)


@bp.route("/settings/<int:setting_id>/update", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["edit_setting"])
def update_setting(setting_id: int):
    hannah = get_hannah()
    value_type = request.form.get("value_type", "json")
    if value_type == "text":
        text_value = request.form.get("text_value", "").replace("\r\n", "\n")
        value_json = json.dumps(text_value, ensure_ascii=False)
    elif value_type == "list":
        items = [v.strip() for v in request.form.getlist("list_item") if v.strip()]
        value_json = json.dumps(items, ensure_ascii=False)
    elif value_type == "keyvalue":
        keys = request.form.getlist("kv_key")
        values = request.form.getlist("kv_value")
        pairs = {k.strip(): v.strip() for k, v in zip(keys, values) if k.strip()}
        value_json = json.dumps(pairs, ensure_ascii=False)
    else:
        value_json = request.form.get("value", "")
    ok, message = hannah.update_setting(setting_id, value_json)
    if not ok:
        flash(message, "danger")
    return redirect(url_for("settings.settings"))
