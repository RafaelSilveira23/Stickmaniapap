# -*- coding: utf-8 -*-
"""rink.py - ringue oficial de hóquei em patins com piso de madeira, tabelas e balizas reais."""
import os
import pygame
from settings import *
from team import carregar_logo_equipa, obter_info_equipa
from cores import cor_linhas_campo, misturar, cor_texto_sobre
from baliza import criar_baliza
from camera import Camera

# ---------- Câmara em perspetiva ----------
CAM_TOPO       = 142    # y no ecrã da linha do fundo do ringue
CAM_BASE       = 522    # y no ecrã da linha da frente do ringue
CAM_LARG_TOPO  = 1010   # largura do ringue no fundo (mais estreito = mais perspetiva)
CAM_LARG_BASE  = 1230   # largura do ringue à frente
ALTURA_TABELA  = 24     # altura das tabelas (px do mundo)


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
        self._campo = self._gerar_piso_madeira(RINK_W, RINK_H)

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

    def _gerar_piso_madeira(self, w: int, h: int) -> pygame.Surface:
        """Gera o piso de madeira natural envernizada do ringue de hóquei."""
        surf = pygame.Surface((w, h))
        surf.fill((224, 178, 122))

        # Tonalidades quentes de tábuas de madeira
        cores_tabua = [
            (226, 180, 124),
            (221, 175, 118),
            (230, 184, 128),
            (218, 171, 114),
            (225, 178, 120),
        ]
        tabua_h = 16

        for y in range(0, h, tabua_h):
            cor = cores_tabua[(y // tabua_h) % len(cores_tabua)]
            pygame.draw.rect(surf, cor, (0, y, w, tabua_h))
            # Linha horizontal sutil entre tábuas
            pygame.draw.line(surf, (196, 150, 96), (0, y), (w, y), 1)

            # Juntas verticais das tábuas intercaladas
            offset_x = (y * 43) % 95
            for x in range(offset_x, w, 115):
                pygame.draw.line(surf, (190, 145, 92), (x, y), (x, y + tabua_h), 1)

        return surf

    # ================================================================== #
    # Construção da imagem do ringue (feita uma vez; muda com a equipa da casa)
    # ================================================================== #

    def _construir_plano(self) -> pygame.Surface:
        """Piso visto de cima (plano), com todas as linhas. Depois é posto em perspetiva."""
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        r = self.rect
        surf.blit(self._mascara_cantos(self._campo), r.topleft)

        cx, cy = r.center
        cor_linha = self.cor_linhas
        # Linha do meio, círculo central e emblema
        pygame.draw.line(surf, cor_linha, (cx, r.top), (cx, r.bottom), LINHA + 1)
        pygame.draw.circle(surf, cor_linha, (cx, cy), RAIO_CENTRO, LINHA + 1)
        pygame.draw.circle(surf, cor_linha, (cx, cy), 5)
        self._desenhar_centro_emblema(surf, cx, cy)
        # Grandes áreas
        area_esq = pygame.Rect(self.linha_golo_esq_x, cy - AREA_H // 2, AREA_W, AREA_H)
        area_dir = pygame.Rect(self.linha_golo_dir_x - AREA_W, cy - AREA_H // 2, AREA_W, AREA_H)
        pygame.draw.rect(surf, cor_linha, area_esq, LINHA + 1)
        pygame.draw.rect(surf, cor_linha, area_dir, LINHA + 1)
        # Linhas de golo vermelhas
        for gx in (self.linha_golo_esq_x, self.linha_golo_dir_x):
            pygame.draw.line(surf, (220, 40, 40), (gx, self.baliza_topo_y), (gx, self.baliza_base_y), 3)
        # Marcas de penálti e de livre direto
        for gx, sinal in ((self.linha_golo_esq_x, 1), (self.linha_golo_dir_x, -1)):
            pygame.draw.circle(surf, cor_linha, (gx + 85 * sinal, cy), 4)
            pygame.draw.circle(surf, cor_linha, (gx + 130 * sinal, cy), 3)
        # Linha de proteção atrás das balizas
        pygame.draw.arc(surf, cor_linha, pygame.Rect(self.linha_golo_esq_x - 65, cy - 45, 65, 90),
                        1.57, 4.71, 2)
        pygame.draw.arc(surf, cor_linha, pygame.Rect(self.linha_golo_dir_x, cy - 45, 65, 90),
                        -1.57, 1.57, 2)
        return surf.subsurface(r).copy()

    def _por_em_perspetiva(self, plano: pygame.Surface, destino: pygame.Surface):
        """
        Desenha o piso plano em perspetiva, linha a linha:
        para cada linha do ecrã descobre-se que linha do campo lhe corresponde
        e estica-se essa linha para a largura certa.
        Para as linhas do campo ficarem suaves (sem "escadinhas"), fazemos tudo
        com o dobro da resolução e no fim reduzimos com smoothscale.
        """
        cam = self.camera
        Q = 2                                            # super-amostragem
        plano2 = pygame.transform.smoothscale(plano, (RINK_W * Q, RINK_H * Q))
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
        destino.blit(pygame.transform.smoothscale(temp, (WIDTH, y1 - y0)), (0, y0))

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
        Tabelas com altura: cada pedaço do contorno vira um retângulo "de pé".
        As do fundo e dos lados veem-se por dentro (brancas); a da frente é mais baixa
        para não esconder o jogo. Por cima corre o corrimão na cor da equipa da casa.
        """
        cam = self.camera
        pts = self._contorno_ringue()
        r = self.rect
        chao, topo = [], []
        for wx, wy in pts:
            frente = wy > r.bottom - CANTO
            h = ALTURA_TABELA * (0.45 if frente else 1.0) * cam.fator(wy)
            sx, sy = cam.projetar(wx, wy)
            chao.append((sx, sy))
            topo.append((sx, sy - h))

        # Desenhar do fundo para a frente
        n = len(pts)
        segs = sorted(range(n), key=lambda i: pts[i][1] + pts[(i + 1) % n][1])
        for i in segs:
            k = (i + 1) % n
            (ax, ay), (bx, by) = pts[i], pts[k]
            # Normal do segmento -> luz: fundo mais claro, lados mais escuros
            nx, ny = by - ay, -(bx - ax)
            comp = max(1e-6, (nx * nx + ny * ny) ** 0.5)
            luz = 0.86 + 0.14 * max(0.0, -ny / comp)
            cor = tuple(int(c * luz) for c in (236, 240, 248))
            quad = [chao[i], chao[k], topo[k], topo[i]]
            pygame.draw.polygon(surf, cor, quad)
            pygame.draw.polygon(surf, cor, quad, 1)

        # Rodapé escuro junto ao piso e corrimão por cima
        rodape = misturar(self.cor_linhas, (10, 14, 28), 0.55)
        pygame.draw.lines(surf, rodape, True, chao, 3)
        pygame.draw.lines(surf, self.cor_linhas, True, topo, 4)
        pygame.draw.lines(surf, misturar(self.cor_linhas, (255, 255, 255), 0.45), True,
                          [(x, y - 1) for x, y in topo], 1)
        self._desenhar_placards_perspetiva(surf)

    def _desenhar_placards_perspetiva(self, surf):
        """Publicidade na tabela do fundo (vista de frente, por isso é um retângulo)."""
        cam = self.camera
        r = self.rect
        x1, y_chao = cam.projetar(r.left + CANTO, r.top)
        x2, _ = cam.projetar(r.right - CANTO, r.top)
        h = ALTURA_TABELA * cam.fator(r.top)
        faixa = pygame.Rect(round(x1), round(y_chao - h + 4), round(x2 - x1), round(h - 7))

        info = obter_info_equipa(self.equipa_casa)
        cor_a = misturar(info.get("cor_primaria", (18, 40, 100)), (10, 14, 28), 0.30)
        cor_b = (245, 247, 252)
        nome = info.get("nome", "").upper()
        textos = ["STICKMANIA", "HÓQUEI EM PATINS", nome,
                  "JOGO • PAIXÃO • TRADIÇÃO", "PAP 2026/2027", nome]
        fonte = pygame.font.SysFont("Arial", max(9, faixa.height - 4), bold=True)
        n = len(textos)
        for i, txt in enumerate(textos):
            px = faixa.x + faixa.width * i // n
            pw = faixa.width * (i + 1) // n - faixa.width * i // n
            painel = pygame.Rect(px + 1, faixa.y, pw - 2, faixa.height)
            fundo = cor_a if i % 2 == 0 else cor_b
            pygame.draw.rect(surf, fundo, painel, border_radius=2)
            t = fonte.render(txt, True, cor_texto_sobre(fundo))
            if t.get_width() > painel.width - 6:
                t = pygame.transform.smoothscale(t, (painel.width - 6, t.get_height()))
            surf.blit(t, (painel.centerx - t.get_width() // 2, painel.centery - t.get_height() // 2))

    def _desenhar_bancadas(self, surf):
        """
        Bancadas com público desenhado no código: filas de degraus e adeptos
        (muitos com as cores da equipa da casa). As filas de cima estão mais longe,
        por isso são mais pequenas.
        """
        import random
        rnd = random.Random(7)                       # sempre o mesmo público
        info = obter_info_equipa(self.equipa_casa)
        c1 = tuple(info.get("cor_primaria", (30, 80, 180)))
        c2 = tuple(info.get("cor_secundaria", (240, 240, 240)))
        outras = [(200, 40, 40), (240, 240, 240), (30, 30, 36), (60, 120, 200),
                  (230, 190, 40), (90, 90, 100), (40, 140, 70)]
        peles = [(240, 200, 165), (222, 175, 135), (190, 135, 95), (140, 95, 65), (250, 215, 185)]
        cabelos = [(40, 28, 20), (70, 45, 25), (20, 20, 22), (150, 110, 60), (200, 170, 110)]

        limite = CAM_BASE + 12
        surf.fill((12, 18, 38), (0, 0, WIDTH, limite))
        y = limite
        fila = 0
        filas = []
        while y > -30:
            # perto (em baixo) = filas altas; longe (em cima) = filas baixas
            alt = max(13, round(26 - 13 * (1 - y / limite)))
            y -= alt
            filas.append((y, alt))
            fila += 1
        # Desenhar de cima (longe) para baixo (perto)
        for y, alt in reversed(filas):
            degrau = (22, 32, 66) if (y // alt) % 2 else (18, 27, 56)
            pygame.draw.rect(surf, degrau, (0, y + alt * 0.55, WIDTH, alt * 0.45 + 1))
            pygame.draw.line(surf, (34, 48, 92), (0, round(y + alt * 0.55)), (WIDTH, round(y + alt * 0.55)))
            passo = alt * 0.62
            x = -rnd.uniform(0, passo)
            while x < WIDTH + passo:
                if rnd.random() < 0.9:                   # alguns lugares vazios
                    r_cab = alt * 0.17
                    cor = c1 if rnd.random() < 0.45 else (c2 if rnd.random() < 0.3 else rnd.choice(outras))
                    cx_p = x + rnd.uniform(-1, 1)
                    topo_corpo = y + alt * 0.38
                    corpo = pygame.Rect(0, 0, round(alt * 0.42), round(alt * 0.5))
                    corpo.midtop = (round(cx_p), round(topo_corpo))
                    pygame.draw.rect(surf, cor, corpo, border_radius=max(1, round(alt * 0.12)))
                    if rnd.random() < 0.12:              # braços no ar / cachecol
                        pygame.draw.line(surf, cor, (corpo.left, corpo.top + 2),
                                         (corpo.left - alt * 0.15, corpo.top - alt * 0.3), 2)
                        pygame.draw.line(surf, cor, (corpo.right, corpo.top + 2),
                                         (corpo.right + alt * 0.15, corpo.top - alt * 0.3), 2)
                    cab = (round(cx_p), round(topo_corpo - r_cab * 0.6))
                    pygame.draw.circle(surf, rnd.choice(peles), cab, max(2, round(r_cab)))
                    pygame.draw.circle(surf, rnd.choice(cabelos), (cab[0], cab[1] - round(r_cab * 0.45)),
                                       max(1, round(r_cab * 0.8)), draw_top_left=True, draw_top_right=True)
                x += passo * rnd.uniform(0.9, 1.15)

        # Luz: mais claro em cima (iluminação do pavilhão), mais escuro dos lados e em baixo
        sombra = pygame.Surface((WIDTH, limite), pygame.SRCALPHA)
        for yy in range(limite):
            t = max(0.0, (yy - 60) / (limite - 60))
            pygame.draw.line(sombra, (8, 12, 26, int(30 + 175 * t)), (0, yy), (WIDTH, yy))
        surf.blit(sombra, (0, 0))
        # Varandim à frente da primeira fila
        cam = self.camera
        y_var = round(cam.ecra_y(self.rect.top) - ALTURA_TABELA * cam.fator(self.rect.top)) - 8
        pygame.draw.rect(surf, (16, 24, 48), (0, y_var, WIDTH, 8))
        pygame.draw.line(surf, (60, 80, 130), (0, y_var), (WIDTH, y_var), 2)

    def _preparar_balizas_perspetiva(self):
        """
        Cria as balizas já com o tamanho do ecrã:
          - a abertura (de poste a poste) segue a perspetiva do chão;
          - a altura dos postes segue o tamanho dos jogadores.
        Assim os postes ficam exatamente nas pontas da linha de golo.
        """
        cam = self.camera
        cy = self.rect.centery
        boca = round(cam.ecra_y(self.baliza_base_y) - cam.ecra_y(self.baliza_topo_y))
        altura = round(24 * cam.escala(cy))
        prof = round(40 * cam.fator(cy))
        self._balizas_ecra = []
        for gx, lado in ((self.linha_golo_esq_x, "direita"), (self.linha_golo_dir_x, "esquerda")):
            fundo, frente, ancora = criar_baliza(boca, altura=altura, profundidade=prof, virada_para=lado)
            sx, _ = cam.projetar(gx, cy)
            sy = (cam.ecra_y(self.baliza_topo_y) + cam.ecra_y(self.baliza_base_y)) / 2
            pos = (round(sx - ancora[0]), round(sy - ancora[1]))
            self._balizas_ecra.append((fundo, frente, pos))

    def _construir(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill(COR_FUNDO)
        self._desenhar_bancadas(surf)
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

    def _desenhar_centro_emblema(self, surf, cx, cy):
        """Emblema oficial da equipa da casa no centro do campo como no mockup."""
        logo_centro = carregar_logo_equipa(self.equipa_casa, (96, 96))
        if logo_centro is not None:
            lw, lh = logo_centro.get_size()
            surf.blit(logo_centro, (cx - lw // 2, cy - lh // 2))
        else:
            info = obter_info_equipa(self.equipa_casa)
            cor = info.get("cor_primaria", (20, 60, 160))
            sigla = info.get("sigla", "FCP")
            pygame.draw.circle(surf, cor, (cx, cy), 28)
            pygame.draw.circle(surf, (230, 200, 60), (cx, cy), 28, 2)
            f = pygame.font.SysFont("Arial", 11, bold=True)
            t = f.render(sigla, True, (255, 255, 255))
            surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))

    def _desenhar_placards(self, surf, muro):
        """Faixa publicitária estilizada ao longo da tabela superior."""
        font_pl = pygame.font.SysFont("Arial", 11, bold=True)
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
        mask = pygame.Surface((RINK_W, RINK_H), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, RINK_W, RINK_H), border_radius=CANTO)
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
