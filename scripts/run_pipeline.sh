#!/usr/bin/env bash
# Run the PipeGen-generated perception pipeline AND the incident processor together.
#
# This script deliberately does NOT hard-code PipeGen CLI commands: use the exact
# run command documented/printed by YOUR installed PipeGen version.
#
# Required environment:
#   PIPEGEN_RUN_CMD  the command that launches the generated pipeline. If unset,
#                    the run.sh that PipeGen generates inside pipegen_project/export/
#                    is used (PipeGen "generates a DeepStream app with a run.sh").
#   METADATA_PATH    the JSONL file the pipeline writes per-frame detections to
# Optional:
#   METADATA_FORMAT  generic | deepstream_minimal   (default: settings.yaml)
#   SENTINEL_MQTT=1  also publish alerts to MQTT
#   INCIDENTS_PATH / STATS_PATH  override incidents.output_path / stats_path
#   EVIDENCE_DIR     where logs go (default reports/evidence/pipeline_runs)
#   IDLE_EXIT        seconds without new metadata before the processor stops (default 10)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "${PIPEGEN_RUN_CMD:-}" ]]; then
  # `|| true`: with pipefail, find on a missing export/ dir would otherwise abort
  # the script silently (set -e) before the explanatory error below.
  RUN_SH="$(find "$ROOT/pipegen_project/export" -name run.sh 2>/dev/null | head -1 || true)"
  if [[ -n "$RUN_SH" ]]; then PIPEGEN_RUN_CMD="cd '$(dirname "$RUN_SH")' && ./run.sh"; fi
fi
: "${PIPEGEN_RUN_CMD:?no run.sh under pipegen_project/export/ - export the PipeGen project there or set PIPEGEN_RUN_CMD}"
: "${METADATA_PATH:?set METADATA_PATH to the detection-metadata file the pipeline writes}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
EVID="${EVIDENCE_DIR:-$ROOT/reports/evidence/pipeline_runs}"; mkdir -p "$EVID"
LOG="$EVID/pipeline_run_$TS.log"

PROC_ARGS=(--input "$METADATA_PATH" --follow --idle-exit "${IDLE_EXIT:-10}")
[[ -n "${METADATA_FORMAT:-}" ]] && PROC_ARGS+=(--format "$METADATA_FORMAT")
[[ "${SENTINEL_MQTT:-0}" == "1" ]] && PROC_ARGS+=(--mqtt)
[[ -n "${INCIDENTS_PATH:-}" ]] && PROC_ARGS+=(--output "$INCIDENTS_PATH")
[[ -n "${STATS_PATH:-}" ]] && PROC_ARGS+=(--stats "$STATS_PATH")
# Project venv if present; never inherit a ROS PYTHONPATH into the processor.
PY=python3; [[ -x "$ROOT/.venv/bin/python" ]] && PY="$ROOT/.venv/bin/python"

echo "[sentinel] starting incident processor on $METADATA_PATH"
# Process substitution (not a pipe) so that $! is the processor itself, not tee:
# the EXIT trap must be able to stop it.
env -u PYTHONPATH "$PY" "$ROOT/src/incident_processor.py" "${PROC_ARGS[@]}" > >(tee "$EVID/incident_processor_$TS.log") 2>&1 &
PROC_PID=$!
trap 'kill "$PROC_PID" 2>/dev/null || true' EXIT

echo "[sentinel] launching pipeline: $PIPEGEN_RUN_CMD"
echo "# command: $PIPEGEN_RUN_CMD" > "$LOG"; echo "# started: $(date -u +%FT%TZ) host: $(hostname)" >> "$LOG"
set +e
bash -c "$PIPEGEN_RUN_CMD" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}
set -e
echo "# finished: $(date -u +%FT%TZ) exit: $RC" >> "$LOG"
echo "[sentinel] pipeline exited with $RC; waiting for processor to drain ..."
wait "$PROC_PID" || true
echo "[sentinel] pipeline log: $LOG"
echo "[sentinel] processor log: $EVID/incident_processor_$TS.log"
echo "[sentinel] incidents:    ${INCIDENTS_PATH:-$ROOT/data/incidents.jsonl}"
echo "[sentinel] stats:        ${STATS_PATH:-$ROOT/data/stats.json}"
exit "$RC"
