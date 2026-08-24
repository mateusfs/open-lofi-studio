#!/usr/bin/env python3
"""Registro e validação de trilhas por produção — uma playlist única por vídeo."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "assets/audio/music-registry.json"


class MusicRegistryError(ValueError):
    pass


def track_slug(path: Path | str) -> str:
    return Path(path).stem


def load_registry(registry_path: Path = DEFAULT_REGISTRY) -> dict:
    if not registry_path.exists():
        raise MusicRegistryError(f"Registro não encontrado: {registry_path}")
    return json.loads(registry_path.read_text(encoding="utf-8"))


def save_registry(data: dict, registry_path: Path = DEFAULT_REGISTRY) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def production_track_slugs(registry: dict, production_id: str) -> set[str]:
    entry = registry.get("productions", {}).get(production_id, {})
    return {track_slug(name) for name in entry.get("tracks", [])}


def all_used_slugs(registry: dict, exclude_production_id: str | None = None) -> set[str]:
    used: set[str] = set()
    for prod_id, entry in registry.get("productions", {}).items():
        if exclude_production_id and prod_id == exclude_production_id:
            continue
        used.update(track_slug(name) for name in entry.get("tracks", []))
    return used


def validate_playlist(
    production_id: str,
    music_files: list[Path],
    registry_path: Path = DEFAULT_REGISTRY,
) -> None:
    registry = load_registry(registry_path)
    slugs = [track_slug(path) for path in music_files]
    if len(slugs) != len(set(slugs)):
        raise MusicRegistryError(f"Playlist duplicada na mesma produção: {slugs}")

    rules = registry.get("rules", {})
    legacy_size = rules.get("playlistSize", 4)
    min_size = rules.get("playlistSizeMin", legacy_size)
    max_size = rules.get("playlistSizeMax", legacy_size)
    if not min_size <= len(slugs) <= max_size:
        raise MusicRegistryError(
            f"Produção {production_id}: playlist deve ter entre {min_size} e {max_size} faixas, "
            f"recebeu {len(slugs)}"
        )

    existing = production_track_slugs(registry, production_id)
    if existing == set(slugs):
        return

    used_elsewhere = all_used_slugs(registry, exclude_production_id=production_id)
    blocked = {track_slug(name) for name in registry.get("blockedSlugs", [])}
    planned_elsewhere: set[str] = set()
    for planned_id, entry in registry.get("planned", {}).items():
        if planned_id == production_id:
            continue
        planned_elsewhere.update(track_slug(name) for name in entry.get("tracks", []))
    conflicts = [
        slug
        for slug in slugs
        if slug in used_elsewhere or slug in blocked or slug in planned_elsewhere
    ]
    if conflicts:
        raise MusicRegistryError(
            f"Faixas já usadas ou bloqueadas: {', '.join(conflicts)}. "
            "Baixe trilhas novas do open-lofi e atualize productions/XXX/audio.json"
        )


def register_production(
    production_id: str,
    music_files: list[Path],
    registry_path: Path = DEFAULT_REGISTRY,
) -> None:
    registry = load_registry(registry_path)
    productions = registry.setdefault("productions", {})
    productions[production_id] = {
        "tracks": [track_slug(path) for path in music_files],
        "files": [str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path) for path in music_files],
    }
    save_registry(registry, registry_path)


def _normalize_slug(value: object) -> str:
    return track_slug(str(value))


def locked_production_ids(
    queue_path: Path = ROOT / "assets/production-queue.json",
) -> set[str]:
    locked: set[str] = set()
    if queue_path.exists():
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
        for video in payload.get("videos", []):
            status = video.get("status")
            production_id = str(video.get("productionId", ""))
            if status in {"produzido", "preview", "em produção"} and production_id:
                locked.add(production_id)
    productions_root = ROOT / "productions"
    if productions_root.exists():
        for production_dir in productions_root.iterdir():
            if not production_dir.is_dir():
                continue
            exports = production_dir / "exports" / "youtube"
            if not exports.exists():
                continue
            for path in exports.glob("*.mp4"):
                if "preview" in path.name:
                    continue
                if path.stat().st_size > 20_000_000:
                    locked.add(production_dir.name)
                    break
    return locked


def prune_unlocked_registry_entries(
    registry_path: Path = DEFAULT_REGISTRY,
    queue_path: Path = ROOT / "assets/production-queue.json",
) -> list[str]:
    registry = load_registry(registry_path)
    locked = locked_production_ids(queue_path)
    productions = registry.setdefault("productions", {})
    removed: list[str] = []
    for production_id in list(productions.keys()):
        if production_id not in locked:
            del productions[production_id]
            removed.append(production_id)
    if removed:
        save_registry(registry, registry_path)
    return removed


def available_track_slugs(
    exclude_production_id: str | None = None,
    registry_path: Path | None = None,
    music_dir: Path | None = None,
) -> list[str]:
    registry_path = registry_path or DEFAULT_REGISTRY
    music_dir = music_dir or (ROOT / "assets/audio/music")
    registry = load_registry(registry_path)
    used = all_used_slugs(registry, exclude_production_id=exclude_production_id)
    blocked = {_normalize_slug(name) for name in registry.get("blockedSlugs", [])}
    local = sorted(path.stem for path in music_dir.glob("*.mp3"))
    return [slug for slug in local if slug not in used and slug not in blocked]


def allocate_playlist_slugs(
    production_id: str,
    count: int = 4,
    preferred: list[str] | None = None,
    registry_path: Path | None = None,
    music_dir: Path | None = None,
) -> list[str]:
    registry_path = registry_path or DEFAULT_REGISTRY
    music_dir = music_dir or (ROOT / "assets/audio/music")
    prune_unlocked_registry_entries(registry_path)
    available = available_track_slugs(
        exclude_production_id=production_id,
        registry_path=registry_path,
        music_dir=music_dir,
    )
    if len(available) < count:
        from replenish_music import ensure_free_track_count

        ensure_free_track_count(count, exclude_production_id=production_id)
        available = available_track_slugs(
            exclude_production_id=production_id,
            registry_path=registry_path,
            music_dir=music_dir,
        )
    available_set = set(available)
    chosen: list[str] = []
    for slug in preferred or []:
        clean = _normalize_slug(slug)
        if clean in available_set and clean not in chosen:
            chosen.append(clean)
        if len(chosen) >= count:
            return chosen[:count]
    for slug in available:
        if slug not in chosen:
            chosen.append(slug)
        if len(chosen) >= count:
            return chosen[:count]
    raise MusicRegistryError(
        f"Produção {production_id}: só há {len(chosen)} faixas livres (precisa {count}) "
        "mesmo após packs CC0 e geração original. Verifique ffmpeg e OPENAI_API_KEY no .env."
    )


def ensure_audio_json_playlist(
    production_dir: Path,
    production_id: str,
    preferred_slugs: list[str] | None = None,
    registry_path: Path | None = None,
) -> list[Path]:
    registry_path = registry_path or DEFAULT_REGISTRY
    audio_path = production_dir / "audio.json"
    if not audio_path.exists():
        raise MusicRegistryError(f"audio.json ausente em {production_dir}")
    payload = json.loads(audio_path.read_text(encoding="utf-8"))
    current = [Path(str(item)) for item in payload.get("tracks", [])]
    current_files = [
        (ROOT / path if not path.is_absolute() else path) for path in current
    ]
    try:
        existing = [path for path in current_files if path.exists()]
        if existing:
            validate_playlist(production_id, existing, registry_path)
            if float(payload.get("musicVolume", 1.0)) >= 0.5:
                payload["musicVolume"] = 0.065
                audio_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return existing
    except MusicRegistryError:
        pass

    preferred = preferred_slugs or [track_slug(path) for path in current]
    music_dir = ROOT / "assets/audio/music"
    slugs = allocate_playlist_slugs(
        production_id,
        count=4,
        preferred=preferred,
        registry_path=registry_path,
        music_dir=music_dir,
    )
    files = [music_dir / f"{slug}.mp3" for slug in slugs]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise MusicRegistryError(f"Faixas alocadas ausentes no disco: {', '.join(missing)}")
    payload["tracks"] = [f"assets/audio/music/{slug}.mp3" for slug in slugs]
    payload["productionId"] = production_id
    if float(payload.get("musicVolume", 1.0)) >= 0.5:
        payload["musicVolume"] = 0.065
    audio_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return files
