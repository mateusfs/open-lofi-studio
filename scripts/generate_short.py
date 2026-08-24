#!/usr/bin/env python3
"""Gera Shorts via MoneyPrinterTurbo CLI oficial (script → TTS → legendas → clips → BGM)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
MPT_ROOT = ROOT / "tools" / "moneyprinterturbo" / "upstream"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from queue_catalog import catalog_entries

QUEUE_PATH = ROOT / "assets/production-queue.json"
DEFAULT_VOICE = "en-US-AriaNeural-Female"
DEFAULT_SUBTITLE_FONT = "Inter-Bold.ttf"
DEFAULT_SUBTITLE_SIZE = 64


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed: {' '.join(command)}\n"
            f"stdout:\n{result.stdout[-2000:]}\n"
            f"stderr:\n{result.stderr[-2500:]}"
        )


def probe_duration(path: Path) -> float:
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
        check=True,
    )
    return float(result.stdout.strip())


def load_queue() -> dict:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def resolve_production_dir(selector: str) -> Path:
    raw = selector.strip()
    as_path = Path(raw)
    if as_path.is_dir() and (as_path / "meta.json").exists():
        return as_path.resolve()
    if not as_path.is_absolute():
        candidate = (ROOT / as_path).resolve()
        if candidate.is_dir() and (candidate / "meta.json").exists():
            return candidate

    videos = load_queue().get("videos", [])
    entries = list(videos) + list(catalog_entries())
    for entry in entries:
        number = str(entry.get("number", ""))
        production_id = str(entry.get("productionId", ""))
        if raw == number or raw == production_id or raw.lstrip("0") == number.lstrip("0"):
            path = ROOT / "productions" / production_id
            if path.is_dir():
                return path.resolve()
            raise FileNotFoundError(f"Produção na fila mas pasta ausente: {path}")

    matches = sorted((ROOT / "productions").glob(f"{raw}*"))
    for match in matches:
        if match.is_dir() and (match / "meta.json").exists():
            return match.resolve()

    raise FileNotFoundError(
        f"Produção não encontrada: {selector}\n"
        "Use: npm run short:preview -- 110"
    )


def load_meta(production_dir: Path) -> dict:
    return json.loads((production_dir / "meta.json").read_text(encoding="utf-8"))


def load_audio_config(production_dir: Path) -> dict:
    path = production_dir / "audio.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_bgm(production_dir: Path, audio: dict) -> Path | None:
    tracks = audio.get("tracks", [])
    for track in tracks:
        path = Path(str(track))
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            return path
        slug = path.stem
        candidate = ROOT / "assets/audio/music" / f"{slug}.mp3"
        if candidate.exists():
            return candidate
    return None


def build_mpt_script(meta: dict) -> str:
    series = str(meta.get("series", "Ambience Session"))
    mood = str(meta.get("mood", "Deep Focus"))
    mood = mood.replace("•", "—").replace("  ", " ").strip()
    duration = str(meta.get("durationLabel", "4 HOURS"))
    return (
        f"Welcome to {series}. "
        f"This is {mood} — a {duration.lower()} focus session built for developers. "
        f"Settle into the ambience, open your editor, and stay in flow. "
        f"The full session is waiting on the channel. "
        f"Subscribe, hit play, and code with us."
    )


def ensure_mpt_ready() -> Path:
    if not MPT_ROOT.is_dir():
        raise FileNotFoundError(
            f"MoneyPrinterTurbo não encontrado em {MPT_ROOT}. "
            "Clone: git clone https://github.com/harry0703/MoneyPrinterTurbo.git "
            "tools/moneyprinterturbo/upstream"
        )
    config = MPT_ROOT / "config.toml"
    if not config.exists():
        example = MPT_ROOT / "config.example.toml"
        if not example.exists():
            raise FileNotFoundError("config.example.toml ausente no upstream MPT")
        text = example.read_text(encoding="utf-8")
        text = text.replace('video_source = "pexels"', 'video_source = "local"')
        config.write_text(text, encoding="utf-8")
    fonts_dir = MPT_ROOT / "resource" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    target_font = fonts_dir / DEFAULT_SUBTITLE_FONT
    if not target_font.exists():
        brand_font = ROOT / "brand" / "fonts" / DEFAULT_SUBTITLE_FONT
        system_font = Path("/usr/share/fonts/truetype/inter-zorin-os/Inter-Bold.ttf")
        source = brand_font if brand_font.exists() else system_font
        if not source.exists():
            raise FileNotFoundError(
                f"Fonte de legenda ausente: {DEFAULT_SUBTITLE_FONT}. "
                f"Coloque em brand/fonts/ ou {fonts_dir}"
            )
        shutil.copy2(source, target_font)
    return MPT_ROOT


def resolve_mpt_python(mpt_root: Path) -> Path:
    candidates = [
        mpt_root / ".venv" / "bin" / "python",
        ROOT / ".venv" / "bin" / "python",
        Path(sys.executable),
    ]
    for path in candidates:
        if path.exists():
            return path
    return Path(sys.executable)


def prepare_materials(
    production_dir: Path,
    materials_dir: Path,
    clip_seconds: int = 4,
    clip_count: int = 10,
) -> list[Path]:
    materials_dir.mkdir(parents=True, exist_ok=True)
    source = production_dir / "source"
    scene = source / "scene-base.png"
    loop = source / "scene-loop.mp4"
    thumb = source / "thumbnail.png"
    prepared: list[Path] = []

    if scene.exists():
        dest = materials_dir / "scene-base.png"
        shutil.copy2(scene, dest)
        prepared.append(dest)
    if thumb.exists():
        dest = materials_dir / "thumbnail.png"
        shutil.copy2(thumb, dest)
        prepared.append(dest)

    if loop.exists():
        duration = max(probe_duration(loop), 1.0)
        usable = max(duration - clip_seconds, 0.1)
        for index in range(clip_count):
            start = (index * (usable / max(clip_count - 1, 1))) % duration
            clip_path = materials_dir / f"loop-clip-{index:02d}.mp4"
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{start:.3f}",
                    "-i",
                    str(loop),
                    "-t",
                    str(clip_seconds),
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip_path),
                ]
            )
            prepared.append(clip_path)

    if not prepared:
        raise FileNotFoundError("Precisa de scene-base.png ou scene-loop.mp4 para Short MPT")
    return prepared


def stage_bgm(mpt_root: Path, bgm: Path | None) -> str | None:
    if not bgm or not bgm.exists():
        return None
    bgm_dir = mpt_root / "storage" / "bgm"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    dest = bgm_dir / bgm.name
    shutil.copy2(bgm, dest)
    return dest.name


def find_latest_final_mp4(mpt_root: Path, since_mtime: float) -> Path:
    storage = mpt_root / "storage"
    candidates: list[Path] = []
    for path in storage.rglob("final-*.mp4"):
        if path.stat().st_mtime >= since_mtime - 1:
            candidates.append(path)
    if not candidates:
        for path in storage.rglob("*.mp4"):
            if "final" in path.name.lower() and path.stat().st_mtime >= since_mtime - 1:
                candidates.append(path)
    if not candidates:
        raise FileNotFoundError(
            f"MPT não gerou final-*.mp4 em {storage}. "
            "Verifique logs do CLI."
        )
    return max(candidates, key=lambda item: item.stat().st_mtime)


def run_mpt_cli(
    mpt_root: Path,
    subject: str,
    script: str,
    materials: list[Path],
    bgm_name: str | None,
    voice_name: str,
    clip_duration: int,
) -> Path:
    python = resolve_mpt_python(mpt_root)
    materials_arg = ",".join(str(path.resolve()) for path in materials)
    command = [
        str(python),
        "cli.py",
        "--video-subject",
        subject,
        "--video-script",
        script,
        "--video-language",
        "en-US",
        "--video-source",
        "local",
        "--video-materials",
        materials_arg,
        "--video-aspect",
        "9:16",
        "--video-concat-mode",
        "random",
        "--video-transition-mode",
        "fade-in",
        "--video-clip-duration",
        str(clip_duration),
        "--video-count",
        "1",
        "--voice-name",
        voice_name,
        "--voice-volume",
        "1.0",
        "--voice-rate",
        "1.0",
        "--subtitle-enabled",
        "--subtitle-position",
        "bottom",
        "--font-name",
        DEFAULT_SUBTITLE_FONT,
        "--font-size",
        str(DEFAULT_SUBTITLE_SIZE),
        "--text-fore-color",
        "#FFFFFF",
        "--stroke-color",
        "#000000",
        "--stroke-width",
        "2.0",
        "--bgm-volume",
        "0.18",
    ]
    if bgm_name:
        command.extend(["--bgm-type", "custom", "--bgm-file", bgm_name])
    else:
        command.extend(["--bgm-type", "random"])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(mpt_root)
    t0 = time.time()
    print("Rodando MoneyPrinterTurbo CLI (pipeline oficial)...")
    run(command, cwd=mpt_root, env=env)
    return find_latest_final_mp4(mpt_root, t0)


def generate_short(
    production_dir: Path,
    seconds: int = 45,
    width: int = 1080,
    height: int = 1920,
    voice_name: str = DEFAULT_VOICE,
) -> Path:
    del width, height, seconds
    production_dir = production_dir.resolve()
    meta = load_meta(production_dir)
    audio = load_audio_config(production_dir)
    mpt_root = ensure_mpt_ready()
    basename = meta.get("exportBasename", production_dir.name)
    output_dir = production_dir / "exports" / "shorts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{basename}-mpt-9x16.mp4"

    with tempfile.TemporaryDirectory(prefix="mpt-materials-") as temp_dir:
        materials = prepare_materials(production_dir, Path(temp_dir))
        bgm = resolve_bgm(production_dir, audio)
        bgm_name = stage_bgm(mpt_root, bgm)
        script = build_mpt_script(meta)
        subject = f"{meta.get('series', 'Ambience Session')} | {meta.get('mood', 'Focus')}"
        final = run_mpt_cli(
            mpt_root=mpt_root,
            subject=subject,
            script=script,
            materials=materials,
            bgm_name=bgm_name,
            voice_name=voice_name,
            clip_duration=4,
        )
        shutil.copy2(final, output)

    manifest = {
        "productionId": production_dir.name,
        "output": str(output),
        "engine": "moneyprinterturbo-cli",
        "voice": voice_name,
        "script": script,
        "bgm": str(bgm) if bgm else None,
        "mptFinal": str(final),
        "note": (
            "Short gerado pelo CLI oficial do MoneyPrinterTurbo: "
            "script → Edge TTS → legendas → materiais locais → BGM."
        ),
    }
    (output_dir / f"{basename}-mpt-9x16.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Shorts via MoneyPrinterTurbo CLI (aceita 110 / productionId / path)"
    )
    parser.add_argument("selector", nargs="?", default=None)
    parser.add_argument("--production", default=None)
    parser.add_argument("--seconds", type=int, default=45, help="legado; duração vem do TTS")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    args = parser.parse_args()
    selector = args.production or args.selector
    if not selector:
        parser.error("Informe a produção: npm run short:preview -- 110")
    production_dir = resolve_production_dir(str(selector))
    output = generate_short(
        production_dir,
        args.seconds,
        args.width,
        args.height,
        voice_name=args.voice,
    )
    print(
        json.dumps(
            {
                "status": "preview",
                "engine": "moneyprinterturbo-cli",
                "production": str(production_dir),
                "short": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
