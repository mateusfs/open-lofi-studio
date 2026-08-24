#!/usr/bin/env python3
"""Retorna o próximo vídeo da fila e atualiza status."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "assets/production-queue.json"


def load_queue() -> dict:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def save_queue(data: dict) -> None:
    data["updatedAt"] = datetime.now(UTC).strftime("%Y-%m-%d")
    QUEUE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def find_video(data: dict, production_id: str | None) -> dict | None:
    for video in data.get("videos", []):
        if production_id and video.get("productionId") == production_id:
            return video
        if not production_id and video.get("status") == "planejado":
            return video
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fila de produção Ambience Session")
    parser.add_argument("--json", action="store_true", help="Imprime próximo vídeo como JSON")
    parser.add_argument("--claim", action="store_true", help="Marca próximo como em produção")
    parser.add_argument("--complete", type=str, help="Marca productionId como produzido")
    parser.add_argument("--id", type=str, help="Busca vídeo específico por productionId")
    args = parser.parse_args()

    data = load_queue()
    video = find_video(data, args.id)
    if not video:
        raise SystemExit("Nenhum vídeo planejado na fila.")

    if args.claim:
        for entry in data["videos"]:
            if entry["productionId"] == video["productionId"]:
                entry["status"] = "em produção"
                break
        save_queue(data)

    if args.complete:
        for entry in data["videos"]:
            if entry["productionId"] == args.complete:
                entry["status"] = "produzido"
                break
        save_queue(data)
        print(f"Marcado como produzido: {args.complete}")
        return

    if args.json:
        print(json.dumps(video, indent=2))
    else:
        print(f"{video['number']} — {video['titleEn']} ({video['productionId']})")


if __name__ == "__main__":
    main()
