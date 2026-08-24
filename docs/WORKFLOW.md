# Workflow (community)

## 1. Scaffold a production

Copy from `templates/production-meta.example.json` → `templates/production-meta.json` (local, gitignored) and use `templates/audio-config.json` when scaffolding a folder:

```text
productions/my-session/
  meta.json
  audio.json
  source/
```

`productions/` is gitignored — keep videos on your machine.

## 2. Scene

- Generate or place `source/scene-base.png`
- Prefer prompts without baked-in steam/smoke (vapor can be an overlay when needed)
- Default animation mode: `ambient` (static camera + subtle ambient effects)

## 3. Preview

```bash
.venv/bin/python scripts/produce_video.py \
  --production productions/my-session \
  --duration 10800 \
  --preview 300
```

Or use `npm run next:preview` when a queue is configured.

Approve the preview before a full render.

## 4. Shorts (optional)

Install MoneyPrinterTurbo under `tools/moneyprinterturbo/upstream` (see that README), then:

```bash
npm run short:preview -- my-session
```

## 5. Metadata

Preview/scaffold writes `source/youtube-metadata.json` (title ≤70 chars, 15 tags).
