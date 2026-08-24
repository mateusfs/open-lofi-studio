from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH = 1920
HEIGHT = 1080
WINDOW_Y_MAX_RATIO = 0.65


def _window_mask_from_base(base: np.ndarray) -> Image.Image:
    from animate_scene import detect_window_mask

    mask, _, _ = detect_window_mask(base)
    return mask


def _mask_bounds(mask: Image.Image) -> tuple[int, int, int, int]:
    arr = np.array(mask.convert("L"))
    ys, xs = np.where(arr > 32)
    if xs.size == 0:
        return 0, 0, WIDTH - 1, int(HEIGHT * WINDOW_Y_MAX_RATIO)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _apply_window_mask(overlay: Image.Image, mask: Image.Image | None) -> Image.Image:
    if mask is None:
        return overlay
    rgba = overlay.convert("RGBA")
    alpha = np.asarray(rgba.getchannel("A"), dtype=np.float32)
    window = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    combined = np.clip(alpha * window, 0, 255).astype(np.uint8)
    out = rgba.copy()
    out.putalpha(Image.fromarray(combined, mode="L"))
    return out


def _resolve_window_mask(
    base_array: np.ndarray,
    rain_mask: Image.Image | None,
) -> Image.Image:
    if rain_mask is not None:
        return rain_mask
    return _window_mask_from_base(base_array)


def render_sunrise_glow(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    window_mask: Image.Image,
) -> Image.Image:
    progress = frame_index / max(total_frames - 1, 1)
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    warm_alpha = int(22 + 26 * (0.5 + 0.5 * np.sin(progress * 2 * np.pi)))
    pad_x = max(12, int((x1 - x0) * 0.04))
    draw.rectangle((x0 - pad_x, y0, x1 + pad_x, y1), fill=(255, 190, 110, warm_alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(22))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, window_mask),
    )


def render_mist_drift(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    seed: int,
    window_mask: Image.Image,
) -> Image.Image:
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    span_x = max(x1 - x0, 120)
    span_y = max(y1 - y0, 80)
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    local_x = np.linspace(0.0, 1.0, span_x + 1, dtype=np.float32)[np.newaxis, :]
    local_y = np.linspace(0.0, 1.0, span_y + 1, dtype=np.float32)[:, np.newaxis]
    alpha = np.zeros((span_y + 1, span_x + 1), dtype=np.float32)
    for band in range(4):
        center = 0.2 + band * 0.16
        thickness = 0.045 + band * 0.008
        vertical = np.exp(-((local_y - center) ** 2) / (2 * thickness**2))
        horizontal = 0.72 + 0.28 * np.sin(
            2 * np.pi * (local_x * (1.1 + band * 0.15)) + phase + seed * 0.01 + band
        )
        alpha += vertical * horizontal * (13 + band * 3)
    alpha_image = Image.fromarray(np.clip(alpha, 0, 42).astype(np.uint8), mode="L")
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(9))
    local_overlay = Image.new("RGBA", alpha_image.size, (238, 234, 226, 0))
    local_overlay.putalpha(alpha_image)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay.paste(local_overlay, (x0, y0), local_overlay)
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, window_mask),
    )


def render_candle_flicker(base_array: np.ndarray, frame_index: int) -> np.ndarray:
    center_x = int(WIDTH * 0.11)
    center_y = int(HEIGHT * 0.56)
    radius = 200
    phase = 2 * np.pi * frame_index / 36
    intensity = 0.32 + 0.22 * np.sin(phase) + 0.1 * np.sin(phase * 3.4 + 0.6)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt((xs - center_x) ** 2 + (ys - center_y) ** 2)
    falloff = np.clip(1.0 - dist / radius, 0.0, 1.0) ** 2.4
    result = base_array.astype(np.float32)
    glow = intensity * falloff
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 38, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 20, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 8, 0, 255)
    return result.astype(np.uint8)


def _monitor_glow_center(base_array: np.ndarray) -> tuple[int, int, int]:
    brightness = base_array.astype(np.float32).mean(axis=2)
    band = brightness[int(HEIGHT * 0.18) : int(HEIGHT * 0.62), int(WIDTH * 0.28) : int(WIDTH * 0.78)]
    if band.size == 0:
        return int(WIDTH * 0.52), int(HEIGHT * 0.38), 340
    flat_index = int(np.argmax(band))
    local_y, local_x = np.unravel_index(flat_index, band.shape)
    center_x = int(WIDTH * 0.28) + int(local_x)
    center_y = int(HEIGHT * 0.18) + int(local_y)
    peak = float(band.flat[flat_index])
    radius = 300 if peak >= 120 else 340
    return center_x, center_y, radius


def render_monitor_glow(base_array: np.ndarray, frame_index: int) -> np.ndarray:
    center_x, center_y, radius = _monitor_glow_center(base_array)
    phase = 2 * np.pi * frame_index / 96
    intensity = 0.28 + 0.16 * np.sin(phase) + 0.07 * np.sin(phase * 2.3 + 1.1)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt(((xs - center_x) * 0.92) ** 2 + ((ys - center_y) * 1.15) ** 2)
    falloff = np.clip(1.0 - dist / radius, 0.0, 1.0) ** 2.1
    result = base_array.astype(np.float32)
    glow = intensity * falloff
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 10, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 28, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 46, 0, 255)
    return result.astype(np.uint8)


def render_dust_motes(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    seed: int,
    base_array: np.ndarray,
) -> Image.Image:
    center_x, center_y, radius = _monitor_glow_center(base_array)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    for index in range(56):
        mote_rng = np.random.default_rng(seed + index * 29)
        angle = mote_rng.random() * 2 * np.pi
        orbit = radius * (0.12 + 0.78 * mote_rng.random())
        drift = 10 + mote_rng.random() * 28
        x = int(center_x + np.cos(angle + phase * (0.4 + mote_rng.random())) * orbit)
        y = int(
            center_y
            + np.sin(angle * 0.85 + phase * (0.55 + mote_rng.random() * 0.4)) * orbit * 0.72
            + np.sin(frame_index / 18 + index) * drift * 0.15
        )
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            continue
        size = 1 + int(mote_rng.integers(0, 3))
        alpha = 40 + int(mote_rng.integers(0, 90))
        warm = mote_rng.random() > 0.65
        color = (255, 236, 210, alpha) if warm else (190, 220, 255, alpha)
        draw.ellipse((x - size, y - size, x + size, y + size), fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.45))
    return Image.alpha_composite(base_frame.convert("RGBA"), overlay)


def _fireplace_center(base_array: np.ndarray) -> tuple[int, int, int]:
    rgb = base_array.astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    brightness = (red + green + blue) / 3.0
    warm = (
        (red >= green + 12)
        & (red >= blue + 28)
        & (brightness >= 55)
        & (brightness <= 220)
    )
    warm[:, : int(WIDTH * 0.55)] = False
    warm[: int(HEIGHT * 0.28), :] = False
    warm[int(HEIGHT * 0.88) :, :] = False
    if not warm.any():
        return int(WIDTH * 0.82), int(HEIGHT * 0.62), 260
    ys, xs = np.where(warm)
    weights = brightness[warm]
    center_x = int(np.average(xs, weights=weights))
    center_y = int(np.average(ys, weights=weights))
    return center_x, center_y, 260


def render_fireplace_flicker(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int = 480,
) -> np.ndarray:
    center_x, center_y, radius = _fireplace_center(base_array)
    x0 = max(0, int(WIDTH * 0.70))
    x1 = WIDTH
    y0 = max(0, int(HEIGHT * 0.38))
    y1 = min(HEIGHT, int(HEIGHT * 0.95))
    rgb = base_array[y0:y1, x0:x1].astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    brightness = (red + green + blue) / 3.0
    warm = (red >= green + 6) & (red >= blue + 14) & (brightness >= 28)
    core = warm & (brightness >= 70)
    local_h = y1 - y0
    local_w = x1 - x0
    ys = np.arange(y0, y1, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(x0, x1, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt((xs - center_x) ** 2 + ((ys - center_y) * 1.2) ** 2)
    falloff = np.clip(1.0 - dist / max(radius * 1.35, 1.0), 0.0, 1.0) ** 1.05
    weight = warm.astype(np.float32) * falloff
    core_w = core.astype(np.float32) * falloff

    rng = np.random.default_rng((frame_index * 9973 + 17) % (2**32 - 1))
    noise = rng.random((max(local_h // 8, 8), max(local_w // 8, 8)), dtype=np.float32)
    noise_f = (
        np.asarray(
            Image.fromarray((noise * 255).astype(np.uint8), mode="L").resize(
                (local_w, local_h),
                Image.Resampling.BILINEAR,
            ),
            dtype=np.float32,
        )
        / 255.0
    )
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    t = float(frame_index)
    tongues = (
        0.55
        + 0.45
        * np.sin(xs / 22.0 + t * 0.42)
        * np.sin(ys / 14.0 - t * 0.68 + phase)
        * np.sin(xs / 55.0 - t * 0.19)
    )
    flicker = 0.42 + 0.78 * noise_f * (0.45 + 0.55 * tongues)
    global_pulse = 0.78 + 0.22 * np.sin(phase * 3.0) + 0.08 * np.sin(phase * 7.0 + 1.1)
    factor = 0.55 + 0.75 * flicker * global_pulse
    result = rgb.copy()
    result[:, :, 0] = np.clip(rgb[:, :, 0] * (1.0 + (factor - 1.0) * weight), 0, 255)
    result[:, :, 1] = np.clip(rgb[:, :, 1] * (1.0 + (factor - 1.0) * weight * 0.9), 0, 255)
    result[:, :, 2] = np.clip(rgb[:, :, 2] * (1.0 + (factor - 1.0) * weight * 0.55), 0, 255)

    shift = np.clip((noise_f - 0.5) * 8.0 + np.sin(xs / 18.0 + t * 0.5) * 3.0, -6.0, 6.0)
    local_y = np.arange(local_h, dtype=np.int32)[:, np.newaxis]
    local_x = np.arange(local_w, dtype=np.int32)[np.newaxis, :]
    src_y = np.clip(local_y + (shift * core_w).astype(np.int32), 0, local_h - 1)
    warped = rgb[src_y, np.broadcast_to(local_x, (local_h, local_w))]
    mix = np.clip(core_w * 0.5, 0.0, 1.0)[:, :, np.newaxis]
    result = result * (1.0 - mix) + warped * mix

    hot = np.clip((flicker * global_pulse - 0.62) * 3.2, 0.0, 1.0) * core_w
    result[:, :, 0] = np.clip(result[:, :, 0] + hot * 70, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + hot * 28, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + hot * 6, 0, 255)

    spill_x = np.clip((xs - (center_x - 120)) / 420.0, 0.0, 1.0)
    spill_y = np.clip((ys - (center_y - 40)) / 360.0, 0.0, 1.0)
    desk = ((ys > int(HEIGHT * 0.62)) & (brightness < 120)).astype(np.float32)
    spill = desk * spill_x * (1.0 - spill_y * 0.35) * (0.55 + 0.45 * global_pulse)
    result[:, :, 0] = np.clip(result[:, :, 0] + spill * 18, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + spill * 8, 0, 255)

    out = base_array.copy()
    out[y0:y1, x0:x1] = np.clip(result, 0, 255).astype(np.uint8)
    return out


def _desk_lamp_center(base_array: np.ndarray) -> tuple[int, int, int]:
    rgb = base_array.astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    brightness = (red + green + blue) / 3.0
    warm = (red >= green + 8) & (red >= blue + 18) & (brightness >= 70) & (brightness <= 230)
    warm[:, : int(WIDTH * 0.45)] = False
    warm[: int(HEIGHT * 0.2), :] = False
    warm[int(HEIGHT * 0.82) :, :] = False
    if not warm.any():
        return int(WIDTH * 0.86), int(HEIGHT * 0.52), 240
    ys, xs = np.where(warm)
    weights = brightness[warm]
    center_x = int(np.average(xs, weights=weights))
    center_y = int(np.average(ys, weights=weights))
    return center_x, center_y, 240


def render_desk_lamp_breathe(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    center_x, center_y, radius = _desk_lamp_center(base_array)
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    intensity = 0.28 + 0.16 * np.sin(phase)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt((xs - center_x) ** 2 + ((ys - center_y) * 1.08) ** 2)
    falloff = np.clip(1.0 - dist / radius, 0.0, 1.0) ** 2.3
    monitor_guard = np.ones_like(falloff)
    monitor_guard[
        int(HEIGHT * 0.16) : int(HEIGHT * 0.58),
        int(WIDTH * 0.32) : int(WIDTH * 0.72),
    ] *= 0.03
    result = base_array.astype(np.float32)
    glow = intensity * falloff * monitor_guard
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 48, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 24, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 8, 0, 255)
    return result.astype(np.uint8)


def render_desk_lamp_flicker(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int = 288,
) -> np.ndarray:
    return render_desk_lamp_breathe(base_array, frame_index, total_frames)


def render_city_haze(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    seed: int,
    window_mask: Image.Image,
) -> Image.Image:
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    span_x = max(x1 - x0, 120)
    span_y = max(y1 - y0, 80)
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    wash = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash)
    wash_alpha = int(16 + 14 * (0.5 + 0.5 * np.sin(phase)))
    pad_x = max(8, int(span_x * 0.03))
    draw.rectangle((x0 - pad_x, y0, x1 + pad_x, y1), fill=(255, 178, 110, wash_alpha))
    wash = wash.filter(ImageFilter.GaussianBlur(20))
    rgba = Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(wash, window_mask),
    )

    local_x = np.linspace(0.0, 1.0, span_x + 1, dtype=np.float32)[np.newaxis, :]
    local_y = np.linspace(0.0, 1.0, span_y + 1, dtype=np.float32)[:, np.newaxis]
    alpha = np.zeros((span_y + 1, span_x + 1), dtype=np.float32)
    for band in range(4):
        center = 0.18 + band * 0.17
        thickness = 0.05 + band * 0.01
        vertical = np.exp(-((local_y - center) ** 2) / (2 * thickness**2))
        horizontal = 0.78 + 0.22 * np.sin(
            2 * np.pi * (local_x * (0.9 + band * 0.12)) + phase + seed * 0.01 + band * 0.7
        )
        alpha += vertical * horizontal * (12 + band * 3)
    alpha_image = Image.fromarray(np.clip(alpha, 0, 40).astype(np.uint8), mode="L")
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(12))
    local_overlay = Image.new("RGBA", alpha_image.size, (255, 200, 140, 0))
    local_overlay.putalpha(alpha_image)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay.paste(local_overlay, (x0, y0), local_overlay)
    return Image.alpha_composite(rgba, _apply_window_mask(overlay, window_mask))


def render_blinds_city_pulse(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    window_mask: Image.Image,
) -> Image.Image:
    return render_city_haze(base_frame, frame_index, total_frames, 17, window_mask)


def render_keyboard_underglow(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int = 288,
) -> np.ndarray:
    center_x = int(WIDTH * 0.50)
    center_y = int(HEIGHT * 0.78)
    radius_x = 340
    radius_y = 100
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    intensity = 0.28 + 0.16 * np.sin(phase)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt(((xs - center_x) / radius_x) ** 2 + ((ys - center_y) / radius_y) ** 2)
    falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 1.7
    falloff[: int(HEIGHT * 0.64), :] = 0.0
    result = base_array.astype(np.float32)
    glow = intensity * falloff
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 14, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 36, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 48, 0, 255)
    return result.astype(np.uint8)


def render_rgb_breathe(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    mix = 0.5 + 0.5 * np.sin(phase)
    left_strength = 0.34 + 0.18 * np.sin(phase)
    right_strength = 0.34 + 0.18 * np.sin(phase + 2.0)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]

    wall_y = np.exp(-((ys - HEIGHT * 0.30) / (HEIGHT * 0.16)) ** 2)
    wall_x_left = np.clip(1.0 - np.abs(xs - WIDTH * 0.28) / (WIDTH * 0.28), 0.0, 1.0) ** 1.4
    wall_x_right = np.clip(1.0 - np.abs(xs - WIDTH * 0.72) / (WIDTH * 0.28), 0.0, 1.0) ** 1.4
    wall = wall_y * (wall_x_left * (1.0 - 0.35 * mix) + wall_x_right * (0.65 + 0.35 * mix))
    wall[int(HEIGHT * 0.48) :, :] = 0.0

    under_left = np.clip(
        1.0 - np.sqrt(((xs - WIDTH * 0.30) / 380) ** 2 + ((ys - HEIGHT * 0.86) / 70) ** 2),
        0.0,
        1.0,
    ) ** 1.6
    under_right = np.clip(
        1.0 - np.sqrt(((xs - WIDTH * 0.70) / 360) ** 2 + ((ys - HEIGHT * 0.86) / 70) ** 2),
        0.0,
        1.0,
    ) ** 1.6
    under_left[: int(HEIGHT * 0.72), :] = 0.0
    under_right[: int(HEIGHT * 0.72), :] = 0.0

    result = base_array.astype(np.float32)
    cyan = left_strength * (wall * wall_x_left + under_left)
    magenta = right_strength * (wall * wall_x_right + under_right)
    result[:, :, 0] = np.clip(result[:, :, 0] + cyan * 16 + magenta * 58, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + cyan * 42 + magenta * 18, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + cyan * 62 + magenta * 48, 0, 255)
    return result.astype(np.uint8)


def render_screen_bloom(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    intensity = 0.3 + 0.16 * np.sin(phase)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    left_dist = np.sqrt(((xs - WIDTH * 0.36) / 280) ** 2 + ((ys - HEIGHT * 0.60) / 100) ** 2)
    right_dist = np.sqrt(((xs - WIDTH * 0.64) / 280) ** 2 + ((ys - HEIGHT * 0.60) / 100) ** 2)
    falloff = np.clip(1.0 - np.minimum(left_dist, right_dist), 0.0, 1.0) ** 2.0
    falloff[: int(HEIGHT * 0.40), :] *= 0.04
    falloff[int(HEIGHT * 0.78) :, :] *= 0.45
    result = base_array.astype(np.float32)
    glow = intensity * falloff
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 16, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 34, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 52, 0, 255)
    return result.astype(np.uint8)


def render_plant_sway(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    sway = 0.55 + 0.45 * np.sin(phase)
    rgb = base_array.astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    plant = (green > red + 12) & (green > blue + 8) & (green > 35)
    plant[:, int(WIDTH * 0.32) :] = False
    plant[int(HEIGHT * 0.72) :, :] = False
    if not plant.any():
        return base_array.astype(np.uint8)
    result = rgb.copy()
    lift = plant.astype(np.float32) * (4.5 + 5.5 * sway)
    result[:, :, 1] = np.clip(result[:, :, 1] + lift, 0, 255)
    result[:, :, 0] = np.clip(result[:, :, 0] + lift * 0.25, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + lift * 0.15, 0, 255)
    return result.astype(np.uint8)


def render_desk_specular(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
) -> np.ndarray:
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    center_x = WIDTH * (0.38 + 0.24 * (0.5 + 0.5 * np.sin(phase)))
    center_y = HEIGHT * 0.82
    intensity = 0.22 + 0.1 * np.sin(phase + 0.8)
    ys = np.arange(HEIGHT, dtype=np.float32)[:, np.newaxis]
    xs = np.arange(WIDTH, dtype=np.float32)[np.newaxis, :]
    dist = np.sqrt(((xs - center_x) / 420) ** 2 + ((ys - center_y) / 55) ** 2)
    falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2.4
    falloff[: int(HEIGHT * 0.74), :] = 0.0
    falloff[int(HEIGHT * 0.92) :, :] = 0.0
    result = base_array.astype(np.float32)
    glow = intensity * falloff
    result[:, :, 0] = np.clip(result[:, :, 0] + glow * 28, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + glow * 34, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] + glow * 42, 0, 255)
    return result.astype(np.uint8)


def render_falling_leaves(
    base_frame: Image.Image,
    frame_index: int,
    window_mask: Image.Image,
    seed: int,
) -> Image.Image:
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    span_x = max(x1 - x0, 80)
    span_y = max(y1 - y0, 80)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    colors = [(196, 110, 42, 160), (168, 72, 32, 140), (210, 145, 55, 150), (140, 88, 38, 130)]
    for index in range(32):
        leaf_rng = np.random.default_rng(seed + index * 17)
        base_x = x0 + int(leaf_rng.integers(0, span_x))
        speed = 1.8 + leaf_rng.random() * 2.2
        sway = 12 + leaf_rng.random() * 28
        travel = int((frame_index * speed + leaf_rng.integers(0, span_y)) % (span_y + 50))
        y = y0 + travel - 20
        if y > y1 + 10:
            continue
        x = int(base_x + np.sin(frame_index / 16 + index * 0.7) * sway)
        x = min(max(x, x0), x1)
        size = 4 + int(leaf_rng.integers(0, 5))
        color = colors[index % len(colors)]
        draw.ellipse((x - size, y - size // 2, x + size, y + size // 2), fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.6))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, window_mask),
    )


def render_snow_particles(
    base_frame: Image.Image,
    frame_index: int,
    window_mask: Image.Image,
    seed: int,
) -> Image.Image:
    hard_mask = window_mask.point(lambda value: 255 if value > 72 else 0)
    x0, y0, x1, y1 = _mask_bounds(hard_mask)
    span_x = max(x1 - x0, 80)
    span_y = max(y1 - y0, 80)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for index in range(130):
        flake_rng = np.random.default_rng(seed + index * 13)
        depth = flake_rng.random()
        base_x = x0 + int(flake_rng.integers(0, span_x))
        speed = 0.28 + depth * 1.05
        drift = 4 + depth * 12
        travel = int((frame_index * speed + flake_rng.integers(0, span_y)) % (span_y + 40))
        y = y0 + travel - 16
        x_shift = int(base_x + np.sin(frame_index / 34 + index * 0.7) * drift)
        if y < y0 - 10 or y > y1 + 10:
            continue
        if depth < 0.62:
            alpha = int(70 + depth * 50)
            draw.ellipse(
                (x_shift - 1, y - 1, x_shift + 1, y + 1),
                fill=(198, 214, 232, alpha),
            )
        else:
            alpha = int(90 + depth * 55)
            radius = 1 + int(depth > 0.85)
            draw.ellipse(
                (x_shift - radius, y - radius, x_shift + radius, y + radius),
                fill=(210, 222, 238, alpha),
            )
    soft = layer.filter(ImageFilter.GaussianBlur(1.8))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(soft, hard_mask),
    )


def _sky_flight_mask(base_frame: Image.Image, window_mask: Image.Image) -> Image.Image:
    rgb = np.asarray(base_frame.convert("RGB"), dtype=np.float32)
    win = np.asarray(window_mask.convert("L"), dtype=np.float32) / 255.0
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    brightness = (red + green + blue) / 3.0
    sky = (
        (win > 0.2)
        & (brightness >= 145)
        & (blue + 12 >= green)
        & (green < 210)
    )
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    sky_band = np.zeros_like(sky, dtype=bool)
    band_bottom = y0 + max(40, int((y1 - y0) * 0.42))
    sky_band[y0:band_bottom, x0 : x1 + 1] = True
    combined = sky & sky_band
    if combined.mean() < 0.004:
        combined = sky_band & (win > 0.25) & (brightness >= 120)
    alpha = (combined.astype(np.float32) * 255.0).astype(np.uint8)
    mask = Image.fromarray(alpha, mode="L")
    return mask.filter(ImageFilter.GaussianBlur(4))


def _foliage_mask(base_frame: Image.Image, window_mask: Image.Image) -> Image.Image:
    rgb = np.asarray(base_frame.convert("RGB"), dtype=np.float32)
    win = np.asarray(window_mask.convert("L"), dtype=np.float32) / 255.0
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    foliage = (win > 0.15) & (green > red + 8) & (green > blue + 4) & (green > 70)
    alpha = (foliage.astype(np.float32) * 255.0).astype(np.uint8)
    return Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(3))


def render_foliage_shimmer(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    window_mask: Image.Image,
    seed: int,
) -> Image.Image:
    foliage = _foliage_mask(base_frame, window_mask)
    x0, y0, x1, y1 = _mask_bounds(foliage)
    if x1 <= x0 or y1 <= y0:
        return base_frame.convert("RGBA")
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    span_x = max(x1 - x0, 80)
    span_y = max(y1 - y0, 80)
    for index in range(18):
        blob_rng = np.random.default_rng(seed + index * 19)
        cx = x0 + int(blob_rng.integers(0, span_x))
        cy = y0 + int(blob_rng.integers(0, span_y))
        radius = 18 + int(blob_rng.integers(0, 34))
        drift = np.sin(phase * (1.2 + index * 0.07) + index) * 10
        alpha = int(10 + 10 * (0.5 + 0.5 * np.sin(phase * 2 + index * 0.4)))
        warm = (255, 236, 190, alpha)
        cool = (150, 190, 130, max(6, alpha - 4))
        color = warm if index % 2 == 0 else cool
        draw.ellipse(
            (cx - radius + drift, cy - radius, cx + radius + drift, cy + radius),
            fill=color,
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(14))
    masked = _apply_window_mask(overlay, foliage)
    return Image.alpha_composite(base_frame.convert("RGBA"), masked)


def render_birds(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    window_mask: Image.Image,
    seed: int,
) -> Image.Image:
    flight_mask = _sky_flight_mask(base_frame, window_mask)
    x0, y0, x1, y1 = _mask_bounds(flight_mask)
    span_x = max(x1 - x0, 120)
    span_y = max(y1 - y0, 36)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    flock_count = 5
    for index in range(flock_count):
        bird_rng = np.random.default_rng(seed + index * 53)
        cycle = 140 + int(bird_rng.integers(0, 80))
        phase = int(bird_rng.integers(0, cycle))
        travel = (frame_index * (0.55 + bird_rng.random() * 0.35) + phase) % cycle
        visible_span = cycle * 0.72
        if travel > visible_span:
            continue
        progress = travel / max(visible_span, 1)
        direction = 1 if index % 2 == 0 else -1
        lane = 0.2 + bird_rng.random() * 0.5
        y = int(y0 + span_y * lane + np.sin(frame_index / 22 + index) * 2.5)
        if direction > 0:
            x = int(x0 - 16 + progress * (span_x + 32))
        else:
            x = int(x1 + 16 - progress * (span_x + 32))
        if x < x0 - 10 or x > x1 + 10 or y < y0 or y > y1:
            continue
        size = 2 + int(bird_rng.integers(0, 2))
        alpha = 55 + int(bird_rng.integers(0, 35))
        color = (48, 52, 58, alpha)
        trail = 5 + size * 2
        for step in range(3):
            trail_alpha = max(12, alpha - step * 18)
            trail_x = x - direction * step * (trail // 3)
            draw.ellipse(
                (
                    trail_x - size - step,
                    y - 1,
                    trail_x + size + step,
                    y + 1,
                ),
                fill=(48, 52, 58, trail_alpha),
            )
        draw.ellipse((x - size, y - 1, x + size + 1, y + 1), fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(2.4))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, flight_mask),
    )


def render_water_shimmer(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    window_mask: Image.Image,
) -> Image.Image:
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    phase = frame_index / max(total_frames, 1)
    stripe_count = 5
    for stripe in range(stripe_count):
        y = y0 + int((y1 - y0) * (0.25 + stripe * 0.14))
        offset = int(np.sin(phase * 2 * np.pi + stripe * 0.9) * 14)
        alpha = 12 + stripe * 2
        draw.line((x0 + offset, y, x1 + offset, y + 6), fill=(180, 210, 230, alpha), width=6)
    overlay = overlay.filter(ImageFilter.GaussianBlur(8))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, window_mask),
    )


def _find_pendant_lamps(base_array: np.ndarray) -> list[tuple[int, int, int]]:
    rgb = base_array.astype(np.float32)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    brightness = (red + green + blue) / 3.0
    warm = (
        (red >= green + 10)
        & (red >= blue + 24)
        & (brightness >= 120)
        & (brightness <= 245)
    )
    warm[:, int(WIDTH * 0.62) :] = False
    warm[int(HEIGHT * 0.58) :, :] = False
    warm[: int(HEIGHT * 0.05), :] = False
    labeled = np.zeros(warm.shape, dtype=np.int32)
    label = 0
    lamps: list[tuple[int, int, int]] = []
    height, width = warm.shape
    for y in range(height):
        for x in range(width):
            if not warm[y, x] or labeled[y, x]:
                continue
            label += 1
            stack = [(y, x)]
            pixels: list[tuple[int, int]] = []
            labeled[y, x] = label
            while stack:
                cy, cx = stack.pop()
                pixels.append((cx, cy))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and warm[ny, nx] and labeled[ny, nx] == 0:
                        labeled[ny, nx] = label
                        stack.append((ny, nx))
            if len(pixels) < 80 or len(pixels) > 8000:
                continue
            xs = [point[0] for point in pixels]
            ys = [point[1] for point in pixels]
            lamps.append((int(sum(xs) / len(xs)), int(sum(ys) / len(ys)), 72))
    return sorted(lamps, key=lambda item: item[0])[:3]


def render_pendant_glow(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    base_array: np.ndarray,
) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    phase = 2 * np.pi * frame_index / max(total_frames, 1)
    for lamp_index, (center_x, center_y, radius) in enumerate(_find_pendant_lamps(base_array)):
        pulse = 0.55 + 0.45 * np.sin(phase + lamp_index * 1.4)
        alpha = int(18 + 22 * pulse)
        draw.ellipse(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ),
            fill=(255, 196, 110, alpha),
        )
        cone_h = int(radius * 1.8)
        draw.polygon(
            (
                center_x - radius * 0.45,
                center_y + radius * 0.2,
                center_x + radius * 0.45,
                center_y + radius * 0.2,
                center_x + radius * 0.9,
                center_y + cone_h,
                center_x - radius * 0.9,
                center_y + cone_h,
            ),
            fill=(255, 170, 80, int(10 + 10 * pulse)),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(10))
    return Image.alpha_composite(base_frame.convert("RGBA"), overlay)


def render_city_twinkles(
    base_frame: Image.Image,
    frame_index: int,
    total_frames: int,
    seed: int,
    window_mask: Image.Image,
) -> Image.Image:
    x0, y0, x1, y1 = _mask_bounds(window_mask)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    phase = frame_index / max(total_frames, 1)
    rng = np.random.default_rng(seed + 401)
    for index in range(28):
        local_x = int(rng.integers(max(x0 + 8, 0), max(x1 - 8, x0 + 20)))
        local_y = int(rng.integers(max(y0 + 8, 0), max(y1 - 8, y0 + 20)))
        twinkle = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(phase * 2 * np.pi * 2.4 + index * 0.8))
        radius = 1 + (index % 3)
        alpha = int(40 + 90 * twinkle)
        color = (255, 220, 150, alpha) if index % 4 else (180, 210, 255, alpha)
        draw.ellipse(
            (local_x - radius, local_y - radius, local_x + radius, local_y + radius),
            fill=color,
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(
        base_frame.convert("RGBA"),
        _apply_window_mask(overlay, window_mask),
    )


def apply_scene_effects(
    base_array: np.ndarray,
    frame_index: int,
    total_frames: int,
    effects: list[str],
    seed: int,
    rain_mask: Image.Image | None,
    rain_renderer,
) -> Image.Image:
    window_mask = _resolve_window_mask(base_array, rain_mask)
    frame_array = base_array.copy()
    frame = Image.fromarray(frame_array, mode="RGB")

    if "candle_flicker" in effects:
        frame_array = render_candle_flicker(frame_array, frame_index)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "fireplace_flicker" in effects:
        frame_array = render_fireplace_flicker(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "desk_lamp_breathe" in effects or "desk_lamp_flicker" in effects:
        frame_array = render_desk_lamp_breathe(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "keyboard_underglow" in effects:
        frame_array = render_keyboard_underglow(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "rgb_breathe" in effects:
        frame_array = render_rgb_breathe(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "screen_bloom" in effects:
        frame_array = render_screen_bloom(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "plant_sway" in effects:
        frame_array = render_plant_sway(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "desk_specular" in effects:
        frame_array = render_desk_specular(frame_array, frame_index, total_frames)
        frame = Image.fromarray(frame_array, mode="RGB")
    if "monitor_glow" in effects:
        frame_array = render_monitor_glow(frame_array, frame_index)
        frame = Image.fromarray(frame_array, mode="RGB")

    rgba = frame.convert("RGBA")

    if "sunrise_glow" in effects:
        rgba = render_sunrise_glow(rgba, frame_index, total_frames, window_mask)
    if "mist_drift" in effects:
        rgba = render_mist_drift(rgba, frame_index, total_frames, seed, window_mask)
    if "city_haze" in effects or "blinds_city_pulse" in effects:
        rgba = render_city_haze(rgba, frame_index, total_frames, seed, window_mask)
    if "water_shimmer" in effects:
        rgba = render_water_shimmer(rgba, frame_index, total_frames, window_mask)
    if "rain" in effects and rain_renderer is not None:
        rgba = Image.alpha_composite(rgba, rain_renderer(frame_index))
    if "snow" in effects:
        rgba = render_snow_particles(rgba, frame_index, window_mask, seed + 7)
    if "falling_leaves" in effects:
        rgba = render_falling_leaves(rgba, frame_index, window_mask, seed + 11)
    if "foliage_shimmer" in effects:
        rgba = render_foliage_shimmer(rgba, frame_index, total_frames, window_mask, seed + 17)
    if "birds" in effects:
        rgba = render_birds(rgba, frame_index, total_frames, window_mask, seed + 23)
    if "dust_motes" in effects:
        rgba = render_dust_motes(rgba, frame_index, total_frames, seed + 31, frame_array)
    if "pendant_glow" in effects:
        rgba = render_pendant_glow(rgba, frame_index, total_frames, frame_array)
    if "city_twinkles" in effects:
        rgba = render_city_twinkles(rgba, frame_index, total_frames, seed + 37, window_mask)

    return rgba
