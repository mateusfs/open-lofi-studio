#!/usr/bin/env python3
"""Gera catálogos de 50 itens em templates/audio-config.json e templates/production-meta.json."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT / "assets/audio/.cache/openlofi.zip"
REGISTRY_PATH = ROOT / "assets/audio/music-registry.json"
AUDIO_TEMPLATE_PATH = ROOT / "templates/audio-config.json"
META_TEMPLATE_PATH = ROOT / "templates/production-meta.json"

TRACKS_PER_ITEM = 3

CONCEPTS = [
    ("007", "Ambience Session", "Lisbon Tram", 8, "Lisbon Tram • Warm Focus", 0.06, 0.08, False, False, False, ["cafe", "amber", "golden", "sidewalk", "afternoon"]),
    ("008", "Ambience Session", "Amsterdam Canal", 8, "Amsterdam Canal • Rainy Focus", 0.09, 0.07, False, False, False, ["watercolors", "window-seat", "teacup"]),
    ("009", "Ambience Session", "Kyoto Garden", 6, "Kyoto Garden • Zen Focus", 0.05, 0.05, False, False, False, ["bamboo", "temple", "petals", "blossoms"]),
    ("012", "Rainy Night Coding", "Berlin Loft", 6, "Berlin Loft • Storm Focus", 0.12, 0.0, False, True, False, ["storm", "thunder", "empty-street"]),
    ("013", "Rainy Night Coding", "London Pub", 6, "London Pub • Rain Focus", 0.10, 0.08, False, False, False, ["last-call", "half-empty", "hoodie"]),
    ("014", "Rainy Night Coding", "NYC Fire Escape", 8, "NYC Fire Escape • Night Rain", 0.10, 0.04, False, False, False, ["sidewalk-puddles", "streetlights", "headlights"]),
    ("015", "Rainy Night Coding", "Lisbon Attic", 6, "Lisbon Attic • Quiet Rain", 0.09, 0.03, False, False, False, ["curtains", "envelope", "amber-windowpane"]),
    ("016", "Rainy Night Coding", "Seoul Han River", 8, "Seoul Han River • Rain Focus", 0.14, 0.0, False, True, False, ["rain", "platform-after-rain", "hoodie", "petals-after-rain"]),
    ("017", "Deep Work Sessions", "White Noise Focus", 8, "White Noise • Pure Focus", 0.0, 0.0, True, True, True, ["quiet", "hiss", "lungs", "credits"]),
    ("020", "Cyberpunk Developer Room", "Neon Rain", 4, "Neon Rain • Cyber Focus", 0.11, 0.0, False, True, False, ["neon", "electric"]),
    ("021", "Cyberpunk Developer Room", "Blade Runner Vibes", 8, "Blade Runner Vibes • Night Haze", 0.10, 0.0, False, True, False, ["high-rise", "haze", "blinds", "velvet-cigarette"]),
    ("022", "Cyberpunk Developer Room", "Underground Hacker Den", 6, "Hacker Den • Deep Underground", 0.0, 0.0, True, True, True, ["pixel", "vhs", "cassette-basement", "screen"]),
    ("023", "Cyberpunk Developer Room", "Shinjuku Balcony", 8, "Shinjuku Balcony • Neon Night", 0.10, 0.03, False, False, False, ["lantern", "skyline"]),
    ("024", "Cyberpunk Developer Room", "Rooftop Antenna", 6, "Rooftop Antenna • Static Night", 0.08, 0.0, False, True, False, ["antenna", "rooftop-static"]),
    ("025", "Cyberpunk Developer Room", "Data Market", 8, "Data Market • Neon Bazaar", 0.09, 0.05, False, False, False, ["diner", "mirrorball", "jukebox"]),
    ("030", "Space Programming Session", "Earth View", 6, "Earth View • Orbital Focus", 0.0, 0.0, True, True, True, ["orbiting", "satellite", "constellations"]),
    ("031", "Space Programming Session", "Mars Colony", 8, "Mars Colony • Red Silence", 0.0, 0.0, True, True, True, ["dunes", "red-earth", "starlight"]),
    ("032", "Space Programming Session", "Deep Orbit", 10, "Deep Orbit • Cosmic Drift", 0.0, 0.0, True, True, True, ["deep-space", "elevator-to-the-moon", "aurora"]),
    ("033", "Space Programming Session", "Star Observatory", 10, "Star Observatory • Night Focus", 0.0, 0.0, True, True, True, ["floating", "soft-gold", "star", "observatory", "night"]),
    ("034", "Space Programming Session", "Lunar Base", 8, "Lunar Base • Quiet Moon", 0.0, 0.0, True, True, True, ["moonlit", "moon-through", "polar"]),
    ("040", "AI Research Lab", "Server Hum", 8, "Server Hum • Blue Light", 0.0, 0.0, True, True, True, ["hour-between-clicks", "glasshouse", "static"]),
    ("041", "AI Research Lab", "Neural Network Night", 6, "Neural Night • Data Flow", 0.0, 0.0, True, True, True, ["3-am", "green-after", "echoes"]),
    ("042", "AI Research Lab", "Quantum Lab", 8, "Quantum Lab • Superposition", 0.0, 0.0, True, True, True, ["stained-glass", "porcelain", "underwater"]),
    ("050", "Cabin Programmer", "Fireplace Snow", 10, "Fireplace Snow • Warm Cabin", 0.03, 0.0, False, True, False, ["fireplace", "snow", "winter"]),
    ("051", "Cabin Programmer", "Mountain Sunrise", 6, "Mountain Sunrise • First Light", 0.0, 0.0, True, True, True, ["mountain", "ridge", "fieldnotes", "mist-over"]),
    ("052", "Cabin Programmer", "Scandinavian Minimal", 10, "Scandinavian Cabin • Hygge Focus", 0.03, 0.0, False, True, False, ["candle-wax", "candlelit", "linen"]),
    ("053", "Cabin Programmer", "Lakeside Autumn", 8, "Lakeside Autumn • Falling Leaves", 0.06, 0.0, False, True, False, ["fallen-leaves", "autumn", "harbor"]),
    ("060", "Late Night Debugging", "Single Monitor", 3, "Single Monitor • Dark Room", 0.0, 0.0, True, True, True, ["sink-light", "midnight-notes", "ashes"]),
    ("061", "Late Night Debugging", "Stack Overflow Rabbit Hole", 4, "Rabbit Hole • Cold Coffee", 0.0, 0.0, True, True, True, ["midnight-on-my-mind", "last-train", "headlights"]),
    ("062", "Late Night Debugging", "Production Incident 2AM", 3, "Prod Incident • Adrenaline Calm", 0.05, 0.0, False, True, False, ["smoke", "embers", "street-static"]),
    ("070", "Dark Mode Workspace", "Dual Monitor", 8, "Dual Monitor • RGB Glow", 0.0, 0.0, True, True, True, ["midnight-window", "almost-floating", "soft-weightless"]),
    ("071", "Dark Mode Workspace", "Ultrawide Setup", 6, "Ultrawide • Minimal Focus", 0.0, 0.0, True, True, True, ["quiet-credits", "end-scene", "overpass"]),
    ("072", "Dark Mode Workspace", "Standing Desk", 6, "Standing Desk • Steady Flow", 0.0, 0.0, True, True, True, ["candlelit-at-70", "honey", "heartbeat"]),
    ("073", "Dark Mode Workspace", "RGB Off Minimal", 6, "RGB Off • Pure Dark", 0.0, 0.0, True, True, True, ["quiet-lungs", "hiss", "drifting"]),
    ("080", "Silent Library for Deep Work", "Ancient Books", 4, "Ancient Books • Timeless Quiet", 0.0, 0.0, True, True, True, ["hardcovers", "dog-eared", "cathedral"]),
    ("081", "Silent Library for Deep Work", "University Night", 6, "University Night • Green Lamps", 0.0, 0.0, True, True, True, ["stacks-of-quiet-books", "graphite-in", "sheet-music"]),
    ("082", "Silent Library for Deep Work", "Rooftop Reading Room", 4, "Rooftop Reading • Golden Hour", 0.0, 0.03, True, False, True, ["polaroids", "old-photos", "shoebox"]),
    ("090", "Startup Office at Midnight", "Empty Open Space", 6, "Open Space • After Hours", 0.0, 0.04, True, False, True, ["table-talk", "kitchen-after", "rearview"]),
    ("091", "Startup Office at Midnight", "Whiteboard Ideas", 4, "Whiteboard • Post-it Storm", 0.0, 0.05, True, False, True, ["penciled", "notes-on-the-floor", "envelope"]),
    ("092", "Startup Office at Midnight", "Garage Nights", 6, "Garage Nights • Founder Mode", 0.0, 0.0, True, True, True, ["basement-groove", "cassette", "motel"]),
    ("100", "Linux Hacker Room", "Terminal Green", 4, "Terminal Green • CRT Glow", 0.04, 0.0, False, True, False, ["terminal-rain", "vhs", "pixel"]),
    ("101", "Linux Hacker Room", "Arch Rice", 6, "Arch Rice • Tiling Zen", 0.0, 0.0, True, True, True, ["morning-keys", "dust-on-the-needle", "record-player"]),
    ("102", "Linux Hacker Room", "Homelab Server Closet", 4, "Homelab • Fan Hum", 0.0, 0.0, True, True, True, ["antenna", "blue-below", "high-rise"]),
    ("110", "Deep Work Sessions", "Pomodoro Flow", 2, "Pomodoro • 25min Cycles", 0.0, 0.04, True, False, True, ["sunrise-stretch", "mat-and-morning", "exhale"]),
    ("111", "Deep Work Sessions", "Flow State", 8, "Flow State • Total Immersion", 0.0, 0.0, True, True, True, ["drifting-through", "blue-below", "underwater"]),
    ("112", "Deep Work Sessions", "Ocean Window", 8, "Ocean Window • Tide Focus", 0.0, 0.0, True, True, True, ["tide", "sea-glass", "harbor"]),
    ("113", "Deep Work Sessions", "Zen Garden", 4, "Zen Garden • Still Mind", 0.0, 0.0, True, True, True, ["temple", "moss", "moon-through"]),
    ("s01", "Seasonal", "Black Friday Coding Marathon", 10, "Black Friday • Marathon Mode", 0.0, 0.0, True, True, True, ["groove", "jukebox", "radio", "bounce"]),
    ("s02", "Seasonal", "New Year Deep Work Session", 8, "New Year • Fresh Start", 0.0, 0.0, True, True, True, ["bells", "polar", "first-light"]),
    ("s03", "Seasonal", "Exam Season Focus", 6, "Exam Season • Steady Study", 0.0, 0.05, True, False, True, ["stacks-of-quiet-hours", "curtains", "morning-in-the-hiss"]),
    ("s04", "Seasonal", "Summer Remote Work Vibes", 8, "Summer Remote • Breeze Mode", 0.0, 0.06, True, False, True, ["breezy", "hammock", "lemonade", "palm", "summer"]),
    ("s05", "Seasonal", "Halloween Late Night Code", 6, "Halloween • Spooky Focus", 0.07, 0.0, False, True, False, ["ghosts", "velvet-candle", "cathedral-hiss"]),
]


def slugify(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


def load_all_tracks() -> list[str]:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        return sorted(
            {Path(name).stem for name in archive.namelist() if name.lower().endswith(".mp3")}
        )


def used_tracks() -> set[str]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    used: set[str] = set(registry.get("blockedSlugs", []))
    for entry in registry.get("productions", {}).values():
        used.update(entry.get("tracks", []))
    return used


def assign_playlists(available: list[str]) -> dict[str, list[str]]:
    remaining = set(available)
    assignments: dict[str, list[str]] = {}

    for concept in CONCEPTS:
        number, series, title, *_rest = concept
        keywords = concept[10]
        production_id = f"{number}-{slugify(series)[:24]}-{slugify(title)}"
        scored = sorted(
            remaining,
            key=lambda slug: (-sum(1 for kw in keywords if kw in slug), slug),
        )
        picked: list[str] = []
        for slug in scored:
            if len(picked) == TRACKS_PER_ITEM:
                break
            score = sum(1 for kw in keywords if kw in slug)
            if score > 0:
                picked.append(slug)
        for slug in sorted(remaining):
            if len(picked) == TRACKS_PER_ITEM:
                break
            if slug not in picked:
                picked.append(slug)
        remaining.difference_update(picked)
        assignments[production_id] = picked

    return assignments


def production_id_for(concept: tuple) -> str:
    number, series, title = concept[0], concept[1], concept[2]
    return f"{number}-{slugify(series)[:24]}-{slugify(title)}"


def build_audio_catalog(assignments: dict[str, list[str]]) -> dict:
    catalog = []
    for concept in CONCEPTS:
        number, series, title, hours, mood, rain, cafe, no_rain, no_cafe, _no_ambience, _kw = concept
        production_id = production_id_for(concept)
        catalog.append(
            {
                "productionId": production_id,
                "tracks": [f"assets/audio/music/{slug}.mp3" for slug in assignments[production_id]],
                "rainVolume": rain,
                "cafeVolume": cafe,
                "noRain": no_rain,
                "noCafe": no_cafe,
            }
        )
    return {
        "template": {
            "productionId": "XXX-slug-da-producao",
            "tracks": [
                "assets/audio/music/track-1-slug.mp3",
                "assets/audio/music/track-2-slug.mp3",
                "assets/audio/music/track-3-slug.mp3",
            ],
            "rainVolume": 0.1,
            "cafeVolume": 0.07,
            "noRain": False,
            "noCafe": False,
        },
        "rules": {
            "tracksPerVideo": "3-4",
            "uniqueAcrossVideos": True,
            "source": "open-lofi (CC0)",
            "registry": "assets/audio/music-registry.json",
        },
        "catalog": catalog,
    }


def build_meta_catalog() -> dict:
    catalog = []
    for index, concept in enumerate(CONCEPTS):
        number, series, title, hours, mood, _rain, _cafe, no_rain, _no_cafe, _na, _kw = concept
        production_id = production_id_for(concept)
        duration_seconds = hours * 3600
        title_en = f"{series} | {title} | {hours} Hours for Developers"
        if series == "Seasonal":
            title_en = f"{title} | {hours} Hours for Developers"
        catalog.append(
            {
                "number": number.upper(),
                "productionId": production_id,
                "series": series,
                "titleEn": title_en,
                "durationSeconds": duration_seconds,
                "durationLabel": f"{hours} HOURS" if hours > 1 else "1 HOUR",
                "mood": mood,
                "exportBasename": f"{production_id}-{hours}h",
                "animate": {
                    "noRain": no_rain,
                    "steamX": 760 + (index * 37) % 340,
                    "steamY": 720 + (index * 23) % 90,
                    "seed": 100 + index,
                },
            }
        )
    return {
        "template": {
            "series": "Nome da Série",
            "mood": "Mood • Foco",
            "durationLabel": "8 HOURS",
            "exportBasename": "XXX-slug-8h",
            "animate": {"noRain": False, "steamX": 960, "steamY": 790, "seed": 42},
        },
        "catalog": catalog,
    }


def main() -> None:
    all_tracks = load_all_tracks()
    blocked = used_tracks()
    available = [slug for slug in all_tracks if slug not in blocked]

    needed = len(CONCEPTS) * TRACKS_PER_ITEM
    if len(available) < needed:
        raise SystemExit(
            f"Faixas insuficientes: {len(available)} disponíveis, {needed} necessárias"
        )

    assignments = assign_playlists(available)

    flat = [slug for tracks in assignments.values() for slug in tracks]
    assert len(flat) == len(set(flat)), "Faixa duplicada entre playlists"
    assert not set(flat) & blocked, "Faixa bloqueada usada"

    audio_data = build_audio_catalog(assignments)
    meta_data = build_meta_catalog()

    AUDIO_TEMPLATE_PATH.write_text(
        json.dumps(audio_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    META_TEMPLATE_PATH.write_text(
        json.dumps(meta_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Conceitos: {len(CONCEPTS)}")
    print(f"Faixas alocadas: {len(flat)} únicas de {len(available)} disponíveis")
    print(f"Sobrando no pool: {len(available) - len(flat)}")
    print(f"Escritos: {AUDIO_TEMPLATE_PATH.name}, {META_TEMPLATE_PATH.name}")


if __name__ == "__main__":
    main()
