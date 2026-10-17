#!/usr/bin/env python3
"""Build a clean submission ZIP of this project in dist/ (the project is not modified).

    python3 scripts/package_submission.py [--include-models] [--out DIR]

Excluded: virtual environments, git metadata, Python caches, dist/, regenerable
synthetic outputs (data/synthetic/), secrets (.env, keys, credentials), and by
default large GPU-specific artifacts (TensorRT engines, ONNX models, videos).
The PipeGen export folder (pipegen_project/export/) is included; pass
--include-models to keep its *.engine / *.onnx files too.
A SUBMISSION_MANIFEST.txt (path, size, sha256) is written into the archive.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "workplace_safety_sentinel"

EXCLUDED_DIRS = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
                 ".ruff_cache", "dist", ".idea", ".vscode"}
EXCLUDED_PATH_PREFIXES = ("data/synthetic/",)
EXCLUDED_FILES = ["*.pyc", "*.pyo", "*.tmp", "*.swp", "*~", ".DS_Store",
                  ".env", ".env.*", "*.pem", "*.key", "*credentials*", "*.secret"]
MODEL_FILES = ["*.engine", "*.plan", "*.onnx", "*.etlt", "*.mp4", "*.h264", "*.mkv", "*.avi"]
MAX_FILE_BYTES = 50 * 1024 * 1024


def excluded(rel: str, include_models: bool) -> str | None:
    parts = rel.split("/")
    if any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return "directory"
    if rel.startswith(EXCLUDED_PATH_PREFIXES):
        return "regenerable output"
    name = parts[-1]
    if any(fnmatch.fnmatch(name, pat) for pat in EXCLUDED_FILES):
        return "cache/temp/secret"
    if not include_models and any(fnmatch.fnmatch(name, pat) for pat in MODEL_FILES):
        return "model/video (use --include-models)"
    return None


def collect(include_models: bool) -> tuple[list[Path], dict[str, list[str]]]:
    keep, skipped = [], {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ROOT).as_posix()
        reason = excluded(rel, include_models)
        if reason is None and path.stat().st_size > MAX_FILE_BYTES:
            reason = f"larger than {MAX_FILE_BYTES // 2**20} MB"
        if reason:
            if not any(f"/{d}/" in f"/{rel}" for d in (".venv", ".git", "__pycache__", ".pytest_cache")):
                skipped.setdefault(reason, []).append(rel)
        else:
            keep.append(path)
    return keep, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--include-models", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)

    files, skipped = collect(args.include_models)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{NAME}_submission.zip"   # rebuilt in place; build time is in the manifest

    manifest = [f"# {NAME} submission manifest, built {datetime.now().isoformat(timespec='seconds')}",
                "# path\tbytes\tsha256"]
    tmp_path = zip_path.with_suffix(".zip.partial")
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest.append(f"{rel}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}")
            zf.write(path, f"{NAME}/{rel}")
        zf.writestr(f"{NAME}/SUBMISSION_MANIFEST.txt", "\n".join(manifest) + "\n")

    with zipfile.ZipFile(tmp_path) as zf:
        bad = zf.testzip()
    if bad:
        print(f"ERROR: corrupt member {bad} in {tmp_path}", file=sys.stderr)
        return 1
    tmp_path.replace(zip_path)   # only a verified archive replaces the previous one
    print(f"wrote {zip_path} ({zip_path.stat().st_size / 1024:.0f} KiB, {len(files)} files + manifest)")
    for reason, paths in sorted(skipped.items()):
        print(f"  excluded ({reason}): {len(paths)} file(s), e.g. {paths[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
