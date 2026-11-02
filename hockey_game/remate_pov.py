# -*- coding: utf-8 -*-
"""remate_pov.py - remate na primeira pessoa.

Quando o jogador carrega em X com a bola, a câmara passa para os olhos do jogador, virada
para a baliza (como num penálti). O jogador:
  • aponta com o rato ou com as setas para qualquer ponto da baliza (também em altura);
  • mantém X (ou o botão do rato) carregado para encher a barra de força e larga para rematar.
Mais força = a bola chega mais depressa (o guarda-redes tem menos tempo), mas o remate fica
menos preciso (o círculo da mira fica maior).

Como se desenha a vista na primeira pessoa (projeção em perspetiva):
  A câmara está no jogador e olha para o centro da baliza. Para cada ponto do campo
  (x, y no chão e uma altura h) calculamos:
      z = distância à frente da câmara      (produto escalar com a direção "em frente")
      x = distância para o lado             (produto escalar com a direção "direita")
      ecrã_x = centro + F · x / z           (o que está longe fica mais perto do centro)
      ecrã_y = horizonte + F · (olhos − h) / z
  Os pontos atrás da câmara (z muito pequeno) são cortados ("clipping").

O resultado (golo, defesa, poste ou fora) é decidido com um modelo simples do guarda-redes:
tempo de reação, velocidade de mergulho, alcance (menor nos cantos de cima) e se "lê" ou não
o lado do remate. Depois o jogo 2D continua com a bola no sítio certo.
"""
import math
import os
import random

import pygame

from settings import WIDTH, HEIGHT
from graficos import titulo_estilizado, luz
from componentes import texto, fonte
from sons import som

F = 1000           # distância focal (quanto maior, mais "zoom")
HORIZONTE = 330    # y do horizonte no ecrã
OLHOS = 30         # altura dos olhos do jogador (unidades do campo)
PERTO = 8          # plano de corte: o que está mais perto do que isto não se desenha
CX = WIDTH // 2

ALTURA_BALIZA = 41      # a baliza de hóquei em patins tem 1,05 m de altura e 1,70 m de largura
MEIA_BOCA = 33
PROF_BALIZA = 38
RAIO_BOLA = 5.5
PX_POR_METRO = 1140 / 40      # o rinque tem 40 m de comprimento e 1140 px

# Guarda-redes por dificuldade: reação (s), velocidade de mergulho, alcance (baixo, meio, alto), leitura
# (valores afinados simulando milhares de remates: ver o relatório, secção 4.2)
GR_PERFIL = {
    "facil":   (0.28, 135, (21, 16, 11), 0.38),
    "normal":  (0.20, 160, (24, 19, 14), 0.47),
    "dificil": (0.15, 210, (26, 21, 16), 0.68),
}


def erro_remate(forca: float, distancia: float, precisao: float = 1.0) -> float:
    """Desvio típico do remate (px): cresce muito com a força (força³) e com a distância."""
    return (1.0 + 6 * forca ** 3) * (distancia / 230) * precisao

_PASTA_GR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sprites_v2", "hd", "frames",
                         "guarda_redes")
_cache = {}


def _img_gr(nome: str) -> pygame.Surface:
    if nome not in _cache:
        _cache[nome] = pygame.image.load(os.path.join(_PASTA_GR, nome + ".png")).convert_alpha()
    return _cache[nome]


def decidir_remate(u_alvo: float, h_alvo: float, forca: float, distancia: float, u_gr: float,
                   dificuldade: str, rnd=random, precisao: float = 1.0) -> dict:
    """
    Decide o que acontece a um remate. É uma função à parte (sem desenho) para se poder testar.
      u_alvo, h_alvo : ponto apontado na baliza (u = de lado, 0 = meio; h = altura)
      forca          : 0 a 1 (barra de força)
      distancia      : distância à baliza (px do campo)
      u_gr           : onde está o guarda-redes no início
    Devolve {"resultado", "u", "h", "u_gr", "velocidade", "tempo", "erro"}.
    """
    velocidade = 320 + 560 * forca
    erro = erro_remate(forca, distancia, precisao)
    u = u_alvo + rnd.gauss(0, erro)
    h = max(0.0, h_alvo + rnd.gauss(0, erro * 0.7))
    tempo = distancia / velocidade

    reacao, vel_gr, alcances, leitura = GR_PERFIL.get(dificuldade, GR_PERFIL["normal"])
    # Antes do remate, o guarda-redes já se inclina um pouco para o lado para onde o jogador aponta
    u_gr = u_gr + max(-12.0, min(12.0, u_alvo * 0.15))
    movimento = max(0.0, tempo - reacao) * vel_gr
    # Quanto mais tempo a bola demora a chegar, mais fácil é "ler" o lado do remate
    leitura *= min(1.0, max(0.2, (tempo - 0.12) / 0.45))
    if rnd.random() < leitura:
        destino = u
    else:
        destino = u_gr + rnd.choice((-1, 1)) * rnd.uniform(5, 25)
    u_gr_final = u_gr + max(-movimento, min(movimento, destino - u_gr))
    u_gr_final = max(-MEIA_BOCA, min(MEIA_BOCA, u_gr_final))
    alcance = alcances[0] if h < 13 else (alcances[1] if h < 27 else alcances[2])

    if abs(u) > MEIA_BOCA + 3 or h > ALTURA_BALIZA + 3:
        resultado = "fora"
    elif abs(abs(u) - MEIA_BOCA) <= 3 or abs(h - ALTURA_BALIZA) <= 3:
        resultado = "poste"
    elif abs(u - u_gr_final) <= alcance:
        resultado = "defesa"
    else:
        resultado = "golo"
    return {"resultado": resultado, "u": u, "h": h, "u_gr": u_gr_final, "u_gr_inicio": u_gr,
            "velocidade": velocidade, "tempo": tempo, "erro": erro}


class RematePOV:
    """
    Ecrã do remate na primeira pessoa. O Game chama handle_event, update e draw; quando
    'terminado' fica True, lê 'resultado' (ou None se o jogador cancelou com ESC).
    """

    def __init__(self, screen, rink, jogador, gr, dificuldade: str, limite_tempo: float | None = 5.0,
                 cor_linhas=(30, 95, 210)):
        self.screen = screen
        self.rink = rink
        self.jogador = jogador
        self.gr = gr
        self.dificuldade = dificuldade
        self.limite = limite_tempo
        self.tempo_restante = limite_tempo or 0.0
        self.cor_linhas = cor_linhas
        self.terminado = False
        self.resultado = None
        self.t = 0.0

        r = rink.rect
        self.gx = rink.linha_golo_esq_x          # o jogador (equipa azul) ataca a baliza da esquerda
        self.cy = r.centery
        self.fora_dir = -1                        # "atrás da baliza" é para a esquerda (x menor)
        self.bx = r.left                          # tabela atrás da baliza
        px, py = jogador.pos_x, jogador.pos_y
        dx, dy = self.gx - px, self.cy - py
        self.distancia = max(40.0, math.hypot(dx, dy))
        dist_cam = max(self.distancia, 115.0)     # muito perto, a câmara recua um pouco (vê-se a baliza toda)
        self.fx, self.fy = dx / self.distancia, dy / self.distancia
        self.rx, self.ry = -self.fy, self.fx
        self.cx_mundo = self.gx - self.fx * dist_cam
        self.cy_mundo = self.cy - self.fy * dist_cam
        # Lado do ecrã para onde vai o +u (para as setas andarem para o lado certo)
        a, b = self._proj(self.gx, self.cy, 10), self._proj(self.gx, self.cy + 1, 10)
        self.sinal_u = 1 if (a and b and b[0] > a[0]) else -1

        self.u, self.h = 0.0, 12.0                # mira começa no meio, a meia altura baixa
        self.u_gr0 = max(-22.0, min(22.0, gr.pos_y - self.cy))
        self.u_gr = self.u_gr0
        self.a_carregar = False
        self.forca = 0.0
        self._sentido_forca = 1
        self.estado = "mirar"                     # mirar -> voo -> resultado
        self._rato_ant = pygame.mouse.get_pos()
        self._decisao = None
        self._voo_t = 0.0
        self._voo_dur = 0.4
        self._res_t = 0.0
        self._fundo = self._criar_fundo()
        self._cena = None             # parte fixa da imagem (a câmara não se mexe): feita no 1.º draw
        self._frente = None
        # Bola no stick: um pouco à frente e à direita dos olhos
        self.bola_ini = (self.cx_mundo + self.fx * 120 + self.rx * 34,
                         self.cy_mundo + self.fy * 120 + self.ry * 34, 0.0)

    # ------------------------------------------------------------------ #
    # Projeção                                                           #
    # ------------------------------------------------------------------ #
    def _cam(self, wx, wy):
        vx, vy = wx - self.cx_mundo, wy - self.cy_mundo
        return vx * self.rx + vy * self.ry, vx * self.fx + vy * self.fy       # (x, z)

    def _proj(self, wx, wy, h=0.0):
        x, z = self._cam(wx, wy)
        if z < PERTO:
            return None
        return CX + F * x / z, HORIZONTE + F * (OLHOS - h) / z, z

    def _proj_cam(self, x, z, h):
        return CX + F * x / z, HORIZONTE + F * (OLHOS - h) / z

    def _segmento(self, s, p1, p2, cor, largura_mundo=1.5, larg_min=1):
        """Linha entre dois pontos do mundo (x, y, h), cortada se passar para trás da câmara."""
        (x1, z1), (x2, z2) = self._cam(p1[0], p1[1]), self._cam(p2[0], p2[1])
        h1, h2 = p1[2], p2[2]
        if z1 < PERTO and z2 < PERTO:
            return
        if z1 < PERTO or z2 < PERTO:
            k = (PERTO - z1) / (z2 - z1)
            xm, hm = x1 + (x2 - x1) * k, h1 + (h2 - h1) * k
            if z1 < PERTO:
                x1, z1, h1 = xm, PERTO, hm
            else:
                x2, z2, h2 = xm, PERTO, hm
        a, b = self._proj_cam(x1, z1, h1), self._proj_cam(x2, z2, h2)
        larg = max(larg_min, round(F * largura_mundo / ((z1 + z2) / 2)))
        if larg <= 1:
            pygame.draw.aaline(s, cor, a, b)
        else:
            pygame.draw.line(s, cor, a, b, larg)

    def _poligono(self, pontos_mundo):
        """Corta um polígono (pontos x, y, h do mundo) pelo plano z = PERTO e projeta-o."""
        cam = [(*self._cam(x, y), h) for x, y, h in pontos_mundo]
        out = []
        n = len(cam)
        for i in range(n):
            a, b = cam[i], cam[(i + 1) % n]
            dentro_a, dentro_b = a[1] >= PERTO, b[1] >= PERTO
            if dentro_a:
                out.append(a)
            if dentro_a != dentro_b:
                k = (PERTO - a[1]) / (b[1] - a[1])
                out.append((a[0] + (b[0] - a[0]) * k, PERTO, a[2] + (b[2] - a[2]) * k))
        return [self._proj_cam(x, z, h) for x, z, h in out]

    def _mira_do_rato(self, sx, sy):
        """Converte a posição do rato no ponto (u, h) da baliza (inverso da projeção)."""
        x0, z0 = self._cam(self.gx, self.cy)
        x1, z1 = self._cam(self.gx, self.cy + 1)
        xu, zu = x1 - x0, z1 - z0
        dxs = sx - CX
        den = F * xu - dxs * zu
        if abs(den) < 1e-6:
            return
        u = (dxs * z0 - F * x0) / den
        z = z0 + u * zu
        h = OLHOS - (sy - HORIZONTE) * z / F
        self.u = max(-58.0, min(58.0, u))
        self.h = max(0.0, min(60.0, h))

    # ------------------------------------------------------------------ #
    # Eventos e lógica                                                   #
    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if self.estado != "mirar":
            # Depois do remate, qualquer tecla salta a animação do resultado
            if self.estado == "resultado" and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self._res_t = 99
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not self.a_carregar:
                self.terminado, self.resultado = True, None
            elif event.key in (pygame.K_x, pygame.K_SPACE, pygame.K_RETURN):
                self._comecar_carga()
        elif event.type == pygame.KEYUP and event.key in (pygame.K_x, pygame.K_SPACE, pygame.K_RETURN):
            if self.a_carregar:
                self._rematar()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._comecar_carga()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.a_carregar:
            self._rematar()
        elif event.type == pygame.MOUSEMOTION:
            self._mira_do_rato(*event.pos)

    def _comecar_carga(self):
        if not self.a_carregar:
            self.a_carregar = True
            self.forca = 0.0
            self._sentido_forca = 1

    def update(self, dt: float):
        self.t += dt
        if self.estado == "mirar":
            teclas = pygame.key.get_pressed()
            du = (teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - (teclas[pygame.K_LEFT] or teclas[pygame.K_a])
            dh = (teclas[pygame.K_UP] or teclas[pygame.K_w]) - (teclas[pygame.K_DOWN] or teclas[pygame.K_s])
            self.u = max(-58.0, min(58.0, self.u + du * self.sinal_u * 70 * dt))
            self.h = max(0.0, min(60.0, self.h + dh * 50 * dt))
            # O guarda-redes inclina-se um pouco para o lado para onde estás a apontar
            self.u_gr = self.u_gr0 + max(-12.0, min(12.0, self.u * 0.15))
            if self.a_carregar:
                # A barra sobe e desce: é preciso largar no momento certo
                self.forca += self._sentido_forca * dt / 0.9
                if self.forca >= 1.0:
                    self.forca, self._sentido_forca = 1.0, -1
                elif self.forca <= 0.0:
                    self.forca, self._sentido_forca = 0.0, 1
            if self.limite:
                self.tempo_restante -= dt
                if self.tempo_restante <= 0:
                    # Acabou o tempo: remata como estiver (fraco, se nem começou a carregar)
                    if not self.a_carregar:
                        self.forca = 0.3
                    self._rematar()
        elif self.estado == "voo":
            self._voo_t += dt
            k = min(1.0, self._voo_t / self._voo_dur)
            d = self._decisao
            # O guarda-redes só começa a mexer-se depois do tempo de reação
            reacao = GR_PERFIL.get(self.dificuldade, GR_PERFIL["normal"])[0]
            kr = max(0.0, min(1.0, (k * d["tempo"] - reacao) / max(0.05, d["tempo"] - reacao)))
            ini = d["u_gr_inicio"]
            self.u_gr = ini + (d["u_gr"] - ini) * (1 - (1 - kr) ** 2)
            if k >= 1.0:
                self.estado = "resultado"
                self._res_t = 0.0
                r = d["resultado"]
                if r == "defesa":
                    som.tocar("defesa", 0.9)
                    som.tocar("publico_uh", 0.7)
                elif r == "poste":
                    som.tocar("poste", 1.0)
                    som.tocar("publico_uh", 0.8)
                elif r == "fora":
                    som.tocar("tabela", 0.6)
        elif self.estado == "resultado":
            self._res_t += dt
            if self._res_t > 1.1:
                self.terminado = True
                self.resultado = self._decisao

    def _rematar(self):
        self.a_carregar = False
        precisao = 1.15 - getattr(self.jogador, "stat_remate", 80) / 400
        self._decisao = decidir_remate(self.u, self.h, self.forca, self.distancia, self.u_gr0,
                                       self.dificuldade, precisao=precisao)
        self._decisao["forca"] = self.forca
        # A animação dura mais do que o voo real, para se perceber o que aconteceu
        self._voo_dur = max(0.3, min(0.75, self._decisao["tempo"] * 1.7))
        self._voo_t = 0.0
        self.estado = "voo"
        som.tocar("remate", 0.6 + 0.4 * self.forca)

    # ------------------------------------------------------------------ #
    # Desenho                                                            #
    # ------------------------------------------------------------------ #
    def _criar_fundo(self):
        """Fundo: o público da bancada (do próprio pavilhão), ampliado e desfocado."""
        fundo = pygame.Surface((WIDTH, HEIGHT))
        arena = self.rink._surf
        topo = arena.subsurface((0, 0, WIDTH, 110)).copy()
        topo = pygame.transform.smoothscale(topo, (WIDTH // 3, 120))
        topo = pygame.transform.gaussian_blur(topo, 2)
        fundo.blit(pygame.transform.smoothscale(topo, (WIDTH, HORIZONTE + 40)), (0, 0))
        escuro = pygame.Surface((WIDTH, HORIZONTE + 40), pygame.SRCALPHA)
        for y in range(HORIZONTE + 40):
            pygame.draw.line(escuro, (6, 10, 24, int(150 - 90 * y / (HORIZONTE + 40))), (0, y), (WIDTH, y))
        fundo.blit(escuro, (0, 0))
        for x in (260, 640, 1020):                     # luzes do pavilhão
            l = luz(420, 240, (255, 240, 210), 70)
            fundo.blit(l, l.get_rect(center=(x, 40)), special_flags=pygame.BLEND_RGB_ADD)
        return fundo

    def _desenhar_campo(self, s):
        r = self.rink.rect
        # Piso de madeira
        piso = self._poligono([(r.left, r.top, 0), (r.right, r.top, 0), (r.right, r.bottom, 0), (r.left, r.bottom, 0)])
        if len(piso) >= 3:
            pygame.draw.polygon(s, (218, 170, 112), piso)
            # Mais escuro ao longe (perto do horizonte)
            sombra = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(HORIZONTE - 60, HORIZONTE + 160, 4):
                a = max(0, int(90 * (1 - (y - HORIZONTE + 60) / 220)))
                pygame.draw.rect(sombra, (60, 30, 10, a), (0, y, WIDTH, 4))
            mascara = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(mascara, (255, 255, 255, 255), piso)
            sombra.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(sombra, (0, 0))
        # Tábuas: linhas paralelas às tabelas laterais
        for y in range(r.top + 16, r.bottom, 16):
            self._segmento(s, (r.left, y, 0), (r.right, y, 0), (196, 150, 96), 0.4)
        # Linhas do campo: grande área, linha de golo e marcas de penálti
        a_y0, a_y1 = self.cy - 125, self.cy + 125
        gx, cor = self.gx, self.cor_linhas
        ax = gx + 150
        for p1, p2 in (((gx, a_y0), (ax, a_y0)), ((ax, a_y0), (ax, a_y1)), ((ax, a_y1), (gx, a_y1)),
                       ((gx, a_y0), (gx, a_y1))):
            self._segmento(s, (*p1, 0), (*p2, 0), cor, 2.0, 2)
        self._segmento(s, (gx, self.cy - MEIA_BOCA, 0), (gx, self.cy + MEIA_BOCA, 0), (220, 40, 40), 2.2, 2)
        for dx, rr in ((85, 2.5), (130, 2.0)):
            p = self._proj(gx + dx, self.cy)
            if p:
                pygame.draw.ellipse(s, cor, pygame.Rect(0, 0, max(2, F * rr * 2 / p[2]),
                                                         max(2, F * rr / p[2])).move(p[0] - F * rr / p[2], p[1] - F * rr / 2 / p[2]))

    def _desenhar_tabelas(self, s):
        r = self.rink.rect
        alt = 13
        # Tabela atrás da baliza e tabelas dos lados
        for quad in (
            [(self.bx, r.top, 0), (self.bx, r.bottom, 0), (self.bx, r.bottom, alt), (self.bx, r.top, alt)],
            [(self.bx, r.top, 0), (r.right, r.top, 0), (r.right, r.top, alt), (self.bx, r.top, alt)],
            [(self.bx, r.bottom, 0), (r.right, r.bottom, 0), (r.right, r.bottom, alt), (self.bx, r.bottom, alt)],
        ):
            pts = self._poligono(quad)
            if len(pts) >= 3:
                pygame.draw.polygon(s, (226, 230, 238), pts)
        # Corrimão na cor da equipa da casa
        for p1, p2 in (((self.bx, r.top), (self.bx, r.bottom)), ((self.bx, r.top), (r.right, r.top)),
                       ((self.bx, r.bottom), (r.right, r.bottom))):
            self._segmento(s, (*p1, alt), (*p2, alt), self.cor_linhas, 3.0, 3)
            self._segmento(s, (*p1, 0), (*p2, 0), (80, 86, 104), 1.0, 1)

    def _desenhar_baliza(self, s, frente: bool):
        """frente=False: rede (atrás do guarda-redes); frente=True: postes e barra (à frente)."""
        gx, cy, o = self.gx, self.cy, self.fora_dir
        H, M, P = ALTURA_BALIZA, MEIA_BOCA, PROF_BALIZA
        trasx = gx + o * P
        if not frente:
            rede = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            cor_rede = (235, 240, 250, 150)
            for k in range(0, 2 * M + 1, 6):                         # rede de trás: verticais
                y = cy - M + k
                self._segmento(rede, (trasx, y, 0), (trasx, y, H * 0.8), cor_rede, 0.35)
            for hh in range(0, int(H * 0.8) + 1, 6):                 # rede de trás: horizontais
                self._segmento(rede, (trasx, cy - M, hh), (trasx, cy + M, hh), cor_rede, 0.35)
            for lado in (-1, 1):                                     # redes dos lados
                for k in range(0, P + 1, 6):
                    x = gx + o * k
                    self._segmento(rede, (x, cy + lado * M, 0), (x, cy + lado * M, H - (H * 0.2) * k / P), cor_rede, 0.35)
            for k in range(0, 2 * M + 1, 6):                         # rede de cima
                y = cy - M + k
                self._segmento(rede, (gx, y, H), (trasx, y, H * 0.8), cor_rede, 0.35)
            s.blit(rede, (0, 0))
            for lado in (-1, 1):                                     # postes de trás
                self._segmento(s, (trasx, cy + lado * M, 0), (trasx, cy + lado * M, H * 0.8), (170, 40, 40), 1.6, 2)
            self._segmento(s, (trasx, cy - M, H * 0.8), (trasx, cy + M, H * 0.8), (170, 40, 40), 1.6, 2)
        else:
            for lado in (-1, 1):
                self._segmento(s, (gx, cy + lado * M, 0), (gx, cy + lado * M, H), (25, 10, 10), 3.4, 3)
                self._segmento(s, (gx, cy + lado * M, 0), (gx, cy + lado * M, H), (220, 45, 45), 2.6, 2)
                self._segmento(s, (gx, cy + lado * M, H), (trasx, cy + lado * M, H * 0.8), (220, 45, 45), 2.0, 2)
            self._segmento(s, (gx, cy - M, H), (gx, cy + M, H), (25, 10, 10), 3.4, 3)
            self._segmento(s, (gx, cy - M, H), (gx, cy + M, H), (220, 45, 45), 2.6, 2)

    def _desenhar_ondulacao(self, s):
        """A rede abana onde a bola entrou (só no golo)."""
        trasx = self.gx + self.fora_dir * PROF_BALIZA
        p = self._proj(trasx, self.cy + self._decisao["u"], self._decisao["h"])
        if not p:
            return
        for i in range(3):
            rr = F * (4 + 7 * i + 10 * self._res_t) / p[2]
            a = max(0, int(200 - 160 * self._res_t - 40 * i))
            if a <= 0 or rr < 1:
                continue
            camada = pygame.Surface((round(rr * 2) + 4, round(rr * 1.4) + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(camada, (255, 255, 255, a), camada.get_rect().inflate(-2, -2), 2)
            s.blit(camada, camada.get_rect(center=(p[0], p[1])))

    def _desenhar_gr(self, s):
        x = self.gx - self.fora_dir * 6                 # um pouco à frente da linha de golo
        p = self._proj(x, self.cy + self.u_gr, 0)
        if not p:
            return
        mergulho = self.u_gr - self.u_gr0
        if self.estado == "mirar":
            img = _img_gr("mover_baixo")
            ang, levanta = 0, 0
        else:
            img = _img_gr("defender_01" if int(self.t * 8) % 2 == 0 else "defender_02")
            # Inclina para o lado do mergulho; nos remates altos o corpo sobe
            lado_ecra = 1 if (mergulho * self.sinal_u) > 0 else -1
            ang = -lado_ecra * min(55, abs(mergulho) * 2.2)
            levanta = min(14, self._decisao["h"] * 0.35) * min(1.0, abs(mergulho) / 12)
            if lado_ecra < 0:
                img = pygame.transform.flip(img, True, False)
        alt = F * 62 / p[2]                              # 62 = altura da imagem no campo (o boneco ocupa ~70 %)
        img = pygame.transform.scale(img, (max(2, round(alt)), max(2, round(alt))))
        # O boneco não está ao centro da imagem: centramos pela parte visível
        caixa = img.get_bounding_rect()
        desvio = img.get_width() / 2 - caixa.centerx
        if ang:
            img = pygame.transform.rotate(img, ang)
        sombra = pygame.Surface((round(alt * 0.7), round(alt * 0.16)), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (20, 10, 0, 90), sombra.get_rect())
        s.blit(sombra, sombra.get_rect(center=(p[0], p[1])))
        # O centro do corpo fica a ~35 % da altura da imagem acima dos patins (também quando roda)
        centro = (p[0] + desvio, p[1] - alt * 0.36 - F * levanta / p[2])
        s.blit(img, img.get_rect(center=centro))

    def _pos_bola(self):
        """Posição da bola no mundo (x, y, h) durante a animação do remate."""
        d = self._decisao
        bx0, by0, bh0 = self.bola_ini
        gx, cy = self.gx, self.cy
        alvo = (gx, cy + d["u"], d["h"])
        k = min(1.0, self._voo_t / self._voo_dur) if self.estado == "voo" else 1.0
        if self.estado == "resultado":
            k2 = min(1.0, self._res_t / 0.5)
            r = d["resultado"]
            if r == "golo":
                return (gx + self.fora_dir * 30 * (1 - (1 - k2) ** 2), cy + d["u"], max(0, d["h"] - 15 * k2))
            if r == "defesa":
                lado = 1 if d["u"] >= d["u_gr"] else -1
                return (gx - self.fora_dir * 70 * k2, cy + d["u"] + lado * 40 * k2,
                        max(0.0, d["h"] + 20 * math.sin(math.pi * k2) - d["h"] * k2))
            if r == "poste":
                lado = 1 if d["u"] >= 0 else -1
                return (gx - self.fora_dir * 50 * k2, cy + d["u"] + lado * 50 * k2, max(0.0, d["h"] * (1 - k2)))
            return (gx + self.fora_dir * 60 * k2, cy + d["u"] * (1 + 0.3 * k2), d["h"])
        x = bx0 + (alvo[0] - bx0) * k
        y = by0 + (alvo[1] - by0) * k
        h = bh0 + (alvo[2] - bh0) * k + 6 * math.sin(math.pi * k) * (1 - d["forca"])
        return x, y, h

    def _desenhar_bola(self, s, pos):
        p = self._proj(*pos)
        if not p:
            return
        r = max(2, F * RAIO_BOLA / p[2])
        chao = self._proj(pos[0], pos[1], 0)
        if chao:
            sombra = pygame.Surface((round(r * 2.4), round(r * 0.9)), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (20, 10, 0, 100), sombra.get_rect())
            s.blit(sombra, sombra.get_rect(center=(chao[0], chao[1])))
        pygame.draw.circle(s, (20, 12, 6), (p[0], p[1] - r), r + max(1, r * 0.12))
        pygame.draw.circle(s, (255, 140, 30), (p[0], p[1] - r), r)
        pygame.draw.circle(s, (255, 205, 140), (p[0] - r * 0.35, p[1] - r * 1.35), r * 0.35)

    def _desenhar_stick(self, s):
        """O stick do jogador em primeira pessoa (puxa atrás ao carregar, vai à frente no remate)."""
        bola = self._proj(*self.bola_ini)
        if not bola:
            return
        bx, by = bola[0], bola[1]
        if self.estado == "mirar":
            ang = self.forca * 0.55 if self.a_carregar else 0.0
        else:
            ang = -0.5 * min(1.0, (self._voo_t if self.estado == "voo" else 1.0) / 0.12)
        base = (min(WIDTH + 40, bx + 300), HEIGHT + 60)
        lamina = (bx + 38 + math.sin(ang) * 260, by - 8 - (1 - math.cos(ang)) * 120)
        for cor, w in (((25, 15, 8), 26), ((200, 150, 90), 18), ((235, 195, 140), 6)):
            pygame.draw.line(s, cor, base, lamina, w)
        # Pá curva
        pts = [(lamina[0] + 14 * math.cos(a) - 26, lamina[1] + 18 * math.sin(a)) for a in
               [i * math.pi / 8 for i in range(0, 9)]]
        pygame.draw.lines(s, (25, 15, 8), False, pts, 20)
        pygame.draw.lines(s, (200, 150, 90), False, pts, 13)
        # Fita preta no punho
        fita = (base[0] + (lamina[0] - base[0]) * 0.12, base[1] + (lamina[1] - base[1]) * 0.12)
        pygame.draw.line(s, (20, 20, 25), base, fita, 22)

    def _desenhar_mira(self, s):
        p = self._proj(self.gx, self.cy + self.u, self.h)
        if not p:
            return
        precisao = 1.15 - getattr(self.jogador, "stat_remate", 80) / 400
        erro = erro_remate(self.forca, self.distancia, precisao)
        r = max(8, F * 2 * erro / p[2])
        pulso = 1 + 0.06 * math.sin(self.t * 8)
        cor = (255, 230, 80) if self.a_carregar else (255, 255, 255)
        lado = int(2 * (r * pulso + 18))
        c = lado / 2
        camada = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(camada, (*cor, 50), (c, c), r * pulso)
        pygame.draw.circle(camada, (*cor, 230), (c, c), r * pulso, 2)
        for a in range(4):
            ang = a * math.pi / 2 + self.t
            pygame.draw.line(camada, (*cor, 255), (c + math.cos(ang) * (r + 4), c + math.sin(ang) * (r + 4)),
                             (c + math.cos(ang) * (r + 14), c + math.sin(ang) * (r + 14)), 3)
        pygame.draw.circle(camada, (255, 60, 60, 255), (c, c), 4)
        s.blit(camada, (p[0] - c, p[1] - c))

    def _desenhar_interface(self, s):
        # Barra de força (à direita)
        barra = pygame.Rect(WIDTH - 90, 210, 36, 300)
        pygame.draw.rect(s, (10, 14, 28), barra.inflate(8, 8), border_radius=10)
        cheio = round(barra.height * self.forca)
        for i in range(cheio):
            k = i / barra.height
            cor = (int(60 + 195 * min(1, k * 1.6)), int(220 - 170 * max(0, k - 0.5) * 2), 60)
            pygame.draw.line(s, cor, (barra.left, barra.bottom - i), (barra.right - 1, barra.bottom - i))
        pygame.draw.rect(s, (220, 230, 250), barra, 2, border_radius=6)
        texto(s, "FORÇA", 14, (230, 236, 255), (barra.centerx, barra.bottom + 22))
        texto(s, f"{round(self.forca * 100)}%", 14, (255, 220, 80), (barra.centerx, barra.top - 18))
        # Informação em cima
        dist_m = self.distancia / PX_POR_METRO
        texto(s, f"REMATE  •  {self.jogador.nome}", 20, (255, 255, 255), (30, 30), ancora="midleft", sombra=True)
        texto(s, f"Distância à baliza: {dist_m:.1f} m", 14, (200, 215, 245), (30, 56), ancora="midleft",
              negrito=False)
        texto(s, f"Guarda-redes: {self.gr.nome}", 14, (200, 215, 245), (WIDTH - 30, 30), ancora="midright",
              negrito=False)
        # Tempo para rematar (num jogo a sério os adversários estão a chegar)
        if self.limite and self.estado == "mirar":
            k = max(0.0, self.tempo_restante / self.limite)
            ret = pygame.Rect(0, 0, 54, 54)
            ret.center = (WIDTH // 2, 44)
            pygame.draw.circle(s, (10, 14, 28), ret.center, 30)
            cor = (90, 220, 120) if k > 0.4 else (240, 80, 70)
            if k > 0:
                pygame.draw.arc(s, cor, ret, math.pi / 2, math.pi / 2 + 2 * math.pi * k, 6)
            texto(s, f"{math.ceil(self.tempo_restante)}", 18, (255, 255, 255), ret.center)
        if self.estado == "mirar":
            dica = ("Rato ou setas: apontar     Manter X ou o botão do rato: força (larga para rematar)"
                    "     ESC: cancelar")
            faixa = pygame.Surface((WIDTH, 34), pygame.SRCALPHA)
            faixa.fill((6, 10, 22, 190))
            s.blit(faixa, (0, HEIGHT - 34))
            texto(s, dica, 13, (220, 230, 250), (WIDTH // 2, HEIGHT - 17), negrito=False)

    def _desenhar_resultado(self, s):
        r = self._decisao["resultado"]
        txt, cor = {"golo": ("GOLO!", (255, 220, 60)), "defesa": ("DEFESA!", (120, 255, 160)),
                    "poste": ("POSTE!", (130, 200, 255)), "fora": ("FORA!", (255, 140, 120))}[r]
        t = self._res_t
        esc = (0.4 + 0.9 * t / 0.12) if t < 0.12 else 1.0 + 0.25 * math.exp(-(t - 0.12) * 10)
        img = titulo_estilizado(txt, pygame.font.SysFont("Arial Black", 100), tuple(min(255, c + 60) for c in cor),
                                cor, contorno=10)
        img = pygame.transform.rotozoom(img, -5, esc * 0.9)
        s.blit(img, img.get_rect(center=(WIDTH // 2, 190)))
        if r != "golo":
            vel_kmh = self._decisao["velocidade"] / PX_POR_METRO * 3.6
            texto(s, f"Remate a {vel_kmh:.0f} km/h", 16, (230, 236, 255), (WIDTH // 2, 262), sombra=True)

    def _preparar_cena(self):
        """Fundo, tabelas, campo e rede não mudam durante o remate: desenham-se uma vez."""
        self._cena = pygame.Surface((WIDTH, HEIGHT))
        self._cena.blit(self._fundo, (0, 0))
        self._desenhar_tabelas(self._cena)
        self._desenhar_campo(self._cena)
        self._desenhar_baliza(self._cena, frente=False)
        self._frente = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._desenhar_baliza(self._frente, frente=True)

    def draw(self):
        s = self.screen
        if self._cena is None:
            self._preparar_cena()
        s.blit(self._cena, (0, 0))
        if self.estado == "resultado" and self._decisao["resultado"] == "golo":
            self._desenhar_ondulacao(s)
        bola_atras = False
        pos_bola = None
        if self.estado != "mirar":
            pos_bola = self._pos_bola()
            # Atrás da linha de golo, a bola fica por trás do guarda-redes e dos postes
            bola_atras = (pos_bola[0] - self.gx) * self.fora_dir > 0
            if bola_atras:
                self._desenhar_bola(s, pos_bola)
        self._desenhar_gr(s)
        s.blit(self._frente, (0, 0))
        if self.estado == "mirar":
            self._desenhar_bola(s, self.bola_ini)
        elif not bola_atras:
            self._desenhar_bola(s, pos_bola)
        self._desenhar_stick(s)
        if self.estado == "mirar":
            self._desenhar_mira(s)
        self._desenhar_interface(s)
        if self.estado == "resultado":
            self._desenhar_resultado(s)
