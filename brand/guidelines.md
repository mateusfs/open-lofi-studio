# Brand Guidelines — Open Lofi Studio

## Logo e ícone

Ícone sugerido: café + código (caneca com vapor em forma de `</>` ou `{ }`).

Arquivos em `brand/logos/` (PNG 800×800 para avatar).

## Paleta

Ver [palette.json](./palette.json).

## Thumbnail — layout padrão

```
┌─────────────────────────────────────────────┐
│                                             │
│           CENA PRINCIPAL (85%)              │
│         ambiente imersivo + código          │
│                                             │
├─────────────────────────────────────────────┤
│ AMBIENCE SESSION            ┌───────────┐  │
│ Rainy Evening               │  3 HOURS  │  │
│                             └───────────┘  │
└─────────────────────────────────────────────┘
     barra inferior midnight #1a1a2e
```

### Especificações

| Elemento | Valor |
|----------|-------|
| Dimensão | 1280 × 720 px |
| Barra inferior | 120 px altura, `#1a1a2e` com gradiente superior |
| Título da série | Inter Bold 36px, `#ffffff` |
| Subtítulo mood | Inter Regular 22px, `#f5e6d3` |
| Badge duração | JetBrains Mono Medium 28px, fundo escuro (`#e94560` ou accent), texto `#ffffff` |
| Margem interna | 24 px |

### Regras de contraste

- Nunca usar cores claras como fundo de badge
- Badge de duração sempre com fundo escuro/saturado e texto branco
- Cenas claras recebem escurecimento + vinheta no pipeline

## Tipografia

| Fonte | Uso | Fallback |
|-------|-----|----------|
| Inter | Títulos thumbnails, banner | Arial, sans-serif |
| JetBrains Mono | Duração, detalhes tech | Consolas, monospace |

## Tom de imagem

- Fotorealismo cinematográfico ou ilustração semi-realista
- Preferir noite / golden hour
- Monitores com código colorido mas ilegível em thumbnail
- Sem pessoas visíveis (POV implícito)

## Séries — variação de accent (exemplos)

| Série | Accent |
|-------|--------|
| Ambience Session | `#f5e6d3` (cream no subtítulo); badge `#e94560` |
| Rainy Night Coding | `#0f3460` |
| Cyberpunk Developer Room | `#e94560` + neon `#00fff2` |
| Dark Mode Workspace | `#4ecca3` |

## Documentação relacionada

- [templates/youtube-description-template.md](../templates/youtube-description-template.md)
- [docs/WORKFLOW.md](../docs/WORKFLOW.md)
