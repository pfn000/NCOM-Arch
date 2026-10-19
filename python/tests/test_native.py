"""Python <-> Rust core over the C ABI. Skipped when the library isn't built (CI builds it)."""
import pytest
from ncom_arch.native import Core, NativeError, find_library
from ncom_arch.spec import Rect, Point, anatomy, hit_test

pytestmark = pytest.mark.skipif(find_library() is None, reason="native library not built (set NCOM_ARCH_LIB)")

G0 = Rect(95, 64, 410, 232)


def test_hello():
    with Core() as c:
        r = c.call({"cmd": "hello"})["result"]
        assert r["protocol"] == 1 and r["version"] == c.version
        assert c.abi_version == 1


def test_python_spec_and_rust_core_agree():
    with Core() as c:
        c.call({"cmd": "open", "title": "Notes", "rect": {"x": G0.x, "y": G0.y, "w": G0.w, "h": G0.h}})
        # walk a grid over the window and compare every hit
        mismatches = []
        for x in range(int(G0.x) - 4, int(G0.right) + 4, 3):
            for y in range(int(G0.y) - 4, int(G0.bottom) + 4, 3):
                py = hit_test(G0, Point(x, y))
                rs = c.hit_test(x, y)
                if (py is None) != (rs is None) or (rs and rs[1] != py):
                    mismatches.append((x, y, py, rs))
        assert not mismatches, mismatches[:10]


def test_pill_swipe_minimizes_through_the_core():
    with Core() as c:
        wid = c.call({"cmd": "open", "title": "Notes", "rect": {"x": 95, "y": 64, "w": 410, "h": 232}})["result"]["id"]
        p = anatomy(G0).pill.center()
        c.call({"cmd": "pointer", "kind": "down", "x": p.x, "y": p.y, "t_ms": 0})
        ev = c.call({"cmd": "pointer", "kind": "up", "x": p.x, "y": p.y + 30, "t_ms": 120})["events"]
        assert ev[0] == {"event": "minimized", "id": wid}


def test_errors_raise():
    with Core() as c:
        with pytest.raises(NativeError, match="no window"):
            c.call({"cmd": "close", "id": 99})
