#!/usr/bin/env python3
"""Soundscape Ambience Session: chuva suave, murmúrio de café, lo-fi de foco."""

from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
LOOP_SECONDS = 180
TARGET_LUFS = -15.0
BPM = 74


def write_wav_stereo(path: Path, left: np.ndarray, right: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    left = np.clip(left, -1.0, 1.0)
    right = np.clip(right, -1.0, 1.0)
    interleaved = np.empty(left.size * 2, dtype=np.int16)
    interleaved[0::2] = (left * 32767).astype(np.int16)
    interleaved[1::2] = (right * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(interleaved.tobytes())


def fft_bandpass(signal: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(signal.size, 1 / SAMPLE_RATE)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    spectrum *= mask
    return np.fft.irfft(spectrum, signal.size)


def fft_lowpass(signal: np.ndarray, cutoff_hz: float) -> np.ndarray:
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(signal.size, 1 / SAMPLE_RATE)
    spectrum[freqs > cutoff_hz] = 0
    return np.fft.irfft(spectrum, signal.size)


def pink_noise(length: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(0, 1, length)
    spectrum = np.fft.rfft(white)
    frequencies = np.arange(spectrum.size, dtype=np.float64)
    weights = np.ones_like(frequencies)
    weights[1:] = 1.0 / np.sqrt(frequencies[1:])
    colored = np.fft.irfft(spectrum * weights, n=length)
    peak = np.max(np.abs(colored))
    return colored / peak if peak > 0 else colored


def brown_noise(length: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(0, 1, length)
    brown = np.cumsum(white)
    brown -= np.mean(brown)
    peak = np.max(np.abs(brown))
    return brown / peak if peak > 0 else brown


def seamless_crossfade(signal: np.ndarray, crossfade_samples: int) -> np.ndarray:
    if crossfade_samples <= 0:
        return signal
    fade_out = np.linspace(1.0, 0.0, crossfade_samples)
    fade_in = 1.0 - fade_out
    result = signal.copy()
    result[:crossfade_samples] = (
        signal[:crossfade_samples] * fade_in + signal[-crossfade_samples:] * fade_out
    )
    result[-crossfade_samples:] = (
        signal[-crossfade_samples:] * fade_out + signal[:crossfade_samples] * fade_in
    )
    return result


def conversation_envelope(length: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(length) / SAMPLE_RATE
    env = np.zeros(length, dtype=np.float64)
    for rate in rng.uniform(0.08, 0.25, 4):
        env += 0.25 + 0.75 * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t + rng.uniform(0, 6.28)))
    env /= env.max() if env.max() > 0 else 1.0
    for rate in rng.uniform(2.5, 5.5, 3):
        env *= 0.65 + 0.35 * np.sin(2 * np.pi * rate * t / 60 + rng.uniform(0, 6.28))
    return fft_lowpass(env, 3.0)


def generate_rain_on_window(
    length: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(length) / SAMPLE_RATE
    hiss_l = fft_bandpass(brown_noise(length, rng), 200, 2200)
    hiss_r = fft_bandpass(brown_noise(length, rng), 220, 2400)
    intensity = 0.7 + 0.3 * np.sin(2 * np.pi * 0.035 * t)
    return hiss_l * intensity * 0.1, hiss_r * intensity * 0.1


def generate_cafe_murmur(
    length: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(length) / SAMPLE_RATE
    cluster = conversation_envelope(length, rng)
    murmur_l = np.zeros(length, dtype=np.float64)
    murmur_r = np.zeros(length, dtype=np.float64)

    bands = [(180, 700), (250, 900), (300, 1100), (400, 1300), (500, 1500), (350, 1000)]
    for low_hz, high_hz in bands:
        voice = fft_bandpass(pink_noise(length, rng), low_hz, high_hz)
        syllable_rate = rng.uniform(3.5, 6.0)
        syllables = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_rate * t + rng.uniform(0, 6.28))
        signal = voice * syllables * cluster * 0.018
        pan = rng.uniform(-0.35, 0.35)
        murmur_l += signal * (0.5 - pan)
        murmur_r += signal * (0.5 + pan)

    return fft_lowpass(murmur_l, 2400), fft_lowpass(murmur_r, 2400)


def rhodes_tone(frequency: float, t: np.ndarray) -> np.ndarray:
    tone = np.sin(2 * np.pi * frequency * t) * 0.55
    tone += np.sin(2 * np.pi * frequency * 2 * t) * 0.22
    tone += np.sin(2 * np.pi * frequency * 3 * t) * 0.1
    return tone


def generate_lofi_focus(length: int, duration_seconds: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(length) / SAMPLE_RATE
    progression = [
        [130.81, 155.56, 196.0, 233.08],
        [174.61, 207.65, 261.63, 311.13],
        [196.0, 246.94, 293.66, 349.23],
        [220.0, 261.63, 329.63, 392.0],
    ]
    bar_seconds = duration_seconds / len(progression)
    music = np.zeros(length, dtype=np.float64)
    beat_interval = 60.0 / BPM

    for chord_index, chord in enumerate(progression):
        start = int(chord_index * bar_seconds * SAMPLE_RATE)
        end = int((chord_index + 1) * bar_seconds * SAMPLE_RATE)
        if end > length:
            end = length
        segment_t = t[start:end] - t[start]
        chord_pad = sum(rhodes_tone(freq, segment_t) for freq in chord) / len(chord)
        attack = np.minimum(segment_t / 2.0, 1.0)
        release = np.minimum((bar_seconds - segment_t) / 2.5, 1.0)
        chord_pad *= attack * release

        bass = np.sin(2 * np.pi * (chord[0] / 2) * segment_t) * 0.16
        bass = fft_lowpass(bass, 140)

        beat_phase = (segment_t % beat_interval) / beat_interval
        kick = np.sin(2 * np.pi * 58 * segment_t) * np.exp(-beat_phase * 22) * 0.065
        hat_noise = fft_bandpass(pink_noise(segment_t.size, rng), 5000, 12000)
        hat = hat_noise * (np.exp(-beat_phase * 35) * 0.014 + np.exp(-((beat_phase - 0.5) % 1.0) * 35) * 0.01)

        music[start:end] = chord_pad * 0.06 + bass * 0.045 + kick + hat

    return fft_lowpass(music, 3200)


def normalize_lufs(left: np.ndarray, right: np.ndarray, target: float) -> tuple[np.ndarray, np.ndarray]:
    mono = (left + right) / 2.0
    rms = np.sqrt(np.mean(mono**2))
    if rms <= 0:
        return left, right
    gain = 10 ** ((target - 20 * np.log10(rms)) / 20)
    return np.clip(left * gain, -0.92, 0.92), np.clip(right * gain, -0.92, 0.92)


def mix_segment(duration_seconds: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    length = int(duration_seconds * SAMPLE_RATE)

    rain_l, rain_r = generate_rain_on_window(length, rng)
    murmur_l, murmur_r = generate_cafe_murmur(length, rng)
    focus = generate_lofi_focus(length, duration_seconds, rng)

    left = rain_l + murmur_l + focus
    right = rain_r + murmur_r + focus * 0.99

    crossfade = int(5 * SAMPLE_RATE)
    left = seamless_crossfade(left, crossfade)
    right = seamless_crossfade(right, crossfade)
    return normalize_lufs(left, right, TARGET_LUFS)


def generate_audio(output: Path, duration: int, seed: int) -> None:
    segment_duration = min(duration, LOOP_SECONDS)
    left, right = mix_segment(float(segment_duration), seed)
    write_wav_stereo(output, left, right)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera soundscape Ambience Session")
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_audio(args.output, args.duration, args.seed)
    print(
        f"Audio saved: {args.output} ({args.duration}s) "
        "[rain + cafe murmur + lofi focus]"
    )


if __name__ == "__main__":
    main()
