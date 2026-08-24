# Open Lofi Studio

Open-source pipeline to generate **long-form coding ambience** videos and promotional **Shorts** — free for the community.

Build immersive focus sessions with AI scenes, subtle ambient loops (static camera + mood-driven effects), CC0-friendly audio mixes, YouTube-ready metadata, and optional Shorts via [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo).

## Features

- Long-form preview / export with FFmpeg
- Locked-camera scene loops with ambient micro-animation (no shaky Ken Burns by default)
- Focus audio mix with continuous floor (no silent gaps)
- Thumbnail variants + YouTube metadata helpers
- Shorts via MoneyPrinterTurbo CLI (local materials + TTS + subtitles)

## Requirements

- Python 3.11+
- FFmpeg / ffprobe
- Optional: OpenAI or Pollinations API key for scene generation
- Optional: MoneyPrinterTurbo clone under `tools/moneyprinterturbo/upstream` for Shorts

## Quick start

```bash
git clone https://github.com/mateusfs/open-lofi-studio.git
cd open-lofi-studio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
cp templates/production-meta.example.json templates/production-meta.json
# edit .env if you use scene AI providers
# expand production-meta.json locally: python scripts/build_templates_catalog.py --enqueue
```

Create a production folder locally (never committed):

```bash
mkdir -p productions/demo-session/source
# add scene-base.png, audio.json, meta.json — see templates/
npm run next:preview   # or call scripts directly
```

Shorts (after scene loop exists + MPT setup):

```bash
npm run short:preview -- demo-session
```

See [`tools/moneyprinterturbo/README.md`](tools/moneyprinterturbo/README.md).

## Local-only data

These stay on your machine (gitignored):

- `productions/` — your videos and exports
- `templates/production-meta.json` — your video catalog (copy from `.example.json`)
- `assets/audio/`, `assets/scenes/` — media libraries
- `.env`, OAuth credentials

## Project layout

```
scripts/     Production pipeline
templates/   meta / audio starters
tests/       Unit tests
brand/       Generic visual guidelines
docs/        Community docs
tools/       MoneyPrinterTurbo helper docs
```

## Support the project

If this tool helps you ship ambience videos, you can buy me a coffee:

**[https://buymeacoffee.com/patrimonium](https://buymeacoffee.com/patrimonium)**

## Credits

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — Shorts assembly reference / CLI
- Community CC0 / open lofi packs for music (document licenses in your `assets/audio/LICENSES.md`)

## License

MIT — see [LICENSE](LICENSE).
