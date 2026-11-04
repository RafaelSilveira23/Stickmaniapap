# -*- coding: utf-8 -*-
"""pavilhao_pov.py - o pavilhão visto na primeira pessoa (fundo do ecrã do remate).

Desenha, uma só vez, o que se vê por trás da baliza:
  • a parede de cima com pilares e faixas de patrocinadores;
  • o marcador eletrónico ao centro (com o resultado e o tempo do jogo);
  • a bancada: degraus de cimento, cadeiras azuis e brancas, escadas, corrimãos e alguns adeptos;
  • as placas de publicidade (texturas para colar nas tabelas em perspetiva).
Os patrocinadores são inventados (não são marcas reais).
Tudo é desenhado com o dobro da resolução e reduzido no fim (bordas suaves).
"""
import math
import random

import pygame

from settings import WIDTH

PATROCINADORES = [
    ("STICKMANIA", (255, 255, 255), (20, 60, 160), "circulo"),
    ("ESBN", (30, 36, 48), (255, 255, 255), "triangulo"),
    ("PATINS+", (255, 255, 255), (230, 70, 50), "circulo"),
    ("RINQUE TV", (30, 120, 70), (255, 255, 255), "quadrado"),
    ("HÓQUEI PAP", (255, 255, 255), (40, 40, 50), "triangulo"),
    ("BOLA PRETA", (240, 200, 40), (25, 25, 30), "circulo"),
    ("PAVILHÃO 2027", (25, 70, 150), (255, 255, 255), "quadrado"),
]

_cache = {}


def _logo(s, forma, x, y, r, cor):
    if forma == "circulo":
        pygame.draw.circle(s, cor, (x, y), r)
        pygame.draw.circle(s, (255, 255, 255), (x, y), r * 0.45)
        pygame.draw.circle(s, cor, (x, y), r * 0.25)
    elif forma == "triangulo":
        pygame.draw.polygon(s, cor, [(x - r, y + r * 0.8), (x + r, y + r * 0.8), (x, y - r)])
    else:
        pygame.draw.rect(s, cor, (x - r, y - r, 2 * r, 2 * r), border_radius=max(1, int(r * 0.3)))


def textura_placa(indice: int, w: int = 360, h: int = 100) -> pygame.Surface:
    """Placa de publicidade (para colar nas tabelas)."""
    chave = ("placa", indice, w, h)
    if chave not in _cache:
        nome, fundo, cor, forma = PATROCINADORES[indice % len(PATROCINADORES)]
        s = pygame.Surface((w, h))
        s.fill(fundo)
        # Brilho de ecrã LED: a metade de cima um pouco mais clara
        claro = pygame.Surface((w, h // 2), pygame.SRCALPHA)
        claro.fill((255, 255, 255, 25))
        s.blit(claro, (0, 0))
        f = pygame.font.SysFont("Arial Black", int(h * 0.42))
        img = f.render(nome, True, cor)
        if img.get_width() > w * 0.78:
            img = pygame.transform.smoothscale(img, (int(w * 0.78), int(img.get_height() * w * 0.78 / img.get_width())))
        total = img.get_width() + h * 0.55
        x0 = (w - total) / 2
        _logo(s, forma, x0 + h * 0.2, h / 2, h * 0.2, cor)
        s.blit(img, img.get_rect(midleft=(x0 + h * 0.5, h / 2)))
        pygame.draw.rect(s, (0, 0, 0), s.get_rect(), 2)
        _cache[chave] = s
    return _cache[chave]


CORES_CADEIRAS = [
    ((36, 96, 206), 0.34),     # azul
    ((44, 140, 222), 0.27),    # azul-claro
    ((226, 230, 236), 0.32),   # branco
    ((78, 168, 176), 0.055),   # verde-água
    ((60, 64, 186), 0.01),     # anil
    ((110, 64, 176), 0.005),   # roxo
]


def _cor_cadeira(rnd):
    r = rnd.random()
    for cor, p in CORES_CADEIRAS:
        if r < p:
            return cor
        r -= p
    return CORES_CADEIRAS[0][0]


def _mais(cor, d):
    return tuple(max(0, min(255, c + d)) for c in cor)


def _cadeira(s, x, y_base, h, cor, Q):
    """Cadeira de bancada vista de frente e um pouco de cima: encosto (concha) e assento."""
    w = h * 1.0
    encosto = pygame.Rect(0, 0, round(w * Q), round(h * 0.56 * Q))
    encosto.midbottom = (round(x * Q), round((y_base - h * 0.16) * Q))
    raio = round(w * 0.32 * Q)
    pygame.draw.rect(s, _mais(cor, -70), encosto.move(round(Q * 1.5), round(Q * 2)), border_radius=raio)   # sombra
    pygame.draw.rect(s, cor, encosto, border_top_left_radius=raio, border_top_right_radius=raio,
                     border_bottom_left_radius=raio // 3, border_bottom_right_radius=raio // 3)
    # Parte de baixo do encosto mais escura (curva da concha) e brilho em cima
    pygame.draw.rect(s, _mais(cor, -28), (encosto.left, encosto.top + encosto.height * 0.62, encosto.width,
                                          encosto.height * 0.38), border_bottom_left_radius=raio // 3,
                     border_bottom_right_radius=raio // 3)
    pygame.draw.rect(s, _mais(cor, 30), (encosto.left + encosto.width * 0.18, encosto.top + Q * 1.5,
                                         encosto.width * 0.64, encosto.height * 0.16), border_radius=raio // 2)
    # Assento (por baixo do encosto, um pouco mais largo e mais claro)
    assento = pygame.Rect(0, 0, round(w * 1.02 * Q), round(h * 0.2 * Q))
    assento.midtop = (encosto.centerx, encosto.bottom - round(Q))
    pygame.draw.rect(s, _mais(cor, -45), assento.move(0, round(Q * 1.5)), border_radius=round(h * 0.08 * Q))
    pygame.draw.rect(s, _mais(cor, 18), assento, border_radius=round(h * 0.08 * Q))


def _adepto(s, x, y_base, h, rnd, cor_casa, Q, de_pe=False):
    """Adepto sentado (ou de pé): pernas, tronco com a camisola, braços e cabeça."""
    pele = rnd.choice([(232, 192, 158), (214, 168, 128), (180, 128, 90), (130, 88, 60), (240, 206, 176)])
    cabelo = rnd.choice([(40, 28, 20), (66, 42, 24), (20, 20, 22), (120, 85, 50), (170, 140, 95)])
    camisola = cor_casa if rnd.random() < 0.35 else rnd.choice(
        [(190, 50, 46), (46, 150, 80), (60, 64, 74), (230, 230, 235), (150, 110, 70), (40, 90, 170)])
    calcas = rnd.choice([(44, 56, 86), (36, 40, 50), (70, 80, 100)])
    q = Q
    if de_pe:
        alt = h * 2.6
        tronco = pygame.Rect(0, 0, round(alt * 0.3 * q), round(alt * 0.38 * q))
        tronco.midbottom = (round(x * q), round((y_base - alt * 0.42) * q))
        pygame.draw.rect(s, calcas, (tronco.left + tronco.width * 0.1, tronco.bottom, tronco.width * 0.8, alt * 0.42 * q))
    else:
        alt = h * 1.9
        tronco = pygame.Rect(0, 0, round(alt * 0.36 * q), round(alt * 0.4 * q))
        tronco.midbottom = (round(x * q), round((y_base - h * 0.24) * q))
        # Pernas por cima do assento
        pygame.draw.rect(s, calcas, (tronco.left + tronco.width * 0.05, tronco.bottom - q * 2, tronco.width * 0.9,
                                     h * 0.28 * q), border_radius=round(q * 2))
    pygame.draw.rect(s, camisola, tronco, border_top_left_radius=round(tronco.width * 0.35),
                     border_top_right_radius=round(tronco.width * 0.35))
    pygame.draw.rect(s, _mais(camisola, -35), (tronco.left, tronco.top + tronco.height * 0.55, tronco.width,
                                               tronco.height * 0.45))
    # Braços
    for lado in (-1, 1):
        bx = tronco.centerx + lado * tronco.width * 0.5
        pygame.draw.line(s, _mais(camisola, -20), (bx, tronco.top + tronco.height * 0.2),
                         (bx + lado * q, tronco.bottom - tronco.height * 0.1), max(1, round(tronco.width * 0.18)))
    r = alt * 0.12 * q
    cab = (tronco.centerx, tronco.top - r * 0.85)
    pygame.draw.circle(s, pele, cab, r)
    pygame.draw.circle(s, cabelo, (cab[0], cab[1] - r * 0.25), r * 1.02, draw_top_left=True, draw_top_right=True)


def bancada(altura: int, cor_casa=(30, 80, 180), semente: int = 4) -> pygame.Surface:
    """
    Bancada como na imagem de referência: parede de cimento com faixas e pilares, corrimões
    azul-escuros, filas de cadeiras «concha» azuis, brancas e verde-água em degraus de cimento,
    escadas entre os blocos e poucos adeptos. Fica em cache.
    """
    chave = ("bancada", altura, tuple(cor_casa), semente)
    if chave in _cache:
        return _cache[chave]
    Q = 2
    W, H = WIDTH * Q, altura * Q
    s = pygame.Surface((W, H))
    rnd = random.Random(semente)

    # Teto escuro com luzes
    pygame.draw.rect(s, (32, 34, 40), (0, 0, W, 20 * Q))
    for x in range(60, WIDTH, 160):
        pygame.draw.rect(s, (235, 238, 245), ((x - 18) * Q, 6 * Q, 36 * Q, 6 * Q), border_radius=Q * 2)
    # Parede de cima (cimento), com painéis mais escuros entre os pilares
    for y in range(20 * Q, 118 * Q):
        k = (y - 20 * Q) / (98 * Q)
        c = int(112 + 26 * k)
        pygame.draw.line(s, (c, c + 3, c + 9), (0, y), (W, y))
    pilares = (0, 330, 950, 1280)
    for a, b in zip(pilares, pilares[1:]):
        pygame.draw.rect(s, (104, 108, 116), ((a + 24) * Q, 82 * Q, (b - a - 48) * Q, 34 * Q))
    for px in pilares:
        pygame.draw.rect(s, (148, 152, 160), ((px - 15) * Q, 20 * Q, 30 * Q, 100 * Q))
        pygame.draw.rect(s, (120, 124, 132), ((px + 6) * Q, 20 * Q, 9 * Q, 100 * Q))
    # Faixas dos patrocinadores
    for i, (x, w) in enumerate(((24, 236), (360, 175), (812, 132), (980, 240), (1232, 110))):
        tex = textura_placa(i + 2, 320, 80)
        s.blit(pygame.transform.smoothscale(tex, (w * Q, 42 * Q)), (x * Q, 32 * Q))
    # Rebordo do piso de cima e um adepto de pé atrás do corrimão (como na imagem)
    pygame.draw.rect(s, (176, 178, 184), (0, 116 * Q, W, 7 * Q))
    _adepto(s, 418, 117, 19, rnd, cor_casa, Q, de_pe=True)
    _adepto(s, 1108, 117, 19, rnd, cor_casa, Q, de_pe=True)

    # Filas de cadeiras (as da frente, em baixo, estão mais perto: maiores)
    blocos = [(46, 596), (684, 1234)]
    y = 128
    filas = []
    k = 0
    while True:
        h = 23 + k * 1.8
        if y + h > altura - 34:
            break
        filas.append((y, h))
        y += h
        k += 1
    y_fim = y
    # Degraus de cimento (toda a largura) e escadas
    for y0, h in filas:
        pygame.draw.rect(s, (150, 152, 158), (0, y0 * Q, W, h * 0.34 * Q))             # espelho do degrau
        pygame.draw.rect(s, (184, 186, 192), (0, (y0 + h * 0.34) * Q, W, h * 0.66 * Q))  # piso do degrau
        pygame.draw.line(s, (132, 134, 140), (0, y0 * Q), (W, y0 * Q), Q)
    for ex0, ex1 in ((0, 46), (596, 684), (1234, 1280)):
        for y0, h in filas:
            for j in range(2):
                cor = (196, 198, 204) if j == 0 else (166, 168, 174)
                pygame.draw.rect(s, cor, (ex0 * Q, (y0 + j * h / 2) * Q, (ex1 - ex0) * Q, (h / 2 + 1) * Q))
                pygame.draw.line(s, (140, 142, 148), (ex0 * Q, (y0 + j * h / 2) * Q), (ex1 * Q, (y0 + j * h / 2) * Q), Q)
    # Corrimão das escadas do meio (metal)
    for xx in (606, 674):
        pygame.draw.line(s, (196, 200, 210), (xx * Q, 124 * Q), (xx * Q, y_fim * Q), 2 * Q)
        for y0, h in filas[::2]:
            pygame.draw.line(s, (150, 154, 164), (xx * Q, y0 * Q), (xx * Q, (y0 + 6) * Q), 3 * Q)
    # Molduras azul-escuras atrás da 1.ª fila de cada bloco
    for a, b in blocos:
        pygame.draw.line(s, (34, 44, 74), (a * Q, 124 * Q), (b * Q, 124 * Q), 3 * Q)
        for xx in (a, b):
            pygame.draw.line(s, (34, 44, 74), (xx * Q, 124 * Q), (xx * Q, (filas[1][0] + 4) * Q), 3 * Q)
    # Cadeiras e adeptos
    lugares = []
    for y0, h in filas:
        passo = h * 1.45
        for a, b in blocos:
            x = a + passo * 0.55
            while x < b - passo * 0.4:
                lugares.append((x, y0 + h, h))
                x += passo
    ocupados = set(rnd.sample(range(len(lugares)), k=min(8, len(lugares))))
    for i, (x, yb, h) in enumerate(lugares):
        _cadeira(s, x, yb, h, _cor_cadeira(rnd), Q)
        if i in ocupados:
            _adepto(s, x, yb, h, rnd, cor_casa, Q)
    # Muro da frente da bancada (por trás das placas de publicidade)
    pygame.draw.rect(s, (74, 78, 88), (0, y_fim * Q, W, H - y_fim * Q))
    pygame.draw.rect(s, (196, 198, 204), (0, y_fim * Q, W, 3 * Q))
    # Luz: em cima um pouco mais escuro
    sombra = pygame.Surface((W, H), pygame.SRCALPHA)
    for yy in range(0, H, 2):
        a = int(55 * max(0.0, 1 - yy / (H * 0.6)))
        pygame.draw.line(sombra, (8, 10, 18, a), (0, yy), (W, yy), 2)
    s.blit(sombra, (0, 0))
    final = pygame.transform.smoothscale(s, (WIDTH, altura))
    _cache[chave] = final
    return final


def marcador(s, centro_x: int, placar):
    """Marcador eletrónico ao centro, em cima: golos da casa, tempo, golos de fora."""
    caixa = pygame.Rect(0, 0, 300, 86)
    caixa.midtop = (centro_x, 0)
    pygame.draw.rect(s, (12, 12, 16), caixa)
    pygame.draw.rect(s, (70, 74, 84), caixa, 4)
    pygame.draw.line(s, (90, 94, 104), (caixa.left + 6, caixa.top + 4), (caixa.right - 6, caixa.top + 4), 1)
    if not placar:
        return
    sig_c, g_c, sig_f, g_f, tempo = placar
    f_led = pygame.font.SysFont("Consolas", 40, bold=True)
    f_peq = pygame.font.SysFont("Arial", 11, bold=True)
    for txt, x, cor in ((str(g_c), caixa.left + 56, (255, 70, 50)), (str(g_f), caixa.right - 56, (255, 70, 50)),
                        (tempo, caixa.centerx, (255, 190, 40))):
        img = f_led.render(txt, True, cor)
        brilho = pygame.transform.smoothscale(img, (img.get_width() + 8, img.get_height() + 8))
        brilho.set_alpha(60)
        s.blit(brilho, brilho.get_rect(center=(x, caixa.top + 42)))
        s.blit(img, img.get_rect(center=(x, caixa.top + 42)))
    for txt, x in ((sig_c, caixa.left + 56), (sig_f, caixa.right - 56)):
        img = f_peq.render(txt, True, (200, 205, 215))
        s.blit(img, img.get_rect(center=(x, caixa.top + 72)))
    img = f_peq.render("TEMPO", True, (200, 205, 215))
    s.blit(img, img.get_rect(center=(caixa.centerx, caixa.top + 72)))
    # Pequenas colunas de luzes dos lados (como os marcadores dos pavilhões)
    for lado in (-1, 1):
        x = caixa.centerx + lado * 118
        for i in range(5):
            pygame.draw.circle(s, (220, 160, 40) if i % 2 == 0 else (90, 70, 30), (x, caixa.top + 16 + i * 12), 3)
