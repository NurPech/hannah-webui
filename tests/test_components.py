"""#76: component versions page and update banner."""
import re
from concurrent import futures

import grpc
from hannah_proto.v1 import hannah_pb2 as v1_pb2, hannah_pb2_grpc as v1_pb2_grpc
from hannah_proto.v2 import hannah_pb2, hannah_pb2_grpc

from hannah_webui import extensions
from hannah_webui.grpc_client import HannahClient
from hannah_webui.route_helpers import display_version, group_components

UP_TO_DATE = hannah_pb2.VERSION_COMPARISON_UP_TO_DATE
UPDATE = hannah_pb2.VERSION_COMPARISON_UPDATE_AVAILABLE
NEWER = hannah_pb2.VERSION_COMPARISON_NEWER_THAN_PUBLIC


def _response(*components, latest_available=True):
    return hannah_pb2.GetComponentVersionsResponse(
        components=[
            hannah_pb2.ComponentVersionInfo(
                component=name, instance_id=f"{name}-1", version=version, latest_version=latest, comparison=comparison,
            )
            for name, version, latest, comparison in components
        ],
        latest_available=latest_available, latest_checked_at=1782000000 if latest_available else 0,
    )


def _start(register):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    register(server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    return server, port


class TestDisplayVersion:
    def test_strips_a_leading_v_before_a_digit(self):
        assert display_version("v0.102.6") == "0.102.6"
        assert display_version("v2.15.0-rc1") == "2.15.0-rc1"

    def test_leaves_everything_else_alone(self):
        for version in ("0.102.6", "vnext", "dev", "", "V1.0.0", "1.0.0v2"):
            assert display_version(version) == version

    def test_page_and_banner_show_versions_without_the_v(self, admin_client, hannah):
        hannah.component_versions = _response(("core", "0.102.6", "v0.102.10", UPDATE))
        page = admin_client.get("/components").get_data(as_text=True)
        assert "0.102.10" in page and "v0.102.10" not in page
        banner = admin_client.get("/me").get_data(as_text=True)
        assert "core 0.102.6 → 0.102.10" in banner and "v0.102.10" not in banner


def _info(component, instance, version="1.0.0", latest="1.0.0", comparison=UP_TO_DATE):
    return hannah_pb2.ComponentVersionInfo(
        component=component, instance_id=instance, version=version, latest_version=latest, comparison=comparison,
    )


class TestGroupedEntries:
    def test_group_components_counts_identical_entries_and_sorts(self):
        grouped = group_components([_info("webui", "h1"), _info("core", "h1"), _info("webui", "h1")])
        assert [(c.component, n) for c, n in grouped] == [("core", 1), ("webui", 2)]

    def test_entries_differing_in_version_or_status_stay_apart(self):
        grouped = group_components([
            _info("webui", "h1", "2.15.0"), _info("webui", "h1", "2.15.1"),
            _info("webui", "h1", "2.15.0", comparison=UPDATE),
        ])
        assert [n for _, n in grouped] == [1, 1, 1]

    def test_page_shows_identical_entries_once_with_a_count(self, admin_client, hannah):
        hannah.component_versions = hannah_pb2.GetComponentVersionsResponse(
            latest_available=True, latest_checked_at=1782000000,
            components=[_info("webui", "nuc1"), _info("webui", "nuc1"), _info("core", "nuc1")],
        )
        body = admin_client.get("/components").get_data(as_text=True)
        assert body.count("border-b border-gray-800/60") == 2  # one row each for webui and core
        assert "×2" in body
        assert "×1" not in body

    def test_page_keeps_two_versions_of_the_same_host_as_two_rows(self, admin_client, hannah):
        hannah.component_versions = hannah_pb2.GetComponentVersionsResponse(
            latest_available=True, latest_checked_at=1782000000,
            components=[_info("webui", "nuc1", "2.15.0"), _info("webui", "nuc1", "2.15.1")],
        )
        body = admin_client.get("/components").get_data(as_text=True)
        assert body.count("border-b border-gray-800/60") == 2
        assert "×" not in body


class TestClient:
    def test_returns_the_response_of_a_core_that_has_the_rpc(self):
        class Servicer(hannah_pb2_grpc.HannahServiceServicer):
            def GetSatellites(self, request, context):
                return hannah_pb2.GetSatellitesResponse()

            def GetComponentVersions(self, request, context):
                return _response(("core", "2.14.1", "2.15.0", UPDATE))

        server, port = _start(lambda s: hannah_pb2_grpc.add_HannahServiceServicer_to_server(Servicer(), s))
        client = HannahClient("localhost", port)
        client.connect()
        try:
            [c] = client.get_component_versions().components
            assert (c.component, c.version, c.latest_version, c.comparison) == ("core", "2.14.1", "2.15.0", UPDATE)
        finally:
            client.close()
            server.stop(None)

    def test_core_on_v2_without_the_rpc_means_no_version_info(self):
        class Servicer(hannah_pb2_grpc.HannahServiceServicer):
            def GetSatellites(self, request, context):
                return hannah_pb2.GetSatellitesResponse()

        server, port = _start(lambda s: hannah_pb2_grpc.add_HannahServiceServicer_to_server(Servicer(), s))
        client = HannahClient("localhost", port)
        client.connect()
        try:
            assert client.get_component_versions() is None
        finally:
            client.close()
            server.stop(None)

    def test_core_that_only_serves_v1_means_no_version_info(self):
        class Servicer(v1_pb2_grpc.HannahServiceServicer):
            def GetSatellites(self, request, context):
                return v1_pb2.GetSatellitesResponse()

        server, port = _start(lambda s: v1_pb2_grpc.add_HannahServiceServicer_to_server(Servicer(), s))
        client = HannahClient("localhost", port)
        client.connect()
        try:
            assert client.get_component_versions() is None
        finally:
            client.close()
            server.stop(None)


class TestPage:
    def test_lists_instances_with_versions_and_status(self, admin_client, hannah):
        hannah.component_versions = _response(
            ("core", "2.14.1", "2.15.0", UPDATE), ("telegram", "1.3.0", "1.3.0", UP_TO_DATE),
        )
        body = admin_client.get("/components").get_data(as_text=True)
        assert "core-1" in body and "2.14.1" in body and "2.15.0" in body
        assert "Update verfügbar" in body
        assert "aktuell" in body
        assert "Öffentliche Versionen Stand" in body

    def test_requires_trust_level_10(self, logged_in_client):
        resp = logged_in_client.get("/components", follow_redirects=True)
        assert "Zugriff verweigert" in resp.get_data(as_text=True)

    def test_core_without_version_info_shows_a_hint_not_an_error(self, admin_client, hannah):
        hannah.component_versions = None
        resp = admin_client.get("/components")
        assert resp.status_code == 200
        assert "keine Versionsinformationen" in resp.get_data(as_text=True)

    def test_without_public_versions_only_running_versions_are_shown(self, admin_client, hannah):
        # Even a stale comparison on the wire must not turn into a status
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE), latest_available=False)
        body = admin_client.get("/components").get_data(as_text=True)
        assert "2.14.1" in body
        assert "2.15.0" not in body
        assert "Update verfügbar" not in body
        assert "nicht abrufbar" in body
        assert "Öffentliche Versionen Stand" not in body

    def test_component_newer_than_public_is_shown_neutral(self, admin_client, hannah):
        hannah.component_versions = _response(("core", "2.16.0-rc1", "2.15.0", NEWER))
        body = admin_client.get("/components").get_data(as_text=True)
        assert "neuer als öffentlich" in body
        assert "text-amber-300" not in body

    def test_version_number_links_to_the_page_for_admins_only(self, admin_client):
        body = admin_client.get("/me").get_data(as_text=True)
        assert re.search(r'<a href="/components"[^>]*>\s*dev\s*</a>', body)
        admin_client.get("/logout")
        admin_client.post("/login", data={"username": "claude", "password": "claude"})
        body = admin_client.get("/me").get_data(as_text=True)
        assert 'href="/components"' not in body
        assert "WebUI-Version" in body  # still shown, as plain text

    def test_no_menu_entry_and_logo_still_links_to_the_start_page(self, admin_client):
        body = admin_client.get("/me").get_data(as_text=True)
        assert "Komponenten</a>" not in body
        assert re.search(r'<a href="/"[^>]*>\s*<span[^>]*></span>\s*<span[^>]*>Hannah</span>\s*</a>', body)

    def test_version_number_is_highlighted_on_the_page(self, admin_client):
        on_page = admin_client.get("/components").get_data(as_text=True)
        elsewhere = admin_client.get("/me").get_data(as_text=True)
        pattern = r'<a href="/components"[^>]*class="([^"]*)"[^>]*>\s*dev\s*</a>'
        assert "bg-gray-800" in re.search(pattern, on_page).group(1)
        assert "bg-gray-800" not in re.search(pattern, elsewhere).group(1)


class TestBanner:
    def test_shown_to_admins_when_an_update_is_available(self, admin_client, hannah):
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE), ("telegram", "1.3.0", "1.3.0", UP_TO_DATE))
        body = admin_client.get("/me").get_data(as_text=True)
        assert "Update verfügbar:" in body
        assert "core 2.14.1 → 2.15.0" in body
        assert "telegram 1.3.0" not in body

    def test_instances_with_the_same_outdated_version_are_named_once(self, admin_client, hannah):
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE), ("core", "2.14.1", "2.15.0", UPDATE))
        assert admin_client.get("/me").get_data(as_text=True).count("core 2.14.1 → 2.15.0") == 1

    def test_not_shown_without_an_update(self, admin_client):
        assert "Update verfügbar:" not in admin_client.get("/me").get_data(as_text=True)

    def test_not_shown_for_newer_than_public_or_without_public_versions(self, admin_client, hannah):
        hannah.component_versions = _response(("core", "2.16.0", "2.15.0", NEWER))
        assert "Update verfügbar:" not in admin_client.get("/me").get_data(as_text=True)
        extensions_cache_reset(admin_client)
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE), latest_available=False)
        assert "Update verfügbar:" not in admin_client.get("/me").get_data(as_text=True)

    def test_not_shown_to_regular_users(self, logged_in_client, hannah):
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE))
        assert "Update verfügbar:" not in logged_in_client.get("/me").get_data(as_text=True)

    def test_core_without_version_info_means_no_banner_and_no_error(self, admin_client, hannah):
        hannah.component_versions = None
        resp = admin_client.get("/me")
        assert resp.status_code == 200
        assert "Update verfügbar:" not in resp.get_data(as_text=True)

    def test_unreachable_core_does_not_break_pages(self, admin_client, hannah, monkeypatch):
        def boom():
            raise grpc.RpcError()
        monkeypatch.setattr(hannah, "get_component_versions", boom)
        resp = admin_client.get("/me")
        assert resp.status_code == 200
        assert "Update verfügbar:" not in resp.get_data(as_text=True)

    def test_lookup_is_cached_between_requests(self, admin_client, hannah, monkeypatch):
        calls = []
        original = hannah.get_component_versions
        monkeypatch.setattr(hannah, "get_component_versions", lambda: calls.append(1) or original())
        admin_client.get("/me")
        admin_client.get("/me")
        assert len(calls) == 1

    def test_lookup_is_refreshed_after_the_ttl(self, admin_client, hannah, monkeypatch):
        admin_client.get("/me")
        hannah.component_versions = _response(("core", "2.14.1", "2.15.0", UPDATE))
        assert "Update verfügbar:" not in admin_client.get("/me").get_data(as_text=True)  # still cached
        monkeypatch.setattr(extensions, "_COMPONENT_UPDATES_TTL_S", 0)
        assert "Update verfügbar:" in admin_client.get("/me").get_data(as_text=True)


def extensions_cache_reset(client):
    client.application.extensions.pop("component_updates_cache", None)
