#!/usr/bin/env python3
"""Gera loop de vídeo animado (chuva, vapor, flicker de luz) a partir da cena base."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH = 1920
HEIGHT = 1080
FPS = 24
LOOP_SECONDS = 20
TOTAL_FRAMES = FPS * LOOP_SECONDS
ENCODE_PRESET = "slow"
ENCODE_CRF = "16"
STEAM_SCALE_MIN = 0.2

WINDOW_COVERAGE_MIN = 0.04
WINDOW_COVERAGE_MAX = 0.55
STEAM_CONFIDENCE_MIN = 0.012
RAIN_CONFIDENCE_MIN = 0.06

DESK_Y_START_RATIO = 0.55
DESK_Y_END_RATIO = 0.92
WINDOW_Y_END_RATIO = 0.65
STEAM_SEARCH_Y_START_RATIO = 0.54
STEAM_SEARCH_Y_END_RATIO = 0.88
STEAM_SPAN_MIN = 0.08
STEAM_SPAN_MAX = 0.55
STEAM_COLUMN_DENSITY_MIN = 0.02
STEAM_ABOVE_MIN = 0.06
LOCAL_DARK_MIN = 10.0
MUG_RIM_ABOVE_BODY = 77
LEFT_HALF_RATIO = 0.55
LEFT_OVERRIDE_MAX_RATIO = 0.35
LED_BLUE_DOMINANCE = 35.0


@dataclass
class RainLayer:
    count: int
    speed: float
    length: int
    thickness: int
    alpha: int


@dataclass
class DetectionResult:
    steam_x: int
    steam_y: int
    steam_auto: bool
    rain_auto: bool
    confidence_steam: float = 0.0
    confidence_rain: float = 0.0
    debug_info: dict[str, float | int | bool] | None = None


RAIN_LAYERS = [
    RainLayer(count=70, speed=7.5, length=26, thickness=1, alpha=26),
    RainLayer(count=40, speed=15.0, length=42, thickness=2, alpha=20),
]


def _channel_stats(base: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    red = base[:, :, 0]
    green = base[:, :, 1]
    blue = base[:, :, 2]
    brightness = (red + green + blue) / 3.0
    return red, green, blue, brightness


def _desk_bounds() -> tuple[int, int]:
    return int(HEIGHT * DESK_Y_START_RATIO), int(HEIGHT * DESK_Y_END_RATIO)


def _steam_search_bounds() -> tuple[int, int]:
    return int(HEIGHT * STEAM_SEARCH_Y_START_RATIO), int(HEIGHT * STEAM_SEARCH_Y_END_RATIO)


def _local_dark_support(brightness: np.ndarray, center_x: int, base_y: int) -> float:
    below_y0 = min(HEIGHT - 1, base_y + 5)
    below_y1 = min(HEIGHT, base_y + 45)
    side_y0 = below_y0
    side_y1 = below_y1
    below_x0 = max(0, center_x - 25)
    below_x1 = min(WIDTH, center_x + 26)
    left_x0 = max(0, center_x - 120)
    left_x1 = max(0, center_x - 70)
    right_x0 = min(WIDTH, center_x + 70)
    right_x1 = min(WIDTH, center_x + 120)
    if below_y1 <= below_y0 or below_x1 <= below_x0:
        return 0.0
    below_mean = float(brightness[below_y0:below_y1, below_x0:below_x1].mean())
    left_mean = float(brightness[side_y0:side_y1, left_x0:left_x1].mean()) if left_x1 > left_x0 else below_mean
    right_mean = float(brightness[side_y0:side_y1, right_x0:right_x1].mean()) if right_x1 > right_x0 else below_mean
    return min(left_mean, right_mean) - below_mean


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    labeled = np.zeros(mask.shape, dtype=np.int32)
    current_label = 0
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or labeled[y, x]:
                continue
            current_label += 1
            stack = [(y, x)]
            labeled[y, x] = current_label
            while stack:
                cy, cx = stack.pop()
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and labeled[ny, nx] == 0:
                        labeled[ny, nx] = current_label
                        stack.append((ny, nx))
    return labeled, current_label


def _component_boxes(
    labeled: np.ndarray,
    label_count: int,
) -> list[tuple[int, int, int, int, int]]:
    boxes: list[tuple[int, int, int, int, int]] = []
    for label_id in range(1, label_count + 1):
        ys, xs = np.where(labeled == label_id)
        if ys.size == 0:
            continue
        area = int(ys.size)
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        boxes.append((area, x0, y0, x1, y1))
    return boxes


def _build_steam_column_mask(
    region_brightness: np.ndarray,
    region_red: np.ndarray,
    region_green: np.ndarray,
    region_blue: np.ndarray,
) -> np.ndarray:
    bright_threshold = float(np.percentile(region_brightness, 77))
    low_chroma = (
        (np.abs(region_red - region_green) < 42)
        & (np.abs(region_green - region_blue) < 42)
    )
    led_pixels = (
        (region_blue - region_red > LED_BLUE_DOMINANCE)
        & (region_blue > region_green)
    )
    return (region_brightness >= bright_threshold) & low_chroma & ~led_pixels


def _collect_steam_column_candidates(
    brightness: np.ndarray,
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
) -> list[tuple[float, int, int, float]]:
    search_y0, search_y1 = _steam_search_bounds()
    region_brightness = brightness[search_y0:search_y1, :]
    region_red = red[search_y0:search_y1, :]
    region_green = green[search_y0:search_y1, :]
    region_blue = blue[search_y0:search_y1, :]
    steam_mask = _build_steam_column_mask(region_brightness, region_red, region_green, region_blue)
    candidates: list[tuple[float, int, int, float]] = []
    roi_height = steam_mask.shape[0]
    for center_x in range(WIDTH):
        column = steam_mask[:, center_x]
        if not column.any():
            continue
        rows = np.where(column)[0]
        span = (rows.max() - rows.min() + 1) / max(roi_height, 1)
        density = float(column.mean())
        if span > STEAM_SPAN_MAX or span < STEAM_SPAN_MIN or density < STEAM_COLUMN_DENSITY_MIN:
            continue
        bottom_y = int(rows.max()) + search_y0
        best_local_dark = -999.0
        best_body_y = bottom_y
        for base_y in range(bottom_y - 50, bottom_y + 50, 3):
            if base_y < search_y0 or base_y > search_y1:
                continue
            local_dark = _local_dark_support(brightness, center_x, base_y)
            if local_dark > best_local_dark:
                best_local_dark = local_dark
                best_body_y = base_y
        if best_local_dark < LOCAL_DARK_MIN:
            continue
        rim_y = max(0, best_body_y - MUG_RIM_ABOVE_BODY)
        steam_above = _steam_density_above(brightness, red, green, blue, center_x, best_body_y)
        if steam_above < STEAM_ABOVE_MIN:
            continue
        score = (best_local_dark / 40.0) * (steam_above + 0.05) * min(span, 0.45)
        candidates.append((score, center_x, rim_y, best_local_dark))
    return candidates


def _pick_steam_cluster(
    candidates: list[tuple[float, int, int, float]],
) -> tuple[float, int, int, float] | None:
    if not candidates:
        return None
    clusters = _cluster_column_scores([(score, x, rim_y) for score, x, rim_y, _ in candidates])
    best_cluster = clusters[0]
    split_x = int(WIDTH * LEFT_HALF_RATIO)
    if best_cluster[1] >= split_x:
        left_clusters = [cluster for cluster in clusters if cluster[1] < split_x]
        if left_clusters and left_clusters[0][0] < best_cluster[0] * LEFT_OVERRIDE_MAX_RATIO:
            best_cluster = left_clusters[0]
    cluster_x = best_cluster[1]
    cluster_candidates = [
        candidate
        for candidate in candidates
        if abs(candidate[1] - cluster_x) <= 24
    ]
    if not cluster_candidates:
        return None
    return max(cluster_candidates)


def detect_steam_origin(
    base: np.ndarray,
    fallback: tuple[int, int],
) -> tuple[tuple[int, int], bool, float]:
    red, green, blue, brightness = _channel_stats(base)
    candidates = _collect_steam_column_candidates(brightness, red, green, blue)
    best_candidate = _pick_steam_cluster(candidates)
    if best_candidate is None:
        return fallback, False, 0.0
    best_score, center_x, rim_y, _ = best_candidate
    if best_score < STEAM_CONFIDENCE_MIN:
        return fallback, False, best_score
    return (center_x, rim_y), True, min(best_score, 1.0)


def _steam_density_above(
    brightness: np.ndarray,
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
    center_x: int,
    rim_y: int,
) -> float:
    top_y = max(0, rim_y - int(HEIGHT * 0.18))
    x0 = max(0, center_x - 24)
    x1 = min(WIDTH, center_x + 25)
    if rim_y <= top_y:
        return 0.0
    region_brightness = brightness[top_y:rim_y, x0:x1]
    region_red = red[top_y:rim_y, x0:x1]
    region_green = green[top_y:rim_y, x0:x1]
    region_blue = blue[top_y:rim_y, x0:x1]
    if region_brightness.size == 0:
        return 0.0
    bright_threshold = float(np.percentile(region_brightness, 72))
    low_chroma = (
        (np.abs(region_red - region_green) < 42)
        & (np.abs(region_green - region_blue) < 42)
    )
    led_pixels = (region_blue - region_red > LED_BLUE_DOMINANCE) & (region_blue > region_green)
    steam_mask = (region_brightness >= bright_threshold) & low_chroma & ~led_pixels
    return float(steam_mask.mean())


def _cluster_column_scores(
    scores: list[tuple[float, int, int]],
    merge_distance: int = 22,
) -> list[tuple[float, int, int]]:
    if not scores:
        return []
    scores = sorted(scores, reverse=True)
    clusters: list[list[tuple[float, int, int]]] = []
    for item in scores:
        placed = False
        for cluster in clusters:
            if abs(item[1] - cluster[0][1]) <= merge_distance:
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    merged: list[tuple[float, int, int]] = []
    for cluster in clusters:
        weight_total = sum(score for score, _, _ in cluster)
        center_x = int(round(sum(score * x for score, x, _ in cluster) / weight_total))
        base_y = int(round(sum(score * y for score, _, y in cluster) / weight_total))
        merged.append((weight_total / len(cluster), center_x, base_y))
    merged.sort(reverse=True)
    return merged


def _longest_dense_run(values: np.ndarray, threshold: float, min_length: int) -> tuple[int, int]:
    best_start = 0
    best_end = -1
    run_start = 0
    active = False
    for index, value in enumerate(values):
        if value >= threshold:
            if not active:
                run_start = index
                active = True
            if index - run_start >= best_end - best_start:
                best_start = run_start
                best_end = index
        else:
            active = False
    if best_end - best_start + 1 < min_length:
        return 0, 0
    return best_start, best_end


def _window_texture_score(brightness: np.ndarray, row_start: int, row_end: int, col_start: int, col_end: int) -> float:
    region = brightness[row_start : row_end + 1, col_start : col_end + 1]
    if region.shape[1] < 2:
        return 0.0
    return float(np.abs(np.diff(region, axis=1)).mean())


def detect_window_mask(base: np.ndarray) -> tuple[Image.Image, bool, float]:
    red, green, blue, brightness = _channel_stats(base)
    window_y1 = int(HEIGHT * WINDOW_Y_END_RATIO)
    upper_brightness = brightness[:window_y1, :]
    upper_red = red[:window_y1, :]
    upper_green = green[:window_y1, :]
    upper_blue = blue[:window_y1, :]

    brightness_low = float(np.percentile(upper_brightness, 30))
    brightness_high = float(np.percentile(upper_brightness, 90))
    glass_mask = (upper_brightness >= brightness_low) & (upper_brightness <= brightness_high)
    led_mask = (
        (upper_blue - upper_red > LED_BLUE_DOMINANCE)
        & (upper_blue > upper_green)
        & (upper_brightness > float(np.percentile(upper_brightness, 78)))
    )
    candidate_mask = glass_mask & ~led_mask

    column_density = candidate_mask.mean(axis=0)
    row_density = candidate_mask.mean(axis=1)
    column_start, column_end = _longest_dense_run(column_density, 0.22, 180)
    row_start, row_end = _longest_dense_run(row_density, 0.22, 80)

    window_score = np.zeros((window_y1, WIDTH), dtype=np.float32)
    texture_score = 0.0
    if column_end > column_start and row_end > row_start:
        texture_score = _window_texture_score(upper_brightness, row_start, row_end, column_start, column_end)
        if texture_score >= 3.0:
            window_score[row_start : row_end + 1, column_start : column_end + 1] = 1.0

    labeled, label_count = _label_components(window_score > 0.5)
    max_point_area = int(window_score.size * 0.015)
    for area, x0, y0, x1, y1 in _component_boxes(labeled, label_count):
        if area < 200:
            label_id = int(labeled[y0, x0])
            window_score[labeled == label_id] = 0.0
            continue
        width = x1 - x0 + 1
        height = y1 - y0 + 1
        if area <= max_point_area and max(width, height) < 70:
            label_id = int(labeled[y0, x0])
            window_score[labeled == label_id] = 0.0

    window_score = np.clip(window_score, 0.0, 1.0)
    coverage = float(window_score.sum()) / float(HEIGHT * WIDTH)
    confidence = min(coverage * 2.2, 1.0)
    confident = (
        WINDOW_COVERAGE_MIN <= coverage <= WINDOW_COVERAGE_MAX
        and confidence >= RAIN_CONFIDENCE_MIN
    )

    mask_array = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    if confident:
        mask_array[:window_y1, :] = window_score

    mask_image = Image.fromarray((mask_array * 255).astype(np.uint8), mode="L")
    mask_image = mask_image.filter(ImageFilter.GaussianBlur(12))
    if not confident:
        empty = Image.new("L", (WIDTH, HEIGHT), 0)
        return empty, False, 0.0
    return mask_image, True, confidence


def load_scene(scene_path: Path) -> np.ndarray:
    image = Image.open(scene_path).convert("RGB")
    src_w, src_h = image.size
    target_ratio = WIDTH / HEIGHT
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        image = image.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        image = image.crop((0, top, src_w, top + new_h))
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32)


def resolve_detection(
    base: np.ndarray,
    steam_fallback: tuple[int, int],
    auto_rain: bool,
    auto_steam: bool,
) -> tuple[Image.Image | None, DetectionResult]:
    rain_mask: Image.Image | None = None
    rain_auto = False
    rain_confidence = 0.0
    steam_origin = steam_fallback
    steam_auto = False
    steam_confidence = 0.0

    if auto_rain:
        rain_mask, rain_auto, rain_confidence = detect_window_mask(base)
    if auto_steam:
        steam_origin, steam_auto, steam_confidence = detect_steam_origin(base, steam_fallback)

    debug_info: dict[str, float | int | bool] | None = None
    if auto_steam or auto_rain:
        debug_info = {
            "steam_x": steam_origin[0],
            "steam_y": steam_origin[1],
            "steam_auto": steam_auto,
            "confidence_steam": steam_confidence,
            "rain_auto": rain_auto,
            "confidence_rain": rain_confidence,
        }

    return rain_mask, DetectionResult(
        steam_x=steam_origin[0],
        steam_y=steam_origin[1],
        steam_auto=steam_auto,
        rain_auto=rain_auto,
        confidence_steam=steam_confidence,
        confidence_rain=rain_confidence,
        debug_info=debug_info,
    )


def build_rain_drops(rng: np.random.Generator) -> list[tuple[RainLayer, np.ndarray, np.ndarray]]:
    drops = []
    for layer in RAIN_LAYERS:
        xs = rng.integers(0, WIDTH, layer.count)
        ys = rng.integers(0, HEIGHT, layer.count)
        drops.append((layer, xs, ys))
    return drops


def render_rain(
    frame_index: int,
    drops: list[tuple[RainLayer, np.ndarray, np.ndarray]],
    rain_mask: Image.Image | None,
) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for layer, xs, ys in drops:
        offset = (layer.speed * frame_index) % HEIGHT
        for x, y in zip(xs, ys):
            drop_y = (y + offset) % HEIGHT
            draw.line(
                (x, drop_y, x - 3, drop_y + layer.length),
                fill=(190, 210, 235, layer.alpha),
                width=layer.thickness,
            )
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.6))
    if rain_mask is None:
        return overlay
    masked = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    masked.paste(overlay, (0, 0), rain_mask)
    return masked


def should_enable_rain(rain_requested: bool, auto_rain: bool, rain_detected: bool) -> bool:
    if not rain_requested:
        return False
    if auto_rain and not rain_detected:
        return False
    return True


def should_enable_steam(steam_requested: bool, auto_steam: bool, steam_detected: bool) -> bool:
    if not steam_requested:
        return False
    if auto_steam and not steam_detected:
        return False
    return True


def steam_scale_for_progress(progress: float) -> float:
    clamped = max(0.0, min(1.0, progress))
    eased = 1.0 - (1.0 - clamped) ** 2
    return STEAM_SCALE_MIN + (1.0 - STEAM_SCALE_MIN) * (1.0 - eased)


def steam_scale_at_time(time_seconds: float, full_duration: float) -> float:
    if full_duration <= 0:
        return 1.0
    return steam_scale_for_progress(time_seconds / full_duration)


DEFAULT_STEAM_COLOR: tuple[int, int, int] = (248, 240, 228)


def parse_steam_color(value: object | None) -> tuple[int, int, int]:
    if value is None:
        return DEFAULT_STEAM_COLOR
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 3:
            raise ValueError(f"steamColor inválido: {value!r}")
        channels = [int(part) for part in parts]
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        channels = [int(channel) for channel in value]
    else:
        raise ValueError(f"steamColor inválido: {value!r}")
    if any(channel < 0 or channel > 255 for channel in channels):
        raise ValueError(f"steamColor fora de 0–255: {channels}")
    return channels[0], channels[1], channels[2]


def render_steam(
    origin: tuple[int, int],
    scale: float,
    animation_frame: int,
    color: tuple[int, int, int] = DEFAULT_STEAM_COLOR,
) -> Image.Image:
    if scale <= 0.01:
        return Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    box_w = max(100, int(180 * scale))
    box_h = max(140, int(260 * scale))
    overlay = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    phase = 2 * np.pi * animation_frame / TOTAL_FRAMES
    red, green, blue = color
    for wisp in range(2):
        wisp_phase = phase + wisp * 2.4
        for step in range(20):
            progress = step / 20 + (animation_frame / TOTAL_FRAMES)
            progress %= 1.0
            y = box_h - progress * box_h
            sway = np.sin(wisp_phase + progress * 4.2) * (7 + progress * 16) * scale
            x = box_w / 2 + sway + (wisp - 0.5) * 9 * scale
            radius = (2.8 + progress * 10) * scale
            alpha = int(
                48 * (1 - progress) * (0.7 + 0.3 * np.sin(wisp_phase + step)) * min(scale, 1.0)
            )
            if alpha <= 0:
                continue
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=(red, green, blue, min(alpha, 56)),
            )
    blur_radius = max(1.2, 3.6 * scale)
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur_radius))
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    canvas.paste(overlay, (origin[0] - box_w // 2, origin[1] - box_h))
    return canvas


def light_flicker(frame_index: int) -> float:
    phase = 2 * np.pi * frame_index / TOTAL_FRAMES
    return 1.0 + 0.015 * np.sin(phase * 2) + 0.008 * np.sin(phase * 5 + 1.3)


def apply_slow_zoom(frame: Image.Image, frame_index: int, total_frames: int) -> Image.Image:
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    scale = 1.0 + 0.018 * (0.5 + 0.5 * np.sin(phase))
    new_w = max(WIDTH + 2, int(round(WIDTH * scale)))
    new_h = max(HEIGHT + 2, int(round(HEIGHT * scale)))
    resized = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - WIDTH) // 2
    top = (new_h - HEIGHT) // 2
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def encode_loop(
    scene_path: Path,
    output_path: Path,
    steam_x: int,
    steam_y: int,
    seed: int,
    rain: bool = True,
    steam: bool = True,
    auto_rain: bool = True,
    auto_steam: bool = True,
    steam_scale: float = 1.0,
    steam_color: tuple[int, int, int] = DEFAULT_STEAM_COLOR,
    output_seconds: float | None = None,
    time_offset: float = 0.0,
    full_duration: float | None = None,
    effects: list[str] | None = None,
    effect_mask_path: Path | None = None,
) -> DetectionResult:
    from scene_effects import apply_scene_effects

    scene_effects = effects or []
    use_scene_effects = len(scene_effects) > 0
    rain_enabled = ("rain" in scene_effects) if use_scene_effects else rain
    steam_enabled = ("steam" in scene_effects) if use_scene_effects else steam
    auto_rain_enabled = auto_rain if use_scene_effects else auto_rain
    auto_steam_enabled = auto_steam if use_scene_effects else auto_steam

    window_effects = {
        "mist_drift",
        "sunrise_glow",
        "falling_leaves",
        "snow",
        "water_shimmer",
        "birds",
        "foliage_shimmer",
        "blinds_city_pulse",
        "city_haze",
    }
    needs_window_mask = use_scene_effects and bool(set(scene_effects) & window_effects)
    run_window_detect = (auto_rain_enabled and rain_enabled) or needs_window_mask

    base = load_scene(scene_path)
    rain_mask, detection = resolve_detection(
        base,
        (steam_x, steam_y),
        auto_rain=run_window_detect,
        auto_steam=auto_steam_enabled if steam_enabled else False,
    )
    rain_enabled = should_enable_rain(rain_enabled, auto_rain_enabled, detection.rain_auto)
    steam_enabled = should_enable_steam(
        steam_enabled, auto_steam_enabled, detection.steam_auto
    )
    if effect_mask_path is not None and effect_mask_path.exists():
        rain_mask = Image.open(effect_mask_path).convert("L").resize(
            (WIDTH, HEIGHT),
            Image.Resampling.LANCZOS,
        )
        print(f"Máscara manual de efeitos: {effect_mask_path}")
    rng = np.random.default_rng(seed)
    drops = build_rain_drops(rng)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if use_scene_effects:
        print(f"Efeitos de cena: {', '.join(scene_effects)}")
    if steam_enabled:
        if detection.steam_auto:
            print(f"Vapor detectado em ({detection.steam_x}, {detection.steam_y})")
        else:
            print(f"Vapor usando posição manual ({detection.steam_x}, {detection.steam_y})")
    else:
        print("Vapor desativado")
    if rain_enabled:
        if detection.rain_auto:
            print("Chuva restrita à região de janela detectada")
        else:
            print("Chuva visual ativa (forçada)")
    else:
        print("Chuva desativada: nenhuma janela na cena")

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
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            ENCODE_PRESET,
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

    steam_origin = (detection.steam_x, detection.steam_y)
    frame_total = int(round((output_seconds if output_seconds is not None else LOOP_SECONDS) * FPS))
    steam_decay = steam_enabled and full_duration is not None and full_duration > 0

    def rain_layer(frame_index: int) -> Image.Image:
        return render_rain(frame_index, drops, rain_mask)

    for frame_index in range(frame_total):
        if use_scene_effects:
            brightness = 1.0
            if (
                "fireplace_flicker" not in scene_effects
                and "candle_flicker" not in scene_effects
                and "desk_lamp_flicker" not in scene_effects
                and "desk_lamp_breathe" not in scene_effects
                and "monitor_glow" not in scene_effects
                and "keyboard_underglow" not in scene_effects
                and "rgb_breathe" not in scene_effects
                and "screen_bloom" not in scene_effects
                and "plant_sway" not in scene_effects
                and "desk_specular" not in scene_effects
            ):
                brightness = (
                    1.0
                    if (
                        "sunrise_glow" in scene_effects
                        or "birds" in scene_effects
                        or "foliage_shimmer" in scene_effects
                        or "dust_motes" in scene_effects
                        or "blinds_city_pulse" in scene_effects
                        or "city_haze" in scene_effects
                        or "mist_drift" in scene_effects
                        or "slow_zoom" in scene_effects
                    )
                    else light_flicker(frame_index)
                )
            frame_array = np.clip(base * brightness, 0, 255).astype(np.uint8)
            frame = apply_scene_effects(
                frame_array,
                frame_index,
                frame_total,
                scene_effects,
                seed,
                rain_mask,
                rain_layer if rain_enabled else None,
            )
            if "slow_zoom" in scene_effects:
                frame = apply_slow_zoom(frame.convert("RGB"), frame_index, frame_total).convert("RGBA")
            if steam_enabled:
                global_time = time_offset + frame_index / FPS
                if steam_decay:
                    current_scale = steam_scale_at_time(global_time, full_duration)
                    animation_frame = int(round(global_time * FPS))
                else:
                    current_scale = steam_scale
                    animation_frame = frame_index
                frame = Image.alpha_composite(
                    frame.convert("RGBA"),
                    render_steam(
                        steam_origin,
                        current_scale,
                        animation_frame,
                        color=steam_color,
                    ),
                )
        else:
            brightness = light_flicker(frame_index)
            frame_array = np.clip(base * brightness, 0, 255).astype(np.uint8)
            frame = Image.fromarray(frame_array, mode="RGB").convert("RGBA")
            if rain_enabled:
                frame = Image.alpha_composite(frame, rain_layer(frame_index))
            if steam_enabled:
                global_time = time_offset + frame_index / FPS
                if steam_decay:
                    current_scale = steam_scale_at_time(global_time, full_duration)
                    animation_frame = int(round(global_time * FPS))
                else:
                    current_scale = steam_scale
                    animation_frame = frame_index
                frame = Image.alpha_composite(
                    frame,
                    render_steam(
                        steam_origin,
                        current_scale,
                        animation_frame,
                        color=steam_color,
                    ),
                )
        ffmpeg.stdin.write(frame.convert("RGB").tobytes())

    ffmpeg.stdin.close()
    ffmpeg.wait()
    if ffmpeg.returncode != 0:
        raise RuntimeError("FFmpeg encoding failed")
    return detection


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera loop animado da cena")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steam-x", type=int, default=1010)
    parser.add_argument("--steam-y", type=int, default=800)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-rain", action="store_true")
    parser.add_argument("--no-steam", action="store_true")
    parser.add_argument("--no-auto-rain", action="store_true")
    parser.add_argument("--no-auto-steam", action="store_true")
    parser.add_argument("--steam-scale", type=float, default=1.0)
    parser.add_argument(
        "--steam-color",
        type=str,
        default=None,
        help="Cor RGB do vapor (ex: 200,148,110). Padrão: creme frio",
    )
    parser.add_argument(
        "--effects",
        type=str,
        default="",
        help="Efeitos de cena separados por vírgula (ex: rain,falling_leaves,sunrise_glow)",
    )
    parser.add_argument("--effect-mask", type=Path, default=None)
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="Duração do loop animado em segundos (padrão: LOOP_SECONDS)",
    )
    args = parser.parse_args()
    effect_list = [item.strip() for item in args.effects.split(",") if item.strip()]
    loop_seconds = float(args.seconds) if args.seconds is not None else float(LOOP_SECONDS)
    encode_loop(
        args.scene,
        args.output,
        args.steam_x,
        args.steam_y,
        args.seed,
        rain=not args.no_rain,
        steam=not args.no_steam,
        auto_rain=not args.no_auto_rain,
        auto_steam=not args.no_auto_steam,
        steam_scale=args.steam_scale,
        steam_color=parse_steam_color(args.steam_color),
        output_seconds=loop_seconds,
        effects=effect_list or None,
        effect_mask_path=args.effect_mask,
    )
    print(f"Animated loop saved: {args.output} ({loop_seconds:g}s @ {FPS}fps)")


if __name__ == "__main__":
    main()
