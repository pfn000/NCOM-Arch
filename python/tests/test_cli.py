import json
from ncom_arch.cli import main


def test_scenes(capsys):
    assert main(["scenes"]) == 0
    assert "arc_close" in capsys.readouterr().out


def test_spec(capsys):
    assert main(["spec", "--rect", "95,64,410,232"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["pill"]["w"] == 28 and d["dots_center"]["y"] == 71


def test_frame(tmp_path):
    out = tmp_path / "f.png"
    assert main(["frame", "dots_menu", "2.4", str(out)]) == 0
    assert out.stat().st_size > 1000
