#!/usr/bin/env python3
"""Gera catálogos de 100 itens em templates/audio-config.json e templates/production-meta.json."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_concepts import CONCEPTS, scene_prompt_for

ZIP_PATH = ROOT / "assets/audio/.cache/openlofi.zip"
REGISTRY_PATH = ROOT / "assets/audio/music-registry.json"
AUDIO_TEMPLATE_PATH = ROOT / "templates/audio-config.json"
META_TEMPLATE_PATH = ROOT / "templates/production-meta.json"
QUEUE_PATH = ROOT / "assets/production-queue.json"

TRACKS_PER_ITEM = 3


def slugify(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


def production_id_for(concept) -> str:
    return f"{concept.number}-{slugify(concept.series)[:24]}-{slugify(concept.title)}"


def load_all_tracks() -> list[str]:
    if not ZIP_PATH.exists():
        return []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        return sorted(
            {Path(name).stem for name in archive.namelist() if name.lower().endswith(".mp3")}
        )


def used_tracks() -> set[str]:
    if not REGISTRY_PATH.exists():
        return set()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    used: set[str] = set(registry.get("blockedSlugs", []))
    for entry in registry.get("productions", {}).values():
        used.update(entry.get("tracks", []))
    return used


def placeholder_tracks(production_id: str) -> list[str]:
    return [f"{production_id}-track-{index}" for index in range(1, TRACKS_PER_ITEM + 1)]


def assign_playlists(available: list[str]) -> dict[str, list[str]]:
    remaining = set(available)
    assignments: dict[str, list[str]] = {}

    for concept in CONCEPTS:
        production_id = production_id_for(concept)
        if len(remaining) < TRACKS_PER_ITEM:
            assignments[production_id] = placeholder_tracks(production_id)
            continue
        scored = sorted(
            remaining,
            key=lambda slug: (-sum(1 for kw in concept.keywords if kw in slug), slug),
        )
        picked: list[str] = []
        for slug in scored:
            if len(picked) == TRACKS_PER_ITEM:
                break
            score = sum(1 for kw in concept.keywords if kw in slug)
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


def build_audio_catalog(assignments: dict[str, list[str]]) -> dict:
    catalog = []
    for concept in CONCEPTS:
        production_id = production_id_for(concept)
        catalog.append(
            {
                "productionId": production_id,
                "tracks": [f"assets/audio/music/{slug}.mp3" for slug in assignments[production_id]],
                "musicVolume": 0.065,
                "rainVolume": concept.rain_volume,
                "cafeVolume": concept.cafe_volume,
                "noRain": concept.no_rain,
                "noCafe": concept.no_cafe,
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
            "musicVolume": 0.065,
            "rainVolume": 0.055,
            "cafeVolume": 0.03,
            "whiteNoiseVolume": 0.0,
            "noRain": False,
            "noCafe": False,
            "noWhiteNoise": True,
        },
        "rules": {
            "tracksPerVideo": "3-4",
            "uniqueAcrossVideos": True,
            "source": "open-lofi or other CC0 packs",
            "registry": "assets/audio/music-registry.json",
        },
        "catalog": catalog,
    }


def build_meta_catalog() -> dict:
    catalog = []
    for index, concept in enumerate(CONCEPTS):
        production_id = production_id_for(concept)
        duration_seconds = concept.hours * 3600
        title_en = f"{concept.series} | {concept.title} | {concept.hours} Hours for Developers"
        if concept.series == "Seasonal":
            title_en = f"{concept.title} | {concept.hours} Hours for Developers"
        catalog.append(
            {
                "number": concept.number,
                "productionId": production_id,
                "series": concept.series,
                "titleEn": title_en,
                "durationSeconds": duration_seconds,
                "durationLabel": f"{concept.hours} HOURS" if concept.hours > 1 else "1 HOUR",
                "mood": concept.mood,
                "exportBasename": f"{production_id}-{concept.hours}h",
                "animate": {
                    "mode": "ambient",
                    "loopSeconds": 24,
                    "noRain": concept.no_rain,
                    "steamDecay": False,
                    "steamX": 760 + (index * 37) % 340,
                    "steamY": 720 + (index * 23) % 90,
                    "seed": 122 + index,
                },
                "scenePrompt": scene_prompt_for(concept),
            }
        )
    return {
        "template": {
            "series": "Ambience Session",
            "mood": "Deep Focus",
            "durationLabel": "3 HOURS",
            "exportBasename": "demo-ambience-session-3h",
            "animate": {
                "mode": "ambient",
                "loopSeconds": 24,
                "noRain": False,
                "steamDecay": False,
                "seed": 42,
            },
        },
        "catalog": catalog,
    }


def write_catalogs() -> dict[str, list[str]]:
    all_tracks = load_all_tracks()
    blocked = used_tracks()
    available = [slug for slug in all_tracks if slug not in blocked]
    assignments = assign_playlists(available)

    audio_data = build_audio_catalog(assignments)
    meta_data = build_meta_catalog()

    AUDIO_TEMPLATE_PATH.write_text(
        json.dumps(audio_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    META_TEMPLATE_PATH.write_text(
        json.dumps(meta_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return assignments


def enqueue_catalog() -> int:
    from queue_catalog import catalog_entries

    if QUEUE_PATH.exists():
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    else:
        data = {"version": 1, "videos": []}
    existing = {video["productionId"] for video in data.get("videos", [])}
    added = 0
    for entry in catalog_entries():
        if entry["productionId"] in existing:
            continue
        data.setdefault("videos", []).append(entry)
        added += 1
    data["updatedAt"] = datetime.now(UTC).strftime("%Y-%m-%d")
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera catálogo de 100 produções ambient")
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="Adiciona itens novos do catálogo em assets/production-queue.json",
    )
    args = parser.parse_args()

    assignments = write_catalogs()
    unique_tracks = {slug for tracks in assignments.values() for slug in tracks}
    print(f"Conceitos: {len(CONCEPTS)}")
    print(f"Faixas no catálogo: {len(unique_tracks)}")
    print(f"Escritos: {AUDIO_TEMPLATE_PATH.name}, {META_TEMPLATE_PATH.name}")
    if args.enqueue:
        added = enqueue_catalog()
        print(f"Enfileirados: {added}")


if __name__ == "__main__":
    main()
