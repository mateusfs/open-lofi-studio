# Agentes — Open Lofi Studio

Guia para agentes de IA neste repositório open-source.

## Contexto

Open Lofi Studio é um pipeline comunitário para gerar vídeos longos de ambience/lo-fi e Shorts promocionais. Produções e mídia ficam locais (`productions/` é gitignored).

## Estrutura

| Pasta | Função |
|-------|--------|
| `docs/` | Docs comunitários (`WORKFLOW.md`, `LICENSING.md`, …) |
| `brand/` | Diretrizes visuais genéricas |
| `assets/` | Esqueleto local (áudio/cenas não versionados) |
| `productions/` | Produções locais (ignoradas no git) |
| `templates/` | Modelos de meta/áudio |
| `scripts/` | Automação (Python + FFmpeg) |
| `tools/moneyprinterturbo/` | Docs/compose para Shorts |

## Regras

Ver [rules/producao-video.md](./rules/producao-video.md).

## Princípios

- Preview antes do render completo
- Default de animação: `locked`
- Sem vapor/fumo assado na PNG de cena
- Não commitar vídeos, WAV, ou filas privadas de canal
