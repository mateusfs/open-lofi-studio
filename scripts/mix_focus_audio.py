#!/usr/bin/env python3
"""Mixa trilhas CC0 + ambiência (chuva/café) no estilo coding focus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "assets/audio/music-registry.json"
DEFAULT_RAIN = ROOT / "assets/audio/ambience/rain-window.mp3"
DEFAULT_CAFE = ROOT / "assets/audio/ambience/cafe-murmur.mp3"
DEFAULT_WHITE_NOISE = ROOT / "assets/audio/ambience/white-noise.mp3"
DEFAULT_ROOM_TONE = ROOT / "assets/audio/ambience/soft-room-tone.mp3"
CONTINUOUS_FLOOR_VOLUME = 0.04
SILENCE_RMS_THRESHOLD = 0.002
SILENCE_MAX_SECONDS = 0.5

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_loudness import assert_mix_loudness
from audio_registry import MusicRegistryError, register_production, validate_playlist


NAMED_AMBIENCE: dict[str, dict[str, object]] = {
    "roomTone": {
        "file": "assets/audio/ambience/soft-room-tone.mp3",
        "volume": 0.04,
        "highpass": 40,
        "lowpass": 1800,
    },
    "softHiss": {
        "file": "assets/audio/ambience/white-noise.mp3",
        "volume": 0.025,
        "highpass": 80,
        "lowpass": 2200,
    },
    "libraryHall": {
        "file": "assets/audio/ambience/soft-room-tone.mp3",
        "volume": 0.05,
        "highpass": 50,
        "lowpass": 1600,
    },
}


def resolve_named_ambience(config: dict) -> list[dict[str, object]]:
    layers: list[dict[str, object]] = []
    raw_layers = config.get("ambience", [])
    if isinstance(raw_layers, list):
        for layer in raw_layers:
            if not isinstance(layer, dict):
                continue
            name = layer.get("name")
            if isinstance(name, str) and name in NAMED_AMBIENCE and "file" not in layer:
                merged = dict(NAMED_AMBIENCE[name])
                merged.update({key: value for key, value in layer.items() if key != "name"})
                layers.append(merged)
            else:
                layers.append(layer)
    for key, preset in NAMED_AMBIENCE.items():
        if key in config and isinstance(config[key], dict):
            merged = dict(preset)
            merged.update(config[key])
            layers.append(merged)
        elif key in config and isinstance(config[key], (int, float)):
            merged = dict(preset)
            merged["volume"] = float(config[key])
            layers.append(merged)
    return layers


def active_ambience_layer_count(layers: list[dict[str, object]] | None) -> int:
    count = 0
    for layer in layers or []:
        layer_path = Path(str(layer.get("file", "")))
        if not layer_path.is_absolute():
            layer_path = ROOT / layer_path
        if layer_path.exists() and float(layer.get("volume", 0.0)) > 0:
            count += 1
    return count


def ensure_continuous_floor(
    ambience_layers: list[dict[str, object]] | None,
    *,
    has_rain: bool,
    has_cafe: bool,
    has_white_noise: bool,
) -> list[dict[str, object]]:
    layers = list(ambience_layers or [])
    if has_rain or has_cafe or has_white_noise or active_ambience_layer_count(layers) > 0:
        return layers
    if not DEFAULT_ROOM_TONE.exists():
        return layers
    layers.append(
        {
            "file": str(DEFAULT_ROOM_TONE.relative_to(ROOT)),
            "volume": CONTINUOUS_FLOOR_VOLUME,
            "highpass": 40,
            "lowpass": 1800,
            "role": "continuousFloor",
        }
    )
    return layers


SEAMLESS_CROSSFADE_SECONDS = 16.0
MUSIC_SELF_LOOP_SECONDS = 12.0
MUSIC_TRACK_FADE_SECONDS = 2.0
MUSIC_TRACK_GAP_SECONDS = 0.0
MUSIC_CROSSFADE_SECONDS = MUSIC_TRACK_FADE_SECONDS
DEFAULT_MUSIC_VOLUME = 0.065
DEFAULT_CAFE_VOLUME = 0.03
DEFAULT_RAIN_VOLUME = 0.055


def seamless_crossfade_for_duration(duration: float) -> float:
    if duration <= 0:
        return MUSIC_SELF_LOOP_SECONDS
    return min(24.0, max(8.0, float(duration) * 0.045))


def probe_duration_seconds(path: Path) -> float:
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
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr[-1000:]}")
    try:
        return float(result.stdout.strip())
    except ValueError as error:
        raise RuntimeError(f"invalid duration for {path}: {result.stdout!r}") from error


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed: {' '.join(command)}\n{result.stderr[-3000:]}")


def make_edge_fades(source: Path, output: Path, duration: int, fade: float) -> None:
    fade_len = min(fade, max(duration / 8.0, 0.4))
    fade_out_start = max(duration - fade_len, 0.0)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            str(duration),
            "-af",
            f"afade=t=in:st=0:d={fade_len},afade=t=out:st={fade_out_start}:d={fade_len}",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def make_seamless_loop(source: Path, output: Path, duration: int, crossfade: float) -> None:
    if duration <= crossfade * 2:
        make_edge_fades(source, output, duration, min(crossfade, duration / 4.0))
        return
    loop_length = duration - crossfade
    fade_curve = "qsin"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        body = temp / "body.wav"
        tail = temp / "tail.wav"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-af",
                f"atrim=0:{loop_length},asetpts=N/SR/TB,"
                f"afade=t=in:curve={fade_curve}:st=0:d={crossfade}",
                "-c:a",
                "pcm_s16le",
                str(body),
            ]
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-af",
                f"atrim={loop_length}:{duration},asetpts=N/SR/TB,"
                f"afade=t=out:curve={fade_curve}:st=0:d={crossfade}",
                "-c:a",
                "pcm_s16le",
                str(tail),
            ]
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(body),
                "-i",
                str(tail),
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                "alimiter=limit=0.95[out]",
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )


def render_silence(output: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=44100:cl=stereo:d={seconds}",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def render_faded_track(source: Path, output: Path, fade_seconds: float) -> None:
    duration = probe_duration_seconds(source)
    fade_len = min(fade_seconds, max(duration * 0.12, 0.4))
    fade_out_start = max(duration - fade_len, 0.0)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-af",
            "aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo,"
            f"afade=t=in:st=0:d={fade_len},"
            f"afade=t=out:st={fade_out_start}:d={fade_len}",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def concat_audio_files(files: list[Path], output: Path) -> None:
    listing_path = output.parent / "concat-list.txt"
    listing_path.write_text(
        "".join(f"file '{path.resolve()}'\n" for path in files),
        encoding="utf-8",
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing_path),
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    listing_path.unlink(missing_ok=True)


def build_music_playlist(
    music_files: list[Path],
    output: Path,
    fade_seconds: float = MUSIC_TRACK_FADE_SECONDS,
    gap_seconds: float = MUSIC_TRACK_GAP_SECONDS,
) -> None:
    if len(music_files) == 1:
        render_faded_track(music_files[0], output, fade_seconds)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        pieces: list[Path] = []
        gap_path = temp / "gap.wav"
        if gap_seconds > 0:
            render_silence(gap_path, gap_seconds)
        for index, track in enumerate(music_files):
            faded = temp / f"track_{index:02d}.wav"
            render_faded_track(track, faded, fade_seconds)
            pieces.append(faded)
            if gap_seconds > 0 and index < len(music_files) - 1:
                pieces.append(gap_path)
        concat_audio_files(pieces, output)


def make_playlist_loop_ready(playlist: Path, output: Path, music_file_count: int) -> None:
    duration = probe_duration_seconds(playlist)
    crossfade = seamless_crossfade_for_duration(duration)
    if music_file_count <= 1:
        crossfade = max(crossfade, MUSIC_SELF_LOOP_SECONDS)
    make_seamless_loop(playlist, output, int(duration), crossfade)


def assert_no_long_silence(
    path: Path,
    rms_threshold: float = SILENCE_RMS_THRESHOLD,
    max_silent_seconds: float = SILENCE_MAX_SECONDS,
) -> None:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path))
    mono = audio.mean(axis=1) if getattr(audio, "ndim", 1) > 1 else audio
    window = max(1, int(rate * 0.25))
    silent_windows = 0
    needed = max(1, int(max_silent_seconds / 0.25))
    for index in range(0, len(mono) - window + 1, window):
        chunk = mono[index : index + window]
        rms = float(np.sqrt(np.mean(np.square(chunk))))
        if rms < rms_threshold:
            silent_windows += 1
            if silent_windows >= needed:
                raise RuntimeError(
                    f"Silêncio longo detectado em {path} perto de {index / rate:.1f}s "
                    f"(RMS < {rms_threshold})"
                )
        else:
            silent_windows = 0


def mix_focus_audio(
    output: Path,
    duration: int,
    music_files: list[Path],
    rain_file: Path | None,
    cafe_file: Path | None,
    rain_volume: float,
    cafe_volume: float,
    music_volume: float,
    white_noise_file: Path | None = None,
    white_noise_volume: float = 0.0,
    ambience_layers: list[dict[str, object]] | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        playlist = temp / "playlist.wav"
        playlist_loop = temp / "playlist_loop.wav"
        mixed = temp / "mixed.wav"
        build_music_playlist(music_files, playlist)
        make_playlist_loop_ready(playlist, playlist_loop, len(music_files))

        inputs = ["-stream_loop", "-1", "-i", str(playlist_loop)]
        filter_parts = [
            f"[0:a]volume={music_volume},highpass=f=50,lowpass=f=14000[music]"
        ]
        mix_inputs = "[music]"
        input_index = 1

        if rain_file and rain_file.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(rain_file)])
            filter_parts.append(
                f"[{input_index}:a]volume={rain_volume},"
                "highpass=f=200,lowpass=f=2800[rain]"
            )
            mix_inputs += "[rain]"
            input_index += 1

        if cafe_file and cafe_file.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(cafe_file)])
            filter_parts.append(
                f"[{input_index}:a]volume={cafe_volume},"
                "highpass=f=200,lowpass=f=2400[cafe]"
            )
            mix_inputs += "[cafe]"
            input_index += 1

        if white_noise_file and white_noise_file.exists() and white_noise_volume > 0:
            inputs.extend(["-stream_loop", "-1", "-i", str(white_noise_file)])
            filter_parts.append(
                f"[{input_index}:a]volume={white_noise_volume},"
                "highpass=f=80,lowpass=f=1600[noise]"
            )
            mix_inputs += "[noise]"
            input_index += 1

        for layer_index, layer in enumerate(ambience_layers or []):
            layer_path = Path(str(layer.get("file", "")))
            if not layer_path.is_absolute():
                layer_path = ROOT / layer_path
            layer_volume = float(layer.get("volume", 0.0))
            if not layer_path.exists() or layer_volume <= 0:
                continue
            label = f"amb{layer_index}"
            highpass = int(layer.get("highpass", 200))
            lowpass = int(layer.get("lowpass", 10000))
            inputs.extend(["-stream_loop", "-1", "-i", str(layer_path)])
            filter_parts.append(
                f"[{input_index}:a]volume={layer_volume},"
                f"highpass=f={highpass},lowpass=f={lowpass}[{label}]"
            )
            mix_inputs += f"[{label}]"
            input_index += 1

        filter_parts.append(
            f"{mix_inputs}amix=inputs={input_index}:duration=first:dropout_transition=8,"
            "highpass=f=40,lowpass=f=15000,alimiter=limit=0.92,"
            "loudnorm=I=-15:TP=-1.5:LRA=11[out]"
        )

        run(
            [
                "ffmpeg",
                "-y",
                *inputs,
                "-t",
                str(duration),
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(mixed),
            ]
        )

        make_seamless_loop(
            mixed,
            output,
            duration,
            seamless_crossfade_for_duration(float(duration)),
        )

    assert_no_long_silence(output)
    loudness, true_peak = assert_mix_loudness(output)
    print(f"Loudness OK: {loudness:.2f} LUFS, true peak {true_peak:.2f} dBTP")


def load_production_audio_config(production_dir: Path) -> dict:
    config_path = production_dir / "audio.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"audio.json obrigatório em {production_dir}. "
            "Use a playlist do catalog em templates/audio-config.json ou escolha 3-4 faixas novas."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_music_paths(config: dict) -> list[Path]:
    tracks = config.get("tracks", [])
    if not tracks:
        raise ValueError("audio.json deve listar 3-4 faixas em 'tracks'")
    return [(ROOT / track if not Path(track).is_absolute() else Path(track)) for track in tracks]


def main() -> None:
    parser = argparse.ArgumentParser(description="Mixa áudio focus com trilhas CC0")
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--production-id", type=str, default=None, help="ID da produção (ex: 010-rainy-night-tokyo)")
    parser.add_argument("--production-dir", type=Path, default=None, help="Lê tracks de productions/XXX/audio.json")
    parser.add_argument("--music", type=Path, nargs="*", default=None)
    parser.add_argument("--rain", type=Path, default=DEFAULT_RAIN)
    parser.add_argument("--cafe", type=Path, default=DEFAULT_CAFE)
    parser.add_argument("--white-noise", type=Path, default=DEFAULT_WHITE_NOISE)
    parser.add_argument("--rain-volume", type=float, default=None)
    parser.add_argument("--cafe-volume", type=float, default=None)
    parser.add_argument("--white-noise-volume", type=float, default=None)
    parser.add_argument("--music-volume", type=float, default=DEFAULT_MUSIC_VOLUME)
    parser.add_argument("--no-rain", action="store_true")
    parser.add_argument("--no-cafe", action="store_true")
    parser.add_argument("--no-white-noise", action="store_true")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--register", action="store_true", help="Registra faixas no music-registry.json após mix")
    parser.add_argument("--skip-registry", action="store_true", help="Apenas para manutenção legada")
    args = parser.parse_args()

    production_id = args.production_id
    rain_volume = args.rain_volume
    cafe_volume = args.cafe_volume
    white_noise_volume = args.white_noise_volume
    no_rain = args.no_rain
    no_cafe = args.no_cafe
    no_white_noise = args.no_white_noise

    white_noise_path = args.white_noise
    ambience_layers: list[dict[str, object]] = []

    if args.production_dir:
        config = load_production_audio_config(args.production_dir.resolve())
        production_id = production_id or config.get("productionId")
        music_files = resolve_music_paths(config)
        rain_volume = (
            config.get("rainVolume", DEFAULT_RAIN_VOLUME)
            if rain_volume is None
            else rain_volume
        )
        cafe_volume = (
            config.get("cafeVolume", DEFAULT_CAFE_VOLUME)
            if cafe_volume is None
            else cafe_volume
        )
        white_noise_volume = (
            config.get("whiteNoiseVolume", 0.0)
            if white_noise_volume is None
            else white_noise_volume
        )
        no_rain = config.get("noRain", False) or no_rain
        no_cafe = config.get("noCafe", False) or no_cafe
        no_white_noise = config.get("noWhiteNoise", white_noise_volume <= 0) or no_white_noise
        custom_white = config.get("whiteNoiseFile")
        if custom_white:
            white_noise_path = Path(str(custom_white))
            if not white_noise_path.is_absolute():
                white_noise_path = ROOT / white_noise_path
        ambience_layers = resolve_named_ambience(config)
        music_volume = float(config.get("musicVolume", DEFAULT_MUSIC_VOLUME))
    elif args.music:
        music_files = [path.resolve() for path in args.music]
        music_volume = args.music_volume
    else:
        raise ValueError(
            "Informe --production-dir ou --music. "
            "Cada vídeo precisa de playlist única — ver assets/audio/music-registry.json"
        )

    if "music_volume" not in locals():
        music_volume = args.music_volume

    music_files = [path for path in music_files if path.exists()]
    if not music_files:
        raise FileNotFoundError("Nenhuma trilha musical encontrada. Baixe faixas novas do open-lofi.")

    if not args.skip_registry:
        if not production_id:
            raise ValueError("--production-id ou productionId em audio.json é obrigatório")
        validate_playlist(production_id, music_files, args.registry)

    resolved_white_noise_volume = white_noise_volume if white_noise_volume is not None else 0.0
    has_rain = not no_rain and args.rain.exists()
    has_cafe = not no_cafe and args.cafe.exists()
    has_white_noise = (
        not no_white_noise
        and white_noise_path.exists()
        and resolved_white_noise_volume > 0
    )
    ambience_layers = ensure_continuous_floor(
        ambience_layers,
        has_rain=has_rain,
        has_cafe=has_cafe,
        has_white_noise=has_white_noise,
    )
    mix_focus_audio(
        args.output,
        args.duration,
        music_files,
        args.rain if has_rain else None,
        args.cafe if has_cafe else None,
        rain_volume if rain_volume is not None else DEFAULT_RAIN_VOLUME,
        cafe_volume if cafe_volume is not None else DEFAULT_CAFE_VOLUME,
        music_volume,
        white_noise_path if has_white_noise else None,
        resolved_white_noise_volume,
        ambience_layers,
    )

    if args.register and production_id and not args.skip_registry:
        register_production(production_id, music_files, args.registry)

    ambience_manifest = []
    for layer in ambience_layers:
        layer_path = Path(str(layer.get("file", "")))
        if not layer_path.is_absolute():
            layer_path = ROOT / layer_path
        if layer_path.exists() and float(layer.get("volume", 0.0)) > 0:
            ambience_manifest.append(
                {
                    "file": str(layer_path),
                    "volume": float(layer.get("volume", 0.0)),
                }
            )

    manifest = {
        "productionId": production_id,
        "music": [str(path) for path in music_files],
        "rain": str(args.rain) if not no_rain else None,
        "cafe": str(args.cafe) if not no_cafe else None,
        "whiteNoise": (
            str(white_noise_path)
            if not no_white_noise and resolved_white_noise_volume > 0
            else None
        ),
        "ambience": ambience_manifest,
        "license": "CC0 (open-lofi) + Mixkit License",
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Audio saved: {args.output} ({args.duration}s)")


if __name__ == "__main__":
    main()
