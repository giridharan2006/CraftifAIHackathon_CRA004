"""MQTT must never be required: an unreachable broker disables publishing and the
JSONL log keeps working. (Delivery to a real broker: scripts/mqtt_smoke_test.sh.)"""
import json
import socket

from event_logger import EventLogger
from incident_processor import IncidentProcessor
from metadata_adapters import Detection, Frame
from mqtt_publisher import MqttPublisher
from zone_manager import zones_from_config


def _closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]   # released on close: nothing listens there


def test_unreachable_broker_disables_publisher():
    pub = MqttPublisher("127.0.0.1", _closed_port(), "workplace_safety/alerts")
    assert pub.enabled is False
    assert pub.publish({"event_id": "incident_0001"}) is False
    pub.close()


def test_incidents_still_logged_when_mqtt_unavailable(cfg, tmp_path):
    pub = MqttPublisher("127.0.0.1", _closed_port(), "workplace_safety/alerts")
    proc = IncidentProcessor(zones_from_config(cfg["zones"]), cfg, EventLogger(tmp_path / "inc.jsonl"),
                             publisher=pub)
    det = Detection(label="person", class_id=None, confidence=0.9, bbox_norm=(0.7, 0.4, 0.8, 0.8), track_id=1)
    for i in range(3):
        proc.process_frame(Frame(frame_id=i, timestamp=f"2026-10-16T12:00:0{i}+00:00", detections=[det]))
    rows = [json.loads(l) for l in (tmp_path / "inc.jsonl").read_text().splitlines()]
    assert [r["event_id"] for r in rows] == ["incident_0001"]
    assert pub.published == 0
