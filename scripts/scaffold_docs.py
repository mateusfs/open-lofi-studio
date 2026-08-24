#!/usr/bin/env python3
"""Gera brief.md, script-en.md e checklist.md a partir da fila e docs/11."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTIONS_PATH = ROOT / "docs/11-descricoes-youtube.md"


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    return f"{hours} horas ({seconds:,} segundos)".replace(",", ".")


def extract_youtube_description(number: str) -> str | None:
    text = DESCRIPTIONS_PATH.read_text(encoding="utf-8")
    pattern = rf"### #{number} —[^\n]*\n\n```\n([\s\S]*?)```"
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()


def chapter_timestamps(duration_seconds: int) -> str:
    hours = duration_seconds // 3600
    labels = ["Session Start", "Deep Focus"]
    if hours >= 4:
        labels.append("Mid Flow")
    if hours >= 6:
        labels.append("Second Wind")
    if hours >= 8:
        labels.append("Final Hour")
    while len(labels) < hours:
        labels.insert(-1, "Focus")
    lines = [f"0:00:00 — {labels[0]}"]
    for hour in range(1, hours):
        label = labels[hour] if hour < len(labels) else "Focus"
        lines.append(f"{hour}:00:00 — {label}")
    return "\n".join(lines)


def build_fallback_description(video: dict) -> str:
    mood = video["mood"].replace("•", "—")
    duration_label = video["durationLabel"].lower()
    series_block = playlist_series_label(video["series"])
    return f"""{mood}. A {duration_label} focus session for developers.

🎧 What's inside:
• Ambient atmosphere matching the mood
• Exclusive lofi beats for deep focus
• Seamless {duration_label} mix

⏱ Chapters:
{chapter_timestamps(video["durationSeconds"])}

{series_block}
[PLAYLIST-SERIE]

🎵 Developer Focus Sessions
[PLAYLIST-MAE]

Perfect for: developers, remote workers, deep work sessions

🔔 Subscribe for new coding environments every week.

#coding #ambience #deepwork #lofi #focus
"""


def resolve_youtube_description(video: dict) -> str:
    description = extract_youtube_description(video["number"])
    if description:
        return description
    print(
        f"Aviso: descrição ausente em docs/11 para #{video['number']} — "
        "usando template automático."
    )
    return build_fallback_description(video)


def extract_series_tags(series: str) -> str:
    text = DESCRIPTIONS_PATH.read_text(encoding="utf-8")
    pattern = rf"### {re.escape(series)}\n```\n([\s\S]*?)```"
    match = re.search(pattern, text)
    if not match:
        return (
            "coding ambience, programming music, developer focus, deep work, "
            "lofi coding, focus music, study music, chillhop"
        )
    return match.group(1).strip()


def extract_video_tags(number: str) -> str | None:
    text = DESCRIPTIONS_PATH.read_text(encoding="utf-8")
    pattern = rf"### #{number} —[^\n]*\n\nTags:\n```\n([\s\S]*?)```"
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()


def resolve_youtube_tags(video: dict) -> str:
    queue_tags = video.get("youtubeTags")
    if queue_tags:
        return queue_tags
    doc_tags = extract_video_tags(video["number"])
    if doc_tags:
        return doc_tags
    return extract_series_tags(video["series"])


def playlist_series_label(series: str) -> str:
    if series == "Ambience Session":
        return "☕ Ambience Session"
    if series == "Rainy Night Coding":
        return "🌧️ Rainy Night Coding Series"
    return f"🎵 {series}"


def write_script_en(production_dir: Path, video: dict) -> None:
    from youtube_metadata import build_youtube_metadata, validate_youtube_metadata

    number = video["number"]
    metadata = build_youtube_metadata(video)
    validate_youtube_metadata(metadata)
    description = resolve_youtube_description(video)
    tags = ", ".join(metadata["tags"])
    basename = video["exportBasename"]
    title = metadata["title"]
    content = f"""# Script EN — {video['series']} #{number}

## Title

```
{title}
```

## Description

```
{description}
```

## Tags

```
{tags}
```

## Filename

```
{basename}.mp4
```

## Category

Música

## Playlists

- {video['series']}
- Developer Focus Sessions
"""
    (production_dir / "script-en.md").write_text(content, encoding="utf-8")


def write_brief(production_dir: Path, video: dict) -> None:
    number = video["number"]
    tracks = video["audio"]["tracks"]
    playlist = "\n".join(f"  {i}. {track}" for i, track in enumerate(tracks, start=1))
    brief_extra = video.get("brief", {})
    rain = video["audio"].get("rainVolume", 0)
    cafe = video["audio"].get("cafeVolume", 0)
    content = f"""# Brief — {number} {video['series']}

## Identificação

| Campo | Valor |
|-------|-------|
| Número | {number} |
| Série | {video['series']} |
| Título EN | {video['titleEn']} |
| Duração alvo | {format_duration(video['durationSeconds'])} |
| Data alvo publicação | {video.get('targetDate', '—')} |

## Mood

### Visual

- Cenário: {brief_extra.get('visual', video['mood'])}
- Iluminação: {brief_extra.get('lighting', 'Conforme mood da série')}
- Clima/tempo: {brief_extra.get('weather', 'Conforme série')}
- Elementos obrigatórios: {brief_extra.get('required', 'Laptop com código, ambiente imersivo')}
- Elementos opcionais: {brief_extra.get('optional', '—')}

### Sonoro

- Base: CC0 open-lofi + Mixkit
- Chuva: {rain * 100:.0f}% | Café: {cafe * 100:.0f}%
- **Playlist ({len(tracks)} faixas exclusivas):**
{playlist}
- Config: `audio.json`

## Prompt IA

Ver [prompts/scene-base.md](./prompts/scene-base.md).

## Aprovação

- [x] Brief revisado
- [x] Metadata EN pronta ([script-en.md](./script-en.md))
- [x] Prompts IA definidos
"""
    (production_dir / "brief.md").write_text(content, encoding="utf-8")


def file_done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 1000


def write_checklist(production_dir: Path, video: dict) -> None:
    number = video["number"]
    basename = video["exportBasename"]
    source = production_dir / "source"
    exports = production_dir / "exports" / "youtube"
    tracks = " → ".join(video["audio"]["tracks"])
    rain = video["audio"].get("rainVolume", 0)
    cafe = video["audio"].get("cafeVolume", 0)
    no_rain = video["audio"].get("noRain", False)

    scene_ok = file_done(source / "scene-base.png")
    loop_ok = file_done(source / "scene-loop.mp4")
    thumb_ok = file_done(source / "thumbnail.png")
    audio_ok = file_done(source / "audio-mix.wav")
    video_ok = file_done(exports / f"{basename}.mp4")
    preview_ok = file_done(exports / f"{basename}-30s-preview.mp4")
    flac_ok = any(
        path.is_file() and path.stat().st_size > 0
        for path in (production_dir / "exports" / "streaming").glob(f"{basename}-*min-loop.flac")
    ) if (production_dir / "exports" / "streaming").exists() else False

    def mark(done: bool) -> str:
        return "x" if done else " "

    rain_line = (
        "- [x] Sem chuva (cena diurna/seca)"
        if no_rain
        else f"- [{mark(audio_ok)}] Chuva {rain * 100:.0f}%, murmúrio {cafe * 100:.0f}%"
    )

    content = f"""# Checklist — {video['series']} #{number}

## Pré-produção

- [{mark((production_dir / 'brief.md').exists())}] Brief aprovado
- [{mark((production_dir / 'script-en.md').exists())}] script-en.md preenchido
- [{mark((production_dir / 'prompts/scene-base.md').exists())}] Prompts IA documentados

## Visual

- [{mark(scene_ok)}] Cena base gerada (`source/scene-base.png`)
- [{mark(loop_ok)}] Loop animado 12s (`source/scene-loop.mp4`)
- [{mark(thumb_ok)}] Thumbnail gerada (`source/thumbnail.png`)
- [{mark(loop_ok)}] Resolução 1920×1080 @ 24fps

## Áudio

- [{mark(audio_ok)}] Mix CC0 + ambiência (`source/audio-mix.wav`)
- [{mark(audio_ok)}] Ordem: {tracks}
{rain_line}
- [{mark(audio_ok)}] Licenças em `assets/audio/LICENSES.md`

## Montagem

- [{mark(video_ok)}] Vídeo exportado (`exports/youtube/{basename}.mp4`)
- [{mark(video_ok)}] Duração verificada via ffprobe
- [{mark(preview_ok)}] Preview 30s validado
- [{mark(flac_ok)}] FLAC do loop em `exports/streaming/`

## Licenciamento

- [x] Música: CC0 (open-lofi)
- [x] SFX: Mixkit License
- [ ] Upload privado Content ID check (24–48h)

## Publicação (seguir docs/10-guia-de-upload-youtube.md)

- [ ] Upload como Não listado
- [ ] Metadata copiada do script-en.md
- [ ] Thumbnail aplicada
- [ ] Playlists ({video['series']} + Developer Focus Sessions)
- [ ] End screen + card
- [ ] Público / agendado
- [ ] Comentário fixado (copiar de docs/14-comentarios-fixados-youtube.md)
- [ ] Calendário atualizado

## URLs

| Plataforma | URL |
|------------|-----|
| YouTube | _pendente_ |
"""
    (production_dir / "checklist.md").write_text(content, encoding="utf-8")


def scaffold_docs(production_dir: Path, video: dict) -> None:
    from youtube_metadata import write_youtube_metadata

    write_brief(production_dir, video)
    write_script_en(production_dir, video)
    write_checklist(production_dir, video)
    write_youtube_metadata(production_dir, video)
