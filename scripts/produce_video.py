#!/usr/bin/env python3
"""Pipeline completo de produção para um vídeo Ambience Session."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
DEFAULT_AUDIO_LOOP_SECONDS = 1800

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ambient_presets import default_ambient_loop_seconds, resolve_ambient_effects
from animate_mode import apply_calibration_to_meta, export_loop_seam_frame, resolve_animate_mode
from youtube_metadata import write_youtube_metadata


def resolve_audio_loop_duration(duration: int, preview: int | None) -> int:
    if preview is not None:
        return preview
    return min(DEFAULT_AUDIO_LOOP_SECONDS, duration)


def run_script(script: str, args: list[str]) -> None:
    command = [sys.executable, str(SCRIPTS / script), *args]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed: {script}")


def load_meta(production_dir: Path) -> dict:
    meta_path = production_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"meta.json não encontrado em {production_dir}. "
            "Execute scripts/setup_production.py ou copie templates/production-meta.example.json"
        )
    return json.loads(meta_path.read_text(encoding="utf-8"))


def extract_audio_flac(video_path: Path, flac_path: Path) -> None:
    flac_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-c:a",
            "flac",
            str(flac_path),
        ],
        check=True,
        capture_output=True,
    )


def produce(
    production_dir: Path,
    duration: int,
    preview: int | None = None,
    seed: int | None = None,
    skip_scene: bool = False,
) -> None:
    meta = load_meta(production_dir)
    animate = meta.get("animate", {})
    loop_seed = seed if seed is not None else animate.get("seed", 42)
    scene_effects = animate.get("effects", [])
    has_effect_steam = "steam" in scene_effects
    no_steam = animate.get("noSteam", False) or (bool(scene_effects) and not has_effect_steam)
    steam_decay = (
        animate.get("steamDecay", not no_steam)
        and not no_steam
        and not has_effect_steam
    )
    steam_color = animate.get("steamColor")
    steam_color_arg: list[str] = []
    if steam_color is not None:
        if isinstance(steam_color, (list, tuple)) and len(steam_color) == 3:
            steam_color_csv = ",".join(str(int(channel)) for channel in steam_color)
        else:
            steam_color_csv = str(steam_color)
        steam_color_arg = ["--steam-color", steam_color_csv]

    source = production_dir / "source"
    exports = production_dir / "exports"
    scene_path = source / "scene-base.png"
    loop_path = source / "scene-loop.mp4"
    audio_path = source / "audio-mix.wav"
    thumbnail_path = source / "thumbnail.png"

    target_duration = preview if preview is not None else duration
    basename = meta.get("exportBasename", production_dir.name)
    if preview:
        video_name = f"{basename}-{target_duration}s-preview.mp4"
    else:
        video_name = f"{basename}.mp4"
    video_path = exports / "youtube" / video_name

    if not scene_path.exists():
        raise FileNotFoundError(
            f"Cena base não encontrada: {scene_path}. "
            "Rode via scripts/next.py (generate_scene_ai) ou salve source/scene-base.png."
        )

    animate_mode = resolve_animate_mode(animate)
    if preview and (animate.get("autoSteam", True) or animate.get("autoRain", True)):
        print("Calibração visual (preview)...")
        from calibrate_scene import calibrate_production

        calibration = calibrate_production(production_dir)
        steam = calibration["steam"]
        assert isinstance(steam, dict)
        print(
            f"Vapor detectado: ({steam['detected_x']}, {steam['detected_y']}) "
            f"conf={steam['confidence']} auto={steam['auto']} "
            f"usou_fallback={steam['used_fallback']}"
        )
        meta = apply_calibration_to_meta(production_dir, calibration)
        animate = meta.get("animate", animate)
        no_steam = animate.get("noSteam", False) or (bool(scene_effects) and not has_effect_steam)
        steam_decay = (
            animate.get("steamDecay", not no_steam)
            and not no_steam
            and not has_effect_steam
        )

    if animate_mode == "ambient":
        scene_effects = resolve_ambient_effects(
            str(meta.get("series", "")),
            str(meta.get("mood", "")),
            animate,
        )
        if animate.get("loopSeconds") is None:
            animate = {**animate, "loopSeconds": default_ambient_loop_seconds(animate)}
        has_effect_steam = "steam" in scene_effects
        no_steam = animate.get("noSteam", False) or (bool(scene_effects) and not has_effect_steam)
        steam_decay = (
            animate.get("steamDecay", not no_steam)
            and not no_steam
            and not has_effect_steam
        )
        print(f"Efeitos ambient: {', '.join(scene_effects)}")

    if not skip_scene or not loop_path.exists():
        print("Step 1/4: Animating scene...")
        if animate_mode == "hybrid":
            layers = animate.get("layers", [])
            if not isinstance(layers, list) or not layers:
                raise ValueError("animate.mode=hybrid requer animate.layers não vazio")
            mask_needed = any(
                isinstance(layer, dict) and layer.get("mask")
                for layer in layers
            )
            if mask_needed:
                run_script(
                    "effect_mask.py",
                    [
                        "--scene",
                        str(scene_path),
                        "--output",
                        str(source / "effect-mask.png"),
                    ],
                )
            hybrid_args = [
                "--scene",
                str(scene_path),
                "--output",
                str(loop_path),
                "--production-dir",
                str(production_dir),
                "--layers",
                json.dumps(layers),
                "--seconds",
                str(animate.get("loopSeconds", 54)),
                "--fps",
                str(animate.get("fps", 30)),
                "--seed",
                str(loop_seed),
                "--preset",
                "medium" if preview else "slow",
            ]
            if scene_effects:
                hybrid_args.extend(["--effects", ",".join(scene_effects)])
            if not animate.get("noSteam", False) and (
                "steam" in scene_effects or animate.get("steamX") is not None
            ):
                hybrid_args.extend(
                    [
                        "--steam-x",
                        str(animate.get("steamX", 1010)),
                        "--steam-y",
                        str(animate.get("steamY", 800)),
                        "--steam-scale",
                        str(animate.get("steamScale", 0.45)),
                    ]
                )
                hybrid_args.extend(steam_color_arg)
            run_script("hybrid_effects.py", hybrid_args)
        elif animate_mode == "locked":
            locked_args = [
                "--scene",
                str(scene_path),
                "--output",
                str(loop_path),
                "--seconds",
                str(animate.get("loopSeconds", 30)),
            ]
            run_script("animate_locked.py", locked_args)
        elif animate_mode == "cinematic":
            cinematic_args = [
                "--scene",
                str(scene_path),
                "--output",
                str(loop_path),
                "--zoom",
                str(animate.get("zoom", 0.028)),
                "--pan-x",
                str(animate.get("panX", 26)),
                "--pan-y",
                str(animate.get("panY", 14)),
                "--breathe",
                str(animate.get("breathe", 0.008)),
                "--seconds",
                str(animate.get("loopSeconds", 30)),
            ]
            overlays = animate.get("overlays")
            if overlays is not None:
                cinematic_args.extend(["--overlays", json.dumps(overlays)])
            run_script("animate_cinematic.py", cinematic_args)
        else:
            animate_args = [
                "--scene",
                str(scene_path),
                "--output",
                str(loop_path),
                "--seed",
                str(loop_seed),
                "--steam-x",
                str(animate.get("steamX", 1010)),
                "--steam-y",
                str(animate.get("steamY", 800)),
                "--steam-scale",
                str(animate.get("steamScale", 1.0)),
            ]
            if animate.get("noRain", False):
                animate_args.append("--no-rain")
            if no_steam or steam_decay:
                animate_args.append("--no-steam")
            if not animate.get("autoRain", True):
                animate_args.append("--no-auto-rain")
            if not animate.get("autoSteam", True):
                animate_args.append("--no-auto-steam")
            if scene_effects:
                animate_args.extend(["--effects", ",".join(scene_effects)])
                if not has_effect_steam:
                    animate_args.append("--no-steam")
                if "rain" not in scene_effects:
                    animate_args.append("--no-rain")
            effect_mask_path = source / "effect-mask.png"
            if effect_mask_path.exists():
                animate_args.extend(["--effect-mask", str(effect_mask_path)])
            loop_seconds = animate.get("loopSeconds")
            if loop_seconds is not None:
                animate_args.extend(["--seconds", str(loop_seconds)])
            animate_args.extend(steam_color_arg)
            run_script("animate_scene.py", animate_args)
    else:
        print("Step 1/4: Reusing existing animated loop")

    audio_segment_duration = resolve_audio_loop_duration(duration, preview)

    print(f"Step 2/4: Mixing focus audio ({audio_segment_duration}s loop)...")
    run_script(
        "mix_focus_audio.py",
        [
            "--duration",
            str(audio_segment_duration),
            "--output",
            str(audio_path),
            "--production-dir",
            str(production_dir),
            "--register",
        ],
    )

    print("Step 3/4: Generating thumbnail...")
    thumbnail_args = [
        "--scene",
        str(scene_path),
        "--output",
        str(thumbnail_path),
        "--series",
        meta.get("series", "Ambience Session"),
        "--mood",
        meta.get("mood", "Deep Focus"),
        "--duration",
        meta.get("durationLabel", "3 HOURS"),
        "--brand-dir",
        str(ROOT / "brand"),
    ]
    ambience_hook = meta.get("ambienceHook")
    if ambience_hook:
        thumbnail_args.extend(["--hook", str(ambience_hook)])
    run_script("generate_thumbnail.py", thumbnail_args)
    if preview:
        thumbnail_b_args = [
            "--scene",
            str(scene_path),
            "--output",
            str(source / "thumbnail-b.png"),
            "--series",
            meta.get("series", "Ambience Session"),
            "--mood",
            meta.get("mood", "Deep Focus"),
            "--duration",
            meta.get("durationLabel", "3 HOURS"),
            "--brand-dir",
            str(ROOT / "brand"),
            "--format",
            "short",
        ]
        if ambience_hook:
            thumbnail_b_args.extend(["--hook", str(ambience_hook)])
        run_script("generate_thumbnail.py", thumbnail_b_args)

    queue_video = {
        "series": meta.get("series", "Ambience Session"),
        "mood": meta.get("mood", "Deep Focus"),
        "durationLabel": meta.get("durationLabel", "3 HOURS"),
        "durationSeconds": duration,
        "titleEn": meta.get("titleEn"),
        "youtubeTags": meta.get("youtubeTags"),
        "number": meta.get("number", ""),
    }
    write_youtube_metadata(production_dir, queue_video)

    print(f"Step 4/4: Assembling video ({target_duration}s)...")
    assemble_args = [
        "--visual",
        str(loop_path),
        "--audio",
        str(audio_path),
        "--output",
        str(video_path),
        "--duration",
        str(target_duration),
    ]
    if steam_decay and not no_steam:
        assemble_args.extend(
            [
                "--steam-decay",
                "--scene",
                str(scene_path),
                "--steam-x",
                str(animate.get("steamX", 1010)),
                "--steam-y",
                str(animate.get("steamY", 800)),
                "--seed",
                str(loop_seed),
            ]
        )
        if animate.get("noRain", False):
            assemble_args.append("--no-rain")
        if not animate.get("autoRain", True):
            assemble_args.append("--no-auto-rain")
        if not animate.get("autoSteam", True):
            assemble_args.append("--no-auto-steam")
        assemble_args.extend(steam_color_arg)
    run_script("assemble_video.py", assemble_args)

    if preview:
        seam_path = source / "qa-loop-seam.png"
        export_loop_seam_frame(loop_path, seam_path)
        print(f"QA loop seam: {seam_path}")

    if not preview:
        flac_minutes = max(1, round(audio_segment_duration / 60))
        flac_path = exports / "streaming" / f"{basename}-{flac_minutes}min-loop.flac"
        print("Exporting FLAC loop...")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(audio_path),
                "-c:a",
                "flac",
                str(flac_path),
            ],
            check=True,
            capture_output=True,
        )

    print(f"Done. Video: {video_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline Ambience Session")
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=10800)
    parser.add_argument("--preview", type=int, default=None, help="Gera preview em segundos")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--skip-scene",
        action="store_true",
        help="Reutiliza scene-loop.mp4 existente sem reanimar",
    )
    args = parser.parse_args()
    produce(args.production.resolve(), args.duration, args.preview, args.seed, args.skip_scene)


if __name__ == "__main__":
    main()
