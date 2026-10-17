import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from inspect_metadata import main  # noqa: E402


def test_detects_generic(tmp_path, capsys):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"frame": 1, "width": 1280, "height": 720, "objects": [
        {"label": "person", "track_id": 3, "bbox": {"left": 10, "top": 10, "width": 50, "height": 100}}]}) + "\n")
    assert main([str(p)]) == 0
    out = capsys.readouterr().out
    assert "METADATA_FORMAT=generic" in out and "person label match: ['person']" in out


def test_detects_deepstream_minimal_and_flags_frame_size(tmp_path, capsys):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"id": "1", "objects": ["5|100|100|2400|1300|Person"]}) + "\n")
    assert main([str(p)]) == 0
    out = capsys.readouterr().out
    assert "METADATA_FORMAT=deepstream_minimal" in out
    assert "exceeds input.frame_width/height" in out


def test_unknown_schema_fails(tmp_path, capsys):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"detections": [{"cls": "person"}]}) + "\n")
    assert main([str(p)]) == 1
    assert "map the real field names" in capsys.readouterr().out
