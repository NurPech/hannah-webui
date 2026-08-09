import os
from concurrent import futures
from unittest.mock import Mock

import grpc
import pytest
from hannah_proto import PROTO_VERSION, hannah_pb2, hannah_pb2_grpc
from hannah_proto.interceptor.compat_interceptor import COMPAT_VERSION_METADATA_KEY

from hannah_webui.grpc_client import HannahClient
from hannah_webui.grpc_interceptors import (
    PROTO_VERSION_METADATA_KEY,
    ProtocolVersionClientInterceptor,
    read_proto_version,
)

EXPECTED_VERSION = str(PROTO_VERSION)


class _FakeCallDetails:
    def __init__(self, method="/hannah.HannahService/SubmitText", metadata=None):
        self.method = method
        self.timeout = None
        self.metadata = metadata
        self.credentials = None
        self.wait_for_ready = None
        self.compression = None


def test_read_proto_version_matches_package():
    assert read_proto_version() == EXPECTED_VERSION


def test_intercept_unary_unary_adds_version_metadata():
    interceptor = ProtocolVersionClientInterceptor(EXPECTED_VERSION)
    continuation = Mock(return_value="call-result")
    details = _FakeCallDetails(metadata=[("existing", "1")])

    result = interceptor.intercept_unary_unary(continuation, details, "request")

    assert result == "call-result"
    continuation.assert_called_once()
    forwarded_details, forwarded_request = continuation.call_args[0]
    assert forwarded_request == "request"
    assert ("existing", "1") in forwarded_details.metadata
    assert (PROTO_VERSION_METADATA_KEY, EXPECTED_VERSION) in forwarded_details.metadata
    assert forwarded_details.method == details.method


def test_intercept_unary_unary_preserves_missing_metadata():
    interceptor = ProtocolVersionClientInterceptor(EXPECTED_VERSION)
    continuation = Mock(return_value="call-result")
    details = _FakeCallDetails(metadata=None)

    interceptor.intercept_unary_unary(continuation, details, "request")

    forwarded_details, _ = continuation.call_args[0]
    assert forwarded_details.metadata == [(PROTO_VERSION_METADATA_KEY, EXPECTED_VERSION)]


def test_intercept_unary_stream_adds_version_metadata():
    interceptor = ProtocolVersionClientInterceptor(EXPECTED_VERSION)
    continuation = Mock(return_value="stream-call")
    details = _FakeCallDetails(method="/hannah.HannahService/SubscribeEvents")

    result = interceptor.intercept_unary_stream(continuation, details, "request")

    assert result == "stream-call"
    forwarded_details, forwarded_request = continuation.call_args[0]
    assert forwarded_request == "request"
    assert (PROTO_VERSION_METADATA_KEY, EXPECTED_VERSION) in forwarded_details.metadata


def test_intercept_stream_unary_and_stream_stream_forward_request_iterator():
    interceptor = ProtocolVersionClientInterceptor(EXPECTED_VERSION)
    continuation = Mock(return_value="ok")
    details = _FakeCallDetails()
    request_iterator = iter(["a", "b"])

    interceptor.intercept_stream_unary(continuation, details, request_iterator)
    forwarded_details, forwarded_iter = continuation.call_args[0]
    assert forwarded_iter is request_iterator
    assert (PROTO_VERSION_METADATA_KEY, EXPECTED_VERSION) in forwarded_details.metadata

    continuation.reset_mock()
    interceptor.intercept_stream_stream(continuation, details, request_iterator)
    forwarded_details, forwarded_iter = continuation.call_args[0]
    assert forwarded_iter is request_iterator
    assert (PROTO_VERSION_METADATA_KEY, EXPECTED_VERSION) in forwarded_details.metadata


class _MetadataCapturingServicer(hannah_pb2_grpc.HannahServiceServicer):
    def __init__(self):
        self.received_metadata = None

    def GetRooms(self, request, context):
        self.received_metadata = dict(context.invocation_metadata())
        return hannah_pb2.GetRoomsResponse()


@pytest.fixture
def metadata_server():
    servicer = _MetadataCapturingServicer()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    hannah_pb2_grpc.add_HannahServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    yield servicer, port
    server.stop(None)


def test_connect_chains_proto_version_and_compat_version_interceptors(metadata_server):
    """connect() wires ProtocolVersionClientInterceptor and CompatVersionSyncClientInterceptor
    additively (hannah-proto#10/hannah#217, see grpc_client.py) — a real call must carry both
    x-proto-version and x-compat-version, not just whichever interceptor runs last."""
    servicer, port = metadata_server
    client = HannahClient("localhost", port)
    client.connect()

    client.get_rooms()

    assert servicer.received_metadata[PROTO_VERSION_METADATA_KEY] == EXPECTED_VERSION
    assert COMPAT_VERSION_METADATA_KEY in servicer.received_metadata
