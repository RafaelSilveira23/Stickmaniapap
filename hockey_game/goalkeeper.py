# -*- coding: utf-8 -*-
"""goalkeeper.py - Guarda-redes com sprites próprios e IA de defesa.

Diferenças em relação ao Player de campo:
  - Só se move verticalmente (eixo Y), dentro dos limites da baliza
  - Tem animações próprias: parado, mover_cima/baixo/esquerda/direita, defender_01/02
  - Não apanha a bola nem remata — só bloqueia
  - A IA segue a bola verticalmente e tenta interpor-se
"""
import os
import math
import pygame
from settings import *
from animation import AnimationController, load_animation_from_folder, load_single_frame
from cores import cor_texto_sobre, escurecer_stick
from player import sombra_oval

# Tamanho do sprite do guarda-redes no ecrã
GR_SIZE     = (56, 56)
_TELA_GR    = (GR_SIZE[0] + 16, GR_SIZE[1] + 12)   # espaço extra para a sombra e a inclinação
GR_SPEED    = 240      # velocidade vertical máxima (mais rápido que jogador normal)
GR_ACCEL    = 2400     # aceleração (px/s²)

# Distância a que o GR reage à bola e entra em modo "defender"
GR_ALERTA   = 220


def _pasta_gr():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "hd", "frames", "guarda_redes")


def _carregar_animacoes_gr() -> dict:
    pasta = _pasta_gr()
    s = GR_SIZE
    anims = {
        "parado":        load_single_frame(os.path.join(pasta, "parado.png"), scale=s),
        "mover_cima":    load_single_frame(os.path.join(pasta, "mover_cima.png"),    scale=s),
        "mover_baixo":   load_single_frame(os.path.join(pasta, "mover_baixo.png"),   scale=s),
        "mover_direita": load_single_frame(os.path.join(pasta, "mover_direita.png"), scale=s),
        "mover_esquerda":load_single_frame(os.path.join(pasta, "mover_esquerda.png"),scale=s),
        "defender":      load_animation_from_folder(pasta, "defender", fps=8.0,
                                                    loop=True, scale=s),
    }
    for estado, anim in anims.items():
        # o stick do GR é quase creme (pouco saturado), por isso aceitamos menos saturação
        anim.frames = escurecer_stick(("gr", estado, s), anim.frames, sat_min=0.08)
    return anims


class Goalkeeper(pygame.sprite.Sprite):
    """
    Guarda-redes.

    Parâmetros
    ----------
    equipa       : 'azul' ou 'vermelho'
    lado         : 'esq' ou 'dir' — de que lado do campo fica
    baliza_rect  : pygame.Rect da boca da baliza (geometria de deteção de golos)
    pos_x_fixo   : posição X fixa onde o GR fica (à frente da linha da baliza)
    """

    def __init__(self, equipa: str, lado: str,
                 baliza_rect: pygame.Rect, pos_x_fixo: float,
                 dificuldade: str = "normal"):
        super().__init__()

        self.equipa = equipa
        self.lado   = lado
        self.nome   = "Guarda-redes"
        self.numero = 1
        self.tem_bola = False          # GR nunca tem a bola (não apanha)

        # Animações
        self._anim = AnimationController(_carregar_animacoes_gr())
        self.image = self._anim.imagem

        # Limites verticais: GR move-se dentro da abertura da baliza
        # Margem pequena para o sprite não sair completamente da rede
        margem = GR_SIZE[1] // 4   # 14px — suficiente para parecer dentro
        self._y_min = baliza_rect.top    + margem
        self._y_max = baliza_rect.bottom - margem
        # Garantir que os limites fazem sentido mesmo com balizas pequenas
        if self._y_min >= self._y_max:
            self._y_min = baliza_rect.centery - 10
            self._y_max = baliza_rect.centery + 10

        # Posição inicial: centro da baliza
        self.pos_x = float(pos_x_fixo)
        self.pos_y = float(baliza_rect.centery)

        self.vel_y  = 0.0
        self._target_y = self.pos_y

        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Cooldown da animação de defesa
        self._defender_timer = 0.0
        self.definir_dificuldade(dificuldade)

    def definir_dificuldade(self, nivel: str):
        self.dificuldade = nivel
        if nivel == "facil":
            self.speed = 170
            self.alerta_dist = 175
        elif nivel == "dificil":
            self.speed = 310
            self.alerta_dist = 280
        else:
            self.speed = 240
            self.alerta_dist = 220

    # ================================================================== #
    # Update principal (chamado pelo game.py)                             #
    # ================================================================== #

    def update(self, dt: float, bola):
        self._ia_decidir(bola)
        self._mover(dt)
        self._atualizar_animacao(dt, bola)

    # ------------------------------------------------------------------ #
    # IA do guarda-redes                                                   #
    # ------------------------------------------------------------------ #

    def _ia_decidir(self, bola):
        """
        Define _target_y: o GR tenta alinhar-se verticalmente com a bola.
        Não sai dos limites da baliza.
        """
        # Alvo = posição Y da bola, clampada aos limites da baliza
        alvo_y = max(self._y_min, min(self._y_max, bola.pos_y))
        self._target_y = alvo_y

        # Ativar animação de defender quando a bola se aproxima
        dist = math.hypot(bola.pos_x - self.pos_x, bola.pos_y - self.pos_y)
        if dist < self.alerta_dist and self._defender_timer <= 0:
            self._defender_timer = 0.4   # mostra animação de defender por 0.4s

    # ------------------------------------------------------------------ #
    # Movimento vertical com inércia                                       #
    # ------------------------------------------------------------------ #

    def _mover(self, dt: float):
        dy = self._target_y - self.pos_y
        taxa = GR_ACCEL * dt

        if abs(dy) <= taxa:
            self.pos_y = self._target_y
            self.vel_y = 0.0
        else:
            # Aceleração proporcional à distância (mais rápido quando longe)
            vel_desejada = math.copysign(
                min(self.speed, abs(dy) * 4),   # proporcional mas limitada
                dy
            )
            self.vel_y = vel_desejada

        self.pos_y += self.vel_y * dt

        # Clamp aos limites
        self.pos_y = max(self._y_min, min(self._y_max, self.pos_y))
        self.rect.center = (round(self.pos_x), round(self.pos_y))

    # ------------------------------------------------------------------ #
    # Animação                                                             #
    # ------------------------------------------------------------------ #

    def _atualizar_animacao(self, dt: float, bola):
        self._defender_timer = max(0.0, self._defender_timer - dt)

        if self._defender_timer > 0:
            self._anim.estado = "defender"
        elif abs(self.vel_y) > 8:
            self._anim.estado = "mover_cima" if self.vel_y < 0 else "mover_baixo"
        else:
            self._anim.estado = "parado"

        self._anim.update(dt)
        img = self._anim.imagem
        if self.lado == "dir":
            img = pygame.transform.flip(img, True, False)

        # Pequeno balanço ao deslizar e inclinação para o lado da bola ao defender
        self._fase = (getattr(self, "_fase", 0.0) + dt * 10) if abs(self.vel_y) > 8 else 0.0
        bob = -round(abs(math.sin(self._fase)) * 2)
        angulo = 0.0
        if self._anim.estado == "defender":
            # Inclina o corpo na direção vertical da bola (estica-se para ela)
            dy = max(-1.0, min(1.0, (bola.pos_y - self.pos_y) / 40))
            angulo = -dy * 10 if self.lado == "esq" else dy * 10
            img = pygame.transform.rotozoom(img, angulo, 1.0)

        tela = pygame.Surface(_TELA_GR, pygame.SRCALPHA)
        cx = _TELA_GR[0] // 2
        pes_y = _TELA_GR[1] // 2 + GR_SIZE[1] // 2 - 2
        sombra = sombra_oval(40, 11)
        tela.blit(sombra, (cx - sombra.get_width() // 2, pes_y - 6))
        tela.blit(img, img.get_rect(center=(cx, _TELA_GR[1] // 2 + bob)))
        self.image = tela
        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

    # ------------------------------------------------------------------ #
    # Bloquear a bola (chamado por game.py após update da bola)           #
    # ------------------------------------------------------------------ #

    def bloquear_bola(self, bola) -> bool:
        """
        Verifica se o GR está a bloquear a bola.
        Se a bola colidir com o corpo do GR, ressalta.
        Retorna True se bloqueou.
        """
        if bola.dono is not None:
            return False

        dist = math.hypot(bola.pos_x - self.pos_x, bola.pos_y - self.pos_y)
        raio_colisao = GR_SIZE[0] // 2 + 6

        if dist < raio_colisao and dist > 0.1:
            # Ressalta: inverte componente X (a bola vinha em direção ao GR)
            nx = (bola.pos_x - self.pos_x) / dist
            ny = (bola.pos_y - self.pos_y) / dist
            dot = bola.vel.x * nx + bola.vel.y * ny
            if dot < 0:
                bola.vel.x -= 2 * dot * nx
                bola.vel.y -= 2 * dot * ny
                bola.vel   *= 0.8
                # Empurra a bola para fora
                bola.pos_x += nx * (raio_colisao - dist + 2)
                bola.pos_y += ny * (raio_colisao - dist + 2)
                # Ativa animação de defender
                self._defender_timer = 0.5
                return True
        return False

    # ------------------------------------------------------------------ #
    # Desenho extra (número por cima)                                      #
    # ------------------------------------------------------------------ #

    def draw_extra(self, screen: pygame.Surface, font: pygame.font.Font):
        """Etiqueta 'GR' com a cor do equipamento da equipa."""
        kit = getattr(self, "kit", None)
        fundo = kit["principal"] if kit else (20, 30, 60)
        cor_txt = cor_texto_sobre(fundo)
        t = font.render("GR", True, cor_txt)
        caixa = pygame.Rect(0, 0, t.get_width() + 8, t.get_height() + 2)
        caixa.midbottom = (self.rect.centerx, self.rect.top - 1)
        pygame.draw.rect(screen, fundo, caixa, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), caixa, 1, border_radius=4)
        screen.blit(t, (caixa.centerx - t.get_width() // 2, caixa.centery - t.get_height() // 2))
