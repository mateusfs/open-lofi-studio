# MoneyPrinterTurbo — Shorts oficiais

Shorts do canal usam o **CLI oficial** do [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo):

`script → Edge TTS → legendas → materiais locais → BGM → final MP4`

Não usamos o fallback ffmpeg genérico como caminho principal.

## Setup (uma vez)

```bash
git clone --depth 1 https://github.com/harry0703/MoneyPrinterTurbo.git \
  tools/moneyprinterturbo/upstream

cp tools/moneyprinterturbo/upstream/config.example.toml \
  tools/moneyprinterturbo/upstream/config.toml
# em config.toml: video_source = "local"

cd tools/moneyprinterturbo/upstream
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Opcional (API/WebUI):

```bash
cd tools/moneyprinterturbo/upstream
docker compose up -d
```

## Gerar Short

```bash
npm run short:preview -- 110
```

Equivalente ao que a lib recomenda:

```bash
cd tools/moneyprinterturbo/upstream
.venv/bin/python cli.py \
  --video-subject "Deep Work Sessions | Pomodoro" \
  --video-script "Welcome to ..." \
  --video-source local \
  --video-materials "/path/scene.png,/path/clip1.mp4,..." \
  --video-aspect 9:16 \
  --video-concat-mode random \
  --video-transition-mode fade-in \
  --video-clip-duration 4 \
  --voice-name en-US-AriaNeural-Female \
  --subtitle-enabled \
  --bgm-type custom --bgm-file track.mp3
```

Output: `productions/.../exports/shorts/{basename}-mpt-9x16.mp4`

## Branding

- Materiais = cena/loop da produção (não Pexels)
- Narração TTS curta + legendas (estilo MPT)
- BGM da playlist da produção
- Preview exige aprovação humana antes de publicar
