# -*- coding: utf-8 -*-
"""ai.py - Inteligência Artificial dos jogadores controlados pelo computador.

Cada jogador da IA tem um PAPEL que define o seu comportamento base:
  'avancado'  - fica na frente, pressiona, tenta marcar
  'medio'     - liga ataque e defesa, apoia passes
  'defesa'    - fica atrás, bloqueia, só avança quando tem bola

A IA funciona em estados:
  PERSEGUIR_BOLA  - vai buscar a bola quando está perto e livre
  POSICIONAR      - vai para a posição tática quando outro colega tem a bola
  ATACAR          - tem a bola, avança para a baliza adversária
  DEFENDER        - a equipa adversária tem a bola, volta à zona defensiva

Cada frame, a IA calcula a vel_x/vel_y do jogador.
O player.py aplica essa velocidade no movimento.
"""
import pygame
import math
import random

# Velocidades da IA (um pouco abaixo do humano para ser jogável)
VEL_NORMAL  = 175
VEL_SPRINT  = 270
VEL_DEFESA  = 155

# Distância a que um jogador da IA tenta apanhar a bola
RAIO_PERSEGUIR = 180

# Distância mínima entre jogadores da mesma equipa (separação)
SEP_MIN = 45


class AgentIA:
    """
    Controla um único jogador da IA.

    Parâmetros
    ----------
    jogador   : referência ao Player que esta IA controla
    papel     : 'avancado', 'medio' ou 'defesa'
    equipa    : 'azul' ou 'vermelho'
    pos_base  : (x, y) posição tática de referência no campo
    baliza_propria  : Rect da baliza que esta equipa defende
    baliza_adversaria : Rect da baliza que esta equipa ataca
    """

    def __init__(self, jogador, papel: str, equipa: str,
                 pos_base: tuple,
                 baliza_propria: pygame.Rect,
                 baliza_adversaria: pygame.Rect):
        self.jogador = jogador
        self.papel = papel
        self.equipa = equipa
        self.pos_base = pos_base
        self.baliza_propria = baliza_propria
        self.baliza_adversaria = baliza_adversaria

        # Pequena variação aleatória para evitar que todos façam o mesmo
        self._offset_x = random.uniform(-20, 20)
        self._offset_y = random.uniform(-20, 20)

        # Cooldown para o remate (evita rematar 60x por segundo)
        self._remate_cooldown = 0.0
        self._passe_cooldown  = 0.0

    # ------------------------------------------------------------------ #
    # Update principal — chamado cada frame                                #
    # ------------------------------------------------------------------ #

    def update(self, dt: float, bola, colegas: list, adversarios: list):
        """
        Decide o que fazer e define vel_x/vel_y no jogador.
        bola      : instância de Ball
        colegas   : lista de Players da mesma equipa (excluindo este)
        adversarios: lista de Players da equipa adversária
        """
        j = self.jogador

        # Timers
        self._remate_cooldown = max(0.0, self._remate_cooldown - dt)
        self._passe_cooldown  = max(0.0, self._passe_cooldown  - dt)

        if j.tem_bola:
            self._estado_atacar(dt, bola, colegas, adversarios)
        else:
            colega_com_bola = any(c.tem_bola for c in colegas)
            adv_com_bola    = any(a.tem_bola for a in adversarios)

            if adv_com_bola:
                self._estado_defender(dt, bola)
            elif colega_com_bola:
                self._estado_apoiar(dt, bola, colegas)
            else:
                # Bola livre — vai buscá-la se for o mais perto ou avançado
                self._estado_perseguir(dt, bola, colegas)

    # ------------------------------------------------------------------ #
    # Estados                                                              #
    # ------------------------------------------------------------------ #

    def _estado_atacar(self, dt, bola, colegas, adversarios):
        """Tem a bola — avança e tenta marcar."""
        j = self.jogador
        bx = self.baliza_adversaria.centerx
        by = self.baliza_adversaria.centery

        dx = bx - j.pos_x
        dy = by - j.pos_y
        dist_baliza = math.hypot(dx, dy)

        # Verifica se há adversário à frente (para decidir passar ou rematar)
        adversario_bloqueio = self._adversario_no_caminho(adversarios)

        if dist_baliza < 200 and self._remate_cooldown <= 0:
            # Remata!
            v = pygame.math.Vector2(dx, dy)
            if v.length() > 0:
                v.normalize_ip()
            j.fazer_remate(bola, v)
            self._remate_cooldown = 1.5

        elif adversario_bloqueio and self._passe_cooldown <= 0 and colegas:
            # Passa para o colega mais bem posicionado
            alvo = self._melhor_colega_passe(colegas)
            if alvo:
                vx = alvo.pos_x - j.pos_x
                vy = alvo.pos_y - j.pos_y
                v = pygame.math.Vector2(vx, vy)
                if v.length() > 0:
                    v.normalize_ip()
                j.fazer_passe(bola, v)
                self._passe_cooldown = 1.0

        else:
            # Avança para a baliza
            self._mover_para(bx + self._offset_x, by + self._offset_y, VEL_SPRINT)

    def _estado_defender(self, dt, bola):
        """Adversário tem a bola — volta à zona defensiva ou pressiona a bola."""
        j = self.jogador

        # Avançados pressionam a bola; defesas voltam para casa
        if self.papel == 'avancado':
            # Pressiona a bola mas não abandona completamente o meio-campo
            tx = bola.pos_x
            ty = bola.pos_y
            # Limite de até onde o avançado vai perseguir
            limite_x = self.baliza_adversaria.centerx
            if self.equipa == 'vermelho':
                tx = max(tx, limite_x - 200)
            else:
                tx = min(tx, limite_x + 200)
            self._mover_para(tx, ty, VEL_NORMAL)

        elif self.papel == 'medio':
            # Vai para posição entre a bola e a baliza própria
            tx = (bola.pos_x + self.pos_base[0]) / 2
            ty = (bola.pos_y + self.pos_base[1]) / 2
            self._mover_para(tx + self._offset_x, ty + self._offset_y, VEL_NORMAL)

        else:  # defesa
            # Fica na zona, entre a bola e a baliza
            tx = self.pos_base[0] + self._offset_x
            ty = self.pos_base[1] + self._offset_y
            dist_bola = math.hypot(bola.pos_x - j.pos_x, bola.pos_y - j.pos_y)
            if dist_bola < 120:
                # Se a bola estiver perto, vai buscar
                self._mover_para(bola.pos_x, bola.pos_y, VEL_DEFESA)
            else:
                self._mover_para(tx, ty, VEL_DEFESA)

    def _estado_apoiar(self, dt, bola, colegas):
        """Colega tem a bola — posiciona-se para receber passe."""
        j = self.jogador
        # Vai para posição tática com offset para espaçar
        tx = self.pos_base[0] + self._offset_x
        ty = self.pos_base[1] + self._offset_y
        self._mover_para(tx, ty, VEL_NORMAL)

    def _estado_perseguir(self, dt, bola, colegas):
        """
        Bola livre — APENAS o jogador mais perto da equipa vai buscá-la.
        Os restantes mantêm posições táticas.
        """
        j = self.jogador
        dist_propria = math.hypot(bola.pos_x - j.pos_x, bola.pos_y - j.pos_y)

        # Distância do colega mais perto
        if colegas:
            dist_min_colega = min(
                math.hypot(bola.pos_x - c.pos_x, bola.pos_y - c.pos_y)
                for c in colegas
            )
        else:
            dist_min_colega = float("inf")

        # Só persegue se for claramente o mais perto (margem de 40px)
        e_o_mais_perto = dist_propria < dist_min_colega - 40

        if e_o_mais_perto:
            self._mover_para(bola.pos_x, bola.pos_y, VEL_SPRINT)
        else:
            self._mover_para(
                self.pos_base[0] + self._offset_x,
                self.pos_base[1] + self._offset_y,
                VEL_NORMAL
            )

    # ------------------------------------------------------------------ #
    # Utilitários                                                          #
    # ------------------------------------------------------------------ #

    def _mover_para(self, tx: float, ty: float, velocidade: float):
        """Define a velocidade alvo com inércia para mover o jogador em direção a (tx, ty)."""
        j = self.jogador
        dx = tx - j.pos_x
        dy = ty - j.pos_y
        dist = math.hypot(dx, dy)

        if dist < 12:
            # Chegou ao destino — desacelera
            j.set_target(0.0, 0.0)
            return

        # Normalizar e definir velocidade alvo
        nx = dx / dist
        ny = dy / dist
        j.set_target(nx * velocidade, ny * velocidade)
        j.vetor_direcao = pygame.math.Vector2(nx, ny)

        # Atualizar direção para a animação
        if abs(dx) > abs(dy):
            j.direcao = "direita" if dx > 0 else "esquerda"
        else:
            j.direcao = "baixo" if dy > 0 else "cima"

    def _adversario_no_caminho(self, adversarios: list) -> bool:
        """Verifica se há um adversário entre o jogador e a baliza."""
        j = self.jogador
        bx = self.baliza_adversaria.centerx
        by = self.baliza_adversaria.centery
        for adv in adversarios:
            # Distância do adversário à linha jogador→baliza
            dx = bx - j.pos_x
            dy = by - j.pos_y
            dist_linha = abs(dx * (j.pos_y - adv.pos_y) - dy * (j.pos_x - adv.pos_x))
            comprimento = math.hypot(dx, dy)
            if comprimento == 0:
                continue
            distancia_perp = dist_linha / comprimento
            # Está à frente (no sentido da baliza)?
            dot = dx * (adv.pos_x - j.pos_x) + dy * (adv.pos_y - j.pos_y)
            if distancia_perp < 50 and 0 < dot < comprimento * comprimento:
                return True
        return False

    def _melhor_colega_passe(self, colegas: list):
        """Escolhe o colega mais bem posicionado para receber passe (mais perto da baliza adv.)."""
        if not colegas:
            return None
        bx = self.baliza_adversaria.centerx
        by = self.baliza_adversaria.centery
        return min(colegas, key=lambda c: math.hypot(c.pos_x - bx, c.pos_y - by))
