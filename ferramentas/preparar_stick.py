# -*- coding: utf-8 -*-
"""preparar_stick.py - tira um stick e a bola da imagem do emblema (para o remate na primeira pessoa).

No emblema há dois sticks cruzados com a bola no meio. Para o ecrã do remate é preciso UM stick
inteiro e a bola à parte:
  1. tira-se o fundo azul (como em preparar_emblema.py);
  2. o stick «A» é o que vai de cima à esquerda até à pá em baixo à direita: ficam só os píxeis dos
     quadrantes de cima-esquerda e de baixo-direita (o outro stick está nos outros dois quadrantes),
     tirando o círculo da bola;
  3. roda-se a imagem para o cabo ficar na horizontal e preenche-se o bocado do cabo que estava
     escondido atrás da bola, copiando a "fatia" do cabo mesmo ao lado (o cabo é igual a todo o comprimento);
  4. roda-se para a inclinação do ecrã do remate e guarda-se; a bola é recortada num círculo.

Uso:  python ferramentas/preparar_stick.py docs/originais/emblema_sticks_original.png
"""
import math
import os
import sys
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PASTA = os.path.join(RAIZ, "hockey_game", "assets", "ui")
INCLINACAO_FINAL = 28        # graus: o cabo desce para a direita, como na imagem de referência


def mascara_fundo(img):
    w, h = img.get_size()
    rgb = pygame.image.tobytes(img, "RGB")
    fundo = bytearray(w * h)
    fila = deque([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] +
                 [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    while fila:
        x, y = fila.popleft()
        i = y * w + x
        if fundo[i]:
            continue
        r, g, b = rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]
        if not (b - r >= 9 and max(r, g, b) < 130):
            continue
        fundo[i] = 1
        if x > 0: fila.append((x - 1, y))
        if x < w - 1: fila.append((x + 1, y))
        if y > 0: fila.append((x, y - 1))
        if y < h - 1: fila.append((x, y + 1))
    return rgb, fundo


def centro_bola(img):
    xs = ys = n = 0
    w, h = img.get_size()
    for y in range(h // 2 - 140, h // 2 + 140, 2):
        for x in range(w // 2 - 140, w // 2 + 140, 2):
            r, g, b, _ = img.get_at((x, y))
            if max(r, g, b) < 70 and abs(b - r) < 8:
                xs += x; ys += y; n += 1
    return xs / n, ys / n, (n * 4 / math.pi) ** 0.5


def esfera_preta(lado: int) -> pygame.Surface:
    """Bola de hóquei em patins: esfera preta brilhante (luz de cima, à esquerda)."""
    Q = 3
    T = lado * Q
    sup = pygame.Surface((T, T), pygame.SRCALPHA)
    r = T / 2 - 2 * Q
    c = T / 2
    lx, ly = c - r * 0.35, c - r * 0.4               # de onde vem a luz
    for i in range(60, 0, -1):
        k = i / 60
        # do escuro (borda) para o mais claro (perto do reflexo)
        cor = int(8 + 58 * (1 - k) ** 2)
        cx = c + (lx - c) * (1 - k)
        cy = c + (ly - c) * (1 - k)
        pygame.draw.circle(sup, (cor, cor, cor + 4, 255), (cx, cy), r * k)
    pygame.draw.circle(sup, (0, 0, 0, 255), (c, c), r, 3 * Q)                     # contorno
    pygame.draw.circle(sup, (170, 170, 180, 255), (lx, ly), r * 0.12)            # reflexo
    return pygame.transform.smoothscale(sup, (lado, lado))


def main(origem):
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    img = pygame.image.load(origem).convert()
    w, h = img.get_size()
    rgb, fundo = mascara_fundo(img)
    bcx, bcy, braio = centro_bola(img)
    braio += 3

    stick = pygame.Surface((w, h), pygame.SRCALPHA)
    bola = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if fundo[i]:
                continue
            cor = (rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2], 255)
            d = math.hypot(x - bcx, y - bcy)
            madeira = cor[0] > 120 and cor[0] - cor[2] > 30
            if d <= braio:
                if not madeira:                 # na borda da bola aparecem bocadinhos dos sticks
                    bola.set_at((x, y), cor)
            elif (x < bcx and y < bcy) or (x > bcx and y > bcy):
                stick.set_at((x, y), cor)

    # Eixo do cabo: do centro da bola até à ponta do cabo (primeiro píxel do stick na diagonal)
    d0 = next(d for d in range(0, w) if stick.get_at((d, d)).a > 0)
    ang = math.degrees(math.atan2(bcy - d0, bcx - d0))           # ~48 graus (desce para a direita)
    # Rodar para o cabo ficar horizontal; um ponto vermelho marca o centro da bola
    marca = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(marca, (255, 0, 0, 255), (round(bcx), round(bcy)), 3)
    st_h = pygame.transform.rotate(stick, ang)
    mk_h = pygame.transform.rotate(marca, ang)
    caixa = mk_h.get_bounding_rect()
    mx, my = caixa.center
    # Buraco no cabo (atrás da bola): colunas sem stick na linha do eixo, à volta da bola
    esq = mx
    while esq > 0 and st_h.get_at((esq, my)).a == 0:
        esq -= 1
    dirx = mx
    while dirx < st_h.get_width() - 1 and st_h.get_at((dirx, my)).a == 0:
        dirx += 1
    # Fatias do cabo mesmo antes e mesmo depois do buraco. As duas partes do cabo não estão
    # exatamente alinhadas, por isso o preenchimento vai deslizando de uma para a outra
    # (assim não fica um "degrau" na emenda).
    altura = st_h.get_height()
    fatia_e = st_h.subsurface((esq - 4, 0, 1, altura)).copy()
    fatia_d = st_h.subsurface((dirx + 4, 0, 1, altura)).copy()

    def meio(f):
        ys = [y for y in range(altura) if f.get_at((0, y)).a > 0 and abs(y - my) < 60]
        return (min(ys) + max(ys)) / 2

    desvio = meio(fatia_d) - meio(fatia_e)
    for x in range(esq - 3, dirx + 4):
        k = (x - (esq - 3)) / max(1, (dirx + 4) - (esq - 3))
        st_h.fill((0, 0, 0, 0), (x, round(my - 70), 1, 140))
        # Usa-se só a fatia da esquerda (madeira lisa; a da direita já tem a risca do logótipo)
        st_h.blit(fatia_e, (x, round(desvio * k)))
    # Rodar para a inclinação final do ecrã do remate e recortar
    final = pygame.transform.rotozoom(st_h, -INCLINACAO_FINAL, 1.0)
    final = final.subsurface(final.get_bounding_rect()).copy()
    os.makedirs(PASTA, exist_ok=True)
    pygame.image.save(final, os.path.join(PASTA, "stick_pov.png"))

    # Bola: no emblema está por cima dos sticks (a borda de baixo tem bocadinhos de madeira),
    # por isso é desenhada de novo: esfera preta com sombreado e um reflexo de luz.
    bola_img = esfera_preta(148)
    pygame.image.save(bola_img, os.path.join(PASTA, "bola_pov.png"))
    print("stick:", final.get_size(), "| bola:", bola_img.get_size(), "| eixo:", round(ang, 1), "graus",
          "| buraco preenchido:", dirx - esq, "px")


if __name__ == "__main__":
    main(sys.argv[1])
