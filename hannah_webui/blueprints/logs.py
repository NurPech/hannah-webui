"""Log bundle (#66): tar.gz export from the log collector, requested from the modal in
base.html. Both routes answer the modal's fetch() calls — errors come back as JSON
{"error": ...} for the modal to show, not as a flash + redirect."""
import logging
from datetime import datetime

import grpc
from flask import Blueprint, Response, jsonify, request, stream_with_context
from hannah_proto import logging_pb2

from hannah_webui.extensions import TRUST_LEVELS, get_log_collector, login_required, trust_level_required

log = logging.getLogger(__name__)

bp = Blueprint("logs", __name__, url_prefix="/logs")

_NO_COLLECTOR = "Hannah meldet gerade keinen Log-Collector."
_COLLECTOR_UNREACHABLE = "Der Log-Collector ist nicht erreichbar."


@bp.route("/sources")
@login_required
@trust_level_required(TRUST_LEVELS["export_logs"])
def sources():
    collector = get_log_collector()
    if collector is None:
        return jsonify(error=_NO_COLLECTOR), 503
    try:
        raw = collector.get_sources()
    except grpc.RpcError as e:
        log.warning("Log collector at %s: GetSources failed: %s", collector.address, e)
        return jsonify(error=_COLLECTOR_UNREACHABLE), 502
    finally:
        collector.close()

    # One row per component; several instances of the same component are merged.
    components: dict[str, dict] = {}
    for s in raw:
        c = components.setdefault(s.component, {"component": s.component, "oldest_ms": 0, "newest_ms": 0, "entries": 0})
        c["oldest_ms"] = min(c["oldest_ms"], s.oldest_ms) if c["oldest_ms"] else s.oldest_ms
        c["newest_ms"] = max(c["newest_ms"], s.newest_ms)
        c["entries"] += s.entries
    return jsonify(components=sorted(components.values(), key=lambda c: c["component"]))


@bp.route("/export", methods=["POST"])
@login_required
@trust_level_required(TRUST_LEVELS["export_logs"])
def export():
    components = [c for c in request.form.getlist("components") if c]
    exclude_categories = []
    if not request.form.get("include_transcripts"):
        exclude_categories.append(logging_pb2.LOG_CATEGORY_TRANSCRIPT)
    if not request.form.get("include_metadata"):
        exclude_categories.append(logging_pb2.LOG_CATEGORY_METADATA)
    try:
        since_ms = int(request.form.get("since_ms") or 0)
        until_ms = int(request.form.get("until_ms") or 0)
    except ValueError:
        return jsonify(error="Ungültiger Zeitraum."), 400
    if since_ms < 0 or until_ms < 0 or (until_ms and since_ms >= until_ms):
        return jsonify(error="Ungültiger Zeitraum: „Von“ muss vor „Bis“ liegen."), 400

    collector = get_log_collector()
    if collector is None:
        return jsonify(error=_NO_COLLECTOR), 503

    chunks = collector.export(
        components=components, exclude_categories=exclude_categories,
        since_ms=since_ms, until_ms=until_ms,
    )
    # Pull the first chunk before answering, so a collector error still becomes a
    # proper error response instead of a broken download.
    try:
        first = next(chunks, b"")
    except grpc.RpcError as e:
        collector.close()
        log.warning("Log collector at %s: Export failed: %s", collector.address, e)
        return jsonify(error=_COLLECTOR_UNREACHABLE), 502

    def stream():
        try:
            yield first
            yield from chunks
        finally:
            collector.close()

    filename = f"hannah-logs-{datetime.now():%Y%m%d-%H%M%S}.tar.gz"
    return Response(
        stream_with_context(stream()), mimetype="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
