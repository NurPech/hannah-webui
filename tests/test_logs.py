"""Log bundle (#66): modal/nav gating, /logs/sources and /logs/export against a fake
log collector — no real collector or network needed."""
import grpc
import pytest
from hannah_proto import logging_pb2

from hannah_webui.extensions import get_log_collector
from hannah_webui.log_collector import LogCollectorClient


class FakeRpcError(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE

    def details(self):
        return "collector down"


class FakeLogCollector:
    def __init__(self):
        self.address = "collector:50060"
        self.sources = []
        self.chunks = [b"tar", b"gz"]
        self.fail = False
        self.export_kwargs = None
        self.closed = False

    def get_sources(self):
        if self.fail:
            raise FakeRpcError()
        return self.sources

    def export(self, **kwargs):
        self.export_kwargs = kwargs
        if self.fail:
            raise FakeRpcError()
        yield from self.chunks

    def close(self):
        self.closed = True


class FakeShipping:
    def __init__(self, collector_address):
        self.collector_address = collector_address


@pytest.fixture
def collector(app):
    fake = FakeLogCollector()
    app.extensions["log_collector"] = fake
    return fake


class TestNav:
    def test_admin_sees_button_and_modal(self, admin_client, collector):
        body = admin_client.get("/me").get_data(as_text=True)
        assert "data-open-log-bundle" in body
        assert 'id="log-bundle-modal"' in body

    def test_hidden_without_collector(self, admin_client, app):
        app.extensions["log_shipping"] = FakeShipping(None)
        body = admin_client.get("/me").get_data(as_text=True)
        assert "data-open-log-bundle" not in body
        assert "log-bundle-modal" not in body

    def test_shown_once_shipping_knows_a_collector(self, admin_client, app):
        app.extensions["log_shipping"] = FakeShipping("10.0.0.5:50060")
        body = admin_client.get("/me").get_data(as_text=True)
        assert "data-open-log-bundle" in body

    def test_regular_user_sees_neither(self, logged_in_client, collector):
        body = logged_in_client.get("/me").get_data(as_text=True)
        assert "data-open-log-bundle" not in body
        assert "log-bundle-modal" not in body


class TestSources:
    def test_requires_trust_level(self, logged_in_client, collector):
        resp = logged_in_client.get("/logs/sources")
        assert resp.status_code == 302

    def test_no_collector_known(self, admin_client, app):
        app.extensions["log_shipping"] = FakeShipping(None)
        resp = admin_client.get("/logs/sources")
        assert resp.status_code == 503
        assert "Log-Collector" in resp.get_json()["error"]

    def test_merges_instances_per_component(self, admin_client, collector):
        collector.sources = [
            logging_pb2.LogSource(component="webui", instance="b", oldest_ms=300, newest_ms=900, entries=5),
            logging_pb2.LogSource(component="core", instance="a", oldest_ms=100, newest_ms=500, entries=10),
            logging_pb2.LogSource(component="webui", instance="a", oldest_ms=200, newest_ms=800, entries=7),
        ]
        resp = admin_client.get("/logs/sources")
        assert resp.get_json()["components"] == [
            {"component": "core", "oldest_ms": 100, "newest_ms": 500, "entries": 10},
            {"component": "webui", "oldest_ms": 200, "newest_ms": 900, "entries": 12},
        ]
        assert collector.closed

    def test_collector_unreachable(self, admin_client, collector):
        collector.fail = True
        resp = admin_client.get("/logs/sources")
        assert resp.status_code == 502
        assert collector.closed


class TestExport:
    def test_requires_trust_level(self, logged_in_client, collector):
        resp = logged_in_client.post("/logs/export")
        assert resp.status_code == 302
        assert collector.export_kwargs is None

    def test_defaults_exclude_transcripts_and_metadata(self, admin_client, collector):
        resp = admin_client.post("/logs/export")
        assert resp.status_code == 200
        assert resp.mimetype == "application/gzip"
        assert resp.headers["Content-Disposition"].startswith('attachment; filename="hannah-logs-')
        assert resp.data == b"targz"
        assert collector.export_kwargs == {
            "components": [],
            "exclude_categories": [logging_pb2.LOG_CATEGORY_TRANSCRIPT, logging_pb2.LOG_CATEGORY_METADATA],
            "since_ms": 0, "until_ms": 0,
        }
        assert collector.closed

    def test_selection_is_passed_through(self, admin_client, collector):
        admin_client.post("/logs/export", data={
            "components": ["core", "webui"], "include_transcripts": "1", "include_metadata": "1",
            "since_ms": "1000", "until_ms": "2000",
        })
        assert collector.export_kwargs == {
            "components": ["core", "webui"], "exclude_categories": [],
            "since_ms": 1000, "until_ms": 2000,
        }

    @pytest.mark.parametrize("since, until", [("abc", ""), ("2000", "1000"), ("-5", "")])
    def test_invalid_range(self, admin_client, collector, since, until):
        resp = admin_client.post("/logs/export", data={"since_ms": since, "until_ms": until})
        assert resp.status_code == 400
        assert collector.export_kwargs is None

    def test_no_collector_known(self, admin_client, app):
        resp = admin_client.post("/logs/export")
        assert resp.status_code == 503

    def test_collector_error_before_first_chunk(self, admin_client, collector):
        collector.fail = True
        resp = admin_client.post("/logs/export")
        assert resp.status_code == 502
        assert "error" in resp.get_json()
        assert collector.closed


class TestGetLogCollector:
    def test_uses_address_from_log_shipping(self, app):
        app.extensions["log_shipping"] = FakeShipping("10.0.0.5:50060")
        with app.app_context():
            client = get_log_collector()
        try:
            assert isinstance(client, LogCollectorClient)
            assert client.address == "10.0.0.5:50060"
        finally:
            client.close()

    def test_none_without_shipping_or_address(self, app):
        with app.app_context():
            assert get_log_collector() is None
            app.extensions["log_shipping"] = FakeShipping(None)
            assert get_log_collector() is None
