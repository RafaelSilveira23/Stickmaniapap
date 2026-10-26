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

# Velocidades base da IA (ajustadas dinamicamente pelo perfil de dificuldade)
VEL_NORMAL  = 175
VEL_SPRINT  = 270
VEL_DEFESA  = 155

# Distância a que um jogador da IA tenta apanhar a bola
RAIO_PERSEGUIR = 180

# Distância mínima entre jogadores da mesma equipa (separação)
SEP_MIN = 45

# ── Perfis de Dificuldade da IA ─────────────────────────────────────────
DIFICULDADES = {
    "facil": {
        "id": "facil",
        "nome": "Fácil",
        "vel_normal": 140,
        "vel_sprint": 205,
        "vel_defesa": 120,
        "raio_perseguir": 135,
        "remate_cooldown": 2.2,
        "passe_cooldown": 1.8,
        "dist_remate": 170,
        "erro_mira": 0.22,           # ~12.5 graus de dispersão
        "agressividade": 0.30,
        "descricao": "IA mais calma, velocidade moderada e desarme suave",
        "cor": (80, 200, 120),
    },
    "normal": {
        "id": "normal",
        "nome": "Normal",
        "vel_normal": 175,
        "vel_sprint": 265,
        "vel_defesa": 150,
        "raio_perseguir": 190,
        "remate_cooldown": 1.4,
        "passe_cooldown": 1.0,
        "dist_remate": 225,
        "erro_mira": 0.08,           # ~4.5 graus de dispersão
        "agressividade": 0.60,
        "descricao": "IA equilibrada com boa ocupação de espaços e pressão moderada",
        "cor": (60, 160, 255),
    },
    "dificil": {
        "id": "dificil",
        "nome": "Difícil",
        "vel_normal": 215,
        "vel_sprint": 320,
        "vel_defesa": 185,
        "raio_perseguir": 265,
        "remate_cooldown": 0.75,
        "passe_cooldown": 0.5,
        "dist_remate": 290,
        "erro_mira": 0.02,           # remates cirúrgicos
        "agressividade": 0.90,
        "descricao": "IA veloz, pressão agressiva, passes rápidos e pontaria de elite",
        "cor": (255, 75, 75),
    }
}


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
                 baliza_adversaria: pygame.Rect,
                 dificuldade: str = "normal"):
        self.jogador = jogador
        self.papel = papel
        self.equipa = equipa
        self.pos_base = pos_base
        self.baliza_propria = baliza_propria
        self.baliza_adversaria = baliza_adversaria

        self.dificuldade = dificuldade
        self.cfg = DIFICULDADES.get(dificuldade, DIFICULDADES["normal"])

        # Pequena variação aleatória para evitar que todos façam o mesmo
        self._offset_x = random.uniform(-20, 20)
        self._offset_y = random.uniform(-20, 20)

        # Cooldown para o remate (evita rematar 60x por segundo)
        self._remate_cooldown = 0.0
        self._passe_cooldown  = 0.0

    def definir_dificuldade(self, nivel: str):
        """Atualiza a dificuldade e recalibra parâmetros táticos da IA."""
        if nivel in DIFICULDADES:
            self.dificuldade = nivel
            self.cfg = DIFICULDADES[nivel]

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

        dist_max_remate = self.cfg.get("dist_remate", 225)

        if dist_baliza < dist_max_remate and self._remate_cooldown <= 0:
            # Remata com desvio/imprecisão conforme a dificuldade configurada
            v = pygame.math.Vector2(dx, dy)
            if v.length() > 0:
                v.normalize_ip()
                erro = self.cfg.get("erro_mira", 0.08)
                if erro > 0:
                    ang_erro = random.uniform(-erro, erro)
                    v = v.rotate_rad(ang_erro)
            j.fazer_remate(bola, v)
            self._remate_cooldown = self.cfg.get("remate_cooldown", 1.4)

        elif adversario_bloqueio and self._passe_cooldown <= 0 and colegas:
            # Passa para o colega mais bem posicionado
            alvo = self._melhor_colega_passe(colegas)
            if alvo:
                vx = alvo.pos_x - j.pos_x
                vy = alvo.pos_y - j.pos_y
                v = pygame.math.Vector2(vx, vy)
                if v.length() > 0:
                    v.normalize_ip()
                    erro = self.cfg.get("erro_mira", 0.08) * 0.5
                    if erro > 0:
                        v = v.rotate_rad(random.uniform(-erro, erro))
                j.fazer_passe(bola, v)
                self._passe_cooldown = self.cfg.get("passe_cooldown", 1.0)

        else:
            # Avança para a baliza com velocidade de sprint configurada
            spd = self.cfg.get("vel_sprint", VEL_SPRINT)
            self._mover_para(bx + self._offset_x, by + self._offset_y, spd)

    def _estado_defender(self, dt, bola):
        """Adversário tem a bola — volta à zona defensiva ou pressiona a bola."""
        j = self.jogador
        vel_norm = self.cfg.get("vel_normal", VEL_NORMAL)
        vel_def  = self.cfg.get("vel_defesa", VEL_DEFESA)
        vel_spr  = self.cfg.get("vel_sprint", VEL_SPRINT)
        agressiva = self.cfg.get("agressividade", 0.6)

        # Avançados pressionam a bola; defesas voltam para casa
        if self.papel == 'avancado':
            tx = bola.pos_x
            ty = bola.pos_y
            limite_x = self.baliza_adversaria.centerx
            if self.equipa == 'vermelho':
                tx = max(tx, limite_x - 240)
            else:
                tx = min(tx, limite_x + 240)
            spd = vel_spr if agressiva >= 0.8 else vel_norm
            self._mover_para(tx, ty, spd)

        elif self.papel == 'medio':
            tx = (bola.pos_x + self.pos_base[0]) / 2
            ty = (bola.pos_y + self.pos_base[1]) / 2
            self._mover_para(tx + self._offset_x, ty + self._offset_y, vel_norm)

        else:  # defesa
            tx = self.pos_base[0] + self._offset_x
            ty = self.pos_base[1] + self._offset_y
            dist_bola = math.hypot(bola.pos_x - j.pos_x, bola.pos_y - j.pos_y)
            raio_intervencao = 150 if agressiva >= 0.75 else 115
            if dist_bola < raio_intervencao:
                self._mover_para(bola.pos_x, bola.pos_y, vel_def * 1.15)
            else:
                self._mover_para(tx, ty, vel_def)

    def _estado_apoiar(self, dt, bola, colegas):
        """Colega tem a bola — posiciona-se para receber passe."""
        j = self.jogador
        tx = self.pos_base[0] + self._offset_x
        ty = self.pos_base[1] + self._offset_y
        self._mover_para(tx, ty, self.cfg.get("vel_normal", VEL_NORMAL))

    def _estado_perseguir(self, dt, bola, colegas):
        """
        Bola livre — APENAS o jogador mais perto da equipa vai buscá-la.
        Os restantes mantêm posições táticas.
        """
        j = self.jogador
        dist_propria = math.hypot(bola.pos_x - j.pos_x, bola.pos_y - j.pos_y)
        raio_max = self.cfg.get("raio_perseguir", RAIO_PERSEGUIR)

        if colegas:
            dist_min_colega = min(
                math.hypot(bola.pos_x - c.pos_x, bola.pos_y - c.pos_y)
                for c in colegas
            )
        else:
            dist_min_colega = float("inf")

        # Só persegue se for o mais perto e estiver dentro do alcance de perseguição
        e_o_mais_perto = (dist_propria < dist_min_colega - 35) and (dist_propria < raio_max + 90)

        if e_o_mais_perto:
            self._mover_para(bola.pos_x, bola.pos_y, self.cfg.get("vel_sprint", VEL_SPRINT))
        else:
            self._mover_para(
                self.pos_base[0] + self._offset_x,
                self.pos_base[1] + self._offset_y,
                self.cfg.get("vel_normal", VEL_NORMAL)
            )

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
