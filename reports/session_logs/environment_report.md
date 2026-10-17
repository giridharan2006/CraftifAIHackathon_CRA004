# Environment report — target laptop

Collected 2026-10-16 21:47–21:57 IST by an automated assistant session, with the
actual commands run on this laptop. Full raw output is in `raw/env_*.log`; the
`check_environment.sh` reports are in `../evidence/environment/`.

| Item | Result | Raw log |
| --- | --- | --- |
| Project path | `/home/giridharan-s/Downloads/workplace_safety_sentinel`, not `~/Projects/...` as the request assumed | `raw/env_01_os.log` |
| Host | `giridharan-s-LOQ-15IRX10` (Lenovo LOQ 15IRX10) | `raw/env_01_os.log` |
| OS / kernel | Ubuntu 24.04.4 LTS (noble), Linux 7.0.0-34-generic | `raw/env_01_os.log` |
| CPU / arch | Intel Core i7-14700HX, 28 threads, **x86_64** | `raw/env_01_os.log` |
| RAM / swap | 15 GiB (≈5.4 GiB available at check time) / 4 GiB | `raw/env_09_disk_mem.log` |
| Disk | 231 GB free on `/` (PipeGen container needs ≈35 GB) | `raw/env_09_disk_mem.log` |
| NVIDIA GPU | **Present**: PCI `01:00.0`, `10de:2d59`, Lenovo subsystem `17aa:3e3b` | `raw/env_02_gpu.log` |
| NVIDIA driver | **Not installed.** Kernel driver in use is `nouveau`; `nvidia-smi` is missing, there is no `/dev/nvidia*` and no `/proc/driver/nvidia`; no nvidia packages in dpkg; nouveau logged `gsp: init failed, -110` on resume | `raw/env_04_nvidia_driver.log` |
| Recommended driver | `nvidia-driver-595-open` (`ubuntu-drivers devices`), candidate 595.99.02-0ubuntu0.24.04.1 | `raw/env_04_nvidia_driver.log`, `raw/env_13_docker_sudo.log` |
| Secure Boot | Disabled, so no MOK enrolment is needed for the driver | `raw/env_04_nvidia_driver.log` |
| Integrated GPU | Intel Raptor Lake-S UHD (i915/xe) drives the display | `raw/env_02_gpu.log` |
| CUDA | Not installed (no `nvcc`, no `/usr/local/cuda*`) | `raw/env_05_cuda_trt_ds.log` |
| TensorRT | Not on the host (no `trtexec`, no Python `tensorrt`). PipeGen provides it in its container | `raw/env_05_cuda_trt_ds.log` |
| DeepStream | Not on the host (no `deepstream-app`, `/opt/nvidia`, or `nvinfer` GStreamer element). PipeGen provides it in its container | `raw/env_05_cuda_trt_ds.log` |
| GStreamer | 1.24.2 | `raw/env_05_cuda_trt_ds.log` |
| Docker / NVIDIA Container Toolkit | Not installed; `socat` is present | `raw/env_13_docker_sudo.log` |
| Display session | **Wayland** (`XDG_SESSION_TYPE=wayland`, `DISPLAY=:0`); PipeGen requires X11 | `raw/env_03_display.log` |
| PipeGen | **Not installed** (no binary, package, or config dirs) | `raw/env_06_pipegen.log` |
| CraftifAI auth | Not verifiable: there is no PipeGen app to sign in with | — |
| CraftifAI portal | Reachable (HTTP 200). PipeGen v0.5.1 `.deb` and prereqs script listed; downloads require sign-in | `raw/env_12_network.log`, `../evidence/environment/pipegen_official_install_guide_extract.txt` |
| sudo | Requires a password, so no system changes could be made from this session | `raw/env_13_docker_sudo.log` |
| Python | System 3.12.3, pip 24.0, venv OK. `PYTHONPATH=/opt/ros/jazzy/...` is exported by the shell | `raw/env_07_python.log` |
| Project venv | `.venv` created; PyYAML 6.0.3, paho-mqtt 2.1.0, pytest 9.1.1 | `raw/venv_0*.log` |
| Camera | `/dev/video0` = Integrated Camera (MJPG up to 1280x720 at 30 fps); measured 27–29 fps streaming. `/dev/video1` = metadata node. Access via ACL for this user | `raw/env_08_camera.log`, `raw/env_14_webcam_stream.log` |
| MQTT broker | Mosquitto not installed system-wide. Tested with Ubuntu's 2.0.18 packages unpacked in user space (scratchpad, not the project) | `raw/env_10_mqtt.log`, `raw/synth_04_mqtt_local_broker.log` |
| Git | Repo root is `/home/giridharan-s` (branch `master`, no commits); this project is **untracked** inside it, not its own repo. No git operations were performed | `raw/env_11_git.log` |
| Existing artifacts | Synthetic outputs and cloud-container evidence only; no engine, IR, export, or live incidents | `raw/script_02_validate_project_initial.log` |

## Verdict against the official Track A setup checklist
- PASS: x86_64; camera device present; project under `/home`.
- FAIL: NVIDIA driver (GPU present, nouveau); PipeGen 0.5.1; X11; Docker; NVIDIA
  Container Toolkit; docker group.
