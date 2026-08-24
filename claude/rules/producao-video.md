# Regras — Produção de Vídeo

## Aprovação do usuário (obrigatória)

- Desenvolver = gerar **preview** (`--preview 300` = 5 min), nunca o MP4 completo por iniciativa do agente
- **Proibido** rodar render completo sem permissão explícita do usuário na conversa
- Após o preview: apresentar cena/thumbnail/caminho e **aguardar** aprovação ou pedido de mudança
- Se a cena for rejeitada: nova imagem → novo preview apenas; não regenerar o vídeo longo sozinho
- Status `produzido` só depois do export completo autorizado e concluído

## Antes de produzir

- Ler `productions/XXX/brief.md`
- Confirmar duração e série no calendário
- Verificar reutilização de assets em `assets/`
- Criar `productions/XXX/audio.json` com **3–4 faixas novas** (ver abaixo)

## Música — obrigatório por vídeo

- **Cada vídeo = playlist única de 3–4 faixas** — nunca reutilizar faixas de outro vídeo
- Priorizar playlists no `catalog` de `templates/audio-config.json` (exemplo incluso; amplie localmente)
- Mesmo padrão da imagem: identidade visual e sonora exclusivas por produção
- Fonte: packs CC0 (open-lofi, Holizna) e, se o pool acabar, faixas originais via `generate_lofi_track.py` (receita OpenAI + síntese local)
- Registrar em `assets/audio/music-registry.json` e `productions/XXX/audio.json`
- Consultar faixas já usadas: `assets/audio/MUSIC-REGISTRY.md`
- Mix sempre via `mix_focus_audio.py --production-dir productions/XXX` (validação automática)

### Checklist áudio

1. Usar a playlist do catálogo (`templates/audio-config.json`) ou escolher 3–4 faixas não listadas em `music-registry.json`
2. Copiar MP3 para `assets/audio/music/`
3. Preencher `audio.json` na pasta da produção
4. Rodar mix com `--register` na primeira geração

## Áudio — mix

- Hierarquia do mix: **uma trilha musical por vez**. Fundo só com SFX calmos (chuva, ruído branco, pássaros, room tone) — nunca duas músicas ao mesmo tempo
- Playlist de 3–4 faixas exclusivas por vídeo, em sequência contínua: fade curto de saída → fade curto de entrada, **sem silêncio**. Áudio e vídeo **nunca param** no ponto de loop
- Volumes padrão: trilha `0.065`; café ~`0.03`; chuva ~`0.055` (SFX bem abaixo da música)
- Loudness final: -15 LUFS integrado (pipeline `mix_focus_audio.py`)
- True peak: máximo -1,5 dBTP
- Loop de áudio do vídeo longo: **30 minutos** (1800s), não 10 min, para a costura ficar bem mais espaçada
- Costura do loop de áudio: sempre `make_seamless_loop` (crossfade 8–24s conforme duração) — nunca fade para silêncio no wrap
- Costura do loop de vídeo: `xfade` de ~1s no `scene-loop` curto antes do `stream_loop`
- Piso sonoro contínuo: se o vídeo desligar chuva/café/ruído, o mix injeta `soft-room-tone` baixo automaticamente — **nunca silêncio total** entre faixas (na TV isso parece que o vídeo “acabou”)
- Ambiência (chuva/café/ruído branco) pode variar por mood; trilhas musicais não repetem entre vídeos
- **YouTube TV “Continuar assistindo?”**: é idle check do app (~3h sem mexer no controle). **Não existe flag de criador** para desligar. Nosso lado: A/V contínuos sem gap/travada; do espectador: um toque no controle quando aparecer
- Nunca usar música sem licença verificada
- Não usar `generate_ambient_audio.py` em produção (mix chuva+café+lofi legado)
- `generate_lofi_track.py` pode entrar no pool quando os packs CC0 acabarem — o `next:preview` chama sozinho

## Visual

- Proporção 16:9
- Resolução mínima 1920×1080
- Cena IA única por vídeo — não reutilizar `scene-base.png` de outra produção
- Cena gerada automaticamente por `generate_scene_ai.py` no `npm run next` / `next:preview` (OpenAI ou Pollinations via `.env`); backup em `assets/scenes/`
- Prompt de cena: **sem vapor/fumo/steam assado na PNG** — vapor só via overlay animado
- Modo de animação padrão: **`ambient`** (câmera travada + micro-animação por mood). `hybrid` quando há `animate.layers`. `locked` / `cinematic` / `procedural` só se explícito — nunca `slow_zoom` ou `cinematic` como default
- `effect-mask.png` gerada automaticamente quando o modo hybrid precisa
- Qualidade visual no patamar de TheSoundYouNeed — ver [referencia-canal.md](./referencia-canal.md)
- Loop visual imperceptível; no preview exportar `source/qa-loop-seam.png` no ponto de wrap
- Animações correspondentes ao ambiente da cena (não só chuva/vapor genéricos)
- Chuva visual/sonora **só se houver janela** na cena; vapor **só se houver xícara** (senão desliga, sem fallback no canto da tela)
- Thumbnail: gerar `thumbnail.png` + `thumbnail-b.png` no preview; humano escolhe
- Thumbnail com contraste alto: fundos escuros, badge nunca em cor clara, cenas bright auto-escurecidas

## Export

- MP4 H.264 para YouTube
- Nome: `XXX-serie-mood-duracao.mp4`
- Exportar FLAC para `exports/streaming/`

## QA obrigatório

- Assistir 2 minutos no ponto de loop
- Ouvir 30s no wrap do áudio + 20s no wrap do vídeo no preview
- Conferir `source/qa-loop-seam.png` e as duas thumbnails
- Upload privado para check Content ID
- Preencher `checklist.md` integralmente
- Confirmar que `audio-mix.manifest.json` lista faixas exclusivas
- Confirmar `source/youtube-metadata.json` (título ≤70 chars, 15 tags)

## Metadata

- Título em inglês conforme `docs/07-seo-e-metadata.md`
- 15 tags
- Capítulos a cada hora (ou conforme duração)
- Descrição com playlists

## Após publicação

- Atualizar status no calendário
- Registrar URL do YouTube no brief ou calendário
