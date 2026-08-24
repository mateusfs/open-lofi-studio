#!/usr/bin/env python3
"""Gera cena base com IA a partir do prompt da produção."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from scene_prompt import resolve_scene_prompt
from load_env import ensure_env_file, load_env

ensure_env_file()
load_env()

OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt/"
TARGET_SIZE = (1920, 1080)
MIN_SCENE_BYTES = 50_000


def resize_scene(image_bytes: bytes, output: Path) -> None:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    resized = image.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    resized.save(output, format="PNG", optimize=True)


def download_url(url: str, timeout: int = 180) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "OpenLofiStudio/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def generate_with_openai(prompt: str) -> bytes:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")

    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "high").strip() or "high"

    if model.startswith("gpt-image"):
        payload_obj: dict[str, object] = {
            "model": model,
            "prompt": prompt[:4000],
            "size": "1536x1024",
            "quality": quality if quality in {"low", "medium", "high"} else "high",
            "n": 1,
        }
    else:
        dalle_quality = quality if quality in {"standard", "hd"} else "hd"
        payload_obj = {
            "model": model,
            "prompt": prompt[:4000],
            "size": "1792x1024",
            "quality": dalle_quality,
            "n": 1,
        }

    payload = json.dumps(payload_obj).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_IMAGE_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    item = result["data"][0]
    if "b64_json" in item and item["b64_json"]:
        import base64

        return base64.b64decode(item["b64_json"])
    image_url = item.get("url")
    if not image_url:
        raise RuntimeError("OpenAI image response sem url/b64_json")
    return download_url(image_url)


def pollinations_model() -> str:
    return os.environ.get("POLLINATIONS_MODEL", "flux").strip() or "flux"


def scene_ai_provider() -> str:
    return os.environ.get("SCENE_AI_PROVIDER", "auto").strip().lower() or "auto"


def generate_with_pollinations(prompt: str, seed: int) -> bytes:
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    model = pollinations_model()
    url = (
        f"{POLLINATIONS_BASE_URL}{encoded_prompt}"
        f"?width={TARGET_SIZE[0]}&height={TARGET_SIZE[1]}&model={model}"
        f"&seed={seed}&nologo=true&enhance=true&safe=false"
    )
    return download_url(url, timeout=300)


def scene_cache_path(production_id: str) -> Path:
    return ROOT / "assets" / "scenes" / production_id / "scene-base.png"


def restore_cached_scene(production_id: str, output: Path) -> bool:
    cached = scene_cache_path(production_id)
    if not cached.exists() or cached.stat().st_size < MIN_SCENE_BYTES:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached, output)
    return True


def store_scene_cache(production_id: str, output: Path) -> None:
    cached = scene_cache_path(production_id)
    cached.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, cached)


def generate_scene(
    production_dir: Path,
    video: dict,
    output: Path,
    seed: int,
    force: bool = False,
    provider_preference: str | None = None,
) -> str:
    if not force and restore_cached_scene(video["productionId"], output):
        return "cache"

    prompt = resolve_scene_prompt(production_dir, video)
    provider_mode = (provider_preference or scene_ai_provider()).strip().lower()
    providers: list[tuple[str, Callable[[], bytes]]] = []

    if provider_mode in {"auto", "openai"} and os.environ.get("OPENAI_API_KEY", "").strip():
        providers.append(("openai", lambda: generate_with_openai(prompt)))
    if provider_mode in {"auto", "pollinations"}:
        providers.append(("pollinations", lambda: generate_with_pollinations(prompt, seed)))

    if provider_mode == "openai":
        providers = [item for item in providers if item[0] == "openai"]
    elif provider_mode == "pollinations":
        providers = [item for item in providers if item[0] == "pollinations"]

    if not providers:
        raise RuntimeError(
            "Nenhum provedor de imagem disponível. Configure OPENAI_API_KEY ou use --provider pollinations."
        )

    errors: list[str] = []
    for provider_name, provider_call in providers:
        try:
            print(f"Gerando cena IA ({provider_name})...")
            image_bytes = provider_call()
            resize_scene(image_bytes, output)
            if output.stat().st_size < MIN_SCENE_BYTES:
                raise RuntimeError("imagem gerada muito pequena")
            store_scene_cache(video["productionId"], output)
            return provider_name
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, OSError) as error:
            errors.append(f"{provider_name}: {error}")

    raise RuntimeError("Falha ao gerar cena IA — " + " | ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera cena IA para produção")
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--video-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Ignora cache e regenera cena")
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["auto", "openai", "pollinations"],
        help="Provedor de imagem IA",
    )
    args = parser.parse_args()

    production_dir = args.production.resolve()
    video = json.loads(args.video_json.read_text(encoding="utf-8"))
    if args.force and args.output.exists():
        args.output.unlink()
    provider = generate_scene(
        production_dir,
        video,
        args.output.resolve(),
        args.seed,
        force=args.force,
        provider_preference=args.provider,
    )
    print(f"Scene saved: {args.output} (provider={provider})")


if __name__ == "__main__":
    main()
