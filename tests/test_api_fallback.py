"""#67: the WebUI works with hannah.v1 types and falls back to the unversioned N−1 path
when Core or the log collector is too old for hannah.v1. Real in-process gRPC servers."""
from concurrent import futures

import grpc
import pytest
from hannah_proto import hannah_pb2 as legacy_pb2
from hannah_proto import hannah_pb2_grpc as legacy_pb2_grpc
from hannah_proto import logging_pb2 as legacy_logging_pb2
from hannah_proto import logging_pb2_grpc as legacy_logging_pb2_grpc
from hannah_proto.v1 import hannah_pb2, hannah_pb2_grpc, logging_pb2, logging_pb2_grpc

from hannah_webui.grpc_client import HannahClient
from hannah_webui.log_collector import LogCollectorClient

CASES = [
    (True, False, "v1"),       # server that dropped N−1
    (False, True, "legacy"),   # server too old for hannah.v1
    (True, True, "v1"),        # today's server: serves both, v1 wins
]


def _start(register):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    register(server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    return server, port


def _core_servicer(pb, pb_grpc, tag, hits):
    class Servicer(pb_grpc.HannahServiceServicer):
        def GetSatellites(self, request, context):
            return pb.GetSatellitesResponse()

        def GetRooms(self, request, context):
            hits.append((tag, dict(context.invocation_metadata())))
            return pb.GetRoomsResponse(rooms=[pb.Room(room_id="wz", display_name=tag)])

    return Servicer()


@pytest.mark.parametrize("v1, legacy, expected", CASES)
def test_core_calls_go_to_the_right_path(v1, legacy, expected):
    hits = []

    def register(server):
        if v1:
            hannah_pb2_grpc.add_HannahServiceServicer_to_server(_core_servicer(hannah_pb2, hannah_pb2_grpc, "v1", hits), server)
        if legacy:
            legacy_pb2_grpc.add_HannahServiceServicer_to_server(_core_servicer(legacy_pb2, legacy_pb2_grpc, "legacy", hits), server)

    server, port = _start(register)
    client = HannahClient("localhost", port)
    client.connect()
    try:
        rooms = client.get_rooms()
        assert [r.display_name for r in rooms] == [expected]
        assert isinstance(rooms[0], hannah_pb2.Room)
        [(tag, metadata)] = hits
        assert tag == expected
        assert "x-proto-version" in metadata
        assert "x-compat-version" in metadata
    finally:
        client.close()
        server.stop(None)


def _collector_servicer(pb, pb_grpc, tag, hits):
    class Servicer(pb_grpc.LogServiceServicer):
        def GetSources(self, request, context):
            hits.append(tag)
            return pb.GetSourcesResponse(sources=[pb.LogSource(component=tag)])

        def Export(self, request, context):
            hits.append(tag)
            yield pb.ExportChunk(data=tag.encode())

    return Servicer()


@pytest.mark.parametrize("v1, legacy, expected", CASES)
def test_collector_calls_go_to_the_right_path(v1, legacy, expected):
    hits = []

    def register(server):
        if v1:
            logging_pb2_grpc.add_LogServiceServicer_to_server(_collector_servicer(logging_pb2, logging_pb2_grpc, "v1", hits), server)
        if legacy:
            legacy_logging_pb2_grpc.add_LogServiceServicer_to_server(
                _collector_servicer(legacy_logging_pb2, legacy_logging_pb2_grpc, "legacy", hits), server)

    server, port = _start(register)
    client = LogCollectorClient(f"localhost:{port}")
    try:
        assert [s.component for s in client.get_sources()] == [expected]
        assert b"".join(client.export()) == expected.encode()
        # The probe itself calls GetSources on the v1 path; every served call is on `expected`.
        assert set(hits) == {expected}
    finally:
        client.close()
        server.stop(None)
