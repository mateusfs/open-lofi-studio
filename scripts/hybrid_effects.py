#!/usr/bin/env python3
"""Composição híbrida: footage real mascarado + partículas OpenCV (nunca tela cheia)."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import cv2
import numpy as np
from PIL import Image

WIDTH = 1920
HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_SECONDS = 54
OVERLAYS_DIR = Path(__file__).resolve().parent.parent / "assets" / "images" / "overlays"
ENCODE_PRESET = "medium"
ENCODE_CRF = "16"

BlendMode = Literal["screen", "overlay", "softlight", "addition", "lighten"]
BLEND_MODES: frozenset[str] = frozenset({"screen", "overlay", "softlight", "addition", "lighten"})


@dataclass(frozen=True)
class HybridLayer:
    layer_id: str
    kind: Literal["footage", "procedural"]
    footage: Path | None
    mask: Path | None
    opacity: float
    blend: BlendMode
    effect: str | None
    intensity: float


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stderr[-2500:]}")


def resolve_path(raw: str | Path, base: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidates = [base / path, OVERLAYS_DIR / path, Path(__file__).resolve().parent.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return base / path


def parse_blend(raw: object) -> BlendMode:
    blend = str(raw).lower()
    if blend not in BLEND_MODES:
        raise ValueError(f"unsupported blend: {blend}")
    return cast(BlendMode, blend)


def parse_layer(raw: dict[str, object], production_dir: Path) -> HybridLayer:
    layer_id = str(raw.get("id", "layer"))
    kind_raw = str(raw.get("kind", "footage" if raw.get("footage") else "procedural")).lower()
    kind: Literal["footage", "procedural"] = "procedural" if kind_raw == "procedural" else "footage"
    opacity = float(raw.get("opacity", 0.45))
    if opacity <= 0.0 or opacity > 1.0:
        raise ValueError(f"opacity must be in (0, 1]: {opacity}")
    blend = parse_blend(raw.get("blend", "screen"))
    footage_raw = raw.get("footage")
    mask_raw = raw.get("mask", "effect-mask.png")
    footage = resolve_path(str(footage_raw), production_dir / "source") if footage_raw else None
    mask = resolve_path(str(mask_raw), production_dir / "source") if mask_raw else None
    if kind == "footage" and (footage is None or not footage.exists()):
        raise FileNotFoundError(f"footage missing for layer {layer_id}: {footage_raw}")
    if mask is not None and not mask.exists():
        raise FileNotFoundError(f"mask missing for layer {layer_id}: {mask}")
    effect = str(raw.get("effect")) if raw.get("effect") else None
    intensity = float(raw.get("intensity", 0.45))
    return HybridLayer(
        layer_id=layer_id,
        kind=kind,
        footage=footage,
        mask=mask,
        opacity=opacity,
        blend=blend,
        effect=effect,
        intensity=intensity,
    )


def load_mask_array(mask_path: Path) -> np.ndarray:
    image = Image.open(mask_path).convert("L").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    return arr


def refine_mask(mask: np.ndarray, erode: int = 1, blur: int = 5) -> np.ndarray:
    uint8 = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    if erode > 0:
        kernel = np.ones((erode * 2 + 1, erode * 2 + 1), np.uint8)
        uint8 = cv2.erode(uint8, kernel, iterations=1)
    if blur > 0:
        odd = blur if blur % 2 == 1 else blur + 1
        uint8 = cv2.GaussianBlur(uint8, (odd, odd), 0)
    return uint8.astype(np.float32) / 255.0


def screen_blend(base: np.ndarray, overlay: np.ndarray, amount: np.ndarray) -> np.ndarray:
    base_f = base.astype(np.float32)
    over_f = overlay.astype(np.float32)
    screened = 255.0 - ((255.0 - base_f) * (255.0 - over_f) / 255.0)
    amount_3 = amount[:, :, np.newaxis]
    return np.clip(base_f * (1.0 - amount_3) + screened * amount_3, 0, 255).astype(np.uint8)


def softlight_blend(base: np.ndarray, overlay: np.ndarray, amount: np.ndarray) -> np.ndarray:
    base_f = base.astype(np.float32) / 255.0
    over_f = overlay.astype(np.float32) / 255.0
    result = (1.0 - 2.0 * over_f) * base_f * base_f + 2.0 * over_f * base_f
    amount_3 = amount[:, :, np.newaxis]
    mixed = base_f * (1.0 - amount_3) + result * amount_3
    return np.clip(mixed * 255.0, 0, 255).astype(np.uint8)


def apply_blend(
    base: np.ndarray,
    overlay: np.ndarray,
    amount: np.ndarray,
    blend: BlendMode,
) -> np.ndarray:
    if blend == "screen":
        return screen_blend(base, overlay, amount)
    if blend == "softlight":
        return softlight_blend(base, overlay, amount)
    if blend in {"addition", "lighten"}:
        base_f = base.astype(np.float32)
        over_f = overlay.astype(np.float32)
        amount_3 = amount[:, :, np.newaxis]
        added = np.minimum(base_f + over_f * amount_3, 255.0)
        return added.astype(np.uint8)
    base_f = base.astype(np.float32)
    over_f = overlay.astype(np.float32)
    amount_3 = amount[:, :, np.newaxis]
    return np.clip(base_f * (1.0 - amount_3) + over_f * amount_3, 0, 255).astype(np.uint8)


def render_dust_particles(
    frame_index: int,
    total_frames: int,
    seed: int,
    intensity: float,
    mask: np.ndarray,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    overlay = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    count = int(90 + intensity * 140)
    ys, xs = np.where(mask > 0.35)
    if xs.size == 0:
        return overlay
    for index in range(count):
        particle_rng = np.random.default_rng(seed + index * 17)
        pick = int(particle_rng.integers(0, xs.size))
        base_x = int(xs[pick])
        base_y = int(ys[pick])
        drift = (frame_index / max(total_frames, 1)) * total_frames
        x = int(base_x + np.sin(frame_index / 40.0 + index) * (6 + intensity * 10))
        y = int((base_y + drift * (0.15 + particle_rng.random() * 0.35) + index * 7) % HEIGHT)
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            continue
        if mask[y, x] < 0.35:
            continue
        radius = 1 if particle_rng.random() < 0.75 else 2
        alpha = int(40 + intensity * 90)
        cv2.circle(overlay, (x, y), radius, (210, 205, 195), -1, lineType=cv2.LINE_AA)
        overlay[y, x] = (
            min(255, int(overlay[y, x, 0]) + alpha),
            min(255, int(overlay[y, x, 1]) + alpha),
            min(255, int(overlay[y, x, 2]) + int(alpha * 0.85)),
        )
    blur = cv2.GaussianBlur(overlay, (0, 0), sigmaX=1.2)
    amount = np.clip(mask, 0.0, 1.0)[:, :, np.newaxis]
    return np.clip(blur.astype(np.float32) * amount, 0, 255).astype(np.uint8)


def render_procedural_overlay(
    effect: str,
    frame_index: int,
    total_frames: int,
    seed: int,
    intensity: float,
    mask: np.ndarray,
) -> np.ndarray:
    name = effect.lower().strip()
    if name in {"dust", "dust_particles", "particles"}:
        return render_dust_particles(frame_index, total_frames, seed, intensity, mask)
    if name in {"embers", "fireflies"}:
        dust = render_dust_particles(frame_index, total_frames, seed + 99, intensity * 0.7, mask)
        warm = dust.astype(np.float32)
        warm[:, :, 0] *= 1.15
        warm[:, :, 1] *= 0.75
        warm[:, :, 2] *= 0.35
        return np.clip(warm, 0, 255).astype(np.uint8)
    return render_dust_particles(frame_index, total_frames, seed, intensity, mask)


def open_video_capture(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open footage: {path}")
    return capture


def read_looped_frame(capture: cv2.VideoCapture, frame_index: int) -> np.ndarray:
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    target = frame_index % total
    capture.set(cv2.CAP_PROP_POS_FRAMES, target)
    ok, frame = capture.read()
    if not ok or frame is None:
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = capture.read()
    if not ok or frame is None:
        raise RuntimeError("failed to read footage frame")
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if frame.shape[1] != WIDTH or frame.shape[0] != HEIGHT:
        frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    return frame


def compose_hybrid_loop(
    scene_path: Path,
    output_path: Path,
    layers: list[HybridLayer],
    seconds: float = DEFAULT_SECONDS,
    fps: int = DEFAULT_FPS,
    seed: int = 42,
    encode_preset: str = ENCODE_PRESET,
    scene_effects: list[str] | None = None,
    steam_origin: tuple[int, int] | None = None,
    steam_scale: float = 0.45,
    steam_color: tuple[int, int, int] = (210, 200, 190),
) -> None:
    if not scene_path.exists():
        raise FileNotFoundError(f"scene not found: {scene_path}")
    if not layers:
        raise ValueError("hybrid mode requires at least one layer")

    from animate_scene import render_steam
    from scene_effects import apply_scene_effects

    base = np.asarray(
        Image.open(scene_path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    )
    total_frames = int(round(seconds * fps))
    captures: dict[str, cv2.VideoCapture] = {}
    masks: dict[str, np.ndarray] = {}
    effects = [item for item in (scene_effects or []) if item and item != "steam"]
    steam_enabled = steam_origin is not None

    for layer in layers:
        if layer.mask is not None:
            masks[layer.layer_id] = refine_mask(load_mask_array(layer.mask))
        if layer.kind == "footage" and layer.footage is not None:
            captures[layer.layer_id] = open_video_capture(layer.footage)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            encode_preset,
            "-crf",
            ENCODE_CRF,
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(output_path),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert ffmpeg.stdin is not None

    try:
        for frame_index in range(total_frames):
            frame = base.copy()
            for layer in layers:
                mask = masks.get(layer.layer_id)
                if mask is None:
                    continue
                if layer.kind == "footage":
                    overlay = read_looped_frame(captures[layer.layer_id], frame_index)
                else:
                    effect_name = layer.effect or "dust_particles"
                    overlay = render_procedural_overlay(
                        effect_name,
                        frame_index,
                        total_frames,
                        seed + hash(layer.layer_id) % 10_000,
                        layer.intensity,
                        mask,
                    )
                amount = np.clip(mask * layer.opacity, 0.0, 1.0)
                frame = apply_blend(frame, overlay, amount, layer.blend)
            if effects:
                composed = apply_scene_effects(
                    frame,
                    frame_index,
                    total_frames,
                    effects,
                    seed,
                    None,
                    None,
                )
                frame = np.asarray(composed.convert("RGB"))
            if steam_enabled and steam_origin is not None:
                rgba = Image.fromarray(frame, mode="RGB").convert("RGBA")
                rgba = Image.alpha_composite(
                    rgba,
                    render_steam(steam_origin, steam_scale, frame_index, color=steam_color),
                )
                frame = np.asarray(rgba.convert("RGB"))
            ffmpeg.stdin.write(frame.tobytes())
    finally:
        ffmpeg.stdin.close()
        for capture in captures.values():
            capture.release()
        ffmpeg.wait()

    if ffmpeg.returncode != 0:
        raise RuntimeError("FFmpeg encoding failed for hybrid loop")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera loop híbrido mascarado")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--production-dir", type=Path, required=True)
    parser.add_argument("--layers", type=str, required=True, help="JSON array de layers")
    parser.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--preset", type=str, default=ENCODE_PRESET)
    parser.add_argument("--effects", type=str, default="")
    parser.add_argument("--steam-x", type=int, default=None)
    parser.add_argument("--steam-y", type=int, default=None)
    parser.add_argument("--steam-scale", type=float, default=0.45)
    parser.add_argument("--steam-color", type=str, default="210,200,190")
    args = parser.parse_args()

    raw_layers = json.loads(args.layers)
    if not isinstance(raw_layers, list):
        raise ValueError("--layers must be a JSON array")
    layers = [parse_layer(item, args.production_dir.resolve()) for item in raw_layers if isinstance(item, dict)]
    effects = [item.strip() for item in args.effects.split(",") if item.strip()]
    steam_origin = None
    if args.steam_x is not None and args.steam_y is not None:
        steam_origin = (args.steam_x, args.steam_y)
    color_parts = [int(part.strip()) for part in args.steam_color.split(",")]
    steam_color = (color_parts[0], color_parts[1], color_parts[2])
    compose_hybrid_loop(
        args.scene,
        args.output,
        layers,
        seconds=args.seconds,
        fps=args.fps,
        seed=args.seed,
        encode_preset=args.preset,
        scene_effects=effects,
        steam_origin=steam_origin,
        steam_scale=args.steam_scale,
        steam_color=steam_color,
    )
    print(f"Hybrid loop saved: {args.output} ({args.seconds:g}s @ {args.fps}fps)")


if __name__ == "__main__":
    main()
