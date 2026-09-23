import json
from urllib.parse import quote, urlsplit

import grpc
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from hannah_webui.extensions import (
    TRUST_LEVELS,
    entra_configured,
    get_entra_app,
    get_entra_tenant,
    get_hannah,
    get_telegram_config,
    login_required,
)
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
    # Ein Core ohne GetChannels (älter als hannah-proto 4.3.0) antwortet UNIMPLEMENTED —
    # dann gibt es eben keinen Deep-Link-Weg, /me selbst darf daran nicht scheitern.
    try:
        telegram_deep_link = any(c.service == "telegram" and c.supports_link for c in hannah.get_channels())
    except grpc.RpcError:
        telegram_deep_link = False
    alarms = sorted(hannah.get_alarms(session["user_id"]), key=lambda a: a.time)
    satellites = hannah.get_satellites()
    # Enrollment needs a live satellite to run the guided dialog on — unlike the alarm
    # dropdown below, an offline target here isn't just harmless-but-useless, the request
    # would go nowhere, so filter to connected ones upfront.
    enrollment_satellites = [s for s in satellites if s.connected]
    enrollable_users = (
        [u for u in hannah.get_users() if u.active]
        if session.get("trust_level", 0) >= TRUST_LEVELS["enroll_other_voice"] else []
    )
    return render_template(
        "me.html", display_name=session.get("display_name"),
        linked_accounts=linked_accounts, telegram_login_url=telegram_login_url,
        telegram_deep_link=telegram_deep_link,
        entra_configured=entra_configured(),
        alarms=alarms, satellites=satellites, weekday_names=_WEEKDAY_NAMES,
        enrollment_satellites=enrollment_satellites, enrollable_users=enrollable_users,
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


@bp.route("/me/telegram/link", methods=["POST"])
@login_required
def telegram_link():
    """Deep-Link-Verknüpfung (#63): Core stellt einen Einmal-Code aus und liefert den
    fertigen t.me-Link, der Telegram-Adapter löst ihn beim /start ein. Die WebUI braucht
    dafür weder Bot-Token noch Domain noch TLS."""
    resp = get_hannah().create_link_token(session["user_id"], "telegram")
    if not resp.ok:
        flash(resp.message or "Telegram-Verknüpfung ist gerade nicht möglich.", "danger")
        return redirect(url_for("me.me"))
    return redirect(resp.link_url)


@bp.route("/me/linked-accounts")
@login_required
def linked_accounts():
    """Polling-Ziel für /me, solange eine Deep-Link-Verknüpfung auf "Start" in Telegram wartet."""
    user = next((u for u in get_hannah().get_users() if u.id == session["user_id"]), None)
    return jsonify(dict(user.linked_accounts) if user else {})


@bp.route("/me/telegram/unlink", methods=["POST"])
@login_required
def telegram_unlink():
    hannah = get_hannah()
    hannah.unlink_account(session["user_id"], "telegram", session["user_id"])
    flash("Telegram-Konto getrennt.", "success")
    return redirect(url_for("me.me"))


@bp.route("/me/entra/login")
@login_required
def entra_login():
    entra = get_entra_app()
    if entra is None:
        flash("Microsoft-Entra-Verknüpfung ist auf diesem Server nicht konfiguriert.", "danger")
        return redirect(url_for("me.me"))
    # Redirect-URI wie bei Telegram erzwungen auf https (TLS-terminierender Reverse-Proxy
    # ohne X-Forwarded-Proto, siehe #9) — muss exakt so in der App-Registration stehen.
    # response_mode bleibt beim Default "query": bei form_post käme der Callback als
    # Cross-Site-POST, dem das (SameSite=Lax) Session-Cookie samt Flow-State fehlt.
    flow = entra.initiate_auth_code_flow(
        scopes=[], prompt="select_account",
        redirect_uri=url_for("me.entra_callback", _external=True, _scheme="https"),
    )
    session["entra_flow"] = flow
    return redirect(flow["auth_uri"])


@bp.route("/me/entra/callback")
@login_required
def entra_callback():
    entra = get_entra_app()
    flow = session.pop("entra_flow", None)
    if entra is None or flow is None:
        flash("Microsoft-Entra-Verknüpfung fehlgeschlagen: keine laufende Anmeldung.", "danger")
        return redirect(url_for("me.me"))
    try:
        # prüft state, nonce, PKCE und die ID-Token-Claims (aud/iss/exp)
        result = entra.acquire_token_by_auth_code_flow(flow, request.args.to_dict())
    except ValueError:
        result = {"error": "invalid_state"}
    claims = result.get("id_token_claims") or {}
    if "error" in result or not claims.get("oid"):
        flash("Microsoft-Entra-Verknüpfung fehlgeschlagen.", "danger")
        return redirect(url_for("me.me"))
    if claims.get("tid") != get_entra_tenant():
        flash("Microsoft-Entra-Verknüpfung fehlgeschlagen: Konto gehört zu einem fremden Tenant.", "danger")
        return redirect(url_for("me.me"))
    hannah = get_hannah()
    payload = {k: claims[k] for k in ("oid", "tid", "preferred_username", "name") if k in claims}
    ok = hannah.link_account(session["user_id"], "entra", claims["oid"], json.dumps(payload))
    flash("Microsoft-Entra-Konto verknüpft." if ok else "Verknüpfung fehlgeschlagen.", "success" if ok else "danger")
    return redirect(url_for("me.me"))


@bp.route("/me/entra/unlink", methods=["POST"])
@login_required
def entra_unlink():
    hannah = get_hannah()
    hannah.unlink_account(session["user_id"], "entra", session["user_id"])
    flash("Microsoft-Entra-Konto getrennt.", "success")
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


@bp.route("/me/voice-enrollment/start", methods=["POST"])
@login_required
def start_voice_enrollment():
    hannah = get_hannah()
    satellite_id = request.form.get("satellite_id", "").strip()
    if not satellite_id:
        flash("Satellit ist Pflicht.", "danger")
        return redirect(url_for("me.me"))
    # Self-enrollment is the default and needs no trust level (hannah-webui#52); enrolling
    # someone else is additive and gated — silently ignore target_user_id below that level
    # rather than trusting a tampered form field.
    target_user_id = session["user_id"]
    if session.get("trust_level", 0) >= TRUST_LEVELS["enroll_other_voice"]:
        raw_target = request.form.get("target_user_id", "").strip()
        if raw_target:
            target_user_id = int(raw_target)
    ok, message = hannah.start_voice_enrollment(satellite_id, target_user_id, session["user_id"])
    if ok:
        flash(message or "Voice-Enrollment gestartet.", "success")
    else:
        flash(message or "Voice-Enrollment konnte nicht gestartet werden.", "danger")
    return redirect(url_for("me.me"))
