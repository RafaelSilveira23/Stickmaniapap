# -*- coding: utf-8 -*-
"""ball.py - bola com física realista de hóquei em patins (ressaltos, tabelas e balizas)."""
import os
import math
import random
import pygame
from settings import *

BOLA_SIZE        = 11             # era 14: ficava quase do tamanho da cabeça do jogador
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
        self._imagem_base = pygame.transform.smoothscale(img, (BOLA_SIZE, BOLA_SIZE))
        self.image = self._imagem_base.copy()
        self.rect = self.image.get_rect(center=pos)

        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel   = pygame.math.Vector2(0, 0)
        self.dono  = None
        self.recetor = None        # colega a quem o passe se destina (vai ao encontro da bola)
        self._recetor_timer = 0.0

        self._cooldown_dono  = None
        self._cooldown_timer = 0.0

        # Spin visual
        self._angulo = 0.0   # graus de rotação acumulados

        # Bola no stick: quem a está a conduzir e em que ângulo está à volta dele
        self._seguido = None
        self._ang_stick = 0.0
        self._rink_rect = None
        self._rink = None

    # ------------------------------------------------------------------ #

    def marcar_recetor(self, jogador, tempo: float = 1.6):
        """Indica quem deve ir receber o passe que acabou de ser feito."""
        self.recetor = jogador
        self._recetor_timer = tempo

    def definir_dono(self, jogador):
        self.dono = jogador
        self.recetor = None
        self.vel.update(0, 0)
        self._cooldown_dono  = None
        self._cooldown_timer = 0.0

    def libertar(self, velocidade: pygame.math.Vector2, dono_anterior=None):
        if self.dono is not None:
            self.dono.tem_bola = False
        self._cooldown_dono  = dono_anterior or self.dono
        self._cooldown_timer = COOLDOWN_RECOLHA
        self.dono = None
        self._seguido = None
        self.vel.update(velocidade)

    def seguir_jogador(self, jogador):
        """
        A bola anda à frente do stick de quem a tem.
        Antes saltava de um lado para o outro do jogador quando ele mudava de direção
        (até 44 px num só frame). Agora:
          - a bola RODA à volta do jogador até ao lado para onde ele olha, com velocidade
            limitada (como se o stick a arrastasse);
          - quando alguém apanha a bola, ela DESLIZA até ao stick em vez de aparecer lá.
        """
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            ang_alvo = math.atan2(jogador.vetor_direcao.y, jogador.vetor_direcao.x)
        else:
            ang_alvo = {"direita": 0.0, "esquerda": math.pi,
                        "cima": -math.pi / 2, "baixo": math.pi / 2}.get(jogador.direcao, math.pi / 2)

        novo_dono = jogador is not self._seguido
        if novo_dono:
            # Começa no ângulo em que a bola já está em relação ao jogador
            self._seguido = jogador
            self._ang_stick = math.atan2(self.pos_y + 6 - jogador.pos_y, self.pos_x - jogador.pos_x)

        # Rodar até ao ângulo pretendido (no máximo ~14 rad/s)
        dif = (ang_alvo - self._ang_stick + math.pi) % (2 * math.pi) - math.pi
        passo = 0.24
        self._ang_stick += max(-passo, min(passo, dif))

        tx = jogador.pos_x + math.cos(self._ang_stick) * OFFSET_BOLA
        ty = jogador.pos_y + math.sin(self._ang_stick) * OFFSET_BOLA - 6   # stick um pouco acima do centro

        # Deslizar até ao stick (no máximo 9 px por frame); depois fica colada
        dx, dy = tx - self.pos_x, ty - self.pos_y
        d = math.hypot(dx, dy)
        if d > 9:
            self.pos_x += dx / d * 9
            self.pos_y += dy / d * 9
        else:
            self.pos_x, self.pos_y = tx, ty
        self._dentro_dos_cantos()
        self._fora_das_balizas()
        self.rect.center = (round(self.pos_x), round(self.pos_y))

    def _fora_das_balizas(self):
        """A bola no stick não pode ficar dentro da estrutura/rede da baliza (ex.: atrás da baliza)."""
        if self._rink is None:
            return
        r = BOLA_SIZE / 2
        for obs in (self._rink.obstaculo_baliza_esq, self._rink.obstaculo_baliza_dir):
            o = obs.inflate(2 * r, 2 * r)
            if o.collidepoint(self.pos_x, self.pos_y):
                d = {"esq": self.pos_x - o.left, "dir": o.right - self.pos_x,
                     "cima": self.pos_y - o.top, "baixo": o.bottom - self.pos_y}
                lado = min(d, key=d.get)
                if lado == "esq":
                    self.pos_x = o.left
                elif lado == "dir":
                    self.pos_x = o.right
                elif lado == "cima":
                    self.pos_y = o.top
                else:
                    self.pos_y = o.bottom

    def _dentro_dos_cantos(self) -> bool:
        """
        O rinque tem cantos arredondados (raio CANTO). Se a bola estiver fora dessa curva,
        volta a pô-la lá dentro. Devolve a normal (nx, ny) da tabela se houve correção.
        """
        r_rect = self._rink_rect
        if r_rect is None:
            return None
        rb = BOLA_SIZE / 2
        cx = min(max(self.pos_x, r_rect.left + CANTO), r_rect.right - CANTO)
        cy = min(max(self.pos_y, r_rect.top + CANTO), r_rect.bottom - CANTO)
        dx, dy = self.pos_x - cx, self.pos_y - cy
        d = math.hypot(dx, dy)
        if d <= CANTO - rb or d < 1e-6:
            return None
        nx, ny = dx / d, dy / d
        self.pos_x = cx + nx * (CANTO - rb)
        self.pos_y = cy + ny * (CANTO - rb)
        return nx, ny

    # ------------------------------------------------------------------ #

    def update(self, dt, rink, todos_jogadores=None, guarda_redes=()):
        self._rink_rect = rink.rect
        self._rink = rink
        # Temporizador de imunidade para quem acabou de rematar/passar
        if self._cooldown_timer > 0:
            self._cooldown_timer -= dt
            if self._cooldown_timer <= 0:
                self._cooldown_dono  = None
                self._cooldown_timer = 0.0

        if self._recetor_timer > 0:
            self._recetor_timer -= dt
            if self._recetor_timer <= 0 or self.vel.length() < 30:
                self.recetor = None

        if self.dono is not None:
            self.rect.center = (round(self.pos_x), round(self.pos_y))
            return None

        # Movimento
        pos_anterior = (self.pos_x, self.pos_y)
        self.pos_x += self.vel.x * dt
        self.pos_y += self.vel.y * dt

        # Spin visual — rotação proporcional à velocidade actual
        vel_atual = self.vel.length()
        self._angulo += vel_atual * dt * SPIN_RATE
        self._angulo %= 360.0
        self.image = pygame.transform.rotate(self._imagem_base, self._angulo)
        self.rect  = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Defesa dos guarda-redes ANTES de ver se é golo (senão a bola podia cruzar a
        # linha de golo no mesmo frame em que devia ter batido no GR)
        for gr in guarda_redes:
            if gr.bloquear_bola(self, pos_anterior):
                break

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

        # Cantos arredondados: ressalta na curva da tabela (antes a bola entrava um pouco no canto)
        n = self._dentro_dos_cantos()
        if n is not None and not (parede_x or parede_y):
            vn = self.vel.x * n[0] + self.vel.y * n[1]
            if vn > 0:
                self.vel.x -= (1 + RESSALTO) * vn * n[0]
                self.vel.y -= (1 + RESSALTO) * vn * n[1]
            return

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

    def parar(self):
        self.vel.update(0, 0)
        self.dono = None
        self._cooldown_dono = None
        self._cooldown_timer = 0.0
        self.recetor = None
        self._seguido = None

    def repor(self, pos):
        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])
        self.vel.update(0, 0)
        self.dono = None
        self._cooldown_dono  = None
        self._cooldown_timer = 0.0
        self._angulo = 0.0
        self.recetor = None
        self._seguido = None
        self.image = self._imagem_base.copy()
        self.rect.center = pos

    def pode_ser_apanhada_por(self, jogador):
        if self.dono is not None:
            return False
        if jogador == self._cooldown_dono and self._cooldown_timer > 0:
            return False
        return True
