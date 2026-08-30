from concurrent import futures

import grpc
import pytest
from hannah_proto import hannah_pb2, hannah_pb2_grpc

from hannah_webui.grpc_client import HannahClient


class _LoginServicer(hannah_pb2_grpc.HannahServiceServicer):
    """Mimics Core rejecting bad credentials with a gRPC-level UNAUTHENTICATED
    status (hannah-webui#51) rather than resp.found=False."""

    def Login(self, request, context):
        if request.username == "known" and request.password == "correct":
            return hannah_pb2.UserResponse(found=True, user=hannah_pb2.User(id=1, user_name="known"))
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Ungültige Zugangsdaten.")

    def GetRooms(self, request, context):
        context.abort(grpc.StatusCode.UNAVAILABLE, "down for maintenance")


@pytest.fixture
def login_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    hannah_pb2_grpc.add_HannahServiceServicer_to_server(_LoginServicer(), server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    client = HannahClient("localhost", port)
    client.connect()
    yield client
    server.stop(None)


def test_login_unknown_username_reports_not_found_instead_of_raising(login_server):
    found, user = login_server.login("nobody", "whatever")
    assert (found, user) == (False, None)


def test_login_wrong_password_for_known_user_reports_not_found_instead_of_raising(login_server):
    found, user = login_server.login("known", "wrong")
    assert (found, user) == (False, None)


def test_login_correct_credentials_still_succeed(login_server):
    found, user = login_server.login("known", "correct")
    assert found is True
    assert user.user_name == "known"


def test_login_other_rpc_errors_still_propagate(login_server):
    with pytest.raises(grpc.RpcError) as exc_info:
        login_server.get_rooms()
    assert exc_info.value.code() == grpc.StatusCode.UNAVAILABLE
