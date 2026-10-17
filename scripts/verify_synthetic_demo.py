#!/usr/bin/env python3
"""Independently check the SYNTHETIC demo output (scripts/run_synthetic_demo.sh).

Recomputes the expected result from the synthetic metadata and the zone in
settings.yaml (without using IncidentProcessor) and compares it with
data/synthetic/incidents_synthetic.jsonl and stats_synthetic.json.
Exit code 0 = every check passed. Synthetic input only: this says nothing about
the PipeGen pipeline or live video.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config_loader import load_config  # noqa: E402

SYN = ROOT / "data" / "synthetic"
results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((bool(ok), msg))


cfg = load_config(ROOT / "config" / "settings.yaml")
z = cfg["zones"][0]
confirm = cfg["incidents"]["confirm_frames"]
labels = {l.lower() for l in cfg["detection"]["person_labels"]}

frames = [json.loads(l) for l in (SYN / "metadata_synthetic.jsonl").read_text().splitlines() if l.strip()]
check(all(f.get("synthetic") is True for f in frames), f"all {len(frames)} metadata frames are flagged synthetic")

# Expected: first frame where each track's bottom-centre is inside, and whether it stays inside.
inside_frames: dict = {}
persons = 0
for f in frames:
    for o in f["objects"]:
        if o["label"].lower() not in labels:
            continue
        persons += 1
        b = o["bbox"]
        x = (b["left"] + b["width"] / 2) / f["width"]
        y = (b["top"] + b["height"]) / f["height"]
        if z["x_min"] <= x <= z["x_max"] and z["y_min"] <= y <= z["y_max"]:
            inside_frames.setdefault(o.get("track_id"), []).append(f["frame"])

raw_lines = (SYN / "incidents_synthetic.jsonl").read_text().splitlines()
try:
    incidents = [json.loads(l) for l in raw_lines if l.strip()]
    check(True, f"incidents_synthetic.jsonl: {len(incidents)} line(s), all valid JSON")
except json.JSONDecodeError as exc:
    incidents = []
    check(False, f"incidents_synthetic.jsonl has invalid JSON: {exc}")

check(set(inside_frames) == {1}, f"only track 1 ever has its feet inside the zone (tracks inside: {sorted(map(str, inside_frames))})")
t1 = inside_frames.get(1, [])
contiguous = t1 == list(range(t1[0], t1[0] + len(t1))) if t1 else False
check(contiguous, f"track 1 enters at frame {t1[0] if t1 else None} and stays inside for {len(t1)} frames")
expected_frame = t1[confirm - 1] if len(t1) >= confirm else None
check(len(incidents) == 1, "exactly one incident although track 1 stays inside for many frames (dedup)")
if incidents:
    r = incidents[0]
    check(r["track_id"] == 1, "incident belongs to track 1 (the person who entered)")
    check(r["frame"] == expected_frame, f"incident fires on frame {expected_frame} = entry + confirm_frames({confirm}) - 1 (got {r['frame']})")
    check(r["object_class"] == "person" and r["event_type"] == "restricted_zone_intrusion", "record type/class correct")
    check(not any(i.get("track_id") == 2 for i in incidents), "track 2 (outside the zone) produced no incident")
    # The forklift is untracked and its bottom-centre IS inside the zone, so if it were
    # treated as a person it would produce an untracked (zone_cooldown) incident.
    fk = next(o for o in frames[0]["objects"] if o["label"] == "forklift")["bbox"]
    fx = (fk["left"] + fk["width"] / 2) / frames[0]["width"]
    fy = (fk["top"] + fk["height"]) / frames[0]["height"]
    fk_inside = z["x_min"] <= fx <= z["x_max"] and z["y_min"] <= fy <= z["y_max"]
    check(fk_inside and not any(i.get("track_id") is None for i in incidents),
          f"forklift feet at ({fx:.3f},{fy:.3f}) are inside the zone yet produced no incident (non-person filtered)")

stats = json.loads((SYN / "stats_synthetic.json").read_text())
check(stats["frames_processed"] == len(frames), f"stats.frames_processed == {len(frames)}")
check(stats["total_detections"] == persons, f"stats.total_detections == {persons} person detections (forklift excluded)")
check(stats["unique_tracked_people"] == 2, "stats.unique_tracked_people == 2")
check(stats["incidents_total"] == len(incidents), "stats.incidents_total matches the JSONL")
check(stats["malformed_records"] == 0, "stats.malformed_records == 0")
check(not (ROOT / "data" / "incidents.jsonl").exists()
      or all(not json.loads(l).get("synthetic") for l in (ROOT / "data" / "incidents.jsonl").read_text().splitlines() if l.strip()),
      "live log data/incidents.jsonl untouched by the synthetic demo")

for ok, msg in results:
    print(f"[{'PASS' if ok else 'FAIL'}] {msg}")
failed = sum(not ok for ok, _ in results)
print(f"SYNTHETIC demo verification: {len(results) - failed}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
