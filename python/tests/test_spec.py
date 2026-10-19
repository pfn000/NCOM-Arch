import pytest
from ncom_arch.spec import (Rect, Point, anatomy, hit_test, renderer_controls,
                            ARC_RADIUS, ARC_THICKNESS, PILL_W, PILL_H, PILL_GAP)

G0 = Rect(95, 64, 410, 232)  # the demo window the GIFs use


def test_spec_numbers():
    a = anatomy(G0)
    assert ARC_RADIUS == 17
    assert a.arc_center == Point(G0.right - 24, G0.y + 24)
    assert a.arc_top.y == G0.y + 7
    assert (a.pill.w, a.pill.h) == (PILL_W, PILL_H) == (28, 6)
    assert a.arc_top.x - ARC_THICKNESS / 2 - a.pill.right == PILL_GAP == 13
    assert a.pill.center().y == a.arc_top.y == a.dots_center.y
    assert a.dots_center.x == G0.x + G0.w / 2


def test_renderer_targets_agree_with_spec():
    """The GIF renderer's finger targets land on the parts the spec says they do."""
    ctl = renderer_controls(G0)
    assert anatomy(G0).pill.center() == Point(*ctl["pill"])
    assert hit_test(G0, Point(*ctl["arc"])) == "corner_arc"
    assert hit_test(G0, Point(*ctl["pill"])) == "pill"
    assert hit_test(G0, Point(*ctl["dots"])) == "dots"
    assert hit_test(G0, Point(*ctl["corner"])) == "resize_corner"


def test_renderer_geo_ctrl_matches():
    from ncom_arch.render.scenes import geo_ctrl
    g = geo_ctrl((G0.x, G0.y, G0.w, G0.h))
    ctl = renderer_controls(G0)
    for k in ("pill", "dots", "corner"):
        assert tuple(g[k]) == pytest.approx(ctl[k])


@pytest.mark.parametrize("p,want", [
    (Point(300, 180), "content"),
    (Point(10, 10), None),
    (Point(G0.x + 1, G0.y + 1), None),          # rounded corner cut away
    (Point(G0.x + 1, G0.bottom - 1), None),
])
def test_hit_misc(p, want):
    assert hit_test(G0, p) == want
