//! The NCOM Arch IPC protocol: one JSON request per line in, one JSON response per line out.
//!
//! The same protocol runs over the C ABI (`ncom_session_call` in `ncom_arch.dll`), over
//! `ncomd` (stdio or TCP) and over the Windows named pipe `\\.\pipe\ncom-arch` hosted by the
//! .NET shell service.
//!
//! ```text
//! -> {"cmd":"open","title":"Notes","rect":{"x":95,"y":64,"w":410,"h":232}}
//! <- {"ok":true,"result":{"id":1},"events":[{"event":"opened","id":1,...},{"event":"focused","id":1}]}
//! -> {"cmd":"pointer","kind":"down","x":451,"y":71,"t_ms":0}
//! ```

use crate::anatomy::{anatomy, hit_test, Part};
use crate::geometry::{Point, Rect};
use crate::gesture::{PointerKind, PointerSample};
use crate::menu::SETTINGS_SECTIONS;
use crate::props::DocumentInfo;
use crate::wm::{Desktop, Event, OpenSpec, SnapZone, WindowId, WindowManager, WmError};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

/// Bumped on any breaking change to the request / response shapes.
pub const PROTOCOL_VERSION: u32 = 1;

fn default_true() -> bool {
    true
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "cmd", rename_all = "snake_case")]
pub enum Request {
    Hello,
    Configure {
        desktop: Desktop,
    },
    Open {
        title: String,
        #[serde(default)]
        app: Option<String>,
        #[serde(default)]
        rect: Option<Rect>,
        #[serde(default = "default_true")]
        resizable: bool,
        #[serde(default)]
        document: Option<DocumentInfo>,
    },
    Close {
        id: WindowId,
    },
    Minimize {
        id: WindowId,
    },
    Maximize {
        id: WindowId,
    },
    Restore {
        id: WindowId,
    },
    Focus {
        id: WindowId,
    },
    Snap {
        id: WindowId,
        zone: SnapZone,
    },
    Move {
        id: WindowId,
        x: f64,
        y: f64,
    },
    Resize {
        id: WindowId,
        w: f64,
        h: f64,
    },
    Pointer {
        kind: PointerKind,
        x: f64,
        y: f64,
        t_ms: f64,
    },
    Tick {
        t_ms: f64,
    },
    List,
    HitTest {
        x: f64,
        y: f64,
    },
    Anatomy {
        id: WindowId,
    },
    Properties {
        id: WindowId,
    },
    Menu {
        id: WindowId,
    },
    MenuAction {
        id: WindowId,
        action: String,
    },
    SetQuick {
        id: WindowId,
        key: String,
        value: bool,
    },
    SettingsSections,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Response {
    pub ok: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub events: Vec<Event>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl Response {
    pub fn ok(result: Option<Value>, events: Vec<Event>) -> Self {
        Self { ok: true, result, events, error: None }
    }
    pub fn err(msg: impl Into<String>) -> Self {
        Self { ok: false, result: None, events: Vec::new(), error: Some(msg.into()) }
    }
}

impl From<WmError> for Response {
    fn from(e: WmError) -> Self {
        Response::err(e.to_string())
    }
}

/// One client's view of the window system.
#[derive(Clone, Debug, Default)]
pub struct Session {
    wm: WindowManager,
}

fn to_value<T: Serialize>(v: &T) -> Value {
    serde_json::to_value(v).unwrap_or(Value::Null)
}

impl Session {
    pub fn new(desktop: Desktop) -> Self {
        Self { wm: WindowManager::new(desktop) }
    }
    pub fn wm(&self) -> &WindowManager {
        &self.wm
    }
    pub fn wm_mut(&mut self) -> &mut WindowManager {
        &mut self.wm
    }

    pub fn handle(&mut self, req: Request) -> Response {
        let events = |r: Result<Vec<Event>, WmError>| match r {
            Ok(ev) => Response::ok(None, ev),
            Err(e) => e.into(),
        };
        match req {
            Request::Hello => Response::ok(
                Some(json!({
                    "name": "NCOM Arch",
                    "version": crate::VERSION,
                    "protocol": PROTOCOL_VERSION,
                    "desktop": to_value(self.wm.desktop()),
                    "work_area": to_value(&self.wm.desktop().work_area()),
                    "anatomy": {
                        "corner_radius": crate::anatomy::CORNER_RADIUS,
                        "arc_inset": crate::anatomy::ARC_INSET,
                        "arc_thickness": crate::anatomy::ARC_THICKNESS,
                        "pill": [crate::anatomy::PILL_W, crate::anatomy::PILL_H],
                        "pill_gap": crate::anatomy::PILL_GAP,
                    }
                })),
                vec![],
            ),
            Request::Configure { desktop } => {
                self.wm.set_desktop(desktop);
                Response::ok(Some(json!({ "work_area": to_value(&desktop.work_area()) })), vec![])
            }
            Request::Open { title, app, rect, resizable, document } => {
                let (id, ev) = self.wm.open(OpenSpec { title, app, rect, resizable, document });
                Response::ok(Some(json!({ "id": id })), ev)
            }
            Request::Close { id } => events(self.wm.close(id, 0.0, 0.0)),
            Request::Minimize { id } => events(self.wm.minimize(id)),
            Request::Maximize { id } => events(self.wm.maximize(id)),
            Request::Restore { id } => events(self.wm.restore(id)),
            Request::Focus { id } => events(self.wm.focus(id)),
            Request::Snap { id, zone } => events(self.wm.snap(id, zone)),
            Request::Move { id, x, y } => events(self.wm.move_to(id, x, y)),
            Request::Resize { id, w, h } => events(self.wm.resize(id, w, h)),
            Request::Pointer { kind, x, y, t_ms } => Response::ok(None, self.wm.pointer(PointerSample::new(kind, x, y, t_ms))),
            Request::Tick { t_ms } => Response::ok(None, self.wm.tick(t_ms)),
            Request::List => Response::ok(
                Some(json!({ "windows": to_value(&self.wm.windows()), "focused": self.wm.focused() })),
                vec![],
            ),
            Request::HitTest { x, y } => {
                let hit = self.wm.hit(Point::new(x, y));
                Response::ok(
                    Some(match hit {
                        Some((id, part)) => json!({ "id": id, "part": to_value(&part) }),
                        None => Value::Null,
                    }),
                    vec![],
                )
            }
            Request::Anatomy { id } => match self.wm.window(id) {
                Some(w) => {
                    let a = anatomy(&w.rect);
                    let probe: Vec<(Part, Option<Part>)> = vec![
                        (Part::Pill, hit_test(&w.rect, a.pill.center())),
                        (Part::Dots, hit_test(&w.rect, a.dots_center)),
                        (Part::ResizeCorner, hit_test(&w.rect, a.resize_handle)),
                    ];
                    let consistent = probe.iter().all(|(want, got)| Some(*want) == *got);
                    Response::ok(Some(json!({ "anatomy": to_value(&a), "consistent": consistent })), vec![])
                }
                None => WmError::NoSuchWindow(id).into(),
            },
            Request::Properties { id } => match self.wm.properties(id) {
                Ok(p) => Response::ok(Some(to_value(&p)), vec![]),
                Err(e) => e.into(),
            },
            Request::Menu { id } => match self.wm.menu(id) {
                Ok(m) => Response::ok(Some(to_value(&m)), vec![]),
                Err(e) => e.into(),
            },
            Request::MenuAction { id, action } => events(self.wm.menu_action(id, &action)),
            Request::SetQuick { id, key, value } => events(self.wm.set_quick(id, &key, value)),
            Request::SettingsSections => Response::ok(Some(json!(SETTINGS_SECTIONS)), vec![]),
        }
    }

    /// Parse one JSON request, run it, and return the JSON response (never panics on bad input).
    pub fn handle_json(&mut self, line: &str) -> String {
        let resp = match serde_json::from_str::<Request>(line.trim()) {
            Ok(req) => self.handle(req),
            Err(e) => Response::err(format!("bad request: {e}")),
        };
        serde_json::to_string(&resp).unwrap_or_else(|e| format!("{{\"ok\":false,\"error\":\"encode: {e}\"}}"))
    }
}

/// Serve JSON lines until EOF: one response line per non-empty request line.
pub fn serve<R: BufRead, W: Write>(session: &mut Session, reader: R, mut writer: W) -> io::Result<usize> {
    let mut n = 0;
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        writeln!(writer, "{}", session.handle_json(&line))?;
        writer.flush()?;
        n += 1;
    }
    Ok(n)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn call(s: &mut Session, req: Value) -> Value {
        serde_json::from_str(&s.handle_json(&req.to_string())).unwrap()
    }

    #[test]
    fn hello_reports_protocol_and_anatomy() {
        let mut s = Session::default();
        let r = call(&mut s, json!({"cmd": "hello"}));
        assert_eq!(r["ok"], true);
        assert_eq!(r["result"]["protocol"], PROTOCOL_VERSION);
        assert_eq!(r["result"]["anatomy"]["corner_radius"], 24.0);
        assert_eq!(r["result"]["work_area"]["y"], 48.0);
    }

    #[test]
    fn open_gesture_and_list_round_trip() {
        let mut s = Session::default();
        let r = call(&mut s, json!({"cmd":"open","title":"Notes","rect":{"x":95,"y":64,"w":410,"h":232}}));
        assert_eq!(r["result"]["id"], 1);
        assert_eq!(r["events"][0]["event"], "opened");
        // swipe the pill (451, 71) down
        call(&mut s, json!({"cmd":"pointer","kind":"down","x":451,"y":71,"t_ms":0}));
        let r = call(&mut s, json!({"cmd":"pointer","kind":"up","x":451,"y":101,"t_ms":120}));
        assert_eq!(r["events"][0]["event"], "minimized");
        let r = call(&mut s, json!({"cmd":"list"}));
        assert_eq!(r["result"]["windows"][0]["state"], "minimized");
        assert_eq!(r["result"]["focused"], Value::Null);
    }

    #[test]
    fn errors_are_responses_not_panics() {
        let mut s = Session::default();
        let r = call(&mut s, json!({"cmd":"maximize","id":9}));
        assert_eq!(r["ok"], false);
        assert_eq!(r["error"], "no window with id 9");
        let bad: Value = serde_json::from_str(&s.handle_json("{not json")).unwrap();
        assert_eq!(bad["ok"], false);
        let unknown: Value = serde_json::from_str(&s.handle_json(r#"{"cmd":"explode"}"#)).unwrap();
        assert_eq!(unknown["ok"], false);
    }

    #[test]
    fn properties_menu_and_anatomy() {
        let mut s = Session::default();
        call(
            &mut s,
            json!({"cmd":"open","title":"Plan","app":"Notes","document":{"name":"Plan.ncom","path":"C:\\Users\\Saidie\\Documents\\Plan.ncom","size_bytes":2048}}),
        );
        let p = call(&mut s, json!({"cmd":"properties","id":1}));
        assert_eq!(p["result"]["size"], "2.0 KB");
        assert_eq!(p["result"]["hero"], "Notes");
        let m = call(&mut s, json!({"cmd":"menu","id":1}));
        assert_eq!(m["result"]["top_row"], json!(["File", "Edit", "View"]));
        let a = call(&mut s, json!({"cmd":"anatomy","id":1}));
        assert_eq!(a["result"]["consistent"], true);
        let q = call(&mut s, json!({"cmd":"set_quick","id":1,"key":"glass","value":false}));
        assert_eq!(q["events"][0]["quick"]["glass"], false);
        let secs = call(&mut s, json!({"cmd":"settings_sections"}));
        assert_eq!(secs["result"][0], "General");
    }

    #[test]
    fn serve_answers_each_line() {
        let mut s = Session::default();
        let input = "{\"cmd\":\"hello\"}\n\n{\"cmd\":\"list\"}\n";
        let mut out = Vec::new();
        let n = serve(&mut s, input.as_bytes(), &mut out).unwrap();
        assert_eq!(n, 2);
        let text = String::from_utf8(out).unwrap();
        assert_eq!(text.lines().count(), 2);
        assert!(text.lines().all(|l| l.starts_with("{\"ok\":true")));
    }

    #[test]
    fn requests_serialize_to_the_documented_shape() {
        let r = Request::Pointer { kind: PointerKind::Down, x: 1.0, y: 2.0, t_ms: 3.0 };
        assert_eq!(serde_json::to_value(&r).unwrap(), json!({"cmd":"pointer","kind":"down","x":1.0,"y":2.0,"t_ms":3.0}));
        assert_eq!(serde_json::to_value(Request::Hello).unwrap(), json!({"cmd":"hello"}));
    }
}
