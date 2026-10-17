# Errors and fixes — 2026-10-16 session

Each entry gives the symptom, root cause, action taken, and result. Raw output is
in `raw/`.

## E1. `nvidia-smi: command not found` (exit 127) — NOT FIXED (needs sudo + reboot)
- **Command:** `nvidia-smi` (`raw/env_02_gpu.log`)
- **Root cause:** No NVIDIA proprietary driver is installed. `lspci -nnk` shows the GPU
  `10de:2d59` bound to `nouveau`; there are no nvidia packages in dpkg and no
  `/dev/nvidia*` (`raw/env_04_nvidia_driver.log`).
- **Action:** Identified the supported package (`nvidia-driver-595-open`, recommended
  by `ubuntu-drivers devices`; Secure Boot is disabled, so no MOK step is needed).
  This was not installed: sudo needs your password, and a reboot is required.
- **Remaining:** You run `sudo apt install nvidia-driver-595-open && sudo reboot`.

## E2. `pipegen: command not found` — NOT FIXED (needs portal sign-in + sudo)
- **Root cause:** PipeGen is not installed (`raw/env_06_pipegen.log`).
- **Action:** Read the official install method from developer.craftifai.com (saved at
  `../evidence/environment/pipegen_official_install_guide_extract.txt`): prerequisites
  script, then `sudo apt install ./PipeGen_0.5.1_amd64.deb`. The download endpoints
  return the sign-in SPA without a browser session, so the files could not be fetched.
  The unrelated PyPI `pipegen` was **not** installed.

## E3. Wayland session — NOT FIXED (needs log-out)
- `XDG_SESSION_TYPE=wayland`; PipeGen requires X11. Fix: log out, choose
  "Ubuntu on Xorg" (gear icon on the login screen).

## E4. Docker / NVIDIA Container Toolkit missing — NOT FIXED (needs sudo)
- PipeGen v0.5.1 runs DeepStream and TensorRT in a container. Docker and `nvidia-ctk`
  are absent (`raw/env_13_docker_sudo.log`). The official prerequisites script
  installs both.

## E5. `check_environment.sh` gave misleading diagnostics — FIXED
- **Symptom:** It printed "no NVIDIA GPU / JetPack 6 Jetson detected" although a GPU
  exists, and FAILed on host `deepstream-app`, which PipeGen 0.5.1 does not need on
  the host (`raw/script_01_check_environment.log`).
- **Fix:** It now distinguishes "GPU present but no NVIDIA driver (driver in use:
  nouveau)", checks Docker, `nvidia-ctk` and the docker group, and reports host
  DeepStream as INFO.
- **Result:** `raw/script_03_check_environment_fixed.log`.

## E6. `run_pipeline.sh` exited silently when `pipegen_project/export/` was missing — FIXED
- **Symptom:** exit 1 with no message (`raw/plumb_01_no_export.log`).
- **Root cause:** Under `set -euo pipefail`, `RUN_SH="$(find <missing dir> ... | head -1)"`
  returns find's status 1, so `set -e` aborted before the explanatory `${PIPEGEN_RUN_CMD:?...}`
  error (`raw/plumb_01b_diagnose.log`).
- **Fix:** Added `|| true` to the substitution, and changed the follow-up `&&` to an `if`.
- **Result:** The message now prints (`raw/plumb_01c_no_export_after_fix.log`).
  Regression test `tests/test_run_pipeline.py::test_missing_export_reports_reason`.
  The old logic still fails silently (`raw/test_02c_regression_check_old_logic.log`).

## E7. `run_pipeline.sh` could not be tested without polluting live outputs — FIXED
- It always wrote to `data/incidents.jsonl` and `reports/evidence/pipeline_runs/`, and
  `validate_project.sh` counts any log there as a completed run.
- **Fix:** Added optional `INCIDENTS_PATH`, `STATS_PATH`, `EVIDENCE_DIR`, and `IDLE_EXIT`
  overrides; defaults are unchanged. The processor uses `.venv/bin/python` with
  `PYTHONPATH` unset.
- **Result:** The stub-pipeline test wrote only to synthetic paths
  (`raw/plumb_02_run_pipeline_stub.log`). `data/` contains only `synthetic/`, and
  `reports/evidence/pipeline_runs/` is empty.

## E8. `validate_project.sh` could over-report — FIXED
- Any `pipeline_run_*.log` counted as "Run COMPLETE", even for a failed run; MQTT
  COMPLETE relied on the cloud-container evidence.
- **Fix:** A run counts only if its log has `# finished: ... exit: 0`. MQTT evidence from
  the laptop is preferred and labelled; a separate "MQTT (live pipeline)" line was
  added. The script uses `.venv` and unsets `PYTHONPATH`.

## E9. A new test had a wrong expectation — FIXED (test, not code)
- `test_stub_pipeline_feeds_processor_in_follow_mode` expected frame 11. Recomputing
  the feet x = (150 + 60i)/1000 ≥ 0.6 gives i ≥ 8, so the third inside frame is **10**,
  which is what the processor produced. The expectation was corrected; the test was
  not weakened.

## E10. A synthetic-demo check was tautological — FIXED
- The "forklift produced no incident" check looked at `object_class`, which is always
  `person`. It now verifies that the forklift's feet *are* inside the zone and that no
  untracked incident was produced.

## E11. The session logging helper's redaction was too broad — FIXED
- It masked `passwordless sudo: no`. The regex now redacts only `key=value` / `key: value`
  for token/password/secret/api_key/cookie/authorization, and that log entry was
  corrected by hand. No secrets appeared in any output.

## E12. `paho` missing from system Python / ROS `PYTHONPATH` — WORKED AROUND
- System Python has no paho-mqtt and a ROS Jazzy `PYTHONPATH`. Everything runs in
  `.venv` with `env -u PYTHONPATH`.

## E13. Mosquitto not installed — WORKED AROUND (no sudo)
- `apt-get download mosquitto mosquitto-clients libmosquitto1 libdlt2 libwebsockets19t64`,
  then `dpkg -x` into the session scratchpad, run with `LD_LIBRARY_PATH`. There was no
  system change. First attempt: `libdlt.so.2` / `libwebsockets.so.19` not found, fixed by
  downloading those two libraries.
