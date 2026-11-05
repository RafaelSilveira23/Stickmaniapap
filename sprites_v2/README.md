# Sprites v2 — Hóquei em Patins (PAP)

Sprites limpos, com **o mesmo tamanho de célula** (128×128), **mesma escala** e **pés alinhados no mesmo ponto**.
Isto evita que o jogador "trema" quando o Pygame troca de frame.

Só estão aqui os ficheiros que o jogo usa (as versões que não eram usadas — pixel, spritesheets,
árbitro, sticks extra e imagens antigas da interface — foram retiradas; continuam no histórico do Git).

## Pastas

| Pasta | O que tem | Quem usa |
|---|---|---|
| `hd/frames/azul/` | Jogador de campo (equipamento azul com riscas brancas, pintado com as cores de cada clube) | `player.py`, `remate_pov.py`, `componentes.py` |
| `hd/frames/vermelho/` | Jogador de campo vermelho (só é usado se uma equipa não tiver equipamento definido) | `player.py` |
| `hd/frames/guarda_redes/` | Guarda-redes | `goalkeeper.py`, `remate_pov.py` |
| `hd/extras/bola.png` | Bola | `ball.py` |
| `extras_ui/publico_tile.png` | Público da bancada (repetido ao longo do pavilhão) | `rink.py` |

## Animações (jogadores)

`parado` (3), `correr_cima` (3), `correr_baixo` (3), `correr_esquerda` (3), `correr_direita` (2 azul / 3 vermelho),
`com_bola` (4), `passe` (3), `remate` (2), `colisao` (3: dois a patinar + um caído).

Guarda-redes: `parado`, `mover_cima`, `mover_baixo`, `mover_esquerda`, `mover_direita`, `defender` (2 poses).

## Importante: direção

Todas as poses laterais estão **voltadas para a direita**. Para andar para a esquerda,
espelha o frame no código: `pygame.transform.flip(frame, True, False)`.
