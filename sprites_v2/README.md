# Sprites v2 — Hóquei em Patins (PAP)

Sprites limpos, com **o mesmo tamanho de célula**, **mesma escala** e **pés alinhados no mesmo ponto**.
Isto evita que o jogador "trema" quando o Pygame troca de frame.

## Pastas

| Pasta | O que tem |
|---|---|
| `pixel/` | Versão pixel-art (células **64×64**, paleta reduzida, arestas limpas). **Recomendada.** |
| `hd/` | Versão em resolução alta (células **128×128**, mais detalhe, arestas suaves). |
| `*/frames/` | Cada frame num PNG: `azul/`, `vermelho/`, `guarda_redes/`, `arbitro/`. |
| `*/spritesheets/` | Uma spritesheet por personagem + um `.json` com as animações. |
| `*/extras/` | Bola e 3 sticks (tamanho já proporcional aos jogadores). |
| `extras_ui/` | Balizas (frente/atrás), campo, público, marcador, pausa, cartões. |

## Animações (jogadores)

`parado` (3), `correr_cima` (3), `correr_baixo` (3), `correr_esquerda` (3), `correr_direita` (2 azul / 3 vermelho),
`com_bola` (4), `passe` (3), `remate` (2), `colisao` (3: dois a patinar + um caído).

Guarda-redes: `parado`, `mover_cima`, `mover_baixo`, `mover_esquerda`, `mover_direita`, `defender` (2 poses).
Árbitro: `parado`, `mover_cima`, `mover_baixo`, `mover_esquerda`, `mover_direita`.

## Importante: direção

Todas as poses laterais estão **voltadas para a direita**. Para andar para a esquerda,
espelha o frame no código: `pygame.transform.flip(frame, True, False)`.

## Âncora

O ponto dos pés de cada célula é `(largura/2, altura-3)` (indicado como `ancora_pes` nos `.json`).
Desenha sempre o frame de modo a que esse ponto fique na posição do jogador no campo.

## Exemplo de carregamento em Pygame (cortar a spritesheet)

```python
import json, pygame

def carregar_animacoes(png, jsonf):
    sheet = pygame.image.load(png).convert_alpha()
    info = json.load(open(jsonf, encoding="utf-8"))
    w, h = info["celula"]
    anims = {}
    for nome, a in info["animacoes"].items():
        anims[nome] = [sheet.subsurface((i * w, a["row"] * h, w, h)) for i in range(a["frames"])]
    return anims, info

anims, info = carregar_animacoes("pixel/spritesheets/jogador_azul.png",
                                 "pixel/spritesheets/jogador_azul.json")
frame = anims["correr_direita"][0]                           # voltado para a direita
frame_esq = pygame.transform.flip(frame, True, False)        # voltado para a esquerda
```

Na versão `pixel`, amplia sem suavização: `pygame.transform.scale(frame, (w*3, h*3))`
(usa `scale`, não `smoothscale`, para manter os pixéis nítidos).
