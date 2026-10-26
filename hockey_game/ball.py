# -*- coding: utf-8 -*-
"""ball.py - bola com física realista de hóquei em patins (ressaltos, tabelas e balizas)."""
import os
import random
import pygame
from settings import *

BOLA_SIZE        = 14
ATRITO           = 0.988          # atrito base (mantido para compatibilidade)
ATRITO_BASE      = 0.991          # atrito quando a bola está rápida (menos resistência)
ATRITO_LENTO     = 0.975          # atrito quando a bola está lenta (mais resistência)
VEL_TRANSICAO    = 120            # px/s — abaixo disto aplica ATRITO_LENTO
RESSALTO         = 0.78           # coeficiente de ressalto (era 0.72 → agora 0.78)
VEL_MINIMA       = 8.0            # velocidade abaixo da qual a bola para
VEL_RESSALTO     = 55.0
OFFSET_BOLA      = 22
PASSE_FORCA      = 400
REMATE_FORCA     = 650
RAIO_COLISAO     = 20
PICK_UP_DIST     = 32
COOLDOWN_RECOLHA = 0.35
SPIN_FACTOR      = 0.08           # componente lateral no ressalto (simula rotação/efeito)
SPIN_RATE        = 0.3            # graus por px/s — rotação visual da bola


def _pasta_extras():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "hd", "extras")


class Ball(pygame.sprite.Sprite):
    def __init__(self, pos: tuple):
        super().__init__()

        caminho = os.path.join(_pasta_extras(), "bola.png")
        img = pygame.image.load(caminho).convert_alpha()
        self._imagem_base = pygame.transform.scale(img, (BOLA_SIZE, BOLA_SIZE))
        self.image = self._imagem_base.copy()
        self.rect = self.image.get_rect(center=pos)

        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel   = pygame.math.Vector2(0, 0)
        self.dono  = None

        self._cooldown_dono  = None
        self._cooldown_timer = 0.0

        # Spin visual
        self._angulo = 0.0   # graus de rotação acumulados

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
        # A bola segue à frente do stick do jogador (suporta todas as diagonais)
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            offset = jogador.vetor_direcao * OFFSET_BOLA
            self.pos_x = jogador.pos_x + offset.x
            self.pos_y = jogador.pos_y + offset.y - 6  # stick fica ligeiramente acima do centro
        else:
            offsets = {
                "direita":   ( OFFSET_BOLA,  -6),
                "esquerda":  (-OFFSET_BOLA,  -6),
                "cima":      (0, -OFFSET_BOLA - 6),
                "baixo":     (0,  OFFSET_BOLA - 6),
            }
            dx, dy = offsets.get(jogador.direcao, (0, OFFSET_BOLA - 6))
            self.pos_x = jogador.pos_x + dx
            self.pos_y = jogador.pos_y + dy
        self.rect.center = (round(self.pos_x), round(self.pos_y))

    # ------------------------------------------------------------------ #

    def update(self, dt, rink, todos_jogadores=None):
        # Temporizador de imunidade para quem acabou de rematar/passar
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

        # Spin visual — rotação proporcional à velocidade actual
        vel_atual = self.vel.length()
        self._angulo += vel_atual * dt * SPIN_RATE
        self._angulo %= 360.0
        self.image = pygame.transform.rotate(self._imagem_base, self._angulo)
        self.rect  = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Verificar se é Golo
        resultado = self._verificar_golo(rink)
        if resultado:
            return resultado

        # Colisão com as Balizas (ressalto nos postes e rede exterior)
        self._colisao_balizas(rink)

        # Colisão com as Paredes exteriores do ringue
        self._colisao_paredes(rink.rect)

        # Ressalto em jogadores (bola veloz)
        if todos_jogadores and self.vel.length() >= VEL_RESSALTO:
            self._colisao_jogadores(todos_jogadores)

        # Atrito variável: rápida → ATRITO_BASE; lenta → ATRITO_LENTO
        vel_atual = self.vel.length()
        if vel_atual > VEL_TRANSICAO:
            self.vel *= ATRITO_BASE
        else:
            self.vel *= ATRITO_LENTO

        # Arrasto progressivo — fade gradual nos últimos VEL_MINIMA px/s
        vel_atual = self.vel.length()
        if vel_atual < VEL_MINIMA:
            if vel_atual < 1.0:
                self.vel.update(0, 0)
            else:
                # Fade gradual em vez de corte abrupto
                fator = vel_atual / VEL_MINIMA
                self.vel *= fator * 0.85

        self.rect.center = (round(self.pos_x), round(self.pos_y))
        return None

    def _colisao_paredes(self, rink_rect):
        r = BOLA_SIZE // 2
        parede_x = False
        parede_y = False

        if self.pos_x - r < rink_rect.left:
            self.pos_x = rink_rect.left + r
            self.vel.x = abs(self.vel.x) * RESSALTO
            parede_x = True
        elif self.pos_x + r > rink_rect.right:
            self.pos_x = rink_rect.right - r
            self.vel.x = -abs(self.vel.x) * RESSALTO
            parede_x = True

        if self.pos_y - r < rink_rect.top:
            self.pos_y = rink_rect.top + r
            self.vel.y = abs(self.vel.y) * RESSALTO
            parede_y = True
        elif self.pos_y + r > rink_rect.bottom:
            self.pos_y = rink_rect.bottom - r
            self.vel.y = -abs(self.vel.y) * RESSALTO
            parede_y = True

        # Ressalto com spin — componente lateral ligeira ao bater numa parede em ângulo
        if parede_x and not parede_y:
            # Bate numa parede lateral → adiciona spin no eixo Y
            self.vel.y += self.vel.y * SPIN_FACTOR * (1.0 if self.vel.y >= 0 else -1.0)
        elif parede_y and not parede_x:
            # Bate numa parede topo/base → adiciona spin no eixo X
            self.vel.x += self.vel.x * SPIN_FACTOR * (1.0 if self.vel.x >= 0 else -1.0)
        elif parede_x and parede_y:
            # Canto — desvio suave em vez de "teleportar"/travar abruptamente
            angulo_desvio = random.uniform(-15.0, 15.0)
            comprimento = self.vel.length()
            if comprimento > 0:
                self.vel = self.vel.rotate(angulo_desvio)
                self.vel.scale_to_length(comprimento * RESSALTO)

    def _colisao_balizas(self, rink):
        """Ressalto nos postes ou na rede traseira/lateral das balizas."""
        r = BOLA_SIZE // 2
        for obs in (rink.obstaculo_baliza_esq, rink.obstaculo_baliza_dir):
            if obs.collidepoint(self.pos_x, self.pos_y):
                dx_left   = abs(self.pos_x - obs.left)
                dx_right  = abs(self.pos_x - obs.right)
                dy_top    = abs(self.pos_y - obs.top)
                dy_bottom = abs(self.pos_y - obs.bottom)
                min_dist = min(dx_left, dx_right, dy_top, dy_bottom)

                if min_dist == dx_left:
                    self.pos_x = obs.left - r
                    self.vel.x = -abs(self.vel.x) * RESSALTO
                elif min_dist == dx_right:
                    self.pos_x = obs.right + r
                    self.vel.x = abs(self.vel.x) * RESSALTO
                elif min_dist == dy_top:
                    self.pos_y = obs.top - r
                    self.vel.y = -abs(self.vel.y) * RESSALTO
                else:
                    self.pos_y = obs.bottom + r
                    self.vel.y = abs(self.vel.y) * RESSALTO

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
                    # Velocidade relativa do jogador → transferência de momentum mais realista
                    vel_jogador = pygame.math.Vector2(
                        getattr(j, "vel_x", 0.0),
                        getattr(j, "vel_y", 0.0)
                    )
                    vel_relativa = self.vel - vel_jogador
                    dot_rel = vel_relativa.x * nx + vel_relativa.y * ny

                    # Aplicar impulso baseado na velocidade relativa
                    self.vel.x -= 2 * dot_rel * nx
                    self.vel.y -= 2 * dot_rel * ny
                    # Absorção de energia no impacto
                    self.vel   *= 0.75
                    # Transferir parte do impulso ao jogador (se aplicável)
                    self.pos_x += nx * (RAIO_COLISAO - dist + 1)
                    self.pos_y += ny * (RAIO_COLISAO - dist + 1)
                break

    def _verificar_golo(self, rink):
        """Verifica se a bola cruzou a linha de golo pela frente."""
        # Baliza Esquerda (defendida por Vermelho): azul marca ao rematar para a esquerda
        if self.vel.x < 0:
            if (self.pos_x <= rink.linha_golo_esq_x) and (self.pos_x >= rink.linha_golo_esq_x - 35):
                if rink.baliza_topo_y <= self.pos_y <= rink.baliza_base_y:
                    return "golo_azul"

        # Baliza Direita (defendida por Azul): vermelho marca ao rematar para a direita
        if self.vel.x > 0:
            if (self.pos_x >= rink.linha_golo_dir_x) and (self.pos_x <= rink.linha_golo_dir_x + 35):
                if rink.baliza_topo_y <= self.pos_y <= rink.baliza_base_y:
                    return "golo_vermelho"

        return None

    def repor(self, pos):
        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel.update(0, 0)
        self.dono = None
        self._cooldown_dono  = None
        self._cooldown_timer = 0.0
        self._angulo = 0.0
        self.image = self._imagem_base.copy()
        self.rect.center = pos

    def pode_ser_apanhada_por(self, jogador):
        if self.dono is not None:
            return False
        if jogador == self._cooldown_dono and self._cooldown_timer > 0:
            return False
        return True
