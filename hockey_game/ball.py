# -*- coding: utf-8 -*-
"""ball.py - bola com fisica realista."""
import os
import pygame
from settings import *

BOLA_SIZE        = 14
ATRITO           = 0.988
RESSALTO         = 0.72
VEL_MINIMA       = 8.0
VEL_RESSALTO     = 60.0
OFFSET_BOLA      = 28
PASSE_FORCA      = 400
REMATE_FORCA     = 650
RAIO_COLISAO     = 20
PICK_UP_DIST     = 32
COOLDOWN_RECOLHA = 0.35  # tempo que o rematador/passador não pode reabsorver a bola


def _pasta_extras():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "hd", "extras")


class Ball(pygame.sprite.Sprite):
    def __init__(self, pos: tuple):
        super().__init__()

        # Carregar sprite original
        caminho = os.path.join(_pasta_extras(), "bola.png")
        img = pygame.image.load(caminho).convert_alpha()
        self.image = pygame.transform.scale(img, (BOLA_SIZE, BOLA_SIZE))
        # Rect centrado exatamente no tamanho real da bola
        self.rect = self.image.get_rect(center=pos)

        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel   = pygame.math.Vector2(0, 0)
        self.dono  = None

        self._cooldown_dono  = None
        self._cooldown_timer = 0.0

    # ------------------------------------------------------------------ #

    def definir_dono(self, jogador):
        self.dono = jogador
        self.vel.update(0, 0)
        self._cooldown_dono  = None
        self._cooldown_timer = 0.0

    def libertar(self, velocidade: pygame.math.Vector2, dono_anterior=None):
        if self.dono is not None:
            self.dono.tem_bola = False
        self._cooldown_dono  = dono_anterior or self.dono
        self._cooldown_timer = COOLDOWN_RECOLHA
        self.dono = None
        self.vel.update(velocidade)

    def seguir_jogador(self, jogador):
        # A bola segue o jogador na direção exata para onde ele está voltado (incluindo diagonais)
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            offset = jogador.vetor_direcao * OFFSET_BOLA
            self.pos_x = jogador.pos_x + offset.x
            self.pos_y = jogador.pos_y + offset.y
        else:
            offsets = {
                "direita":   ( OFFSET_BOLA, 0),
                "esquerda":  (-OFFSET_BOLA, 0),
                "cima":      (0, -OFFSET_BOLA),
                "baixo":     (0,  OFFSET_BOLA),
            }
            dx, dy = offsets.get(jogador.direcao, (0, OFFSET_BOLA))
            self.pos_x = jogador.pos_x + dx
            self.pos_y = jogador.pos_y + dy
        self.rect.center = (round(self.pos_x), round(self.pos_y))

    # ------------------------------------------------------------------ #

    def update(self, dt, rink_rect, baliza_esq, baliza_dir, todos_jogadores=None):
        # Cooldown
        if self._cooldown_timer > 0:
            self._cooldown_timer -= dt
            if self._cooldown_timer <= 0:
                self._cooldown_dono  = None
                self._cooldown_timer = 0.0

        if self.dono is not None:
            self.rect.center = (round(self.pos_x), round(self.pos_y))
            return None

        # Movimento
        self.pos_x += self.vel.x * dt
        self.pos_y += self.vel.y * dt

        # Golo
        resultado = self._verificar_golo(baliza_esq, baliza_dir)
        if resultado:
            return resultado

        # Paredes
        self._colisao_paredes(rink_rect)

        # Ressalto em jogadores (so bola rapida)
        if todos_jogadores and self.vel.length() >= VEL_RESSALTO:
            self._colisao_jogadores(todos_jogadores)

        # Atrito
        self.vel *= ATRITO
        if self.vel.length() < VEL_MINIMA:
            self.vel.update(0, 0)

        self.rect.center = (round(self.pos_x), round(self.pos_y))
        return None

    def _colisao_paredes(self, rink_rect):
        r = BOLA_SIZE // 2
        if self.pos_x - r < rink_rect.left:
            self.pos_x = rink_rect.left + r
            self.vel.x = abs(self.vel.x) * RESSALTO
        elif self.pos_x + r > rink_rect.right:
            self.pos_x = rink_rect.right - r
            self.vel.x = -abs(self.vel.x) * RESSALTO
        if self.pos_y - r < rink_rect.top:
            self.pos_y = rink_rect.top + r
            self.vel.y = abs(self.vel.y) * RESSALTO
        elif self.pos_y + r > rink_rect.bottom:
            self.pos_y = rink_rect.bottom - r
            self.vel.y = -abs(self.vel.y) * RESSALTO

    def _colisao_jogadores(self, jogadores):
        for j in jogadores:
            if j == self._cooldown_dono:
                continue
            dx = self.pos_x - j.pos_x
            dy = self.pos_y - j.pos_y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < RAIO_COLISAO and dist > 0.1:
                nx = dx / dist
                ny = dy / dist
                dot = self.vel.x * nx + self.vel.y * ny
                if dot < 0:
                    self.vel.x -= 2 * dot * nx
                    self.vel.y -= 2 * dot * ny
                    self.vel   *= 0.75
                    self.pos_x += nx * (RAIO_COLISAO - dist + 1)
                    self.pos_y += ny * (RAIO_COLISAO - dist + 1)
                break

    def _verificar_golo(self, baliza_esq, baliza_dir):
        if baliza_esq.collidepoint(self.pos_x, self.pos_y):
            return "golo_esq"
        if baliza_dir.collidepoint(self.pos_x, self.pos_y):
            return "golo_dir"
        return None

    def repor(self, pos):
        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel.update(0, 0)
        self.dono = None
        self._cooldown_dono  = None
        self._cooldown_timer = 0.0
        self.rect.center = pos

    def pode_ser_apanhada_por(self, jogador):
        if self.dono is not None:
            return False
        if jogador == self._cooldown_dono and self._cooldown_timer > 0:
            return False
        return True
