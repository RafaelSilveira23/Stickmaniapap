# -*- coding: utf-8 -*-
"""preparar_emblema.py - tira o fundo azul da imagem do emblema (sticks cruzados com a bola).

O fundo é um azul-acinzentado escuro; os sticks são cor de madeira e os contornos e a bola
são pretos/cinzentos neutros. Por isso, a partir das bordas da imagem, "pinta-se" (flood fill)
tudo o que for escuro e azulado e esses píxeis ficam transparentes. Os contornos pretos
param a pintura, por isso o interior dos sticks e da bola nunca é apagado.

Uso:  python ferramentas/preparar_emblema.py imagem_original.png
Resultado: hockey_game/assets/ui/emblema_sticks.png (com transparência, recortado e a 512 px)
"""
import os
import sys
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SAIDA = os.path.join(RAIZ, "hockey_game", "assets", "ui", "emblema_sticks.png")


def e_fundo(r, g, b) -> bool:
    """Fundo = escuro e azulado (o azul é claramente maior do que o vermelho)."""
    return b - r >= 9 and max(r, g, b) < 130


def main(origem: str):
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    img = pygame.image.load(origem).convert()
    w, h = img.get_size()
    rgb = pygame.image.tobytes(img, "RGB")
    fundo = bytearray(w * h)               # 1 = píxel do fundo (fica transparente)
    fila = deque()
    for x in range(w):
        fila.append((x, 0)); fila.append((x, h - 1))
    for y in range(h):
        fila.append((0, y)); fila.append((w - 1, y))
    while fila:
        x, y = fila.popleft()
        i = y * w + x
        if fundo[i]:
            continue
        r, g, b = rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]
        if not e_fundo(r, g, b):
            continue
        fundo[i] = 1
        if x > 0: fila.append((x - 1, y))
        if x < w - 1: fila.append((x + 1, y))
        if y > 0: fila.append((x, y - 1))
        if y < h - 1: fila.append((x, y + 1))

    # Ficam só os píxeis ligados ao desenho principal: pontinhos soltos do fundo são apagados
    visto = bytearray(w * h)
    maior = []
    for inicio in range(w * h):
        if fundo[inicio] or visto[inicio]:
            continue
        grupo, pilha = [], [inicio]
        visto[inicio] = 1
        while pilha:
            i = pilha.pop()
            grupo.append(i)
            x, y = i % w, i // w
            for j in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1,
                      (i - w) if y > 0 else -1, (i + w) if y < h - 1 else -1):
                if j >= 0 and not fundo[j] and not visto[j]:
                    visto[j] = 1
                    pilha.append(j)
        if len(grupo) > len(maior):
            maior = grupo
    manter = bytearray(w * h)
    for i in maior:
        manter[i] = 1
    for i in range(w * h):
        if not manter[i]:
            fundo[i] = 1

    # Imagem nova com transparência (os píxeis do fundo ficam com alpha 0)
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        rgba[4 * i:4 * i + 3] = rgb[3 * i:3 * i + 3]
        rgba[4 * i + 3] = 0 if fundo[i] else 255
    out = pygame.image.frombytes(bytes(rgba), (w, h), "RGBA")
    caixa = out.get_bounding_rect()
    out = out.subsurface(caixa).copy()
    lado = max(caixa.width, caixa.height)
    quadrado = pygame.Surface((lado, lado), pygame.SRCALPHA)
    quadrado.blit(out, ((lado - caixa.width) // 2, (lado - caixa.height) // 2))
    final = pygame.transform.smoothscale(quadrado, (512, 512))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    pygame.image.save(final, SAIDA)
    print("guardado:", os.path.abspath(SAIDA), "| recorte:", caixa)


if __name__ == "__main__":
    main(sys.argv[1])
