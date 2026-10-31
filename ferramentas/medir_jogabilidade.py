# -*- coding: utf-8 -*-
"""medir_jogabilidade.py - joga partidas IA contra IA sem janela e conta problemas de jogabilidade
(golos, remates, passes, faltas, "pingue-pongue" da bola, jogadores a tremer ou sobrepostos...).

Uso (a partir da pasta do projeto):
    python ferramentas/medir_jogabilidade.py hockey_game [minutos] [jogos]
"""
import os, sys, math, random
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
PASTA = os.path.abspath(sys.argv[1])
MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 3
SEEDS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
sys.path.insert(0, PASTA)
os.chdir(PASTA)
import pygame
pygame.init()
import game as G
from ai import AgentIA
from player import SEP_JOGADORES
import player as PL, goalkeeper as GK
_r = PL.Player.fazer_remate
def _rem(self, b, d):
    if self.tem_bola: soma("remates", 1)
    _r(self, b, d)
PL.Player.fazer_remate = _rem
_p = PL.Player.fazer_passe
def _pas(self, b, d):
    if self.tem_bola: soma("passes", 1)
    _p(self, b, d)
PL.Player.fazer_passe = _pas
_bq = GK.Goalkeeper.bloquear_bola
def _blq(self, b, *a):
    r = _bq(self, b, *a)
    if r: soma("defesas_gr", 1)
    return r
GK.Goalkeeper.bloquear_bola = _blq

DT = 1 / 60
tot = {}


def soma(k, v):
    tot[k] = tot.get(k, 0) + v


for seed in range(SEEDS):
    random.seed(seed)
    g = G.Game()
    g.iniciar_partida("fc_porto", "benfica", dificuldade="normal")
    g._msg_timer = 0
    # O jogador "humano" passa a ser controlado pela IA (para jogo IA vs IA)
    h = g.jogador_humano
    h.humano = False
    g._auto_selecionar = lambda: None
    g._trocar_humano = lambda novo: None
    g.agentes_azul.append(AgentIA(h, h.papel, "azul", h.pos_tatica, g.rink.baliza_dir, g.rink.baliza_esq, "normal", **({"gr_adversario": g.gr_vermelho} if "gr_adversario" in AgentIA.__init__.__code__.co_varnames else {})))
    g.tempo_restante = 1e9
    r = g.rink.rect
    jog = list(g.todos_jogadores)
    ant = {j: (j.pos_x, j.pos_y) for j in jog}
    desl_ant = {j: (0.0, 0.0) for j in jog}
    dono_ant, t_troca = None, -9
    t_livre = 0.0
    parado_baliza = {j: 0.0 for j in jog}
    golos0 = 0
    n = int(MIN * 60 * 60)
    for f in range(n):
        t = f * DT
        g.update(DT)
        if g._falta_ativa:
            pass
        # trocas de posse e "pingue-pongue"
        d = g.bola.dono
        if d is not None and d is not dono_ant:
            if dono_ant is not None and d.equipa != dono_ant.equipa:
                soma("trocas_posse", 1)
                if t - t_troca < 0.6:
                    soma("pingue_pongue", 1)
                t_troca = t
            dono_ant = d
        # tremer: deslocamento que inverte o sentido de um frame para o outro
        for j in jog:
            dx, dy = j.pos_x - ant[j][0], j.pos_y - ant[j][1]
            px, py = desl_ant[j]
            m1, m0 = math.hypot(dx, dy), math.hypot(px, py)
            if m1 > 0.4 and m0 > 0.4 and (dx * px + dy * py) / (m1 * m0) < -0.3:
                soma("tremer", 1)
            desl_ant[j] = (dx, dy)
            ant[j] = (j.pos_x, j.pos_y)
            if not (r.left <= j.pos_x <= r.right and r.top <= j.pos_y <= r.bottom):
                soma("fora_rinque", 1)
            # IA presa contra a baliza
            for obs in (g.rink.obstaculo_baliza_esq, g.rink.obstaculo_baliza_dir):
                if obs.inflate(40, 40).collidepoint(j.pos_x, j.pos_y) and math.hypot(j.vel_x, j.vel_y) < 25 \
                        and math.hypot(j._target_vx, j._target_vy) > 60:
                    soma("preso_baliza_s", DT)
        # sobreposições
        for i in range(len(jog)):
            for k in range(i + 1, len(jog)):
                if math.hypot(jog[i].pos_x - jog[k].pos_x, jog[i].pos_y - jog[k].pos_y) < SEP_JOGADORES * 0.75:
                    soma("sobrepostos", 1)
        # bola parada sem ninguém a ir buscá-la
        b = g.bola
        if b.dono is None and b.vel.length() < 25:
            perto = min(math.hypot(j.pos_x - b.pos_x, j.pos_y - b.pos_y) for j in jog)
            if perto > 45:
                t_livre += DT
                if t_livre > 1.5:
                    soma("bola_abandonada_s", DT)
            else:
                t_livre = 0
        else:
            t_livre = 0
    soma("golos", g.golos_azul + g.golos_vermelho)
    soma("faltas", g.faltas_azul + g.faltas_vermelho)

print(f"{SEEDS} jogos x {MIN} min (IA vs IA):")
for k in ("remates", "defesas_gr", "passes", "golos", "faltas", "trocas_posse", "pingue_pongue", "tremer", "sobrepostos", "fora_rinque",
          "preso_baliza_s", "bola_abandonada_s"):
    v = tot.get(k, 0)
    print(f"  {k:20s} {v/SEEDS:10.1f} por jogo")
