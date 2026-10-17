#!/usr/bin/env bash
# Workplace Safety Sentinel - environment diagnostics. Read-only; changes nothing.
# Usage: scripts/check_environment.sh   (report saved under reports/evidence/environment/)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/reports/evidence/environment/environment_report_$(hostname)_$(date -u +%Y%m%dT%H%M%SZ).txt"
mkdir -p "$(dirname "$OUT")"

run() { echo "\$ $*"; timeout 30 bash -c "$*" 2>&1 | head -40; echo "[exit ${PIPESTATUS[0]}]"; echo; }

{
echo "# Environment report - $(date -u +%FT%TZ) - host $(hostname)"
echo "## OS / CPU";            run "uname -a"; run "uname -m"; run "cat /etc/os-release | head -4"
run "cat /etc/nv_tegra_release"          # Jetson only
echo "## Display";             echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<unset>} DISPLAY=${DISPLAY:-<unset>}"; echo
echo "## NVIDIA GPU / driver"; run "nvidia-smi"; run "ls /dev/nvidia* 2>/dev/null"
run "lspci -nnk | grep -iA3 'nvidia' | grep -iE 'nvidia|driver in use'"
run "cat /proc/driver/nvidia/version"
echo "## Container runtime (PipeGen v0.5.1 runs DeepStream in a Docker image; prerequisites script installs these)"
run "docker --version"; run "nvidia-ctk --version"; run "id -nG | tr ' ' '\n' | grep -x docker"
run "docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | head"
echo "## CUDA";                run "nvcc --version"; run "ls -d /usr/local/cuda*"
echo "## TensorRT";            run "which trtexec || ls /usr/src/tensorrt/bin/trtexec"
run "dpkg -l | grep -iE 'tensorrt|nvinfer' | head"
run "python3 -c 'import tensorrt; print(tensorrt.__version__)'"
echo "## DeepStream";          run "deepstream-app --version-all"
run "ls /opt/nvidia/deepstream/"
run "ls /opt/nvidia/deepstream/deepstream/samples/streams/"
run "gst-inspect-1.0 nvinfer | head -5"
run "gst-inspect-1.0 nvtracker | head -5"
echo "## PipeGen";             run "which pipegen"; run "pipegen --version"; run "pipegen --help"
run "pip list 2>/dev/null | grep -iE 'pipegen|craftif'"
echo "## Camera";              run "ls -l /dev/video*"; run "v4l2-ctl --list-devices"
echo "## Python";              run "which python3; python3 --version"
run "python3 -c 'import yaml, paho.mqtt; print(\"yaml ok, paho\", paho.mqtt.__version__)'"
echo "## MQTT broker";         run "which mosquitto mosquitto_sub mosquitto_pub"
echo "## Disk / memory";       run "df -h \"$ROOT\""; run "free -h"
echo "## Official Track A setup checklist (problem statement)"
pass() { echo "  [PASS] $1"; }; fail() { echo "  [FAIL] $1"; }
if command -v nvidia-smi >/dev/null && nvidia-smi >/dev/null 2>&1; then pass "NVIDIA GPU visible (nvidia-smi)"
elif grep -q "R36" /etc/nv_tegra_release 2>/dev/null; then pass "Jetson with JetPack 6 (L4T R36)"
elif lspci 2>/dev/null | grep -qi 'nvidia'; then
  fail "NVIDIA GPU present on PCI but no NVIDIA driver loaded (driver in use: $(lspci -k 2>/dev/null | grep -iA3 'vga.*nvidia' | awk -F': ' '/driver in use/{print $2}' | head -1)); install the proprietary driver"
else fail "no NVIDIA GPU / JetPack 6 Jetson detected"; fi
[[ "$(uname -m)" == "x86_64" || "$(uname -m)" == "aarch64" ]] && pass "arch $(uname -m)" || fail "arch $(uname -m)"
PGV="$(pipegen --version 2>/dev/null || true)"
[[ "$PGV" == *0.5.1* ]] && pass "pipegen --version = $PGV" || fail "pipegen --version should print 0.5.1 (got: ${PGV:-not installed})"
[[ "${XDG_SESSION_TYPE:-}" == "x11" ]] && pass "X11 session" || fail "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<unset>} (PipeGen needs an X11 desktop session)"
ls /dev/video* >/dev/null 2>&1 && pass "camera device(s): $(ls /dev/video* | tr '\n' ' ')" || fail "no /dev/video* (USB camera not connected)"
command -v docker >/dev/null && pass "docker installed ($(docker --version 2>/dev/null))" || fail "docker not found (run PipeGen's pipegen_prerequisites_ubuntu_x86.sh)"
command -v nvidia-ctk >/dev/null && pass "NVIDIA Container Toolkit installed" || fail "nvidia-ctk not found (run PipeGen's pipegen_prerequisites_ubuntu_x86.sh)"
id -nG | tr ' ' '\n' | grep -qx docker && pass "user in docker group" || fail "user not in docker group (log out/in after the prerequisites script)"
command -v deepstream-app >/dev/null && echo "  [INFO] host deepstream-app found" || echo "  [INFO] no host deepstream-app (expected: PipeGen v0.5.1 uses DeepStream inside its container image)"
[[ "$ROOT" == /home/* ]] && pass "project under /home" || fail "project at $ROOT; keep videos under /home"
} | tee "$OUT"
echo "Saved: $OUT"
