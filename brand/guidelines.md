# Brand Guidelines — Open Lofi Studio

## Logo e ícone

O ícone do canal combina **café** e **código**:

- Caneca estilizada com vapor em forma de `</>` ou chaves `{ }`
- Versões: claro sobre escuro (padrão), escuro sobre claro (exceção)

Arquivos em `brand/logos/` (gerar exports PNG 800×800 para avatar).

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
│ COFFEE SHOP CODING          ┌───────────┐  │
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
| Badge duração | JetBrains Mono Medium 28px, fundo escuro (`#e94560` ou accent escuro da série), texto `#ffffff` |
| Margem interna | 24 px |

### Regras de contraste (obrigatório)

- **Nunca usar cores claras** (`#f5e6d3`, branco, pastel, cream) como fundo de badge ou blocos grandes
- Badge de duração sempre com fundo escuro/saturado e texto branco — legível em feed mobile
- Cenas claras (sunrise, neve, dia) recebem escurecimento automático + vinheta forte no pipeline
- Objetivo: thumbnail chama atenção em 0,5s na sidebar do YouTube com feedback visual claro do vídeo
- `coffeeCream` só em subtítulo pequeno sobre a barra `midnight` — nunca como elemento dominante

## Banner YouTube

| Especificação | Valor |
|---------------|-------|
| Dimensão | 2560 × 1440 px |
| Safe zone (texto) | Centro 1546 × 423 px |
| Conteúdo | Cena café + logo + "Immersive focus for developers" |
| Evitar | Texto nas bordas (crop em mobile/TV) |

## Tipografia

| Fonte | Uso | Fallback |
|-------|-----|----------|
| Inter | Títulos thumbnails, banner | Arial, sans-serif |
| JetBrains Mono | Duração, detalhes tech | Consolas, monospace |

## Tom de imagem

- Fotorealismo cinematográfico ou ilustração semi-realista
- Sempre noturno ou golden hour — evitar cenas de dia pleno (exceto série Sunday Morning)
- Monitores com código colorido mas ilegível em thumbnail size
- Sem pessoas visíveis (POV implícito)
- Café/quente sempre que série for Open Lofi Studio

## Séries — variação de cor accent

| Série | Accent secundário |
|-------|-------------------|
| Open Lofi Studio | `#f5e6d3` (cream) — só subtítulo na barra escura; badge usa `#e94560` |
| Rainy Night Coding | `#0f3460` (rain blue) |
| Cyberpunk Developer Room | `#e94560` + neon `#00fff2` |
| Space Programming | `#4ecca3` — barra/acento; badge usa fundo escuro se accent for claro |
| Cabin Programmer | `#d4a574` (wood) — barra/acento; badge usa `#e94560` |
| Dark Mode Workspace | `#4ecca3` (code green) |

Layout da thumbnail permanece idêntico — apenas cena e accent mudam.

## Uso incorreto

- Não distorcer proporções do logo
- Não usar cores fora da paleta em elementos de marca
- Não colocar mais de 3 linhas de texto na thumbnail
- Não usar emojis como substituto do logo

## Documentação relacionada

- [docs/02-marca-e-posicionamento.md](../docs/02-marca-e-posicionamento.md)
- [templates/youtube-description-template.md](../templates/youtube-description-template.md)
