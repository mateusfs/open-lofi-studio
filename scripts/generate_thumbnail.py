#!/usr/bin/env python3
"""Gera thumbnail com layout de marca Ambience Session (cena em tela cheia)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

WIDTH = 1280
HEIGHT = 720
BAR_HEIGHT = 120
SCENE_HEIGHT = HEIGHT - BAR_HEIGHT
MARGIN = 24

SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
SHORT_CAPTION_MAX_CHARS = 18

YOUTUBE_RED = "#FF0000"
YOUTUBE_RED_DARK = "#CC0000"
MAX_BADGE_LUMINANCE = 0.38
BRIGHT_SCENE_LUMINANCE = 0.42
DARK_SCENE_LUMINANCE = 0.28


def load_palette(brand_dir: Path) -> dict:
    with open(brand_dir / "palette.json", encoding="utf-8") as file:
        return json.load(file)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def color_luminance(rgb: tuple[int, int, int]) -> float:
    red, green, blue = (channel / 255 for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def palette_color(palette: dict, name: str) -> tuple[int, int, int]:
    return hex_to_rgb(palette["colors"][name]["hex"])


def badge_fill_color(series: str, palette: dict) -> tuple[int, int, int]:
    accent, _ = series_accent(series, palette)
    if color_luminance(accent) <= MAX_BADGE_LUMINANCE:
        return accent
    return palette_color(palette, "accentRed")


def series_accent(series: str, palette: dict) -> tuple[tuple[int, int, int], tuple[int, int, int] | None]:
    colors = palette["colors"]
    cream = colors["coffeeCream"]["hex"]
    rain = colors["rainBlue"]["hex"]
    green = colors["codeGreen"]["hex"]
    mapping: dict[str, tuple[str, str | None]] = {
        "Ambience Session": (cream, None),
        "Rainy Night Coding": (rain, None),
        "Cyberpunk Developer Room": (YOUTUBE_RED, "#00fff2"),
        "Space Programming Session": (green, None),
        "Cabin Programmer": (cream, "#d4a574"),
        "Dark Mode Workspace": (green, None),
        "AI Research Lab": (green, "#00b4d8"),
        "Linux Hacker Room": (green, None),
        "Late Night Debugging": (YOUTUBE_RED, None),
        "Silent Library for Deep Work": (cream, None),
        "Startup Office at Midnight": (rain, None),
        "Deep Work Sessions": (green, None),
        "Seasonal": (YOUTUBE_RED, None),
    }
    primary_hex, secondary_hex = mapping.get(series, (YOUTUBE_RED, None))
    primary = hex_to_rgb(primary_hex)
    secondary = hex_to_rgb(secondary_hex) if secondary_hex else None
    return primary, secondary


def get_font(
    size: int,
    bold: bool = False,
    monospace: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if monospace:
        candidates = [
            "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        ]
    elif bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def resolve_ambience_hook(series: str, mood: str) -> str | None:
    mood_lower = mood.lower()
    if "white noise" in mood_lower or "brown noise" in mood_lower:
        return "WHITE NOISE"
    if "fan hum" in mood_lower or "homelab" in mood_lower:
        return "FAN HUM"
    if series == "Linux Hacker Room":
        if "homelab" in mood_lower or "server" in mood_lower:
            return "HOMELAB HUM"
        return "TERMINAL FOCUS"
    if series == "Deep Work Sessions":
        return "DEEP FOCUS"
    if "rain" in mood_lower or series == "Rainy Night Coding":
        return "RAIN SOUNDS"
    if "snow" in mood_lower or "fireplace" in mood_lower:
        return "COZY SOUNDS"
    if series == "Space Programming Session":
        return "SPACE AMBIENCE"
    if series == "Lounge Coding Sessions":
        return "LOUNGE FOCUS"
    return None


def resolve_alternate_hook(series: str, mood: str, primary: str | None) -> str:
    candidates = [
        "DEEP FOCUS",
        "CODING AMBIENCE",
        "FOCUS SESSION",
        resolve_ambience_hook(series, mood) or "DEVELOPER FOCUS",
    ]
    for candidate in candidates:
        if candidate and candidate != primary:
            return candidate
    return "CODING AMBIENCE"


def sanitize_short_caption(caption: str) -> str:
    cleaned = caption.upper()
    for separator in ("—", "–", "-", "•", "|", "/", ":"):
        cleaned = cleaned.replace(separator, " ")
    cleaned = " ".join(cleaned.split())
    return cleaned


def resolve_short_caption(series: str, mood: str, ambience_hook: str | None = None) -> str:
    if ambience_hook and ambience_hook.strip():
        return sanitize_short_caption(ambience_hook)

    mood_lower = mood.lower()
    if "flow" in mood_lower or "pomodoro" in mood_lower or "immersion" in mood_lower:
        return "FLOW STATE"
    if "rain" in mood_lower or series == "Rainy Night Coding":
        return "RAIN SOUNDS"
    if "warm" in mood_lower or "cozy" in mood_lower or "cafe" in mood_lower:
        return "WARM FOCUS"
    if "neon" in mood_lower or "synth" in mood_lower or series == "Cyberpunk Developer Room":
        return "NEON NIGHT"
    if "orbit" in mood_lower or "space" in mood_lower or series == "Space Programming Session":
        return "DEEP SPACE"

    for separator in ("•", "—", "–", "|"):
        if separator in mood:
            tail = mood.split(separator)[-1].strip()
            looks_like_duration = any(
                token in tail.lower() for token in ("min", "hour", "hr", "cycle")
            )
            cleaned = sanitize_short_caption(tail)
            if 2 <= len(cleaned) <= SHORT_CAPTION_MAX_CHARS and not looks_like_duration:
                return cleaned
            break

    hook = resolve_ambience_hook(series, mood)
    if hook:
        return sanitize_short_caption(hook)
    return "DEEP FOCUS"


def focal_crop_bias(series: str, mood: str, variant: str = "a") -> float:
    mood_lower = mood.lower()
    if variant == "short":
        if "rain" in mood_lower or series == "Rainy Night Coding":
            return 0.38
        if "sunrise" in mood_lower or "morning" in mood_lower:
            return 0.42
        return 0.48
    if "rain" in mood_lower or series == "Rainy Night Coding":
        return 0.22
    if "sunrise" in mood_lower or "morning" in mood_lower:
        return 0.38
    return 0.32


def fit_scene(
    scene_path: Path,
    target_width: int,
    target_height: int,
    series: str = "",
    mood: str = "",
    variant: str = "a",
) -> Image.Image:
    image = Image.open(scene_path).convert("RGB")
    src_w, src_h = image.size
    target_ratio = target_width / target_height
    src_ratio = src_w / src_h
    bias = focal_crop_bias(series, mood, variant)
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        max_left = max(src_w - new_w, 0)
        left = int(max_left * bias)
        image = image.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        max_top = max(src_h - new_h, 0)
        top = int(max_top * bias)
        image = image.crop((0, top, src_w, top + new_h))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def scene_average_luminance(image: Image.Image) -> float:
    sample = image.resize((160, 90), Image.Resampling.BILINEAR).convert("L")
    flattened = sample.get_flattened_data() if hasattr(sample, "get_flattened_data") else sample.getdata()
    pixels = list(flattened)
    return sum(pixels) / (255 * len(pixels))


def enhance_scene(image: Image.Image) -> Image.Image:
    luminance = scene_average_luminance(image)
    if luminance > BRIGHT_SCENE_LUMINANCE:
        contrast, color, brightness = 1.2, 1.1, 0.76
    elif luminance < DARK_SCENE_LUMINANCE:
        contrast, color, brightness = 1.16, 1.18, 1.04
    else:
        contrast, color, brightness = 1.15, 1.14, 0.98
    boosted = ImageEnhance.Contrast(image).enhance(contrast)
    boosted = ImageEnhance.Color(boosted).enhance(color)
    boosted = ImageEnhance.Brightness(boosted).enhance(brightness)
    return boosted.filter(ImageFilter.UnsharpMask(radius=1.4, percent=110, threshold=2))


def apply_vignette(image: Image.Image, strength: float | None = None) -> Image.Image:
    if strength is None:
        luminance = scene_average_luminance(image)
        if luminance > BRIGHT_SCENE_LUMINANCE:
            strength = 0.72
        elif luminance < DARK_SCENE_LUMINANCE:
            strength = 0.42
        else:
            strength = 0.52
    width, height = image.size
    vignette = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(vignette)
    draw.ellipse(
        (-width * 0.12, -height * 0.18, width * 1.12, height * 1.22),
        fill=int(255 * strength),
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(42))
    dark = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    dark.putalpha(vignette)
    result = image.convert("RGBA")
    result.alpha_composite(dark)
    return result


def scene_fade_to_bar(scene: Image.Image) -> Image.Image:
    fade = Image.new("L", (scene.width, scene.height), 0)
    fade_draw = ImageDraw.Draw(fade)
    fade_top = int(scene.height * 0.58)
    for y in range(fade_top, scene.height):
        progress = (y - fade_top) / max(scene.height - fade_top, 1)
        fade_draw.line([(0, y), (scene.width, y)], fill=int(245 * progress**1.2))
    fade = fade.filter(ImageFilter.GaussianBlur(10))
    overlay = Image.new("RGBA", scene.size, (26, 26, 46, 255))
    overlay.putalpha(fade)
    scene.alpha_composite(overlay)
    return scene


def apply_top_shade(scene: Image.Image) -> Image.Image:
    if scene_average_luminance(scene.convert("RGB")) <= BRIGHT_SCENE_LUMINANCE:
        return scene
    shade = Image.new("L", (scene.width, scene.height), 0)
    shade_draw = ImageDraw.Draw(shade)
    shade_bottom = int(scene.height * 0.42)
    for y in range(shade_bottom):
        progress = 1 - (y / max(shade_bottom, 1))
        shade_draw.line([(0, y), (scene.width, y)], fill=int(150 * progress**1.1))
    shade = shade.filter(ImageFilter.GaussianBlur(12))
    overlay = Image.new("RGBA", scene.size, (0, 0, 0, 255))
    overlay.putalpha(shade)
    scene.alpha_composite(overlay)
    return scene


def draw_text_stroked(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    stroke_width: int = 3,
) -> None:
    draw = ImageDraw.Draw(canvas)
    stroke = (0, 0, 0)
    for offset_x in range(-stroke_width, stroke_width + 1):
        for offset_y in range(-stroke_width, stroke_width + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            draw.text(
                (position[0] + offset_x, position[1] + offset_y),
                text,
                font=font,
                fill=stroke,
            )
    draw.text(position, text, font=font, fill=fill)


def draw_glow_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    glow: tuple[int, int, int] | None,
) -> None:
    if glow:
        glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.text(position, text, font=font, fill=(*glow, 180))
        blurred = glow_layer.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(blurred)
    draw_text_stroked(canvas, position, text, font, fill, stroke_width=2)


def draw_ambience_hook(
    canvas: Image.Image,
    hook: str,
    accent: tuple[int, int, int],
    secondary: tuple[int, int, int] | None,
    white: tuple[int, int, int],
) -> None:
    label = hook.strip().upper()
    hook_font = get_font(26, bold=True)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), label, font=hook_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x = 22
    pad_y = 12
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2
    box_x = MARGIN
    box_y = MARGIN
    radius = 10
    text_x = box_x + (box_w - text_w) // 2 - bbox[0]
    text_y = box_y + (box_h - text_h) // 2 - bbox[1]

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (box_x + 2, box_y + 4, box_x + box_w + 2, box_y + box_h + 4),
        radius=radius,
        fill=(0, 0, 0, 180),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))

    if secondary:
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.rounded_rectangle(
            (box_x - 2, box_y - 2, box_x + box_w + 2, box_y + box_h + 2),
            radius=radius + 2,
            fill=(*secondary, 110),
        )
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))

    draw.rounded_rectangle(
        (box_x, box_y, box_x + box_w, box_y + box_h),
        radius=radius,
        fill=(26, 26, 46, 230),
        outline=(*accent, 255),
        width=2,
    )
    draw.text((text_x, text_y), label, font=hook_font, fill=white)


def draw_duration_badge(
    canvas: Image.Image,
    duration_label: str,
    badge_fill: tuple[int, int, int],
    secondary: tuple[int, int, int] | None,
    white: tuple[int, int, int],
) -> None:
    label = duration_label.strip().upper()
    badge_font = get_font(42 if canvas.width == SHORT_WIDTH else 34, bold=True)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), label, font=badge_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x = 30
    pad_y = 16
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2
    badge_x = canvas.width - badge_w - MARGIN
    badge_y = MARGIN
    radius = badge_h // 2
    text_x = badge_x + (badge_w - text_w) // 2 - bbox[0]
    text_y = badge_y + (badge_h - text_h) // 2 - bbox[1]

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (badge_x + 3, badge_y + 5, badge_x + badge_w + 3, badge_y + badge_h + 5),
        radius=radius,
        fill=(0, 0, 0, 170),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))

    if secondary:
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.rounded_rectangle(
            (badge_x - 3, badge_y - 3, badge_x + badge_w + 3, badge_y + badge_h + 3),
            radius=radius + 3,
            fill=(*secondary, 90),
        )
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(8)))

    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
        radius=radius,
        fill=(*badge_fill, 255),
        outline=(*secondary, 255) if secondary else None,
        width=2 if secondary else 0,
    )
    draw.text((text_x, text_y), label, font=badge_font, fill=white)


def draw_bottom_bar(
    canvas: Image.Image,
    series: str,
    mood: str,
    palette: dict,
    accent: tuple[int, int, int],
    secondary: tuple[int, int, int] | None,
    bar_height: int = BAR_HEIGHT,
) -> None:
    midnight = hex_to_rgb(palette["colors"]["midnight"]["hex"])
    cream = hex_to_rgb(palette["colors"]["coffeeCream"]["hex"])
    white = hex_to_rgb(palette["colors"]["white"]["hex"])
    bar_width = canvas.width

    bar = Image.new("RGBA", (bar_width, bar_height), (*midnight, 255))
    bar_draw = ImageDraw.Draw(bar)
    bar_draw.rectangle((0, 0, 5, bar_height), fill=(*accent, 255))
    if secondary:
        bar_draw.rectangle((5, 0, 8, bar_height), fill=(*secondary, 220))

    gradient = Image.new("L", (1, bar_height), 0)
    for y in range(bar_height):
        gradient.putpixel((0, y), int(90 * (1 - y / bar_height)))
    gradient = gradient.resize((bar_width, bar_height))
    fade = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 255))
    fade.putalpha(gradient)
    bar.alpha_composite(fade)

    series_font = get_font(44 if bar_width == SHORT_WIDTH else 40, bold=True)
    mood_font = get_font(28 if bar_width == SHORT_WIDTH else 24, bold=False)
    series_label = series.upper()
    max_chars = 28 if bar_width == SHORT_WIDTH else 34
    if len(series_label) > max_chars:
        series_label = series_label[: max_chars - 3] + "..."

    draw_glow_text(bar, (MARGIN + 8, 22), series_label, series_font, white, secondary)
    draw_text_stroked(bar, (MARGIN + 8, 78), mood, mood_font, cream, stroke_width=2)

    canvas.alpha_composite(bar, (0, canvas.height - bar_height))


def apply_short_bottom_shade(scene: Image.Image) -> Image.Image:
    shade = Image.new("L", (scene.width, scene.height), 0)
    shade_draw = ImageDraw.Draw(shade)
    shade_top = int(scene.height * 0.62)
    for y in range(shade_top, scene.height):
        progress = (y - shade_top) / max(scene.height - shade_top, 1)
        shade_draw.line([(0, y), (scene.width, y)], fill=int(210 * progress**1.15))
    shade = shade.filter(ImageFilter.GaussianBlur(18))
    overlay = Image.new("RGBA", scene.size, (0, 0, 0, 255))
    overlay.putalpha(shade)
    scene.alpha_composite(overlay)
    return scene


def draw_short_caption(
    canvas: Image.Image,
    caption: str,
    white: tuple[int, int, int],
    glow: tuple[int, int, int] | None,
) -> None:
    label = caption.strip().upper()
    font_size = 92 if len(label) <= 10 else 78 if len(label) <= 14 else 64
    font = get_font(font_size, bold=True)
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (canvas.width - text_w) // 2 - bbox[0]
    text_y = canvas.height - int(canvas.height * 0.16) - text_h // 2 - bbox[1]

    glow_color = glow or white
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.text((text_x, text_y), label, font=font, fill=(*glow_color, 200))
    canvas.alpha_composite(glow_layer.filter(ImageFilter.GaussianBlur(18)))
    draw_text_stroked(canvas, (text_x, text_y), label, font, white, stroke_width=4)


def generate_thumbnail(
    scene_path: Path,
    output: Path,
    series: str,
    mood: str,
    duration_label: str,
    palette: dict,
    ambience_hook: str | None = None,
    variant: str = "a",
    thumb_format: str = "landscape",
) -> None:
    accent, secondary = series_accent(series, palette)
    badge_fill = badge_fill_color(series, palette)
    white = palette_color(palette, "white")
    is_short = thumb_format == "short"

    if is_short:
        caption = resolve_short_caption(series, mood, ambience_hook)
        scene = fit_scene(
            scene_path,
            SHORT_WIDTH,
            SHORT_HEIGHT,
            series,
            mood,
            variant="short",
        )
        scene = enhance_scene(scene)
        scene = apply_vignette(scene)
        scene = apply_top_shade(scene.convert("RGBA"))
        scene = apply_short_bottom_shade(scene)
        draw_short_caption(scene, caption, white, secondary or accent)
        output.parent.mkdir(parents=True, exist_ok=True)
        scene.convert("RGB").save(output, format="PNG", optimize=True)
        return

    hook = ambience_hook or resolve_ambience_hook(series, mood)
    if variant == "b":
        hook = ambience_hook or resolve_alternate_hook(series, mood, hook)

    scene = fit_scene(scene_path, WIDTH, SCENE_HEIGHT, series, mood, variant=variant)
    scene = enhance_scene(scene)
    scene = apply_vignette(scene)
    scene = apply_top_shade(scene.convert("RGBA"))
    scene = scene_fade_to_bar(scene)

    if hook:
        draw_ambience_hook(scene, hook, accent, secondary, white)
    draw_duration_badge(scene, duration_label, badge_fill, secondary, white)

    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    canvas.alpha_composite(scene, (0, 0))
    draw_bottom_bar(canvas, series, mood, palette, accent, secondary, bar_height=BAR_HEIGHT)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera thumbnail Ambience Session")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", default="Ambience Session")
    parser.add_argument("--mood", default="Rainy Evening • Deep Focus")
    parser.add_argument("--duration", default="3 HOURS")
    parser.add_argument("--hook", default=None, help="Badge de ambience (ex: RAIN SOUNDS)")
    parser.add_argument("--variant", default="a", choices=["a", "b"])
    parser.add_argument(
        "--format",
        dest="thumb_format",
        default="landscape",
        choices=["landscape", "short"],
        help="landscape=16:9 YouTube longo; short=9:16 capa de Shorts",
    )
    parser.add_argument("--brand-dir", type=Path, default=Path("brand"))
    args = parser.parse_args()

    palette = load_palette(args.brand_dir)
    generate_thumbnail(
        args.scene,
        args.output,
        args.series,
        args.mood,
        args.duration,
        palette,
        ambience_hook=args.hook,
        variant=args.variant,
        thumb_format=args.thumb_format,
    )
    print(f"Thumbnail saved: {args.output}")


if __name__ == "__main__":
    main()
