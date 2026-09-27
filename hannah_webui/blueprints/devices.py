from flask import Blueprint, render_template

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import _device_overview_rooms

bp = Blueprint("devices", __name__)


@bp.route("/devices")
@login_required
@trust_level_required(TRUST_LEVELS["list_devices"])
def devices():
    hannah = get_hannah()
    rooms = _device_overview_rooms(hannah.get_devices())
    return render_template("devices.html", rooms=rooms)
