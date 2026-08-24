#!/usr/bin/env python3
"""Gera e valida metadata YouTube a partir da fila."""

from __future__ import annotations

import json
import re
from pathlib import Path

MAX_TITLE_CHARS = 70
REQUIRED_TAG_COUNT = 15


def build_youtube_title(series: str, mood: str, duration_label: str) -> str:
    mood_clean = re.sub(r"\s*[•·]\s*", " ", mood).strip()
    mood_clean = re.sub(r"\s+", " ", mood_clean)
    duration_clean = duration_label.strip()
    if not duration_clean.upper().endswith("FOR DEVELOPERS"):
        if "for developers" not in duration_clean.lower():
            duration_part = f"{duration_clean} for Developers"
        else:
            duration_part = duration_clean
    else:
        duration_part = duration_clean
    title = f"{series} | {mood_clean} | {duration_part}"
    if len(title) <= MAX_TITLE_CHARS:
        return title
    short_mood = mood_clean.split()[0] if mood_clean else "Focus"
    compact = f"{series} | {short_mood} | {duration_part}"
    if len(compact) <= MAX_TITLE_CHARS:
        return compact
    return compact[: MAX_TITLE_CHARS - 1].rstrip() + "…"


def parse_tags(raw: str | list[str] | None, series: str, mood: str) -> list[str]:
    if isinstance(raw, list):
        tags = [str(tag).strip() for tag in raw if str(tag).strip()]
    elif isinstance(raw, str) and raw.strip():
        tags = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        tags = []
    defaults = [
        "coding ambience",
        "programming music",
        "developer focus",
        "deep work",
        "lofi coding",
        "focus music",
        "coding session",
        "work music",
        "study music for developers",
        series.lower(),
        mood.split("•")[0].strip().lower(),
        "chillhop",
        "ambient coding",
        "remote work",
        "software engineer focus",
    ]
    for tag in defaults:
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= REQUIRED_TAG_COUNT:
            break
    return tags[:REQUIRED_TAG_COUNT]


def chapter_lines(duration_seconds: int) -> list[str]:
    hours = max(1, duration_seconds // 3600)
    labels = ["Session Start", "Deep Focus", "Mid Flow", "Second Wind", "Final Stretch"]
    lines = ["0:00:00 Session Start"]
    for hour in range(1, hours):
        label = labels[min(hour, len(labels) - 1)]
        lines.append(f"{hour}:00:00 {label}")
    return lines


def build_description(video: dict, chapters: list[str]) -> str:
    mood = video.get("mood", "Deep Focus")
    duration_label = str(video.get("durationLabel", "3 HOURS")).lower()
    series = video.get("series", "Ambience Session")
    return (
        f"{mood}. A {duration_label} focus session for developers.\n\n"
        "🎧 What's inside:\n"
        "• Immersive coding ambience matched to the scene\n"
        "• Exclusive focus playlist (one track at a time)\n"
        "• Seamless long-session mix\n"
        "• Subtle animated workspace loop\n\n"
        "⏱ Chapters:\n"
        + "\n".join(chapters)
        + f"\n\n📺 More from {series}\n"
        "[PLAYLIST-SERIE]\n\n"
        "🎵 Developer Focus Sessions\n"
        "[PLAYLIST-MAE]\n\n"
        "Perfect for: developers, remote workers, deep work sessions\n\n"
        "🔔 Subscribe for new coding environments every week.\n\n"
        "#coding #ambience #deepwork #lofi #focus\n"
    )


def build_youtube_metadata(video: dict) -> dict:
    title = video.get("titleEn") or build_youtube_title(
        str(video.get("series", "Ambience Session")),
        str(video.get("mood", "Deep Focus")),
        str(video.get("durationLabel", "3 HOURS")),
    )
    if len(title) > MAX_TITLE_CHARS:
        title = build_youtube_title(
            str(video.get("series", "Ambience Session")),
            str(video.get("mood", "Deep Focus")),
            str(video.get("durationLabel", "3 HOURS")),
        )
    tags = parse_tags(
        video.get("youtubeTags"),
        str(video.get("series", "Ambience Session")),
        str(video.get("mood", "Deep Focus")),
    )
    chapters = chapter_lines(int(video.get("durationSeconds", 10800)))
    description = build_description(video, chapters)
    return {
        "title": title,
        "titleChars": len(title),
        "tags": tags,
        "tagCount": len(tags),
        "chapters": chapters,
        "description": description,
        "thumbnailPrimary": "source/thumbnail.png",
        "thumbnailAlternate": "source/thumbnail-b.png",
    }


def validate_youtube_metadata(metadata: dict) -> None:
    title = str(metadata.get("title", ""))
    tags = metadata.get("tags", [])
    if len(title) > MAX_TITLE_CHARS:
        raise ValueError(f"Título YouTube com {len(title)} chars (máx {MAX_TITLE_CHARS})")
    if not isinstance(tags, list) or len(tags) < REQUIRED_TAG_COUNT:
        raise ValueError(f"Tags YouTube insuficientes: precisa de {REQUIRED_TAG_COUNT}")


def write_youtube_metadata(production_dir: Path, video: dict) -> Path:
    metadata = build_youtube_metadata(video)
    validate_youtube_metadata(metadata)
    source = production_dir / "source"
    source.mkdir(parents=True, exist_ok=True)
    output = source / "youtube-metadata.json"
    output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
