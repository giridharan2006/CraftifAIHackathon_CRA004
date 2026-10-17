# Submission checklist

Source of the requirements: *Embedded SF: CraftifAI Physical AI Hackathon:
Official Problem Statement*, Track A.

- **Deadline:** 4:00 pm
- **Submission form (PipeGen):** https://forms.gle/eJyeCKCG2UH757QZ8

Status values: **Complete**, **Incomplete**, **Blocked**, **Not verified**.
Last updated **on the target laptop** (Lenovo LOQ 15IRX10, Ubuntu 24.04.4) on
2026-10-16 (optimisation pass, ~22:20 IST); the system state was re-checked and is unchanged. Raw command output: `reports/session_logs/raw/`. Re-run
`bash scripts/validate_project.sh` after each step and update this file.

## Setup checklist (official)

| Item | Status | Evidence / note |
| --- | --- | --- |
| PipeGen v0.5.1 installed, `pipegen --version` prints `0.5.1` | **Blocked** | Not installed (`raw/env_06_pipegen.log`). The download needs a portal sign-in; install needs sudo |
| Signed in with a CraftifAI account | Not verified | Must be done by you in the PipeGen app |
| x86-64 + NVIDIA GPU, or Jetson on JetPack 6 | **Incomplete** | x86_64 ✔. NVIDIA GPU `10de:2d59` present, but on **nouveau**: no NVIDIA driver, no `nvidia-smi` (`raw/env_02_gpu.log`, `raw/env_04_nvidia_driver.log`) |
| Docker + NVIDIA Container Toolkit (PipeGen prerequisites script) | **Blocked** | Neither installed (`raw/env_13_docker_sudo.log`); needs sudo |
| X11 desktop session | **Incomplete** | `XDG_SESSION_TYPE=wayland` (`raw/env_03_display.log`). Switch to "Ubuntu on Xorg" |
| USB camera from the kit | Incomplete | Kit camera not attached. Integrated webcam `/dev/video0` streams 1280x720 at 29 fps (`raw/env_14_webcam_stream.log`) |
| Videos under `/home` | Complete | Project at `/home/giridharan-s/Downloads/workplace_safety_sentinel` |

## Mandatory requirements (Track A)

| # | Requirement | Status | Evidence / note |
| --- | --- | --- | --- |
| 1 | Full PipeGen flow: Requirement | Incomplete | Draft refined at `pipegen_project/requirement.md`; not yet given to PipeGen |
| 1 | Full PipeGen flow: Pipeline IR | **Blocked** | Needs PipeGen. Screenshot to `reports/evidence/pipegen/02_pipeline_ir_graph.png` |
| 1 | Full PipeGen flow: Model | **Blocked** | Needs PipeGen |
| 1 | Full PipeGen flow: Compiler | **Blocked** | Needs PipeGen, the NVIDIA driver, and the container runtime |
| 1 | Full PipeGen flow: Run | **Blocked** | Needs the generated `run.sh` in `pipegen_project/export/` |
| 2 | TensorRT engine and PipeGen speed report | Not verified | No engine or report exists. Screenshot to `reports/evidence/pipegen/04_speed_report.png` |
| 3 | Live run (video file, USB, CSI or RTSP) on a GPU or Jetson | Not verified | Webcam works at V4L2 level only; no pipeline has run |
| 4 | Actionable output (JSON or MQTT feed, alerts) | Complete (component, synthetic input) / Not verified (live) | Laptop: `reports/evidence/synthetic_demo/` (JSONL, stats, 16/16 checks, MQTT received by `mosquitto_sub`) |
| — | Deep integration: PipeGen is load-bearing | Not verified | By design, all perception comes from PipeGen; this needs the real run |

## What to submit

| Item | Status | Path |
| --- | --- | --- |
| Working prototype: live demo at the venue | Not verified | `docs/demo_script.md` |
| Repository link, **including the PipeGen export folder** | Incomplete | `pipegen_project/export/` does not exist yet. The project is not its own git repo (it sits untracked inside the home-directory repo). A clean ZIP is built by `scripts/package_submission.py` |
| Project description (inputs, tasks, models, precision, outputs, bonus) | Incomplete | `docs/project_description.md` (fill in the `TBD`s) |
| Evidence: IR node graph screenshot | Not verified | `reports/evidence/pipegen/02_pipeline_ir_graph.png` |
| Evidence: TensorRT speed report screenshot | Not verified | `reports/evidence/pipegen/04_speed_report.png` |
| Pitch deck or video (optional) | — | — |

## Supporting deliverables verified on the laptop
- Unit tests: 96 passing (`reports/evidence/unit_tests/pytest_final.log`)
- Synthetic demo: `reports/evidence/synthetic_demo/` (`demo_output.txt`,
  `verification_output.txt` = 16/16 checks)
- MQTT delivery (synthetic input): `reports/evidence/synthetic_demo/mqtt_smoke_test_output.txt`,
  `mqtt_subscriber_received.txt`
- `run_pipeline.sh` with a stub pipeline: `tests/test_run_pipeline.py`; first-session run in
  `reports/evidence/synthetic_demo/run_pipeline_plumbing/`
- Environment: `reports/evidence/environment/`, `reports/session_logs/environment_report.md`
- Submission archive: `python3 scripts/package_submission.py` → `dist/`

## Unmet mandatory requirements right now
All five PipeGen stages, the TensorRT engine and speed report, the live run on a
GPU, the PipeGen export folder, and both evidence screenshots. On this laptop the
blockers, in order, are: the NVIDIA driver, the PipeGen download and sign-in, the
prerequisites script, the `.deb` install, the X11 session, and the first-launch
container download. See `pipegen_project/README.md` §0a.
