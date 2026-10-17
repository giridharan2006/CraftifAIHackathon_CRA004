#!/usr/bin/env bash
# MQTT end-to-end check with SYNTHETIC input: starts a private Mosquitto broker on
# 127.0.0.1:$MQTT_TEST_PORT, subscribes with mosquitto_sub, runs the incident
# processor with --mqtt on the synthetic metadata, and checks that the received
# payload equals the JSONL record. Never touches data/incidents.jsonl or a broker
# on 1883.
#
# Mosquitto: uses mosquitto/mosquitto_sub from PATH (sudo apt install mosquitto
# mosquitto-clients), or an unpacked package tree via MOSQUITTO_PREFIX=<dir>
# containing usr/sbin/mosquitto (see docs/testing.md).
# Exit: 0 pass, 1 fail, 77 skipped (Mosquitto not available).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
PY=python3; [[ -x .venv/bin/python ]] && PY=.venv/bin/python
unset PYTHONPATH
PORT="${MQTT_TEST_PORT:-18830}"
TOPIC=workplace_safety/alerts

if [[ -n "${MOSQUITTO_PREFIX:-}" ]]; then
  BROKER="$MOSQUITTO_PREFIX/usr/sbin/mosquitto"; SUB="$MOSQUITTO_PREFIX/usr/bin/mosquitto_sub"
  export LD_LIBRARY_PATH="$MOSQUITTO_PREFIX/usr/lib/x86_64-linux-gnu:$MOSQUITTO_PREFIX/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
else
  BROKER="$(command -v mosquitto || true)"; SUB="$(command -v mosquitto_sub || true)"
fi
if [[ ! -x "$BROKER" || ! -x "$SUB" ]]; then
  echo "SKIP: mosquitto / mosquitto_sub not found (install mosquitto mosquitto-clients or set MOSQUITTO_PREFIX)"
  exit 77
fi

TMP="$(mktemp -d)"; BROKER_PID=""
cleanup() { [[ -n "$BROKER_PID" ]] && kill "$BROKER_PID" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT
OUT=data/synthetic/mqtt_smoke; EVID=reports/evidence/synthetic_demo
mkdir -p "$OUT" "$EVID"; rm -f "$OUT/incidents_synthetic.jsonl"

printf 'listener %s 127.0.0.1\nallow_anonymous true\n' "$PORT" > "$TMP/mosquitto.conf"
"$PY" - "$TMP/settings.yaml" "$PORT" <<'EOF'
import sys, yaml
cfg = yaml.safe_load(open("config/settings.yaml"))
cfg["mqtt"]["port"] = int(sys.argv[2]); cfg["mqtt"]["host"] = "127.0.0.1"
yaml.safe_dump(cfg, open(sys.argv[1], "w"))
EOF

echo "broker: $("$BROKER" -h | head -1) on 127.0.0.1:$PORT"
"$BROKER" -c "$TMP/mosquitto.conf" > "$TMP/broker.log" 2>&1 & BROKER_PID=$!
sleep 1
kill -0 "$BROKER_PID" 2>/dev/null || { echo "FAIL: broker did not start"; cat "$TMP/broker.log"; exit 1; }
"$SUB" -h 127.0.0.1 -p "$PORT" -t "$TOPIC" -v -C 1 -W 20 > "$EVID/mqtt_subscriber_received.txt" 2>&1 & SUB_PID=$!
sleep 1

"$PY" scripts/make_synthetic_metadata.py data/synthetic/metadata_synthetic.jsonl >/dev/null
"$PY" src/incident_processor.py --config "$TMP/settings.yaml" --mqtt \
  --input data/synthetic/metadata_synthetic.jsonl \
  --output "$OUT/incidents_synthetic.jsonl" --stats "$OUT/stats_synthetic.json"
wait "$SUB_PID" && SUB_RC=0 || SUB_RC=$?
echo "--- broker log"; cat "$TMP/broker.log"
echo "--- received by mosquitto_sub ($EVID/mqtt_subscriber_received.txt)"; cat "$EVID/mqtt_subscriber_received.txt"
[[ $SUB_RC -eq 0 ]] || { echo "FAIL: subscriber exit $SUB_RC (no message within 20 s)"; exit 1; }

"$PY" - "$EVID/mqtt_subscriber_received.txt" "$OUT/incidents_synthetic.jsonl" <<'EOF'
import json, sys
topic, payload = open(sys.argv[1]).read().split(" ", 1)
received, logged = json.loads(payload), json.loads(open(sys.argv[2]).readline())
ok = topic == "workplace_safety/alerts" and received == logged
print(f"{'PASS' if ok else 'FAIL'}: MQTT payload {'equals' if ok else 'differs from'} the JSONL record "
      f"({received.get('event_id')}, track {received.get('track_id')}, frame {received.get('frame')}) [SYNTHETIC input]")
sys.exit(0 if ok else 1)
EOF
