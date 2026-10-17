"""Load and validate config/settings.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from metadata_adapters import FORMATS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"

VALID_ANCHORS = {"bottom_center", "center"}


class ConfigError(ValueError):
    """Raised when settings.yaml is missing or invalid."""


def _require_number(section: dict, key: str, where: str, minimum: float | None = None) -> float:
    if key not in section:
        raise ConfigError(f"{where}.{key} is required")
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where}.{key} must be a number, got {value!r}")
    if minimum is not None and value < minimum:
        raise ConfigError(f"{where}.{key} must be >= {minimum}, got {value}")
    return float(value)


def validate_config(cfg: Any) -> dict:
    if not isinstance(cfg, dict):
        raise ConfigError("settings file must contain a YAML mapping")

    zones = cfg.get("zones")
    if not isinstance(zones, list) or not zones:
        raise ConfigError("zones must be a non-empty list")
    seen = set()
    for i, z in enumerate(zones):
        if not isinstance(z, dict) or not z.get("id"):
            raise ConfigError(f"zones[{i}] must be a mapping with an 'id'")
        if z["id"] in seen:
            raise ConfigError(f"duplicate zone id {z['id']!r}")
        seen.add(z["id"])
        # Geometry is validated by zone_manager.Zone itself.

    det = cfg.setdefault("detection", {})
    labels = det.setdefault("person_labels", ["person"])
    class_ids = det.setdefault("person_class_ids", [])
    if not isinstance(labels, list) or not isinstance(class_ids, list):
        raise ConfigError("detection.person_labels and person_class_ids must be lists")
    if not all(isinstance(l, str) and l.strip() for l in labels):
        raise ConfigError("detection.person_labels must contain non-empty strings")
    if not all(isinstance(c, int) and not isinstance(c, bool) for c in class_ids):
        raise ConfigError("detection.person_class_ids must contain integers")
    if not labels and not class_ids:
        raise ConfigError("set detection.person_labels or detection.person_class_ids")
    det.setdefault("min_confidence", 0.4)
    conf = _require_number(det, "min_confidence", "detection", 0.0)
    if conf > 1.0:
        raise ConfigError("detection.min_confidence must be <= 1.0")
    det.setdefault("accept_missing_confidence", True)
    det.setdefault("anchor", "bottom_center")
    if det["anchor"] not in VALID_ANCHORS:
        raise ConfigError(f"detection.anchor must be one of {sorted(VALID_ANCHORS)}")

    inc = cfg.setdefault("incidents", {})
    inc.setdefault("output_path", "data/incidents.jsonl")
    inc.setdefault("stats_path", "data/stats.json")
    inc.setdefault("confirm_frames", 3)
    inc.setdefault("cooldown_seconds", 10.0)
    inc.setdefault("track_timeout_seconds", 5.0)
    cf = inc["confirm_frames"]
    if isinstance(cf, bool) or not isinstance(cf, int) or cf < 1:
        raise ConfigError("incidents.confirm_frames must be an integer >= 1")
    for key in ("output_path", "stats_path"):
        if not isinstance(inc[key], str) or not inc[key].strip():
            raise ConfigError(f"incidents.{key} must be a non-empty path string")
    _require_number(inc, "cooldown_seconds", "incidents", 0.0)
    _require_number(inc, "track_timeout_seconds", "incidents", 0.0)

    inp = cfg.setdefault("input", {})
    inp.setdefault("format", "generic")
    if inp["format"] not in FORMATS:
        raise ConfigError(f"input.format must be one of {list(FORMATS)}")
    inp.setdefault("frame_width", 1920)
    inp.setdefault("frame_height", 1080)
    _require_number(inp, "frame_width", "input", 1)
    _require_number(inp, "frame_height", "input", 1)

    mq = cfg.setdefault("mqtt", {})
    mq.setdefault("enabled", False)
    mq.setdefault("host", "localhost")
    mq.setdefault("port", 1883)
    mq.setdefault("topic", "workplace_safety/alerts")
    mq.setdefault("qos", 1)
    mq.setdefault("client_id", "workplace-safety-sentinel")
    if not isinstance(mq["enabled"], bool):
        raise ConfigError("mqtt.enabled must be true or false")
    if isinstance(mq["qos"], bool) or mq["qos"] not in (0, 1, 2):
        raise ConfigError("mqtt.qos must be 0, 1 or 2")
    port = mq["port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError(f"mqtt.port must be an integer 1-65535, got {port!r}")
    for key in ("host", "topic", "client_id"):
        if not isinstance(mq[key], str) or not mq[key].strip():
            raise ConfigError(f"mqtt.{key} must be a non-empty string")
    if any(c in mq["topic"] for c in "+#"):
        raise ConfigError("mqtt.topic must not contain wildcards (+ or #) for publishing")
    return cfg


def resolve_project_path(p: str | Path) -> Path:
    """Paths in settings.yaml are relative to the project root, not the cwd."""
    path = Path(p)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"settings file not found: {path}")
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    return validate_config(cfg)
