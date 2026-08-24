#!/usr/bin/env python3
"""Baixa faixas do open-lofi por slug e salva em assets/audio/music/."""

from __future__ import annotations

import argparse
import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets/audio/music"
ZIP_URL = "https://github.com/btahir/open-lofi/releases/latest/download/openlofi.zip"


def slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-")


def download_zip(cache_path: Path) -> Path:
    if cache_path.exists() and cache_path.stat().st_size > 1_000_000:
        return cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Baixando open-lofi ({ZIP_URL})...")
    urllib.request.urlretrieve(ZIP_URL, cache_path)
    return cache_path


def find_track_in_zip(archive: zipfile.ZipFile, slug: str) -> str | None:
    slug_norm = slug.lower()
    target = slug_norm.replace("-", " ")
    words = [word for word in slug_norm.split("-") if len(word) > 2]
    candidates: list[tuple[int, str]] = []

    for name in archive.namelist():
        if not name.lower().endswith(".mp3"):
            continue
        base = Path(name).stem
        base_slug = slugify_name(base)
        if base_slug == slug_norm or target in base.lower():
            return name
        if slug_norm in base_slug or base_slug in slug_norm:
            candidates.append((abs(len(base_slug) - len(slug_norm)), name))
        elif words and all(word in base_slug for word in words):
            candidates.append((abs(len(base_slug) - len(slug_norm)), name))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        match = candidates[0][1]
        print(f"Match aproximado: {slug} → {Path(match).stem}")
        return match
    return None


def fetch_tracks(slugs: list[str], output_dir: Path, cache_zip: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = download_zip(cache_zip)
    saved: list[Path] = []

    with zipfile.ZipFile(zip_path) as archive:
        for slug in slugs:
            dest = output_dir / f"{slug}.mp3"
            if dest.exists():
                print(f"Já existe: {dest.name}")
                saved.append(dest)
                continue
            member = find_track_in_zip(archive, slug)
            if not member:
                raise FileNotFoundError(f"Faixa não encontrada no ZIP: {slug}")
            dest.write_bytes(archive.read(member))
            print(f"Extraído: {dest.name}")
            saved.append(dest)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa faixas CC0 do open-lofi")
    parser.add_argument("--slugs", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=MUSIC_DIR)
    parser.add_argument(
        "--cache-zip",
        type=Path,
        default=ROOT / "assets/audio/.cache/openlofi.zip",
    )
    args = parser.parse_args()
    paths = fetch_tracks(args.slugs, args.output_dir, args.cache_zip)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
