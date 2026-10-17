# Testing methodology

Every claim in this project is tagged with the level at which it was verified:

| Level | Meaning | How |
| --- | --- | --- |
| Unit-tested | Behaviour checked by `pytest` with constructed inputs | `tests/` |
| Synthetic input | End-to-end run on hand-written detection metadata (not model output) | `scripts/run_synthetic_demo.sh`, `scripts/mqtt_smoke_test.sh` |
| Real PipeGen pipeline | Metadata produced by the PipeGen-generated DeepStream app | **not done yet** |
| Live camera | That pipeline running on a USB camera | **not done yet** |

Passing tests and synthetic runs say nothing about PipeGen, TensorRT, the GPU, or live
video. Those have not been executed (see `submission_checklist.md`).

## Automated tests (`pytest`)
```bash
.venv/bin/python -m pytest -q     # 96 tests, ~4 s, no GPU, network or broker needed
```
| File | Tests | Covers |
| --- | --- | --- |
| `test_zone_manager.py` | 11 | point-in-zone, boundary inside, invalid zones, bottom-centre vs centre anchor, pixel conversion |
| `test_incident_processor.py` | 20 | one incident per entry, confirm frames, outside/non-person/low-confidence ignored, class-ID match, cooldown dedup, flicker, re-entry, two tracks, missing optional fields, ID continuity, both adapters, malformed lines, CLI |
| `test_validation.py` | 34 | invalid frame size → malformed record; NaN/inverted/zero-size/out-of-frame boxes dropped; clamping; invalid settings (MQTT port/topic/host, types, booleans); CLI paths relative to cwd; unwritable output; follow-mode edge cases |
| `test_event_logger.py` | 5 | JSONL validity, append across runs, directory creation, statistics |
| `test_mqtt_publisher.py` | 2 | unreachable broker disables MQTT; incidents still logged |
| `test_run_pipeline.py` | 2 | `run_pipeline.sh` with a **stub** pipeline (follow mode, exit status logged); clear error without an export folder |
| `test_inspect_metadata.py` | 3 | format detection, frame-size warning, unknown schema |
| `test_zone_to_nvdsanalytics.py` | 3 | ROI rendering at 1280x720 and 1920x1080, bad size |
| `test_package_submission.py` | 16 | archive exclusion rules (venv, caches, secrets, engines, synthetic outputs) |

Regression evidence: 37 of the 55 tests added in the optimisation pass (`test_validation.py`,
`test_zone_to_nvdsanalytics.py`) were also run against the
original source: 26 of them fail there, and each failure corresponds to a defect fixed in this pass
(`reports/session_logs/raw/opt_04b_new_tests_vs_original_src.log`).

## Synthetic end-to-end replay
`scripts/make_synthetic_metadata.py` writes 80 deterministic frames (1920x1080, 10 fps):
track 1 walks into the zone, track 2 stays outside, and an untracked forklift stands
inside it. `scripts/run_synthetic_demo.sh` runs the real processor on them. Then
`scripts/verify_synthetic_demo.py` recomputes the expected result **without** the
processor (geometry from `settings.yaml`) and checks 16 properties: exactly one
incident, on the right frame and track; none for track 2 or the forklift; valid JSONL;
consistent statistics; and the live log untouched.

## MQTT
`scripts/mqtt_smoke_test.sh` starts a private broker on `127.0.0.1:18830` (it never
touches a broker on 1883). It subscribes with `mosquitto_sub`, runs the processor
with `--mqtt` on the synthetic stream, and checks that the received payload equals the
JSONL record. Exit codes: 0 pass, 1 fail, 77 skipped (Mosquitto not found).

### MQTT without sudo
Ubuntu's own packages can be unpacked in user space:
```bash
mkdir -p ~/mosquitto-local && cd ~/mosquitto-local
apt-get download mosquitto mosquitto-clients libmosquitto1 libdlt2 libwebsockets19t64
for d in *.deb; do dpkg -x "$d" root; done
cd ~/Downloads/workplace_safety_sentinel
MOSQUITTO_PREFIX=~/mosquitto-local/root bash scripts/mqtt_smoke_test.sh
```
(With sudo: `sudo apt install mosquitto mosquitto-clients`, then run the script plainly.)

## Static analysis
No linters are project dependencies. They were run from a throwaway virtual environment:
```bash
python3 -m venv /tmp/lint && /tmp/lint/bin/pip install pyflakes shellcheck-py
/tmp/lint/bin/pyflakes src scripts tests
/tmp/lint/bin/shellcheck -S warning scripts/*.sh
```

## Evidence-based status
`scripts/validate_project.sh` re-runs the tests and reports each PipeGen stage as
COMPLETE **only** if its artifact exists: an IR graph or speed report in
`reports/evidence/pipegen/`, an `*.engine`, an export `run.sh`, or a pipeline log
that recorded `exit: 0`.

## Not covered
- Real PipeGen metadata (schema unknown until the pipeline runs: use `inspect_metadata.py`).
- TensorRT engine build, the speed report, and GPU throughput.
- Camera input through the pipeline, and detection accuracy.
- MQTT authentication/TLS (not implemented).
