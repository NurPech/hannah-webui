"""Synchronous gRPC client for the Hannah log collector (LogService, logging.proto).

The collector is not part of Hannah Core: Core only announces where it runs, and the
address comes from the log shipping's discovery (hannah_logging's
LogShipping.collector_address). Used for the log bundle export (#66) — a rare admin
action, so every request opens its own short-lived channel instead of keeping one.
"""
from __future__ import annotations

from typing import Iterable, Iterator

import grpc
from hannah_proto import logging_pb2, logging_pb2_grpc, shared_pb2
from hannah_proto.interceptor.compat_interceptor import CompatVersionSyncClientInterceptor

from hannah_webui.grpc_interceptors import ProtocolVersionClientInterceptor, read_proto_version

GET_SOURCES_TIMEOUT_S = 5.0


class LogCollectorClient:
    def __init__(self, address: str) -> None:
        self.address = address
        service = logging_pb2.DESCRIPTOR.services_by_name["LogService"]
        self._channel = grpc.intercept_channel(
            grpc.insecure_channel(address),
            ProtocolVersionClientInterceptor(read_proto_version()),
            CompatVersionSyncClientInterceptor(service),
        )
        self._stub = logging_pb2_grpc.LogServiceStub(self._channel)

    def close(self) -> None:
        self._channel.close()

    def get_sources(self) -> list["logging_pb2.LogSource"]:
        return list(self._stub.GetSources(shared_pb2.Empty(), timeout=GET_SOURCES_TIMEOUT_S).sources)

    def export(
        self, components: Iterable[str] = (), exclude_categories: Iterable[int] = (),
        since_ms: int = 0, until_ms: int = 0,
    ) -> Iterator[bytes]:
        """tar.gz archive as a sequence of chunks, to be concatenated in order."""
        request = logging_pb2.ExportRequest(
            components=list(components), exclude_categories=list(exclude_categories),
            since_ms=since_ms, until_ms=until_ms,
        )
        for chunk in self._stub.Export(request):
            yield chunk.data
