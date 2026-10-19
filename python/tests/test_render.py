import shutil
import pytest
from ncom_arch.render import scenes as SC
from ncom_arch.render.core import CW, CH


def test_all_ten_scenes_exist():
    assert set(SC.SCENES) == {"arc_close", "pill_minimize", "pill_maximize", "pill_info", "dots_menu",
                              "dots_move", "dots_settings", "dots_snap", "resize", "bubble"}


@pytest.mark.parametrize("name", sorted(SC.SCENES))
def test_scene_renders_a_frame(name):
    _, T = SC.SCENES[name](0)
    im, _ = SC.SCENES[name](T * 0.6)
    assert im.size == (CW, CH)
    # not a blank frame
    lo, hi = im.convert("L").getextrema()
    assert hi - lo > 40


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_cli_render_gif(tmp_path, monkeypatch):
    from ncom_arch.cli import main
    monkeypatch.setenv("NCOM_FPS", "4")
    out = tmp_path / "bubble.gif"
    assert main(["render", "bubble", str(out)]) == 0
    assert out.stat().st_size > 1000
