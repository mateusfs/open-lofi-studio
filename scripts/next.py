#!/usr/bin/env python3
"""Gera o próximo vídeo da fila — um comando, sem paths manuais."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from load_env import ensure_env_file, load_env
from queue_catalog import pick_next_catalog_entry

ensure_env_file()
load_env()

QUEUE_PATH = ROOT / "assets/production-queue.json"
PROCEDURAL_SCENE_SHA256 = (
    "4b2c2a00f80595a3cee1e3899b8b6146066140fa6ec5f463a1c12a6d942f32ca"
)
PROCEDURAL_ONLY_IDS = frozenset({"001-coffee-shop-coding"})
MIN_SCENE_BYTES = 50_000


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Comando falhou: {' '.join(command)}\n{result.stderr[-2000:]}"
        )
    return result


def load_queue() -> dict:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def save_queue(data: dict) -> None:
    from datetime import UTC, datetime

    data["updatedAt"] = datetime.now(UTC).strftime("%Y-%m-%d")
    QUEUE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def final_export_path(video: dict) -> Path:
    basename = video["exportBasename"]
    return ROOT / "productions" / video["productionId"] / "exports" / "youtube" / f"{basename}.mp4"


def export_duration(path: Path) -> float | None:
    if not path.exists():
        return None
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def is_export_complete(video: dict) -> bool:
    path = final_export_path(video)
    duration = export_duration(path)
    if duration is None:
        return False
    return abs(duration - video["durationSeconds"]) < 2


def free_disk_gb(path: Path = ROOT) -> float:
    return shutil.disk_usage(path).free / (1024**3)


def estimate_required_gb(duration_seconds: int) -> float:
    hours = duration_seconds / 3600
    return max(6.0, hours * 0.65 + 4.0)


def ensure_disk_space(duration_seconds: int) -> None:
    required = estimate_required_gb(duration_seconds)
    available = free_disk_gb()
    if available < required:
        raise SystemExit(
            f"Espaço insuficiente: {available:.1f} GB livres, "
            f"necessário ~{required:.1f} GB para {duration_seconds // 3600}h. "
            "Apague exports antigos ou mova para HD externo."
        )


def remove_corrupt_export(video: dict) -> None:
    path = final_export_path(video)
    if not path.exists():
        return
    if is_export_complete(video) or render_in_progress(video):
        return
    print(f"Removendo export corrompido/incompleto: {path.name}")
    path.unlink(missing_ok=True)


def render_in_progress(video: dict) -> bool:
    path = final_export_path(video)
    if is_export_complete(video):
        return False
    if not path.exists():
        return False
    result = subprocess.run(
        ["pgrep", "-f", str(path.name)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def preview_export_path(video: dict, preview_seconds: int | None = None) -> Path:
    basename = video["exportBasename"]
    exports = ROOT / "productions" / video["productionId"] / "exports" / "youtube"
    if preview_seconds is not None:
        return exports / f"{basename}-{preview_seconds}s-preview.mp4"
    matches = sorted(exports.glob(f"{basename}-*-preview.mp4"))
    if matches:
        return matches[-1]
    return exports / f"{basename}-30s-preview.mp4"


def has_ready_preview(video: dict) -> bool:
    exports = ROOT / "productions" / video["productionId"] / "exports" / "youtube"
    if not exports.exists():
        return False
    basename = video["exportBasename"]
    for path in exports.glob(f"{basename}-*-preview.mp4"):
        if path.stat().st_size > 100_000:
            return True
    return False


def resolve_next_video(mutate: bool = True, preview_mode: bool = False) -> dict:
    data = load_queue()
    for video in data.get("videos", []):
        status = video.get("status")
        if is_export_complete(video):
            continue
        if status == "em produção":
            if preview_mode and has_ready_preview(video):
                if mutate:
                    set_video_status(video["productionId"], "preview")
                continue
            return video
        if status == "preview" and not preview_mode:
            return video
    for video in data.get("videos", []):
        if video.get("status") == "planejado":
            return video

    next_entry = pick_next_catalog_entry(data.get("videos", []), is_export_complete)
    if next_entry:
        if mutate:
            data = load_queue()
            ids = {item["productionId"] for item in data.get("videos", [])}
            if next_entry["productionId"] not in ids:
                data.setdefault("videos", []).append(next_entry)
                save_queue(data)
                print(
                    f"Enfileirado do catálogo: #{next_entry['number']} — {next_entry['titleEn']}"
                )
            else:
                next_entry = next(
                    item
                    for item in data["videos"]
                    if item["productionId"] == next_entry["productionId"]
                )
        return next_entry

    raise SystemExit("Fila vazia: nenhum vídeo pendente no catálogo.")


def set_video_status(production_id: str, status: str) -> None:
    data = load_queue()
    for entry in data["videos"]:
        if entry["productionId"] == production_id:
            entry["status"] = status
            break
    save_queue(data)


def claim_video(production_id: str) -> None:
    set_video_status(production_id, "em produção")


def complete_video(production_id: str) -> None:
    set_video_status(production_id, "produzido")


def mark_preview_ready(production_id: str) -> None:
    set_video_status(production_id, "preview")


def scaffold(production_dir: Path, video: dict) -> None:
    run(
        [
            sys.executable,
            str(SCRIPTS / "setup_production.py"),
            "--id",
            video["productionId"],
        ]
    )


def fetch_tracks(slugs: list[str]) -> None:
    if not slugs:
        return
    run(
        [
            sys.executable,
            str(SCRIPTS / "fetch_open_lofi_tracks.py"),
            "--slugs",
            *slugs,
        ]
    )


def ensure_playlist(production_dir: Path, video: dict) -> list[str]:
    from audio_registry import MusicRegistryError, ensure_audio_json_playlist

    preferred = [str(slug) for slug in video.get("audio", {}).get("tracks", [])]
    try:
        files = ensure_audio_json_playlist(
            production_dir,
            video["productionId"],
            preferred_slugs=preferred,
        )
    except MusicRegistryError as error:
        raise SystemExit(str(error)) from error
    slugs = [path.stem for path in files]
    fetch_tracks(slugs)
    video.setdefault("audio", {})["tracks"] = slugs
    print(f"Playlist OK ({len(slugs)} faixas): {', '.join(slugs)}")
    return slugs


def is_procedural_scene(scene_path: Path) -> bool:
    digest = hashlib.sha256(scene_path.read_bytes()).hexdigest()
    return digest == PROCEDURAL_SCENE_SHA256


def scene_is_ready(scene_path: Path) -> bool:
    if not scene_path.exists():
        return False
    if scene_path.stat().st_size < MIN_SCENE_BYTES:
        return False
    return not is_procedural_scene(scene_path)


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


def ensure_scene(production_dir: Path, video: dict) -> None:
    scene_path = production_dir / "source" / "scene-base.png"
    production_id = video["productionId"]

    if scene_is_ready(scene_path):
        store_scene_cache(production_id, scene_path)
        return

    if scene_path.exists():
        print(f"Removendo cena inválida (procedural ou muito pequena): {scene_path.name}")
        scene_path.unlink(missing_ok=True)
        loop_path = production_dir / "source" / "scene-loop.mp4"
        loop_path.unlink(missing_ok=True)

    if restore_cached_scene(production_id, scene_path) and scene_is_ready(scene_path):
        print(f"Cena restaurada do backup: {scene_cache_path(production_id)}")
        return

    if production_id in PROCEDURAL_ONLY_IDS:
        print("Cena ausente — usando fallback procedural (#001)...")
        run(
            [
                sys.executable,
                str(SCRIPTS / "generate_scene.py"),
                "--output",
                str(scene_path),
            ]
        )
        return

    seed = int(video.get("animate", {}).get("seed", 42))
    video_json = production_dir / "source" / ".video-for-scene.json"
    video_json.parent.mkdir(parents=True, exist_ok=True)
    video_json.write_text(json.dumps(video, indent=2) + "\n", encoding="utf-8")
    print("Cena ausente — gerando automaticamente via generate_scene_ai.py...")
    run(
        [
            sys.executable,
            str(SCRIPTS / "generate_scene_ai.py"),
            "--production",
            str(production_dir),
            "--video-json",
            str(video_json),
            "--output",
            str(scene_path),
            "--seed",
            str(seed),
        ]
    )
    if not scene_is_ready(scene_path):
        raise SystemExit(
            f"Falha ao gerar cena IA: {scene_path}\n"
            "Configure OPENAI_API_KEY ou SCENE_AI_PROVIDER=pollinations no .env"
        )
    store_scene_cache(production_id, scene_path)


def produce(production_dir: Path, duration: int, preview: int | None, skip_scene: bool) -> Path:
    args = [
        sys.executable,
        str(SCRIPTS / "produce_video.py"),
        "--production",
        str(production_dir),
        "--duration",
        str(duration),
    ]
    if preview:
        args.extend(["--preview", str(preview)])
    if skip_scene:
        args.append("--skip-scene")
    result = subprocess.run(args)
    if result.returncode != 0:
        raise RuntimeError("produce_video.py falhou")
    meta = json.loads((production_dir / "meta.json").read_text(encoding="utf-8"))
    basename = meta["exportBasename"]
    if preview:
        return production_dir / "exports" / "youtube" / f"{basename}-{preview}s-preview.mp4"
    return production_dir / "exports" / "youtube" / f"{basename}.mp4"


def update_calendar_status(production_id: str, status: str) -> None:
    calendar = ROOT / "docs/05-calendario-de-videos.md"
    if not calendar.exists():
        return
    text = calendar.read_text(encoding="utf-8")
    number = production_id.split("-")[0]
    old = f"| {number} |"
    if old not in text:
        return
    lines = text.splitlines()
    updated: list[str] = []
    for line in lines:
        if not line.startswith(f"| {number} |"):
            updated.append(line)
            continue
        if "| planejado |" in line:
            updated.append(line.replace("| planejado |", f"| {status} |"))
        elif "| em produção |" in line and status in {"preview", "produzido"}:
            updated.append(line.replace("| em produção |", f"| {status} |"))
        elif "| preview |" in line and status == "produzido":
            updated.append(line.replace("| preview |", "| produzido |"))
        else:
            updated.append(line)
    calendar.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o próximo vídeo da fila")
    parser.add_argument("--preview", type=int, default=None, help="Só gera preview (segundos)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o próximo sem produzir")
    args = parser.parse_args()

    preview_mode = args.preview is not None
    video = resolve_next_video(mutate=not args.dry_run, preview_mode=preview_mode)
    production_id = video["productionId"]
    production_dir = ROOT / "productions" / production_id
    duration = video["durationSeconds"]

    print(f"▶ Próximo: #{video['number']} — {video['titleEn']}")

    if args.dry_run:
        print(json.dumps(video, indent=2))
        return

    if render_in_progress(video):
        print(
            json.dumps(
                {
                    "status": "em_andamento",
                    "productionId": production_id,
                    "message": "Render já em execução. Aguarde concluir antes de rodar novamente.",
                },
                indent=2,
            )
        )
        return

    if video.get("status") == "planejado":
        claim_video(production_id)
        update_calendar_status(production_id, "em produção")

    scaffold(production_dir, video)
    ensure_playlist(production_dir, video)
    ensure_scene(production_dir, video)

    if not args.preview:
        remove_corrupt_export(video)
        ensure_disk_space(duration)

    loop_exists = (production_dir / "source" / "scene-loop.mp4").exists()
    output = produce(
        production_dir,
        duration,
        args.preview,
        skip_scene=loop_exists and not args.preview,
    )

    if args.preview:
        mark_preview_ready(production_id)
        update_calendar_status(production_id, "preview")
    else:
        complete_video(production_id)
        update_calendar_status(production_id, "produzido")

    summary = {
        "productionId": production_id,
        "title": video["titleEn"],
        "output": str(output),
        "thumbnail": str(production_dir / "source" / "thumbnail.png"),
        "status": "preview" if args.preview else "produzido",
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
