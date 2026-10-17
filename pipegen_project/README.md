# PipeGen runbook (run on the NVIDIA GPU / Jetson machine)

Official requirements come from *Embedded SF: CraftifAI Physical AI Hackathon:
Official Problem Statement*, Track A. This project is the problem statement's
**suggested track #1, "Workplace Safety Sentinel"**: person detection plus zone
checks on a site camera, with alerts published over MQTT and a JSON incident log.

PipeGen was **not available** in the environment where this repository was
prepared (a cloud container with no NVIDIA GPU, no PipeGen, and no access to the
CraftifAI portal). It is also **not yet installed on the target laptop** (checked
2026-10-16; see §0a). Nothing in this folder is PipeGen output yet. Use the commands
and screens from the **PipeGen v0.5.1 Lab** for every step below. This runbook
only says *what* to produce and *where to save it*. Do not use the unrelated
`pipegen` package on PyPI, which is an AWS CodePipeline tool by another author.

## 0. Setup (official checklist)

- Download PipeGen **v0.5.1** from https://developer.craftifai.com/dashboard?tab=downloads
  and sign in with your CraftifAI account.
- Confirm that `pipegen --version` prints `0.5.1`.
- Use an x86-64 Linux PC with an NVIDIA GPU, or a Jetson on **JetPack 6**, in an
  **X11** desktop session (`echo $XDG_SESSION_TYPE` should print `x11`).
- Plug in the kit's USB camera. Keep any videos **under `/home`**.

```bash
cd ~/Downloads/workplace_safety_sentinel
bash scripts/check_environment.sh     # prints PASS/FAIL against the checklist above
```

### 0a. Exact steps for this laptop (state measured on 2026-10-16)

Measured: Ubuntu 24.04.4, x86_64, NVIDIA GPU `10de:2d59` on the **nouveau** driver
(no `nvidia-smi`), **Wayland** session, no Docker, no PipeGen, Secure Boot
**disabled**, and 231 GB free. Evidence is in `reports/session_logs/raw/env_*.log`.
Steps 1, 3 and 4 need your sudo password. Steps 2 and 6 need the browser and GUI.

1. **NVIDIA driver** (the official PipeGen guide does not cover this; this is the
   package `ubuntu-drivers devices` recommends here):
   ```bash
   sudo apt update && sudo apt install -y nvidia-driver-595-open
   sudo reboot
   nvidia-smi        # after reboot: must list the GPU and a driver version
   ```
2. **Download** from https://developer.craftifai.com/dashboard?tab=downloads (sign in):
   *PipeGen → Linux .deb x86_64* (`PipeGen_0.5.1_amd64.deb`) **and** the Ubuntu x86
   prerequisites script (`pipegen_prerequisites_ubuntu_x86.sh`). Save both to `~/Downloads`.
3. **Prerequisites** (official): installs Docker, the NVIDIA Container Toolkit and
   socat, and adds you to the `docker` group:
   ```bash
   cd ~/Downloads && chmod +x ./pipegen_prerequisites_ubuntu_x86.sh && ./pipegen_prerequisites_ubuntu_x86.sh
   ```
4. **Install PipeGen** (official): `sudo apt install ./PipeGen_0.5.1_amd64.deb`
   (if dependencies are missing: `sudo apt-get -f install`).
5. **Log out, then switch to X11.** On the login screen, click your name, then the
   gear icon at the bottom right, choose **"Ubuntu on Xorg"**, and log in. Check with
   `echo $XDG_SESSION_TYPE`, which should print `x11`. The log-out also applies the
   `docker` group.
6. **First launch:** run `pipegen`. It downloads the DeepStream container (~12 GB, ~35 GB
   unpacked). If the download drops, run `pipegen` again to resume. Then sign in or
   create your account in the app.
7. Verify:
   ```bash
   pipegen --version                 # 0.5.1
   docker run --rm --gpus all ubuntu nvidia-smi   # GPU visible inside containers
   bash scripts/check_environment.sh
   ```

Camera on this laptop: the integrated webcam at `/dev/video0` (MJPG 1280x720 at
30 fps; measured 29 fps). `/dev/video1` is a metadata node, not a camera. Use the
kit USB camera if you have it, and record which one you used.

## 1. Requirement
Give PipeGen the sentence/paragraph in `pipegen_project/requirement.md`. Take a
screenshot and save it as `reports/evidence/pipegen/01_requirement.png`.

## 2. Pipeline IR
Review the generated IR. It should contain: source (USB camera or file) →
detector → tracker → OSD/display → **JSON metadata output** and **MQTT output**.
**Screenshot the Pipeline IR node graph** (this is mandatory evidence) and save it
as `reports/evidence/pipegen/02_pipeline_ir_graph.png`. Also save the IR file if
PipeGen exports one.

## 3. Model
Choose a model from the CraftifAI catalog, or use Deep Search, as long as it has a
**person** class. Open its label file and set `detection.person_labels` /
`person_class_ids` in `config/settings.yaml` exactly as the file names the class.
Copy the label file to `reports/evidence/pipegen/03_model_labels.txt`.

## 4. Compiler (TensorRT)
Compile the ONNX model to a TensorRT engine. **FP16** is the safe default.
**INT8** earns the *Edge Optimization* bonus, but only if you report the
speed/power/accuracy trade-off from PipeGen's reports. **Screenshot the TensorRT
speed report** (mandatory evidence) and save it as
`reports/evidence/pipegen/04_speed_report.png`, plus any exported text/JSON.
Engine files (`*.engine`) are git-ignored because of their size.

## 5. Run
Export the PipeGen project into **`pipegen_project/export/`**. It must be part of
the submitted repository. PipeGen generates a DeepStream app with a `run.sh`.

```bash
export METADATA_PATH="<JSON metadata file the generated app writes>"
scripts/run_pipeline.sh       # finds export/**/run.sh; logs -> reports/evidence/pipeline_runs/
```

Screenshot the live display with boxes and track IDs, and save it as
`reports/evidence/pipegen/05_live_run.png`. Say whether the input was the USB
camera or a video file.

### Connecting PipeGen's outputs to the incident processor
PipeGen natively outputs **JSON metadata files** and **MQTT**. Before the demo,
look at 3 real lines:

```bash
head -3 "$METADATA_PATH"        # or: mosquitto_sub -h <broker> -t '<pipegen topic>' -C 3
python3 scripts/inspect_metadata.py "$METADATA_PATH"   # adapter, labels, track IDs, frame-size check
```

Save that output as `reports/evidence/pipegen/06_metadata_inspection.txt`. If no
adapter extracts detections, the real field names must be mapped in
`src/metadata_adapters.py`. Add a unit test with 2-3 real lines when you do.

| What the lines look like | What to do |
| --- | --- |
| One JSON per frame with objects (label, confidence, bbox, track id) | Use `--format generic`, and adjust key names in `src/metadata_adapters.py::parse_generic` if needed |
| DeepStream nvmsgconv minimal (`"objects": ["id\|l\|t\|r\|b\|label"]`) | Use `--format deepstream_minimal` |
| PipeGen MQTT topic | Run `mosquitto_sub -h <broker> -t '<topic>' \| python3 src/incident_processor.py --input - --format <fmt>` |

The incident processor republishes **only confirmed intrusions** to
`workplace_safety/alerts` and to `data/incidents.jsonl`.

### Restricted zone on screen (optional)
If the generated app has, or lets you add, `nvdsanalytics`, run
`python3 src/zone_to_nvdsanalytics.py --width <W> --height <H>`. The output goes
to `config/config_nvdsanalytics.txt`.

### Closed Loop bonus (optional, needs Track B)
An ESP32 built with FirmGen can subscribe to `workplace_safety/alerts` and drive a
buzzer or light. To qualify, the MQTT bridge has to be written into the FirmGen PRD
as a requirement.

Finally, run `scripts/validate_project.sh`.
