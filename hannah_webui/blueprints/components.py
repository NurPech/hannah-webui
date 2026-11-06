from datetime import datetime

from flask import Blueprint, render_template

from hannah_webui.extensions import TRUST_LEVELS, get_hannah, login_required, trust_level_required
from hannah_webui.route_helpers import group_components

bp = Blueprint("components", __name__)


@bp.route("/components")
@login_required
@trust_level_required(TRUST_LEVELS["list_components"])
def components():
    info = get_hannah().get_component_versions()
    checked_at = None
    if info is not None and info.latest_available and info.latest_checked_at:
        checked_at = datetime.fromtimestamp(info.latest_checked_at).strftime("%d.%m.%Y %H:%M")
    return render_template(
        "components.html",
        # None = Core cannot tell (hannah.v1-only or without the RPC): a hint, not an error
        info=info,
        components=group_components(info.components) if info else [],
        checked_at=checked_at,
    )
