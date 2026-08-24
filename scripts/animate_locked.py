#!/usr/bin/env python3
"""Anima cena com câmera travada: still looped, sem zoompan/pan/breathe."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

WIDTH = 1920
HEIGHT = 1080
FPS = 24
LOOP_SECONDS = 30
ENCODE_PRESET = "slow"
ENCODE_CRF = "16"


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stderr[-2500:]}")


def animate_locked(
    scene: Path,
    output: Path,
    loop_seconds: int = LOOP_SECONDS,
) -> None:
    if not scene.exists():
        raise FileNotFoundError(f"Scene not found: {scene}")
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},format=yuv420p"
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            str(scene),
            "-t",
            str(loop_seconds),
            "-vf",
            vf,
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            ENCODE_PRESET,
            "-crf",
            ENCODE_CRF,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(output),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Locked-camera still loop (no Ken Burns)")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=LOOP_SECONDS)
    args = parser.parse_args()
    animate_locked(args.scene, args.output, args.seconds)
    print(f"Wrote locked loop: {args.output}")


if __name__ == "__main__":
    main()
