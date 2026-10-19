"""ncom-arch command line."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .spec import Rect, anatomy


def _render_scene(name: str, out: str) -> None:
    from .render import scenes as SC
    from .render.core import FPS, W, H, Image, save_gif

    fn = SC.SCENES[name]
    _, T = fn(0)
    TT = min(T, {"pill_info": 5.0}.get(name, 4.0))
    n = int(round(TT * FPS))
    frames = [fn(i / FPS * T / TT)[0].convert("RGB").resize((W, H), Image.LANCZOS) for i in range(n)]
    save_gif(frames, out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ncom-arch", description="NCOM Arch tools")
    ap.add_argument("--version", action="version", version=f"ncom-arch {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scenes", help="list the gesture scenes")
    f = sub.add_parser("frame", help="render one frame of a scene to PNG (no ffmpeg)")
    f.add_argument("scene"); f.add_argument("t", type=float); f.add_argument("out")
    r = sub.add_parser("render", help="render a scene to GIF (needs ffmpeg)")
    r.add_argument("scene"); r.add_argument("out")
    h = sub.add_parser("hero", help="render the README hero banner (needs ffmpeg)")
    h.add_argument("out_gif"); h.add_argument("out_png", nargs="?")
    s = sub.add_parser("spec", help="print a window's control positions as JSON")
    s.add_argument("--rect", default="95,64,410,232", help="x,y,w,h")
    c = sub.add_parser("call", help="send one JSON request to the native core")
    c.add_argument("request")
    a = ap.parse_args(argv)

    if a.cmd == "scenes":
        from .render.scenes import SCENES
        print("\n".join(SCENES))
    elif a.cmd == "frame":
        from .render.scenes import SCENES
        if a.scene not in SCENES:
            ap.error(f"unknown scene {a.scene!r}; try: {', '.join(SCENES)}")
        SCENES[a.scene](a.t)[0].convert("RGB").save(a.out)
        print(a.out)
    elif a.cmd == "render":
        from .render.scenes import SCENES
        if a.scene not in SCENES:
            ap.error(f"unknown scene {a.scene!r}; try: {', '.join(SCENES)}")
        _render_scene(a.scene, a.out)
        print(a.out)
    elif a.cmd == "hero":
        import runpy
        sys.argv = ["hero", a.out_gif] + ([a.out_png] if a.out_png else [])
        runpy.run_module("ncom_arch.render.hero", run_name="__main__")
    elif a.cmd == "spec":
        print(json.dumps(anatomy(Rect.parse(a.rect)).to_dict(), indent=2))
    elif a.cmd == "call":
        from .native import Core
        with Core() as core:
            print(core.call_json(a.request))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
