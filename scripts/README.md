# Scripts de Produção

Automação para geração de assets e montagem de vídeos Ambience Session.

## Dependências

- Python 3.10+
- FFmpeg (`ffmpeg`, `ffprobe`)
- `numpy`, `Pillow`, `google-api-python-client`, `google-auth-oauthlib`, `openai`

```bash
pip install -r requirements.txt
```

## Scripts

| Script | Função |
|--------|--------|
| `generate_scene_ai.py` | Gera cena via OpenAI/Pollinations (chamado por `next.py`) |
| `effect_mask.py` | Gera `effect-mask.png` automaticamente para hybrid |
| `generate_scene.py` | Cena base estilizada procedural (fallback do #001) |
| `ambient_presets.py` | Presets de efeitos por series/mood (modo `ambient`, default) |
| `animate_scene.py` | Loop animado procedural 20s (chuva, vapor, efeitos); modo legado `procedural` |
| `animate_cinematic.py` | Loop cinematográfico 24s: Ken Burns + overlays reais (`assets/images/overlays/`) |
| `mix_focus_audio.py` | Mix CC0 chillhop + chuva + café; exige `audio.json` único por produção |
| `audio_registry.py` | Valida que faixas não repetem entre vídeos |
| `generate_ambient_audio.py` | Legado procedural (não usar em produção) |
| `generate_thumbnail.py` | Thumbnail 16:9 (`thumbnail.png`) + capa Short 9:16 (`thumbnail-b.png`) |
| `assemble_video.py` | Monta vídeo longo repetindo o loop animado (stream copy) |
| `produce_video.py` | Pipeline completo para uma produção (lê `meta.json` + `audio.json`) |
| `setup_production.py` | Scaffold da pasta a partir de `production-queue.json` |
| `next_video.py` | Próximo vídeo da fila (`--claim`, `--complete`) |
| `fetch_open_lofi_tracks.py` | Baixa faixas CC0 novas do ZIP open-lofi |
| `replenish_music.py` | Reabastece packs CC0 e, se acabarem, gera faixas originais |
| `generate_lofi_track.py` | Faixas lo-fi originais (receita OpenAI + síntese local) |
| `youtube_outreach.py` | Outreach híbrido: comentários em canais inspiradores (YouTube API) |

## Uso principal

```bash
npm run next          # gera o próximo vídeo completo
npm run next:preview  # preview 5 min do próximo
npm run next:dry      # mostra qual será o próximo
npm run outreach:dry  # preview comentários de outreach
npm run outreach      # sessão interativa de outreach
npm run outreach:auth # autenticação OAuth YouTube
```

## Outreach YouTube

Comentários em canais inspiradores para ganhar visibilidade. Requer OAuth configurado.

Guia: `docs/15-outreach-comentarios-youtube.md`

```bash
npm run outreach:auth
npm run outreach:dry
npm run outreach
```

## Cena IA

Gere a imagem externamente conforme `prompts/scene-base.md` e salve em `source/scene-base.png` antes de rodar o pipeline. O `npm run next` não gera cenas automaticamente.

## Modos de animação (`meta.json` → `animate.mode`)

| Modo | Comportamento |
|------|----------------|
| **`ambient`** (default) | Câmera fixa + efeitos por `series`/`mood` via `ambient_presets.py` |
| **`procedural`** | Legado: chuva/vapor auto se `effects` vazio |
| **`locked`** | Loop estático (PNG repetido) |
| **`cinematic`** | Ken Burns — só se explícito |
| **`hybrid`** | Overlays + procedural quando `animate.layers` está definido |

## Regras de áudio

- **Cada vídeo = 3–4 faixas exclusivas** — não reutilizar trilhas entre produções
- Configurar em `productions/XXX/audio.json` (catálogo com 100 playlists: `templates/audio-config.json`)
- Catálogo local (gitignored): `cp templates/production-meta.example.json templates/production-meta.json`
- Regenerar catálogo completo: `python3 scripts/build_templates_catalog.py --enqueue`
- Registro global: `assets/audio/music-registry.json`
- Guia completo: `assets/audio/MUSIC-REGISTRY.md`

```bash
python3 scripts/mix_focus_audio.py \
  --production-dir productions/010-rainy-night-tokyo \
  --duration 600 \
  --output productions/010-rainy-night-tokyo/source/audio-mix.wav \
  --register
```

## Uso rápido — vídeo #001

```bash
cd "/home/mateus/projetos/Ambience Session"

python3 scripts/produce_video.py \
  --production productions/001-coffee-shop-coding \
  --duration 10800 \
  --preview 30
```

`--preview 30` gera versão de 30s para validação. Omitir para export completo de 3h.

## Notas

- Áudio procedural é 100% livre de copyright
- Para produção final com IA, substituir `source/scene-base.png` pela imagem gerada
- Vídeos longos levam tempo proporcional ao FFmpeg (3h ≈ 10–30 min de encode)
