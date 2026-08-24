#!/usr/bin/env python3
"""Resolve modo de animação e utilitários de cena/QA visual."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


DEFAULT_ANIMATE_MODE = "locked"
STEAM_AUTO_MIN_CONFIDENCE = 0.05
STEAM_DISABLE_CONFIDENCE = 0.02


def resolve_animate_mode(animate: dict) -> str:
    layers = animate.get("layers")
    if isinstance(layers, list) and layers:
        return "hybrid"
    raw = animate.get("mode")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_ANIMATE_MODE
    mode = str(raw).strip().lower()
    if mode in {"default", "auto"}:
        return DEFAULT_ANIMATE_MODE
    return mode


def apply_calibration_to_meta(production_dir: Path, calibration: dict[str, object]) -> dict:
    meta_path = production_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    animate = dict(meta.get("animate", {}))
    steam = calibration.get("steam")
    if not isinstance(steam, dict) or animate.get("noSteam", False):
        return meta

    confidence = float(steam.get("confidence", 0.0))
    used_fallback = bool(steam.get("used_fallback", False))
    if animate.get("autoSteam", True) and (used_fallback or confidence < STEAM_AUTO_MIN_CONFIDENCE):
        animate["autoSteam"] = False
        if not used_fallback:
            animate["steamX"] = int(steam["detected_x"])
            animate["steamY"] = int(steam["detected_y"])
        if confidence < STEAM_DISABLE_CONFIDENCE and used_fallback:
            animate["noSteam"] = True
        meta["animate"] = animate
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(
            "Calibração: autoSteam=false"
            + (", noSteam=true" if animate.get("noSteam") else "")
        )
    return meta


def export_loop_seam_frame(loop_path: Path, output_path: Path) -> None:
    if not loop_path.exists():
        return
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(loop_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(probe.stdout.strip())
    seek = max(duration - 0.5, 0.0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seek:.3f}",
            "-i",
            str(loop_path),
            "-frames:v",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
