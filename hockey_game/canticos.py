# -*- coding: utf-8 -*-
"""canticos.py - compõe por código um cântico original para cada clube.

Cada cântico (cerca de 25 s) é a bancada de um pavilhão a cantar pelo clube:
  • parte A  - a multidão canta uma melodia («ô-ô-ô») a várias vozes, com os instrumentos do clube;
  • parte B  - a multidão grita o nome do clube («BEN-FI-CA!») seguido de três palmas;
  • parte A outra vez, mais forte, e um grito final.

As vozes são feitas como a voz humana: uma onda «dente de serra» (as cordas vocais) passa por
três filtros que deixam passar só as frequências de cada vogal (os formantes: «a», «e», «i», «o», «u»).
Várias vozes ligeiramente desafinadas e desencontradas dão o efeito de multidão, e um eco (reverberação)
dá o som do pavilhão. Cada clube tem o seu ritmo, tom, melodia, bateria e instrumento.

Como criar os ficheiros (assets/sounds/canticos/<id>.wav):
    python canticos.py            -> cria os que faltam
    python canticos.py benfica    -> cria (ou refaz) só os clubes indicados
O jogo (sons.py) só lê os ficheiros; se não existirem, joga-se sem cânticos.
"""
import math
import os
import random
import sys

from sons import TAXA, PASTA_CANTICOS, _Passabanda, _multidao, _normalizar, gravar_wav

DOIS_PI = 2 * math.pi

# ====================================================================== #
# Os clubes                                                              #
# ====================================================================== #
# raiz     - nota da tónica (número MIDI: 50 = Ré, 52 = Mi, 53 = Fá, 55 = Sol)
# melodia  - (meio-tons acima da raiz, tempos) para 2 compassos de 4 tempos
# vogais   - vogal de cada nota da melodia (repete-se se for mais curta)
# grito    - sílabas do nome: (vogal, tempos)
# acordes  - um acorde por compasso: (meio-tons acima da raiz, "M" maior ou "m" menor)
# bateria  - estilo do ritmo; instrumento - o que toca com a bancada
CLUBES = {
    "fc_porto": dict(
        bpm=100, raiz=50, bateria="bombos", instrumento="metais", grave=48,
        melodia=[(7, 1), (7, .5), (8, .5), (7, 1), (5, 1), (3, 1.5), (2, .5), (0, 2)],
        vogais="oooooeoo", grito=[("o", .75), ("u", 1.25)],
        acordes=[(0, "m"), (8, "M"), (3, "M"), (10, "M")]),
    "benfica": dict(
        bpm=116, raiz=53, bateria="marcha", instrumento="metais", grave=55,
        melodia=[(0, .5), (4, .5), (7, 1), (7, .5), (9, .5), (7, 1), (4, 1), (5, .5), (4, .5), (2, 1), (0, 1)],
        vogais="eeoeeoaeeoo", grito=[("e", .5), ("i", .5), ("a", 1)],
        acordes=[(0, "M"), (5, "M"), (7, "M"), (0, "M")]),
    "sporting": dict(
        bpm=124, raiz=52, bateria="palmas", instrumento=None, grave=52,
        melodia=[(0, .5), (0, .5), (3, .5), (5, .5), (7, 1), (5, .5), (3, .5), (5, 1), (3, .5), (2, .5), (0, 2)],
        vogais="oooeoooeooo", grito=[("o", .75), ("i", 1.25)],
        acordes=[(0, "m"), (10, "M"), (8, "M"), (10, "M")]),
    "oc_barcelos": dict(
        bpm=128, raiz=55, bateria="folk", instrumento="concertina", grave=50,
        melodia=[(4, .5), (5, .5), (7, 1), (7, .5), (5, .5), (4, 1), (2, .5), (4, .5), (5, 1), (4, .5), (2, .5),
                 (0, 1)],
        vogais="aaoaaoaaoaao", grito=[("a", .5), ("e", .5), ("u", 1)],
        acordes=[(0, "M"), (7, "M"), (7, "M"), (0, "M")]),
    "ud_oliveirense": dict(
        bpm=132, raiz=52, bateria="rock", instrumento="guitarra", grave=50,
        melodia=[(0, 1), (0, .5), (3, .5), (5, 1), (7, 1), (5, .5), (3, .5), (0, 1.5), (-2, .5), (0, 1)],
        vogais="oeoooeooeo", grito=[("o", .25), ("i", .25), ("e", .25), ("e", .5), ("e", .75)],
        acordes=[(0, "m"), (3, "M"), (10, "M"), (0, "m")]),
    "valongo": dict(
        bpm=104, raiz=50, bateria="samba", instrumento=None, grave=46,
        melodia=[(7, .75), (7, .75), (9, .5), (7, 1), (4, .75), (4, .75), (5, .5), (4, 1), (2, 1), (0, 1)],
        vogais="eeeoeeeoao", grito=[("a", .5), ("o", .5), ("u", 1)],
        acordes=[(0, "M"), (9, "m"), (2, "m"), (7, "M")]),
    "riba_dave": dict(
        bpm=150, raiz=52, bateria="polka", instrumento="acordeao", grave=52,
        melodia=[(0, .5), (4, .5), (7, .5), (4, .5), (5, .5), (9, .5), (7, 1), (5, .5), (4, .5), (2, .5), (4, .5),
                 (0, 2)],
        vogais="eeeeaaoeeeeo", grito=[("i", .5), ("a", .5), ("a", .5), ("e", .5)],
        acordes=[(0, "M"), (5, "M"), (7, "M"), (0, "M")]),
    "crp_lavra": dict(
        bpm=84, raiz=50, bateria="maritimo", instrumento=None, grave=44, graves=True,
        melodia=[(0, 1.5), (3, .5), (5, 1), (7, 1), (8, 1.5), (7, .5), (5, 1), (3, 1)],
        vogais="oaoooaoo", grito=[("a", .75), ("a", 1.25)],
        acordes=[(0, "m"), (5, "m"), (10, "M"), (0, "m")]),
    # ── 2.ª divisão ──
    "hc_turquel": dict(
        bpm=112, raiz=50, bateria="folk", instrumento="concertina", grave=50,
        melodia=[(0, 1), (2, .5), (4, .5), (5, 1), (4, 1), (2, .5), (0, .5), (2, 1), (0, 2)],
        vogais="oeeoaeeoo", grito=[("u", .75), ("e", 1.25)],
        acordes=[(0, "M"), (5, "M"), (7, "M"), (0, "M")]),
    "paco_arcos": dict(
        bpm=122, raiz=53, bateria="marcha", instrumento="metais", grave=52,
        melodia=[(7, .5), (5, .5), (4, 1), (4, .5), (5, .5), (7, 1), (9, .5), (7, .5), (5, 1), (4, .5), (2, .5),
                 (0, 1)],
        vogais="eeoeeoaaoeeo", grito=[("a", .5), ("o", .5), ("a", .5), ("o", .5)],
        acordes=[(0, "M"), (9, "m"), (5, "M"), (7, "M")]),
    "cd_povoa": dict(
        bpm=118, raiz=55, bateria="palmas", instrumento=None, grave=52,
        melodia=[(0, .5), (3, .5), (7, 1), (5, .5), (3, .5), (2, 1), (3, .5), (5, .5), (7, 1), (0, 2)],
        vogais="oooeeoooao", grito=[("o", .5), ("o", .5), ("a", 1)],
        acordes=[(0, "m"), (8, "M"), (10, "M"), (0, "m")]),
    "ch_carvalhos": dict(
        bpm=130, raiz=52, bateria="rock", instrumento="guitarra", grave=48,
        melodia=[(0, .5), (0, .5), (0, .5), (3, .5), (5, 1), (3, 1), (0, .5), (0, .5), (-2, 1), (0, 2)],
        vogais="eeeoaoeeoo", grito=[("a", .5), ("a", .5), ("o", 1)],
        acordes=[(0, "m"), (10, "M"), (8, "M"), (10, "M")]),
    "aa_espinho": dict(
        bpm=96, raiz=50, bateria="maritimo", instrumento=None, grave=44, graves=True,
        melodia=[(7, 1.5), (5, .5), (3, 1), (2, 1), (3, 1.5), (5, .5), (0, 2)],
        vogais="ooaooao", grito=[("e", .5), ("i", .5), ("o", 1)],
        acordes=[(0, "m"), (3, "M"), (10, "M"), (0, "m")]),
    "sc_marinhense": dict(
        bpm=108, raiz=52, bateria="samba", instrumento=None, grave=46,
        melodia=[(4, .75), (4, .75), (5, .5), (7, 1), (9, .75), (7, .75), (5, .5), (4, 1), (2, 1), (0, 1)],
        vogais="eeeoaaeoeo", grito=[("a", .5), ("i", .5), ("e", .5), ("e", .5)],
        acordes=[(0, "M"), (5, "M"), (2, "m"), (7, "M")]),
    "ha_cambra": dict(
        bpm=140, raiz=55, bateria="polka", instrumento="acordeao", grave=52,
        melodia=[(7, .5), (4, .5), (7, .5), (4, .5), (5, .5), (2, .5), (5, 1), (4, .5), (2, .5), (0, .5), (2, .5),
                 (4, 2)],
        vogais="aeaeaeoeeeeo", grito=[("a", .75), ("a", 1.25)],
        acordes=[(0, "M"), (7, "M"), (7, "M"), (0, "M")]),
    # ── Clubes espanhóis (Taça Europeia) ──
    "fc_barcelona": dict(
        bpm=110, raiz=52, bateria="bombos", instrumento="metais", grave=46,
        melodia=[(0, 1), (4, 1), (7, 1.5), (9, .5), (7, 1), (5, .5), (4, .5), (2, 1), (0, 1)],
        vogais="ooooaoeoo", grito=[("a", .75), ("a", 1.25)],
        acordes=[(0, "M"), (5, "M"), (7, "M"), (0, "M")]),
    "liceo": dict(
        bpm=104, raiz=50, bateria="folk", instrumento="concertina", grave=48,
        melodia=[(0, .5), (2, .5), (3, .5), (5, .5), (7, 1), (5, .5), (3, .5), (2, .5), (3, .5), (2, .5), (0, .5),
                 (-2, 1), (0, 1)],
        vogais="eeeeoeeeeeeoo", grito=[("i", .5), ("e", .5), ("o", 1)],
        acordes=[(0, "m"), (10, "M"), (8, "M"), (10, "M")]),
    "reus": dict(
        bpm=126, raiz=53, bateria="palmas", instrumento=None, grave=50,
        melodia=[(0, .5), (0, .5), (7, 1), (5, .5), (3, .5), (5, 1), (0, .5), (0, .5), (3, 1), (2, .5), (0, 1.5)],
        vogais="eeoeeoeeoeo", grito=[("e", .5), ("u", 1.5)],
        acordes=[(0, "m"), (5, "m"), (10, "M"), (0, "m")]),
    "voltrega": dict(
        bpm=116, raiz=50, bateria="marcha", instrumento="metais", grave=50,
        melodia=[(0, .5), (0, .5), (4, .5), (7, .5), (12, 1), (9, 1), (7, .5), (5, .5), (4, 1), (2, 1), (0, 1)],
        vogais="eeeeoaeeoao", grito=[("o", .5), ("e", .5), ("a", 1)],
        acordes=[(0, "M"), (9, "m"), (5, "M"), (7, "M")]),
}

# Formantes das vogais: (frequência em Hz, volume)
FORMANTES = {
    "a": ((750, 1.0), (1150, 0.7), (2600, 0.25)),
    "e": ((420, 1.0), (1950, 0.45), (2600, 0.25)),
    "i": ((300, 1.0), (2250, 0.4), (3000, 0.2)),
    "o": ((470, 1.0), (800, 0.7), (2500, 0.15)),
    "u": ((330, 1.0), (700, 0.45), (2400, 0.1)),
}


def _n(segundos: float) -> int:
    return max(1, int(segundos * TAXA))


def _hz(nota: float) -> float:
    return 440.0 * 2 ** ((nota - 69) / 12)


def _env(i: int, n: int, a: int, s: int) -> float:
    if i < a:
        return i / a
    if i > n - s:
        return max(0.0, (n - i) / s)
    return 1.0


class _Faixa:
    """Uma pista de áudio onde se vão colando sons em instantes de tempo."""

    def __init__(self, segundos: float):
        self.a = [0.0] * _n(segundos)

    def por(self, amostras, t: float, ganho: float = 1.0):
        a = self.a
        i0 = int(t * TAXA)
        if i0 < 0:
            amostras, i0 = amostras[-i0:], 0
        for k in range(min(len(amostras), len(a) - i0)):
            a[i0 + k] += amostras[k] * ganho


# ====================================================================== #
# Vozes                                                                  #
# ====================================================================== #

def _voz(freq, dur, vogal, rnd, sopro=0.12, grito=False, ataque=0.04, saida=0.09):
    """Uma pessoa a cantar (ou a gritar) uma vogal."""
    n = _n(dur)
    (f1, g1), (f2, g2), (f3, g3) = [(_Passabanda(f * rnd.uniform(0.95, 1.05), max(3.0, f / 110)), g)
                                    for f, g in FORMANTES[vogal]]
    vr, vd, vf = rnd.uniform(4.5, 6.5), rnd.uniform(0.005, 0.014), rnd.uniform(0, DOIS_PI)
    a, s = _n(ataque), _n(min(saida, dur / 2))
    fase, out, ru, sen, ex = rnd.random(), [0.0] * n, rnd.uniform, math.sin, math.exp
    for i in range(n):
        t = i / TAXA
        f = freq * (1 + vd * sen(DOIS_PI * vr * t + vf))
        if grito:                                    # o grito começa mais agudo e vai descendo
            f *= 1 + 0.3 * ex(-t / 0.04) - 0.15 * t / dur
        fase += f / TAXA
        if fase >= 1:
            fase -= 1
        x = (2 * fase - 1) * (1 - sopro) + ru(-1, 1) * sopro
        out[i] = (f1(x) * g1 + f2(x) * g2 + f3(x) * g3) * _env(i, n, a, s)
    return out


def _coro(nota, dur, vogal, rnd, graves=False):
    """A multidão a cantar uma nota: várias vozes desafinadas e desencontradas."""
    vozes = [(0, 1.0)] * 4 + [(12, 0.45)] * 2 + ([(-12, 0.8)] * 2 if graves else [])
    folga = 0.04
    out = [0.0] * _n(dur + 0.2 + folga)
    for oitava, ganho in vozes:
        f = _hz(nota + oitava + rnd.uniform(-0.15, 0.15))           # até 15 cêntimos desafinado
        v = _normalizar(_voz(f, dur * 1.03 + 0.08, vogal, rnd), ganho)
        i0 = _n(rnd.uniform(0, folga))
        for k, x in enumerate(v):
            out[i0 + k] += x
    return out


def _grito(silabas, spb, rnd, vozes=9):
    """A multidão a gritar o nome do clube, sílaba a sílaba, com o som das consoantes."""
    total = sum(b for _, b in silabas) * spb + 0.6
    out = [0.0] * _n(total)
    for _ in range(vozes):
        f0 = rnd.uniform(150, 320)
        t = rnd.uniform(0, 0.03)
        for k, (vogal, tempos) in enumerate(silabas):
            ultima = k == len(silabas) - 1
            d = max(0.4, tempos * spb) if ultima else tempos * spb * 0.92
            f = f0 * (1.1 if k == 0 else (0.9 if ultima else 1.0))
            v = _voz(f, d, vogal, rnd, sopro=0.45, grito=True, ataque=0.012, saida=0.07 if not ultima else 0.15)
            v = _normalizar(v, rnd.uniform(0.7, 1.0))
            i0 = _n(t)
            # consoante: um sopro de ruído agudo no início da sílaba
            filtro = _Passabanda(rnd.uniform(2200, 3200), 1.0)
            for j in range(_n(0.02)):
                if i0 + j < len(out):
                    out[i0 + j] += 0.8 * filtro(rnd.uniform(-1, 1)) * math.exp(-j / TAXA / 0.008)
            for j, x in enumerate(v):
                if i0 + j < len(out):
                    out[i0 + j] += x
            t += tempos * spb
    return _normalizar(out, 0.9)


# ====================================================================== #
# Percussão                                                              #
# ====================================================================== #

def _ruido(n, rnd):
    return [rnd.uniform(-1, 1) for _ in range(n)]


def _bombo(rnd, grave=50.0, decai=0.28):
    n, fase, out = _n(decai * 3.5), 0.0, []
    for i in range(n):
        t = i / TAXA
        fase += DOIS_PI * (grave + grave * 1.6 * math.exp(-t / 0.025)) / TAXA
        out.append(math.sin(fase) * math.exp(-t / decai) + 0.35 * rnd.uniform(-1, 1) * math.exp(-t / 0.002))
    return _normalizar(out, 1.0)


def _caixa(rnd):
    n = _n(0.3)
    fb = _Passabanda(1900, 0.7)
    out = []
    for i in range(n):
        t = i / TAXA
        out.append(1.6 * fb(rnd.uniform(-1, 1)) * math.exp(-t / 0.1) +
                   0.6 * math.sin(DOIS_PI * 185 * t) * math.exp(-t / 0.05) +
                   0.3 * math.sin(DOIS_PI * 330 * t) * math.exp(-t / 0.03))
    return _normalizar(out, 0.9)


def _agudo(rnd, decai):
    """Ruído só com os agudos (pratos)."""
    n, lp, out = _n(decai * 4), 0.0, []
    k = 1 - math.exp(-DOIS_PI * 5000 / TAXA)
    for i in range(n):
        x = rnd.uniform(-1, 1)
        lp += k * (x - lp)
        out.append((x - lp) * math.exp(-i / TAXA / decai))
    return _normalizar(out, 0.8)


def _palmas(rnd, pessoas=12):
    """Muitas pessoas a bater palmas (cada palma são 3 estalos muito rápidos)."""
    out = [0.0] * _n(0.2)
    for _ in range(pessoas):
        fb = _Passabanda(rnd.uniform(900, 1500), 1.2)
        i0 = _n(rnd.uniform(0, 0.03))
        for r in range(3):
            j0 = i0 + _n(r * rnd.uniform(0.007, 0.011))
            for j in range(_n(0.06)):
                if j0 + j < len(out):
                    out[j0 + j] += fb(rnd.uniform(-1, 1)) * math.exp(-j / TAXA / (0.006 if r < 2 else 0.025))
    return _normalizar(out, 0.9)


def _apito_samba(rnd, dur=0.16):
    n, fase, out = _n(dur), 0.0, []
    for i in range(n):
        t = i / TAXA
        fase += DOIS_PI * (2900 + 120 * math.sin(DOIS_PI * 45 * t)) / TAXA
        out.append((math.sin(fase) + 0.4 * rnd.uniform(-1, 1)) * _env(i, n, _n(0.01), _n(0.03)))
    return _normalizar(out, 0.6)


# Padrões de bateria de um compasso: (tempo, instrumento, volume)
# B bombo, S caixa, H prato fechado, C palmas, T tambor, U surdo
BATERIAS = {
    "bombos": [(0, "B", 1), (1, "B", .8), (2, "B", 1), (3, "B", .8), (3.5, "B", .6)],
    "marcha": [(0, "B", 1), (2, "B", .9), (1, "S", .8), (3, "S", .8), (.5, "S", .25), (1.5, "S", .25),
               (2.5, "S", .25), (3.5, "S", .45), (3.75, "S", .55)],
    "palmas": [(0, "T", 1), (.75, "T", .7), (1.5, "T", .8), (2, "T", 1), (2.75, "T", .7), (3.5, "T", .8),
               (1, "C", .9), (3, "C", .9)],
    "folk": [(0, "B", 1), (1, "B", .7), (2, "B", 1), (3, "B", .7)] + [(k / 2, "S", .22) for k in range(8)],
    "rock": [(0, "B", 1), (1.5, "B", .8), (2, "B", 1), (1, "S", 1), (3, "S", 1)] +
            [(k / 2, "H", .35) for k in range(8)],
    "samba": [(1, "U", 1), (3, "U", 1), (0, "U", .45), (2, "U", .45)] +
             [(k / 4, "S", .4 if k % 4 in (0, 3) else .2) for k in range(16)],
    "polka": [(0, "B", 1), (2, "B", .9), (1, "S", .7), (3, "S", .7)],
    "maritimo": [(0, "B", 1), (2, "B", .8), (1, "C", .55), (3, "C", .55)],
}


# ====================================================================== #
# Instrumentos                                                           #
# ====================================================================== #

def _metal(freq, dur, rnd):
    """Metais (trompete/trombone): dente de serra que «abre» o som no ataque."""
    n, out = _n(dur), []
    fases = [rnd.random(), rnd.random()]
    det = (1.0, 1.004)
    lp1 = lp2 = 0.0
    a, s = _n(0.02), _n(0.06)
    for i in range(n):
        t = i / TAXA
        x = 0.0
        for k in (0, 1):
            fases[k] += freq * det[k] / TAXA
            fases[k] -= int(fases[k])
            x += 2 * fases[k] - 1
        corte = 500 + 2800 * min(1.0, t / 0.05) - 1000 * min(1.0, t / 0.4)
        c = 1 - math.exp(-DOIS_PI * corte / TAXA)
        lp1 += c * (x - lp1)
        lp2 += c * (lp1 - lp2)
        out.append(lp2 * _env(i, n, a, s))
    return _normalizar(out, 0.8)


def _palheta(freq, dur, rnd):
    """Concertina / acordeão: duas palhetas ligeiramente desafinadas (o som «a tremer»)."""
    n, out = _n(dur), []
    fases = [rnd.random(), rnd.random(), rnd.random()]
    mult = (1.0, 1.006, 2.0)
    vol = (1.0, 1.0, 0.35)
    lp = 0.0
    c = 1 - math.exp(-DOIS_PI * 2600 / TAXA)
    a, s = _n(0.015), _n(0.05)
    for i in range(n):
        x = 0.0
        for k in range(3):
            fases[k] += freq * mult[k] / TAXA
            fases[k] -= int(fases[k])
            x += vol[k] * (1.0 if fases[k] < 0.4 else -1.0)
        lp += c * (x - lp)
        out.append(lp * _env(i, n, a, s))
    return _normalizar(out, 0.8)


def _guitarra(freq, dur, rnd, abafada=True):
    """Guitarra elétrica distorcida: acorde de quinta (tónica, quinta e oitava)."""
    n, out = _n(dur), []
    mult = (1.0, 1.4983, 2.0, 1.003)
    fases = [rnd.random() for _ in mult]
    lp = 0.0
    c = 1 - math.exp(-DOIS_PI * 2800 / TAXA)
    a, s = _n(0.004), _n(0.03)
    for i in range(n):
        t = i / TAXA
        x = 0.0
        for k, m in enumerate(mult):
            fases[k] += freq * m / TAXA
            fases[k] -= int(fases[k])
            x += 2 * fases[k] - 1
        x = math.tanh(3.5 * x)
        lp += c * (x - lp)
        corpo = math.exp(-t / 0.09) if abafada else 0.6 + 0.4 * math.exp(-t / 0.3)
        out.append(lp * corpo * _env(i, n, a, s))
    return _normalizar(out, 0.8)


def _baixo(freq, dur, rnd):
    n, out = _n(dur), []
    a, s = _n(0.008), _n(0.05)
    for i in range(n):
        t = i / TAXA
        f = DOIS_PI * freq * t
        out.append((math.sin(f) + 0.35 * math.sin(2 * f) + 0.12 * math.sin(3 * f)) *
                   (0.5 + 0.5 * math.exp(-t / 0.35)) * _env(i, n, a, s))
    return _normalizar(out, 0.9)


INSTRUMENTOS = {"metais": _metal, "concertina": _palheta, "acordeao": _palheta, "guitarra": _guitarra}


# ====================================================================== #
# Reverberação (o eco do pavilhão)                                       #
# ====================================================================== #

def _reverb(x, mistura=0.3, realimentacao=0.83, amortecer=0.4):
    """Reverberação de Schroeder: 4 ecos em paralelo (filtros pente) e 2 «passa-tudo» em série."""
    n = len(x)
    molhado = [0.0] * n
    for d in (701, 773, 839, 913):
        buf, idx, lp = [0.0] * d, 0, 0.0
        for i in range(n):
            y = buf[idx]
            lp = y * (1 - amortecer) + lp * amortecer
            buf[idx] = x[i] + lp * realimentacao
            idx += 1
            if idx == d:
                idx = 0
            molhado[i] += y
    for d, g in ((225, 0.5), (341, 0.5)):
        buf, idx = [0.0] * d, 0
        for i in range(n):
            b = buf[idx]
            y = -g * molhado[i] + b
            buf[idx] = molhado[i] + g * y
            idx += 1
            if idx == d:
                idx = 0
            molhado[i] = y
    return [a * (1 - mistura) + w * mistura * 0.25 for a, w in zip(x, molhado)]


# ====================================================================== #
# Compor                                                                 #
# ====================================================================== #

def compor(cid: str):
    """Devolve as amostras do cântico do clube 'cid'."""
    c = CLUBES[cid]
    rnd = random.Random("cantico-" + cid)
    spb = 60.0 / c["bpm"]                  # segundos por tempo
    compasso = 4 * spb
    raiz = c["raiz"]
    total = 12 * compasso + 3.0
    voz, grito, perc, inst = (_Faixa(total) for _ in range(4))

    # --- sons usados muitas vezes (feitos uma só vez) --- #
    sons = {"B": _bombo(rnd, c["grave"]), "S": _caixa(rnd), "H": _agudo(rnd, 0.03), "C": _palmas(rnd),
            "T": _bombo(rnd, c["grave"] * 2.2, 0.16), "U": _bombo(rnd, c["grave"] * 0.9, 0.45)}
    prato = _agudo(rnd, 0.9)
    gritos = [_grito(c["grito"], spb, rnd) for _ in range(2)]
    cache = {}

    def nota_coro(nota, dur, vogal, variante):
        chave = (nota, dur, vogal, variante)
        if chave not in cache:
            cache[chave] = _coro(nota, dur, vogal, rnd, c.get("graves", False))
        return cache[chave]

    def nota_inst(func, nota, dur, **kw):
        chave = (func.__name__, nota, dur, tuple(kw.items()))
        if chave not in cache:
            cache[chave] = func(_hz(nota), dur, rnd, **kw)
        return cache[chave]

    def acorde(compasso_i):
        st, q = c["acordes"][compasso_i % 4]
        return raiz + st, (0, 4 if q == "M" else 3, 7)

    instrumento = INSTRUMENTOS.get(c["instrumento"])

    # --- Partes A: a bancada canta a melodia (compassos 0-3 e 8-11) --- #
    for inicio, forca in ((0, 0.85), (8, 1.0)):
        for rep in range(2):
            t0 = (inicio + rep * 2) * compasso
            b = 0.0
            for k, (st, tempos) in enumerate(c["melodia"]):
                vogal = c["vogais"][k % len(c["vogais"])]
                t = t0 + b * spb
                voz.por(nota_coro(raiz + st, tempos * spb, vogal, rep), t - 0.02, forca)
                if c["instrumento"] in ("metais", "concertina", "acordeao"):
                    inst.por(nota_inst(instrumento, raiz + st + 12, tempos * spb * 0.95), t, 0.5 * forca)
                b += tempos

    # --- Parte B: o nome do clube aos gritos e três palmas (compassos 4-7) --- #
    for ci in range(4, 8):
        t0 = ci * compasso
        grito.por(gritos[ci % 2], t0)
        if ci < 7:
            for bt in (2, 2.5, 3):
                perc.por(sons["C"], t0 + bt * spb, 1.0)
        else:
            grito.por(gritos[(ci + 1) % 2], t0 + 2 * spb, 1.1)
    # Grito final, depois da segunda parte A
    t_fim = 12 * compasso
    grito.por(gritos[0], t_fim, 1.15)
    perc.por(sons["B"], t_fim, 1.2)
    perc.por(prato, t_fim, 0.8)
    for ci in (0, 4, 8):
        perc.por(prato, ci * compasso, 0.6)

    # --- Bateria (todos os compassos) --- #
    padrao = BATERIAS[c["bateria"]]
    for ci in range(12):
        t0 = ci * compasso
        parte_b = 4 <= ci < 8
        for bt, qual, vol in padrao:
            if parte_b and qual == "C":
                continue                        # na parte B as palmas são as da bancada
            perc.por(sons[qual], t0 + bt * spb, vol * (0.8 if parte_b else 1.0))
        if c["bateria"] == "samba" and ci >= 4:
            for bt in (0, 1.5, 2.5):
                perc.por(_apito_samba(rnd), t0 + bt * spb, 0.35)

    # --- Acompanhamento: baixo e instrumento --- #
    for ci in range(12):
        t0 = ci * compasso
        fund, intervalos = acorde(ci)
        if c["bateria"] == "maritimo":
            inst.por(nota_inst(_baixo, fund - 24, compasso * 0.98), t0, 0.7)          # nota longa, como o mar
        elif c["bateria"] != "samba":
            for bt in (0, 2):
                inst.por(nota_inst(_baixo, fund - 24, 1.5 * spb), t0 + bt * spb, 0.6)
        if c["instrumento"] == "metais" and 4 <= ci < 8:
            for bt in (0, 2.5):
                for iv in intervalos:
                    inst.por(nota_inst(_metal, fund + iv, 0.35 * spb * 2), t0 + bt * spb, 0.3)
        elif c["instrumento"] in ("concertina", "acordeao"):
            for bt in (1, 3) if c["bpm"] < 140 else (0.5, 1.5, 2.5, 3.5):
                for iv in intervalos:
                    inst.por(nota_inst(_palheta, fund + iv, 0.4 * spb), t0 + bt * spb, 0.22)
        elif c["instrumento"] == "guitarra":
            if 8 <= ci < 12 and ci % 2 == 0:
                inst.por(nota_inst(_guitarra, fund - 12, compasso * 2 * 0.98, abafada=False), t0, 0.55)
            elif not 8 <= ci < 12:
                for k in range(8):
                    inst.por(nota_inst(_guitarra, fund - 12, 0.45 * spb), t0 + k * spb / 2, 0.4)

    # --- Mistura --- #
    publico = _normalizar(_multidao(total, rnd, lambda t: 0.8 + 0.2 * math.sin(t * 0.7)), 0.35)
    v, g, p, s = (_normalizar(f.a, 1.0) for f in (voz, grito, perc, inst))
    mistura = [0.95 * a + 0.85 * b + 0.7 * cc + 0.45 * d for a, b, cc, d in zip(v, g, p, s)]
    mistura = _reverb(mistura)
    mistura = [m + q for m, q in zip(mistura, publico)]
    n, nf = len(mistura), _n(1.5)
    for i in range(nf):                            # o fim desaparece devagar
        mistura[n - nf + i] *= 1 - i / nf
    return _normalizar(mistura, 0.92)


def gerar(ids=None, forcar=False) -> list:
    """Cria os ficheiros dos cânticos (os que faltam, ou os 'ids' indicados). Devolve os criados."""
    os.makedirs(PASTA_CANTICOS, exist_ok=True)
    criados = []
    for cid in ids or CLUBES:
        caminho = os.path.join(PASTA_CANTICOS, cid + ".wav")
        if forcar or ids or not os.path.exists(caminho):
            gravar_wav(caminho, compor(cid))
            criados.append(cid)
    return criados


if __name__ == "__main__":
    import time
    for cid in sys.argv[1:] or [c for c in CLUBES
                                 if not os.path.exists(os.path.join(PASTA_CANTICOS, c + ".wav"))]:
        t = time.time()
        gerar([cid])
        print(f"{cid}: {time.time() - t:.1f} s", flush=True)
