from flask import Blueprint, Response, abort, render_template, request, session

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required
from hannah_webui.route_helpers import _ACTIVITY_LOG_PAGE_SIZE, _build_wav, _parse_activity_log_history, _resolve_activity_channel

bp = Blueprint("activity_log", __name__)


@bp.route("/activity-log")
@login_required
def activity_log():
    hannah = get_hannah()
    can_filter = session.get("trust_level", 0) >= TRUST_LEVELS["filter_activity_log"]
    filter_user_id = int(request.args.get("filter_user_id") or 0) if can_filter else 0
    before_id = int(request.args.get("before_id") or 0)
    history = _parse_activity_log_history(request.args.get("history", ""))

    entries, has_more = hannah.list_activity_log(
        requestor_id=session["user_id"], filter_user_id=filter_user_id,
        page_size=_ACTIVITY_LOG_PAGE_SIZE, before_id=before_id,
    )

    satellite_display_names = {s.device_id: (s.display_name or s.device_id) for s in hannah.get_satellites()}
    user_display_names = {u.id: (u.display_name or u.user_name) for u in hannah.get_users()}
    rows = [{
        "entry": entry,
        "channel": _resolve_activity_channel(entry, satellite_display_names),
        "user_display_name": user_display_names.get(entry.user_id, ""),
    } for entry in entries]

    return render_template(
        "activity_log.html", rows=rows, has_more=has_more,
        next_before_id=entries[-1].id if entries else 0,
        older_history=",".join(str(x) for x in (*history, before_id)),
        has_prev=before_id != 0,
        prev_before_id=history[-1] if history else 0,
        prev_history=",".join(str(x) for x in history[:-1]),
        can_filter=can_filter, users=[u for u in hannah.get_users() if u.active] if can_filter else [],
        filter_user_id=filter_user_id,
    )


@bp.route("/activity-log/<int:entry_id>/audio")
@login_required
def activity_log_audio(entry_id: int):
    hannah = get_hannah()
    pcm, sample_rate = hannah.stream_activity_audio(requestor_id=session["user_id"], activity_log_id=entry_id)
    if not pcm:
        abort(404)
    return Response(_build_wav(pcm, sample_rate), mimetype="audio/wav")
