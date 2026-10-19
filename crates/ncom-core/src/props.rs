//! The pill-tap Info / Properties panel: hero banner, name, size, type, dates, path,
//! then the quick settings row (On top, Glass, Notify).

use serde::{Deserialize, Serialize};

/// What the program tells the window system about the document it shows.
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct DocumentInfo {
    pub name: String,
    pub path: String,
    #[serde(default)]
    pub size_bytes: u64,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub created: String,
    #[serde(default)]
    pub modified: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct QuickSettings {
    pub on_top: bool,
    pub glass: bool,
    pub notify: bool,
}

impl Default for QuickSettings {
    fn default() -> Self {
        Self { on_top: false, glass: true, notify: true }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct PropertiesPanel {
    /// The program's hero banner (its app id; the shell maps it to the banner image).
    pub hero: String,
    pub title: String,
    pub name: String,
    pub size: String,
    pub size_bytes: u64,
    pub kind: String,
    pub created: String,
    pub modified: String,
    pub path: String,
    pub quick: QuickSettings,
    /// The link at the bottom of the panel.
    pub open_settings: String,
}

/// File size the way Windows Explorer shows it (1024-based, one decimal).
pub fn human_size(bytes: u64) -> String {
    const UNITS: [&str; 5] = ["B", "KB", "MB", "GB", "TB"];
    if bytes < 1024 {
        return format!("{bytes} B");
    }
    let mut v = bytes as f64;
    let mut i = 0;
    while v >= 1024.0 && i < UNITS.len() - 1 {
        v /= 1024.0;
        i += 1;
    }
    format!("{v:.1} {}", UNITS[i])
}

pub fn panel(app: &str, title: &str, doc: Option<&DocumentInfo>, quick: QuickSettings) -> PropertiesPanel {
    let d = doc.cloned().unwrap_or_default();
    let name = if d.name.is_empty() { title.to_string() } else { d.name.clone() };
    PropertiesPanel {
        hero: app.to_string(),
        title: title.to_string(),
        name,
        size: if d.path.is_empty() && d.size_bytes == 0 { String::new() } else { human_size(d.size_bytes) },
        size_bytes: d.size_bytes,
        kind: d.kind,
        created: d.created,
        modified: d.modified,
        path: d.path,
        quick,
        open_settings: "Open settings…".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sizes() {
        assert_eq!(human_size(0), "0 B");
        assert_eq!(human_size(999), "999 B");
        assert_eq!(human_size(1536), "1.5 KB");
        assert_eq!(human_size(2048), "2.0 KB");
        assert_eq!(human_size(5 * 1024 * 1024), "5.0 MB");
        assert_eq!(human_size(3 * 1024 * 1024 * 1024), "3.0 GB");
    }

    #[test]
    fn panel_from_document() {
        let doc = DocumentInfo {
            name: "Plan.ncom".into(),
            path: r"C:\Users\Saidie\Documents\Plan.ncom".into(),
            size_bytes: 248_832,
            kind: "NCOM document".into(),
            created: "2026-10-14".into(),
            modified: "2026-10-18".into(),
        };
        let p = panel("notes", "Plan", Some(&doc), QuickSettings::default());
        assert_eq!(p.name, "Plan.ncom");
        assert_eq!(p.size, "243.0 KB");
        assert!(p.quick.glass && p.quick.notify && !p.quick.on_top);
        assert_eq!(p.open_settings, "Open settings…");
    }

    #[test]
    fn panel_without_document_uses_title() {
        let p = panel("calc", "Calculator", None, QuickSettings::default());
        assert_eq!(p.name, "Calculator");
        assert_eq!(p.size, "");
    }
}
