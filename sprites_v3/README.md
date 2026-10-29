# Sprites v3 — gerados por código

Estes sprites **não foram desenhados à mão**: são gerados pelo script
[`ferramentas/gerar_sprites.py`](../ferramentas/gerar_sprites.py) a partir de um esqueleto
(anca, joelhos, cotovelos, patins e stick). Por isso todos os frames têm exatamente
as mesmas proporções e cores, e o jogador não "treme" ao trocar de frame.

Para voltar a gerar (por exemplo depois de mudar uma pose ou uma cor):

```bash
python ferramentas/gerar_sprites.py
```

## Ficheiros

| Ficheiro | O que tem |
|---|---|
| `jogador.png` + `.json` | Spritesheet do jogador de campo (uma animação por linha) |
| `guarda_redes.png` + `.json` | Spritesheet do guarda-redes |
| `frames/` | Cada frame num PNG à parte |
| `preview.gif` | Todas as animações a mexer (para ver rapidamente / relatório) |

Células de **96×96**, pés em `(48, 90)`, todos os frames **virados para a direita**
(o jogo espelha-os para a esquerda). O equipamento é **azul com riscas brancas**:
o jogo troca essas cores pelas de cada clube (`hockey_game/cores.py`).

## Animações do jogador (11)

| Animação | Frames | Quando aparece |
|---|---|---|
| `parado` | 4 | parado, a respirar e a bater o stick |
| `patinar` | 8 | a patinar (pernas alternadas) |
| `sprint` | 6 | a correr a fundo, com o braço livre a balançar |
| `travar` | 2 | travagem forte (com raspas dos patins) |
| `com_bola` | 8 | a conduzir a bola com a pá do stick |
| `passe` | 5 | passe |
| `remate` | 6 | remate (stick levantado atrás e acompanhamento) |
| `desarme` | 4 | quando rouba a bola a um adversário |
| `queda` | 5 | quando sofre uma carga e cai |
| `levantar` | 4 | depois da queda |
| `festejar` | 6 | depois de marcar golo |

## Animações do guarda-redes (5)

`parado` (4), `mover` (4), `defender` (3, em baixo), `defesa_alta` (3, luva no ar), `festejar` (4).

## Exemplo de carregamento

```python
from animation import carregar_spritesheet
anims = carregar_spritesheet("sprites_v3/jogador.png", "sprites_v3/jogador.json", scale=(52, 52))
frame = anims["patinar"].imagem
```
