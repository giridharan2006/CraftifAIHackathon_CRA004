from zone_manager import Zone
from zone_to_nvdsanalytics import main, render


def test_render_rectangle_as_four_point_roi():
    text = render([Zone("restricted_zone_1", 0.6, 0.2, 0.95, 0.9)], 1280, 720)
    assert "config-width=1280" in text and "config-height=720" in text
    assert "roi-restricted_zone_1=768;144;1216;144;1216;648;768;648" in text


def test_main_writes_file_for_streammux_size(tmp_path):
    out = tmp_path / "nvdsanalytics.txt"
    assert main(["--width", "1920", "--height", "1080", "--out", str(out)]) == 0
    assert "roi-restricted_zone_1=1152;216;1824;216;1824;972;1152;972" in out.read_text()


def test_main_rejects_bad_size(tmp_path):
    assert main(["--width", "-1", "--height", "720", "--out", str(tmp_path / "x.txt")]) == 2
