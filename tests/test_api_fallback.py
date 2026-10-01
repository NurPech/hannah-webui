"""#71: the WebUI works with hannah.v2 types and falls back to hannah.v1 (N−1) when Core or the
log collector is too old for hannah.v2; on that path Core calls are translated, so the WebUI
code only ever sees hannah.v2 messages. Real in-process gRPC servers."""
from concurrent import futures

import grpc
import pytest
from hannah_proto.v1 import hannah_pb2 as v1_pb2, hannah_pb2_grpc as v1_pb2_grpc
from hannah_proto.v1 import logging_pb2 as v1_logging_pb2, logging_pb2_grpc as v1_logging_pb2_grpc
from hannah_proto.v2 import hannah_pb2, hannah_pb2_grpc, logging_pb2, logging_pb2_grpc

from hannah_webui.grpc_client import HannahClient
from hannah_webui.log_collector import LogCollectorClient

CASES = [
    (True, False, "v2"),       # server that dropped N−1
    (False, True, "v1"),       # server too old for hannah.v2
    (True, True, "v2"),        # today's server: serves both, v2 wins
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


@pytest.mark.parametrize("v2, v1, expected", CASES)
def test_core_calls_go_to_the_right_path(v2, v1, expected):
    hits = []

    def register(server):
        if v2:
            hannah_pb2_grpc.add_HannahServiceServicer_to_server(_core_servicer(hannah_pb2, hannah_pb2_grpc, "v2", hits), server)
        if v1:
            v1_pb2_grpc.add_HannahServiceServicer_to_server(_core_servicer(v1_pb2, v1_pb2_grpc, "v1", hits), server)

    server, port = _start(register)
    client = HannahClient("localhost", port)
    client.connect()
    try:
        rooms = client.get_rooms()
        assert [r.display_name for r in rooms] == [expected]
        # Also on the N−1 path the caller gets hannah.v2 messages
        assert isinstance(rooms[0], hannah_pb2.Room)
        [(tag, metadata)] = hits
        assert tag == expected
        assert "x-proto-version" in metadata
        assert "x-compat-version" in metadata
    finally:
        client.close()
        server.stop(None)


def test_devices_of_a_hannah_v1_core_arrive_as_typed_slots_without_identifier():
    """A Core too old for hannah.v2 describes devices by state keys; the translation turns them
    into a class and slots, which carry no identifier (only a hannah.v2 Core can name one)."""
    class Servicer(v1_pb2_grpc.HannahServiceServicer):
        def GetSatellites(self, request, context):
            return v1_pb2.GetSatellitesResponse()

        def GetDevices(self, request, context):
            return v1_pb2.GetDevicesResponse(rooms=[v1_pb2.RoomInfo(key="wz", name="Wohnzimmer", devices=[
                v1_pb2.DeviceInfo(
                    id="javascript.0.virtualDevice.Licht.Decke", name="Decke", category="light",
                    states=["on"], current={"on": "true"}, state_types={"on": v1_pb2.StateType.BOOLEAN},
                    state_writable={"on": True},
                ),
            ])])

    server, port = _start(lambda s: v1_pb2_grpc.add_HannahServiceServicer_to_server(Servicer(), s))
    client = HannahClient("localhost", port)
    client.connect()
    try:
        [room] = client.get_devices()
        [device] = room.devices
        assert device.device_class == hannah_pb2.DEVICE_CLASS_LIGHT
        [slot] = device.slots
        assert (slot.slot_id, slot.kind, slot.writable, slot.value.boolean) == ("on", hannah_pb2.SLOT_KIND_ON, True, True)
        assert slot.identifier == ""
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


@pytest.mark.parametrize("v2, v1, expected", CASES)
def test_collector_calls_go_to_the_right_path(v2, v1, expected):
    hits = []

    def register(server):
        if v2:
            logging_pb2_grpc.add_LogServiceServicer_to_server(_collector_servicer(logging_pb2, logging_pb2_grpc, "v2", hits), server)
        if v1:
            v1_logging_pb2_grpc.add_LogServiceServicer_to_server(
                _collector_servicer(v1_logging_pb2, v1_logging_pb2_grpc, "v1", hits), server)

    server, port = _start(register)
    client = LogCollectorClient(f"localhost:{port}")
    try:
        assert [s.component for s in client.get_sources()] == [expected]
        assert b"".join(client.export()) == expected.encode()
        # The probe itself calls GetSources on the hannah.v2 path; every served call is on `expected`.
        assert set(hits) == {expected}
    finally:
        client.close()
        server.stop(None)
