# -*- coding: utf-8 -*-
"""rink.py - ringue oficial de hóquei em patins com piso de madeira, tabelas e balizas reais."""
import os
import pygame
from settings import *
from team import carregar_logo_equipa, obter_info_equipa
from cores import cor_linhas_campo, misturar, cor_texto_sobre
from baliza import criar_baliza


def _pasta_ui():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "extras_ui")


class Rink:
    def __init__(self, equipa_casa: str = "fc_porto"):
        self.equipa_casa = equipa_casa
        self.cor_linhas  = self._calcular_cor_linhas()
        self.rect = pygame.Rect(RINK_X, RINK_Y, RINK_W, RINK_H)
        cy = self.rect.centery

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

    def _construir(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        r    = self.rect
        muro = r.inflate(MURO * 2, MURO * 2)

        # Bancada com público no topo a toda a largura
        self._tile_faixa(surf, 0, WIDTH, 0, muro.top)

        # Sombra da tabela
        pygame.draw.rect(surf, COR_MURO_SOMBRA, muro.move(0, 4), border_radius=CANTO + MURO)
        # Tabela em madeira branca/creme
        pygame.draw.rect(surf, COR_MURO, muro, border_radius=CANTO + MURO)

        # Piso de madeira recortado com cantos arredondados
        surf.blit(self._mascara_cantos(self._campo), r.topleft)

        # Painéis publicitários da tabela superior
        self._desenhar_placards(surf, muro)

        # ── Linhas Oficiais do Ringue (na cor da equipa da casa) ────────
        cx, cy = r.center
        cor_linha = self.cor_linhas

        # Linha de meio-campo e círculo central
        pygame.draw.line(surf, cor_linha, (cx, r.top + 3), (cx, r.bottom - 3), LINHA)
        pygame.draw.circle(surf, cor_linha, (cx, cy), RAIO_CENTRO, LINHA)
        pygame.draw.circle(surf, cor_linha, (cx, cy), 5)

        # Emblema central sutil no meio do círculo
        self._desenhar_centro_emblema(surf, cx, cy)

        # Grandes Áreas (Retângulos à frente das balizas)
        area_esq = pygame.Rect(self.linha_golo_esq_x, cy - AREA_H // 2, AREA_W, AREA_H)
        area_dir = pygame.Rect(self.linha_golo_dir_x - AREA_W, cy - AREA_H // 2, AREA_W, AREA_H)
        pygame.draw.rect(surf, cor_linha, area_esq, LINHA)
        pygame.draw.rect(surf, cor_linha, area_dir, LINHA)

        # Linhas de Golo vermelhas entre os postes
        pygame.draw.line(surf, (220, 40, 40),
                         (self.linha_golo_esq_x, self.baliza_topo_y),
                         (self.linha_golo_esq_x, self.baliza_base_y), 3)
        pygame.draw.line(surf, (220, 40, 40),
                         (self.linha_golo_dir_x, self.baliza_topo_y),
                         (self.linha_golo_dir_x, self.baliza_base_y), 3)

        # Marcas de Penálti
        pygame.draw.circle(surf, cor_linha, (self.linha_golo_esq_x + 85, cy), 4)
        pygame.draw.circle(surf, cor_linha, (self.linha_golo_dir_x - 85, cy), 4)

        # Marcas de Livre Direto
        pygame.draw.circle(surf, cor_linha, (self.linha_golo_esq_x + 130, cy), 3)
        pygame.draw.circle(surf, cor_linha, (self.linha_golo_dir_x - 130, cy), 3)

        # Linha circular de proteção atrás da baliza
        pygame.draw.arc(surf, cor_linha,
                        pygame.Rect(self.linha_golo_esq_x - 65, cy - 45, 65, 90),
                        1.57, 4.71, 2)
        pygame.draw.arc(surf, cor_linha,
                        pygame.Rect(self.linha_golo_dir_x, cy - 45, 65, 90),
                        -1.57, 1.57, 2)

        # Balizas Oficiais (desenhadas com nitidez sem duplicidade)
        surf.blit(self._bal_esq, self._pos_baliza_esq)
        surf.blit(self._bal_dir, self._pos_baliza_dir)

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
        screen.blit(self._bal_esq_frente, self._pos_baliza_esq)
        screen.blit(self._bal_dir_frente, self._pos_baliza_dir)

    def rect_frente_baliza(self, lado: str) -> pygame.Rect:
        """Retângulo ocupado pela camada da frente de uma baliza ('esq' ou 'dir')."""
        if lado == "esq":
            return self._bal_esq_frente.get_rect(topleft=self._pos_baliza_esq)
        return self._bal_dir_frente.get_rect(topleft=self._pos_baliza_dir)
