# -*- coding: utf-8 -*-
"""efeitos.py - estilo ARCADE: efeitos que dão "peso" e energia ao jogo.

  • tremer      - o ecrã treme num choque forte, num remate ao poste ou num golo
  • pausa       - o jogo congela uns milissegundos no impacto ("hit-stop"), como nos jogos de luta
  • câmara lenta- depois de um golo o jogo fica mais lento por um momento
  • partículas  - faíscas, pó das tabelas, anéis de impacto e confetes
  • rasto       - a bola deixa um rasto quando vai depressa
  • textos pop  - "DEFESA!", "POSTE!", "ROUBO!" em estilo banda desenhada
  • golo        - "GOLO!" gigante com uma explosão na cor da equipa

Tudo isto só mexe no DESENHO e no relógio do jogo: a física e a IA não mudam.
Liga-se e desliga-se nas Definições (engrenagem do menu principal); a escolha fica gravada.
"""
import math
import random

import pygame

from settings import WIDTH, HEIGHT
from graficos import titulo_estilizado, luz

COR_CONTORNO = (18, 14, 30)


def _fonte_bd(tamanho: int) -> pygame.font.Font:
    """Fonte grossa para os textos de banda desenhada."""
    return pygame.font.SysFont("Arial Black", tamanho)


_cache_fontes = {}


def fonte_bd(tamanho: int) -> pygame.font.Font:
    if tamanho not in _cache_fontes:
        _cache_fontes[tamanho] = _fonte_bd(tamanho)
    return _cache_fontes[tamanho]


def contornar(img: pygame.Surface, espessura: int = 2, cor=COR_CONTORNO) -> pygame.Surface:
    """
    Contorno grosso à volta de um sprite (estilo desenho animado).
    A "máscara" diz que píxeis são do boneco; desenha-se essa forma em escuro
    deslocada em 8 direções e o sprite por cima.
    """
    mascara = pygame.mask.from_surface(img, 200)            # ignora a sombra (semitransparente)
    silhueta = mascara.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0))
    w, h = img.get_size()
    e = espessura
    out = pygame.Surface((w + 2 * e, h + 2 * e), pygame.SRCALPHA)
    for dx, dy in ((-e, 0), (e, 0), (0, -e), (0, e), (-e, -e), (e, -e), (-e, e), (e, e)):
        out.blit(silhueta, (e + dx, e + dy))
    out.blit(img, (e, e))
    return out


def _estrela(cx, cy, r_ext, r_int, pontas, rot=0.0):
    pts = []
    for i in range(pontas * 2):
        a = rot + math.pi * i / pontas
        r = r_ext if i % 2 == 0 else r_int
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class Efeitos:
    def __init__(self):
        self.ativo = True
        self.reiniciar()

    def reiniciar(self):
        self._tremer = 0.0          # intensidade atual (px)
        self._tremer_t = 0.0
        self._pausa = 0.0           # segundos de "hit-stop" que faltam
        self._lento = 0.0           # segundos de câmara lenta que faltam
        self._lento_fator = 1.0
        self._flash = 0.0
        self.particulas = []
        self.textos = []
        self.grande = None
        self.rasto = []
        self.t = 0.0

    # ------------------------------------------------------------------ #
    # Tempo                                                              #
    # ------------------------------------------------------------------ #
    def tempo(self, dt: float) -> float:
        """Recebe o tempo real do frame e devolve o tempo que o jogo deve andar."""
        self.t += dt
        self._atualizar(dt)
        if not self.ativo:
            return dt
        if self._pausa > 0:
            self._pausa -= dt
            return 0.0
        if self._lento > 0:
            self._lento -= dt
            # Volta à velocidade normal aos poucos no último terço
            k = min(1.0, self._lento / 0.4)
            return dt * (self._lento_fator * k + (1 - k))
        return dt

    def tremer(self, forca: float, duracao: float = 0.25):
        if self.ativo and forca >= self._tremer:
            self._tremer, self._tremer_t = forca, duracao

    def pausa(self, duracao: float):
        if self.ativo:
            self._pausa = max(self._pausa, duracao)

    def camara_lenta(self, duracao: float, fator: float = 0.3):
        if self.ativo:
            self._lento, self._lento_fator = duracao, fator

    def flash(self, forca: float = 1.0):
        if self.ativo:
            self._flash = max(self._flash, forca)

    def deslocamento(self) -> tuple[int, int]:
        """Quanto o mundo está deslocado neste frame por causa do tremer."""
        if not self.ativo or self._tremer_t <= 0:
            return 0, 0
        a = self._tremer
        return round(random.uniform(-a, a)), round(random.uniform(-a, a) * 0.7)

    # ------------------------------------------------------------------ #
    # Partículas e textos                                                #
    # ------------------------------------------------------------------ #
    def _p(self, x, y, vx, vy, vida, cor, tam, tipo="ponto", gravidade=0.0):
        self.particulas.append([x, y, vx, vy, vida, vida, cor, tam, tipo, random.uniform(0, 6.28), gravidade])

    def faiscas(self, x, y, cor=(255, 230, 120), n=10, vel=260):
        if not self.ativo:
            return
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.4, 1.0) * vel
            self._p(x, y, math.cos(a) * v, math.sin(a) * v * 0.7, random.uniform(0.18, 0.35), cor,
                    random.uniform(2, 3.5), "risco")
        self._p(x, y, 0, 0, 0.25, cor, 10, "anel")

    def poeira(self, x, y, n=8):
        if not self.ativo:
            return
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(30, 110)
            self._p(x, y, math.cos(a) * v, math.sin(a) * v * 0.5 - 20, random.uniform(0.3, 0.6),
                    (235, 220, 190), random.uniform(3, 6), "fumo")

    def confetis(self, x, y, cores, n=70):
        if not self.ativo:
            return
        for _ in range(n):
            a = random.uniform(-math.pi, 0)
            v = random.uniform(150, 520)
            self._p(x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(1.0, 2.0),
                    random.choice(cores), random.uniform(4, 8), "confete", gravidade=520)

    def texto_pop(self, txt: str, x: float, y: float, cor=(255, 220, 60), tam: int = 30):
        if self.ativo:
            self.textos.append([txt, x, y, 0.0, 0.9, cor, tam, random.uniform(-10, 10)])

    def golo(self, nome_equipa: str, marcador: str | None, cor):
        if not self.ativo:
            return
        self.grande = {"t": 0.0, "dur": 2.0, "sub": marcador or nome_equipa, "equipa": nome_equipa,
                       "cor": cor}

    def bola(self, x: float, y: float, velocidade: float, livre: bool):
        """Guarda as últimas posições da bola (no ecrã) para o rasto."""
        if not self.ativo or not livre or velocidade < 260:
            if self.rasto:
                self.rasto.pop(0)
            return
        self.rasto.append((x, y, min(1.0, (velocidade - 260) / 400)))
        del self.rasto[:-9]

    def _atualizar(self, dt: float):
        if self._tremer_t > 0:
            self._tremer_t -= dt
            self._tremer *= 0.88
        self._flash = max(0.0, self._flash - dt * 3)
        vivas = []
        for p in self.particulas:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[10] * dt
            if p[8] in ("risco", "fumo"):
                p[2] *= 0.92
                p[3] *= 0.92
            p[9] += dt * 8
            vivas.append(p)
        self.particulas = vivas[-400:]
        for t in self.textos:
            t[3] += dt
        self.textos = [t for t in self.textos if t[3] < t[4]]
        if self.grande:
            self.grande["t"] += dt
            if self.grande["t"] > self.grande["dur"]:
                self.grande = None

    # ------------------------------------------------------------------ #
    # Desenho                                                            #
    # ------------------------------------------------------------------ #
    def desenhar_rasto(self, s):
        """Rasto da bola (desenhado antes da bola)."""
        n = len(self.rasto)
        for i, (x, y, k) in enumerate(self.rasto):
            f = (i + 1) / n
            r = max(1, round(5 * f))
            camada = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(camada, (255, 245, 210, int(170 * f * k)), (r + 1, r + 1), r)
            s.blit(camada, (x - r - 1, y - r - 1))

    def desenhar_mundo(self, s):
        """Partículas (ficam por baixo do marcador e dos menus)."""
        for x, y, _vx, _vy, vida, vmax, cor, tam, tipo, rot, _g in self.particulas:
            k = vida / vmax
            if tipo == "risco":
                comp = tam * 3 * k + 2
                a = math.atan2(_vy, _vx) if (_vx or _vy) else rot
                pygame.draw.line(s, cor, (x, y), (x - math.cos(a) * comp, y - math.sin(a) * comp),
                                 max(1, round(tam * k)))
            elif tipo == "anel":
                r = round(tam + (1 - k) * 26)
                camada = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(camada, (*cor, int(220 * k)), (r + 2, r + 2), r, 3)
                s.blit(camada, (x - r - 2, y - r - 2))
            elif tipo == "fumo":
                r = round(tam * (1.6 - k))
                camada = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(camada, (*cor, int(120 * k)), (r + 1, r + 1), r)
                s.blit(camada, (x - r - 1, y - r - 1))
            elif tipo == "confete":
                w = max(1, round(tam * abs(math.cos(rot))))
                pygame.draw.rect(s, cor, (round(x), round(y), w, round(tam * 1.5)))
            else:
                pygame.draw.circle(s, cor, (round(x), round(y)), max(1, round(tam * k)))

    def _texto_bd(self, txt, tam, cor):
        topo = tuple(min(255, c + 60) for c in cor)
        return titulo_estilizado(txt, fonte_bd(tam), topo, cor, cor_contorno=COR_CONTORNO, contorno=max(3, tam // 9))

    def desenhar_ui(self, s):
        """Textos pop, o "GOLO!" gigante e o clarão (por cima de tudo)."""
        for txt, x, y, t, dur, cor, tam, ang in self.textos:
            # Entra a crescer (passa um pouco do tamanho e volta), sobe e desaparece
            if t < 0.12:
                esc = 0.4 + 0.9 * (t / 0.12)
            else:
                esc = 1.0 + 0.3 * math.exp(-(t - 0.12) * 12)
            img = pygame.transform.rotozoom(self._texto_bd(txt, tam, cor), ang, esc * 0.8)
            alfa = 255 if t < dur * 0.6 else int(255 * (dur - t) / (dur * 0.4))
            img.set_alpha(max(0, alfa))
            s.blit(img, img.get_rect(center=(round(x), round(y - 40 * t))))

        if self.grande:
            self._desenhar_golo(s)

        if self._flash > 0:
            camada = pygame.Surface((WIDTH, HEIGHT))
            camada.fill((255, 255, 255))
            camada.set_alpha(int(150 * min(1.0, self._flash)))
            s.blit(camada, (0, 0))

    def _desenhar_golo(self, s):
        g = self.grande
        t, dur, cor = g["t"], g["dur"], g["cor"]
        cx, cy = WIDTH // 2, 300
        sai = max(0.0, (t - (dur - 0.35)) / 0.35)            # 0 → 1 no fim (sai a encolher)
        entra = min(1.0, t / 0.18)
        bounce = 1.0 + 0.35 * math.exp(-t * 7) * math.cos(t * 22)
        esc = entra * bounce * (1 - sai)
        if esc <= 0.02:
            return
        # Explosão em estrela na cor da equipa, a rodar
        raio = 190 * esc
        rot = t * 0.8
        brilho = luz(int(560 * esc) + 2, int(380 * esc) + 2, cor, 140)
        s.blit(brilho, brilho.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.polygon(s, COR_CONTORNO, _estrela(cx + 6, cy + 8, raio + 10, raio * 0.62 + 6, 14, rot))
        pygame.draw.polygon(s, cor, _estrela(cx, cy, raio, raio * 0.62, 14, rot))
        claro = tuple(min(255, c + 70) for c in cor)
        pygame.draw.polygon(s, claro, _estrela(cx, cy, raio * 0.72, raio * 0.45, 14, -rot * 1.3))
        # GOLO!
        img = pygame.transform.rotozoom(self._texto_bd("GOLO!", 120, (255, 220, 60)), -6, esc * 0.85)
        s.blit(img, img.get_rect(center=(cx, cy - 10)))
        # Fita com o nome de quem marcou
        if t > 0.25:
            k = min(1.0, (t - 0.25) / 0.2) * (1 - sai)
            f = fonte_bd(26)
            nome = f.render(g["sub"].upper(), True, (255, 255, 255))
            w = nome.get_width() + 60
            fita = pygame.Surface((w, 50), pygame.SRCALPHA)
            pygame.draw.polygon(fita, (*COR_CONTORNO, 255), [(10, 4), (w, 0), (w - 10, 50), (0, 46)])
            pygame.draw.polygon(fita, (*cor, 255), [(14, 8), (w - 6, 5), (w - 14, 44), (5, 42)])
            fita.blit(f.render(g["sub"].upper(), True, COR_CONTORNO), (32, 9))
            fita.blit(nome, (30, 6))
            fita = pygame.transform.rotozoom(fita, 3, k)
            s.blit(fita, fita.get_rect(center=(cx, cy + 120)))
