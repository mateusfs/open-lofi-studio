#!/usr/bin/env python3
"""Carrega variáveis do arquivo .env na raiz do projeto."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def load_env(env_path: Path = ENV_PATH) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def ensure_env_file() -> Path:
    if ENV_PATH.exists():
        return ENV_PATH
    example_path = ROOT / ".env.example"
    if example_path.exists():
        ENV_PATH.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    return ENV_PATH
