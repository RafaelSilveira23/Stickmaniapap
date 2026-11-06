# -*- coding: utf-8 -*-
"""graficos.py - efeitos gráficos reutilizáveis (luz suave, ícones, título, brilho).

Para os desenhos ficarem com as bordas suaves (sem "escadinhas"), quase tudo é
desenhado primeiro com 3 ou 4 vezes o tamanho e depois reduzido com smoothscale
(super-amostragem). Os resultados ficam em cache, porque são sempre iguais.
"""
import math
import os
import pygame

_cache = {}


def _guardar(chave, criar):
    if chave not in _cache:
        if len(_cache) > 800:          # nunca cresce sem limite (as cores animadas criavam imagens novas)
            _cache.clear()
        _cache[chave] = criar()
    return _cache[chave]


# ====================================================================== #
# Luz e sombra suaves                                                    #
# ====================================================================== #

def gradiente_radial(largura: int, altura: int, cor, alpha_centro: int = 255,
                     dureza: float = 1.6) -> pygame.Surface:
    """
    Elipse que vai do centro (alpha_centro) até à borda (transparente).
    'dureza' controla a queda da luz: 1 = linear, maior = mais concentrada no centro.
    """
    def criar():
        # Calcula-se numa imagem pequena (rápido) e amplia-se com smoothscale (fica suave)
        pw, ph = max(2, min(64, largura)), max(2, min(64, altura))
        peq = pygame.Surface((pw, ph), pygame.SRCALPHA)
        cx, cy = (pw - 1) / 2, (ph - 1) / 2
        for y in range(ph):
            for x in range(pw):
                d = math.hypot((x - cx) / (pw / 2), (y - cy) / (ph / 2))
                a = max(0.0, 1.0 - d) ** dureza
                peq.set_at((x, y), (*cor[:3], int(alpha_centro * a)))
        return pygame.transform.smoothscale(peq, (max(1, largura), max(1, altura)))
    return _guardar(("radial", largura, altura, tuple(cor[:3]), alpha_centro, dureza), criar)


def luz(largura: int, altura: int, cor, intensidade: int = 120, dureza: float = 1.6) -> pygame.Surface:
    """
    Mancha de luz para somar ao ecrã (blit com special_flags=BLEND_RGB_ADD).
    A cor já vem multiplicada pela intensidade, por isso o preto não muda nada.
    """
    def criar():
        pw, ph = max(2, min(64, largura)), max(2, min(64, altura))
        peq = pygame.Surface((pw, ph))
        cx, cy = (pw - 1) / 2, (ph - 1) / 2
        for y in range(ph):
            for x in range(pw):
                d = math.hypot((x - cx) / (pw / 2), (y - cy) / (ph / 2))
                a = max(0.0, 1.0 - d) ** dureza * intensidade / 255
                peq.set_at((x, y), tuple(int(c * a) for c in cor[:3]))
        return pygame.transform.smoothscale(peq, (max(1, largura), max(1, altura)))
    return _guardar(("luz", largura, altura, tuple(cor[:3]), intensidade, dureza), criar)


def cone_luz(largura_base: int, altura: int, cor=(255, 245, 215), i_topo: int = 10,
             i_base: int = 38) -> pygame.Surface:
    """Feixe de um projetor (para BLEND_RGB_ADD): estreito em cima, largo e esbatido em baixo."""
    def criar():
        pw, ph = 48, 64
        peq = pygame.Surface((pw, ph))
        for y in range(ph):
            t = y / (ph - 1)
            meia = 0.03 + 0.47 * t
            for x in range(pw):
                d = abs((x + 0.5) / pw - 0.5) / meia
                a = max(0.0, 1.0 - d) ** 0.8 * (i_topo + (i_base - i_topo) * t) / 255
                a *= min(1.0, (1.0 - t) * 3.5)        # o fim do feixe também se esbate
                peq.set_at((x, y), tuple(int(c * a) for c in cor))
        return pygame.transform.smoothscale(peq, (largura_base, altura))
    return _guardar(("cone", largura_base, altura, tuple(cor), i_topo, i_base), criar)


def sombra_suave(largura: int, altura: int, alpha: int = 90) -> pygame.Surface:
    """Sombra no chão com a borda esbatida (mais realista do que uma elipse dura)."""
    return gradiente_radial(largura, altura, (10, 6, 2), alpha, dureza=0.9)


def brilho_retangulo(rect_size, cor, raio: int = 14, espalhar: int = 18, alpha: int = 120) -> pygame.Surface:
    """Halo de luz à volta de um retângulo arredondado (usado nos botões com foco)."""
    w, h = rect_size

    def criar():
        W, H = w + espalhar * 2, h + espalhar * 2
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        passos = 10
        for i in range(passos):
            k = i / passos
            a = int(alpha * (k ** 2) / passos * 2.2)
            pad = int(espalhar * (1 - k))
            pygame.draw.rect(s, (*cor[:3], a), (espalhar - pad, espalhar - pad, w + pad * 2, h + pad * 2),
                             border_radius=raio + pad)
        return s
    return _guardar(("halo", w, h, tuple(cor[:3]), raio, espalhar, alpha), criar)


def vinheta(largura: int, altura: int, forca: int = 170) -> pygame.Surface:
    """Escurece as bordas do ecrã (efeito de lente de câmara)."""
    def criar():
        s = pygame.Surface((largura, altura), pygame.SRCALPHA)
        s.fill((0, 0, 0, forca))
        buraco = gradiente_radial(int(largura * 1.35), int(altura * 1.6), (0, 0, 0), 255, dureza=0.55)
        s.blit(buraco, buraco.get_rect(center=(largura // 2, altura // 2)),
               special_flags=pygame.BLEND_RGBA_SUB)
        return s
    return _guardar(("vinheta", largura, altura, forca), criar)


# ====================================================================== #
# Ícones desenhados no código                                            #
# ====================================================================== #

def _pontos_engrenagem(cx, cy, r_ext, r_int, dentes):
    pts = []
    for i in range(dentes * 4):
        a = 2 * math.pi * i / (dentes * 4)
        r = r_ext if (i % 4) in (1, 2) else r_int
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def icone(nome: str, tamanho: int, cor=(255, 255, 255)) -> pygame.Surface:
    """
    Ícones simples desenhados com formas: 'engrenagem', 'jogar', 'trofeu', 'sair'.
    Desenhados 4x maiores e reduzidos, para ficarem suaves.
    """
    def criar():
        Q = 4
        T = tamanho * Q
        s = pygame.Surface((T, T), pygame.SRCALPHA)
        c = (*cor[:3], 255)
        m = T / 2
        if nome == "engrenagem":
            pygame.draw.polygon(s, c, _pontos_engrenagem(m, m, T * 0.48, T * 0.36, 8))
            pygame.draw.circle(s, c, (m, m), T * 0.36)
            pygame.draw.circle(s, (0, 0, 0, 0), (m, m), T * 0.15)
        elif nome == "jogar":
            pygame.draw.polygon(s, c, [(T * 0.28, T * 0.18), (T * 0.28, T * 0.82), (T * 0.84, T * 0.5)])
        elif nome == "trofeu":
            # Taça
            pygame.draw.polygon(s, c, [(T * 0.24, T * 0.14), (T * 0.76, T * 0.14), (T * 0.70, T * 0.42),
                                       (T * 0.56, T * 0.56), (T * 0.44, T * 0.56), (T * 0.30, T * 0.42)])
            pygame.draw.ellipse(s, c, (T * 0.24, T * 0.06, T * 0.52, T * 0.16))
            # Asas
            for x0 in (T * 0.06, T * 0.68):
                pygame.draw.ellipse(s, c, (x0, T * 0.16, T * 0.26, T * 0.26), int(T * 0.06))
            # Pé e base
            pygame.draw.rect(s, c, (T * 0.45, T * 0.54, T * 0.10, T * 0.20))
            pygame.draw.rect(s, c, (T * 0.28, T * 0.74, T * 0.44, T * 0.12), border_radius=int(T * 0.03))
        elif nome == "alvo":
            # Alvo (círculos) para o modo teste
            for k, r in enumerate((0.46, 0.32, 0.18)):
                pygame.draw.circle(s, c, (m, m), T * r, int(T * 0.07) if k < 2 else 0)
            pygame.draw.line(s, c, (m, T * 0.0), (m, T * 0.22), int(T * 0.06))
            pygame.draw.line(s, c, (m, T * 0.78), (m, T), int(T * 0.06))
        elif nome == "avancar":
            # Dois triângulos (avançar rápido = simular)
            for x0 in (T * 0.12, T * 0.48):
                pygame.draw.polygon(s, c, [(x0, T * 0.2), (x0, T * 0.8), (x0 + T * 0.4, T * 0.5)])
        elif nome == "recomecar":
            # Seta em círculo
            w = int(T * 0.11)
            ret = pygame.Rect(T * 0.16, T * 0.16, T * 0.68, T * 0.68)
            pygame.draw.arc(s, c, ret, math.radians(70), math.radians(360), w)
            pygame.draw.polygon(s, c, [(T * 0.50, T * 0.02), (T * 0.72, T * 0.18), (T * 0.48, T * 0.32)])
        elif nome == "casa":
            pygame.draw.polygon(s, c, [(T * 0.5, T * 0.1), (T * 0.92, T * 0.5), (T * 0.08, T * 0.5)])
            pygame.draw.rect(s, c, (T * 0.2, T * 0.46, T * 0.6, T * 0.42))
            pygame.draw.rect(s, (0, 0, 0, 0), (T * 0.42, T * 0.62, T * 0.16, T * 0.26))
        elif nome == "coracao":
            pygame.draw.circle(s, c, (T * 0.32, T * 0.36), T * 0.2)
            pygame.draw.circle(s, c, (T * 0.68, T * 0.36), T * 0.2)
            pygame.draw.polygon(s, c, [(T * 0.13, T * 0.42), (T * 0.87, T * 0.42), (T * 0.5, T * 0.88)])
        elif nome == "livro":
            pygame.draw.polygon(s, c, [(T * 0.08, T * 0.2), (T * 0.47, T * 0.26), (T * 0.47, T * 0.86),
                                       (T * 0.08, T * 0.78)])
            pygame.draw.polygon(s, c, [(T * 0.92, T * 0.2), (T * 0.53, T * 0.26), (T * 0.53, T * 0.86),
                                       (T * 0.92, T * 0.78)])
        elif nome == "moeda":
            pygame.draw.circle(s, c, (m, m), T * 0.44)
            pygame.draw.circle(s, (0, 0, 0, 0), (m, m), T * 0.32)
            pygame.draw.rect(s, c, (T * 0.44, T * 0.28, T * 0.12, T * 0.44), border_radius=int(T * 0.04))
        elif nome == "estrela":
            pts = []
            for i in range(10):
                ang = -math.pi / 2 + i * math.pi / 5
                r = T * (0.48 if i % 2 == 0 else 0.2)
                pts.append((m + r * math.cos(ang), m + r * math.sin(ang)))
            pygame.draw.polygon(s, c, pts)
        elif nome == "cruz":
            pygame.draw.rect(s, c, (T * 0.38, T * 0.1, T * 0.24, T * 0.8), border_radius=int(T * 0.05))
            pygame.draw.rect(s, c, (T * 0.1, T * 0.38, T * 0.8, T * 0.24), border_radius=int(T * 0.05))
        elif nome == "jogador":
            # Um jogador: cabeça e tronco (carreira de jogador)
            pygame.draw.circle(s, c, (m, T * 0.26), T * 0.17)
            pygame.draw.ellipse(s, c, (T * 0.18, T * 0.48, T * 0.64, T * 0.56))
            pygame.draw.rect(s, (0, 0, 0, 0), (0, T * 0.86, T, T * 0.14))
        elif nome == "globo":
            # Globo (jogar online): círculo com o equador, dois paralelos e um meridiano
            w = int(T * 0.07)
            pygame.draw.circle(s, c, (m, m), T * 0.44, w)
            pygame.draw.ellipse(s, c, (T * 0.30, T * 0.06, T * 0.40, T * 0.88), w)
            pygame.draw.line(s, c, (T * 0.06, m), (T * 0.94, m), w)
            for y in (0.28, 0.72):
                meia = math.sqrt(max(0.0, 0.44 ** 2 - (y - 0.5) ** 2)) * T
                pygame.draw.line(s, c, (m - meia, T * y), (m + meia, T * y), w)
            pygame.draw.line(s, c, (m, T * 0.06), (m, T * 0.94), w)
        elif nome == "sair":
            # Símbolo de "desligar"
            w = int(T * 0.11)
            ret = pygame.Rect(T * 0.16, T * 0.18, T * 0.68, T * 0.68)
            pygame.draw.arc(s, c, ret, math.radians(-50), math.radians(230), w)
            pygame.draw.rect(s, c, (m - w / 2, T * 0.08, w, T * 0.44), border_radius=w // 2)
        return pygame.transform.smoothscale(s, (tamanho, tamanho))
    return _guardar(("icone", nome, tamanho, tuple(cor[:3])), criar)


CAMINHO_EMBLEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui", "emblema_sticks.png")


def emblema_sticks(tamanho: int) -> pygame.Surface:
    """
    Emblema do jogo: dois sticks de hóquei em patins cruzados com a bola ao meio.
    Usa a imagem assets/ui/emblema_sticks.png (o fundo foi tirado com ferramentas/preparar_emblema.py);
    se a imagem não existir, desenha uma versão simples no código.
    """
    def carregar():
        img = pygame.image.load(CAMINHO_EMBLEMA)
        if pygame.display.get_surface() is not None:
            img = img.convert_alpha()
        return pygame.transform.smoothscale(img, (tamanho, tamanho))
    if os.path.exists(CAMINHO_EMBLEMA):
        try:
            return _guardar(("emblema_img", tamanho), carregar)
        except pygame.error:
            pass
    return _emblema_desenhado(tamanho)


def _emblema_desenhado(tamanho: int) -> pygame.Surface:
    """Versão de reserva do emblema, desenhada com formas."""
    def criar():
        Q = 4
        T = tamanho * Q
        s = pygame.Surface((T, T), pygame.SRCALPHA)
        larg = T * 0.075

        def stick(sinal):
            # Cabo reto de cima até perto do fundo, e a pá curva no fim
            x0, y0 = T / 2 - sinal * T * 0.36, T * 0.06
            x1, y1 = T / 2 + sinal * T * 0.20, T * 0.74
            pts = [(x0 + (x1 - x0) * k / 20, y0 + (y1 - y0) * k / 20) for k in range(21)]
            # Pá: curva que sai para o lado
            for k in range(1, 9):
                a = k / 8 * math.pi / 2
                pts.append((x1 + sinal * T * 0.13 * math.sin(a), y1 + T * 0.13 * (1 - math.cos(a)) + T * 0.04 * math.sin(a)))
            for cor, w in (((20, 14, 8, 255), larg * 1.5), ((214, 168, 104, 255), larg), ((240, 206, 150, 255), larg * 0.35)):
                for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                    pygame.draw.line(s, cor, (ax, ay), (bx, by), int(w))
                    pygame.draw.circle(s, cor, (bx, by), w / 2)
            # Fita preta no punho
            pygame.draw.line(s, (25, 25, 30, 255), pts[0], pts[3], int(larg * 1.1))

        stick(1)
        stick(-1)
        # Bola laranja com brilho
        cx, cy, r = T / 2, T * 0.80, T * 0.095
        pygame.draw.circle(s, (20, 10, 4, 255), (cx, cy), r * 1.25)
        pygame.draw.circle(s, (255, 140, 30, 255), (cx, cy), r)
        pygame.draw.circle(s, (255, 205, 130, 255), (cx - r * 0.35, cy - r * 0.35), r * 0.35)
        return pygame.transform.smoothscale(s, (tamanho, tamanho))
    return _guardar(("emblema", tamanho), criar)


# ====================================================================== #
# Texto com contorno, gradiente e brilho                                 #
# ====================================================================== #

def titulo_estilizado(txt: str, fonte: pygame.font.Font, cor_topo, cor_base,
                      cor_contorno=(10, 14, 30), contorno: int = 4,
                      cor_brilho=None) -> pygame.Surface:
    """
    Texto grande de título: preenchimento em gradiente vertical, contorno grosso
    e (opcional) um brilho esbatido por trás.
    """
    def criar():
        base = fonte.render(txt, True, (255, 255, 255))
        w, h = base.get_size()
        pad = contorno + 26
        s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)

        if cor_brilho is not None:
            glow = fonte.render(txt, True, cor_brilho)
            camada = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            camada.blit(glow, (pad, pad))
            camada = pygame.transform.gaussian_blur(camada, 14)
            s.blit(camada, (0, 0))
            s.blit(camada, (0, 0))

        # Contorno: o texto escuro desenhado à volta, num círculo de deslocamentos
        sombra = fonte.render(txt, True, cor_contorno)
        for ang in range(0, 360, 20):
            dx = round(contorno * math.cos(math.radians(ang)))
            dy = round(contorno * math.sin(math.radians(ang)))
            s.blit(sombra, (pad + dx, pad + dy))
        s.blit(sombra, (pad + 2, pad + contorno + 3))            # sombra projetada

        # Preenchimento com gradiente
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            k = y / max(1, h - 1)
            cor = [int(cor_topo[i] + (cor_base[i] - cor_topo[i]) * k) for i in range(3)]
            pygame.draw.line(grad, (*cor, 255), (0, y), (w, y))
        preench = base.copy()
        preench.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(preench, (pad, pad))
        # Reflexo: metade de cima um pouco mais clara
        reflexo = base.copy()
        reflexo.fill((255, 255, 255, 60), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(reflexo, (pad, pad), (0, 0, w, int(h * 0.45)))
        return s
    return _guardar(("titulo", txt, id(fonte), tuple(cor_topo), tuple(cor_base), contorno,
                     None if cor_brilho is None else tuple(cor_brilho)), criar)
