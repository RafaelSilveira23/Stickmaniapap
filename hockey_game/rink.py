# -*- coding: utf-8 -*-
"""rink.py - ringue oficial de hóquei em patins com piso de madeira, tabelas e balizas reais."""
import os
import pygame
from settings import *


def _pasta_ui():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "extras_ui")


class Rink:
    def __init__(self):
        self.rect = pygame.Rect(RINK_X, RINK_Y, RINK_W, RINK_H)
        cy = self.rect.centery

        ui = _pasta_ui()
        publico_raw = pygame.image.load(os.path.join(ui, "publico_tile.png")).convert_alpha()
        atras_raw   = pygame.image.load(os.path.join(ui, "baliza_atras.png")).convert_alpha()
        frente_raw  = pygame.image.load(os.path.join(ui, "baliza_frente.png")).convert_alpha()

        self._pub   = publico_raw
        self._pub_w = publico_raw.get_width()
        self._pub_h = publico_raw.get_height()

        # ── Gerar Piso de Madeira Real (Tábua Corrida / Parquet de Hóquei) ──
        self._campo = self._gerar_piso_madeira(RINK_W, RINK_H)

        # ── Balizas Proporcionais Alinhadas ao Pixel ─────────────────────
        BSH = 88
        fw, fh = frente_raw.get_size()     # 69, 89
        self.BSW_FRENTE = int(fw * BSH / fh)    # ~68
        aw, ah = atras_raw.get_size()     # 61, 86
        self.BSW_ATRAS  = int(aw * BSH / ah)    # ~62

        atras_s  = pygame.transform.scale(atras_raw,  (self.BSW_ATRAS,  BSH))
        frente_s = pygame.transform.scale(frente_raw, (self.BSW_FRENTE, BSH))

        self._bal_atras_esq  = atras_s
        self._bal_frente_esq = frente_s
        self._bal_atras_dir  = pygame.transform.flip(atras_s,  True, False)
        self._bal_frente_dir = pygame.transform.flip(frente_s, True, False)

        # ── Linhas de Golo e Posições (Espaço atrás da baliza para patinar) ──
        self.linha_golo_esq_x = self.rect.left + BALIZA_OFFSET       # X ~ 185
        self.linha_golo_dir_x = self.rect.right - BALIZA_OFFSET      # X ~ 1095

        self.baliza_boca_h = 66
        self.baliza_topo_y = cy - self.baliza_boca_h // 2
        self.baliza_base_y = cy + self.baliza_boca_h // 2

        # Posições de desenho perfeitamente alinhadas com a linha de golo
        # Esquerda: os postes frontais terminam exatamente em linha_golo_esq_x
        self._pos_frente_esq = (self.linha_golo_esq_x - self.BSW_FRENTE, cy - BSH // 2)
        self._pos_atras_esq  = (self.linha_golo_esq_x - self.BSW_ATRAS,  cy - BSH // 2)

        # Direita: os postes frontais começam exatamente em linha_golo_dir_x
        self._pos_frente_dir = (self.linha_golo_dir_x, cy - BSH // 2)
        self._pos_atras_dir  = (self.linha_golo_dir_x, cy - BSH // 2)

        # Retângulos interiores de golo
        gw = 32
        self.baliza_esq = pygame.Rect(self.linha_golo_esq_x - gw, self.baliza_topo_y, gw, self.baliza_boca_h)
        self.baliza_dir = pygame.Rect(self.linha_golo_dir_x,     self.baliza_topo_y, gw, self.baliza_boca_h)

        # Obstáculos físicos das redes (jogadores patinam à volta sem atravessar a rede)
        prof_obs = 46
        self.obstaculo_baliza_esq = pygame.Rect(
            self.linha_golo_esq_x - prof_obs,
            cy - BSH // 2 + 8,
            prof_obs,
            BSH - 16
        )
        self.obstaculo_baliza_dir = pygame.Rect(
            self.linha_golo_dir_x,
            cy - BSH // 2 + 8,
            prof_obs,
            BSH - 16
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

    def _construir(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        r    = self.rect
        muro = r.inflate(MURO * 2, MURO * 2)

        # Bancada com público no topo
        self._tile_faixa(surf, muro.left, muro.right, 0, muro.top)

        # Sombra da tabela
        pygame.draw.rect(surf, COR_MURO_SOMBRA, muro.move(0, 4), border_radius=CANTO + MURO)
        # Tabela em madeira branca/creme
        pygame.draw.rect(surf, COR_MURO, muro, border_radius=CANTO + MURO)

        # Piso de madeira recortado com cantos arredondados
        surf.blit(self._mascara_cantos(self._campo), r.topleft)

        # Painéis publicitários da tabela superior
        self._desenhar_placards(surf, muro)

        # ── Linhas Oficiais do Ringue (Azul Hóquei) ─────────────────────
        cx, cy = r.center

        # Linha de meio-campo e círculo central
        pygame.draw.line(surf, COR_LINHA, (cx, r.top + 3), (cx, r.bottom - 3), LINHA)
        pygame.draw.circle(surf, COR_LINHA, (cx, cy), RAIO_CENTRO, LINHA)
        pygame.draw.circle(surf, COR_LINHA, (cx, cy), 5)

        # Emblema central sutil no meio do círculo
        self._desenhar_centro_emblema(surf, cx, cy)

        # Grandes Áreas (Retângulos à frente das balizas)
        area_esq = pygame.Rect(self.linha_golo_esq_x, cy - AREA_H // 2, AREA_W, AREA_H)
        area_dir = pygame.Rect(self.linha_golo_dir_x - AREA_W, cy - AREA_H // 2, AREA_W, AREA_H)
        pygame.draw.rect(surf, COR_LINHA, area_esq, LINHA)
        pygame.draw.rect(surf, COR_LINHA, area_dir, LINHA)

        # Linhas de Golo vermelhas entre os postes
        pygame.draw.line(surf, (220, 40, 40),
                         (self.linha_golo_esq_x, self.baliza_topo_y),
                         (self.linha_golo_esq_x, self.baliza_base_y), 3)
        pygame.draw.line(surf, (220, 40, 40),
                         (self.linha_golo_dir_x, self.baliza_topo_y),
                         (self.linha_golo_dir_x, self.baliza_base_y), 3)

        # Marcas de Penálti
        pygame.draw.circle(surf, COR_LINHA, (self.linha_golo_esq_x + 85, cy), 4)
        pygame.draw.circle(surf, COR_LINHA, (self.linha_golo_dir_x - 85, cy), 4)

        # Marcas de Livre Direto
        pygame.draw.circle(surf, COR_LINHA, (self.linha_golo_esq_x + 130, cy), 3)
        pygame.draw.circle(surf, COR_LINHA, (self.linha_golo_dir_x - 130, cy), 3)

        # Linha circular de proteção atrás da baliza
        pygame.draw.arc(surf, COR_LINHA,
                        pygame.Rect(self.linha_golo_esq_x - 65, cy - 45, 65, 90),
                        1.57, 4.71, 2)
        pygame.draw.arc(surf, COR_LINHA,
                        pygame.Rect(self.linha_golo_dir_x, cy - 45, 65, 90),
                        -1.57, 1.57, 2)

        # Balizas (parte de trás da rede)
        surf.blit(self._bal_atras_esq, self._pos_atras_esq)
        surf.blit(self._bal_atras_dir, self._pos_atras_dir)

        return surf

    def _desenhar_centro_emblema(self, surf, cx, cy):
        """Emblema discreto de hóquei no centro do campo como no mockup."""
        # Pequeno círculo dourado/azul
        pygame.draw.circle(surf, (30, 75, 160), (cx, cy), 22)
        pygame.draw.circle(surf, (220, 180, 50), (cx, cy), 22, 2)
        f = pygame.font.SysFont("Arial", 8, bold=True)
        t = f.render("F C P", True, (255, 255, 255))
        surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))

    def _desenhar_placards(self, surf, muro):
        """Faixa publicitária estilizada ao longo da tabela superior."""
        font_pl = pygame.font.SysFont("Arial", 11, bold=True)
        pl_h = 16
        pl_y = muro.top + 2
        w_total = muro.width - 240
        x_inicio = muro.left + 120

        # Fundo azul dos anúncios
        pygame.draw.rect(surf, (18, 40, 100), (x_inicio, pl_y, w_total, pl_h), border_radius=3)
        pygame.draw.rect(surf, (50, 90, 170), (x_inicio, pl_y, w_total, pl_h), 1, border_radius=3)

        t1 = font_pl.render("STICKMANIA  •  HÓQUEI EM PATINS", True, (240, 245, 255))
        t2 = font_pl.render("JOGO  •  PAIXÃO  •  TRADIÇÃO", True, (210, 230, 255))
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
        """Desenha os postes frontais e a travessa por cima dos jogadores e da bola."""
        screen.blit(self._bal_frente_esq, self._pos_frente_esq)
        screen.blit(self._bal_frente_dir, self._pos_frente_dir)
