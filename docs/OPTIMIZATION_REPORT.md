# Optimisation report

Pass carried out on 2026-10-16, 22:06–22:25 IST, on the target laptop. It was performed by
an automated coding-assistant session at the project owner's direction. Every command
and its full output is in `reports/session_logs/raw/opt_*.log`. Before any change, a
full backup was taken:
`~/Downloads/workplace_safety_sentinel_backup_20261016_220640.tar.gz`
(162 entries, `.venv` excluded, SHA-256 `f50194da…d63a`).

## 1. Summary
- **Defects fixed:** the 26 new tests that fail against the original code, plus two script bugs.
  - `run_pipeline.sh` left an orphaned processor on SIGTERM.
  - The status report could over-report progress.
- **Input validation:** malformed metadata and invalid settings are now rejected
  explicitly instead of silently changing behaviour.
- **Error handling:** clean exit codes and messages replace tracebacks on I/O errors,
  and the input file is now closed.
- **Duplication removed:** the format list, project root and default config path each
  now have one definition.
- **Tests:** 41 → **96**, all passing. `pyflakes` is clean and `shellcheck` has 0 warnings.
- **Reproducibility:** the MQTT test is now a project script (it previously lived in a
  temporary folder). There is also a submission packager, and the archive was verified
  in a fresh virtual environment.
- **Folder clean-up:**
  - removed caches, stale ad-hoc outputs, obsolete cloud-container artifacts and duplicate evidence;
  - replaced a 106 KB JavaScript dump with a 3 KB readable install-guide extract;
  - rewrote `.gitignore`.
- **Documentation:** the README was rewritten around 16 reviewer-facing sections; new
  `docs/testing.md`; corrected one inaccurate claim (below).
- **Unchanged:** the PipeGen / TensorRT / GPU status. It is still **blocked** on this
  laptop, and nothing was fabricated.

## 2. Files added, modified and removed
**Added**
| File | Purpose |
| --- | --- |
| `scripts/mqtt_smoke_test.sh` | reproducible MQTT delivery test on a private loopback broker (skip = exit 77) |
| `scripts/package_submission.py` | builds `dist/workplace_safety_sentinel_submission.zip` with a manifest |
| `tests/test_validation.py` (34) | metadata/config validation, CLI paths, I/O errors, follow mode |
| `tests/test_mqtt_publisher.py` (2) | unreachable broker → MQTT disabled, JSONL continues |
| `tests/test_zone_to_nvdsanalytics.py` (3) | ROI export (previously untested) |
| `tests/test_package_submission.py` (16) | archive exclusion rules |
| `docs/testing.md` | testing methodology and coverage |
| `docs/OPTIMIZATION_REPORT.md` | this report |
| `reports/evidence/synthetic_demo/{demo_output,verification_output,mqtt_smoke_test_output}.txt`, `mqtt_subscriber_received.txt` | final-run evidence |
| `reports/evidence/environment/environment_report_…_20261016T164744Z.txt` | final environment check |
| `reports/evidence/{pipegen,pipeline_runs}/.gitkeep` | keep the evidence folders in the archive |

**Modified**
- **Source**
  - `src/metadata_adapters.py`: finite/positive-size checks; invalid frame size → malformed
    record; the parser table defines `FORMATS`.
  - `src/config_loader.py`: `PROJECT_ROOT`, `DEFAULT_CONFIG_PATH` and
    `resolve_project_path`; MQTT/label/boolean validation; read errors become `ConfigError`.
  - `src/incident_processor.py`: CLI paths relative to the cwd; file closed; I/O errors →
    exit 1; `--idle-exit` validated; shared constants.
  - `src/zone_to_nvdsanalytics.py`: shared constants; `main(argv)`; size and write
    validation.
- **Scripts**
  - `scripts/run_pipeline.sh`: processor PID captured correctly (process substitution), so
    the EXIT trap stops it; quoting.
  - `scripts/run_synthetic_demo.sh`: venv Python, `PYTHONPATH` unset, quoting.
  - `scripts/make_synthetic_metadata.py`: structure only (`main()`, imports); the output is
    byte-identical (SHA-256 `ec61cd07…4801` before and after).
  - `scripts/validate_project.sh`: `cd` guard; MQTT evidence path.
  - `scripts/check_environment.sh`: report written to `reports/evidence/environment/`.
- **Docs**
  - Rewritten: `README.md`, `docs/architecture.md` (metadata contract, execution flow,
    corrected verification table).
  - Updated: `docs/demo_script.md`, `docs/project_description.md`,
    `docs/submission_checklist.md`, `reports/session_logs/final_status.md`.
  - Neutral wording: `reports/session_logs/environment_report.md`, `errors_and_fixes.md`.
- **Other:** `.gitignore`; the install-guide extract (cleaned).

**Removed** (all still in the backup tarball)
| Removed | Reason |
| --- | --- |
| `__pycache__/`, `.pytest_cache/` | regenerable caches |
| `data/synthetic/{mqtt_broker,mqtt_nobroker,plumbing}/` | ad-hoc outputs from the first session, superseded by `mqtt_smoke_test.sh` and `tests/test_run_pipeline.py` |
| `reports/environment_report_CLOUD_CONTAINER_no_gpu.txt`, `reports/evidence/synthetic_component_test/` | evidence from a different (cloud) machine, superseded by laptop evidence |
| two older `environment_report_…` files | superseded by the final check (history kept in `raw/script_01_*`, `raw/script_03_*`) |
| `reports/evidence/synthetic_demo/synth_0*.log`, `final_0*.log`, `…_laptop.txt`, `unit_tests/pytest_full_after_changes.log` | copies of raw logs; replaced by final-run evidence |
| the tool-branded session-log file name | renamed to `reports/session_logs/execution_log_20261016_214700.md` |

## 3. Code-quality improvements (each covered by a test)
| Problem in the original code | Effect | Fix |
| --- | --- | --- |
| Invalid frame `width`/`height` in a record | every detection in the frame silently dropped; frame counted as processed | record counted as malformed (`MetadataError`) |
| `NaN`/`Infinity` coordinates (accepted by `json.loads`) | NaN anchor; detection silently never in the zone | object dropped |
| Zero-size, inverted, or fully off-frame boxes | degenerate detections reached the zone test | object dropped; partly off-frame boxes still clamped |
| `--output`/`--stats` resolved against the project root | surprising location when run from another directory | CLI paths are relative to the cwd; settings paths to the project root |
| Unwritable output location | traceback | `cannot create incident log …`, exit 1 |
| Input file opened and never closed | resource leak | context manager |
| MQTT `port`, `host`, `topic`, `enabled` unchecked; `true` accepted as `confirm_frames`/`qos`; non-string labels | failures only at connect time, or silent misconfiguration | validated at start-up (`ConfigError`, exit 2) |
| `run_pipeline.sh` stored the PID of `tee`, not the processor | processor left running after Ctrl+C/SIGTERM (`raw/opt_09_*`) | process substitution |
| Format list in 3 places; `PROJECT_ROOT` in 2 | drift risk | single definitions |

Regression proof: 37 of the new tests were run against the original source; **26 fail
there** and 11 pass on both (`raw/opt_04b_new_tests_vs_original_src.log`).

Corrected documentation claim: `docs/architecture.md` previously listed the MQTT failure
path as *unit-tested* when no unit test existed. A unit test was added
(`tests/test_mqtt_publisher.py`), so the claim is now true.

## 4. Dependencies
`requirements.txt` is **unchanged** (PyYAML, paho-mqtt, pytest; verified versions 6.0.3,
2.1.0, 9.1.1). No dependency was found unused: paho-mqtt is optional at runtime but
imported by the MQTT path and tests. The linters (`pyflakes` 4.0.3, ShellCheck 0.11.0 via `shellcheck-py`)
ran from a throwaway virtual environment and are not project dependencies.

## 5. Tests executed (exact results)
| Run | Result | Log |
| --- | --- | --- |
| Baseline pytest (before changes) | 41 passed | `raw/opt_01_baseline_pytest.log` |
| Baseline lint | pyflakes 0; shellcheck 1 warning (SC2164) | `raw/opt_03_baseline_lint.log` |
| New tests vs original source | 26 failed, 11 passed (expected) | `raw/opt_04b_*.log` |
| Final pytest | **96 passed** in 3.63 s | `raw/opt_10_final_pytest.log` |
| Final lint | pyflakes 0; shellcheck 0 warnings; compileall OK; `bash -n` OK | `raw/opt_16_final_lint.log` |
| Reference scan of all Markdown | stale references fixed; the rest are outputs that do not exist yet (PipeGen screenshots, `data/incidents.jsonl`, `pipegen_project/export/`) | `raw/opt_17_reference_scan.log` |
| Archive in a fresh venv | installs; 96 passed; demo 1 incident; 16/16; MQTT skip 77; validate OK | `raw/opt_19_verify_archive.log` |

## 6. Synthetic demo (synthetic input, not model output)
`run_synthetic_demo.sh`: 80 frames, 160 person detections, **1 incident**
(`incident_0001`, track 1, frame 51), 2 unique tracks, 0 malformed.
`verify_synthetic_demo.py`: **16/16** checks. `mqtt_smoke_test.sh`: **PASS**; the payload
received by `mosquitto_sub` from Mosquitto 2.0.18 equals the JSONL record. Metadata
SHA-256 is unchanged from before the pass. Evidence: `reports/evidence/synthetic_demo/`.

## 7. Actual PipeGen status
**Not installed** (re-checked at 22:17 IST, `raw/opt_14_final_check_environment.log`).
No Pipeline IR, model selection, TensorRT engine, speed report, export folder, or live
run exists. `pipegen_project/` contains only the Stage 1 requirement draft and the
runbook. The unrelated PyPI package `pipegen` was not installed or referenced as the
framework.

## 8. Actual TensorRT / GPU status
The NVIDIA GPU (`10de:2d59`) is present but bound to **nouveau**: there is no NVIDIA
driver, no `nvidia-smi`, and no CUDA. TensorRT and DeepStream are expected to come from
PipeGen's container, which cannot be pulled yet (no Docker, no NVIDIA Container
Toolkit). The session is **Wayland**. No GPU, FPS, latency or accuracy figure exists, and
none is claimed.

## 9. Known blockers
In order: (1) NVIDIA driver (sudo + reboot); (2) PipeGen download (portal sign-in);
(3) prerequisites script (sudo); (4) `.deb` install (sudo); (5) X11 session (log out);
(6) first-launch 12 GB container pull and sign-in. Not verified: whether the container
supports this GPU generation.

## 10. Remaining work for full compliance
1. Clear the blockers (`pipegen_project/README.md` §0a).
2. In PipeGen: Requirement → IR (screenshot `02_pipeline_ir_graph.png`) → Model (copy the
   labels to `03_model_labels.txt`; set `person_labels`/`person_class_ids`) → Compiler FP16
   (screenshot `04_speed_report.png`) → Run; export to `pipegen_project/export/`.
3. Run `scripts/inspect_metadata.py` on the real metadata, set `METADATA_FORMAT`, then run
   `SENTINEL_MQTT=1 bash scripts/run_pipeline.sh` and capture a live incident.
4. Fill the `TBD`s in `docs/project_description.md`, rebuild the archive, and submit.
5. Optional: give the project its own git repository (it currently sits untracked inside
   the home-directory repository). This was not done because it needs your approval.

## 11. Reproduce
```bash
cd ~/Downloads/workplace_safety_sentinel
unset PYTHONPATH && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                                            # 96 passed
bash scripts/run_synthetic_demo.sh && .venv/bin/python scripts/verify_synthetic_demo.py   # 16/16
bash scripts/mqtt_smoke_test.sh            # PASS with Mosquitto; 77 = skipped (see docs/testing.md)
bash scripts/check_environment.sh          # PipeGen readiness (currently 3 PASS / 6 FAIL)
bash scripts/validate_project.sh           # PipeGen stages: NOT VERIFIED
.venv/bin/python scripts/package_submission.py
```

## 12. Submission archive
`dist/workplace_safety_sentinel_submission.zip`, inside the project folder. It is rebuilt
in place by `scripts/package_submission.py`, and `SUBMISSION_MANIFEST.txt` inside lists
every file with its SHA-256. It excludes `.venv/`, `.git/`, caches, `dist/`,
`data/synthetic/` (regenerable), secrets, and TensorRT engines, ONNX models and videos
(`--include-models` keeps them). The original project folder is not modified by
packaging.

## Note on AI-tool references
- **Removed:** a tool-branded title and filename in the session log, and a tool-branded
  "collected by" line.
- **Reworded:** first-person assistant phrasing in the session reports is now neutral.
- **Kept, deliberately:**
  - the raw command logs and evidence transcripts, verbatim; some contain the
    assistant's temporary-directory path;
  - one neutral provenance statement (this report and `environment_report.md`).

Editing verbatim logs would misrepresent the record. No copyright, licence or
attribution notices existed or were removed.
