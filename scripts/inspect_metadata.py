#!/usr/bin/env python3
"""Inspect a detection-metadata file written by the generated pipeline (read-only).

Run it on the REAL PipeGen output before the demo to choose METADATA_FORMAT and
check settings.yaml:

    python3 scripts/inspect_metadata.py "$METADATA_PATH" [--lines 300]

It reports which adapter parses the records, the labels/class IDs seen, whether
track IDs are present, and the largest pixel coordinates. DeepStream reports
boxes in the nvstreammux output resolution, so for formats without a frame size
input.frame_width/height must equal the streammux width/height, not the camera's.
Exit code: 0 if one of the adapters parses the records, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config_loader import load_config  # noqa: E402
from metadata_adapters import MetadataError, parse_line  # noqa: E402


def inspect(lines: list[str], cfg: dict) -> dict:
    fw, fh = cfg["input"]["frame_width"], cfg["input"]["frame_height"]
    records = []
    for line in lines:
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append(None)
    report = {"lines": len(records), "invalid_json": records.count(None),
              "top_level_keys": Counter(), "adapters": {}}
    for r in records:
        if isinstance(r, dict):
            report["top_level_keys"].update(r.keys())
    for fmt in ("generic", "deepstream_minimal"):
        ok = dets = 0
        labels, class_ids = Counter(), Counter()
        tracked = 0
        for line in lines:
            try:
                frame = parse_line(line, fmt, fw, fh)
            except MetadataError:
                continue
            if frame is None:
                continue
            ok += 1
            for d in frame.detections:
                dets += 1
                labels[str(d.label)] += 1
                if d.class_id is not None:
                    class_ids[d.class_id] += 1
                if d.track_id is not None:
                    tracked += 1
        report["adapters"][fmt] = {"frames_parsed": ok, "detections": dets,
                                   "labels": dict(labels.most_common(10)),
                                   "class_ids": dict(class_ids.most_common(10)),
                                   "detections_with_track_id": tracked}
    # Raw pixel extents, to compare against the configured / reported frame size.
    max_x = max_y = 0.0
    sizes = Counter()
    for r in records:
        if not isinstance(r, dict):
            continue
        if "width" in r and "height" in r:
            sizes[f"{r['width']}x{r['height']}"] += 1
        for o in r.get("objects", []) if isinstance(r.get("objects"), list) else []:
            if isinstance(o, dict) and isinstance(o.get("bbox"), dict):
                b = o["bbox"]
                try:
                    max_x = max(max_x, float(b["left"]) + float(b["width"]))
                    max_y = max(max_y, float(b["top"]) + float(b["height"]))
                except (KeyError, TypeError, ValueError):
                    pass
            elif isinstance(o, str) and len(o.split("|")) >= 6:
                try:
                    max_x = max(max_x, float(o.split("|")[3]))
                    max_y = max(max_y, float(o.split("|")[4]))
                except ValueError:
                    pass
    report["frame_sizes_in_records"] = dict(sizes)
    report["max_pixel_right_bottom"] = [max_x, max_y]
    report["configured_frame_size"] = [fw, fh]
    report["top_level_keys"] = dict(report["top_level_keys"])
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--lines", type=int, default=300)
    ap.add_argument("--config", default=str(ROOT / "config" / "settings.yaml"))
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    with open(args.path, encoding="utf-8") as fh:
        lines = [l for _, l in zip(range(args.lines), fh)]
    rep = inspect(lines, cfg)
    print(json.dumps(rep, indent=2, default=str))

    person = {l.lower() for l in cfg["detection"]["person_labels"]}
    best = max(rep["adapters"].items(), key=lambda kv: (kv[1]["detections"], kv[1]["frames_parsed"]))
    fmt, a = best
    print("\n== verdict")
    if a["frames_parsed"] == 0 or a["detections"] == 0:
        print("  no adapter extracts detections: map the real field names in src/metadata_adapters.py")
        return 1
    print(f"  METADATA_FORMAT={fmt}  ({a['frames_parsed']} frames, {a['detections']} detections)")
    seen = {l.lower() for l in a["labels"]}
    hit = seen & person
    print(f"  person label match: {sorted(hit) if hit else 'NONE'} (labels seen: {sorted(a['labels'])}; "
          f"settings person_labels={sorted(person)}, person_class_ids={cfg['detection']['person_class_ids']})")
    print(f"  track IDs present on {a['detections_with_track_id']}/{a['detections']} detections")
    mx, my = rep["max_pixel_right_bottom"]
    if not rep["frame_sizes_in_records"]:
        fw, fh = rep["configured_frame_size"]
        warn = " <-- exceeds input.frame_width/height: set them to the streammux resolution" if mx > fw or my > fh else ""
        print(f"  records carry no frame size; max bbox right/bottom = {mx:.0f},{my:.0f} vs configured {fw}x{fh}{warn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
