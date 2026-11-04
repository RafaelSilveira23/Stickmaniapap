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


def bancada(altura: int, cor_casa=(30, 80, 180), semente: int = 4) -> pygame.Surface:
    """Parede, faixas, bancada com cadeiras e adeptos (sem o marcador). Fica em cache."""
    chave = ("bancada", altura, tuple(cor_casa), semente)
    if chave in _cache:
        return _cache[chave]
    Q = 2
    W, H = WIDTH * Q, altura * Q
    s = pygame.Surface((W, H))
    rnd = random.Random(semente)

    # Parede de cima (escura) com pilares
    for y in range(int(80 * Q)):
        k = y / (80 * Q)
        c = int(40 + 22 * k)
        pygame.draw.line(s, (c, c + 3, c + 10), (0, y), (W, y))
    for px in (0, 330, 950, 1280):
        pygame.draw.rect(s, (86, 90, 100), ((px - 14) * Q, 0, 28 * Q, 96 * Q))
        pygame.draw.rect(s, (110, 114, 124), ((px - 14) * Q, 0, 6 * Q, 96 * Q))
    # Faixas dos patrocinadores na parede
    for i, (x, w) in enumerate(((22, 210), (360, 150), (800, 140), (970, 200), (1180, 120))):
        tex = textura_placa(i + 2, 300, 70)
        s.blit(pygame.transform.smoothscale(tex, (w * Q, 40 * Q)), (x * Q, 14 * Q))

    # Varanda de cima com corrimão
    y_var = 84
    pygame.draw.rect(s, (160, 162, 168), (0, y_var * Q, W, 10 * Q))
    pygame.draw.rect(s, (195, 197, 202), (0, y_var * Q, W, 2 * Q))
    pygame.draw.line(s, (120, 124, 134), (0, (y_var - 16) * Q), (W, (y_var - 16) * Q), 2 * Q)
    for x in range(10, WIDTH, 44):
        pygame.draw.line(s, (120, 124, 134), (x * Q, (y_var - 16) * Q), (x * Q, y_var * Q), Q)
    # Dois adeptos de pé na varanda
    for x in (215, 1040):
        _adepto(s, x * Q, (y_var - 2) * Q, 26 * Q, rnd, cor_casa, de_pe=True)

    # Bancada: filas de cadeiras (as de baixo estão mais perto: um pouco maiores)
    y = y_var + 10
    filas = []
    k = 0
    while y < altura - 26:
        h = 15 + k * 0.8
        filas.append((y, h))
        y += h
        k += 1
    escadas = [(615, 50), (20, 30), (1255, 30)]     # (x do centro, largura)
    cores = [(38, 112, 214), (38, 112, 214), (38, 112, 214), (232, 236, 242), (232, 236, 242), (98, 168, 232)]
    for y, h in filas:
        # Degrau de cimento
        pygame.draw.rect(s, (186, 188, 194), (0, (y + h * 0.62) * Q, W, (h * 0.38 + 1) * Q))
        pygame.draw.line(s, (150, 152, 160), (0, (y + h * 0.62) * Q), (W, (y + h * 0.62) * Q), Q)
        pygame.draw.rect(s, (168, 170, 176), (0, y * Q, W, h * 0.62 * Q))
        passo = h * 1.12
        x = passo / 2
        while x < WIDTH:
            if any(abs(x - ex) < ew / 2 + passo * 0.45 for ex, ew in escadas):
                x += passo
                continue
            cor = rnd.choice(cores)
            cad = pygame.Rect(0, 0, round(h * 0.86 * Q), round(h * 0.6 * Q))
            cad.midbottom = (round(x * Q), round((y + h * 0.66) * Q))
            pygame.draw.rect(s, tuple(max(0, c - 40) for c in cor), cad.move(0, Q), border_radius=int(h * 0.2 * Q))
            pygame.draw.rect(s, cor, cad, border_radius=int(h * 0.2 * Q))
            pygame.draw.rect(s, tuple(min(255, c + 25) for c in cor),
                             (cad.left + Q, cad.top + Q, cad.width - 2 * Q, cad.height * 0.3), border_radius=int(h * 0.15 * Q))
            if rnd.random() < 0.07:
                _adepto(s, x * Q, (y + h * 0.62) * Q, h * 1.15 * Q, rnd, cor_casa)
            x += passo
    # Escadas: degraus mais claros e corrimão
    for ex, ew in escadas:
        for y, h in filas:
            for j in range(2):
                cor = (205, 207, 212) if j == 0 else (172, 174, 180)
                pygame.draw.rect(s, cor, ((ex - ew / 2) * Q, (y + j * h / 2) * Q, ew * Q, (h / 2 + 1) * Q))
        if ew > 40:
            for lado in (-1, 1):
                xx = (ex + lado * ew * 0.42) * Q
                pygame.draw.line(s, (130, 134, 144), (xx, (y_var + 10) * Q), (xx, (altura - 30) * Q), 2 * Q)
    # Muro da frente da bancada (por trás das placas)
    pygame.draw.rect(s, (46, 50, 60), (0, (altura - 26) * Q, W, 26 * Q))
    pygame.draw.line(s, (120, 124, 134), (0, (altura - 26) * Q), (W, (altura - 26) * Q), 2 * Q)
    # Luz do pavilhão: o topo um pouco mais escuro
    sombra = pygame.Surface((W, H), pygame.SRCALPHA)
    for yy in range(0, H, 2):
        a = int(70 * max(0.0, 1 - yy / (H * 0.7)))
        pygame.draw.line(sombra, (6, 8, 16, a), (0, yy), (W, yy), 2)
    s.blit(sombra, (0, 0))
    final = pygame.transform.smoothscale(s, (WIDTH, altura))
    _cache[chave] = final
    return final


def _adepto(s, x, y_base, alt, rnd, cor_casa, de_pe=False):
    """Um adepto sentado (ou de pé): corpo com a camisola e cabeça."""
    pele = rnd.choice([(232, 192, 158), (214, 168, 128), (180, 128, 90), (130, 88, 60), (240, 206, 176)])
    cabelo = rnd.choice([(40, 28, 20), (66, 42, 24), (20, 20, 22), (120, 85, 50), (170, 140, 95)])
    camisola = cor_casa if rnd.random() < 0.4 else rnd.choice(
        [(200, 40, 40), (40, 140, 80), (230, 230, 235), (60, 60, 70), (230, 160, 40)])
    larg = alt * (0.42 if de_pe else 0.55)
    corpo_h = alt * (0.62 if de_pe else 0.48)
    corpo = pygame.Rect(0, 0, round(larg), round(corpo_h))
    corpo.midbottom = (round(x), round(y_base))
    pygame.draw.rect(s, camisola, corpo, border_top_left_radius=int(larg * 0.4), border_top_right_radius=int(larg * 0.4))
    if de_pe:
        pygame.draw.rect(s, (50, 55, 70), (corpo.left + larg * 0.1, corpo.bottom, larg * 0.8, alt * 0.35))
    r = alt * 0.15
    cab = (corpo.centerx, corpo.top - r * 0.8)
    pygame.draw.circle(s, pele, cab, r)
    pygame.draw.circle(s, cabelo, (cab[0], cab[1] - r * 0.3), r, draw_top_left=True, draw_top_right=True)


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
