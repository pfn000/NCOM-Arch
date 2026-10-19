//! C ABI over the NCOM Arch core.
//!
//! Every call takes and returns UTF-8 JSON in the protocol documented in `ncom_core::ipc`.
//! Strings returned by this library must be released with [`ncom_string_free`].
//! No panic crosses the boundary: a panic becomes `{"ok":false,"error":"panic: ..."}`.
//! See `include/ncom_arch.h` for the C declarations.

use ncom_core::ipc::Session;
use ncom_core::wm::Desktop;
use std::ffi::{c_char, CStr, CString};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr;

/// Bumped when a function signature in this file changes.
pub const ABI_VERSION: u32 = 1;

/// Opaque session handle.
pub struct NcomSession {
    inner: Session,
}

fn into_c(s: String) -> *mut c_char {
    // JSON never contains an interior NUL, but be safe anyway.
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => CString::new("{\"ok\":false,\"error\":\"interior NUL in response\"}").map(CString::into_raw).unwrap_or(ptr::null_mut()),
    }
}

/// Library version, a static NUL-terminated string. Do not free.
#[no_mangle]
pub extern "C" fn ncom_version() -> *const c_char {
    concat!(env!("CARGO_PKG_VERSION"), "\0").as_ptr() as *const c_char
}

#[no_mangle]
pub extern "C" fn ncom_abi_version() -> u32 {
    ABI_VERSION
}

/// Create a session on a `width` × `height` desktop. Pass 0, 0 for the default 600 × 375.
/// Returns NULL only on allocation failure.
#[no_mangle]
pub extern "C" fn ncom_session_new(width: f64, height: f64) -> *mut NcomSession {
    let desktop = if width > 0.0 && height > 0.0 { Desktop::with_size(width, height) } else { Desktop::default() };
    match catch_unwind(|| Box::new(NcomSession { inner: Session::new(desktop) })) {
        Ok(b) => Box::into_raw(b),
        Err(_) => ptr::null_mut(),
    }
}

/// Free a session. NULL is ignored.
///
/// # Safety
/// `session` must come from [`ncom_session_new`] and must not be used afterwards.
#[no_mangle]
pub unsafe extern "C" fn ncom_session_free(session: *mut NcomSession) {
    if !session.is_null() {
        drop(Box::from_raw(session));
    }
}

/// Run one JSON request. Returns a newly allocated JSON response (free with [`ncom_string_free`]).
///
/// # Safety
/// `session` must be a live handle from [`ncom_session_new`], used by one thread at a time;
/// `request_json` must be a NUL-terminated UTF-8 string.
#[no_mangle]
pub unsafe extern "C" fn ncom_session_call(session: *mut NcomSession, request_json: *const c_char) -> *mut c_char {
    if session.is_null() || request_json.is_null() {
        return into_c("{\"ok\":false,\"error\":\"null argument\"}".to_string());
    }
    let s = &mut *session;
    let req = match CStr::from_ptr(request_json).to_str() {
        Ok(r) => r.to_owned(),
        Err(_) => return into_c("{\"ok\":false,\"error\":\"request is not UTF-8\"}".to_string()),
    };
    let out = catch_unwind(AssertUnwindSafe(|| s.inner.handle_json(&req)));
    into_c(out.unwrap_or_else(|_| "{\"ok\":false,\"error\":\"panic: request aborted\"}".to_string()))
}

/// Hit-test without JSON: writes the window id and part code (see `ncom_arch.h`) and returns 1,
/// or returns 0 when nothing is under the point.
///
/// # Safety
/// `session` must be live; `out_id` and `out_part` must be valid writable pointers.
#[no_mangle]
pub unsafe extern "C" fn ncom_hit_test(session: *const NcomSession, x: f64, y: f64, out_id: *mut u32, out_part: *mut u32) -> i32 {
    if session.is_null() || out_id.is_null() || out_part.is_null() {
        return 0;
    }
    let s = &*session;
    match s.inner.wm().hit(ncom_core::Point::new(x, y)) {
        Some((id, part)) => {
            *out_id = id;
            *out_part = part_code(part);
            1
        }
        None => 0,
    }
}

/// Stable numeric codes for [`ncom_core::Part`] (mirrored in ncom_arch.h and NcomArch.Interop).
pub fn part_code(p: ncom_core::Part) -> u32 {
    use ncom_core::Part::*;
    match p {
        Content => 0,
        CornerArc => 1,
        Pill => 2,
        Dots => 3,
        ResizeCorner => 4,
    }
}

/// Free a string returned by this library. NULL is ignored.
///
/// # Safety
/// `s` must come from this library and must not be freed twice.
#[no_mangle]
pub unsafe extern "C" fn ncom_string_free(s: *mut c_char) {
    if !s.is_null() {
        drop(CString::from_raw(s));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    unsafe fn call(h: *mut NcomSession, req: &str) -> String {
        let c = CString::new(req).unwrap();
        let p = ncom_session_call(h, c.as_ptr());
        let out = CStr::from_ptr(p).to_str().unwrap().to_owned();
        ncom_string_free(p);
        out
    }

    #[test]
    fn version_is_static_and_matches() {
        let v = unsafe { CStr::from_ptr(ncom_version()) }.to_str().unwrap();
        assert_eq!(v, env!("CARGO_PKG_VERSION"));
        assert_eq!(ncom_abi_version(), ABI_VERSION);
    }

    #[test]
    fn call_round_trip_over_the_c_abi() {
        unsafe {
            let h = ncom_session_new(0.0, 0.0);
            assert!(!h.is_null());
            assert!(call(h, r#"{"cmd":"hello"}"#).starts_with(r#"{"ok":true"#));
            let opened = call(h, r#"{"cmd":"open","title":"Notes","rect":{"x":95,"y":64,"w":410,"h":232}}"#);
            assert!(opened.contains(r#""id":1"#), "{opened}");
            let (mut id, mut part) = (0u32, 99u32);
            assert_eq!(ncom_hit_test(h, 451.0, 71.0, &mut id, &mut part), 1);
            assert_eq!((id, part), (1, 2));
            assert_eq!(ncom_hit_test(h, 1.0, 1.0, &mut id, &mut part), 0);
            assert!(call(h, "garbage").starts_with(r#"{"ok":false"#));
            ncom_session_free(h);
        }
    }

    #[test]
    fn null_arguments_are_safe() {
        unsafe {
            let p = ncom_session_call(ptr::null_mut(), ptr::null());
            assert!(CStr::from_ptr(p).to_str().unwrap().contains("null argument"));
            ncom_string_free(p);
            ncom_session_free(ptr::null_mut());
            ncom_string_free(ptr::null_mut());
        }
    }
}
