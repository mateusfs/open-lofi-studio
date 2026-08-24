#!/usr/bin/env python3
"""Prepara pasta de produção a partir da fila (assets/production-queue.json)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS))
from scaffold_docs import scaffold_docs
from scene_prompt import build_scene_prompt


def run_next_video(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "next_video.py"), "--json", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def write_audio_json(production_dir: Path, video: dict) -> None:
    audio = video["audio"]
    tracks = [f"assets/audio/music/{slug}.mp3" for slug in audio["tracks"]]
    payload = {
        "productionId": video["productionId"],
        "tracks": tracks,
        "rainVolume": audio.get("rainVolume", 0.055),
        "cafeVolume": audio.get("cafeVolume", 0.03),
        "whiteNoiseVolume": audio.get("whiteNoiseVolume", 0.0),
        "musicVolume": audio.get("musicVolume", 0.065),
        "noRain": audio.get("noRain", False),
        "noCafe": audio.get("noCafe", False),
        "noWhiteNoise": audio.get("noWhiteNoise", audio.get("whiteNoiseVolume", 0.0) <= 0),
    }
    if "ambience" in audio:
        payload["ambience"] = audio["ambience"]
    (production_dir / "audio.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_meta_json(production_dir: Path, video: dict) -> None:
    animate = dict(video.get("animate", {}))
    layers = animate.get("layers")
    if isinstance(layers, list) and layers:
        animate.setdefault("mode", "hybrid")
    else:
        animate.setdefault("mode", "ambient")
        animate.setdefault("loopSeconds", 24)
    payload = {
        "series": video["series"],
        "mood": video["mood"],
        "durationLabel": video["durationLabel"],
        "exportBasename": video["exportBasename"],
        "animate": animate,
        "number": video.get("number"),
        "titleEn": video.get("titleEn"),
        "youtubeTags": video.get("youtubeTags"),
        "durationSeconds": video.get("durationSeconds"),
    }
    (production_dir / "meta.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_scene_prompt(production_dir: Path, video: dict) -> None:
    prompt = build_scene_prompt(video)
    content = f"""# Prompt — {video['titleEn']}

## Midjourney / DALL·E

```
{prompt}
```

### Parâmetros Midjourney

```
--ar 16:9 --style raw --v 6
```

## Stable Diffusion XL

**Positive:**
```
{prompt}
```

**Negative:**
```
people, faces, text, watermark, logo, blurry, low quality, cartoon, anime,
bright daylight, overexposed
```

Salvar imagem final em `source/scene-base.png` (mínimo 1920×1080).
"""
    prompts = production_dir / "prompts" / "scene-base.md"
    prompts.parent.mkdir(parents=True, exist_ok=True)
    prompts.write_text(content, encoding="utf-8")


def scaffold(production_dir: Path, video: dict) -> None:
    for sub in ("prompts", "source", "exports/youtube", "exports/streaming"):
        (production_dir / sub).mkdir(parents=True, exist_ok=True)
    write_audio_json(production_dir, video)
    write_meta_json(production_dir, video)
    scaffold_docs(production_dir, video)
    write_scene_prompt(production_dir, video)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold de produção a partir da fila")
    parser.add_argument("--claim", action="store_true", help="Marca vídeo como em produção na fila")
    parser.add_argument("--id", type=str, default=None, help="productionId específico")
    args = parser.parse_args()

    claim_args = ["--claim"] if args.claim else []
    if args.id:
        claim_args.extend(["--id", args.id])
    video = run_next_video(claim_args)
    production_dir = ROOT / "productions" / video["productionId"]
    scaffold(production_dir, video)
    print(json.dumps({"productionDir": str(production_dir), "video": video}, indent=2))


if __name__ == "__main__":
    main()
