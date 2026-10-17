#!/usr/bin/env bash
# Evidence-based status check. A stage is only reported COMPLETE if its artifact exists.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
ok()   { printf "  [COMPLETE]     %-38s %s\n" "$1" "$2"; }
miss() { printf "  [NOT VERIFIED] %-38s %s\n" "$1" "$2"; }
first() { find "$@" 2>/dev/null | head -1; }
# Prefer the project venv; ROS setups export a PYTHONPATH that must not leak in.
PY=python3; [[ -x .venv/bin/python ]] && PY=.venv/bin/python
unset PYTHONPATH

echo "== Unit tests"; $PY -m pytest -q 2>&1 | tail -3
echo "== Config";     $PY -c "import sys; sys.path.insert(0,'src'); from config_loader import load_config; from zone_manager import zones_from_config; c=load_config('config/settings.yaml'); print('  settings.yaml valid; zones:', [z.id for z in zones_from_config(c['zones'])])"
echo "== PipeGen v0.5.1: $(pipegen --version 2>/dev/null || echo NOT INSTALLED)"
echo "== PipeGen evidence (reports/evidence/pipegen, pipegen_project/)"
f=$(first reports/evidence/pipegen -iname '*requirement*'); [[ -n "$f" ]] && ok "1 Requirement" "$f" || miss "1 Requirement" "draft in pipegen_project/requirement.md; export PipeGen's copy to reports/evidence/pipegen/"
f=$(first reports/evidence/pipegen \( -iname '*pipeline_ir*' -o -iname '*graph*' \)); [[ -n "$f" ]] && ok "2 Pipeline IR" "$f" || miss "2 Pipeline IR" "no IR artifact found"
f=$(first pipegen_project reports/evidence/pipegen \( -name '*.onnx' -o -name '*.etlt' -o -iname '*model*.txt' -o -iname 'labels*.txt' \)); [[ -n "$f" ]] && ok "3 Model" "$f" || miss "3 Model" "no model/label file found"
f=$(first "$ROOT" -name '*.engine'); [[ -z "$f" ]] && f=$(first reports/evidence/pipegen -iname '*engine*'); [[ -n "$f" ]] && ok "4 TensorRT engine" "$f" || miss "4 TensorRT engine" "no *.engine found"
f=$(first reports/evidence/pipegen -iname '*speed*'); [[ -n "$f" ]] && ok "4 Speed report" "$f" || miss "4 Speed report" "no speed report in reports/evidence/pipegen/"
f=$(first pipegen_project/export -name run.sh); [[ -n "$f" ]] && ok "5 PipeGen export (run.sh)" "$f" || miss "5 PipeGen export (run.sh)" "export the PipeGen project to pipegen_project/export/"
# A run only counts if run_pipeline.sh recorded "exit: 0" for the generated pipeline.
f=$(grep -l '^# finished: .* exit: 0$' reports/evidence/pipeline_runs/pipeline_run_*.log 2>/dev/null | head -1)
if [[ -n "$f" ]]; then ok "5 Run (pipeline log, exit 0)" "$f"
else f=$(first reports/evidence/pipeline_runs -name 'pipeline_run_*.log'); miss "5 Run (pipeline log)" "${f:+only failed/unfinished runs, e.g. $f; }run scripts/run_pipeline.sh on the GPU machine"; fi
echo "== Actionable output"
if [[ -s data/incidents.jsonl ]]; then ok "Live incidents (data/incidents.jsonl)" "$(wc -l < data/incidents.jsonl) record(s)"; else miss "Live incidents" "data/incidents.jsonl empty/absent"; fi
# MQTT evidence from scripts/mqtt_smoke_test.sh (synthetic input) and from a live run.
[[ -s reports/evidence/synthetic_demo/mqtt_subscriber_received.txt ]] && ok "MQTT (component, synthetic input)" "reports/evidence/synthetic_demo/mqtt_subscriber_received.txt" || miss "MQTT (component)" "run scripts/mqtt_smoke_test.sh"
[[ -s reports/evidence/pipeline_runs/mqtt_subscriber_live.txt ]] && ok "MQTT (live pipeline)" "reports/evidence/pipeline_runs/mqtt_subscriber_live.txt" || miss "MQTT (live pipeline)" "not captured"
