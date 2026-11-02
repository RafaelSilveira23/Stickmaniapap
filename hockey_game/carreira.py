# -*- coding: utf-8 -*-
"""carreira.py - modo carreira: um campeonato entre as 8 equipas, guardado em SQLite.

Como funciona:
  - O jogador escolhe a sua equipa e a dificuldade.
  - Cria-se o calendário: todas as equipas jogam contra todas uma vez (7 jornadas, 4 jogos cada).
  - Em cada jornada o jogador joga o seu jogo; os outros 3 jogos são simulados.
  - Vitória = 3 pontos, empate = 1, derrota = 0.
  - Desempate na classificação: diferença de golos, depois golos marcados.

Tudo fica numa base de dados SQLite (saves/carreira.db), por isso dá para fechar o jogo
e continuar mais tarde. As tabelas seguem o modelo de dados do relatório:
  equipa, torneio, partida, classificacao
Todas as consultas usam parâmetros (?), nunca texto colado na SQL.
"""
import math
import os
import random
import sqlite3
from datetime import datetime

from team import EQUIPAS_LISTA, EQUIPAS_INFO

PASTA_SAVES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
CAMINHO_BD = os.path.join(PASTA_SAVES, "carreira.db")

PONTOS_VITORIA, PONTOS_EMPATE, PONTOS_DERROTA = 3, 1, 0

# Força de cada equipa (0-100), usada para simular os jogos que o jogador não joga
FORCA_EQUIPAS = {
    "fc_porto": 90,
    "benfica": 88,
    "sporting": 87,
    "oc_barcelos": 82,
    "ud_oliveirense": 79,
    "valongo": 74,
    "riba_dave": 71,
    "crp_lavra": 67,
}

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS equipa (
    id      TEXT PRIMARY KEY,
    nome    TEXT NOT NULL,
    sigla   TEXT NOT NULL,
    forca   INTEGER NOT NULL CHECK (forca BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS torneio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    equipa_jogador  TEXT NOT NULL REFERENCES equipa(id),
    dificuldade     TEXT NOT NULL,
    epoca           INTEGER NOT NULL DEFAULT 1,
    data_inicio     TEXT NOT NULL,
    estado          TEXT NOT NULL CHECK (estado IN ('em_curso', 'terminado', 'abandonado'))
);
CREATE TABLE IF NOT EXISTS partida (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    torneio_id  INTEGER NOT NULL REFERENCES torneio(id),
    jornada     INTEGER NOT NULL,
    casa_id     TEXT NOT NULL REFERENCES equipa(id),
    fora_id     TEXT NOT NULL REFERENCES equipa(id),
    golos_casa  INTEGER CHECK (golos_casa >= 0),
    golos_fora  INTEGER CHECK (golos_fora >= 0),
    jogada      INTEGER NOT NULL DEFAULT 0,      -- 0 = por jogar, 1 = já jogada
    do_jogador  INTEGER NOT NULL DEFAULT 0       -- 1 = jogo da equipa do jogador
);
CREATE TABLE IF NOT EXISTS classificacao (
    torneio_id      INTEGER NOT NULL REFERENCES torneio(id),
    equipa_id       TEXT NOT NULL REFERENCES equipa(id),
    jogos           INTEGER NOT NULL DEFAULT 0,
    vitorias        INTEGER NOT NULL DEFAULT 0,
    empates         INTEGER NOT NULL DEFAULT 0,
    derrotas        INTEGER NOT NULL DEFAULT 0,
    golos_marcados  INTEGER NOT NULL DEFAULT 0 CHECK (golos_marcados >= 0),
    golos_sofridos  INTEGER NOT NULL DEFAULT 0 CHECK (golos_sofridos >= 0),
    pontos          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (torneio_id, equipa_id)
);
"""


def gerar_calendario(equipas: list) -> list:
    """
    Calendário de "todos contra todos" pelo método do círculo:
    a primeira equipa fica fixa e as outras rodam uma posição em cada jornada.
    Com 8 equipas dá 7 jornadas de 4 jogos, e cada equipa joga uma vez contra cada uma das outras.
    As equipas vão alternando entre jogar em casa e fora.
    Devolve uma lista de jornadas; cada jornada é uma lista de (casa, fora).
    """
    eq = list(equipas)
    if len(eq) % 2:
        eq.append(None)                      # número ímpar: uma equipa folga em cada jornada
    n = len(eq)
    jogos_em_casa = {e: 0 for e in eq if e is not None}
    ultimo_em_casa = {e: None for e in eq if e is not None}
    jornadas = []
    for r in range(n - 1):
        jogos = []
        for i in range(n // 2):
            a, b = eq[i], eq[n - 1 - i]
            if a is None or b is None:
                continue
            # Quem joga em casa: quem tem menos jogos em casa; em caso de empate,
            # quem jogou fora na jornada anterior (para ir alternando)
            if jogos_em_casa[a] != jogos_em_casa[b]:
                a_em_casa = jogos_em_casa[a] < jogos_em_casa[b]
            else:
                a_em_casa = ultimo_em_casa[a] is not True
            casa, fora = (a, b) if a_em_casa else (b, a)
            jogos_em_casa[casa] += 1
            ultimo_em_casa[casa], ultimo_em_casa[fora] = True, False
            jogos.append((casa, fora))
        jornadas.append(jogos)
        eq = [eq[0]] + [eq[-1]] + eq[1:-1]   # rodar todas menos a primeira
    return jornadas


def _poisson(media: float, rnd: random.Random) -> int:
    """Número aleatório com distribuição de Poisson (bom modelo para o número de golos)."""
    limite = math.exp(-media)
    k, p = 0, 1.0
    while True:
        p *= rnd.random()
        if p <= limite:
            return k
        k += 1


def simular_jogo(casa: str, fora: str, rnd: random.Random = random) -> tuple[int, int]:
    """
    Resultado de um jogo que o jogador não joga.
    Cada equipa marca em média 3 golos, mais se for mais forte do que o adversário,
    e quem joga em casa tem uma pequena vantagem.
    """
    fc, ff = FORCA_EQUIPAS.get(casa, 75), FORCA_EQUIPAS.get(fora, 75)
    media_casa = 3.0 * (fc / ff) ** 2 + 0.3
    media_fora = 3.0 * (ff / fc) ** 2
    return _poisson(media_casa, rnd), _poisson(media_fora, rnd)


class Campeonato:
    """Um campeonato (torneio) guardado na base de dados."""

    def __init__(self, caminho_bd: str = CAMINHO_BD):
        self.caminho_bd = caminho_bd
        pasta = os.path.dirname(caminho_bd)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        self.con = sqlite3.connect(caminho_bd)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        with self.con:
            self.con.executescript(_ESQUEMA)
            # As equipas são sempre as mesmas: garantir que existem (INSERT OR IGNORE)
            self.con.executemany(
                "INSERT OR IGNORE INTO equipa (id, nome, sigla, forca) VALUES (?, ?, ?, ?)",
                [(e, EQUIPAS_INFO[e]["nome"], EQUIPAS_INFO[e]["sigla"], FORCA_EQUIPAS.get(e, 75))
                 for e in EQUIPAS_LISTA])
        self.torneio_id = None
        self._carregar_ativo()

    def fechar(self):
        self.con.close()

    # ------------------------------------------------------------------ #
    # Criar / carregar                                                     #
    # ------------------------------------------------------------------ #

    def _carregar_ativo(self):
        """Procura o último campeonato (em curso ou terminado e ainda não substituído)."""
        linha = self.con.execute(
            "SELECT id FROM torneio WHERE estado != 'abandonado' ORDER BY id DESC LIMIT 1").fetchone()
        self.torneio_id = linha["id"] if linha else None

    @property
    def existe(self) -> bool:
        return self.torneio_id is not None

    @property
    def info(self) -> sqlite3.Row:
        return self.con.execute("SELECT * FROM torneio WHERE id = ?", (self.torneio_id,)).fetchone()

    @property
    def equipa_jogador(self) -> str:
        return self.info["equipa_jogador"]

    @property
    def dificuldade(self) -> str:
        return self.info["dificuldade"]

    @property
    def terminado(self) -> bool:
        return self.existe and self.info["estado"] == "terminado"

    def novo(self, equipa_jogador: str, dificuldade: str = "normal", semente: int | None = None):
        """
        Cria um campeonato novo: torneio, calendário (todas as partidas) e classificação a zeros.
        Tudo numa só transação: ou fica tudo gravado, ou nada (se houver um erro, o anterior fica intacto).
        """
        if equipa_jogador not in EQUIPAS_LISTA:
            raise ValueError(f"equipa desconhecida: {equipa_jogador}")
        rnd = random.Random(semente)
        epoca = 1
        if self.existe:
            anterior = self.info
            if anterior["equipa_jogador"] == equipa_jogador and anterior["estado"] == "terminado":
                epoca = anterior["epoca"] + 1            # continua a carreira: época seguinte
        equipas = list(EQUIPAS_LISTA)
        rnd.shuffle(equipas)                              # calendário diferente em cada época
        jornadas = gerar_calendario(equipas)
        with self.con:
            if self.existe and not self.terminado:
                self.con.execute("UPDATE torneio SET estado = 'abandonado' WHERE id = ?", (self.torneio_id,))
            cur = self.con.execute(
                "INSERT INTO torneio (nome, equipa_jogador, dificuldade, epoca, data_inicio, estado) "
                "VALUES (?, ?, ?, ?, ?, 'em_curso')",
                (f"Campeonato Nacional {2026 + epoca - 1}/{2027 + epoca - 1}", equipa_jogador, dificuldade,
                 epoca, datetime.now().isoformat(timespec="seconds")))
            tid = cur.lastrowid
            for n, jogos in enumerate(jornadas, start=1):
                for casa, fora in jogos:
                    self.con.execute(
                        "INSERT INTO partida (torneio_id, jornada, casa_id, fora_id, do_jogador) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (tid, n, casa, fora, int(equipa_jogador in (casa, fora))))
            self.con.executemany(
                "INSERT INTO classificacao (torneio_id, equipa_id) VALUES (?, ?)",
                [(tid, e) for e in EQUIPAS_LISTA])
        self.torneio_id = tid

    # ------------------------------------------------------------------ #
    # Consultas                                                            #
    # ------------------------------------------------------------------ #

    @property
    def total_jornadas(self) -> int:
        return self.con.execute("SELECT MAX(jornada) FROM partida WHERE torneio_id = ?",
                                (self.torneio_id,)).fetchone()[0] or 0

    @property
    def jornada_atual(self) -> int:
        """Primeira jornada que ainda tem jogos por jogar (ou a última, se acabou)."""
        linha = self.con.execute(
            "SELECT MIN(jornada) FROM partida WHERE torneio_id = ? AND jogada = 0",
            (self.torneio_id,)).fetchone()
        return linha[0] if linha[0] is not None else self.total_jornadas

    def proximo_jogo(self) -> sqlite3.Row | None:
        """O próximo jogo da equipa do jogador (ou None se o campeonato acabou)."""
        return self.con.execute(
            "SELECT * FROM partida WHERE torneio_id = ? AND do_jogador = 1 AND jogada = 0 "
            "ORDER BY jornada LIMIT 1", (self.torneio_id,)).fetchone()

    def jogos_da_jornada(self, jornada: int) -> list:
        return self.con.execute(
            "SELECT * FROM partida WHERE torneio_id = ? AND jornada = ? ORDER BY do_jogador DESC, id",
            (self.torneio_id, jornada)).fetchall()

    def jogos_do_jogador(self) -> list:
        return self.con.execute(
            "SELECT * FROM partida WHERE torneio_id = ? AND do_jogador = 1 ORDER BY jornada",
            (self.torneio_id,)).fetchall()

    def ultima_jornada_jogada(self) -> int:
        linha = self.con.execute(
            "SELECT MAX(jornada) FROM partida WHERE torneio_id = ? AND jogada = 1",
            (self.torneio_id,)).fetchone()
        return linha[0] or 0

    def classificacao(self) -> list:
        """Tabela classificativa ordenada: pontos, diferença de golos, golos marcados, nome."""
        return self.con.execute(
            "SELECT c.*, e.nome, e.sigla, (c.golos_marcados - c.golos_sofridos) AS diferenca "
            "FROM classificacao c JOIN equipa e ON e.id = c.equipa_id "
            "WHERE c.torneio_id = ? "
            "ORDER BY c.pontos DESC, diferenca DESC, c.golos_marcados DESC, e.nome ASC",
            (self.torneio_id,)).fetchall()

    def posicao_do_jogador(self) -> int:
        for i, linha in enumerate(self.classificacao(), start=1):
            if linha["equipa_id"] == self.equipa_jogador:
                return i
        return 0

    # ------------------------------------------------------------------ #
    # Registar resultados                                                  #
    # ------------------------------------------------------------------ #

    def _registar(self, partida_id: int, casa: str, fora: str, gc: int, gf: int):
        """Grava o resultado de uma partida e atualiza a classificação das duas equipas."""
        if gc < 0 or gf < 0:
            raise ValueError("não pode haver golos negativos")
        self.con.execute(
            "UPDATE partida SET golos_casa = ?, golos_fora = ?, jogada = 1 WHERE id = ? AND jogada = 0",
            (gc, gf, partida_id))
        for eq, marcados, sofridos in ((casa, gc, gf), (fora, gf, gc)):
            v = int(marcados > sofridos)
            e = int(marcados == sofridos)
            d = int(marcados < sofridos)
            pts = v * PONTOS_VITORIA + e * PONTOS_EMPATE + d * PONTOS_DERROTA
            self.con.execute(
                "UPDATE classificacao SET jogos = jogos + 1, vitorias = vitorias + ?, empates = empates + ?, "
                "derrotas = derrotas + ?, golos_marcados = golos_marcados + ?, "
                "golos_sofridos = golos_sofridos + ?, pontos = pontos + ? "
                "WHERE torneio_id = ? AND equipa_id = ?",
                (v, e, d, marcados, sofridos, pts, self.torneio_id, eq))

    def registar_jogo_do_jogador(self, golos_jogador: int, golos_adversario: int,
                                 semente: int | None = None) -> int:
        """
        Grava o resultado do jogo que o jogador acabou de jogar e simula os outros jogos
        dessa jornada. Tudo numa transação. Devolve o número da jornada.
        """
        jogo = self.proximo_jogo()
        if jogo is None:
            raise RuntimeError("o campeonato já terminou")
        if jogo["casa_id"] == self.equipa_jogador:
            gc, gf = golos_jogador, golos_adversario
        else:
            gc, gf = golos_adversario, golos_jogador
        rnd = random.Random(semente)
        with self.con:
            self._registar(jogo["id"], jogo["casa_id"], jogo["fora_id"], gc, gf)
            for p in self.jogos_da_jornada(jogo["jornada"]):
                if not p["jogada"] and not p["do_jogador"]:
                    a, b = simular_jogo(p["casa_id"], p["fora_id"], rnd)
                    self._registar(p["id"], p["casa_id"], p["fora_id"], a, b)
            por_jogar = self.con.execute(
                "SELECT COUNT(*) FROM partida WHERE torneio_id = ? AND jogada = 0",
                (self.torneio_id,)).fetchone()[0]
            if por_jogar == 0:
                self.con.execute("UPDATE torneio SET estado = 'terminado' WHERE id = ?", (self.torneio_id,))
        return jogo["jornada"]
