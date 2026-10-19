//! Per-pointer gesture recognition for the four window controls.
//!
//! A [`Recognizer`] is created on pointer-down with the [`Part`] that was hit and fed every
//! following sample. It is pure: no window state, only the gesture the samples describe.

use crate::anatomy::Part;
use crate::geometry::Point;
use serde::{Deserialize, Serialize};

/// Press-and-hold time before ••• lifts the window for moving.
pub const HOLD_MS: f64 = 350.0;
/// Longest press that still counts as a tap.
pub const TAP_MAX_MS: f64 = 500.0;
/// Movement under this many pixels is "not moved".
pub const MOVE_SLOP: f64 = 6.0;
/// Vertical travel that turns a pill press into a swipe.
pub const SWIPE_MIN: f64 = 18.0;
/// Inward travel (toward the window, down-left) that closes on release.
pub const FLICK_MIN_DIST: f64 = 10.0;
/// Average speed (px/ms) that closes on release even with a short flick.
pub const FLICK_MIN_VELOCITY: f64 = 0.35;
/// The arc follows the finger by at most this many pixels; the window never shrinks.
pub const ARC_NUDGE_MAX: f64 = 4.0;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PointerKind {
    Down,
    Move,
    Up,
    Cancel,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct PointerSample {
    pub kind: PointerKind,
    pub x: f64,
    pub y: f64,
    pub t_ms: f64,
}

impl PointerSample {
    pub fn new(kind: PointerKind, x: f64, y: f64, t_ms: f64) -> Self {
        Self { kind, x, y, t_ms }
    }
    pub fn pos(&self) -> Point {
        Point::new(self.x, self.y)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "gesture", rename_all = "snake_case")]
pub enum Gesture {
    /// The arc follows the finger a few pixels while dragging.
    ArcNudge { dx: f64, dy: f64 },
    /// Released with an inward flick: close, flying away along (dx, dy).
    ArcFlickClose { dx: f64, dy: f64, velocity: f64 },
    /// Released without a flick: the arc springs back.
    ArcRelease,
    PillSwipeDown,
    PillSwipeUp,
    PillTap,
    DotsTap,
    /// Hold threshold reached: the window lifts.
    DotsLift,
    DotsDrag { dx: f64, dy: f64, x: f64, y: f64 },
    DotsDrop { dx: f64, dy: f64, x: f64, y: f64 },
    ResizeDrag { dx: f64, dy: f64 },
    ResizeEnd { dx: f64, dy: f64 },
    ContentTap,
    Cancelled,
}

#[derive(Clone, Debug)]
pub struct Recognizer {
    part: Part,
    start: Point,
    start_t: f64,
    lifted: bool,
    moved_before_lift: bool,
    done: bool,
}

impl Recognizer {
    pub fn begin(part: Part, down: &PointerSample) -> Self {
        Self {
            part,
            start: down.pos(),
            start_t: down.t_ms,
            lifted: false,
            moved_before_lift: false,
            done: false,
        }
    }

    pub fn part(&self) -> Part {
        self.part
    }
    pub fn is_lifted(&self) -> bool {
        self.lifted
    }
    pub fn is_done(&self) -> bool {
        self.done
    }

    /// Time passing with the finger still: lets ••• lift on hold without a move sample.
    pub fn tick(&mut self, t_ms: f64) -> Option<Gesture> {
        if self.part == Part::Dots && !self.done && !self.lifted && !self.moved_before_lift && t_ms - self.start_t >= HOLD_MS {
            self.lifted = true;
            return Some(Gesture::DotsLift);
        }
        None
    }

    pub fn update(&mut self, s: &PointerSample) -> Vec<Gesture> {
        let mut out = Vec::new();
        if self.done {
            return out;
        }
        let p = s.pos();
        let (dx, dy) = (p.x - self.start.x, p.y - self.start.y);
        let dist = dx.hypot(dy);
        let dur = (s.t_ms - self.start_t).max(0.0);
        match s.kind {
            PointerKind::Down => {}
            PointerKind::Move => match self.part {
                Part::CornerArc => {
                    let k = if dist > ARC_NUDGE_MAX { ARC_NUDGE_MAX / dist } else { 1.0 };
                    out.push(Gesture::ArcNudge { dx: dx * k, dy: dy * k });
                }
                Part::Dots => {
                    if !self.lifted {
                        if let Some(g) = self.tick(s.t_ms) {
                            out.push(g);
                        } else if dist > MOVE_SLOP {
                            self.moved_before_lift = true;
                        }
                    }
                    if self.lifted {
                        out.push(Gesture::DotsDrag { dx, dy, x: p.x, y: p.y });
                    }
                }
                Part::ResizeCorner => out.push(Gesture::ResizeDrag { dx, dy }),
                Part::Pill | Part::Content => {}
            },
            PointerKind::Up => {
                self.done = true;
                match self.part {
                    Part::CornerArc => {
                        // inward = toward the window body: left and down from the top-right corner
                        let inward = (-dx + dy) / std::f64::consts::SQRT_2;
                        let velocity = if dur > 0.0 { dist / dur } else { 0.0 };
                        if inward >= FLICK_MIN_DIST || (inward > 3.0 && velocity >= FLICK_MIN_VELOCITY) {
                            out.push(Gesture::ArcFlickClose { dx, dy, velocity });
                        } else {
                            out.push(Gesture::ArcRelease);
                        }
                    }
                    Part::Pill => {
                        if dy.abs() >= SWIPE_MIN && dy.abs() > dx.abs() {
                            out.push(if dy > 0.0 { Gesture::PillSwipeDown } else { Gesture::PillSwipeUp });
                        } else if dist <= MOVE_SLOP && dur <= TAP_MAX_MS {
                            out.push(Gesture::PillTap);
                        } else {
                            out.push(Gesture::Cancelled);
                        }
                    }
                    Part::Dots => {
                        if !self.lifted && !self.moved_before_lift && dist <= MOVE_SLOP && dur >= HOLD_MS {
                            // held in place and let go: lift and drop where it was
                            self.lifted = true;
                            out.push(Gesture::DotsLift);
                        }
                        if self.lifted {
                            out.push(Gesture::DotsDrop { dx, dy, x: p.x, y: p.y });
                        } else if !self.moved_before_lift && dist <= MOVE_SLOP && dur <= TAP_MAX_MS {
                            out.push(Gesture::DotsTap);
                        } else {
                            out.push(Gesture::Cancelled);
                        }
                    }
                    Part::ResizeCorner => out.push(Gesture::ResizeEnd { dx, dy }),
                    Part::Content => {
                        out.push(if dist <= MOVE_SLOP { Gesture::ContentTap } else { Gesture::Cancelled });
                    }
                }
            }
            PointerKind::Cancel => {
                self.done = true;
                out.push(Gesture::Cancelled);
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use PointerKind::*;

    fn run(part: Part, samples: &[(PointerKind, f64, f64, f64)]) -> Vec<Gesture> {
        let first = PointerSample::new(samples[0].0, samples[0].1, samples[0].2, samples[0].3);
        let mut r = Recognizer::begin(part, &first);
        let mut out = Vec::new();
        for &(k, x, y, t) in &samples[1..] {
            out.extend(r.update(&PointerSample::new(k, x, y, t)));
        }
        out
    }

    #[test]
    fn arc_flick_inward_closes() {
        let g = run(Part::CornerArc, &[(Down, 100.0, 100.0, 0.0), (Move, 92.0, 108.0, 60.0), (Up, 88.0, 112.0, 90.0)]);
        assert!(matches!(g.last(), Some(Gesture::ArcFlickClose { .. })));
    }

    #[test]
    fn arc_nudge_is_capped() {
        let g = run(Part::CornerArc, &[(Down, 100.0, 100.0, 0.0), (Move, 60.0, 140.0, 100.0)]);
        match g[0] {
            Gesture::ArcNudge { dx, dy } => assert!((dx.hypot(dy) - ARC_NUDGE_MAX).abs() < 1e-9),
            ref other => panic!("{other:?}"),
        }
    }

    #[test]
    fn arc_outward_drag_springs_back() {
        let g = run(Part::CornerArc, &[(Down, 100.0, 100.0, 0.0), (Up, 120.0, 80.0, 400.0)]);
        assert_eq!(g, vec![Gesture::ArcRelease]);
    }

    #[test]
    fn pill_swipes_and_tap() {
        assert_eq!(run(Part::Pill, &[(Down, 0.0, 0.0, 0.0), (Up, 2.0, 30.0, 150.0)]), vec![Gesture::PillSwipeDown]);
        assert_eq!(run(Part::Pill, &[(Down, 0.0, 0.0, 0.0), (Up, -3.0, -25.0, 150.0)]), vec![Gesture::PillSwipeUp]);
        assert_eq!(run(Part::Pill, &[(Down, 0.0, 0.0, 0.0), (Up, 1.0, 1.0, 120.0)]), vec![Gesture::PillTap]);
        assert_eq!(run(Part::Pill, &[(Down, 0.0, 0.0, 0.0), (Up, 30.0, 4.0, 120.0)]), vec![Gesture::Cancelled]);
    }

    #[test]
    fn dots_tap_vs_hold_move() {
        assert_eq!(run(Part::Dots, &[(Down, 0.0, 0.0, 0.0), (Up, 0.0, 0.0, 100.0)]), vec![Gesture::DotsTap]);
        let g = run(Part::Dots, &[(Down, 0.0, 0.0, 0.0), (Move, 1.0, 0.0, 400.0), (Move, 50.0, 20.0, 600.0), (Up, 60.0, 30.0, 700.0)]);
        assert_eq!(g[0], Gesture::DotsLift);
        assert!(matches!(g[1], Gesture::DotsDrag { .. }));
        assert_eq!(g.last(), Some(&Gesture::DotsDrop { dx: 60.0, dy: 30.0, x: 60.0, y: 30.0 }));
    }

    #[test]
    fn dots_quick_drag_does_not_move() {
        let g = run(Part::Dots, &[(Down, 0.0, 0.0, 0.0), (Move, 40.0, 0.0, 50.0), (Up, 80.0, 0.0, 600.0)]);
        assert_eq!(g, vec![Gesture::Cancelled]);
    }

    #[test]
    fn dots_lift_on_tick_without_moving() {
        let mut r = Recognizer::begin(Part::Dots, &PointerSample::new(Down, 5.0, 5.0, 1000.0));
        assert_eq!(r.tick(1200.0), None);
        assert_eq!(r.tick(1400.0), Some(Gesture::DotsLift));
        assert_eq!(r.tick(1500.0), None);
        assert!(r.is_lifted());
    }

    #[test]
    fn resize_reports_deltas() {
        let g = run(Part::ResizeCorner, &[(Down, 0.0, 0.0, 0.0), (Move, 10.0, 5.0, 10.0), (Up, 40.0, 20.0, 50.0)]);
        assert_eq!(g, vec![Gesture::ResizeDrag { dx: 10.0, dy: 5.0 }, Gesture::ResizeEnd { dx: 40.0, dy: 20.0 }]);
    }

    #[test]
    fn cancel_ends() {
        let g = run(Part::Pill, &[(Down, 0.0, 0.0, 0.0), (Cancel, 0.0, 0.0, 10.0), (Up, 0.0, 40.0, 20.0)]);
        assert_eq!(g, vec![Gesture::Cancelled]);
    }
}
