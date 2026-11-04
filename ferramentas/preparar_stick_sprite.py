# -*- coding: utf-8 -*-
"""preparar_stick_sprite.py - prepara o sprite do stick para o remate na primeira pessoa.

O sprite (stick «SUPER / AZEMAD.» com punho preto) vem num fundo branco, com o punho em cima à
direita e a pá em baixo à esquerda. Fica assim no ecrã do remate (virá-lo deixava as letras ao
contrário): o cabo vem de cima à direita e a bola fica pousada na pá, em baixo à esquerda.
  1. tira-se o fundo branco: a partir das bordas, "pinta-se" (flood fill) tudo o que é quase branco
     e esses píxeis ficam transparentes (o contorno escuro do stick trava a pintura);
  2. as bordas ficam suaves: os píxeis claros junto ao stick ficam meio transparentes;
  3. roda-se um pouco para o cabo ficar menos a pique e recorta-se.

Uso:  python ferramentas/preparar_stick_sprite.py docs/originais/stick_sprite_original.jpg
Resultado: hockey_game/assets/ui/stick_pov.png
"""
import os
import sys
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SAIDA = os.path.join(RAIZ, "hockey_game", "assets", "ui", "stick_pov.png")
RODAR = -14          # graus (negativo = sentido dos ponteiros): o cabo fica menos a pique


def e_branco(r, g, b) -> bool:
    return min(r, g, b) > 228 and max(r, g, b) - min(r, g, b) < 18


def main(origem: str):
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    img = pygame.image.load(origem).convert()
    w, h = img.get_size()
    rgb = pygame.image.tobytes(img, "RGB")
    fundo = bytearray(w * h)
    fila = deque([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] +
                 [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    while fila:
        x, y = fila.popleft()
        i = y * w + x
        if fundo[i] or not e_branco(rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]):
            continue
        fundo[i] = 1
        if x > 0: fila.append((x - 1, y))
        if x < w - 1: fila.append((x + 1, y))
        if y > 0: fila.append((x, y - 1))
        if y < h - 1: fila.append((x, y + 1))

    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        r, g, b = rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]
        rgba[4 * i:4 * i + 3] = bytes((r, g, b))
        if fundo[i]:
            a = 0
        else:
            # Borda suave: quanto mais claro (quase branco) mais transparente fica, só junto ao fundo
            x, y = i % w, i // w
            junto = any(0 <= x + dx < w and 0 <= y + dy < h and fundo[(y + dy) * w + x + dx]
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            a = 255
            if junto:
                claro = min(r, g, b)
                a = max(0, min(255, int((255 - claro) * 255 / 70)))
        rgba[4 * i + 3] = a
    out = pygame.image.frombytes(bytes(rgba), (w, h), "RGBA")
    out = pygame.transform.rotozoom(out, RODAR, 1.0)
    out = out.subsurface(out.get_bounding_rect()).copy()
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    pygame.image.save(out, SAIDA)
    print("guardado:", os.path.abspath(SAIDA), out.get_size())


if __name__ == "__main__":
    main(sys.argv[1])
