//! The ••• app menu and the settings sheet, as recommended in docs/APP-MENU.md.
//!
//! File · Edit · View sit in a row at the top; below them the real settings in groups.
//! Minimize and maximize are deliberately NOT here: they live on the pill.

use crate::props::QuickSettings;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MenuItem {
    pub id: String,
    pub label: String,
    /// `Some(checked)` for toggles.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub toggle: Option<bool>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MenuGroup {
    pub name: String,
    pub items: Vec<MenuItem>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct AppMenu {
    pub top_row: Vec<String>,
    pub groups: Vec<MenuGroup>,
}

fn item(id: &str, label: impl Into<String>) -> MenuItem {
    MenuItem { id: id.into(), label: label.into(), toggle: None }
}
fn toggle(id: &str, label: &str, on: bool) -> MenuItem {
    MenuItem { id: id.into(), label: label.into(), toggle: Some(on) }
}

pub fn app_menu(app_name: &str, quick: QuickSettings) -> AppMenu {
    AppMenu {
        top_row: vec!["File".into(), "Edit".into(), "View".into()],
        groups: vec![
            MenuGroup {
                name: "App".into(),
                items: vec![
                    item("about", format!("About {app_name}")),
                    item("settings", "Settings…"),
                    item("shortcuts", "Keyboard Shortcuts"),
                    item("help", "Help & Feedback"),
                ],
            },
            MenuGroup {
                name: "Window".into(),
                items: vec![
                    toggle("keep_on_top", "Keep on Top", quick.on_top),
                    item("snap_layout", "Snap Layout"),
                    toggle("glass", "Glass", quick.glass),
                    item("move_to_desktop", "Move to Desktop"),
                ],
            },
            MenuGroup {
                name: "This app".into(),
                items: vec![
                    toggle("notifications", "Notifications", quick.notify),
                    item("appearance", "Appearance"),
                    item("reset", "Reset App…"),
                ],
            },
            MenuGroup {
                name: "Last".into(),
                items: vec![item("hide", "Hide"), item("quit", format!("Quit {app_name}"))],
            },
        ],
    }
}

/// The settings sheet's sidebar, in order.
pub const SETTINGS_SECTIONS: [&str; 8] = [
    "General",
    "Appearance",
    "Window",
    "Notifications",
    "Permissions",
    "Language",
    "Shortcuts",
    "About",
];

impl AppMenu {
    pub fn find(&self, id: &str) -> Option<&MenuItem> {
        self.groups.iter().flat_map(|g| g.items.iter()).find(|i| i.id == id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn menu_shape_follows_the_doc() {
        let m = app_menu("Notes", QuickSettings::default());
        assert_eq!(m.top_row, ["File", "Edit", "View"]);
        let names: Vec<_> = m.groups.iter().map(|g| g.name.as_str()).collect();
        assert_eq!(names, ["App", "Window", "This app", "Last"]);
        assert_eq!(m.find("about").unwrap().label, "About Notes");
        assert_eq!(m.find("glass").unwrap().toggle, Some(true));
        assert_eq!(m.find("keep_on_top").unwrap().toggle, Some(false));
    }

    #[test]
    fn no_minimize_or_maximize_in_menu() {
        let m = app_menu("Notes", QuickSettings::default());
        for g in &m.groups {
            for i in &g.items {
                let l = i.label.to_lowercase();
                assert!(!l.contains("minimize") && !l.contains("maximize"), "{}", i.label);
            }
        }
    }

    #[test]
    fn ellipsis_only_where_more_input_is_needed() {
        let m = app_menu("Notes", QuickSettings::default());
        assert_eq!(m.find("settings").unwrap().label, "Settings…");
        assert_eq!(m.find("reset").unwrap().label, "Reset App…");
        assert_eq!(SETTINGS_SECTIONS.len(), 8);
    }
}
