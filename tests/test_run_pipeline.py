"""scripts/run_pipeline.sh plumbing, with a stub in place of the PipeGen run.sh.

The stub only replays metadata; these tests say nothing about PipeGen itself.
Everything is written under tmp_path so live data/ and reports/ are untouched.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_pipeline.sh"


def _frame(i, left):
    return json.dumps({"frame": i, "timestamp": f"2026-10-16T12:00:{i * 0.1:06.3f}+00:00",
                       "width": 1000, "height": 1000,
                       "objects": [{"label": "person", "confidence": 0.9, "track_id": 1,
                                    "bbox": {"left": left, "top": 400, "width": 100, "height": 400}}]})


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("PIPEGEN_RUN_CMD", "PYTHONPATH")}
    env.update(extra)
    return env


def test_missing_export_reports_reason(tmp_path):
    # Copy the script into an empty project so pipegen_project/export/ does not exist.
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "run_pipeline.sh")
    r = subprocess.run(["bash", str(tmp_path / "scripts" / "run_pipeline.sh")],
                       env=_env(METADATA_PATH=str(tmp_path / "m.jsonl")),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode != 0
    assert "no run.sh under pipegen_project/export/" in r.stderr


def test_stub_pipeline_feeds_processor_in_follow_mode(tmp_path):
    src = tmp_path / "source.jsonl"
    src.write_text("\n".join(_frame(i, 100 + 60 * i) for i in range(12)) + "\n")
    meta = tmp_path / "stream.jsonl"
    stub = tmp_path / "stub.py"
    stub.write_text(
        "import sys, time\n"
        "with open(sys.argv[2], 'w') as o:\n"
        "    for l in open(sys.argv[1]):\n"
        "        o.write(l); o.flush(); time.sleep(0.02)\n")
    inc, stats, evid = tmp_path / "inc.jsonl", tmp_path / "stats.json", tmp_path / "evid"
    r = subprocess.run(
        ["bash", str(SCRIPT)],
        env=_env(PIPEGEN_RUN_CMD=f"'{sys.executable}' '{stub}' '{src}' '{meta}'",
                 METADATA_PATH=str(meta), INCIDENTS_PATH=str(inc), STATS_PATH=str(stats),
                 EVIDENCE_DIR=str(evid), IDLE_EXIT="2"),
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    records = [json.loads(l) for l in inc.read_text().splitlines()]
    # feet x = (100 + 60i + 50)/1000 >= 0.6 from i = 8; confirmed on 3rd inside frame (i = 10)
    assert [(x["track_id"], x["frame"]) for x in records] == [(1, 10)]
    assert json.loads(stats.read_text())["frames_processed"] == 12
    run_log = next(evid.glob("pipeline_run_*.log")).read_text()
    assert "exit: 0" in run_log
