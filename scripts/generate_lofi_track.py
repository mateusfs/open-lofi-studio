#!/usr/bin/env python3
"""Gera faixas lo-fi originais quando o pool CC0 acaba (OpenAI + síntese local)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from load_env import load_env

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets/audio/music"
STATE_PATH = ROOT / "assets/audio/.cache/music-packs-state.json"
LICENSES_PATH = ROOT / "assets/audio/LICENSES.md"
SAMPLE_RATE = 44100
DEFAULT_DURATION_SECONDS = 96.0
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
ADJECTIVES = (
    "amber",
    "quiet",
    "midnight",
    "graphite",
    "velvet",
    "paper",
    "slow",
    "warm",
    "dusty",
    "soft",
)
NOUNS = (
    "window",
    "keys",
    "harbor",
    "lantern",
    "notebook",
    "overpass",
    "kettle",
    "static",
    "corridor",
    "ember",
)


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((float(midi) - 69.0) / 12.0))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "focus-loop"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"importedPackIds": [], "generatedTrackSerial": 0}
    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    payload.setdefault("importedPackIds", [])
    payload.setdefault("generatedTrackSerial", 0)
    return payload


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def next_serial(state: dict | None = None) -> int:
    current = state if state is not None else load_state()
    serial = int(current.get("generatedTrackSerial", 0)) + 1
    current["generatedTrackSerial"] = serial
    save_state(current)
    return serial


def unique_slug(title: str, serial: int, music_dir: Path) -> str:
    base = slugify(title)
    candidate = f"csc-{base}-{serial:04d}"
    if not (music_dir / f"{candidate}.mp3").exists():
        return candidate
    suffix = 2
    while True:
        candidate = f"csc-{base}-{serial:04d}-{suffix}"
        if not (music_dir / f"{candidate}.mp3").exists():
            return candidate
        suffix += 1


def fallback_recipe(serial: int, existing_titles: set[str]) -> dict:
    adjective = ADJECTIVES[(serial - 1) % len(ADJECTIVES)]
    noun = NOUNS[((serial - 1) // len(ADJECTIVES)) % len(NOUNS)]
    title = f"{adjective}-{noun}"
    if title in existing_titles:
        title = f"{title}-{serial}"
    root = 48 + (serial % 12)
    offsets = (
        (0, 3, 7, 10),
        (5, 8, 12, 15),
        (7, 10, 14, 17),
        (3, 7, 10, 14),
    )
    shift = serial % 5
    chords = [
        [root + note + shift for note in chord]
        for chord in offsets
    ]
    return {
        "title": title,
        "bpm": 68 + (serial % 16),
        "midiChords": chords,
        "swing": 0.06 + (serial % 7) * 0.01,
        "warmth": 0.35 + (serial % 5) * 0.08,
        "hatAmount": 0.012 + (serial % 6) * 0.002,
        "vinylAmount": 0.008 + (serial % 4) * 0.002,
        "seed": 10_000 + serial,
    }


def normalize_recipe(raw: dict, serial: int) -> dict:
    fallback = fallback_recipe(serial, set())
    title = slugify(str(raw.get("title", fallback["title"])))
    bpm = int(raw.get("bpm", fallback["bpm"]))
    bpm = min(92, max(64, bpm))
    chords_raw = raw.get("midiChords", fallback["midiChords"])
    chords: list[list[int]] = []
    if isinstance(chords_raw, list):
        for chord in chords_raw:
            if not isinstance(chord, list) or len(chord) < 3:
                continue
            notes = [int(note) for note in chord if isinstance(note, (int, float))]
            notes = [min(84, max(36, note)) for note in notes[:5]]
            if len(notes) >= 3:
                chords.append(notes)
    if len(chords) < 3:
        chords = fallback["midiChords"]
    return {
        "title": title,
        "bpm": bpm,
        "midiChords": chords[:6],
        "swing": float(min(0.18, max(0.0, raw.get("swing", fallback["swing"])))),
        "warmth": float(min(0.85, max(0.2, raw.get("warmth", fallback["warmth"])))),
        "hatAmount": float(min(0.04, max(0.006, raw.get("hatAmount", fallback["hatAmount"])))),
        "vinylAmount": float(
            min(0.03, max(0.0, raw.get("vinylAmount", fallback["vinylAmount"])))
        ),
        "seed": int(raw.get("seed", fallback["seed"])),
    }


def recipe_from_openai(serial: int) -> dict | None:
    load_env()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    prompt = (
        "Create one original instrumental lo-fi hip-hop bed for coding ambience. "
        "No vocals, no lyrics, no copyrighted melody. Return JSON only with keys: "
        "title (short kebab-case english, 2-4 words), bpm (64-88 integer), "
        "midiChords (array of 4 chords, each 4 MIDI notes between 40 and 76), "
        f"swing (0-0.16), warmth (0.25-0.8), hatAmount (0.008-0.03), vinylAmount (0.004-0.02). "
        f"Make it unique for serial {serial}."
    )
    payload = json.dumps(
        {
            "model": model,
            "temperature": 1.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You design unique royalty-free lo-fi instrumentals as JSON recipes.",
                },
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_CHAT_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "OpenLofiStudio/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
        print(f"OpenAI receita musical indisponível ({error}). Usando síntese local.")
        return None
    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content")
    if not isinstance(content, str):
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    parsed["seed"] = 20_000 + serial
    return normalize_recipe(parsed, serial)


def resolve_recipe(serial: int) -> dict:
    openai_recipe = recipe_from_openai(serial)
    if openai_recipe is not None:
        print(f"Receita OpenAI: {openai_recipe['title']} ({openai_recipe['bpm']} BPM)")
        return openai_recipe
    recipe = fallback_recipe(serial, set())
    print(f"Receita local: {recipe['title']} ({recipe['bpm']} BPM)")
    return recipe


def pink_noise(length: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(0, 1, length)
    spectrum = np.fft.rfft(white)
    frequencies = np.arange(spectrum.size, dtype=np.float64)
    weights = np.ones_like(frequencies)
    weights[1:] = 1.0 / np.sqrt(frequencies[1:])
    colored = np.fft.irfft(spectrum * weights, n=length)
    peak = np.max(np.abs(colored))
    return colored / peak if peak > 0 else colored


def fft_lowpass(signal: np.ndarray, cutoff_hz: float) -> np.ndarray:
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(signal.size, 1 / SAMPLE_RATE)
    spectrum[freqs > cutoff_hz] = 0
    return np.fft.irfft(spectrum, signal.size)


def fft_bandpass(signal: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(signal.size, 1 / SAMPLE_RATE)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    spectrum *= mask
    return np.fft.irfft(spectrum, signal.size)


def rhodes_tone(frequency: float, t: np.ndarray, warmth: float) -> np.ndarray:
    tone = np.sin(2 * np.pi * frequency * t)
    tone += np.sin(2 * np.pi * frequency * 2 * t) * (0.18 + warmth * 0.12)
    tone += np.sin(2 * np.pi * frequency * 3 * t) * 0.06
    return tone


def synthesize_recipe(recipe: dict, duration_seconds: float) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(recipe["seed"]))
    length = int(duration_seconds * SAMPLE_RATE)
    t = np.arange(length) / SAMPLE_RATE
    chords = recipe["midiChords"]
    bar_seconds = duration_seconds / len(chords)
    bpm = float(recipe["bpm"])
    beat_interval = 60.0 / bpm
    swing = float(recipe["swing"])
    warmth = float(recipe["warmth"])
    hat_amount = float(recipe["hatAmount"])
    vinyl_amount = float(recipe["vinylAmount"])
    left = np.zeros(length, dtype=np.float64)
    right = np.zeros(length, dtype=np.float64)

    for chord_index, chord in enumerate(chords):
        start = int(chord_index * bar_seconds * SAMPLE_RATE)
        end = int((chord_index + 1) * bar_seconds * SAMPLE_RATE)
        if end > length:
            end = length
        segment_t = t[start:end] - t[start]
        freqs = [midi_to_hz(note) for note in chord]
        pad = sum(rhodes_tone(freq, segment_t, warmth) for freq in freqs) / len(freqs)
        attack = np.minimum(segment_t / 1.8, 1.0)
        release = np.minimum((bar_seconds - segment_t) / 2.2, 1.0)
        pad *= attack * np.maximum(release, 0.05)
        bass = np.sin(2 * np.pi * (freqs[0] / 2.0) * segment_t) * 0.22
        bass = fft_lowpass(bass, 130)
        beat_phase = (segment_t % beat_interval) / beat_interval
        swung = (beat_phase + swing * np.sin(2 * np.pi * beat_phase)) % 1.0
        kick = np.sin(2 * np.pi * 54 * segment_t) * np.exp(-swung * 18) * 0.08
        hat_noise = fft_bandpass(pink_noise(segment_t.size, rng), 4500, 11000)
        hat = hat_noise * (
            np.exp(-swung * 28) * hat_amount
            + np.exp(-((swung - 0.5) % 1.0) * 28) * hat_amount * 0.7
        )
        mix = pad * (0.11 + warmth * 0.04) + bass + kick + hat
        detune = np.sin(2 * np.pi * (freqs[0] * 1.003) * segment_t) * 0.02
        left[start:end] += mix
        right[start:end] += mix * 0.97 + detune

    vinyl = pink_noise(length, rng)
    clicks = rng.random(length) < 0.0008
    crackle = fft_bandpass(vinyl, 800, 6000) * vinyl_amount
    click_count = int(np.count_nonzero(clicks))
    if click_count:
        crackle[clicks] += rng.uniform(-0.08, 0.08, click_count)
    left += crackle
    right += crackle * 0.92

    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-9)
    gain = 0.86 / peak
    return np.clip(left * gain, -0.92, 0.92), np.clip(right * gain, -0.92, 0.92)


def write_wav_stereo(path: Path, left: np.ndarray, right: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved = np.empty(left.size * 2, dtype=np.int16)
    interleaved[0::2] = (left * 32767).astype(np.int16)
    interleaved[1::2] = (right * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(interleaved.tobytes())


def encode_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(mp3_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not mp3_path.exists() or mp3_path.stat().st_size < 8_000:
        raise RuntimeError(f"ffmpeg falhou ao gerar MP3: {result.stderr[-1000:]}")


def append_generated_license(slugs: list[str]) -> None:
    if not slugs or not LICENSES_PATH.exists():
        return
    marker = "## Original procedural `csc-lofi`"
    text = LICENSES_PATH.read_text(encoding="utf-8")
    note = f"- {', '.join(slugs)} ({time.strftime('%Y-%m-%d')})\n"
    if marker not in text:
        block = (
            f"\n{marker}\n\n"
            "Faixas originais sintetizadas localmente a partir de receita OpenAI "
            "(ou fallback procedural). Uso comercial do projeto, sem Content ID de terceiros.\n\n"
            f"{note}"
        )
        LICENSES_PATH.write_text(text + block, encoding="utf-8")
        return
    if any(slug in text for slug in slugs):
        return
    LICENSES_PATH.write_text(text + note, encoding="utf-8")


def generate_unique_tracks(
    count: int,
    music_dir: Path | None = None,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
) -> list[str]:
    if count <= 0:
        return []
    music_dir = music_dir or MUSIC_DIR
    music_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    for _ in range(count):
        serial = next_serial()
        recipe = resolve_recipe(serial)
        slug = unique_slug(str(recipe["title"]), serial, music_dir)
        dest = music_dir / f"{slug}.mp3"
        left, right = synthesize_recipe(recipe, duration_seconds)
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / f"{slug}.wav"
            write_wav_stereo(wav_path, left, right)
            encode_wav_to_mp3(wav_path, dest)
        generated.append(slug)
        print(f"Faixa original gerada: {dest.name}")
    append_generated_license(generated)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera faixas lo-fi originais")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_SECONDS)
    args = parser.parse_args()
    slugs = generate_unique_tracks(args.count, duration_seconds=args.duration)
    print(json.dumps({"generated": slugs}, indent=2))


if __name__ == "__main__":
    main()
