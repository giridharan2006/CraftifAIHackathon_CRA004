import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from package_submission import excluded  # noqa: E402


@pytest.mark.parametrize("rel", [
    ".venv/lib/python3.12/site-packages/yaml/__init__.py",
    "src/__pycache__/zone_manager.cpython-312.pyc",
    ".pytest_cache/v/cache/nodeids",
    "dist/old.zip",
    "data/synthetic/incidents_synthetic.jsonl",
    ".env",
    "config/mqtt_credentials.yaml",
    "pipegen_project/export/model_b1_gpu0_fp16.engine",
    "pipegen_project/export/videos/sample.mp4",
])
def test_excluded(rel):
    assert excluded(rel, include_models=False) is not None


@pytest.mark.parametrize("rel", [
    "src/incident_processor.py",
    "README.md",
    "config/settings.yaml",
    "pipegen_project/export/run.sh",
    "reports/evidence/pipegen/04_speed_report.png",
    "data/incidents.jsonl",
])
def test_included(rel):
    assert excluded(rel, include_models=False) is None


def test_models_kept_on_request():
    assert excluded("pipegen_project/export/model.engine", include_models=True) is None
