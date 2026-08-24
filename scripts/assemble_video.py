#!/usr/bin/env python3
"""Monta vídeo longo a partir de um loop animado (ou imagem) e trilha de áudio."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from animate_scene import (
    DEFAULT_STEAM_COLOR,
    LOOP_SECONDS,
    encode_loop,
    parse_steam_color,
    steam_scale_for_progress,
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
STEAM_DECAY_MIN_SEGMENTS = 8
STEAM_DECAY_MAX_SEGMENTS = 12
STEAM_DECAY_SECONDS_PER_SEGMENT = 3600
VIDEO_LOOP_CROSSFADE_SECONDS = 1.0
SEAMLESS_VIDEO_MAX_SOURCE_SECONDS = 120.0


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stderr[-2000:]}")


def get_duration(media_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def make_seamless_video_loop(
    source: Path,
    output: Path,
    crossfade: float = VIDEO_LOOP_CROSSFADE_SECONDS,
) -> Path:
    duration = get_duration(source)
    if duration > SEAMLESS_VIDEO_MAX_SOURCE_SECONDS:
        return source
    if duration <= crossfade * 2 + 0.25:
        return source
    overlap = min(crossfade, duration / 3.0)
    loop_length = duration - overlap
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            (
                f"[0:v]trim=0:{loop_length:.3f},setpts=PTS-STARTPTS[body];"
                f"[0:v]trim={loop_length:.3f}:{duration:.3f},setpts=PTS-STARTPTS[tail];"
                f"[tail][body]xfade=transition=fade:duration={overlap:.3f}:offset=0,"
                "format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


def image_to_loop(scene_path: Path, loop_path: Path, seconds: int, fps: int) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(scene_path),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-t",
            str(seconds),
            "-an",
            str(loop_path),
        ]
    )


def loop_and_mux(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    duration: int,
) -> None:
    audio_duration = get_duration(audio_path)
    audio_input: list[str] = (
        ["-stream_loop", "-1", "-i", str(audio_path)]
        if audio_duration < duration - 0.5
        else ["-i", str(audio_path)]
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        seamless_path = Path(temp_dir) / "seamless-loop.mp4"
        visual = make_seamless_video_loop(video_path, seamless_path)
        run_command(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(visual),
                *audio_input,
                "-t",
                str(duration),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-af",
                "afade=t=in:st=0:d=2,highpass=f=40,lowpass=f=12000,alimiter=limit=0.95",
                str(output_path),
            ]
        )


def steam_decay_segment_count(duration: int) -> int:
    estimated = duration // STEAM_DECAY_SECONDS_PER_SEGMENT
    if estimated < 1:
        return 1
    return max(
        STEAM_DECAY_MIN_SEGMENTS,
        min(STEAM_DECAY_MAX_SEGMENTS, estimated),
    )


def concat_videos(video_paths: list[Path], output_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as concat_file:
        concat_path = Path(concat_file.name)
        for video_path in video_paths:
            concat_file.write(f"file '{video_path.resolve()}'\n")

    try:
        run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c:v",
                "copy",
                "-an",
                str(output_path),
            ]
        )
    finally:
        concat_path.unlink(missing_ok=True)


def extend_loop(loop_path: Path, output_path: Path, duration: float) -> None:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(loop_path),
            "-t",
            f"{duration:.6f}",
            "-c:v",
            "copy",
            "-an",
            str(output_path),
        ]
    )


def build_steam_decay_visual(
    scene_path: Path,
    output_path: Path,
    duration: int,
    steam_x: int,
    steam_y: int,
    seed: int,
    rain: bool,
    auto_rain: bool,
    auto_steam: bool,
    temp_dir: Path,
    steam_color: tuple[int, int, int] = DEFAULT_STEAM_COLOR,
) -> None:
    segments = steam_decay_segment_count(duration)
    segment_duration = duration / segments
    segment_paths: list[Path] = []

    for index in range(segments):
        progress = index / max(segments - 1, 1) if segments > 1 else 0.0
        steam_scale = steam_scale_for_progress(progress)
        loop_path = temp_dir / f"steam-loop-{index:03d}.mp4"
        segment_path = temp_dir / f"steam-segment-{index:03d}.mp4"
        encode_loop(
            scene_path,
            loop_path,
            steam_x,
            steam_y,
            seed + index,
            rain=rain,
            steam=True,
            auto_rain=auto_rain,
            auto_steam=auto_steam,
            steam_scale=steam_scale,
            steam_color=steam_color,
        )
        extend_loop(loop_path, segment_path, segment_duration)
        segment_paths.append(segment_path)

    concat_videos(segment_paths, output_path)


def assemble_video(
    visual_path: Path,
    audio_path: Path,
    output_path: Path,
    duration: int | None = None,
    fps: int = 24,
    steam_decay: bool = False,
    scene_path: Path | None = None,
    steam_x: int = 1010,
    steam_y: int = 800,
    seed: int = 42,
    rain: bool = True,
    auto_rain: bool = True,
    auto_steam: bool = True,
    steam_color: tuple[int, int, int] = DEFAULT_STEAM_COLOR,
) -> None:
    audio_duration = int(get_duration(audio_path))
    target_duration = duration if duration is not None else audio_duration
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)

        if steam_decay:
            if scene_path is None:
                raise ValueError("scene_path é obrigatório com --steam-decay")
            visual_track = temp_root / "steam-decay-visual.mp4"
            build_steam_decay_visual(
                scene_path,
                visual_track,
                target_duration,
                steam_x,
                steam_y,
                seed,
                rain,
                auto_rain,
                auto_steam,
                temp_root,
                steam_color=steam_color,
            )
            loop_path = visual_track
        elif visual_path.suffix.lower() in VIDEO_EXTENSIONS:
            loop_path = visual_path
        else:
            loop_path = temp_root / "loop.mp4"
            image_to_loop(visual_path, loop_path, min(LOOP_SECONDS, target_duration), fps)

        loop_and_mux(loop_path, audio_path, output_path, target_duration)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta vídeo Ambience Session")
    parser.add_argument(
        "--visual",
        type=Path,
        required=True,
        help="Loop animado (mp4) ou imagem estática (png)",
    )
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=None, help="Duração em segundos")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--steam-decay", action="store_true")
    parser.add_argument("--scene", type=Path, default=None)
    parser.add_argument("--steam-x", type=int, default=1010)
    parser.add_argument("--steam-y", type=int, default=800)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-rain", action="store_true")
    parser.add_argument("--no-auto-rain", action="store_true")
    parser.add_argument("--no-auto-steam", action="store_true")
    parser.add_argument(
        "--steam-color",
        type=str,
        default=None,
        help="Cor RGB do vapor (ex: 200,148,110)",
    )
    args = parser.parse_args()

    assemble_video(
        args.visual,
        args.audio,
        args.output,
        args.duration,
        args.fps,
        steam_decay=args.steam_decay,
        scene_path=args.scene,
        steam_x=args.steam_x,
        steam_y=args.steam_y,
        seed=args.seed,
        rain=not args.no_rain,
        auto_rain=not args.no_auto_rain,
        auto_steam=not args.no_auto_steam,
        steam_color=parse_steam_color(args.steam_color),
    )
    print(f"Video saved: {args.output}")


if __name__ == "__main__":
    main()
