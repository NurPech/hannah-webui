from flask import Blueprint, redirect, render_template, request, session, url_for

from hannah_webui.extensions import get_hannah

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        found, user = get_hannah().login(username, password)
        if found:
            session["user_id"] = user.id
            session["display_name"] = user.display_name or user.user_name
            session["trust_level"] = user.trust_level
            return redirect(url_for("me.me"))
        error = "Ungültige Zugangsdaten."
    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
