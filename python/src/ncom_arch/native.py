"""ctypes bindings to the Rust core (crates/ncom-ffi -> ncom_arch.dll / libncom_arch.so)."""
from __future__ import annotations

import ctypes
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from .spec import PARTS


def _lib_names() -> list[str]:
    if sys.platform == "win32":
        return ["ncom_arch.dll"]
    if sys.platform == "darwin":
        return ["libncom_arch.dylib"]
    return ["libncom_arch.so"]


def find_library() -> Optional[str]:
    """NCOM_ARCH_LIB, else target/release or target/debug above the current directory."""
    env = os.environ.get("NCOM_ARCH_LIB")
    if env:
        return env if Path(env).exists() else None
    here = Path.cwd().resolve()
    for base in [here, *here.parents]:
        for prof in ("release", "debug"):
            for n in _lib_names():
                p = base / "target" / prof / n
                if p.exists():
                    return str(p)
    return None


class NativeError(RuntimeError):
    pass


class Core:
    """One window-system session inside the native library."""

    def __init__(self, width: float = 0, height: float = 0, lib_path: Optional[str] = None):
        path = lib_path or find_library()
        if not path:
            raise NativeError("ncom_arch native library not found (build crates/ncom-ffi or set NCOM_ARCH_LIB)")
        lib = ctypes.CDLL(path)
        lib.ncom_version.restype = ctypes.c_char_p
        lib.ncom_abi_version.restype = ctypes.c_uint32
        lib.ncom_session_new.argtypes = [ctypes.c_double, ctypes.c_double]
        lib.ncom_session_new.restype = ctypes.c_void_p
        lib.ncom_session_free.argtypes = [ctypes.c_void_p]
        lib.ncom_session_call.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.ncom_session_call.restype = ctypes.c_void_p
        lib.ncom_string_free.argtypes = [ctypes.c_void_p]
        lib.ncom_hit_test.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]
        lib.ncom_hit_test.restype = ctypes.c_int32
        self._lib = lib
        self.path = path
        self._h = lib.ncom_session_new(float(width), float(height))
        if not self._h:
            raise NativeError("ncom_session_new returned NULL")

    @property
    def version(self) -> str:
        return self._lib.ncom_version().decode()

    @property
    def abi_version(self) -> int:
        return int(self._lib.ncom_abi_version())

    def call_json(self, request: str) -> str:
        if not self._h:
            raise NativeError("session is closed")
        p = self._lib.ncom_session_call(self._h, request.encode("utf-8"))
        try:
            return ctypes.string_at(p).decode("utf-8")
        finally:
            self._lib.ncom_string_free(p)

    def call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request; raises NativeError when the core answers ok:false."""
        resp = json.loads(self.call_json(json.dumps(request)))
        if not resp.get("ok"):
            raise NativeError(resp.get("error", "unknown error"))
        return resp

    def hit_test(self, x: float, y: float) -> Optional[tuple[int, str]]:
        wid, part = ctypes.c_uint32(), ctypes.c_uint32()
        if self._lib.ncom_hit_test(self._h, x, y, ctypes.byref(wid), ctypes.byref(part)):
            return wid.value, PARTS[part.value]
        return None

    def close(self) -> None:
        if self._h:
            self._lib.ncom_session_free(self._h)
            self._h = None

    def __enter__(self) -> "Core":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
