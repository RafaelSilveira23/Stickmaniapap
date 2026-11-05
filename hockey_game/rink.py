# -*- coding: utf-8 -*-
"""rink.py - ringue oficial de hóquei em patins com piso de madeira, tabelas e balizas reais."""
import os
import pygame
import fontes
from settings import *
from team import carregar_logo_equipa, obter_info_equipa
from cores import cor_linhas_campo, misturar, cor_texto_sobre
from baliza import criar_baliza, criar_baliza_camera
from camera import Camera
from graficos import luz

# Super-amostragem do piso: o campo plano é desenhado com o dobro da resolução
# e só no fim é reduzido (as linhas ficam suaves, sem "escadinhas").
Q_PISO = 2

# ---------- Câmara em perspetiva ----------
CAM_TOPO       = 142    # y no ecrã da linha do fundo do ringue
CAM_BASE       = 522    # y no ecrã da linha da frente do ringue
CAM_LARG_TOPO  = 1010   # largura do ringue no fundo (mais estreito = mais perspetiva)
CAM_LARG_BASE  = 1230   # largura do ringue à frente
ALTURA_TABELA  = 13     # altura das tabelas (px do mundo)
FAIXA_PUB_H    = 24     # altura da faixa de publicidade por cima da tabela do fundo (px do ecrã)


def _pasta_ui():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "extras_ui")


class Rink:
    def __init__(self, equipa_casa: str = "fc_porto"):
        self.equipa_casa = equipa_casa
        self.cor_linhas  = self._calcular_cor_linhas()
        self.rect = pygame.Rect(RINK_X, RINK_Y, RINK_W, RINK_H)
        cy = self.rect.centery

        # A câmara transforma o campo plano (onde a física acontece) no ecrã em perspetiva
        self.camera = Camera(RINK_X, RINK_Y, RINK_W, RINK_H,
                             CAM_TOPO, CAM_BASE, CAM_LARG_TOPO, CAM_LARG_BASE, WIDTH / 2)

        ui = _pasta_ui()
        publico_raw = pygame.image.load(os.path.join(ui, "publico_tile.png")).convert_alpha()

        self._pub   = publico_raw
        self._pub_w = publico_raw.get_width()
        self._pub_h = publico_raw.get_height()

        # ── Gerar Piso de Madeira Real (Tábua Corrida / Parquet de Hóquei) ──
        self._campo = self._gerar_piso_madeira(RINK_W, RINK_H, Q_PISO)

        # ── Balizas (desenhadas no código, ver baliza.py) ─────────────────
        BSH = 88
        self.baliza_boca_h = 66
        PROF = 38                                   # profundidade da baliza
        self.BSW_FRENTE = PROF + 4                  # largura usada nas colisões
        self.BSW_ATRAS  = PROF + 4
        (self._bal_esq, self._bal_esq_frente,
         self._ancora_esq) = criar_baliza(self.baliza_boca_h, profundidade=PROF, virada_para="direita")
        (self._bal_dir, self._bal_dir_frente,
         self._ancora_dir) = criar_baliza(self.baliza_boca_h, profundidade=PROF, virada_para="esquerda")

        # ── Linhas de Golo e Posições (Espaço atrás da baliza para patinar) ──
        self.linha_golo_esq_x = self.rect.left + BALIZA_OFFSET       # X ~ 185
        self.linha_golo_dir_x = self.rect.right - BALIZA_OFFSET      # X ~ 1095

        self.baliza_topo_y = cy - self.baliza_boca_h // 2
        self.baliza_base_y = cy + self.baliza_boca_h // 2

        # Posições de desenho: a âncora (meio da boca, no chão) fica sobre a linha de golo
        self._pos_baliza_esq = (self.linha_golo_esq_x - self._ancora_esq[0], cy - self._ancora_esq[1])
        self._pos_baliza_dir = (self.linha_golo_dir_x - self._ancora_dir[0], cy - self._ancora_dir[1])

        # Retângulos interiores de golo
        gw = 32
        self.baliza_esq = pygame.Rect(self.linha_golo_esq_x - gw, self.baliza_topo_y, gw, self.baliza_boca_h)
        self.baliza_dir = pygame.Rect(self.linha_golo_dir_x,     self.baliza_topo_y, gw, self.baliza_boca_h)

        # Obstáculos físicos das redes (jogadores patinam à volta sem atravessar a rede)
        self.obstaculo_baliza_esq = pygame.Rect(
            self.linha_golo_esq_x - self.BSW_FRENTE + 4,
            cy - BSH // 2 + 10,
            self.BSW_FRENTE - 8,
            BSH - 20
        )
        self.obstaculo_baliza_dir = pygame.Rect(
            self.linha_golo_dir_x + 4,
            cy - BSH // 2 + 10,
            self.BSW_ATRAS - 8,
            BSH - 20
        )

        # Zonas de defesa dos Guarda-Redes (sobre a linha de golo)
        self.zona_gr_esq = pygame.Rect(self.linha_golo_esq_x - 12, self.baliza_topo_y, 24, self.baliza_boca_h)
        self.zona_gr_dir = pygame.Rect(self.linha_golo_dir_x - 12, self.baliza_topo_y, 24, self.baliza_boca_h)

        self._surf = self._construir()

    def _gerar_piso_madeira(self, w: int, h: int, Q: int = 1) -> pygame.Surface:
        """
        Piso de madeira envernizada (tábua corrida), com Q vezes a resolução.
        Cada tábua tem um tom ligeiramente diferente e veios da madeira, como no real.
        Usa sempre a mesma "semente", por isso o piso é sempre igual.
        """
        import random
        rnd = random.Random(11)
        W, H = w * Q, h * Q
        surf = pygame.Surface((W, H))
        surf.fill((224, 178, 122))
        tabua_h = 16 * Q
        comp = 115 * Q

        def tom(c):
            return max(0, min(255, int(c)))

        for i, y in enumerate(range(0, H, tabua_h)):
            x = ((i * 43) % 95) * Q - comp
            while x < W:
                v = rnd.uniform(-8, 8)
                q = rnd.uniform(-4, 4)                 # umas tábuas mais quentes, outras mais claras
                cor = (tom(225 + v + q), tom(178 + v), tom(121 + v - q))
                pygame.draw.rect(surf, cor, (x, y, comp, tabua_h))
                # Veios: riscos finos um pouco mais escuros ao longo da tábua
                for _ in range(rnd.randint(3, 6)):
                    gy = y + rnd.uniform(2, tabua_h - 2)
                    gx0 = x + rnd.uniform(0, comp * 0.5)
                    gx1 = min(x + comp - 2, gx0 + rnd.uniform(comp * 0.25, comp * 0.8))
                    d = rnd.uniform(6, 15)
                    pygame.draw.line(surf, (tom(cor[0] - d), tom(cor[1] - d), tom(cor[2] - d * 0.8)),
                                     (gx0, gy), (gx1, gy + rnd.uniform(-1, 1) * Q), 1)
                # Nó da madeira de vez em quando
                if rnd.random() < 0.06:
                    nx, ny = x + rnd.uniform(10, comp - 10), y + tabua_h / 2
                    pygame.draw.ellipse(surf, (tom(cor[0] - 18), tom(cor[1] - 20), tom(cor[2] - 16)),
                                        (nx - 4 * Q, ny - 2 * Q, 8 * Q, 4 * Q))
                # Junta entre tábuas (topo)
                pygame.draw.line(surf, (190, 145, 92), (x, y), (x, y + tabua_h), Q)
                x += comp
            # Junta entre filas de tábuas
            pygame.draw.line(surf, (196, 150, 96), (0, y), (W, y), Q)

        # Sombra junto às tabelas: o piso fica um pouco mais escuro perto da borda
        sombra = pygame.Surface((W, H), pygame.SRCALPHA)
        n = 22 * Q
        for k in range(n):
            a = int(85 * (1 - k / n) ** 2.2)
            pygame.draw.rect(sombra, (60, 30, 6, a), (k, k, W - 2 * k, H - 2 * k), 2,
                             border_radius=max(0, CANTO * Q - k))
        surf.blit(sombra, (0, 0))
        return surf

    # ================================================================== #
    # Construção da imagem do ringue (feita uma vez; muda com a equipa da casa)
    # ================================================================== #

    def _construir_plano(self) -> pygame.Surface:
        """
        Piso visto de cima (plano), com todas as linhas, com Q_PISO vezes a resolução.
        Depois é posto em perspetiva.
        """
        Q = Q_PISO
        r = self.rect
        surf = self._mascara_cantos(self._campo)

        def P(x, y):                      # mundo -> imagem do plano
            return ((x - r.left) * Q, (y - r.top) * Q)

        def ret(x, y, w, h):
            return pygame.Rect(round((x - r.left) * Q), round((y - r.top) * Q), round(w * Q), round(h * Q))

        cx, cy = r.center
        cor_linha = self.cor_linhas
        lw = (LINHA + 1) * Q
        # Linha do meio, círculo central e emblema
        pygame.draw.line(surf, cor_linha, P(cx, r.top), P(cx, r.bottom), lw)
        pygame.draw.circle(surf, cor_linha, P(cx, cy), RAIO_CENTRO * Q, lw)
        pygame.draw.circle(surf, cor_linha, P(cx, cy), 5 * Q)
        self._desenhar_centro_emblema(surf, *P(cx, cy), escala=Q)
        # Grandes áreas
        pygame.draw.rect(surf, cor_linha, ret(self.linha_golo_esq_x, cy - AREA_H // 2, AREA_W, AREA_H), lw)
        pygame.draw.rect(surf, cor_linha, ret(self.linha_golo_dir_x - AREA_W, cy - AREA_H // 2, AREA_W, AREA_H), lw)
        # Linhas de golo vermelhas
        for gx in (self.linha_golo_esq_x, self.linha_golo_dir_x):
            pygame.draw.line(surf, (220, 40, 40), P(gx, self.baliza_topo_y), P(gx, self.baliza_base_y), 3 * Q)
        # Marcas de penálti e de livre direto
        for gx, sinal in ((self.linha_golo_esq_x, 1), (self.linha_golo_dir_x, -1)):
            pygame.draw.circle(surf, cor_linha, P(gx + 85 * sinal, cy), 4 * Q)
            pygame.draw.circle(surf, cor_linha, P(gx + 130 * sinal, cy), 3 * Q)
        # Linha de proteção atrás das balizas
        pygame.draw.arc(surf, cor_linha, ret(self.linha_golo_esq_x - 65, cy - 45, 65, 90), 1.57, 4.71, 2 * Q)
        pygame.draw.arc(surf, cor_linha, ret(self.linha_golo_dir_x, cy - 45, 65, 90), -1.57, 1.57, 2 * Q)
        return surf

    def _por_em_perspetiva(self, plano: pygame.Surface, destino: pygame.Surface):
        """
        Desenha o piso plano em perspetiva, linha a linha:
        para cada linha do ecrã descobre-se que linha do campo lhe corresponde
        e estica-se essa linha para a largura certa.
        Para as linhas do campo ficarem suaves (sem "escadinhas"), fazemos tudo
        com o dobro da resolução e no fim reduzimos com smoothscale.
        """
        cam = self.camera
        Q = Q_PISO                                       # o plano já vem com esta resolução
        plano2 = plano
        y0, y1 = int(cam.topo), int(cam.base) + 1
        temp = pygame.Surface((WIDTH * Q, (y1 - y0) * Q), pygame.SRCALPHA)
        for linha_ecra in range((y1 - y0) * Q):
            sy = y0 + (linha_ecra + 0.5) / Q
            _, wy = cam.desprojetar(cam.cx, sy)
            linha = min(RINK_H * Q - 1, max(0, int((wy - RINK_Y) * Q)))
            largura = cam.fator(wy) * RINK_W * Q
            fatia = plano2.subsurface((0, linha, RINK_W * Q, 1))
            esticada = pygame.transform.smoothscale(fatia, (max(1, round(largura)), 1))
            temp.blit(esticada, (round(cam.cx * Q - largura / 2), linha_ecra))
        piso = pygame.transform.smoothscale(temp, (WIDTH, y1 - y0))
        self._iluminar_piso(piso)
        destino.blit(piso, (0, y0))

    def _iluminar_piso(self, piso: pygame.Surface):
        """
        Luz do pavilhão no piso envernizado:
          - os cantos e o fundo do ringue ficam um pouco mais escuros (vinheta);
          - os projetores do teto refletem-se no verniz (manchas de brilho suaves).
        Só mexe nas cores (RGB): as partes transparentes à volta do ringue continuam transparentes.
        """
        import math
        w, h = piso.get_size()
        # Vinheta: imagem pequena calculada ponto a ponto e ampliada (fica suave)
        pw, ph = 64, 24
        peq = pygame.Surface((pw, ph))
        for y in range(ph):
            ty = y / (ph - 1)
            for x in range(pw):
                dx = (x + 0.5) / pw * 2 - 1
                k = 1.0 - 0.20 * dx ** 4 - 0.10 * (1 - ty) ** 2
                c = max(0, min(255, int(255 * k)))
                peq.set_at((x, y), (c, c, c))
        piso.blit(pygame.transform.smoothscale(peq, (w, h)), (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # Reflexos dos projetores (mais largos do que altos por causa da perspetiva)
        brilho = pygame.Surface((w, h))
        cor = (255, 246, 225)
        geral = luz(int(w * 0.8), int(h * 0.9), cor, 26, 1.2)
        brilho.blit(geral, geral.get_rect(center=(w // 2, int(h * 0.5))), special_flags=pygame.BLEND_RGB_ADD)
        for fx in (0.18, 0.39, 0.61, 0.82):
            for fy, tam, inten in ((0.30, 0.85, 34), (0.72, 1.15, 26)):
                mancha = luz(int(230 * tam), int(70 * tam), cor, inten, 1.5)
                # Os reflexos de baixo afastam-se do centro (perspetiva)
                x = w / 2 + (fx - 0.5) * w * (0.86 + 0.12 * fy)
                brilho.blit(mancha, mancha.get_rect(center=(round(x), round(h * fy))),
                            special_flags=pygame.BLEND_RGB_ADD)
        piso.blit(brilho, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _contorno_ringue(self, passos_canto: int = 14) -> list:
        """Pontos (do mundo) à volta do ringue com cantos arredondados, no sentido do relógio."""
        import math
        r, R = self.rect, CANTO
        cantos = [  # (centro do arco, ângulo inicial)
            ((r.left + R,  r.top + R),    180),
            ((r.right - R, r.top + R),    270),
            ((r.right - R, r.bottom - R),   0),
            ((r.left + R,  r.bottom - R),  90),
        ]
        pts = []
        for (ccx, ccy), a0 in cantos:
            for k in range(passos_canto + 1):
                a = math.radians(a0 + 90 * k / passos_canto)
                pts.append((ccx + R * math.cos(a), ccy + R * math.sin(a)))
        return pts

    def _desenhar_tabelas(self, surf):
        """
        Tabelas baixas (cinzento-claro) com um corrimão grosso na cor da equipa da casa.
        Cada pedaço do contorno do ringue vira um retângulo "de pé" na perspetiva.
        Desenhamos tudo com o dobro do tamanho e reduzimos no fim (bordas suaves).
        """
        cam = self.camera
        Q = 2
        camada = pygame.Surface((WIDTH * Q, HEIGHT * Q), pygame.SRCALPHA)
        pts = self._contorno_ringue(20)
        r = self.rect
        chao, topo = [], []
        for wx, wy in pts:
            frente = wy > r.bottom - CANTO
            h = ALTURA_TABELA * (0.75 if frente else 1.0) * cam.fator(wy)
            sx, sy = cam.projetar(wx, wy)
            chao.append((sx * Q, sy * Q))
            topo.append((sx * Q, (sy - h) * Q))

        n = len(pts)
        segs = sorted(range(n), key=lambda i: pts[i][1] + pts[(i + 1) % n][1])
        for i in segs:
            k = (i + 1) % n
            (ax, ay), (bx, by) = pts[i], pts[k]
            nx, ny = by - ay, -(bx - ax)
            comp = max(1e-6, (nx * nx + ny * ny) ** 0.5)
            # Painéis do fundo um pouco mais claros que os dos lados
            luz = 0.92 + 0.08 * max(0.0, -ny / comp)
            cor = tuple(int(c * luz) for c in (222, 226, 234))
            quad = [chao[i], chao[k], topo[k], topo[i]]
            pygame.draw.polygon(camada, cor, quad)
            pygame.draw.polygon(camada, cor, quad, 2)

        # Rodapé escuro junto ao piso
        pygame.draw.lines(camada, (70, 78, 96), True, chao, 3 * Q // 2)
        # Corrimão: contorno escuro + cor da equipa + brilho
        cor_rail = self.cor_linhas
        pygame.draw.lines(camada, misturar(cor_rail, (8, 10, 20), 0.55), True, topo, 7 * Q)
        pygame.draw.lines(camada, cor_rail, True, topo, 5 * Q)
        pygame.draw.lines(camada, misturar(cor_rail, (255, 255, 255), 0.4), True,
                          [(x, y - 1.5 * Q) for x, y in topo], Q)
        surf.blit(pygame.transform.smoothscale(camada, (WIDTH, HEIGHT)), (0, 0))

    def _desenhar_placards_perspetiva(self, surf):
        """Faixa de publicidade azul-escura por cima da tabela do fundo, a toda a largura."""
        cam = self.camera
        r = self.rect
        topo_tabela = cam.ecra_y(r.top) - ALTURA_TABELA * cam.fator(r.top)
        faixa = pygame.Rect(0, round(topo_tabela - FAIXA_PUB_H - 3), WIDTH, FAIXA_PUB_H)
        self._faixa_pub = faixa

        info = obter_info_equipa(self.equipa_casa)
        cor_base = misturar(info.get("cor_primaria", (18, 40, 100)), (6, 10, 30), 0.45)
        pygame.draw.rect(surf, cor_base, faixa)
        pygame.draw.line(surf, misturar(cor_base, (255, 255, 255), 0.35), faixa.topleft, faixa.topright, 2)
        pygame.draw.line(surf, misturar(cor_base, (0, 0, 0), 0.5), faixa.bottomleft, faixa.bottomright, 2)

        nome = info.get("nome", "").upper()
        textos = ["HÓQUEI EM PATINS", nome, "JOGO • PAIXÃO • TRADIÇÃO", "STICKMANIA", nome]
        fonte = fontes.SysFont("Arial", 13, bold=True)
        n = len(textos)
        for i, txt in enumerate(textos):
            x0 = faixa.width * i // n
            x1 = faixa.width * (i + 1) // n
            if i:
                pygame.draw.line(surf, misturar(cor_base, (255, 255, 255), 0.25),
                                 (x0, faixa.top + 3), (x0, faixa.bottom - 3), 2)
            t = fonte.render(txt, True, (240, 244, 252))
            surf.blit(t, ((x0 + x1) // 2 - t.get_width() // 2, faixa.centery - t.get_height() // 2))

    def _desenhar_bancadas(self, surf):
        """
        Bancadas atrás da tabela do fundo: adeptos sentados em cadeiras azuis,
        setores separados por escadas e um vidro de proteção à frente.
        Por baixo da faixa de publicidade, dos lados do ringue, fica a zona escura do pavilhão.
        """
        import random
        rnd = random.Random(7)                       # sempre o mesmo público
        cam = self.camera
        r = self.rect
        info = obter_info_equipa(self.equipa_casa)
        c1 = tuple(info.get("cor_primaria", (30, 80, 180)))
        c2 = tuple(info.get("cor_secundaria", (240, 240, 240)))
        outras = [(70, 80, 100), (150, 150, 160), (40, 40, 48), (120, 60, 60), (60, 90, 70)]
        peles = [(232, 192, 158), (214, 168, 128), (180, 128, 90), (130, 88, 60), (240, 206, 176)]
        cabelos = [(40, 28, 20), (66, 42, 24), (20, 20, 22), (120, 85, 50), (170, 140, 95)]
        cor_cadeira = (34, 62, 128)

        topo_tabela = cam.ecra_y(r.top) - ALTURA_TABELA * cam.fator(r.top)
        y_faixa = round(topo_tabela - FAIXA_PUB_H - 3)
        y_vidro = y_faixa - 12

        # Zona escura do pavilhão (dos lados do ringue)
        for yy in range(y_faixa, HEIGHT):
            t = min(1.0, (yy - y_faixa) / 300)
            pygame.draw.line(surf, misturar((20, 28, 52), (8, 12, 24), t), (0, yy), (WIDTH, yy))

        # Bancada: fundo e filas (de cima/longe para baixo/perto)
        surf.fill((14, 20, 40), (0, 0, WIDTH, y_faixa))
        escadas = [(x, 40) for x in (190, 640, 1090)]   # (centro, largura) das escadas
        filas = []
        y = y_faixa
        while y > -40:
            alt = max(20, round(34 - 12 * (1 - y / y_faixa)))
            y -= alt
            filas.append((y, alt))
        for y, alt in reversed(filas):
            # degrau de betão
            pygame.draw.rect(surf, (24, 32, 58), (0, y + alt * 0.62, WIDTH, alt * 0.38 + 1))
            pygame.draw.line(surf, (40, 52, 86), (0, round(y + alt * 0.62)), (WIDTH, round(y + alt * 0.62)))
            passo = alt * 0.78
            x = passo / 2 - rnd.uniform(0, passo)
            while x < WIDTH + passo:
                if any(abs(x - ex) < ew / 2 + passo * 0.4 for ex, ew in escadas):
                    x += passo
                    continue
                # Encosto da cadeira
                cad = pygame.Rect(0, 0, round(alt * 0.56), round(alt * 0.42))
                cad.midbottom = (round(x), round(y + alt * 0.66))
                pygame.draw.rect(surf, cor_cadeira, cad, border_radius=max(1, alt // 8))
                if rnd.random() < 0.86:                  # alguns lugares vazios
                    sorteio = rnd.random()
                    cor = c1 if sorteio < 0.5 else (c2 if sorteio < 0.7 else rnd.choice(outras))
                    corpo = pygame.Rect(0, 0, round(alt * 0.46), round(alt * 0.4))
                    corpo.midbottom = (round(x + rnd.uniform(-1, 1)), round(y + alt * 0.7))
                    pygame.draw.rect(surf, cor, corpo, border_top_left_radius=alt // 5,
                                     border_top_right_radius=alt // 5)
                    r_cab = alt * 0.15
                    cab = (corpo.centerx, round(corpo.top - r_cab * 0.75))
                    pygame.draw.circle(surf, rnd.choice(peles), cab, max(2, round(r_cab)))
                    pygame.draw.circle(surf, rnd.choice(cabelos), (cab[0], cab[1] - round(r_cab * 0.35)),
                                       max(2, round(r_cab)), draw_top_left=True, draw_top_right=True)
                x += passo
        # Escadas entre setores
        for ex, ew in escadas:
            for y, alt in filas:
                for k in range(2):
                    cor = (78, 86, 106) if k == 0 else (60, 66, 84)
                    pygame.draw.rect(surf, cor, (ex - ew // 2, y + k * alt / 2, ew, alt / 2 + 1))
            pygame.draw.line(surf, (110, 118, 138), (ex - ew // 2, 0), (ex - ew // 2, y_vidro), 2)
            pygame.draw.line(surf, (110, 118, 138), (ex + ew // 2, 0), (ex + ew // 2, y_vidro), 2)

        # Luz do pavilhão: o público fica um pouco mais escuro em cima
        sombra = pygame.Surface((WIDTH, y_faixa), pygame.SRCALPHA)
        for yy in range(y_faixa):
            t = 1 - yy / y_faixa
            pygame.draw.line(sombra, (8, 12, 26, int(40 + 110 * t)), (0, yy), (WIDTH, yy))
        surf.blit(sombra, (0, 0))

        # Vidro de proteção com prumos
        vidro = pygame.Surface((WIDTH, y_faixa - y_vidro), pygame.SRCALPHA)
        vidro.fill((190, 210, 235, 45))
        surf.blit(vidro, (0, y_vidro))
        pygame.draw.line(surf, (200, 214, 232), (0, y_vidro), (WIDTH, y_vidro), 2)
        for x in range(40, WIDTH, 160):
            pygame.draw.line(surf, (150, 162, 184), (x, y_vidro), (x, y_faixa), 2)

    def _preparar_balizas_perspetiva(self):
        """Balizas em 3D projetadas pela câmara (ver baliza.criar_baliza_camera)."""
        self._balizas_ecra = [
            criar_baliza_camera(self.camera, self.linha_golo_esq_x, self.baliza_topo_y,
                                self.baliza_base_y, -1),
            criar_baliza_camera(self.camera, self.linha_golo_dir_x, self.baliza_topo_y,
                                self.baliza_base_y, +1),
        ]

    def _construir(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill(COR_FUNDO)
        self._desenhar_bancadas(surf)
        self._desenhar_placards_perspetiva(surf)
        self._por_em_perspetiva(self._construir_plano(), surf)
        self._desenhar_tabelas(surf)
        self._preparar_balizas_perspetiva()
        for fundo, _frente, pos in self._balizas_ecra:
            surf.blit(fundo, pos)
        return surf

    def _calcular_cor_linhas(self) -> tuple:
        """Cor das linhas = cor principal da equipa da casa, ajustada para se ver no piso."""
        info = obter_info_equipa(self.equipa_casa)
        return cor_linhas_campo(info.get("cor_primaria", COR_LINHA))

    def definir_equipa_casa(self, equipa_id: str):
        """Atualiza a equipa da casa e recria o campo (emblema, linhas e publicidade)."""
        if self.equipa_casa != equipa_id:
            self.equipa_casa = equipa_id
            self.cor_linhas  = self._calcular_cor_linhas()
            self._surf = self._construir()

    def _desenhar_centro_emblema(self, surf, cx, cy, escala: int = 1):
        """Emblema oficial da equipa da casa no centro do campo como no mockup."""
        cx, cy = round(cx), round(cy)
        logo_centro = carregar_logo_equipa(self.equipa_casa, (96 * escala, 96 * escala))
        if logo_centro is not None:
            lw, lh = logo_centro.get_size()
            surf.blit(logo_centro, (cx - lw // 2, cy - lh // 2))
        else:
            info = obter_info_equipa(self.equipa_casa)
            cor = info.get("cor_primaria", (20, 60, 160))
            sigla = info.get("sigla", "FCP")
            pygame.draw.circle(surf, cor, (cx, cy), 28 * escala)
            pygame.draw.circle(surf, (230, 200, 60), (cx, cy), 28 * escala, 2 * escala)
            f = fontes.SysFont("Arial", 11 * escala, bold=True)
            t = f.render(sigla, True, (255, 255, 255))
            surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))

    def _desenhar_placards(self, surf, muro):
        """Faixa publicitária estilizada ao longo da tabela superior."""
        font_pl = fontes.SysFont("Arial", 11, bold=True)
        pl_h = 16
        pl_y = muro.top + 2
        w_total = muro.width - 240
        x_inicio = muro.left + 120

        # Fundo dos anúncios com as cores da equipa da casa
        info = obter_info_equipa(self.equipa_casa)
        cor_fundo = misturar(info.get("cor_primaria", (18, 40, 100)), (10, 14, 28), 0.35)
        cor_borda = info.get("cor_secundaria", (50, 90, 170))
        cor_txt   = cor_texto_sobre(cor_fundo)
        pygame.draw.rect(surf, cor_fundo, (x_inicio, pl_y, w_total, pl_h), border_radius=3)
        pygame.draw.rect(surf, cor_borda, (x_inicio, pl_y, w_total, pl_h), 1, border_radius=3)

        t1 = font_pl.render("STICKMANIA  •  HÓQUEI EM PATINS", True, cor_txt)
        t2 = font_pl.render(f"BEM-VINDOS AO RINGUE DO {info.get('nome', '').upper()}", True, cor_txt)
        surf.blit(t1, (x_inicio + 30, pl_y + 1))
        surf.blit(t2, (x_inicio + w_total - t2.get_width() - 30, pl_y + 1))

    def _tile_faixa(self, surf, x0, x1, y0, y1):
        if y1 <= y0 or x1 <= x0:
            return
        tw, th = self._pub_w, self._pub_h
        for y in range(y0, y1, th):
            for x in range(x0, x1, tw):
                dest  = pygame.Rect(x, y, tw, th)
                clipr = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
                clip  = dest.clip(clipr)
                if clip.width > 0 and clip.height > 0:
                    src = pygame.Rect(clip.x - x, clip.y - y, clip.width, clip.height)
                    surf.blit(self._pub, clip.topleft, src)

    def _mascara_cantos(self, img):
        result = img.copy().convert_alpha()
        w, h = img.get_size()
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=round(CANTO * w / RINK_W))
        result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return result

    def draw(self, screen):
        screen.blit(self._surf, (0, 0))

    def draw_frente(self, screen):
        """Travessa, poste da frente e rede lateral: ficam POR CIMA da bola e do guarda-redes."""
        for _fundo, frente, pos in self._balizas_ecra:
            screen.blit(frente, pos)

    def rect_frente_baliza(self, lado: str) -> pygame.Rect:
        """Retângulo ocupado pela camada da frente de uma baliza ('esq' ou 'dir')."""
        if lado == "esq":
            return self._bal_esq_frente.get_rect(topleft=self._pos_baliza_esq)
        return self._bal_dir_frente.get_rect(topleft=self._pos_baliza_dir)
