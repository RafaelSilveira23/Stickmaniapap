# -*- coding: utf-8 -*-
"""rink.py - campo com sprites pixel-art originais."""
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
        campo_raw   = pygame.image.load(os.path.join(ui, "campo_tile.png")).convert_alpha()
        publico_raw = pygame.image.load(os.path.join(ui, "publico_tile.png")).convert_alpha()
        atras_raw   = pygame.image.load(os.path.join(ui, "baliza_atras.png")).convert_alpha()
        frente_raw  = pygame.image.load(os.path.join(ui, "baliza_frente.png")).convert_alpha()

        self._campo = pygame.transform.scale(campo_raw, (RINK_W, RINK_H))
        self._pub   = publico_raw
        self._pub_w = publico_raw.get_width()
        self._pub_h = publico_raw.get_height()

        # Balizas pixel-art
        BSH = 100
        aw, ah = atras_raw.get_size()
        BSW = int(aw * BSH / ah)
        fw, fh = frente_raw.get_size()
        BSW2 = int(fw * BSH / fh)

        atras_s  = pygame.transform.scale(atras_raw,  (BSW,  BSH))
        frente_s = pygame.transform.scale(frente_raw, (BSW2, BSH))

        self._bal_atras_esq  = atras_s
        self._bal_frente_esq = frente_s
        self._bal_atras_dir  = pygame.transform.flip(atras_s,  True, False)
        self._bal_frente_dir = pygame.transform.flip(frente_s, True, False)

        REDE_DENTRO = int(BSW * 0.58)
        self._pos_esq = (self.rect.left - (BSW - REDE_DENTRO), cy - BSH // 2)
        self._pos_dir = (self.rect.right - REDE_DENTRO,        cy - BSH // 2)

        gw = REDE_DENTRO - 2
        gh = int(BSH * 0.62)
        self.baliza_esq = pygame.Rect(self.rect.left - gw + 1, cy - gh // 2, gw, gh)
        self.baliza_dir = pygame.Rect(self.rect.right - 1,     cy - gh // 2, gw, gh)

        grh = int(BSH * 0.78)
        self.zona_gr_esq = pygame.Rect(self.rect.left - gw + 1, cy - grh // 2, gw, grh)
        self.zona_gr_dir = pygame.Rect(self.rect.right - 1,     cy - grh // 2, gw, grh)

        self._surf = self._construir()

    def _construir(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        r    = self.rect
        muro = r.inflate(MURO * 2, MURO * 2)

        # Bancadas
        self._tile_faixa(surf, muro.left, muro.right, HUD_H,       muro.top)
        self._tile_faixa(surf, muro.left, muro.right, muro.bottom, HEIGHT)

        # Muro
        pygame.draw.rect(surf, COR_MURO_SOMBRA, muro.move(0, 4), border_radius=CANTO + MURO)
        pygame.draw.rect(surf, COR_MURO,        muro,            border_radius=CANTO + MURO)

        # Campo
        surf.blit(self._mascara_cantos(self._campo), r.topleft)

        # Linhas
        cx, cy = r.center
        pygame.draw.line(surf, COR_LINHA, (cx, r.top + 6), (cx, r.bottom - 6), 4)
        pygame.draw.circle(surf, COR_LINHA, (cx, cy), RAIO_CENTRO, LINHA)
        pygame.draw.circle(surf, COR_LINHA, (cx, cy), 6)
        for area in (
            pygame.Rect(r.left,           cy - AREA_H // 2, AREA_W, AREA_H),
            pygame.Rect(r.right - AREA_W, cy - AREA_H // 2, AREA_W, AREA_H),
        ):
            pygame.draw.rect(surf, COR_LINHA, area, LINHA)
            pygame.draw.circle(surf, COR_LINHA, area.center, 5)

        # Balizas traseiras
        surf.blit(self._bal_atras_esq, self._pos_esq)
        surf.blit(self._bal_atras_dir, self._pos_dir)

        return surf

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
        screen.blit(self._bal_frente_esq, self._pos_esq)
        screen.blit(self._bal_frente_dir, self._pos_dir)
