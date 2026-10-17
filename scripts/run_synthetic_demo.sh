#!/usr/bin/env bash
# Component demo WITHOUT a GPU: replays a SYNTHETIC metadata stream through the
# incident processor. Output goes to data/synthetic/, never to data/incidents.jsonl.
# Usage: scripts/run_synthetic_demo.sh [--mqtt]   (extra args go to incident_processor.py)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
# Project venv if present; never inherit a ROS PYTHONPATH.
PY=python3; [[ -x .venv/bin/python ]] && PY=.venv/bin/python
unset PYTHONPATH
OUT=data/synthetic
"$PY" scripts/make_synthetic_metadata.py "$OUT/metadata_synthetic.jsonl"
rm -f "$OUT/incidents_synthetic.jsonl"   # fresh run: event IDs restart at incident_0001
"$PY" src/incident_processor.py --input "$OUT/metadata_synthetic.jsonl" \
  --output "$OUT/incidents_synthetic.jsonl" --stats "$OUT/stats_synthetic.json" "$@"
echo "--- SYNTHETIC incidents:"; cat "$OUT/incidents_synthetic.jsonl"
echo "--- SYNTHETIC stats:";     cat "$OUT/stats_synthetic.json"; echo
