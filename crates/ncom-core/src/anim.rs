//! Easing curves (the same curves the GIF renderer uses) and the animation scheduler.
//!
//! The window manager changes a window's logical rect at once; the scheduler holds the
//! presentational rect for each window while it animates there. A compositor calls
//! [`Scheduler::tick`] once per frame and draws the rects it returns.

use crate::geometry::Rect;
use serde::{Deserialize, Serialize};

pub fn clamp01(x: f64) -> f64 {
    x.clamp(0.0, 1.0)
}

/// Cubic ease-in-out (`ease` in tools: 4x³, then 1 - (-2x+2)³/2).
pub fn ease_in_out(x: f64) -> f64 {
    let x = clamp01(x);
    if x < 0.5 {
        4.0 * x * x * x
    } else {
        1.0 - (-2.0 * x + 2.0).powi(3) / 2.0
    }
}

/// Cubic ease-out (`eout` in tools).
pub fn ease_out(x: f64) -> f64 {
    1.0 - (1.0 - clamp01(x)).powi(3)
}

/// Damped spring 0 → 1 with overshoot (`spring` in tools, freq 3, damping 5).
pub fn spring(x: f64, freq: f64, damp: f64) -> f64 {
    let x = x.max(0.0);
    1.0 - (-damp * x).exp() * (2.0 * std::f64::consts::PI * freq * x).cos()
}

/// The bubble jiggle when a window can't resize: amplitude of the corner's displacement.
pub fn bounce_amplitude(t_s: f64) -> f64 {
    (-4.2 * t_s).exp() * (2.0 * std::f64::consts::PI * 2.6 * t_s).cos()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Easing {
    Linear,
    EaseInOut,
    EaseOut,
    Spring,
}

impl Easing {
    pub fn apply(self, x: f64) -> f64 {
        match self {
            Easing::Linear => clamp01(x),
            Easing::EaseInOut => ease_in_out(x),
            Easing::EaseOut => ease_out(x),
            Easing::Spring => {
                if x >= 1.0 {
                    1.0
                } else {
                    spring(x, 3.0, 5.0)
                }
            }
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Tween {
    pub id: u32,
    pub from: Rect,
    pub to: Rect,
    pub start_ms: f64,
    pub duration_ms: f64,
    pub easing: Easing,
}

impl Tween {
    pub fn progress(&self, now: f64) -> f64 {
        if self.duration_ms <= 0.0 {
            1.0
        } else {
            clamp01((now - self.start_ms) / self.duration_ms)
        }
    }
    pub fn sample(&self, now: f64) -> Rect {
        let p = self.progress(now);
        if p >= 1.0 {
            self.to
        } else {
            self.from.lerp(&self.to, self.easing.apply(p))
        }
    }
}

/// One frame of output: where each animating window is drawn now.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct FrameOut {
    pub frames: Vec<(u32, Rect)>,
    pub finished: Vec<u32>,
}

#[derive(Clone, Debug, Default)]
pub struct Scheduler {
    tweens: Vec<Tween>,
}

impl Scheduler {
    pub fn new() -> Self {
        Self::default()
    }
    /// Start a tween. A newer tween for the same window replaces the older one,
    /// starting from wherever the older one had got to.
    pub fn schedule(&mut self, mut t: Tween) {
        if let Some(old) = self.tweens.iter().find(|x| x.id == t.id) {
            t.from = old.sample(t.start_ms);
        }
        self.tweens.retain(|x| x.id != t.id);
        self.tweens.push(t);
    }
    pub fn cancel(&mut self, id: u32) {
        self.tweens.retain(|x| x.id != id);
    }
    pub fn is_animating(&self, id: u32) -> bool {
        self.tweens.iter().any(|x| x.id == id)
    }
    pub fn len(&self) -> usize {
        self.tweens.len()
    }
    pub fn is_empty(&self) -> bool {
        self.tweens.is_empty()
    }
    pub fn sample(&self, id: u32, now: f64) -> Option<Rect> {
        self.tweens.iter().find(|x| x.id == id).map(|t| t.sample(now))
    }
    pub fn tick(&mut self, now: f64) -> FrameOut {
        let mut out = FrameOut::default();
        for t in &self.tweens {
            out.frames.push((t.id, t.sample(now)));
            if t.progress(now) >= 1.0 {
                out.finished.push(t.id);
            }
        }
        self.tweens.retain(|t| t.progress(now) < 1.0);
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn easing_endpoints_and_midpoint() {
        for e in [Easing::Linear, Easing::EaseInOut, Easing::EaseOut, Easing::Spring] {
            assert!((e.apply(0.0)).abs() < 1e-9, "{e:?}");
            assert!((e.apply(1.0) - 1.0).abs() < 1e-9, "{e:?}");
        }
        assert!((ease_in_out(0.5) - 0.5).abs() < 1e-12);
        assert!(ease_out(0.5) > 0.5);
    }

    #[test]
    fn spring_overshoots() {
        let peak = (1..100).map(|i| spring(i as f64 / 100.0, 3.0, 5.0)).fold(0.0, f64::max);
        assert!(peak > 1.0);
    }

    #[test]
    fn bounce_decays() {
        assert!((bounce_amplitude(0.0) - 1.0).abs() < 1e-12);
        assert!(bounce_amplitude(1.5).abs() < 0.01);
    }

    #[test]
    fn scheduler_runs_to_completion() {
        let mut s = Scheduler::new();
        let a = Rect::new(0.0, 0.0, 100.0, 100.0);
        let b = Rect::new(100.0, 100.0, 200.0, 200.0);
        s.schedule(Tween { id: 1, from: a, to: b, start_ms: 0.0, duration_ms: 300.0, easing: Easing::EaseInOut });
        let mid = s.tick(150.0);
        assert_eq!(mid.frames.len(), 1);
        assert!(mid.finished.is_empty());
        assert!(mid.frames[0].1.approx_eq(&a.lerp(&b, 0.5), 1e-9));
        let end = s.tick(300.0);
        assert_eq!(end.frames, vec![(1, b)]);
        assert_eq!(end.finished, vec![1]);
        assert!(s.is_empty());
    }

    #[test]
    fn retarget_starts_from_current_position() {
        let mut s = Scheduler::new();
        let a = Rect::new(0.0, 0.0, 100.0, 100.0);
        let b = Rect::new(100.0, 0.0, 100.0, 100.0);
        s.schedule(Tween { id: 7, from: a, to: b, start_ms: 0.0, duration_ms: 100.0, easing: Easing::Linear });
        s.schedule(Tween { id: 7, from: b, to: a, start_ms: 50.0, duration_ms: 100.0, easing: Easing::Linear });
        assert_eq!(s.len(), 1);
        assert!(s.sample(7, 50.0).unwrap().approx_eq(&Rect::new(50.0, 0.0, 100.0, 100.0), 1e-9));
    }
}
