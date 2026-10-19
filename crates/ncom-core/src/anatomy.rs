//! The approved window anatomy (README, "Window anatomy (approved spec)") and hit testing.
//!
//! - Window: 24px corner radius.
//! - Corner arc: a short 90° arc on the top-right corner curve only, concentric with the
//!   24px radius, inset 7px, 6px thick, round caps.
//! - Pill: 28 × 6 px on the same line as the arc's top end, with a 13px gap.
//! - •••: centered on the top frame, level with the pill and the arc's top.
//! - Hidden resize corner: bottom-right, visible only while resizing.

use crate::geometry::{Point, Rect};
use serde::{Deserialize, Serialize};

pub const CORNER_RADIUS: f64 = 24.0;
pub const ARC_INSET: f64 = 7.0;
pub const ARC_THICKNESS: f64 = 6.0;
pub const ARC_RADIUS: f64 = CORNER_RADIUS - ARC_INSET;
pub const PILL_W: f64 = 28.0;
pub const PILL_H: f64 = 6.0;
pub const PILL_GAP: f64 = 13.0;
/// y offset (from the window top) of the shared control line: arc top end, pill, •••.
pub const CONTROL_LINE: f64 = ARC_INSET;
pub const DOTS_SPACING: f64 = 9.0;
pub const DOTS_RADIUS: f64 = 2.6;
/// Extra touch padding around the small controls.
pub const TOUCH_SLOP: f64 = 10.0;
/// Size of the hidden bottom-right resize zone.
pub const RESIZE_ZONE: f64 = 28.0;

/// Which part of a window a point lands on.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Part {
    CornerArc,
    Pill,
    Dots,
    ResizeCorner,
    Content,
}

/// Resolved control positions for one window rect.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct Anatomy {
    pub arc_center: Point,
    pub arc_radius: f64,
    pub arc_thickness: f64,
    /// The arc's top end (angle 270°), the point the control line runs through.
    pub arc_top: Point,
    pub pill: Rect,
    pub dots_center: Point,
    pub dots: [Point; 3],
    pub resize_handle: Point,
}

pub fn anatomy(win: &Rect) -> Anatomy {
    let arc_center = Point::new(win.right() - CORNER_RADIUS, win.y + CORNER_RADIUS);
    let arc_top = Point::new(arc_center.x, win.y + CONTROL_LINE);
    // The gap is measured from the arc's round cap, which reaches half the stroke past its end.
    let pill_right = arc_top.x - ARC_THICKNESS / 2.0 - PILL_GAP;
    let pill = Rect::new(pill_right - PILL_W, win.y + CONTROL_LINE - PILL_H / 2.0, PILL_W, PILL_H);
    let dots_center = Point::new(win.x + win.w / 2.0, win.y + CONTROL_LINE);
    let dots = [
        Point::new(dots_center.x - DOTS_SPACING, dots_center.y),
        dots_center,
        Point::new(dots_center.x + DOTS_SPACING, dots_center.y),
    ];
    Anatomy {
        arc_center,
        arc_radius: ARC_RADIUS,
        arc_thickness: ARC_THICKNESS,
        arc_top,
        pill,
        dots_center,
        dots,
        resize_handle: Point::new(win.right() - 9.0, win.bottom() - 9.0),
    }
}

/// True when `p` is inside `win` but cut away by one of its 24px rounded corners.
fn in_cut_corner(win: &Rect, p: Point) -> bool {
    let r = CORNER_RADIUS;
    let cx = if p.x < win.x + r {
        win.x + r
    } else if p.x > win.right() - r {
        win.right() - r
    } else {
        return false;
    };
    let cy = if p.y < win.y + r {
        win.y + r
    } else if p.y > win.bottom() - r {
        win.bottom() - r
    } else {
        return false;
    };
    p.dist(Point::new(cx, cy)) > r
}

/// Hit-test one window. `None` when the point misses the window's rounded shape.
pub fn hit_test(win: &Rect, p: Point) -> Option<Part> {
    if !win.contains(p) {
        return None;
    }
    let a = anatomy(win);
    // Corner arc: near the arc stroke, inside the top-right quadrant of the corner circle.
    let d = p.dist(a.arc_center);
    if p.x >= a.arc_center.x - 2.0
        && p.y <= a.arc_center.y + 2.0
        && (d - ARC_RADIUS).abs() <= ARC_THICKNESS / 2.0 + TOUCH_SLOP
    {
        return Some(Part::CornerArc);
    }
    if in_cut_corner(win, p) {
        return None;
    }
    if a.pill.inflate(8.0, TOUCH_SLOP).contains(p) {
        return Some(Part::Pill);
    }
    if (p.x - a.dots_center.x).abs() <= 20.0 && (p.y - a.dots_center.y).abs() <= PILL_H / 2.0 + TOUCH_SLOP {
        return Some(Part::Dots);
    }
    if p.x >= win.right() - RESIZE_ZONE && p.y >= win.bottom() - RESIZE_ZONE {
        return Some(Part::ResizeCorner);
    }
    Some(Part::Content)
}

#[cfg(test)]
mod tests {
    use super::*;

    // G0 from tools: the demo window at (95, 64) 410 x 232.
    const G0: Rect = Rect::new(95.0, 64.0, 410.0, 232.0);

    #[test]
    fn spec_numbers() {
        assert_eq!(ARC_RADIUS, 17.0);
        let a = anatomy(&G0);
        // arc concentric with the 24px corner
        assert_eq!(a.arc_center, Point::new(G0.right() - 24.0, G0.y + 24.0));
        // arc top end sits on the control line, 7px under the top edge
        assert_eq!(a.arc_top.y, G0.y + 7.0);
        // pill is 28 x 6, centered on the control line, 13px from the arc's cap
        assert_eq!((a.pill.w, a.pill.h), (28.0, 6.0));
        assert_eq!(a.pill.center().y, a.arc_top.y);
        assert_eq!(a.arc_top.x - ARC_THICKNESS / 2.0 - a.pill.right(), 13.0);
        // pill center matches the renderer's geo_ctrl: (x + w - 54, y + 7)
        assert_eq!(a.pill.center(), Point::new(G0.x + G0.w - 54.0, G0.y + 7.0));
        // ••• centered on the top frame, level with the pill
        assert_eq!(a.dots_center, Point::new(G0.x + G0.w / 2.0, a.pill.center().y));
    }

    #[test]
    fn hit_parts() {
        let a = anatomy(&G0);
        assert_eq!(hit_test(&G0, a.pill.center()), Some(Part::Pill));
        assert_eq!(hit_test(&G0, a.dots_center), Some(Part::Dots));
        assert_eq!(hit_test(&G0, a.dots[0]), Some(Part::Dots));
        // the renderer's arc finger target (x + w - 12, y + 12)
        assert_eq!(hit_test(&G0, Point::new(G0.right() - 12.0, G0.y + 12.0)), Some(Part::CornerArc));
        assert_eq!(hit_test(&G0, a.resize_handle), Some(Part::ResizeCorner));
        assert_eq!(hit_test(&G0, G0.center()), Some(Part::Content));
        assert_eq!(hit_test(&G0, Point::new(10.0, 10.0)), None);
    }

    #[test]
    fn rounded_corners_are_not_window() {
        // top-left and bottom-left corner pixels are cut away by the 24px radius
        assert_eq!(hit_test(&G0, Point::new(G0.x + 1.0, G0.y + 1.0)), None);
        assert_eq!(hit_test(&G0, Point::new(G0.x + 1.0, G0.bottom() - 1.0)), None);
    }

    #[test]
    fn arc_and_pill_zones_do_not_overlap() {
        let a = anatomy(&G0);
        let pill_zone = a.pill.inflate(8.0, TOUCH_SLOP);
        assert!(pill_zone.right() < a.arc_center.x - 2.0);
    }
}
