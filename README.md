<p align="center">
  <img src="assets/brand/NCOM-Arch-logo.png" alt="NCOM Arch" width="160">
</p>

<p align="center">
  <img src="assets/brand/hero.gif" alt="NCOM Arch: the window system you drive with gestures, not buttons" width="100%">
</p>

# NCOM Arch

- **What it is:** the window system for N•OS. Every window is a 24px rounded glass panel with no title-bar buttons.
- **What it does:** the window's own corners do the work. Flick the corner arc to close. Swipe the pill to minimize or maximize, and tap it for info and properties. Tap ••• for the app menu and settings, or hold it to move and snap. Drag the hidden corner to resize.
- **Why it's better:** no title-bar clutter and no tiny buttons to aim for. Each control is one gesture you learn once, and it sits in the same spot on every window, light or dark.

| Control | Gesture | Result |
|---|---|---|
| Corner arc | flick inward | **Close** (the window keeps its size, then flicks away) |
| Pill | swipe down | **Minimize** to the dock |
| Pill | swipe up | **Maximize** |
| Pill | tap | **Info / properties**: hero banner, file name, size, path, type, dates, quick settings |
| ••• | tap | **App menu / settings** |
| ••• → Settings… | tap | **Settings sheet** |
| ••• | press and hold, drag | **Move** |
| ••• | hold and drag to an edge | **Snap**: top edge = full screen, side = half |
| Hidden corner | drag | **Resize** (the handle shows only while resizing) |
| Corner on a window that can't resize | drag | **Bounce**: the corner stretches and springs back |

---

## Gestures

Each loop ends on its result. The caption bar names the gesture and the RESULT, and the dot with a trail is your finger.

### Flick the corner arc inward → Close
The window does **not** shrink while you drag. Only the arc moves a few pixels with your finger. Think of it as a flick inward: on release, the whole window closes away in the direction of the flick.

<img src="assets/gifs/01-arc-drag-close.gif" alt="Flick the corner arc inward to close" width="600">

### Swipe the pill down → Minimize
The window drops into a chip beside the dock. Tap the chip to bring it back.

<img src="assets/gifs/02-pill-swipe-down-minimize.gif" alt="Swipe the pill down to minimize" width="600">

### Swipe the pill up → Maximize
The window fills the usable screen between the top bar and the dock, and keeps its 24px corners. Swipe down on the pill to restore it.

<img src="assets/gifs/03-pill-swipe-up-maximize.gif" alt="Swipe the pill up to maximize" width="600">

### Tap the pill → Info / properties
A glass Properties panel opens under the corner. The program's hero banner sits on top. Under it are the document's name, its file size, type, created and modified dates, and its file path (for example `C:\Users\Saidie\Documents\Plan.ncom`). At the bottom is a Settings row of quick toggles (On top, Glass, Notify) and an **Open settings…** link to the full settings sheet.

<img src="assets/gifs/04-pill-tap-info.gif" alt="Tap the pill for info and properties" width="600">

### Tap ••• → App menu / settings
The ••• opens the app's own menu. The program's File · Edit · View sit in a row at the top. Below them are the real settings, in groups:
- **App:** About, Settings…, Keyboard Shortcuts, Help & Feedback
- **Window:** Keep on Top, Snap Layout, Glass, Move to Desktop
- **This app:** Notifications, Appearance, Reset App…
- **Last:** Hide and Quit

Minimize and maximize are **not** in this menu. They live on the pill. The research behind this menu is in [docs/APP-MENU.md](docs/APP-MENU.md).

<img src="assets/gifs/05-dots-tap-menu.gif" alt="Tap ••• to open the app menu and settings" width="600">

### Tap Settings… → Settings sheet
A glass settings sheet opens over the window. The sidebar has General, Appearance, Window, Notifications, Permissions, Language, Shortcuts and About. Every change applies at once.

<img src="assets/gifs/05b-dots-menu-settings.gif" alt="Settings sheet from the ••• menu" width="600">

### Hold ••• → Move
Press and hold the ••• and the window lifts: its shadow deepens and it scales up slightly. Drag it, then let go to drop it.

<img src="assets/gifs/06-dots-hold-move.gif" alt="Hold ••• to move the window" width="600">

### Hold ••• and drag to an edge → Snap
Drag to the top edge and a glass preview shows the full screen. Let go and the window fills it. Drag to the left or right edge for a half-screen snap.

<img src="assets/gifs/09-dots-hold-snap.gif" alt="Hold ••• and drag to an edge to snap" width="600">

### Drag the hidden corner → Resize
The resize handle shows only while you resize. Drag the bottom corner and the window grows. The dashed line marks the old size, and the label shows the new size. When you let go, the handle hides again.

<img src="assets/gifs/07-hidden-resize-corner.gif" alt="Drag the hidden corner to resize" width="600">

### Can't resize → Bounce
If a window can't be resized, its corner stretches like a bubble and springs back with a jiggle. That tells you this window doesn't resize.

<img src="assets/gifs/08-corner-bubble-jiggle.gif" alt="Corner bounce on a window that can't be resized" width="600">

---

## Original sketches

These are Saidie's own sketches, videos and markups from October 14, 2026. They define the system.

**The first window sketch.** Drag the corner arc to close. Swipe the pill beside it down to minimize and up to maximize. Tap the ••• at the top for the menu.

<img src="assets/sketches/01-original-window-sketch.jpg" alt="Original NCOM Arch window sketch" width="520">

**The two sketch videos that came with it** (playable loops):

<img src="assets/sketches/07-sketch-video-1.gif" alt="Sketch video 1" width="300"> <img src="assets/sketches/08-sketch-video-2.gif" alt="Sketch video 2" width="300">

**Spec sheet.** Tapping ••• opens the program's menu along the top line. Tapping the pill opens the info popover under the corner: the program's hero banner on top, then the about info, then the options.

<img src="assets/sketches/02-spec-sheet-menu-and-info.jpg" alt="Spec sheet: ••• menu and pill info popover" width="520">

**Markups**, in the order she sent them:

| Pill = minimize / maximize / info. No Minimize or Maximize in the ••• menu. | "Oops ••• menu should be inside and centered." The toolbar was covering it. The next markup replaced this one. | "Oops ••• should be alined level go tab pill." This is the current rule, and it replaces the markup before it. | Corner arc: "not so large". | Corner reference |
|---|---|---|---|---|
| <img src="assets/sketches/03-markup-pill-min-max-info.jpg" width="150"> | <img src="assets/sketches/09-markup-dots-inside-centered.jpg" width="150"> | <img src="assets/sketches/04-markup-dots-level-with-pill.jpg" width="150"> | <img src="assets/sketches/05-markup-corner-not-so-large.jpg" width="150"> | <img src="assets/sketches/06-corner-arc-and-pill-reference.png" width="150"> |

---

## Window anatomy (approved spec)

- **Window:** 24px corner radius, flat edges, a soft drop shadow when floating. The material is refractive glass (Apple liquid-glass style), in light and dark mode.
- **Corner arc:** a short 90° arc on the top-right corner curve only. It's concentric with the 24px radius, inset 7px, 6px thick, with round caps. It does not run down the side.
- **Pill:** 28 × 6 px, on the same line as the arc's top end, with a 13px gap. It's the only place for minimize (swipe down) and maximize (swipe up). Tapping it opens Info / Properties: the hero banner, the file's name, size, path, type and dates, then quick settings.
- **•••:** inside the window, centered on the top frame, level with the pill and the arc's top. Nothing covers it. Tap it for the app menu and settings. Hold it to move, or drag to an edge to snap.
- **Menus and popovers:** the same refractive glass as the windows.
- **Screen:** the desktop also has 24px rounded corners. Windows always fit between the top bar and the dock.

**About the GIFs:** these are animated mockups of the spec, rendered with Python, Pillow and ffmpeg. They aren't screen captures of a live N•OS build.
- The menus, the Info / Properties popover and the settings sheet are rendered as refractive glass. The background bends through the panel with a lens displacement that's strongest at the rounded edges, plus a slight chromatic split at the edge. They also get a thin bright rim along the top edge, a soft inner shadow along the bottom, and a light blur.
- The windows themselves use a lighter frosted rendering, so the gestures stay easy to read.

## Repo layout

```
assets/
  brand/      NCOM Arch logo (PNG 512 / 64, SVG, dark + transparent), hero banner (GIF + PNG),
              official NCOM logo + symbol (unchanged)
  sketches/   Saidie's original sketches, markups and sketch videos (as GIF loops)
  gifs/       one gray UI loop per gesture (600 px wide, under 2 MB each)
docs/
  APP-MENU.md research and the recommended ••• app menu / settings
tools/
  gif-render/ the script that renders the GIFs (Python + Pillow + numpy + ffmpeg)
```

To re-render a GIF, run `python3 tools/gif-render/scenes.py arc_close out.gif`. The scenes are `arc_close`, `pill_minimize`, `pill_maximize`, `pill_info`, `dots_menu`, `dots_settings`, `dots_move`, `dots_snap`, `resize` and `bubble`. You need the Inter font (`NCOM_FONT=/path/to/Inter.ttf`) and ffmpeg.

---

<sub>© NCOM Systems. Design by Saidie. Private repository.</sub>
