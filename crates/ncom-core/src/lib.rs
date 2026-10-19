//! # NCOM Arch core
//!
//! The window system for N•OS, as specified in the repository README:
//! every window is a 24px rounded glass panel with no title-bar buttons, and the
//! window's own corners do the work.
//!
//! | Control        | Gesture                    | Result                         |
//! |----------------|----------------------------|--------------------------------|
//! | Corner arc     | flick inward               | Close                          |
//! | Pill           | swipe down / up / tap      | Minimize / Maximize / Info     |
//! | •••            | tap / hold + drag / edge   | App menu / Move / Snap         |
//! | Hidden corner  | drag                       | Resize (or Bounce)             |
//!
//! Modules:
//! - [`geometry`]: points and rectangles.
//! - [`anatomy`]: the approved window anatomy (arc, pill, •••, hidden corner) and hit testing.
//! - [`gesture`]: the per-pointer gesture recognizer.
//! - [`wm`]: the window manager (z-order, focus, minimize/maximize/snap/move/resize).
//! - [`anim`]: easing curves and the animation scheduler (tweens driven by ticks).
//! - [`menu`] / [`props`]: the ••• app menu, the settings sheet and the pill's Properties panel.
//! - [`ipc`]: the JSON-lines protocol spoken over the FFI boundary, `ncomd` and the Windows named pipe.

pub mod anatomy;
pub mod anim;
pub mod geometry;
pub mod gesture;
pub mod ipc;
pub mod menu;
pub mod props;
pub mod wm;

pub use anatomy::{hit_test, Part};
pub use geometry::{Point, Rect};
pub use gesture::{Gesture, PointerKind, PointerSample};
pub use ipc::{Request, Response, Session, PROTOCOL_VERSION};
pub use wm::{Desktop, Event, SnapZone, Window, WindowId, WindowManager, WindowState, WmError};

/// Crate version, also reported by the `hello` IPC command.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
