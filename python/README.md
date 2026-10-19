# ncom-arch (Python)

The Python side of NCOM Arch:

- `ncom_arch.spec`: the approved window anatomy (24px corners, arc, pill, •••, hidden corner) and hit testing, in pure Python. It mirrors the Rust core and the tests check both agree.
- `ncom_arch.native`: `ctypes` bindings to the Rust core library (`ncom_arch.dll` / `libncom_arch.so`). Set `NCOM_ARCH_LIB` to its path.
- `ncom_arch.client`: a JSON-lines client for `ncomd --listen` (TCP) and the Windows shell's named pipe `\\.\pipe\ncom-arch`.
- `ncom_arch.render`: the gesture GIF and hero banner renderer (formerly `tools/gif-render`).
- `ncom-arch` CLI.

```bash
pip install -e "python[dev]"
pytest python/tests
ncom-arch scenes                          # list the gesture scenes
ncom-arch frame arc_close 1.0 out.png     # one frame, no ffmpeg needed
ncom-arch render arc_close out.gif        # a GIF (needs ffmpeg)
ncom-arch hero hero.gif hero.png          # the README banner (needs ffmpeg)
ncom-arch spec --rect 95,64,410,232       # control positions as JSON
NCOM_ARCH_LIB=target/release/libncom_arch.so ncom-arch call '{"cmd":"hello"}'
```

Fonts: the renderer uses Inter (`NCOM_FONT=/path/to/Inter.ttf`) and falls back to Pillow's built-in font.
