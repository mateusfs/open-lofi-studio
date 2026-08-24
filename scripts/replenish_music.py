#!/usr/bin/env python3
"""Reabastece automaticamente o pool de música quando faltam faixas livres."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets/audio/music"
CACHE_DIR = ROOT / "assets/audio/.cache"
STATE_PATH = CACHE_DIR / "music-packs-state.json"
LICENSES_PATH = ROOT / "assets/audio/LICENSES.md"

CC0_MUSIC_PACKS: list[dict[str, str]] = [
    {
        "id": "openlofi",
        "url": "https://github.com/btahir/open-lofi/releases/latest/download/openlofi.zip",
        "filename": "openlofi.zip",
        "license": "CC0 1.0 — https://github.com/btahir/open-lofi",
    },
    {
        "id": "holizna-sad-lofi-1",
        "url": "https://opengameart.org/sites/default/files/sad_lofi_1.zip",
        "filename": "sad_lofi_1.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt sad_lofi_1",
    },
    {
        "id": "holizna-sad-lofi-2",
        "url": "https://opengameart.org/sites/default/files/sad_lofi_2.zip",
        "filename": "sad_lofi_2.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt sad_lofi_2",
    },
    {
        "id": "holizna-lofi-chill-1",
        "url": "https://opengameart.org/sites/default/files/lo-fi_and_chill_lofi_collection.zip",
        "filename": "lo-fi_and_chill_lofi_collection.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt lo-fi and chill 1",
    },
    {
        "id": "holizna-lofi-chill-2",
        "url": "https://opengameart.org/sites/default/files/lo-fi_and_chill_lofi_collection_2.zip",
        "filename": "lo-fi_and_chill_lofi_collection_2.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt lo-fi and chill 2",
    },
    {
        "id": "holizna-lofi-chill-3",
        "url": "https://opengameart.org/sites/default/files/lo-fi_and_chill_lofi_collection_3.zip",
        "filename": "lo-fi_and_chill_lofi_collection_3.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt lo-fi and chill 3",
    },
    {
        "id": "holizna-happy-lofi",
        "url": "https://opengameart.org/sites/default/files/happy_lo-fi_lofi_collection.zip",
        "filename": "happy_lo-fi_lofi_collection.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt happy lo-fi",
    },
    {
        "id": "holizna-chillout-instrumentals",
        "url": "https://opengameart.org/sites/default/files/chillout_instrumentals.zip",
        "filename": "chillout_instrumentals.zip",
        "license": "CC0 1.0 — Holizna / OpenGameArt chillout instrumentals",
    },
]


def slugify_track_name(name: str) -> str:
    cleaned = re.sub(r"\.mp3$", "", name, flags=re.I)
    cleaned = re.sub(r"^[\d\s._-]+", "", cleaned)
    cleaned = re.sub(r"^holiznacc0\s*-?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\(lofi\)", "", cleaned, flags=re.I)
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned.lower()).strip("-")
    return slug


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"importedPackIds": [], "generatedTrackSerial": 0}
    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    payload.setdefault("importedPackIds", [])
    payload.setdefault("generatedTrackSerial", 0)
    return payload


def save_state(state: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def download_pack(pack: dict[str, str]) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / pack["filename"]
    if cache_path.exists() and cache_path.stat().st_size > 100_000:
        return cache_path
    print(f"Baixando pack CC0 '{pack['id']}'...")
    request = urllib.request.Request(
        pack["url"],
        headers={"User-Agent": "OpenLofiStudio/1.0"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        cache_path.write_bytes(response.read())
    if cache_path.stat().st_size < 100_000:
        cache_path.unlink(missing_ok=True)
        raise RuntimeError(f"Download inválido: {pack['url']}")
    return cache_path


def import_mp3s_from_zip(zip_path: Path, music_dir: Path = MUSIC_DIR) -> list[str]:
    music_dir.mkdir(parents=True, exist_ok=True)
    imported: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            lower = info.filename.lower()
            if not lower.endswith(".mp3"):
                continue
            if lower.endswith(".mp3.ogg"):
                continue
            base = Path(info.filename).name
            base = re.sub(r"\.mp3\.mp3$", ".mp3", base, flags=re.I)
            slug = slugify_track_name(Path(base).stem)
            if not slug:
                continue
            dest = music_dir / f"{slug}.mp3"
            if dest.exists():
                continue
            with archive.open(info) as source, dest.open("wb") as target:
                shutil.copyfileobj(source, target)
            if dest.stat().st_size < 10_000:
                dest.unlink(missing_ok=True)
                continue
            imported.append(slug)
            print(f"Importada: {dest.name}")
    return imported


def append_license_note(pack: dict[str, str], imported: list[str]) -> None:
    if not imported or not LICENSES_PATH.exists():
        return
    marker = f"## Pack `{pack['id']}`"
    text = LICENSES_PATH.read_text(encoding="utf-8")
    if marker in text:
        return
    block = (
        f"\n{marker}\n\n"
        f"Fonte/licença: {pack['license']}\n\n"
        f"Faixas importadas automaticamente: {', '.join(imported)}\n"
    )
    LICENSES_PATH.write_text(text + block, encoding="utf-8")


def import_next_unused_pack(state: dict | None = None) -> list[str]:
    state = state if state is not None else load_state()
    imported_ids = set(state.get("importedPackIds", []))
    for pack in CC0_MUSIC_PACKS:
        if pack["id"] in imported_ids:
            continue
        try:
            zip_path = download_pack(pack)
            imported = import_mp3s_from_zip(zip_path)
        except Exception as error:
            print(f"Falha no pack {pack['id']}: {error}")
            continue
        imported_ids.add(pack["id"])
        state["importedPackIds"] = sorted(imported_ids)
        save_state(state)
        append_license_note(pack, imported)
        if imported:
            return imported
        print(f"Pack {pack['id']} sem faixas novas (já estavam no disco).")
    return []


def generate_original_tracks(missing: int, music_dir: Path) -> list[str]:
    from generate_lofi_track import generate_unique_tracks

    print(
        f"Packs CC0 esgotados ou insuficientes. "
        f"Gerando {missing} faixa(s) original(is) (OpenAI + síntese local)..."
    )
    return generate_unique_tracks(missing, music_dir=music_dir)


def ensure_free_track_count(
    needed: int,
    exclude_production_id: str | None = None,
    music_dir: Path | None = None,
) -> int:
    from audio_registry import available_track_slugs

    music_dir = music_dir or MUSIC_DIR
    if needed <= 0:
        return len(
            available_track_slugs(
                exclude_production_id=exclude_production_id,
                music_dir=music_dir,
            )
        )

    free = available_track_slugs(
        exclude_production_id=exclude_production_id,
        music_dir=music_dir,
    )
    if len(free) >= needed:
        return len(free)

    print(
        f"Pool de música baixo ({len(free)} livres, precisa {needed}). "
        "Reabastecendo automaticamente..."
    )
    state = load_state()
    while len(free) < needed:
        imported = import_next_unused_pack(state)
        if imported:
            free = available_track_slugs(
                exclude_production_id=exclude_production_id,
                music_dir=music_dir,
            )
            print(f"Faixas livres agora: {len(free)}")
            continue
        missing = needed - len(free)
        generated = generate_original_tracks(missing, music_dir)
        free = available_track_slugs(
            exclude_production_id=exclude_production_id,
            music_dir=music_dir,
        )
        print(f"Faixas livres agora: {len(free)}")
        if not generated or len(free) >= needed:
            break
    return len(free)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reabastece música CC0/original no projeto")
    parser.add_argument("--needed", type=int, default=4)
    parser.add_argument("--exclude-production-id", type=str, default=None)
    args = parser.parse_args()
    total = ensure_free_track_count(args.needed, args.exclude_production_id)
    print(json.dumps({"freeTracks": total}, indent=2))


if __name__ == "__main__":
    main()
