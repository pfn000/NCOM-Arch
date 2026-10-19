"""The approved NCOM Arch window anatomy, in pure Python.

Mirrors crates/ncom-core/src/anatomy.rs. Numbers come from the README's
"Window anatomy (approved spec)":

- window: 24px corner radius
- corner arc: 90° on the top-right curve only, concentric, inset 7px, 6px thick, round caps
- pill: 28 x 6 px on the same line as the arc's top end, 13px gap
- •••: centered on the top frame, level with the pill and the arc's top
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Optional

CORNER_RADIUS = 24.0
ARC_INSET = 7.0
ARC_THICKNESS = 6.0
ARC_RADIUS = CORNER_RADIUS - ARC_INSET
PILL_W = 28.0
PILL_H = 6.0
PILL_GAP = 13.0
CONTROL_LINE = ARC_INSET
DOTS_SPACING = 9.0
TOUCH_SLOP = 10.0
RESIZE_ZONE = 28.0

PARTS = ("content", "corner_arc", "pill", "dots", "resize_corner")  # index = native part code


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def dist(self, o: "Point") -> float:
        return math.hypot(self.x - o.x, self.y - o.y)


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def center(self) -> Point:
        return Point(self.x + self.w / 2, self.y + self.h / 2)

    def contains(self, p: Point) -> bool:
        return self.x <= p.x < self.right and self.y <= p.y < self.bottom

    def inflate(self, dx: float, dy: float) -> "Rect":
        return Rect(self.x - dx, self.y - dy, self.w + 2 * dx, self.h + 2 * dy)

    @classmethod
    def parse(cls, s: str) -> "Rect":
        x, y, w, h = (float(v) for v in s.split(","))
        return cls(x, y, w, h)


@dataclass(frozen=True)
class Anatomy:
    arc_center: Point
    arc_top: Point
    pill: Rect
    dots_center: Point
    dots: tuple
    resize_handle: Point

    def to_dict(self) -> dict:
        return asdict(self)


def anatomy(win: Rect) -> Anatomy:
    arc_center = Point(win.right - CORNER_RADIUS, win.y + CORNER_RADIUS)
    arc_top = Point(arc_center.x, win.y + CONTROL_LINE)
    pill_right = arc_top.x - ARC_THICKNESS / 2 - PILL_GAP
    pill = Rect(pill_right - PILL_W, win.y + CONTROL_LINE - PILL_H / 2, PILL_W, PILL_H)
    dc = Point(win.x + win.w / 2, win.y + CONTROL_LINE)
    dots = (Point(dc.x - DOTS_SPACING, dc.y), dc, Point(dc.x + DOTS_SPACING, dc.y))
    return Anatomy(arc_center, arc_top, pill, dc, dots, Point(win.right - 9, win.bottom - 9))


def _in_cut_corner(win: Rect, p: Point) -> bool:
    r = CORNER_RADIUS
    if p.x < win.x + r:
        cx = win.x + r
    elif p.x > win.right - r:
        cx = win.right - r
    else:
        return False
    if p.y < win.y + r:
        cy = win.y + r
    elif p.y > win.bottom - r:
        cy = win.bottom - r
    else:
        return False
    return p.dist(Point(cx, cy)) > r


def hit_test(win: Rect, p: Point) -> Optional[str]:
    """Which part of `win` the point lands on, or None (same rules as the Rust core)."""
    if not win.contains(p):
        return None
    a = anatomy(win)
    d = p.dist(a.arc_center)
    if p.x >= a.arc_center.x - 2 and p.y <= a.arc_center.y + 2 and abs(d - ARC_RADIUS) <= ARC_THICKNESS / 2 + TOUCH_SLOP:
        return "corner_arc"
    if _in_cut_corner(win, p):
        return None
    if a.pill.inflate(8, TOUCH_SLOP).contains(p):
        return "pill"
    if abs(p.x - a.dots_center.x) <= 20 and abs(p.y - a.dots_center.y) <= PILL_H / 2 + TOUCH_SLOP:
        return "dots"
    if p.x >= win.right - RESIZE_ZONE and p.y >= win.bottom - RESIZE_ZONE:
        return "resize_corner"
    return "content"


def renderer_controls(win: Rect) -> dict:
    """The control points the GIF renderer aims its finger at (render.scenes.geo_ctrl)."""
    return dict(
        arc=(win.right - 12, win.y + 12),
        pill=(win.right - 54, win.y + 7),
        dots=(win.x + win.w / 2, win.y + 7),
        corner=(win.right - 9, win.bottom - 9),
    )
