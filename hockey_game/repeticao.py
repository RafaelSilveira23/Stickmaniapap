# -*- coding: utf-8 -*-
"""
repeticao.py - repetição dos golos, como na televisão.

Durante o jogo guarda-se, em cada frame, uma "fotografia" do que se vê: a imagem e a posição de
cada jogador, dos guarda-redes e da bola (só referências às imagens, que já são novas em cada
frame, por isso não se copia nada). Ficam guardados os últimos REP_GRAVAR_S segundos.

Quando há golo, esse lance fica de lado e continua a gravar-se mais REP_DEPOIS_S segundos (a bola
a entrar na rede). Depois da festa, o lance passa outra vez: à velocidade normal no início e em
câmara lenta (REP_LENTO) no último segundo antes do golo. Qualquer tecla, clique ou botão do
comando salta a repetição. Liga-se e desliga-se nas Definições.

Nos golos da stickada (remate na primeira pessoa) o jogo 2D não viu a bola a voar: a repetição
mostra o lance até ao remate e acrescenta o voo da bola até à baliza.

Não há repetição no jogo online (os dois computadores teriam de a ver ao mesmo tempo) nem no
modo teste.
"""
import math
from collections import deque

import pygame

from componentes import texto
from graficos import sombra_suave

REP_GRAVAR_S = 4.0       # segundos guardados antes do golo
REP_DEPOIS_S = 0.6       # segundos guardados depois do golo
REP_MINIMO_S = 1.0       # lances mais curtos do que isto não se repetem
REP_LENTO = 0.4          # velocidade da câmara lenta
REP_LENTO_ANTES = 1.2    # a câmara lenta começa este tempo antes do golo


class RepeticaoMixin:

    def _rep_reiniciar(self):
        self._rep_buf = deque()          # (dt, fotografia) dos últimos segundos
        self._rep_buf_t = 0.0
        self._rep_lance = None           # lance do golo (a gravar o "depois")
        self._rep_t_golo = 0.0
        self._rep_depois = 0.0
        self._repeticao = None           # repetição a passar

    def _rep_permitida(self) -> bool:
        return getattr(self, "repeticao_golos", True) and not self.online and not self.modo_teste

    def _rep_cortar(self):
        """O lance foi interrompido (falta, stickada sem golo): o que estava gravado já não serve."""
        self._rep_buf.clear()
        self._rep_buf_t = 0.0

    # ------------------------------------------------------------------ #
    # Gravar                                                               #
    # ------------------------------------------------------------------ #

    def _rep_foto(self, bola_pos=None):
        atores = [(a.image, a.pos_x, a.pos_y) for a in list(self.todos_jogadores) + list(self.grupo_gr)]
        b = self.bola
        bx, by = bola_pos if bola_pos is not None else (b.pos_x, b.pos_y)
        return atores, (b.image, bx, by, b.dono is not None)

    def _rep_gravar(self, dt: float):
        """No fim de cada update do jogo."""
        if dt <= 0 or not self._rep_permitida():
            return
        if self._rep_lance is not None:
            if self._rep_depois < REP_DEPOIS_S:            # a bola a entrar na rede
                self._rep_lance.append((dt, self._rep_foto()))
                self._rep_depois += dt
            return
        self._rep_buf.append((dt, self._rep_foto()))
        self._rep_buf_t += dt
        while self._rep_buf and self._rep_buf_t - self._rep_buf[0][0] > REP_GRAVAR_S:
            self._rep_buf_t -= self._rep_buf.popleft()[0]

    def _rep_voo_da_bola(self, origem, destino, velocidade: float):
        """Golo da stickada: acrescenta ao lance a bola a voar do stick até à rede."""
        if not self._rep_buf:
            return
        atores, (img, *_r) = self._rep_buf[-1][1]
        dist = math.hypot(destino[0] - origem[0], destino[1] - origem[1])
        dur = max(0.15, min(0.6, dist / max(300.0, velocidade)))
        n = max(2, round(dur * 60))
        for i in range(1, n + 1):
            k = i / n
            x = origem[0] + (destino[0] - origem[0]) * k
            y = origem[1] + (destino[1] - origem[1]) * k
            self._rep_buf.append((dur / n, (atores, (img, x, y, False))))
            self._rep_buf_t += dur / n

    def _rep_marcar_golo(self):
        """Chamado no golo: o lance fica guardado para a repetição."""
        if not self._rep_permitida() or self._rep_buf_t < REP_MINIMO_S:
            self._rep_lance = None
            self._rep_cortar()
            return
        self._rep_lance = list(self._rep_buf)
        self._rep_t_golo = self._rep_buf_t
        self._rep_depois = 0.0
        self._rep_cortar()

    # ------------------------------------------------------------------ #
    # Passar a repetição                                                   #
    # ------------------------------------------------------------------ #

    def _rep_ou_repor(self, saida: str):
        """Acabou a festa do golo: passa a repetição (se houver) e só depois se repõe o jogo."""
        lance, self._rep_lance = self._rep_lance, None
        if lance and self._rep_permitida():
            tempos, t = [], 0.0
            for dt, _f in lance:
                t += dt
                tempos.append(t)
            self._repeticao = {"lance": lance, "tempos": tempos, "t": 0.0, "fim": t,
                               "lento_desde": self._rep_t_golo - REP_LENTO_ANTES, "saida": saida, "idade": 0.0}
        else:
            self._repor_posicoes(saida=saida)

    def _rep_atualizar(self, dt: float):
        r = self._repeticao
        r["idade"] += dt
        r["t"] += dt * (REP_LENTO if r["t"] >= r["lento_desde"] else 1.0)
        if r["t"] >= r["fim"]:
            self._rep_saltar()

    def _rep_saltar(self):
        r, self._repeticao = self._repeticao, None
        if r is not None:
            self._repor_posicoes(saida=r["saida"])

    def _rep_evento(self, event) -> bool:
        """Durante a repetição, qualquer tecla, clique ou botão a salta. True se tratou o evento."""
        if self._repeticao is None or event.type == pygame.QUIT:
            return False
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self._repeticao["idade"] > 0.25:
            self._rep_saltar()
        return True

    # ------------------------------------------------------------------ #
    # Desenho                                                              #
    # ------------------------------------------------------------------ #

    def _rep_desenhar(self):
        r = self._repeticao
        i = min(len(r["tempos"]) - 1, max(0, _procurar(r["tempos"], r["t"])))
        atores, (b_img, bx, by, com_dono) = r["lance"][i][1]
        s, rink = self.screen, self.rink
        cam = rink.camera
        from settings import COR_FUNDO
        s.fill(COR_FUNDO)
        rink.draw(s)

        class _Ator:
            __slots__ = ("image", "pos_x", "pos_y", "rect_ecra")

            def __init__(self, img, x, y):
                self.image, self.pos_x, self.pos_y = img, x, y

        itens = [(y, _Ator(img, x, y)) for img, x, y in atores]
        na_rede = rink.baliza_topo_y <= by <= rink.baliza_base_y and (bx < rink.linha_golo_esq_x or
                                                                       bx > rink.linha_golo_dir_x)
        if not na_rede:
            itens.append((by + (8 if com_dono else 0), None))
        itens.sort(key=lambda t: t[0])

        def bola():
            k = cam.fator(by) * 1.1
            img = b_img
            if abs(k - 1.0) > 0.01:
                img = pygame.transform.smoothscale(img, (max(1, round(img.get_width() * k)),
                                                         max(1, round(img.get_height() * k))))
            sx, sy = cam.projetar(bx, by)
            sombra = sombra_suave(max(4, round(20 * k)), max(2, round(8 * k)), 120)
            s.blit(sombra, sombra.get_rect(center=(round(sx + 2 * k), round(sy + 5 * k))))
            s.blit(img, img.get_rect(center=(round(sx), round(sy))))

        for prof, a in itens:
            if prof >= rink.baliza_topo_y:
                break
            bola() if a is None else self._desenhar_ator(a, cam)
        if na_rede:
            bola()
        rink.draw_frente(s)
        for prof, a in itens:
            if prof >= rink.baliza_topo_y:
                bola() if a is None else self._desenhar_ator(a, cam)

        self.hud.draw_top_bar(s, self)
        self.hud.draw_bottom_panel(s, self)
        self._rep_moldura(s, r)

    def _rep_moldura(self, s, r):
        """Faixas, «REPETIÇÃO» a piscar e como saltar."""
        area = self.rink.rect
        caixa = pygame.Rect(28, 140, 196, 36)          # canto de cima, à esquerda (como na televisão)
        pygame.draw.rect(s, (10, 14, 24), caixa.inflate(6, 6), border_radius=10)
        pygame.draw.rect(s, (200, 30, 40), caixa, border_radius=8)
        if int(r["idade"] * 2) % 2 == 0:
            pygame.draw.circle(s, (255, 255, 255), (caixa.left + 20, caixa.centery), 6)
        texto(s, "REPETIÇÃO", 20, (255, 255, 255), (caixa.centerx + 12, caixa.centery))
        # Barra do tempo da repetição
        barra = pygame.Rect(caixa.left, caixa.bottom + 6, caixa.width, 4)
        pygame.draw.rect(s, (30, 40, 70), barra, border_radius=2)
        cheia = barra.copy()
        cheia.width = round(barra.width * min(1.0, r["t"] / max(0.01, r["fim"])))
        pygame.draw.rect(s, (255, 255, 255), cheia, border_radius=2)
        if r["t"] >= r["lento_desde"]:
            texto(s, "CÂMARA LENTA", 14, (255, 215, 120), (caixa.left, barra.bottom + 14), ancora="midleft",
                  sombra=True)
        _x, base = self.rink.camera.projetar(area.centerx, area.bottom)
        texto(s, "qualquer tecla ou botão para saltar", 13, (220, 230, 255),
              (s.get_width() // 2, round(base) + 14), sombra=True, negrito=False)


def _procurar(tempos, t) -> int:
    """Índice do último frame com tempo <= t (procura binária)."""
    lo, hi = 0, len(tempos) - 1
    while lo < hi:
        m = (lo + hi + 1) // 2
        if tempos[m] <= t:
            lo = m
        else:
            hi = m - 1
    return lo
