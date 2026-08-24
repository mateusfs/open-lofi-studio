#!/usr/bin/env python3
"""Validação objetiva de loudness (LUFS / true peak)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

TARGET_LUFS = -15.0
LUFS_TOLERANCE = 1.5
TRUE_PEAK_MAX = -1.2


def measure_loudness(path: Path) -> tuple[float, float]:
    data, rate = sf.read(str(path), always_2d=True)
    if data.size == 0:
        raise ValueError(f"empty audio: {path}")
    meter = pyln.Meter(rate)
    loudness = float(meter.integrated_loudness(data))
    peak = float(np.max(np.abs(data)))
    true_peak_db = 20.0 * np.log10(max(peak, 1e-12))
    return loudness, true_peak_db


def clamp_true_peak(path: Path, target_db: float = -1.5) -> None:
    data, rate = sf.read(str(path), always_2d=True)
    peak = float(np.max(np.abs(data)))
    if peak <= 0:
        return
    true_peak_db = 20.0 * np.log10(peak)
    if true_peak_db <= target_db:
        return
    gain = 10 ** ((target_db - true_peak_db) / 20.0)
    sf.write(str(path), np.clip(data * gain, -1.0, 1.0), rate)


def assert_mix_loudness(path: Path) -> tuple[float, float]:
    clamp_true_peak(path, target_db=-1.5)
    loudness, true_peak_db = measure_loudness(path)
    if abs(loudness - TARGET_LUFS) > LUFS_TOLERANCE:
        raise RuntimeError(
            f"Loudness fora da faixa: {loudness:.2f} LUFS (alvo {TARGET_LUFS} ± {LUFS_TOLERANCE})"
        )
    if true_peak_db > TRUE_PEAK_MAX:
        raise RuntimeError(
            f"True peak acima do limite: {true_peak_db:.2f} dBTP (máx {TRUE_PEAK_MAX})"
        )
    return loudness, true_peak_db
