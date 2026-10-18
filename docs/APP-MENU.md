# NCOM ••• app menu: research and recommendation

Saidie, Oct 18 2026, 4:06 PM: *"the three dot app menu is not just file edit view. It's actually the actual settings."*

This note looks at what per-app and per-window menus contain on today's major platforms. From that, it proposes what the NCOM Arch ••• menu should hold. Every source below was fetched on 2026-10-18. Quotes are short excerpts from those pages.

## What the platforms put in their app/window menus

### macOS: the app menu (Apple Human Interface Guidelines, "The menu bar")
Source: https://developer.apple.com/design/human-interface-guidelines/the-menu-bar

- The app menu "lists items that apply to your app or game as a whole, rather than to a specific task, document, or window."
- Standard order:
  - **About *App*** (in a group by itself)
  - **Settings…** ("Use only for app-level settings")
  - optional app-specific configuration items
  - **Services**
  - **Hide *App*** · **Hide Others** · **Show All**
  - **Quit *App***
- Apple keeps the Window menu separate. It "lets people navigate, organize, and manage an app's windows" and holds Minimize, Zoom, tab moves and panels. It "doesn't help people customize the appearance of windows or close them."

### Apple menus in general (HIG, "Menus")
Source: https://developer.apple.com/design/human-interface-guidelines/menus

- "Append an ellipsis to a menu item's label when the action requires more information before it can complete." That's why it's **Settings…** and **Reset App…**.
- Group related items, and "use a separator" between the groups.

### Apple windows: iPadOS / visionOS window controls
Sources:
- https://developer.apple.com/design/human-interface-guidelines/windows
- https://developer.apple.com/videos/play/wwdc2025/208/ (WWDC25, "Elevate the design of your iPad app")

- Windows "include system-provided interface elements such as frames and window controls that let people open, close, resize, and relocate them."
- On iPad (WWDC25), the window controls "become larger on tap, revealing their functionality. If you press and hold, they expand even further, showing a set of shortcuts that quickly create various window layouts."
- This is the same tap-for-menu / hold-for-layout idea as NCOM's tap ••• / hold ••• to move and snap.

### Windows: the window (system) menu, and app settings pages (Microsoft Learn)
Sources:
- https://learn.microsoft.com/en-us/windows/win32/menurc/about-menus
- https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec
- https://learn.microsoft.com/en-us/windows/apps/design/app-settings/guidelines-for-app-settings

- The window menu "provides a standard set of menu items that the user can choose to change a window's size or position, or close the application." It opens with Alt+Spacebar ("Open the context menu for the active window").
- App settings pages should be simple:
  - "make use of binary (on/off) controls. A toggle switch is usually the best control for a binary setting."
  - "When a user changes a setting, the app should immediately reflect the change."
  - Put an **About** section at the bottom of settings, with the "app name, icon, and version number" and links to the repo, bug reports, and dependencies.

### GNOME / libadwaita: the primary menu (GNOME HIG, "Menus")
Source: https://developer.gnome.org/hig/patterns/controls/menus.html

- "Most apps have primary menus, and they are the location for standard features which every app is expected to have."
- Standard items, grouped at the end: **Preferences** · **Keyboard Shortcuts** · **Help** · **About *App*** ("Every primary menu should include this item").
- "Primary menus shouldn't include menu items for Close or Quit: windows can already be closed using the close button in the header bar."

### Browsers: Edge's "Settings and more" ⋯ menu
Source: https://support.microsoft.com/en-us/edge/keyboard-shortcuts-in-microsoft-edge

- In browsers, ⋯ is the app's own menu. Alt+F or Alt+E opens "the Settings and more menu", which is the entry point to the app's Settings page. In Chrome, the same menu is "More".

## What this means for NCOM

1. Every platform has an **app-level menu**: About, Settings…, Shortcuts, Help. NCOM's ••• is that menu, so Saidie is right that it's "the actual settings" entry point and not just File / Edit / View.
2. Window actions that *aren't* min/max/close belong in the menu too. These are layout/snap, keep-on-top and move-to-desktop. Apple and Microsoft put these in a window menu, and iPad puts them on the window controls.
3. NCOM's rule from Oct 14 (5:30 PM) still applies: **no Minimize/Maximize in the ••• menu.** The pill does that, and the arc flick closes. GNOME's rule (no Close in the primary menu, because the window already has a close control) backs this up.
4. The program's own menus (File / Edit / View, from the 5:50 PM spec) stay. They become a compact row at the top of the ••• menu.

## Recommended NCOM ••• menu (what the GIFs show)

```
[ File ][ Edit ][ View ]          ← the program's own menus (5:50 PM spec)
────────────────────────
About Programming
Settings…                    ⌘,
Keyboard Shortcuts           ⌘/
Help & Feedback
────────────────────────
Keep on Top                 (toggle)
Snap Layout                  ›   (halves, quarters, full; same as hold-••• snapping)
Glass                        ›   (clear ↔ frosted, light / dark)
Move to Desktop              ›
────────────────────────
Notifications                ›
Appearance                   ›   (Light · Dark · Auto, accent)
Reset App…
────────────────────────
Hide Programming             ⌘H
Quit Programming             ⌘Q   (quits the whole app; the arc flick closes one window)
```

**Settings… sheet** (05b GIF): a glass sheet over the window.
- Sidebar: General · Appearance · Window · Notifications · Permissions · Language · Shortcuts · About.
- General pane: Open at login (toggle), Appearance (Light / Dark / Auto), Glass (Clear ↔ Frosted slider), Keep window on top (toggle), Notifications (Allowed ›).
- Changes apply at once, per Microsoft's guidance.

**Not in this menu:** Minimize and Maximize (the pill), Close (the arc flick), Resize (the hidden corner).

**Open question for Saidie:** should Full Screen (hiding the top bar and dock) be a menu item? It isn't maximize, but it is close to it, so it's left out until she decides.
