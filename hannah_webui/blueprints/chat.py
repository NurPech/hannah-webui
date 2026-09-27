import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from hannah_webui.extensions import get_hannah, login_required

bp = Blueprint("chat", __name__)


@bp.route("/chat")
def chat():
    # Bewusst kein login_required: der Chat authentifiziert sich über den Token im
    # localStorage des Browsers, nicht über die Flask-Session (#70) — soll standalone
    # in einem eigenen Browserfenster laufen, ohne die WebUI je gesehen zu haben.
    return render_template("chat.html")


@bp.route("/chat/authorize")
@login_required
def chat_authorize():
    """Verknüpft den eingeloggten User per Zufalls-Token mit dem Service "webchat" und
    reicht das Token an den Chat zurück, der es im localStorage ablegt. Bewusst kein
    CreateLinkToken/Redeem-Umweg wie bei Telegram — die WebUI-Session hat den User hier
    bereits selbst authentifiziert, das Token muss also nicht erst von einem externen
    Adapter eingelöst werden."""
    token = secrets.token_urlsafe(32)
    get_hannah().link_account(session["user_id"], "webchat", token)
    return redirect(url_for("chat.chat", token=token))


@bp.route("/chat/send", methods=["POST"])
def chat_send():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    token = data.get("token") or ""
    if not text:
        return jsonify({"error": "text fehlt"}), 400
    answer, intent_name = get_hannah().submit_text(text, source_service="webchat" if token else "", source_user_id=token)
    return jsonify({"answer": answer, "intent_name": intent_name})
