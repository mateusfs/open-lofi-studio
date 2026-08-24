#!/usr/bin/env python3
"""Regenera a cena de uma produção e opcionalmente refaz só o preview."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from load_env import ensure_env_file, load_env
from queue_catalog import catalog_entries

ensure_env_file()
load_env()

QUEUE_PATH = ROOT / "assets/production-queue.json"


def load_queue() -> dict:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def resolve_video(selector: str) -> dict:
    selector = selector.strip()
    data = load_queue()
    videos = data.get("videos", [])

    for video in videos:
        if video.get("productionId") == selector or str(video.get("number")) == selector:
            return video

    for entry in catalog_entries():
        if entry.get("productionId") == selector or str(entry.get("number")) == selector:
            return entry

    raise SystemExit(
        f"Produção não encontrada: {selector}\n"
        "Use o número (ex.: 090) ou o productionId completo."
    )


def clear_scene_artifacts(production_dir: Path, production_id: str) -> None:
    source = production_dir / "source"
    targets = [
        source / "scene-base.png",
        source / "scene-loop.mp4",
        source / "effect-mask.png",
        source / "thumbnail.png",
        ROOT / "assets" / "scenes" / production_id / "scene-base.png",
    ]
    for path in targets:
        if path.exists():
            path.unlink()
            print(f"Removido: {path.relative_to(ROOT)}")


DEFAULT_PREVIEW_SECONDS = 300


def apply_prompt_variation(production_dir: Path, video: dict, seed: int) -> str:
    from scene_prompt import resolve_scene_prompt

    base = resolve_scene_prompt(production_dir, video)
    variations = [
        "different camera angle and framing than previous generations",
        "wider establishing shot of the empty office floor",
        "closer desk-level composition with stronger depth of field",
        "side angle showing more of the open space and glass windows",
        "elevated three-quarter view of the late-night workspace",
    ]
    variation = variations[seed % len(variations)]
    prompt = (
        f"{base}, {variation}, unique prop arrangement, "
        f"do not copy prior generations, variation id {seed}"
    )
    prompt_path = production_dir / "prompts" / "scene-base.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    title = video.get("titleEn", video.get("productionId", "scene"))
    prompt_path.write_text(
        f"# Prompt — {title}\n\n"
        f"## Midjourney / DALL·E\n\n```\n{prompt}\n```\n\n"
        f"### Parâmetros Midjourney\n\n```\n--ar 16:9 --style raw --v 6\n```\n\n"
        f"## Stable Diffusion XL\n\n**Positive:**\n```\n{prompt}\n```\n\n"
        f"**Negative:**\n```\npeople, faces, text, watermark, logo, blurry, low quality, "
        f"cartoon, anime, bright daylight, overexposed\n```\n\n"
        f"Salvar imagem final em `source/scene-base.png` (mínimo 1920×1080).\n",
        encoding="utf-8",
    )
    video["scenePrompt"] = prompt
    return prompt


def regenerate_scene(production_dir: Path, video: dict, seed: int, provider: str | None) -> None:
    production_dir.mkdir(parents=True, exist_ok=True)
    (production_dir / "source").mkdir(parents=True, exist_ok=True)
    (production_dir / "prompts").mkdir(parents=True, exist_ok=True)

    apply_prompt_variation(production_dir, video, seed)

    video_json = production_dir / "source" / ".video-for-scene.json"
    video_json.write_text(json.dumps(video, indent=2) + "\n", encoding="utf-8")
    output = production_dir / "source" / "scene-base.png"

    command = [
        sys.executable,
        str(SCRIPTS / "generate_scene_ai.py"),
        "--production",
        str(production_dir),
        "--video-json",
        str(video_json),
        "--output",
        str(output),
        "--seed",
        str(seed),
        "--force",
    ]
    if provider:
        command.extend(["--provider", provider])

    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit("Falha ao regenerar a cena.")

    cache = ROOT / "assets" / "scenes" / video["productionId"] / "scene-base.png"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(output.read_bytes())
    print(f"Cache atualizado: {cache.relative_to(ROOT)}")


def run_preview(production_dir: Path, preview_seconds: int) -> Path:
    command = [
        sys.executable,
        str(SCRIPTS / "produce_video.py"),
        "--production",
        str(production_dir),
        "--preview",
        str(preview_seconds),
    ]
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit("Falha ao gerar o preview.")
    meta = json.loads((production_dir / "meta.json").read_text(encoding="utf-8"))
    basename = meta["exportBasename"]
    return production_dir / "exports" / "youtube" / f"{basename}-{preview_seconds}s-preview.mp4"


def main() -> None:
    parser = argparse.ArgumentParser(description="Refaz a cena de uma produção")
    parser.add_argument("production", help="Número (090) ou productionId")
    parser.add_argument("--seed", type=int, default=None, help="Seed da imagem (muda o resultado)")
    parser.add_argument(
        "--provider",
        choices=["auto", "openai", "pollinations"],
        default=None,
    )
    parser.add_argument(
        "--preview",
        type=int,
        nargs="?",
        const=DEFAULT_PREVIEW_SECONDS,
        default=None,
        help="Depois da cena, gera preview (padrão 300s / 5 min se passar --preview)",
    )
    args = parser.parse_args()

    video = resolve_video(args.production)
    production_id = video["productionId"]
    production_dir = ROOT / "productions" / production_id
    seed = (
        args.seed
        if args.seed is not None
        else int(video.get("animate", {}).get("seed", 42)) + int(time.time()) % 10_000
    )

    print(f"▶ Refazendo cena: #{video.get('number')} — {video.get('titleEn')}")
    clear_scene_artifacts(production_dir, production_id)
    regenerate_scene(production_dir, video, seed=seed, provider=args.provider)

    if args.preview is not None:
        if not (production_dir / "meta.json").exists():
            subprocess.run(
                [sys.executable, str(SCRIPTS / "setup_production.py"), "--id", production_id],
                check=True,
            )
        preview_path = run_preview(production_dir, args.preview)
        print(
            json.dumps(
                {
                    "status": "preview",
                    "scene": str(production_dir / "source" / "scene-base.png"),
                    "preview": str(preview_path),
                    "previewSeconds": args.preview,
                },
                indent=2,
            )
        )
        return

    print(
        json.dumps(
            {
                "status": "scene_ready",
                "scene": str(production_dir / "source" / "scene-base.png"),
                "hint": "Abra scene-base.png para ver a nova cena. O MP4 antigo NÃO muda até rodar preview.",
                "next": (
                    f".venv/bin/python scripts/produce_video.py --production {production_dir} "
                    f"--preview {DEFAULT_PREVIEW_SECONDS}"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
