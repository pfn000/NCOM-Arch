//! The NCOM Arch window manager: windows, z-order, focus, and what each gesture does.

use crate::anatomy::{hit_test, Part};
use crate::anim::{Easing, Scheduler, Tween};
use crate::geometry::{Point, Rect};
use crate::gesture::{Gesture, PointerKind, PointerSample, Recognizer};
use crate::menu::{app_menu, AppMenu};
use crate::props::{panel, DocumentInfo, PropertiesPanel, QuickSettings};
use serde::{Deserialize, Serialize};
use std::fmt;

pub type WindowId = u32;

/// Minimum size a resizable window can be dragged down to.
pub const MIN_W: f64 = 160.0;
pub const MIN_H: f64 = 100.0;
/// How close to a work-area edge the pointer must be for a snap preview.
pub const SNAP_EDGE: f64 = 10.0;
/// Gap between two half-screen windows.
pub const SNAP_GAP: f64 = 8.0;
/// Animation lengths (ms).
pub const ANIM_MS: f64 = 300.0;
/// The corner of a window that can't resize stretches by this share of the drag, capped.
pub const BOUNCE_SHARE: f64 = 0.5;
pub const BOUNCE_MAX: f64 = 18.0;

/// The screen: 24px rounded corners, a top bar and a dock. Windows always fit between them.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct Desktop {
    pub width: f64,
    pub height: f64,
    pub top_bar: f64,
    pub dock: f64,
    pub margin: f64,
}

impl Default for Desktop {
    /// The 600 × 375 desktop the gesture GIFs are drawn on (work area 8, 48, 584 × 276).
    fn default() -> Self {
        Self { width: 600.0, height: 375.0, top_bar: 40.0, dock: 51.0, margin: 8.0 }
    }
}

impl Desktop {
    pub fn with_size(width: f64, height: f64) -> Self {
        Self { width, height, ..Self::default() }
    }
    pub fn screen(&self) -> Rect {
        Rect::new(0.0, 0.0, self.width, self.height)
    }
    /// The usable area between the top bar and the dock.
    pub fn work_area(&self) -> Rect {
        let y = self.top_bar + self.margin;
        Rect::new(
            self.margin,
            y,
            (self.width - 2.0 * self.margin).max(0.0),
            (self.height - self.dock - y).max(0.0),
        )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SnapZone {
    Full,
    Left,
    Right,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WindowState {
    Normal,
    Minimized,
    Maximized,
    Snapped,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Window {
    pub id: WindowId,
    pub title: String,
    pub app: String,
    pub rect: Rect,
    pub state: WindowState,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snap: Option<SnapZone>,
    /// Where restore goes back to after maximize / snap.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub restore_rect: Option<Rect>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub minimized_from: Option<WindowState>,
    pub resizable: bool,
    pub lifted: bool,
    pub quick: QuickSettings,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub document: Option<DocumentInfo>,
}

/// Everything the window system tells a compositor / shell.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum Event {
    Opened { id: WindowId, rect: Rect },
    Focused { id: WindowId },
    /// The window keeps its size and flies away along (dx, dy).
    Closed { id: WindowId, flick_dx: f64, flick_dy: f64 },
    Minimized { id: WindowId },
    Maximized { id: WindowId, rect: Rect },
    Restored { id: WindowId, rect: Rect },
    Snapped { id: WindowId, zone: SnapZone, rect: Rect },
    SnapPreview { zone: Option<SnapZone>, rect: Option<Rect> },
    Moved { id: WindowId, rect: Rect },
    Resized { id: WindowId, rect: Rect },
    ArcNudge { id: WindowId, dx: f64, dy: f64 },
    ArcSpringBack { id: WindowId },
    Lifted { id: WindowId },
    Dropped { id: WindowId, rect: Rect },
    ResizeHandle { id: WindowId, visible: bool },
    Bounce { id: WindowId, dx: f64, dy: f64 },
    BounceRelease { id: WindowId },
    InfoRequested { id: WindowId },
    MenuRequested { id: WindowId },
    QuickChanged { id: WindowId, quick: QuickSettings },
    Frame { id: WindowId, rect: Rect },
    AnimationDone { id: WindowId },
}

#[derive(Clone, Debug, PartialEq)]
pub enum WmError {
    NoSuchWindow(WindowId),
    NotResizable(WindowId),
    UnknownSetting(String),
    UnknownAction(String),
}

impl fmt::Display for WmError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WmError::NoSuchWindow(id) => write!(f, "no window with id {id}"),
            WmError::NotResizable(id) => write!(f, "window {id} can't be resized"),
            WmError::UnknownSetting(k) => write!(f, "unknown quick setting '{k}' (on_top, glass, notify)"),
            WmError::UnknownAction(a) => write!(f, "unknown menu action '{a}'"),
        }
    }
}

impl std::error::Error for WmError {}

pub type WmResult<T> = Result<T, WmError>;

/// Parameters for a new window.
#[derive(Clone, Debug, PartialEq, Default)]
pub struct OpenSpec {
    pub title: String,
    pub app: Option<String>,
    pub rect: Option<Rect>,
    pub resizable: bool,
    pub document: Option<DocumentInfo>,
}

#[derive(Clone, Debug)]
struct ActivePointer {
    id: WindowId,
    rec: Recognizer,
    origin: Rect,
    resizing: bool,
}

#[derive(Clone, Debug)]
pub struct WindowManager {
    desktop: Desktop,
    /// Back-to-front.
    windows: Vec<Window>,
    next_id: WindowId,
    active: Option<ActivePointer>,
    snap_preview: Option<SnapZone>,
    scheduler: Scheduler,
    now: f64,
}

impl Default for WindowManager {
    fn default() -> Self {
        Self::new(Desktop::default())
    }
}

impl WindowManager {
    pub fn new(desktop: Desktop) -> Self {
        Self { desktop, windows: Vec::new(), next_id: 1, active: None, snap_preview: None, scheduler: Scheduler::new(), now: 0.0 }
    }

    pub fn desktop(&self) -> &Desktop {
        &self.desktop
    }
    pub fn set_desktop(&mut self, d: Desktop) {
        self.desktop = d;
        let wa = d.work_area();
        for w in &mut self.windows {
            w.rect = match (w.state, w.snap) {
                (WindowState::Maximized, _) => wa,
                (WindowState::Snapped, Some(z)) => snap_rect(&wa, z),
                _ => w.rect.clamp_into(&wa),
            };
        }
    }
    pub fn windows(&self) -> &[Window] {
        &self.windows
    }
    pub fn window(&self, id: WindowId) -> Option<&Window> {
        self.windows.iter().find(|w| w.id == id)
    }
    pub fn snap_preview(&self) -> Option<SnapZone> {
        self.snap_preview
    }
    pub fn now(&self) -> f64 {
        self.now
    }
    pub fn scheduler(&self) -> &Scheduler {
        &self.scheduler
    }
    /// The focused window: the top-most one that isn't minimized.
    pub fn focused(&self) -> Option<WindowId> {
        self.windows.iter().rev().find(|w| w.state != WindowState::Minimized).map(|w| w.id)
    }

    fn idx(&self, id: WindowId) -> WmResult<usize> {
        self.windows.iter().position(|w| w.id == id).ok_or(WmError::NoSuchWindow(id))
    }
    fn win_mut(&mut self, id: WindowId) -> WmResult<&mut Window> {
        let i = self.idx(id)?;
        Ok(&mut self.windows[i])
    }
    fn get_mut(&mut self, id: WindowId) -> Option<&mut Window> {
        self.windows.iter_mut().find(|w| w.id == id)
    }
    fn advance(&mut self, t: f64) {
        if t > self.now {
            self.now = t;
        }
    }
    fn animate(&mut self, id: WindowId, from: Rect, to: Rect, easing: Easing) {
        if from != to {
            self.scheduler.schedule(Tween { id, from, to, start_ms: self.now, duration_ms: ANIM_MS, easing });
        }
    }
    /// Keep "on top" windows above the rest, preserving order inside each layer.
    fn restack(&mut self) {
        self.windows.sort_by_key(|w| w.quick.on_top);
    }

    pub fn open(&mut self, spec: OpenSpec) -> (WindowId, Vec<Event>) {
        let id = self.next_id;
        self.next_id += 1;
        let wa = self.desktop.work_area();
        let rect = match spec.rect {
            Some(r) => r,
            None => {
                // cascade from the demo window's spot
                let n = self.windows.len() as f64;
                let w = (wa.w * 0.7).max(MIN_W);
                let h = (wa.h * 0.84).max(MIN_H);
                Rect::new(wa.x + (wa.w - w) / 2.0 + 24.0 * n, wa.y + 16.0 + 24.0 * n, w, h)
            }
        }
        .clamp_into(&wa);
        let app = spec.app.unwrap_or_else(|| spec.title.clone());
        self.windows.push(Window {
            id,
            title: spec.title,
            app,
            rect,
            state: WindowState::Normal,
            snap: None,
            restore_rect: None,
            minimized_from: None,
            resizable: spec.resizable,
            lifted: false,
            quick: QuickSettings::default(),
            document: spec.document,
        });
        self.restack();
        (id, vec![Event::Opened { id, rect }, Event::Focused { id }])
    }

    pub fn focus(&mut self, id: WindowId) -> WmResult<Vec<Event>> {
        let i = self.idx(id)?;
        let mut ev = Vec::new();
        if self.windows[i].state == WindowState::Minimized {
            ev.extend(self.restore(id)?);
        }
        if self.focused() != Some(id) {
            let i = self.idx(id)?;
            let w = self.windows.remove(i);
            self.windows.push(w);
            self.restack();
            ev.push(Event::Focused { id });
        }
        Ok(ev)
    }

    /// Close: the window keeps its size, then flicks away along (dx, dy).
    pub fn close(&mut self, id: WindowId, flick_dx: f64, flick_dy: f64) -> WmResult<Vec<Event>> {
        let i = self.idx(id)?;
        self.windows.remove(i);
        self.scheduler.cancel(id);
        if self.active.as_ref().map(|a| a.id) == Some(id) {
            self.active = None;
        }
        let mut ev = vec![Event::Closed { id, flick_dx, flick_dy }];
        if let Some(f) = self.focused() {
            ev.push(Event::Focused { id: f });
        }
        Ok(ev)
    }

    pub fn minimize(&mut self, id: WindowId) -> WmResult<Vec<Event>> {
        let w = self.win_mut(id)?;
        if w.state == WindowState::Minimized {
            return Ok(vec![]);
        }
        w.minimized_from = Some(w.state);
        w.state = WindowState::Minimized;
        w.lifted = false;
        let mut ev = vec![Event::Minimized { id }];
        if let Some(f) = self.focused() {
            ev.push(Event::Focused { id: f });
        }
        Ok(ev)
    }

    /// Fill the usable screen between the top bar and the dock (24px corners stay).
    pub fn maximize(&mut self, id: WindowId) -> WmResult<Vec<Event>> {
        let wa = self.desktop.work_area();
        let w = self.win_mut(id)?;
        if w.state == WindowState::Maximized {
            return Ok(vec![]);
        }
        let from = w.rect;
        if w.state == WindowState::Normal || (w.state == WindowState::Minimized && w.minimized_from == Some(WindowState::Normal)) {
            w.restore_rect = Some(w.rect);
        }
        w.state = WindowState::Maximized;
        w.snap = None;
        w.minimized_from = None;
        w.rect = wa;
        self.animate(id, from, wa, Easing::EaseInOut);
        Ok(vec![Event::Maximized { id, rect: wa }])
    }

    pub fn restore(&mut self, id: WindowId) -> WmResult<Vec<Event>> {
        let w = self.win_mut(id)?;
        match w.state {
            WindowState::Minimized => {
                w.state = w.minimized_from.take().unwrap_or(WindowState::Normal);
                let rect = w.rect;
                Ok(vec![Event::Restored { id, rect }])
            }
            WindowState::Maximized | WindowState::Snapped => {
                let from = w.rect;
                let to = w.restore_rect.take().unwrap_or(from);
                w.state = WindowState::Normal;
                w.snap = None;
                w.rect = to;
                self.animate(id, from, to, Easing::EaseInOut);
                Ok(vec![Event::Restored { id, rect: to }])
            }
            WindowState::Normal => Ok(vec![]),
        }
    }

    pub fn snap(&mut self, id: WindowId, zone: SnapZone) -> WmResult<Vec<Event>> {
        let wa = self.desktop.work_area();
        let target = snap_rect(&wa, zone);
        let w = self.win_mut(id)?;
        let from = w.rect;
        if w.state == WindowState::Normal {
            w.restore_rect = Some(w.rect);
        }
        w.state = if zone == SnapZone::Full { WindowState::Maximized } else { WindowState::Snapped };
        w.snap = Some(zone);
        w.rect = target;
        self.animate(id, from, target, Easing::EaseInOut);
        Ok(vec![Event::Snapped { id, zone, rect: target }])
    }

    pub fn move_to(&mut self, id: WindowId, x: f64, y: f64) -> WmResult<Vec<Event>> {
        let wa = self.desktop.work_area();
        let w = self.win_mut(id)?;
        if w.state != WindowState::Normal {
            w.rect = w.restore_rect.take().unwrap_or(w.rect);
            w.state = WindowState::Normal;
            w.snap = None;
        }
        w.rect = Rect::new(x, y, w.rect.w, w.rect.h).clamp_into(&wa);
        Ok(vec![Event::Moved { id, rect: w.rect }])
    }

    pub fn resize(&mut self, id: WindowId, width: f64, height: f64) -> WmResult<Vec<Event>> {
        let wa = self.desktop.work_area();
        let w = self.win_mut(id)?;
        if !w.resizable {
            return Err(WmError::NotResizable(id));
        }
        let r = w.rect;
        let nw = width.max(MIN_W).min(wa.right() - r.x);
        let nh = height.max(MIN_H).min(wa.bottom() - r.y);
        w.rect = Rect::new(r.x, r.y, nw, nh);
        w.state = WindowState::Normal;
        w.snap = None;
        w.restore_rect = None;
        Ok(vec![Event::Resized { id, rect: w.rect }])
    }

    pub fn set_quick(&mut self, id: WindowId, key: &str, value: bool) -> WmResult<Vec<Event>> {
        let w = self.win_mut(id)?;
        match key {
            "on_top" | "keep_on_top" => w.quick.on_top = value,
            "glass" => w.quick.glass = value,
            "notify" | "notifications" => w.quick.notify = value,
            other => return Err(WmError::UnknownSetting(other.to_string())),
        }
        let quick = w.quick;
        self.restack();
        Ok(vec![Event::QuickChanged { id, quick }])
    }

    pub fn properties(&self, id: WindowId) -> WmResult<PropertiesPanel> {
        let w = self.window(id).ok_or(WmError::NoSuchWindow(id))?;
        Ok(panel(&w.app, &w.title, w.document.as_ref(), w.quick))
    }

    pub fn menu(&self, id: WindowId) -> WmResult<AppMenu> {
        let w = self.window(id).ok_or(WmError::NoSuchWindow(id))?;
        Ok(app_menu(&w.app, w.quick))
    }

    /// Run a ••• menu item. Items that open UI (About, Settings…) are reported back for the shell to show.
    pub fn menu_action(&mut self, id: WindowId, action: &str) -> WmResult<Vec<Event>> {
        let q = self.window(id).ok_or(WmError::NoSuchWindow(id))?.quick;
        match action {
            "keep_on_top" => self.set_quick(id, "on_top", !q.on_top),
            "glass" => self.set_quick(id, "glass", !q.glass),
            "notifications" => self.set_quick(id, "notify", !q.notify),
            "hide" => self.minimize(id),
            "quit" => self.close(id, 0.0, 0.0),
            "snap_layout" => Ok(vec![Event::SnapPreview { zone: Some(SnapZone::Full), rect: Some(self.desktop.work_area()) }]),
            "about" | "settings" | "shortcuts" | "help" | "appearance" | "reset" | "move_to_desktop" => Ok(vec![]),
            other => Err(WmError::UnknownAction(other.to_string())),
        }
    }

    /// Top-most window under a point, and the part that was hit.
    pub fn hit(&self, p: Point) -> Option<(WindowId, Part)> {
        self.windows
            .iter()
            .rev()
            .filter(|w| w.state != WindowState::Minimized)
            .find_map(|w| hit_test(&w.rect, p).map(|part| (w.id, part)))
    }

    fn zone_at(&self, p: Point) -> Option<SnapZone> {
        let wa = self.desktop.work_area();
        if p.y <= wa.y + SNAP_EDGE {
            Some(SnapZone::Full)
        } else if p.x <= wa.x + SNAP_EDGE {
            Some(SnapZone::Left)
        } else if p.x >= wa.right() - SNAP_EDGE {
            Some(SnapZone::Right)
        } else {
            None
        }
    }

    /// Feed one pointer sample. Returns what happened.
    pub fn pointer(&mut self, s: PointerSample) -> Vec<Event> {
        self.advance(s.t_ms);
        let mut ev = Vec::new();
        if s.kind == PointerKind::Down {
            if self.active.is_some() {
                return ev; // one pointer at a time
            }
            if let Some((id, part)) = self.hit(s.pos()) {
                if let Ok(f) = self.focus(id) {
                    ev.extend(f);
                }
                let origin = self.window(id).map(|w| w.rect).unwrap_or_default();
                self.active = Some(ActivePointer { id, rec: Recognizer::begin(part, &s), origin, resizing: false });
            }
            return ev;
        }
        let gestures = match self.active.as_mut() {
            Some(a) => a.rec.update(&s),
            None => return ev,
        };
        for g in gestures {
            ev.extend(self.apply(g));
        }
        if matches!(s.kind, PointerKind::Up | PointerKind::Cancel) {
            self.active = None;
        }
        ev
    }

    /// Advance the clock: hold-to-lift on •••, then animation frames.
    pub fn tick(&mut self, t_ms: f64) -> Vec<Event> {
        self.advance(t_ms);
        let mut ev = Vec::new();
        let lift = self.active.as_mut().and_then(|a| a.rec.tick(t_ms));
        if let Some(g) = lift {
            ev.extend(self.apply(g));
        }
        let out = self.scheduler.tick(self.now);
        ev.extend(out.frames.into_iter().map(|(id, rect)| Event::Frame { id, rect }));
        ev.extend(out.finished.into_iter().map(|id| Event::AnimationDone { id }));
        ev
    }

    fn apply(&mut self, g: Gesture) -> Vec<Event> {
        let (id, origin) = match self.active.as_ref() {
            Some(a) => (a.id, a.origin),
            None => return vec![],
        };
        let state = match self.window(id) {
            Some(w) => w.state,
            None => return vec![],
        };
        let wa = self.desktop.work_area();
        let ok = |r: WmResult<Vec<Event>>| r.unwrap_or_default();
        match g {
            Gesture::ArcNudge { dx, dy } => vec![Event::ArcNudge { id, dx, dy }],
            Gesture::ArcFlickClose { dx, dy, .. } => ok(self.close(id, dx, dy)),
            Gesture::ArcRelease => vec![Event::ArcSpringBack { id }],
            Gesture::PillSwipeDown => match state {
                WindowState::Maximized | WindowState::Snapped => ok(self.restore(id)),
                _ => ok(self.minimize(id)),
            },
            Gesture::PillSwipeUp => match state {
                WindowState::Normal | WindowState::Snapped => ok(self.maximize(id)),
                _ => vec![],
            },
            Gesture::PillTap => vec![Event::InfoRequested { id }],
            Gesture::DotsTap => vec![Event::MenuRequested { id }],
            Gesture::DotsLift => {
                if let Some(w) = self.get_mut(id) {
                    w.lifted = true;
                }
                vec![Event::Lifted { id }]
            }
            Gesture::DotsDrag { dx, dy, x, y } => {
                let mut ev = Vec::new();
                let mut rect = origin.translate(dx, dy);
                let mut new_origin = None;
                if let Some(w) = self.get_mut(id) {
                    if w.state != WindowState::Normal {
                        // dragging a maximized / snapped window out: back to its own size under the finger
                        let size = w.restore_rect.take().unwrap_or(origin);
                        let fx = ((x - origin.x) / origin.w.max(1.0)).clamp(0.0, 1.0);
                        rect = Rect::new(x - size.w * fx, origin.y + dy, size.w, size.h);
                        w.state = WindowState::Normal;
                        w.snap = None;
                        new_origin = Some(Rect::new(rect.x - dx, rect.y - dy, size.w, size.h));
                    }
                    w.rect = rect;
                }
                if let (Some(o), Some(a)) = (new_origin, self.active.as_mut()) {
                    a.origin = o;
                }
                ev.push(Event::Moved { id, rect });
                let zone = self.zone_at(Point::new(x, y));
                if zone != self.snap_preview {
                    self.snap_preview = zone;
                    ev.push(Event::SnapPreview { zone, rect: zone.map(|z| snap_rect(&wa, z)) });
                }
                ev
            }
            Gesture::DotsDrop { x, y, .. } => {
                let mut ev = Vec::new();
                let had_preview = self.snap_preview.is_some();
                let zone = self.snap_preview.take().or_else(|| self.zone_at(Point::new(x, y)));
                if let Some(w) = self.get_mut(id) {
                    w.lifted = false;
                }
                if had_preview {
                    ev.push(Event::SnapPreview { zone: None, rect: None });
                }
                match zone {
                    Some(z) => {
                        ev.extend(ok(self.snap(id, z)));
                        // snapping from a drag restores to where the drag began
                        if let Some(w) = self.get_mut(id) {
                            w.restore_rect = Some(origin);
                        }
                    }
                    None => {
                        if let Some(w) = self.get_mut(id) {
                            // keep the ••• reachable: the window stays inside the work area
                            w.rect = w.rect.clamp_into(&wa);
                            let rect = w.rect;
                            ev.push(Event::Dropped { id, rect });
                        }
                    }
                }
                ev
            }
            Gesture::ResizeDrag { dx, dy } => {
                let resizable = self.window(id).map(|w| w.resizable).unwrap_or(false);
                if resizable {
                    let mut ev = Vec::new();
                    let first = self.active.as_ref().map(|a| !a.resizing).unwrap_or(false);
                    if first {
                        if let Some(a) = self.active.as_mut() {
                            a.resizing = true;
                        }
                        ev.push(Event::ResizeHandle { id, visible: true });
                    }
                    ev.extend(ok(self.resize(id, origin.w + dx, origin.h + dy)));
                    ev
                } else {
                    let k = |v: f64| (v * BOUNCE_SHARE).clamp(-BOUNCE_MAX, BOUNCE_MAX);
                    vec![Event::Bounce { id, dx: k(dx), dy: k(dy) }]
                }
            }
            Gesture::ResizeEnd { dx, dy } => {
                let resizable = self.window(id).map(|w| w.resizable).unwrap_or(false);
                if resizable {
                    let mut ev = ok(self.resize(id, origin.w + dx, origin.h + dy));
                    ev.push(Event::ResizeHandle { id, visible: false });
                    ev
                } else {
                    vec![Event::BounceRelease { id }]
                }
            }
            Gesture::ContentTap => vec![],
            Gesture::Cancelled => {
                let lifted = self.window(id).map(|w| w.lifted).unwrap_or(false);
                let mut ev = Vec::new();
                if lifted {
                    if let Some(w) = self.get_mut(id) {
                        w.lifted = false;
                        w.rect = origin;
                    }
                    ev.push(Event::Moved { id, rect: origin });
                    if self.snap_preview.take().is_some() {
                        ev.push(Event::SnapPreview { zone: None, rect: None });
                    }
                }
                if self.active.as_ref().map(|a| a.rec.part()) == Some(Part::CornerArc) {
                    ev.push(Event::ArcSpringBack { id });
                }
                ev
            }
        }
    }
}

/// The rect a snap zone fills inside the work area.
pub fn snap_rect(wa: &Rect, zone: SnapZone) -> Rect {
    let half = (wa.w - SNAP_GAP) / 2.0;
    match zone {
        SnapZone::Full => *wa,
        SnapZone::Left => Rect::new(wa.x, wa.y, half, wa.h),
        SnapZone::Right => Rect::new(wa.right() - half, wa.y, half, wa.h),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::anatomy::anatomy;
    use PointerKind::*;

    const G0: Rect = Rect::new(95.0, 64.0, 410.0, 232.0);

    fn wm_with(resizable: bool) -> (WindowManager, WindowId) {
        let mut wm = WindowManager::default();
        let (id, _) = wm.open(OpenSpec { title: "Notes".into(), rect: Some(G0), resizable, ..Default::default() });
        (wm, id)
    }

    fn s(kind: PointerKind, p: Point, t: f64) -> PointerSample {
        PointerSample::new(kind, p.x, p.y, t)
    }

    fn feed(wm: &mut WindowManager, samples: &[PointerSample]) -> Vec<Event> {
        samples.iter().flat_map(|x| wm.pointer(*x)).collect()
    }

    #[test]
    fn work_area_matches_the_gifs() {
        assert_eq!(Desktop::default().work_area(), Rect::new(8.0, 48.0, 584.0, 276.0));
    }

    #[test]
    fn arc_flick_closes_without_shrinking() {
        let (mut wm, id) = wm_with(true);
        let a = Point::new(G0.right() - 12.0, G0.y + 12.0);
        let ev = feed(
            &mut wm,
            &[s(Down, a, 0.0), s(Move, Point::new(a.x - 6.0, a.y + 6.0), 40.0), s(Up, Point::new(a.x - 14.0, a.y + 14.0), 80.0)],
        );
        // while dragging only the arc nudges; the window rect never changed
        assert!(ev.iter().any(|e| matches!(e, Event::ArcNudge { .. })));
        assert!(!ev.iter().any(|e| matches!(e, Event::Resized { .. } | Event::Moved { .. })));
        assert!(ev.iter().any(|e| matches!(e, Event::Closed { id: c, .. } if *c == id)));
        assert!(wm.windows().is_empty());
    }

    #[test]
    fn pill_swipe_down_minimizes_and_up_maximizes() {
        let (mut wm, id) = wm_with(true);
        let pill = anatomy(&G0).pill.center();
        let ev = feed(&mut wm, &[s(Down, pill, 0.0), s(Up, Point::new(pill.x, pill.y + 30.0), 120.0)]);
        assert!(ev.contains(&Event::Minimized { id }));
        assert_eq!(wm.window(id).unwrap().state, WindowState::Minimized);
        // a minimized window can't be hit
        assert_eq!(wm.hit(pill), None);
        wm.focus(id).unwrap();
        assert_eq!(wm.window(id).unwrap().state, WindowState::Normal);

        let ev = feed(&mut wm, &[s(Down, pill, 1000.0), s(Up, Point::new(pill.x, pill.y - 30.0), 1100.0)]);
        let wa = wm.desktop().work_area();
        assert!(ev.contains(&Event::Maximized { id, rect: wa }));
        // swipe down on a maximized window restores it
        let pill_max = anatomy(&wa).pill.center();
        let ev = feed(&mut wm, &[s(Down, pill_max, 2000.0), s(Up, Point::new(pill_max.x, pill_max.y + 30.0), 2100.0)]);
        assert!(ev.contains(&Event::Restored { id, rect: G0 }));
        assert_eq!(wm.window(id).unwrap().rect, G0);
    }

    #[test]
    fn pill_tap_info_and_dots_tap_menu() {
        let (mut wm, id) = wm_with(true);
        let a = anatomy(&G0);
        let ev = feed(&mut wm, &[s(Down, a.pill.center(), 0.0), s(Up, a.pill.center(), 80.0)]);
        assert_eq!(ev, vec![Event::InfoRequested { id }]);
        let ev = feed(&mut wm, &[s(Down, a.dots_center, 200.0), s(Up, a.dots_center, 260.0)]);
        assert_eq!(ev, vec![Event::MenuRequested { id }]);
    }

    #[test]
    fn dots_hold_moves_and_top_edge_snaps_full() {
        let (mut wm, id) = wm_with(true);
        let d = anatomy(&G0).dots_center;
        wm.pointer(s(Down, d, 0.0));
        let ev = wm.tick(400.0);
        assert!(ev.contains(&Event::Lifted { id }));
        let ev = wm.pointer(s(Move, Point::new(d.x + 30.0, d.y + 20.0), 450.0));
        assert!(ev.contains(&Event::Moved { id, rect: G0.translate(30.0, 20.0) }));
        let ev = wm.pointer(s(Move, Point::new(300.0, 30.0), 600.0));
        assert!(ev.iter().any(|e| matches!(e, Event::SnapPreview { zone: Some(SnapZone::Full), .. })));
        let ev = wm.pointer(s(Up, Point::new(300.0, 30.0), 650.0));
        let wa = wm.desktop().work_area();
        assert!(ev.contains(&Event::Snapped { id, zone: SnapZone::Full, rect: wa }));
        assert_eq!(wm.window(id).unwrap().state, WindowState::Maximized);
        assert_eq!(wm.window(id).unwrap().restore_rect, Some(G0));
        assert_eq!(wm.snap_preview(), None);
    }

    #[test]
    fn side_edges_snap_halves() {
        let (mut wm, id) = wm_with(true);
        let d = anatomy(&G0).dots_center;
        wm.pointer(s(Down, d, 0.0));
        wm.tick(400.0);
        wm.pointer(s(Move, Point::new(5.0, 200.0), 500.0));
        wm.pointer(s(Up, Point::new(5.0, 200.0), 550.0));
        let w = wm.window(id).unwrap();
        assert_eq!((w.state, w.snap), (WindowState::Snapped, Some(SnapZone::Left)));
        assert_eq!(w.rect, Rect::new(8.0, 48.0, 288.0, 276.0));
        wm.snap(id, SnapZone::Right).unwrap();
        assert_eq!(wm.window(id).unwrap().rect, Rect::new(304.0, 48.0, 288.0, 276.0));
    }

    #[test]
    fn hidden_corner_resizes_with_handle() {
        let (mut wm, id) = wm_with(true);
        let c = anatomy(&G0).resize_handle;
        let ev = feed(
            &mut wm,
            &[s(Down, c, 0.0), s(Move, Point::new(c.x + 20.0, c.y + 10.0), 50.0), s(Up, Point::new(c.x + 40.0, c.y + 20.0), 100.0)],
        );
        assert_eq!(ev.first(), Some(&Event::ResizeHandle { id, visible: true }));
        assert_eq!(ev.last(), Some(&Event::ResizeHandle { id, visible: false }));
        let r = wm.window(id).unwrap().rect;
        assert_eq!((r.w, r.h), (G0.w + 40.0, G0.h + 20.0));
    }

    #[test]
    fn resize_respects_minimum_and_work_area() {
        let (mut wm, id) = wm_with(true);
        wm.resize(id, 10.0, 10.0).unwrap();
        let r = wm.window(id).unwrap().rect;
        assert_eq!((r.w, r.h), (MIN_W, MIN_H));
        wm.resize(id, 5000.0, 5000.0).unwrap();
        let r = wm.window(id).unwrap().rect;
        let wa = wm.desktop().work_area();
        assert_eq!((r.right(), r.bottom()), (wa.right(), wa.bottom()));
    }

    #[test]
    fn cant_resize_bounces() {
        let (mut wm, id) = wm_with(false);
        let c = anatomy(&G0).resize_handle;
        let ev = feed(&mut wm, &[s(Down, c, 0.0), s(Move, Point::new(c.x + 100.0, c.y + 10.0), 50.0), s(Up, c, 300.0)]);
        assert!(ev.contains(&Event::Bounce { id, dx: BOUNCE_MAX, dy: 5.0 }));
        assert!(ev.contains(&Event::BounceRelease { id }));
        assert_eq!(wm.window(id).unwrap().rect, G0);
        assert_eq!(wm.resize(id, 500.0, 300.0), Err(WmError::NotResizable(id)));
    }

    #[test]
    fn maximize_animates_through_the_scheduler() {
        let (mut wm, id) = wm_with(true);
        wm.tick(1000.0);
        wm.maximize(id).unwrap();
        let wa = wm.desktop().work_area();
        let mid = wm.tick(1150.0);
        let frame = mid.iter().find_map(|e| match e {
            Event::Frame { rect, .. } => Some(*rect),
            _ => None,
        });
        assert!(frame.unwrap().approx_eq(&G0.lerp(&wa, 0.5), 1e-9));
        let end = wm.tick(1300.0);
        assert!(end.contains(&Event::AnimationDone { id }));
        assert!(wm.scheduler().is_empty());
    }

    #[test]
    fn z_order_focus_and_on_top() {
        let mut wm = WindowManager::default();
        let (a, _) = wm.open(OpenSpec { title: "A".into(), rect: Some(G0), resizable: true, ..Default::default() });
        let (b, _) = wm.open(OpenSpec { title: "B".into(), rect: Some(G0), resizable: true, ..Default::default() });
        assert_eq!(wm.focused(), Some(b));
        assert_eq!(wm.hit(G0.center()), Some((b, Part::Content)));
        wm.pointer(PointerSample::new(Down, 1.0, 1.0, 0.0)); // empty desktop: nothing
        wm.focus(a).unwrap();
        assert_eq!(wm.focused(), Some(a));
        wm.set_quick(b, "on_top", true).unwrap();
        assert_eq!(wm.focused(), Some(b));
        wm.focus(a).unwrap();
        assert_eq!(wm.focused(), Some(b), "an on-top window stays above");
    }

    #[test]
    fn menu_actions() {
        let (mut wm, id) = wm_with(true);
        wm.menu_action(id, "keep_on_top").unwrap();
        assert!(wm.window(id).unwrap().quick.on_top);
        assert_eq!(wm.menu(id).unwrap().find("keep_on_top").unwrap().toggle, Some(true));
        wm.menu_action(id, "hide").unwrap();
        assert_eq!(wm.window(id).unwrap().state, WindowState::Minimized);
        assert!(matches!(wm.menu_action(id, "bogus"), Err(WmError::UnknownAction(_))));
        wm.menu_action(id, "quit").unwrap();
        assert!(wm.window(id).is_none());
    }

    #[test]
    fn open_without_rect_fits_the_work_area() {
        let mut wm = WindowManager::new(Desktop::with_size(1920.0, 1080.0));
        let wa = wm.desktop().work_area();
        for i in 0..20 {
            let (id, _) = wm.open(OpenSpec { title: format!("W{i}"), resizable: true, ..Default::default() });
            let r = wm.window(id).unwrap().rect;
            assert!(r.x >= wa.x && r.y >= wa.y && r.right() <= wa.right() + 1e-9 && r.bottom() <= wa.bottom() + 1e-9);
        }
    }

    #[test]
    fn unknown_window_errors() {
        let mut wm = WindowManager::default();
        assert_eq!(wm.minimize(42), Err(WmError::NoSuchWindow(42)));
        assert_eq!(wm.close(42, 0.0, 0.0), Err(WmError::NoSuchWindow(42)));
    }
}
