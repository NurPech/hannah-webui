from flask import Blueprint, render_template

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required

bp = Blueprint("rooms", __name__)


@bp.route("/rooms")
@login_required
@trust_level_required(TRUST_LEVELS["list_rooms"])
def rooms():
    hannah = get_hannah()
    all_rooms = hannah.get_rooms()
    all_groups = hannah.get_groups()
    room_groups: dict[str, list[str]] = {r.room_id: [] for r in all_rooms}
    for g in all_groups:
        for r in g.rooms:
            if r.room_id in room_groups:
                room_groups[r.room_id].append(g.display_name)
    return render_template("rooms.html", rooms=all_rooms, room_groups=room_groups)
