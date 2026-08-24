#!/usr/bin/env python3
"""Utilitários de prompt para cenas IA."""

from __future__ import annotations

import re
from pathlib import Path


def join_prompt_parts(*parts: str) -> str:
    ignored = {"—", "Conforme mood da série", "Conforme série"}
    cleaned = [part.strip() for part in parts if part and part.strip() not in ignored]
    return ", ".join(cleaned)


SCENE_SUFFIX = (
    "developer workspace with laptop showing colorful blurred code, "
    "photorealistic, no people, no readable text, "
    "ceramic mug without steam if a mug is present, "
    "no steam, no smoke, no vapor wisps, no fog plumes, "
    "shallow depth of field, 16:9 aspect ratio"
)

STEAM_STRIP_PATTERNS = (
    r"\bsteaming\b",
    r"\bwith\s+steam\b",
    r"\bwith\s+visible\s+wisps\s+of\s+steam\b",
    r"\bsoft\s+warm\s+steam\b",
    r"\bgentle\s+rising\s+steam\b",
    r"\brising\s+steam\b",
    r"\bwisps\s+of\s+steam\b",
    r"\bsteam\b",
)


def sanitize_scene_prompt(prompt: str) -> str:
    cleaned = prompt
    for pattern in STEAM_STRIP_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned).strip(" ,")
    lower = cleaned.lower()
    if "no steam" not in lower:
        cleaned = f"{cleaned}, no steam, no smoke, no vapor wisps"
    return cleaned


def build_scene_prompt(video: dict) -> str:
    custom = video.get("scenePrompt", "").strip()
    if custom:
        return sanitize_scene_prompt(custom)

    brief = video.get("brief", {})
    scene_details = join_prompt_parts(
        brief.get("visual", video["mood"]),
        brief.get("lighting", "cinematic lighting"),
        brief.get("weather", ""),
        brief.get("required", "laptop with code, immersive developer workspace"),
        brief.get("optional", ""),
    )
    return sanitize_scene_prompt(f"{scene_details}, {SCENE_SUFFIX}")


def extract_prompt_from_markdown(prompt_path: Path) -> str | None:
    if not prompt_path.exists():
        return None
    text = prompt_path.read_text(encoding="utf-8")
    match = re.search(
        r"## Midjourney / DALL·E\s+```\n([\s\S]*?)```",
        text,
    )
    if not match:
        return None
    prompt = " ".join(match.group(1).split())
    return prompt if prompt else None


def resolve_scene_prompt(production_dir: Path, video: dict) -> str:
    prompt_path = production_dir / "prompts" / "scene-base.md"
    extracted = extract_prompt_from_markdown(prompt_path)
    if extracted:
        return sanitize_scene_prompt(extracted)
    return build_scene_prompt(video)
