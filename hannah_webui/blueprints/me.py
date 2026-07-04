import json
from urllib.parse import quote, urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from hannah_webui.extensions import get_hannah, get_telegram_config, login_required
from hannah_webui.route_helpers import _WEEKDAY_NAMES, _verify_telegram_auth

bp = Blueprint("me", __name__)


@bp.route("/")
@login_required
def index():
    return redirect(url_for("me.me"))


@bp.route("/me")
@login_required
def me():
    hannah = get_hannah()
    telegram_bot_token, telegram_bot_username = get_telegram_config()
    user = next((u for u in hannah.get_users() if u.id == session["user_id"]), None)
    linked_accounts = user.linked_accounts if user else {}
    telegram_login_url = None
    if telegram_bot_token and telegram_bot_username:
        # Telegram appends the signed result as a URL *fragment* (#tgAuthResult=...) on
        # return_to, not a query string — fragments never reach the server, so return_to
        # must be a real page (this one) whose JS decodes it and forwards to the callback
        # route as a proper query string. See the inline script in me.html.
        me_url = url_for("me.me", _external=True, _scheme="https")
        origin = "{0.scheme}://{0.netloc}".format(urlsplit(me_url))
        bot_id = telegram_bot_token.split(":", 1)[0]
        telegram_login_url = (
            f"https://oauth.telegram.org/auth?bot_id={quote(bot_id)}&origin={quote(origin, safe='')}"
            f"&request_access=write&return_to={quote(me_url, safe='')}"
        )
    alarms = sorted(hannah.get_alarms(session["user_id"]), key=lambda a: a.time)
    return render_template(
        "me.html", display_name=session.get("display_name"),
        linked_accounts=linked_accounts, telegram_login_url=telegram_login_url,
        alarms=alarms, satellites=hannah.get_satellites(), weekday_names=_WEEKDAY_NAMES,
    )


@bp.route("/me/telegram/callback")
@login_required
def telegram_callback():
    hannah = get_hannah()
    telegram_bot_token, _ = get_telegram_config()
    data = request.args.to_dict()
    if not _verify_telegram_auth(data, telegram_bot_token):
        flash("Telegram-Verknüpfung fehlgeschlagen: ungültige oder abgelaufene Signatur.", "danger")
        return redirect(url_for("me.me"))
    ok = hannah.link_account(session["user_id"], "telegram", data["id"], json.dumps(data))
    flash("Telegram-Konto verknüpft." if ok else "Verknüpfung fehlgeschlagen.", "success" if ok else "danger")
    return redirect(url_for("me.me"))


@bp.route("/me/telegram/unlink", methods=["POST"])
@login_required
def telegram_unlink():
    hannah = get_hannah()
    hannah.unlink_account(session["user_id"], "telegram", session["user_id"])
    flash("Telegram-Konto getrennt.", "success")
    return redirect(url_for("me.me"))


@bp.route("/me/password", methods=["POST"])
@login_required
def update_my_password():
    hannah = get_hannah()
    password = request.form.get("password", "").strip()
    confirm = request.form.get("password_confirm", "").strip()
    if not password:
        flash("Passwort darf nicht leer sein.", "danger")
        return redirect(url_for("me.me"))
    if password != confirm:
        flash("Passwörter stimmen nicht überein.", "danger")
        return redirect(url_for("me.me"))
    user = next((u for u in hannah.get_users() if u.id == session["user_id"]), None)
    if user is None:
        flash("User nicht gefunden.", "danger")
        return redirect(url_for("me.me"))
    ok, message = hannah.update_user(user.id, user.display_name, user.email, user.type, user.active, password)
    flash(message if not ok else "Passwort geändert.", "danger" if not ok else "success")
    return redirect(url_for("me.me"))


@bp.route("/me/alarms/create", methods=["POST"])
@login_required
def create_alarm():
    hannah = get_hannah()
    time_str = request.form.get("time", "").strip()
    if not time_str:
        flash("Uhrzeit ist Pflicht.", "danger")
        return redirect(url_for("me.me"))
    satellite_id = request.form.get("satellite_id", "").strip()
    if not satellite_id:
        flash("Satellit ist Pflicht — ein Wecker kann nicht auf allen Satelliten gleichzeitig klingeln.", "danger")
        return redirect(url_for("me.me"))
    label = request.form.get("label", "").strip()
    one_shot_date = ""
    weekdays: list[int] = []
    if request.form.get("alarm_type", "once") == "recurring":
        weekdays = sorted({int(d) for d in request.form.getlist("weekdays")})
    else:
        one_shot_date = request.form.get("one_shot_date", "").strip()
    ok, message = hannah.create_alarm(satellite_id, time_str, weekdays, one_shot_date, label, session["user_id"])
    if not ok:
        flash(message, "danger")
    return redirect(url_for("me.me"))


@bp.route("/me/alarms/<int:alarm_id>/toggle", methods=["POST"])
@login_required
def toggle_alarm(alarm_id: int):
    hannah = get_hannah()
    alarm = next((a for a in hannah.get_alarms(session["user_id"]) if a.id == alarm_id), None)
    if alarm is None:
        return redirect(url_for("me.me"))
    ok, message = hannah.update_alarm(
        alarm_id, alarm.satellite_id, alarm.time, list(alarm.weekdays), list(alarm.skip_dates),
        alarm.one_shot_date, not alarm.enabled, alarm.label,
    )
    if not ok:
        flash(message, "danger")
    return redirect(url_for("me.me"))


@bp.route("/me/alarms/<int:alarm_id>/delete", methods=["POST"])
@login_required
def delete_alarm(alarm_id: int):
    hannah = get_hannah()
    alarm = next((a for a in hannah.get_alarms(session["user_id"]) if a.id == alarm_id), None)
    if alarm is not None:
        hannah.delete_alarm(alarm_id)
    return redirect(url_for("me.me"))
