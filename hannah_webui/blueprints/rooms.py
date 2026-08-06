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
        # A room "belongs to" a group if any of the group's satellites currently sits in it —
        # groups reference satellites directly now (#56/hannah-proto#7), not rooms.
        group_room_ids = {s.room_id for s in g.satellites if s.room_id}
        for room_id in group_room_ids:
            if room_id in room_groups:
                room_groups[room_id].append(g.display_name)
    return render_template("rooms.html", rooms=all_rooms, room_groups=room_groups)
