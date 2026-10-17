"""Input validation and error handling: malformed metadata, bad settings, CLI paths."""
import copy
import json

import pytest

from conftest import BASE_CFG
from config_loader import DEFAULT_CONFIG_PATH, ConfigError, load_config, validate_config
from incident_processor import follow_file, main
from metadata_adapters import FORMATS, MetadataError, parse_line

PERSON_IN_ZONE = {"label": "person", "confidence": 0.9, "track_id": 1, "bbox_norm": [0.7, 0.4, 0.8, 0.8]}


# --- metadata --------------------------------------------------------------

@pytest.mark.parametrize("w,h", [("abc", 100), (0, 100), (100, -5), (None, 100)])
def test_invalid_frame_size_is_malformed_record(w, h):
    line = json.dumps({"width": w, "height": h, "objects": [PERSON_IN_ZONE]})
    with pytest.raises(MetadataError):
        parse_line(line, "generic", 1920, 1080)


@pytest.mark.parametrize("obj", [
    {"label": "person", "bbox_norm": [float("nan"), 0.1, 0.5, 0.5]},       # NaN (json allows it)
    {"label": "person", "bbox_norm": [0.5, 0.1, 0.4, 0.5]},                 # inverted
    {"label": "person", "bbox_norm": [1.2, 0.1, 1.5, 0.5]},                 # entirely outside frame
    {"label": "person", "bbox": {"left": 10, "top": 10, "width": 0, "height": 50}},   # zero width
    {"label": "person", "bbox": {"left": 10, "top": 10, "width": 20, "height": -5}},  # negative height
    {"label": "person", "bbox": {"left": "x", "top": 10, "width": 20, "height": 50}},  # non-numeric
])
def test_unusable_objects_dropped_rest_of_frame_kept(obj):
    line = json.dumps({"width": 100, "height": 100, "objects": [obj, PERSON_IN_ZONE]})
    frame = parse_line(line, "generic", 0, 0)
    assert len(frame.detections) == 1 and frame.detections[0].track_id == 1


def test_partially_outside_box_is_clamped_not_dropped():
    line = json.dumps({"width": 100, "height": 100, "objects": [
        {"label": "person", "bbox": {"left": 90, "top": 50, "width": 30, "height": 70}}]})
    assert parse_line(line, "generic", 0, 0).detections[0].bbox_norm == pytest.approx((0.9, 0.5, 1.0, 1.0))


def test_deepstream_minimal_drops_inverted_and_nan_boxes():
    line = json.dumps({"objects": ["1|500|100|400|300|Person", "2|NaN|0|10|10|Person", "3|100|100|200|300|Person"]})
    frame = parse_line(line, "deepstream_minimal", 1000, 1000)
    assert [d.track_id for d in frame.detections] == [3]


def test_unknown_format_rejected():
    assert "generic" in FORMATS
    with pytest.raises(MetadataError, match="unknown format"):
        parse_line("{}", "yolo_txt", 100, 100)


# --- settings ----------------------------------------------------------------

def test_shipped_settings_file_is_valid():
    cfg = load_config(DEFAULT_CONFIG_PATH)
    assert cfg["zones"][0]["id"] == "restricted_zone_1"


@pytest.mark.parametrize("section,key,value", [
    ("mqtt", "port", 0),
    ("mqtt", "port", "1883"),
    ("mqtt", "port", True),
    ("mqtt", "topic", "workplace_safety/#"),
    ("mqtt", "host", ""),
    ("mqtt", "enabled", "yes"),
    ("mqtt", "qos", True),
    ("incidents", "confirm_frames", True),
    ("incidents", "output_path", ""),
    ("detection", "person_labels", [1]),
    ("detection", "person_class_ids", ["0"]),
    ("input", "format", "yolo_txt"),
    ("input", "frame_width", 0),
])
def test_invalid_settings_rejected(section, key, value):
    cfg = copy.deepcopy(BASE_CFG)
    cfg[section][key] = value
    with pytest.raises(ConfigError):
        validate_config(cfg)


def test_missing_settings_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_invalid_yaml(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("zones: [unclosed\n")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(p)


# --- CLI ---------------------------------------------------------------------

def _meta(tmp_path):
    p = tmp_path / "meta.jsonl"
    p.write_text("\n".join(json.dumps({"frame": i, "timestamp": f"2026-10-16T12:00:0{i}+00:00",
                                       "width": 100, "height": 100, "objects": [PERSON_IN_ZONE]})
                           for i in range(4)) + "\n")
    return p


def test_cli_relative_output_paths_are_relative_to_cwd(tmp_path, monkeypatch):
    meta = _meta(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["--input", str(meta), "--output", "out/inc.jsonl", "--stats", "out/stats.json"]) == 0
    assert len((tmp_path / "out" / "inc.jsonl").read_text().splitlines()) == 1
    assert json.loads((tmp_path / "out" / "stats.json").read_text())["incidents_total"] == 1


def test_cli_unwritable_output_fails_cleanly(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a directory is needed")
    rc = main(["--input", str(_meta(tmp_path)), "--output", str(blocker / "inc.jsonl"),
               "--stats", str(tmp_path / "s.json")])
    assert rc == 1


def test_cli_rejects_non_positive_idle_exit(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--input", "x.jsonl", "--follow", "--idle-exit", "0"])
    assert exc.value.code == 2


def test_follow_gives_up_when_file_never_appears(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(follow_file(tmp_path / "never.jsonl", idle_exit=0.5))


def test_follow_yields_complete_lines_only(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text('{"a": 1}\n{"b":')   # second line still being written
    assert list(follow_file(p, idle_exit=0.4)) == ['{"a": 1}\n', '{"b":']
