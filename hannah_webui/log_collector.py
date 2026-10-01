"""Synchronous gRPC client for the Hannah log collector (LogService, logging.proto).

The collector is not part of Hannah Core: Core only announces where it runs, and the
address comes from the log shipping's discovery (hannah_grpc.logging's
LogShipping.collector_address). Used for the log bundle export (#66) — a rare admin
action, so every request opens its own short-lived channel instead of keeping one.

Calls go to hannah.v2.LogService; a collector too old for it gets them on hannah.v1.LogService
instead (N−1), probed per channel with GetSources (#71). The two generations have their own
message classes, so each call uses the ones of the generation in use.
"""
from __future__ import annotations

from typing import Iterable, Iterator

import grpc
from hannah_grpc import client as hannah_client
from hannah_proto.v1 import logging_pb2 as logging_v1_pb2, shared_pb2 as shared_v1_pb2
from hannah_proto.v2 import logging_pb2, shared_pb2

GET_SOURCES_TIMEOUT_S = 5.0

LOG_SERVICE = logging_pb2.DESCRIPTOR.services_by_name["LogService"]
PREVIOUS_LOG_SERVICE = logging_v1_pb2.DESCRIPTOR.services_by_name["LogService"]


class LogCollectorClient:
    def __init__(self, address: str) -> None:
        self.address = address
        self._channel = grpc.intercept_channel(grpc.insecure_channel(address), *hannah_client.sync_interceptors())
        self._stubs = hannah_client.SyncVersionedStub(
            self._channel, LOG_SERVICE, PREVIOUS_LOG_SERVICE,
            probe_method="GetSources", peer="the log collector",
        )

    def close(self) -> None:
        self._channel.close()

    def _messages(self):
        """The message classes of the generation in use (resolve() decides it first)."""
        return (logging_v1_pb2, shared_v1_pb2) if self._stubs.previous else (logging_pb2, shared_pb2)

    def get_sources(self) -> list["logging_pb2.LogSource"]:
        stub = self._stubs.resolve()
        _, shared = self._messages()
        return list(stub.GetSources(shared.Empty(), timeout=GET_SOURCES_TIMEOUT_S).sources)

    def export(
        self, components: Iterable[str] = (), exclude_categories: Iterable[int] = (),
        since_ms: int = 0, until_ms: int = 0,
    ) -> Iterator[bytes]:
        """tar.gz archive as a sequence of chunks, to be concatenated in order."""
        stub = self._stubs.resolve()
        logging, _ = self._messages()
        request = logging.ExportRequest(
            components=list(components), exclude_categories=list(exclude_categories),
            since_ms=since_ms, until_ms=until_ms,
        )
        for chunk in stub.Export(request):
            yield chunk.data
