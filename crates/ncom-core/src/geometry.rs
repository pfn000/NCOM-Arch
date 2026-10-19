//! Points and rectangles in desktop pixels (origin top-left, y grows down).

use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub const fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }
    pub fn dist(self, o: Point) -> f64 {
        (self.x - o.x).hypot(self.y - o.y)
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

impl Rect {
    pub const fn new(x: f64, y: f64, w: f64, h: f64) -> Self {
        Self { x, y, w, h }
    }
    pub fn right(&self) -> f64 {
        self.x + self.w
    }
    pub fn bottom(&self) -> f64 {
        self.y + self.h
    }
    pub fn center(&self) -> Point {
        Point::new(self.x + self.w / 2.0, self.y + self.h / 2.0)
    }
    /// Half-open containment: left/top edges are inside, right/bottom are not.
    pub fn contains(&self, p: Point) -> bool {
        p.x >= self.x && p.x < self.right() && p.y >= self.y && p.y < self.bottom()
    }
    pub fn translate(&self, dx: f64, dy: f64) -> Rect {
        Rect::new(self.x + dx, self.y + dy, self.w, self.h)
    }
    /// Grow by `dx` on the left and right and `dy` on the top and bottom.
    pub fn inflate(&self, dx: f64, dy: f64) -> Rect {
        Rect::new(self.x - dx, self.y - dy, self.w + 2.0 * dx, self.h + 2.0 * dy)
    }
    pub fn lerp(&self, o: &Rect, t: f64) -> Rect {
        let l = |a: f64, b: f64| a + (b - a) * t;
        Rect::new(l(self.x, o.x), l(self.y, o.y), l(self.w, o.w), l(self.h, o.h))
    }
    /// Shrink to fit `area` if needed, then shift so the rect lies inside it.
    pub fn clamp_into(&self, area: &Rect) -> Rect {
        let w = self.w.min(area.w);
        let h = self.h.min(area.h);
        let x = self.x.clamp(area.x, area.right() - w);
        let y = self.y.clamp(area.y, area.bottom() - h);
        Rect::new(x, y, w, h)
    }
    pub fn approx_eq(&self, o: &Rect, eps: f64) -> bool {
        (self.x - o.x).abs() <= eps
            && (self.y - o.y).abs() <= eps
            && (self.w - o.w).abs() <= eps
            && (self.h - o.h).abs() <= eps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contains_is_half_open() {
        let r = Rect::new(10.0, 10.0, 100.0, 50.0);
        assert!(r.contains(Point::new(10.0, 10.0)));
        assert!(!r.contains(Point::new(110.0, 30.0)));
        assert!(!r.contains(Point::new(50.0, 60.0)));
    }

    #[test]
    fn clamp_into_shifts_and_shrinks() {
        let area = Rect::new(8.0, 48.0, 584.0, 276.0);
        let r = Rect::new(-50.0, 300.0, 200.0, 100.0).clamp_into(&area);
        assert_eq!(r, Rect::new(8.0, 224.0, 200.0, 100.0));
        let big = Rect::new(0.0, 0.0, 1000.0, 1000.0).clamp_into(&area);
        assert_eq!(big, area);
    }

    #[test]
    fn lerp_endpoints() {
        let a = Rect::new(0.0, 0.0, 10.0, 10.0);
        let b = Rect::new(10.0, 20.0, 30.0, 40.0);
        assert_eq!(a.lerp(&b, 0.0), a);
        assert_eq!(a.lerp(&b, 1.0), b);
        assert_eq!(a.lerp(&b, 0.5), Rect::new(5.0, 10.0, 20.0, 25.0));
    }
}
