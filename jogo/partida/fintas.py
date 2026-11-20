# -*- coding: utf-8 -*-
"""
fintas.py - fintas (dribles) de quem tem a bola.

O movimento da finta é feito no Player (player.py, comecar_finta / _atualizar_finta) com a
física normal do jogo (velocidade-alvo + inércia), em duas fases:
  1. ENGANO (FINTA_ENGANO s): o corpo e a bola vão para um lado;
  2. CORTE  (FINTA_CORTE s): arranque forte para o lado contrário, com a bola arrastada pelo
     stick de um lado para o outro; no fim a inércia leva o jogador na diagonal.

Aqui (no Game) decide-se:
  - para que lado se finta (setas / stick do jogador, ou para longe do defesa);
  - o que acontece aos defesas que estão à frente: quem vai atrás do engano fica
    desequilibrado e sem poder desarmar uns instantes; fintar demasiado perto pode
    fazer perder a bola;
  - quando é que a IA finta (defesa a fechar à frente, à distância certa).
"""
import math
import random

import pygame

import comando
from sons import som

FINTA_ALCANCE = 120          # defesas a menos disto (e à frente) contam para a finta
FINTA_DIST_IDEAL = (45, 95)  # a finta resulta melhor com o defesa a esta distância
FINTA_PERTO = 40             # mais perto do que isto é arriscado (pode perder a bola)
ROLETA_ALCANCE = 80          # a roleta só conta para defesas mesmo perto
ROLETA_DIST_IDEAL = (30, 65) # a roleta resulta melhor com o defesa já em cima


class FintasMixin:

    def _fintas_reiniciar(self):
        self._pops_finta = []         # textos "FINTA!" por cima dos jogadores: [txt, x, y, t, cor]

    # ------------------------------------------------------------------ #
    # Pedir uma finta                                                      #
    # ------------------------------------------------------------------ #

    def _pedir_finta_humano(self, tipo: str = "corte"):
        """
        Tecla V / Y do comando (corte) ou F / LB do comando (roleta).
        O lado é o das setas (se apontarem para o lado).
        """
        k = comando.teclas()
        dx = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        dy = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        self._pedir_finta(self.jogador_humano, dx, dy, tipo)

    def _pedir_finta(self, j, dx: float = 0.0, dy: float = 0.0, tipo: str = "corte") -> bool:
        if (j is None or not j.tem_bola or not self.jogo_ativo or self.remate_pov is not None
                or getattr(self, "_bola_parada", None) is not None):
            return False
        frente, perp = j.direcao_finta()
        adversarios = list(self.equipa_vermelha if j.equipa == "azul" else self.equipa_azul)

        # Lado do corte: o que as setas pedem (componente para o lado); senão, para longe do
        # defesa mais perto que está à frente
        lado = 0
        pedido = pygame.math.Vector2(dx, dy)
        if pedido.length_squared() > 0:
            comp = pedido.normalize().dot(perp)
            if abs(comp) > 0.3:
                lado = 1 if comp > 0 else -1
        if lado == 0:
            perto = self._defesa_a_frente(j, adversarios, frente)
            if perto is not None:
                s = (perto.pos_x - j.pos_x) * perp.x + (perto.pos_y - j.pos_y) * perp.y
                lado = -1 if s > 0 else 1
            else:
                lado = random.choice((-1, 1))
        if not j.comecar_finta(lado, tipo):
            return False
        som.tocar("passe", 0.25)          # o stick a arrastar a bola
        if tipo == "roleta":
            self._roleta_nos_defesas(j, adversarios)
        else:
            self._finta_nos_defesas(j, adversarios)
        return True

    def _roleta_nos_defesas(self, j, adversarios):
        """
        Roleta: resulta com o defesa já perto (ele é ultrapassado pela volta). Com o defesa
        longe não engana ninguém, mas também quase nunca se perde a bola (o corpo protege-a).
        """
        frente, perp, lado = j._finta["frente"], j._finta["perp"], j._finta["lado"]
        enganou = False
        for d in adversarios:
            v = pygame.math.Vector2(d.pos_x - j.pos_x, d.pos_y - j.pos_y)
            dist = v.length()
            if dist > ROLETA_ALCANCE or dist < 1 or frente.dot(v / dist) < 0.1:
                continue
            p = 0.40 + (getattr(j, "stat_velocidade", 80) - getattr(d, "stat_defesa", 70)) / 150
            if ROLETA_DIST_IDEAL[0] <= dist <= ROLETA_DIST_IDEAL[1]:
                p += 0.18
            else:
                p -= 0.15
            if d.humano:
                p -= 0.10
            p = max(0.10, min(0.85, p))
            if random.random() < p:
                # Fica para trás: a volta passa por ele e ele perde o equilíbrio
                d.vel_x += -perp.x * lado * 80 - frente.x * 60
                d.vel_y += -perp.y * lado * 80 - frente.y * 60
                d._desestabilizado_timer = max(d._desestabilizado_timer, 0.65)
                d._bloqueio_desarme = max(d._bloqueio_desarme, 0.9)
                enganou = True
            elif dist < FINTA_PERTO and random.random() < 0.25:
                # Colado e não foi enganado: mete o stick no meio da volta
                j.cancelar_finta()
                j.desarme_limpo(self.bola, pygame.math.Vector2(v.x, v.y))
                d._cooldown_desarme = 0.0
                self._pop_finta("DESARME!", j, (255, 150, 70))
                return
        if enganou:
            j._roleta_ok_ms = pygame.time.get_ticks()     # para a conquista «roleta mágica»
            j._cooldown_desarme = max(j._cooldown_desarme, 0.5)
            self._pop_finta("ROLETA!", j, (255, 140, 200))
            som.tocar("publico_uh", 0.55)

    @staticmethod
    def _defesa_a_frente(j, adversarios, frente):
        melhor, melhor_d = None, FINTA_ALCANCE
        for d in adversarios:
            v = pygame.math.Vector2(d.pos_x - j.pos_x, d.pos_y - j.pos_y)
            dist = v.length()
            if 1 < dist < melhor_d and frente.dot(v / dist) > 0.2:
                melhor, melhor_d = d, dist
        return melhor

    def _finta_nos_defesas(self, j, adversarios):
        """Os defesas à frente vão (ou não) atrás do engano."""
        f = j._finta
        frente, perp, lado = f["frente"], f["perp"], f["lado"]
        enganou = False
        for d in adversarios:
            v = pygame.math.Vector2(d.pos_x - j.pos_x, d.pos_y - j.pos_y)
            dist = v.length()
            if dist > FINTA_ALCANCE or dist < 1 or frente.dot(v / dist) < 0.2:
                continue
            p = 0.42 + (getattr(j, "stat_velocidade", 80) - getattr(d, "stat_defesa", 70)) / 150
            if FINTA_DIST_IDEAL[0] <= dist <= FINTA_DIST_IDEAL[1]:
                p += 0.12
            elif dist < FINTA_PERTO:
                p -= 0.25
            if d.humano:
                p -= 0.10                 # contra o jogador é mais difícil (ele pode reagir)
            p = max(0.10, min(0.90, p))
            if random.random() < p:
                # Foi atrás do engano: é empurrado para o lado errado e fica desequilibrado
                d.vel_x += -perp.x * lado * 140
                d.vel_y += -perp.y * lado * 140
                d._desestabilizado_timer = max(d._desestabilizado_timer, 0.75)
                d._bloqueio_desarme = max(d._bloqueio_desarme, 1.0)
                enganou = True
            elif dist < FINTA_PERTO and random.random() < 0.5:
                # Leu a finta e estava colado: rouba a bola
                j.cancelar_finta()
                j.desarme_limpo(self.bola, pygame.math.Vector2(v.x, v.y))
                d._cooldown_desarme = 0.0
                self._pop_finta("DESARME!", j, (255, 150, 70))
                return
        if enganou:
            j._cooldown_desarme = max(j._cooldown_desarme, 0.45)
            self._pop_finta("FINTA!", j, (120, 230, 255))
            som.tocar("publico_uh", 0.5)
            if getattr(self, "stats_jogo", None) is not None and "fintas" in self.stats_jogo[j.equipa]:
                self.stats_jogo[j.equipa]["fintas"] += 1

    # ------------------------------------------------------------------ #
    # IA                                                                   #
    # ------------------------------------------------------------------ #

    def _fintas_ia(self, dt: float):
        """Quem tem a bola e é da IA finta às vezes, quando um defesa fecha à frente."""
        dono = self.bola.dono
        if dono is None or dono.humano or getattr(dono, "remoto", False) or dono._finta is not None:
            return
        if dono._finta_cd > 0:
            return
        frente, _perp = dono.direcao_finta()
        adversarios = list(self.equipa_vermelha if dono.equipa == "azul" else self.equipa_azul)
        d = self._defesa_a_frente(dono, adversarios, frente)
        if d is None:
            return
        dist = math.hypot(d.pos_x - dono.pos_x, d.pos_y - dono.pos_y)
        if ROLETA_DIST_IDEAL[0] <= dist < FINTA_DIST_IDEAL[0] + 10:
            tipo = "roleta"               # defesa já em cima: a volta protege a bola
        elif dist <= FINTA_DIST_IDEAL[1] + 10:
            tipo = "corte"
        else:
            return
        # O defesa está a vir na direção de quem tem a bola?
        para_dono = pygame.math.Vector2(dono.pos_x - d.pos_x, dono.pos_y - d.pos_y) / dist
        fecho = (d.vel_x - dono.vel_x) * para_dono.x + (d.vel_y - dono.vel_y) * para_dono.y
        if fecho < 40:
            return
        if random.random() < dt * 0.7 * getattr(dono, "stat_velocidade", 80) / 85:
            if self._pedir_finta(dono, tipo=tipo):
                dono._finta_cd = 3.0      # a IA não finta sempre (o jogador pode voltar a fintar em 1,2 s)

    # ------------------------------------------------------------------ #
    # Desenho                                                              #
    # ------------------------------------------------------------------ #

    def _pop_finta(self, txt, j, cor):
        self._pops_finta.append([txt, j.pos_x, j.pos_y, 0.0, cor])

    def _desenhar_fintas(self, screen, dt: float = 1 / 60):
        if not self._pops_finta:
            return
        from componentes import texto
        cam = self.rink.camera
        for p in list(self._pops_finta):
            p[3] += dt
            if p[3] > 0.8:
                self._pops_finta.remove(p)
                continue
            sx, sy = cam.projetar(p[1], p[2])
            k = p[3] / 0.8
            img_y = sy - 70 - 30 * k
            camada = pygame.Surface((160, 40), pygame.SRCALPHA)
            texto(camada, p[0], 20, p[4], (80, 20), sombra=True)
            camada.set_alpha(int(255 * (1 - k * k)))
            screen.blit(camada, camada.get_rect(center=(sx, img_y)))
