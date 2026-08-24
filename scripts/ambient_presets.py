#!/usr/bin/env python3
"""Presets de efeitos ambientais por series/mood (câmera fixa, micro-animação)."""

from __future__ import annotations

BASE_EFFECTS: tuple[str, ...] = ("monitor_glow", "desk_lamp_breathe", "dust_motes")

FORBIDDEN_EFFECTS: frozenset[str] = frozenset({"slow_zoom"})


def _mood_series_text(series: str, mood: str) -> str:
    return f"{series} {mood}".lower()


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen or item in FORBIDDEN_EFFECTS:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _build_preset_effects(series: str, mood: str) -> list[str]:
    text = _mood_series_text(series, mood)
    effects: list[str] = list(BASE_EFFECTS)

    if _has_any(text, ("rain",)) or series == "Rainy Night Coding":
        effects.extend(["rain", "city_haze"])

    if _has_any(text, ("snow", "fireplace", "winter", "cozy")):
        effects.extend(["snow", "fireplace_flicker"])

    if _has_any(text, ("morning", "sunrise")):
        effects.extend(["sunrise_glow", "foliage_shimmer", "birds"])

    if _has_any(text, ("homelab", "server", "neon", "synth", "rgb")):
        effects.extend(["keyboard_underglow", "rgb_breathe"])

    if _has_any(text, ("coffee", "warm", "mug", "cafe", "coffeehouse")):
        effects.append("steam")
        effects.append("pendant_glow")

    if _has_any(text, ("water", "lake", "beach")):
        effects.append("water_shimmer")

    if _has_any(
        text,
        ("city", "river", "bridge", "harbor", "canal", "night market", "skyline", "ribeira"),
    ):
        effects.append("city_twinkles")

    if series == "Space Programming Session" or _has_any(text, ("space", "orbital")):
        effects.append("screen_bloom")

    return _dedupe_preserve_order(effects)


def _apply_animate_flags(effects: list[str], animate: dict) -> list[str]:
    filtered = list(effects)
    if animate.get("noRain", False):
        filtered = [effect for effect in filtered if effect != "rain"]
    if animate.get("noSteam", False):
        filtered = [effect for effect in filtered if effect != "steam"]
    return _dedupe_preserve_order(filtered)


def resolve_ambient_effects(series: str, mood: str, animate: dict) -> list[str]:
    explicit = animate.get("effects")
    if isinstance(explicit, list) and explicit:
        raw = [str(item).strip() for item in explicit if str(item).strip()]
        return _apply_animate_flags(_dedupe_preserve_order(raw), animate)

    preset = _build_preset_effects(series, mood)
    return _apply_animate_flags(preset, animate)


def default_ambient_loop_seconds(animate: dict) -> int:
    loop_seconds = animate.get("loopSeconds")
    if loop_seconds is not None:
        return int(loop_seconds)
    return 24
