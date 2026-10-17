"""Convert detection metadata emitted by the perception pipeline into Frames.

Two input formats are supported:

generic (one JSON object per frame, per line):
    {"frame": 12, "timestamp": "2026-10-16T15:00:00.000Z", "source_id": 0,
     "width": 1920, "height": 1080,
     "objects": [{"label": "person", "class_id": 0, "confidence": 0.91,
                  "track_id": 3,
                  "bbox": {"left": 1200, "top": 300, "width": 150, "height": 420}}]}
  * "bbox" is in pixels (DeepStream rect_params convention: left/top/width/height)
    and needs frame width/height; alternatively give "bbox_norm": [x1, y1, x2, y2].
  * timestamp, source_id, class_id, confidence, track_id are optional.

deepstream_minimal (DeepStream nvmsgconv payload-type 1, one message per line):
    {"version": "4.0", "id": "12", "@timestamp": "...", "sensorId": "cam0",
     "objects": ["3|1200|300|1350|720|Person", ...]}
  * object string fields used: trackId|left|top|right|bottom|label (pixels).
  * frame size is not part of this schema, so it comes from settings.yaml.
  * This adapter follows the published nvmsgconv schema; verify it against the
    actual output of your generated pipeline before relying on it.

A record that cannot be used at all (invalid JSON, wrong types, invalid frame
size) raises MetadataError. A single unusable object (missing/non-finite
coordinates, zero or negative size) is dropped and the rest of the frame kept.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Optional

# DeepStream reports untracked objects with UNTRACKED_OBJECT_ID (0xFFFFFFFFFFFFFFFF).
_UNTRACKED_IDS = {-1, 0xFFFFFFFFFFFFFFFF}


class MetadataError(ValueError):
    """Raised when a metadata record cannot be parsed."""


@dataclass
class Detection:
    label: Optional[str]
    class_id: Optional[int]
    confidence: Optional[float]
    bbox_norm: tuple[float, float, float, float]  # x1, y1, x2, y2 in 0..1
    track_id: Optional[Any] = None


@dataclass
class Frame:
    frame_id: Optional[Any]
    timestamp: Optional[str]
    source_id: Any = 0
    detections: list[Detection] = field(default_factory=list)


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _finite(raw: Any) -> float:
    """float(raw), rejecting NaN/inf (json.loads accepts NaN and Infinity)."""
    v = float(raw)
    if not math.isfinite(v):
        raise ValueError(f"non-finite value {raw!r}")
    return v


def _frame_size(w: Any, h: Any) -> tuple[float, float]:
    try:
        fw, fh = _finite(w), _finite(h)
    except (TypeError, ValueError) as exc:
        raise MetadataError(f"invalid frame size {w!r}x{h!r}") from exc
    if fw <= 0 or fh <= 0:
        raise MetadataError(f"frame width/height must be positive, got {w!r}x{h!r}")
    return fw, fh


def _box(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float]:
    """Clamp a normalized box to the frame; reject it if nothing of it is left."""
    box = (_clamp01(x1), _clamp01(y1), _clamp01(x2), _clamp01(y2))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"empty or inverted box {box}")
    return box


def _norm_box(x1: float, y1: float, x2: float, y2: float, w: float, h: float) -> tuple[float, float, float, float]:
    return _box(x1 / w, y1 / h, x2 / w, y2 / h)


def _track_id(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    try:
        as_int = int(raw)
    except (TypeError, ValueError):
        return raw
    return None if as_int in _UNTRACKED_IDS else as_int


def _opt_float(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _opt_int(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def parse_generic(record: dict, default_w: float, default_h: float) -> Frame:
    if not isinstance(record, dict):
        raise MetadataError("record is not a JSON object")
    w, h = _frame_size(record.get("width", default_w), record.get("height", default_h))
    objects = record.get("objects", [])
    if not isinstance(objects, list):
        raise MetadataError("'objects' must be a list")
    dets = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue  # skip a single malformed object, keep the rest of the frame
        try:
            if "bbox_norm" in obj:
                x1, y1, x2, y2 = (_finite(v) for v in obj["bbox_norm"])
                box = _box(x1, y1, x2, y2)
            else:
                b = obj["bbox"]
                left, top = _finite(b["left"]), _finite(b["top"])
                box = _norm_box(left, top, left + _finite(b["width"]), top + _finite(b["height"]), w, h)
        except (KeyError, TypeError, ValueError):
            continue
        dets.append(
            Detection(
                label=obj.get("label"),
                class_id=_opt_int(obj.get("class_id")),
                confidence=_opt_float(obj.get("confidence")),
                bbox_norm=box,
                track_id=_track_id(obj.get("track_id")),
            )
        )
    return Frame(
        frame_id=record.get("frame"),
        timestamp=record.get("timestamp"),
        source_id=record.get("source_id", 0),
        detections=dets,
    )


def parse_deepstream_minimal(record: dict, frame_w: float, frame_h: float) -> Frame:
    if not isinstance(record, dict):
        raise MetadataError("record is not a JSON object")
    w, h = _frame_size(frame_w, frame_h)
    objects = record.get("objects", [])
    if not isinstance(objects, list):
        raise MetadataError("'objects' must be a list")
    dets = []
    for obj in objects:
        if not isinstance(obj, str):
            continue
        parts = obj.split("|")
        if len(parts) < 6:
            continue
        try:
            left, top, right, bottom = (_finite(p) for p in parts[1:5])
            box = _norm_box(left, top, right, bottom, w, h)
        except ValueError:
            continue
        dets.append(
            Detection(
                label=parts[5],
                class_id=None,
                confidence=None,
                bbox_norm=box,
                track_id=_track_id(parts[0]),
            )
        )
    return Frame(
        frame_id=record.get("id"),
        timestamp=record.get("@timestamp"),
        source_id=record.get("sensorId", 0),
        detections=dets,
    )


def parse_line(line: str, fmt: str, frame_w: float, frame_h: float) -> Optional[Frame]:
    """Parse one line. Returns None for blank lines, raises MetadataError if malformed."""
    line = line.strip()
    if not line:
        return None
    parser = _PARSERS.get(fmt)
    if parser is None:
        raise MetadataError(f"unknown format {fmt!r}; expected one of {FORMATS}")
    try:
        record = json.loads(line)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"invalid JSON: {exc}") from exc
    return parser(record, frame_w, frame_h)


_PARSERS = {"generic": parse_generic, "deepstream_minimal": parse_deepstream_minimal}
FORMATS = tuple(_PARSERS)  # single source of truth for config validation and the CLI
