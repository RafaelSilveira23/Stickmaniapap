# -*- coding: utf-8 -*-
"""camera.py - câmara em perspetiva (vista de bancada, como na TV).

Ideia principal:
  Toda a lógica do jogo (física, IA, golos) continua num campo PLANO, visto de cima,
  com as coordenadas de sempre ("coordenadas do mundo").
  A câmara só muda a forma como esse campo é DESENHADO no ecrã:
    - o campo vira um trapézio: mais estreito ao fundo, mais largo à frente;
    - as linhas do fundo ficam mais "achatadas" (encurtamento da perspetiva);
    - os jogadores do fundo ficam mais pequenos do que os da frente.

Matemática:
  t = posição vertical no campo, de 0 (fundo) a 1 (frente).
  f(t) = escala horizontal, cresce em linha reta de f_topo até f_base.
  Na perspetiva, a altura de cada "fatia" do campo no ecrã é proporcional a f(t),
  por isso o y no ecrã é o integral de f(t):  G(t) = f_topo*t + (f_base - f_topo)*t²/2.
  Para converter do ecrã para o mundo (ex.: posição do rato) resolve-se a equação
  do 2.º grau G(t) = valor.
"""
import math


class Camera:
    def __init__(self, mundo_x0: float, mundo_y0: float, mundo_w: float, mundo_h: float,
                 ecra_topo: float, ecra_base: float, larg_topo: float, larg_base: float,
                 centro_x: float):
        # Zona do mundo que a câmara mostra (o ringue com as tabelas)
        self.x0, self.y0 = mundo_x0, mundo_y0
        self.w, self.h = mundo_w, mundo_h
        self.cx_mundo = mundo_x0 + mundo_w / 2
        # Onde fica no ecrã
        self.topo, self.base = ecra_topo, ecra_base
        self.cx = centro_x
        self.f_topo = larg_topo / mundo_w
        self.f_base = larg_base / mundo_w
        self._g1 = self._G(1.0)

    # ------------------------------------------------------------------ #

    def _G(self, t: float) -> float:
        return self.f_topo * t + (self.f_base - self.f_topo) * t * t / 2

    def _t(self, wy: float) -> float:
        return (wy - self.y0) / self.h

    def fator(self, wy: float) -> float:
        """Escala horizontal da perspetiva a uma dada profundidade (y do mundo)."""
        t = self._t(wy)
        return self.f_topo + (self.f_base - self.f_topo) * t

    # Os jogadores ficam maiores do que na vista de cima (a câmara está mais perto, como na TV)
    ZOOM_SPRITES = 1.45

    def escala(self, wy: float) -> float:
        """Tamanho dos sprites a esta profundidade (1.0 = tamanho normal)."""
        return self.fator(wy) * self.ZOOM_SPRITES

    def ecra_y(self, wy: float) -> float:
        return self.topo + (self.base - self.topo) * self._G(self._t(wy)) / self._g1

    def projetar(self, wx: float, wy: float) -> tuple[float, float]:
        """Mundo -> ecrã."""
        return (self.cx + (wx - self.cx_mundo) * self.fator(wy), self.ecra_y(wy))

    def desprojetar(self, sx: float, sy: float) -> tuple[float, float]:
        """Ecrã -> mundo (usado para saber para onde aponta o rato)."""
        g = (sy - self.topo) / (self.base - self.topo) * self._g1
        a = (self.f_base - self.f_topo) / 2
        b = self.f_topo
        if abs(a) < 1e-9:
            t = g / b
        else:
            t = (-b + math.sqrt(max(0.0, b * b + 4 * a * g))) / (2 * a)
        wy = self.y0 + t * self.h
        wx = self.cx_mundo + (sx - self.cx) / self.fator(wy)
        return wx, wy
