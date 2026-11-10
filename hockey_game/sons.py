# -*- coding: utf-8 -*-
"""sons.py - efeitos sonoros do StickMania.

Os sons são criados por síntese (matemática), sem ficheiros de fora:
  • apito    - um tom de ~3 kHz com o "trinado" da bolinha do apito (modulação rápida);
  • tacadas  - um estalo curto (ruído) com duas frequências de madeira a desaparecer;
  • tabela   - uma pancada grave (frequência que desce) com um pouco de ruído;
  • poste    - som metálico: várias frequências que não são múltiplas umas das outras;
  • público  - ruído filtrado nas frequências da voz, com subidas e descidas lentas;
  • golo     - buzina (acorde com vibrato) e o público a festejar.

Na primeira vez os sons são gravados como .wav em assets/sounds (para não se repetir a
síntese em cada arranque). Se o computador não tiver placa de som, o jogo continua sem som.
"""
import math
import os
import random
import struct

import pygame

PASTA_SONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")
# Cânticos dos clubes: um ficheiro por clube (<id do clube>.mp3), feitos com IA (CellCog)
PASTA_CANTICOS = os.path.join(PASTA_SONS, "canticos")
TAXA = 22050          # amostras por segundo dos ficheiros .wav


# ====================================================================== #
# Síntese                                                                #
# ====================================================================== #

def _n(segundos: float) -> int:
    return int(segundos * TAXA)


def _envelope(i: int, n: int, ataque: float = 0.005, saida: float = 0.03) -> float:
    """Sobe nos primeiros 'ataque' segundos e desce nos últimos 'saida' segundos (evita estalos)."""
    a, s = max(1, _n(ataque)), max(1, _n(saida))
    if i < a:
        return i / a
    if i > n - s:
        return max(0.0, (n - i) / s)
    return 1.0


def _decai(t: float, tempo: float) -> float:
    """Decaimento exponencial (como uma corda ou uma pancada)."""
    return math.exp(-t / tempo)


class _Passabanda:
    """Filtro passa-banda (biquad, fórmulas do "Audio EQ Cookbook")."""

    def __init__(self, freq: float, q: float = 1.0):
        w = 2 * math.pi * freq / TAXA
        alfa = math.sin(w) / (2 * q)
        a0 = 1 + alfa
        self.b0, self.b2 = alfa / a0, -alfa / a0
        self.a1, self.a2 = -2 * math.cos(w) / a0, (1 - alfa) / a0
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def __call__(self, x: float) -> float:
        y = self.b0 * x + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y


def _passa_baixo(amostras, corte: float):
    """Filtro passa-baixo simples de 1.ª ordem."""
    k = 1 - math.exp(-2 * math.pi * corte / TAXA)
    y, saida = 0.0, []
    for x in amostras:
        y += k * (x - y)
        saida.append(y)
    return saida


def _normalizar(amostras, pico: float = 0.9):
    m = max(1e-9, max(abs(a) for a in amostras))
    return [a * pico / m for a in amostras]


def _misturar(*faixas):
    n = max(len(f) for f in faixas)
    return [sum(f[i] for f in faixas if i < len(f)) for i in range(n)]


def _silencio(segundos: float):
    return [0.0] * _n(segundos)


def sintetizar_apito(duracao: float, rnd: random.Random):
    n = _n(duracao)
    fase = 0.0
    sopro = _Passabanda(3200, 2.0)
    out = []
    for i in range(n):
        t = i / TAXA
        trinado = math.sin(2 * math.pi * 31 * t)          # a bolinha dentro do apito a girar
        f = 3050 + 110 * trinado
        fase += 2 * math.pi * f / TAXA
        amp = 0.62 + 0.38 * (0.5 + 0.5 * trinado)
        s = math.sin(fase) + 0.18 * math.sin(2 * fase) + 0.06 * math.sin(3 * fase)
        s = s * amp + 0.9 * sopro(rnd.uniform(-1, 1))
        out.append(s * _envelope(i, n, 0.015, 0.06))
    return _normalizar(out, 0.8)


def sintetizar_tacada(forte: bool, rnd: random.Random):
    dur = 0.16 if forte else 0.11
    n = _n(dur)
    f1, f2 = (720, 1850) if forte else (560, 1450)
    out = []
    for i in range(n):
        t = i / TAXA
        estalo = rnd.uniform(-1, 1) * _decai(t, 0.004)
        madeira = (0.9 * math.sin(2 * math.pi * f1 * t) * _decai(t, 0.035) +
                   0.5 * math.sin(2 * math.pi * f2 * t) * _decai(t, 0.012))
        out.append(estalo * 0.9 + madeira)
    return _normalizar(out, 0.9 if forte else 0.6)


def sintetizar_tabela(rnd: random.Random):
    n = _n(0.26)
    fase = 0.0
    ruido = _passa_baixo([rnd.uniform(-1, 1) for _ in range(n)], 900)
    out = []
    for i in range(n):
        t = i / TAXA
        f = 95 + 90 * _decai(t, 0.03)                       # a frequência desce (pancada)
        fase += 2 * math.pi * f / TAXA
        corpo = math.sin(fase) * _decai(t, 0.07)
        tabua = 0.35 * math.sin(2 * math.pi * 410 * t) * _decai(t, 0.025)
        out.append(corpo + tabua + 1.6 * ruido[i] * _decai(t, 0.015))
    return _normalizar(out, 0.85)


def sintetizar_poste(rnd: random.Random):
    n = _n(0.75)
    parciais = [(1, 1.0, 0.45), (2.32, 0.6, 0.25), (4.25, 0.4, 0.14), (6.8, 0.25, 0.08)]
    base = 1150
    out = []
    for i in range(n):
        t = i / TAXA
        s = sum(a * math.sin(2 * math.pi * base * k * t) * _decai(t, d) for k, a, d in parciais)
        s += rnd.uniform(-1, 1) * _decai(t, 0.003)
        out.append(s * _envelope(i, n, 0.0005, 0.05))
    return _normalizar(out, 0.7)


def sintetizar_defesa(rnd: random.Random):
    n = _n(0.16)
    ruido = _passa_baixo([rnd.uniform(-1, 1) for _ in range(n)], 600)
    out = []
    for i in range(n):
        t = i / TAXA
        out.append(1.8 * ruido[i] * _decai(t, 0.03) + 0.7 * math.sin(2 * math.pi * 130 * t) * _decai(t, 0.05))
    return _normalizar(out, 0.85)


def _multidao(duracao: float, rnd: random.Random, forma, brilho: float = 1.0):
    """
    Público: ruído filtrado em três bandas da voz humana (como muitas pessoas a falar ao mesmo
    tempo), com subidas e descidas lentas. 'forma(t)' dá a intensidade ao longo do tempo.
    """
    n = _n(duracao)
    bandas = [(_Passabanda(420, 0.9), 1.0), (_Passabanda(950, 1.1), 0.75 * brilho),
              (_Passabanda(2300, 1.4), 0.35 * brilho)]
    ondas = [(rnd.uniform(0.15, 0.6), rnd.uniform(0, 6.28), rnd.uniform(0.05, 0.15)) for _ in range(5)]
    out = []
    for i in range(n):
        t = i / TAXA
        x = rnd.uniform(-1, 1)
        s = sum(f(x) * g for f, g in bandas)
        vaga = 1.0 + sum(a * math.sin(2 * math.pi * fr * t + fa) for fr, fa, a in ondas)
        out.append(s * vaga * forma(t))
    return out


def sintetizar_publico(rnd: random.Random):
    """Ambiente do pavilhão (8 s), feito para tocar em ciclo sem se notar o corte."""
    dur, cruz = 8.0, 1.0
    total = _multidao(dur + cruz, rnd, lambda t: 1.0)
    n, nc = _n(dur), _n(cruz)
    # O fim é misturado com o início, para o ciclo não ter um "salto"
    out = total[:n]
    for i in range(nc):
        k = i / nc
        out[i] = out[i] * k + total[n + i] * (1 - k)
    return _normalizar(out, 0.55)


def sintetizar_uh(rnd: random.Random):
    """O «uhhh» do público quando a bola bate no poste ou o guarda-redes faz uma grande defesa."""
    dur = 1.6
    forma = lambda t: math.sin(math.pi * min(1.0, t / dur)) ** 1.5
    return _normalizar(_multidao(dur, rnd, forma, brilho=0.6), 0.75)


def sintetizar_golo(rnd: random.Random):
    """Buzina do pavilhão + o público a festejar."""
    dur = 4.2
    festa = _multidao(dur, rnd, lambda t: min(1.0, t / 0.25) * (1.0 if t < 1.8 else _decai(t - 1.8, 1.2)),
                      brilho=1.5)
    # Assobios de festa espalhados
    for _ in range(9):
        t0 = rnd.uniform(0.1, 2.2)
        f0 = rnd.uniform(1800, 2900)
        i0, d = _n(t0), _n(rnd.uniform(0.25, 0.6))
        fase = 0.0
        for i in range(d):
            if i0 + i >= len(festa):
                break
            fase += 2 * math.pi * (f0 + 500 * i / d) / TAXA
            festa[i0 + i] += 0.05 * math.sin(fase) * _envelope(i, d, 0.03, 0.08)
    festa = _normalizar(festa, 0.7)
    # Buzina: acorde maior com vibrato e várias harmónicas (som "rouco")
    nb = _n(1.5)
    buzina = []
    fases = [0.0, 0.0, 0.0]
    for i in range(nb):
        t = i / TAXA
        vib = 1 + 0.006 * math.sin(2 * math.pi * 5.5 * t)
        s = 0.0
        for k, f in enumerate((233.0, 293.7, 349.2)):
            fases[k] += 2 * math.pi * f * vib / TAXA
            s += sum(math.sin(h * fases[k]) / h for h in range(1, 7))
        buzina.append(s * _envelope(i, nb, 0.03, 0.25))
    buzina = _normalizar(buzina, 0.6)
    return _normalizar(_misturar(festa, buzina), 0.9)


def sintetizar_ui(tipo: str):
    if tipo == "mover":
        n = _n(0.035)
        return [0.35 * math.sin(2 * math.pi * 2200 * i / TAXA) * _decai(i / TAXA, 0.008) for i in range(n)]
    notas = (880, 1320) if tipo == "confirmar" else (1100, 740)
    out = []
    for f in notas:
        n = _n(0.06)
        out += [0.5 * math.sin(2 * math.pi * f * i / TAXA) * _envelope(i, n, 0.003, 0.03) for i in range(n)]
    return out


def _receitas():
    """Nome do ficheiro -> função que cria as amostras. A semente fixa dá sempre o mesmo som."""
    def r(seed):
        return random.Random(seed)
    return {
        "apito_curto": lambda: sintetizar_apito(0.32, r(1)),
        "apito_longo": lambda: sintetizar_apito(0.95, r(2)),
        "apito_final": lambda: (sintetizar_apito(0.28, r(3)) + _silencio(0.12) +
                                sintetizar_apito(0.28, r(4)) + _silencio(0.12) + sintetizar_apito(1.1, r(5))),
        "remate": lambda: sintetizar_tacada(True, r(6)),
        "passe": lambda: sintetizar_tacada(False, r(7)),
        "tabela": lambda: sintetizar_tabela(r(8)),
        "poste": lambda: sintetizar_poste(r(9)),
        "defesa": lambda: sintetizar_defesa(r(10)),
        "publico": lambda: sintetizar_publico(r(11)),
        "publico_uh": lambda: sintetizar_uh(r(12)),
        "golo": lambda: sintetizar_golo(r(13)),
        "ui_mover": lambda: sintetizar_ui("mover"),
        "ui_confirmar": lambda: sintetizar_ui("confirmar"),
        "ui_voltar": lambda: sintetizar_ui("voltar"),
    }


def gravar_wav(caminho: str, amostras):
    import wave          # só é preciso para criar os .wav (no browser já vêm feitos)
    with wave.open(caminho, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(TAXA)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, a)) * 32767)) for a in amostras))


def gerar_ficheiros(forcar: bool = False) -> list:
    """Cria os .wav que faltam (ou todos, se forcar=True). Devolve os nomes criados."""
    os.makedirs(PASTA_SONS, exist_ok=True)
    criados = []
    for nome, criar in _receitas().items():
        caminho = os.path.join(PASTA_SONS, nome + ".wav")
        if forcar or not os.path.exists(caminho):
            gravar_wav(caminho, criar())
            criados.append(nome)
    return criados


# ====================================================================== #
# Gestor de som                                                          #
# ====================================================================== #

class Sons:
    """
    Toca os efeitos. Se não houver placa de som (ou o pygame.mixer falhar),
    todos os métodos simplesmente não fazem nada - o jogo continua a funcionar.
    """

    # Intervalo mínimo entre dois sons iguais (evita "metralhadora" de pancadas na tabela)
    INTERVALO = {"tabela": 0.07, "defesa": 0.1, "poste": 0.15, "ui_mover": 0.03, "publico_uh": 2.5}

    def __init__(self):
        self.ativo = False
        self.vol_efeitos = 0.8
        self.vol_publico = 0.5
        self._sons = {}
        self._ultimo = {}
        self.gravacao = None        # lista onde se guardam os sons (só no anfitrião de um jogo online)
        self._canal_publico = None
        self._nivel_publico = 0.0      # 0 = desligado, 1 = jogo, valores intermédios nos menus
        # Cânticos dos clubes
        self._canal_cantico = None
        self._canticos = {}            # id do clube -> pygame.mixer.Sound (ou None se não houver ficheiro)
        self.equipas_jogo = ()         # (casa, fora) do jogo que está a decorrer
        self._espera_cantico = 0.0     # segundos até a bancada começar outro cântico
        self._fim_cantico = 0.0        # segundos até o cântico atual acabar (desce o volume devagar)
        self._golo_cantico = 0.0       # > 0 enquanto se canta o golo (mais alto)

    def iniciar(self):
        if self.ativo:
            return
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(2)                 # canal 0 para o público, 1 para os cânticos
            gerar_ficheiros()
            for nome in _receitas():
                self._sons[nome] = pygame.mixer.Sound(os.path.join(PASTA_SONS, nome + ".wav"))
            self._canal_publico = pygame.mixer.Channel(0)
            self._canal_cantico = pygame.mixer.Channel(1)
            self.ativo = True
        except (pygame.error, OSError):
            self.ativo = False

    # ------------------------------------------------------------------ #
    def tocar(self, nome: str, volume: float = 1.0, x: float | None = None):
        """Toca um efeito. 'x' (posição no ecrã) põe o som mais à esquerda ou à direita."""
        # Jogo online: o anfitrião guarda os sons do jogo para o convidado os tocar também
        if self.gravacao is not None and not nome.startswith("ui_"):
            self.gravacao.append([nome, round(volume, 2), None if x is None else round(x)])
            del self.gravacao[:-40]
        if not self.ativo or nome not in self._sons:
            return
        agora = pygame.time.get_ticks() / 1000
        if agora - self._ultimo.get(nome, -10) < self.INTERVALO.get(nome, 0.0):
            return
        self._ultimo[nome] = agora
        canal = self._sons[nome].play()
        if canal is None:
            return
        v = max(0.0, min(1.0, volume)) * self.vol_efeitos
        if x is None:
            canal.set_volume(v)
        else:
            from settings import WIDTH
            p = max(0.0, min(1.0, x / WIDTH))             # 0 = esquerda, 1 = direita
            canal.set_volume(v * min(1.0, 2 * (1 - p)) ** 0.5, v * min(1.0, 2 * p) ** 0.5)

    def ui(self, nome: str):
        self.tocar("ui_" + nome, 0.7)

    def publico(self, nivel: float):
        """Liga o barulho de fundo do pavilhão (nivel 0 = desligado)."""
        self._nivel_publico = nivel
        if not self.ativo:
            return
        if nivel <= 0:
            if self._canal_publico.get_busy():
                self._canal_publico.fadeout(600)
            return
        if not self._canal_publico.get_busy():
            self._canal_publico.play(self._sons["publico"], loops=-1, fade_ms=900)
        self._canal_publico.set_volume(nivel * self.vol_publico)

    def definir_volumes(self, efeitos: float, publico: float):
        self.vol_efeitos = max(0.0, min(1.0, efeitos))
        self.vol_publico = max(0.0, min(1.0, publico))
        if self.ativo and self._canal_publico.get_busy():
            self._canal_publico.set_volume(self._nivel_publico * self.vol_publico)
        if self.ativo and self._canal_cantico.get_busy():
            self._canal_cantico.set_volume(self._volume_cantico())

    # ------------------------------------------------------------------ #
    # Cânticos dos clubes                                                  #
    # ------------------------------------------------------------------ #
    # Durante o jogo, de vez em quando, a bancada canta o cântico de um dos clubes (mais vezes o
    # da casa). Quando há golo, ouve-se logo o cântico do clube que marcou, mais alto.
    # Os cânticos seguem o volume do público.
    VOL_CANTICO = 0.45             # cântico da bancada (por baixo do jogo)
    VOL_CANTICO_GOLO = 0.9         # cântico do golo
    DURACAO_CANTICO = 26.0         # segundos que a bancada canta de cada vez
    DURACAO_CANTICO_GOLO = 12.0

    def _cantico(self, equipa_id: str):
        """Carrega (uma só vez) o cântico de um clube. None se não houver ficheiro."""
        if equipa_id not in self._canticos:
            som_clube = None
            for ext in (".ogg", ".mp3", ".wav"):
                caminho = os.path.join(PASTA_CANTICOS, equipa_id + ext)
                if os.path.exists(caminho):
                    try:
                        som_clube = pygame.mixer.Sound(caminho)
                    except pygame.error:
                        som_clube = None
                    break
            self._canticos[equipa_id] = som_clube
        return self._canticos[equipa_id]

    def _volume_cantico(self) -> float:
        base = self.VOL_CANTICO_GOLO if self._golo_cantico > 0 else self.VOL_CANTICO
        return base * self.vol_publico

    def comecar_canticos(self, casa: str, fora: str):
        """Começo de um jogo: guarda as equipas e carrega já os dois cânticos (para o golo não ter atraso)."""
        self.equipas_jogo = (casa, fora)
        self._espera_cantico = random.uniform(5.0, 9.0)
        self._golo_cantico = self._fim_cantico = 0.0
        if self.ativo:
            self._canal_cantico.stop()
            for equipa_id in self.equipas_jogo:
                self._cantico(equipa_id)

    def parar_canticos(self):
        self.equipas_jogo = ()
        self._golo_cantico = 0.0
        if self.ativo and self._canal_cantico.get_busy():
            self._canal_cantico.fadeout(1200)

    def cantico_golo(self, equipa_id: str):
        """Golo: a bancada canta o cântico do clube que marcou."""
        if not self.ativo:
            return
        som_clube = self._cantico(equipa_id)
        if som_clube is None:
            return
        self._golo_cantico = self.DURACAO_CANTICO_GOLO
        self._canal_cantico.stop()
        self._canal_cantico.play(som_clube, fade_ms=1500)     # entra devagar, por baixo da buzina
        self._canal_cantico.set_volume(self._volume_cantico())
        self._espera_cantico = random.uniform(20.0, 35.0)

    def atualizar_canticos(self, dt: float, a_jogar: bool):
        """Chamado em cada frame. 'a_jogar' é False na pausa e no fim do jogo (o cântico vai-se calando)."""
        if not self.ativo or not self.equipas_jogo:
            return
        canal = self._canal_cantico
        if self._golo_cantico > 0:
            self._golo_cantico -= dt
            if self._golo_cantico <= 0:
                canal.fadeout(3000)
            return
        if not a_jogar:
            if canal.get_busy():
                canal.fadeout(1500)
            return
        if canal.get_busy():
            self._fim_cantico -= dt
            if self._fim_cantico <= 0:
                canal.fadeout(3500)
                self._fim_cantico = 99.0
            return
        self._espera_cantico -= dt
        if self._espera_cantico > 0:
            return
        casa, fora = self.equipas_jogo
        equipa_id = casa if random.random() < 0.6 else fora     # a casa tem mais adeptos
        som_clube = self._cantico(equipa_id) or self._cantico(casa if equipa_id == fora else fora)
        self._espera_cantico = random.uniform(15.0, 30.0)
        if som_clube is None:
            return
        canal.play(som_clube, fade_ms=2500)
        canal.set_volume(self._volume_cantico())
        self._fim_cantico = self.DURACAO_CANTICO


# Um só gestor para o jogo todo (os menus também o usam para os cliques)
som = Sons()
