#!/usr/bin/env python3
"""Anima cena estática com Ken Burns e overlays atmosféricos reais via FFmpeg."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

WIDTH = 1920
HEIGHT = 1080
FPS = 24
LOOP_SECONDS = 24
ENCODE_PRESET = "slow"
ENCODE_CRF = "16"
OVERLAYS_DIR = Path(__file__).resolve().parent.parent / "assets" / "images" / "overlays"
ZOOM_PAD = 1.12


@dataclass(frozen=True)
class OverlayLayer:
    path: Path
    opacity: float
    blend: str


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stderr[-2500:]}")


def resolve_overlay(entry: str | dict[str, object]) -> OverlayLayer:
    if isinstance(entry, str):
        path = Path(entry)
        opacity = 0.18
        blend = "screen"
    else:
        file_name = str(entry.get("file", ""))
        if not file_name:
            raise ValueError("Overlay entry requires 'file'")
        path = Path(file_name)
        opacity = float(entry.get("opacity", 0.18))
        blend = str(entry.get("blend", "screen")).lower()

    if not path.is_absolute():
        path = OVERLAYS_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"Overlay not found: {path}")
    if opacity <= 0.0 or opacity > 1.0:
        raise ValueError(f"Overlay opacity must be in (0, 1]: {opacity}")
    if blend not in {"screen", "overlay", "softlight", "addition", "lighten"}:
        raise ValueError(f"Unsupported blend mode: {blend}")
    return OverlayLayer(path=path, opacity=opacity, blend=blend)


def build_filter_complex(
    overlays: list[OverlayLayer],
    zoom_amount: float,
    pan_x: float,
    pan_y: float,
    breathe: float,
    total_frames: int,
) -> str:
    pad_w = int(WIDTH * ZOOM_PAD)
    pad_h = int(HEIGHT * ZOOM_PAD)
    zoom_expr = f"1+{zoom_amount:.5f}*sin(2*PI*on/{total_frames})"
    x_expr = (
        f"(iw-iw/zoom)/2+{pan_x:.3f}*sin(2*PI*on/{total_frames})"
    )
    y_expr = (
        f"(ih-ih/zoom)/2+{pan_y:.3f}*cos(2*PI*on/{total_frames})"
    )
    breathe_expr = f"{breathe:.5f}*sin(2*PI*t/11)"
    saturation_expr = f"1+{max(breathe, 0.0) * 1.6:.5f}*sin(2*PI*t/17)"

    filters: list[str] = [
        (
            f"[0:v]scale={pad_w}:{pad_h}:force_original_aspect_ratio=increase,"
            f"crop={pad_w}:{pad_h},setsar=1,"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=1:"
            f"s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"eq=brightness='{breathe_expr}':saturation='{saturation_expr}',"
            f"format=yuv420p[base]"
        )
    ]

    current = "base"
    for index, layer in enumerate(overlays, start=1):
        scaled = f"ov{index}"
        blended = f"b{index}"
        filters.append(
            f"[{index}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1,format=yuv420p,"
            f"eq=brightness=-0.08:contrast=1.15[{scaled}]"
        )
        filters.append(
            f"[{current}][{scaled}]blend=all_mode={layer.blend}:"
            f"all_opacity={layer.opacity:.4f}:shortest=1[{blended}]"
        )
        current = blended

    filters.append(f"[{current}]format=yuv420p[outv]")
    return ";".join(filters)


def animate_cinematic(
    scene: Path,
    output: Path,
    overlays: list[OverlayLayer],
    zoom_amount: float = 0.028,
    pan_x: float = 26.0,
    pan_y: float = 14.0,
    breathe: float = 0.008,
    loop_seconds: int = LOOP_SECONDS,
) -> None:
    if not scene.exists():
        raise FileNotFoundError(f"Scene not found: {scene}")
    if zoom_amount < 0.0 or zoom_amount > 0.12:
        raise ValueError("zoom_amount must be between 0 and 0.12")
    if breathe < 0.0 or breathe > 0.05:
        raise ValueError("breathe must be between 0 and 0.05")

    output.parent.mkdir(parents=True, exist_ok=True)
    total_frames = FPS * loop_seconds
    filter_complex = build_filter_complex(
        overlays=overlays,
        zoom_amount=zoom_amount,
        pan_x=pan_x,
        pan_y=pan_y,
        breathe=breathe,
        total_frames=total_frames,
    )

    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-i",
        str(scene),
    ]
    for layer in overlays:
        command.extend(["-stream_loop", "-1", "-i", str(layer.path)])

    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-t",
            str(loop_seconds),
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
    run_command(command)


def parse_overlays_arg(raw: str | None) -> list[OverlayLayer]:
    if raw is None or raw.strip() == "":
        return [
            resolve_overlay({"file": "dust-floating-black.mp4", "opacity": 0.2, "blend": "screen"}),
            resolve_overlay({"file": "light-leaks.mp4", "opacity": 0.08, "blend": "screen"}),
        ]
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("--overlays must be a JSON list")
    return [resolve_overlay(item) for item in payload]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cinematic Ken Burns + atmospheric overlays")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlays", type=str, default=None)
    parser.add_argument("--zoom", type=float, default=0.028)
    parser.add_argument("--pan-x", type=float, default=26.0)
    parser.add_argument("--pan-y", type=float, default=14.0)
    parser.add_argument("--breathe", type=float, default=0.008)
    parser.add_argument("--seconds", type=int, default=LOOP_SECONDS)
    args = parser.parse_args()

    overlays = parse_overlays_arg(args.overlays)
    animate_cinematic(
        scene=args.scene,
        output=args.output,
        overlays=overlays,
        zoom_amount=args.zoom,
        pan_x=args.pan_x,
        pan_y=args.pan_y,
        breathe=args.breathe,
        loop_seconds=args.seconds,
    )
    print(f"Wrote cinematic loop: {args.output}")


if __name__ == "__main__":
    main()
