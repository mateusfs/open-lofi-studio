#!/usr/bin/env python3
"""Enfileira o próximo vídeo a partir dos catálogos de templates."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META_PATH = ROOT / "templates/production-meta.json"
AUDIO_PATH = ROOT / "templates/audio-config.json"
CALENDAR_PATH = ROOT / "docs/05-calendario-de-videos.md"


def number_sort_key(number: str) -> tuple[int, int, str]:
    upper = number.upper()
    if upper.startswith("S") and upper[1:].isdigit():
        return (2, int(upper[1:]), upper)
    if number.isdigit():
        return (1, int(number), "")
    return (1, 9999, number)


def parse_number(number: str) -> int | None:
    upper = number.upper()
    if upper.startswith("S") and upper[1:].isdigit():
        return 10_000 + int(upper[1:])
    if number.isdigit():
        return int(number)
    return None


def load_audio_catalog() -> dict[str, dict]:
    payload = json.loads(AUDIO_PATH.read_text(encoding="utf-8"))
    return {entry["productionId"]: entry for entry in payload.get("catalog", [])}


def load_meta_catalog() -> list[dict]:
    payload = json.loads(META_PATH.read_text(encoding="utf-8"))
    return payload.get("catalog", [])


def calendar_metadata() -> dict[str, dict[str, str]]:
    if not CALENDAR_PATH.exists():
        return {}
    metadata: dict[str, dict[str, str]] = {}
    for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 7:
            continue
        number = parts[0]
        if parse_number(number) is None:
            continue
        metadata[number] = {
            "priority": parts[-3],
            "targetDate": parts[-1],
            "visualHint": parts[-4],
        }
    return metadata


def track_slugs(audio_entry: dict) -> list[str]:
    return [Path(track).stem for track in audio_entry["tracks"]]


def build_brief(meta: dict, calendar_row: dict[str, str]) -> dict:
    mood = meta["mood"]
    hint = calendar_row.get("visualHint", mood)
    series = meta["series"]
    if series == "Rainy Night Coding":
        weather = "Chuva e trovão distante no vidro"
        if "storm" not in mood.lower() and "trovão" not in hint.lower():
            weather = "Chuva constante no vidro"
        return {
            "visual": f"Cenário: {hint}",
            "lighting": "Escuro com luz quente pontual no workspace",
            "weather": weather,
            "required": "Janelas com chuva, laptop com código, ambiente imersivo",
            "optional": "—",
        }
    if series == "Silent Library for Deep Work":
        return {
            "visual": hint,
            "lighting": "Lâmpadas verdes de banqueiro e luar frio nas janelas altas",
            "weather": "Noite seca e silenciosa no campus",
            "required": "Mesas de carvalho, lâmpadas verdes, estantes, laptop com código",
            "optional": "Livros empilhados, cadernos, poeira na luz",
        }
    if series == "Seasonal" and "summer" in mood.lower():
        return {
            "visual": hint,
            "lighting": "Sol da manhã generoso, brisa e flares quentes",
            "weather": "Dia claro de verão, céu azul, leve brisa",
            "required": "Escritório remoto ensolarado, laptop, vista aberta, plantas",
            "optional": "Limonada gelada, cortinas leves, pássaros ao fundo",
        }
    return {
        "visual": hint,
        "lighting": "Iluminação cinematográfica conforme mood",
        "weather": "Conforme série",
        "required": "Laptop com código, ambiente imersivo",
        "optional": "—",
    }


def build_queue_entry(meta: dict, audio: dict, calendar: dict[str, dict[str, str]]) -> dict:
    number = meta["number"]
    calendar_row = calendar.get(number, {})
    audio_payload: dict = {
        "tracks": track_slugs(audio),
        "rainVolume": audio.get("rainVolume", 0.055),
        "cafeVolume": audio.get("cafeVolume", 0.03),
        "whiteNoiseVolume": audio.get("whiteNoiseVolume", 0.0),
        "musicVolume": audio.get("musicVolume", 0.065),
        "noRain": audio.get("noRain", False),
        "noCafe": audio.get("noCafe", False),
        "noWhiteNoise": audio.get("noWhiteNoise", audio.get("whiteNoiseVolume", 0.0) <= 0),
    }
    if "whiteNoiseFile" in audio:
        audio_payload["whiteNoiseFile"] = audio["whiteNoiseFile"]
    if "ambience" in audio:
        audio_payload["ambience"] = audio["ambience"]
    entry: dict = {
        "number": number,
        "productionId": meta["productionId"],
        "series": meta["series"],
        "titleEn": meta["titleEn"],
        "durationSeconds": meta["durationSeconds"],
        "durationLabel": meta["durationLabel"],
        "mood": meta["mood"],
        "status": "planejado",
        "priority": calendar_row.get("priority", "P2"),
        "exportBasename": meta["exportBasename"],
        "audio": audio_payload,
        "animate": meta["animate"],
        "brief": build_brief(meta, calendar_row),
        "targetDate": calendar_row.get("targetDate", "—"),
    }
    scene_prompt = meta.get("scenePrompt", "").strip()
    if scene_prompt:
        entry["scenePrompt"] = scene_prompt
    return entry


def catalog_entries() -> list[dict]:
    audio_catalog = load_audio_catalog()
    calendar = calendar_metadata()
    entries: list[dict] = []
    for meta in load_meta_catalog():
        audio = audio_catalog.get(meta["productionId"])
        if not audio:
            continue
        entries.append(build_queue_entry(meta, audio, calendar))
    return sorted(entries, key=lambda entry: number_sort_key(entry["number"]))


def max_completed_number(videos: list[dict], is_complete: Callable[[dict], bool]) -> int:
    highest = 0
    for video in videos:
        if video.get("status") != "produzido":
            continue
        if not is_complete(video):
            continue
        parsed = parse_number(str(video["number"]))
        if parsed is not None:
            highest = max(highest, parsed)
    return highest


def max_completed_thresholds(
    videos: list[dict],
    is_complete: Callable[[dict], bool],
) -> tuple[int, int]:
    regular = 0
    seasonal = 0
    for video in videos:
        if video.get("status") != "produzido":
            continue
        if not is_complete(video):
            continue
        parsed = parse_number(str(video["number"]))
        if parsed is None:
            continue
        if parsed >= 10_000:
            seasonal = max(seasonal, parsed)
        else:
            regular = max(regular, parsed)
    return regular, seasonal


def pick_next_catalog_entry(
    videos: list[dict],
    is_complete: Callable[[dict], bool],
) -> dict | None:
    queued_ids = {video["productionId"] for video in videos}
    regular_threshold, seasonal_threshold = max_completed_thresholds(videos, is_complete)
    for entry in catalog_entries():
        parsed = parse_number(entry["number"])
        if parsed is not None:
            threshold = seasonal_threshold if parsed >= 10_000 else regular_threshold
            if parsed <= threshold:
                continue
        if entry["productionId"] in queued_ids:
            continue
        return entry
    return None
