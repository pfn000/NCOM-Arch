"""JSON-lines client for the NCOM Arch protocol.

- `ncomd --listen 127.0.0.1:47820` (any OS): `Client.tcp("127.0.0.1", 47820)`
- the Windows shell service (NcomArch.Shell): `Client.pipe()` opens \\.\pipe\ncom-arch
"""
from __future__ import annotations

import json
import socket
from typing import Any, BinaryIO, Optional

DEFAULT_PORT = 47820
PIPE_NAME = "ncom-arch"


class ProtocolError(RuntimeError):
    pass


class Client:
    def __init__(self, stream: BinaryIO, sock: Optional[socket.socket] = None):
        self._f = stream
        self._sock = sock

    @classmethod
    def tcp(cls, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 5.0) -> "Client":
        s = socket.create_connection((host, port), timeout=timeout)
        return cls(s.makefile("rwb"), s)

    @classmethod
    def pipe(cls, name: str = PIPE_NAME) -> "Client":
        return cls(open(rf"\\.\pipe\{name}", "r+b", buffering=0))

    def call(self, request: dict[str, Any]) -> dict[str, Any]:
        self._f.write((json.dumps(request) + "\n").encode("utf-8"))
        self._f.flush()
        line = self._f.readline()
        if not line:
            raise ProtocolError("connection closed")
        resp = json.loads(line)
        if not resp.get("ok"):
            raise ProtocolError(resp.get("error", "unknown error"))
        return resp

    def close(self) -> None:
        try:
            self._f.close()
        finally:
            if self._sock:
                self._sock.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
