from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from hannah_webui.extensions import get_hannah, login_required

bp = Blueprint("messages", __name__)

MESSAGE_SOURCE = "webui"


@bp.route("/messages")
@login_required
def messages():
    hannah = get_hannah()
    msgs = sorted(hannah.list_messages(requestor_id=session["user_id"]), key=lambda m: m.id, reverse=True)
    display_names = {u.id: (u.display_name or u.user_name) for u in hannah.get_users()}
    rows = [{"message": m, "sender_name": display_names.get(m.sender_user_id, "")} for m in msgs]
    recipients = [u for u in hannah.get_users() if u.active and u.id != session["user_id"]]
    return render_template("messages.html", rows=rows, recipients=recipients)


@bp.route("/messages/send", methods=["POST"])
@login_required
def send_message():
    hannah = get_hannah()
    recipient_id = int(request.form.get("recipient_id") or 0)
    content = request.form.get("content", "").strip()
    if not recipient_id or not content:
        flash("Empfänger und Text sind Pflicht.", "danger")
        return redirect(url_for("messages.messages"))
    ok, message = hannah.create_message(
        user_id=recipient_id, content=content, source=MESSAGE_SOURCE,
        sender_user_id=session["user_id"], reply_to_id=0,
    )
    if not ok:
        flash(message, "danger")
    return redirect(url_for("messages.messages"))


@bp.route("/messages/<int:message_id>/reply", methods=["POST"])
@login_required
def reply_message(message_id: int):
    hannah = get_hannah()
    original = next((m for m in hannah.list_messages(requestor_id=session["user_id"]) if m.id == message_id), None)
    if original is None or not original.sender_user_id:
        return redirect(url_for("messages.messages"))
    content = request.form.get("content", "").strip()
    if not content:
        flash("Antworttext darf nicht leer sein.", "danger")
        return redirect(url_for("messages.messages"))
    ok, message = hannah.create_message(
        user_id=original.sender_user_id, content=content, source=MESSAGE_SOURCE,
        sender_user_id=session["user_id"], reply_to_id=original.id,
    )
    if not ok:
        flash(message, "danger")
    return redirect(url_for("messages.messages"))


@bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message(message_id: int):
    hannah = get_hannah()
    hannah.delete_message(requestor_id=session["user_id"], message_id=message_id)
    return redirect(url_for("messages.messages"))
