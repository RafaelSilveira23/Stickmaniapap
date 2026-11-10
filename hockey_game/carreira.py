# -*- coding: utf-8 -*-
"""carreira.py - modo carreira: uma época com duas divisões e a Taça Europeia, guardada em SQLite.

Como funciona:
  - O jogador escolhe um clube português (da 1.ª ou da 2.ª divisão) e a dificuldade.
  - Cada divisão tem o seu campeonato: todas as equipas jogam contra todas uma vez (7 jornadas;
    na 2.ª divisão, com 7 equipas, uma folga em cada jornada).
  - Taça Europeia: os 4 primeiros da 1.ª divisão da época anterior e 4 clubes espanhóis, por
    eliminatórias (quartos, meias e final, num só jogo; se empatar, decide-se nos penáltis).
    As eliminatórias são jogadas entre as jornadas da liga.
  - Em cada ronda o jogador joga o seu jogo (ou simula-o); os outros jogos são todos simulados.
  - Vitória = 3 pontos, empate = 1, derrota = 0. Desempate: diferença de golos, depois golos marcados.
  - No fim da época, o campeão da 2.ª divisão sobe e o último da 1.ª desce.

Tudo fica numa base de dados SQLite (saves/carreira.db), por isso dá para fechar o jogo
e continuar mais tarde. As tabelas seguem o modelo de dados do relatório:
  equipa, torneio, partida, classificacao, jogador e estatistica (golos de cada jogador em cada partida)
Todas as consultas usam parâmetros (?), nunca texto colado na SQL.
"""
import math
import os
import random
import sqlite3
import sys
from datetime import datetime

from team import (EQUIPAS_LISTA, EQUIPAS_INFO, EQUIPAS_PORTUGUESAS, EQUIPAS_1_DIVISAO, EQUIPAS_2_DIVISAO,
                  EQUIPAS_ESTRANGEIRAS, obter_plantel)

if getattr(sys, "frozen", False):
    # Programa instalado (StickMania.exe): os jogos gravados ficam em %APPDATA%\StickMania,
    # para não se perderem quando se instala uma versão nova
    PASTA_SAVES = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "StickMania")
else:
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
    # 2.ª divisão
    "hc_turquel": 66,
    "paco_arcos": 65,
    "cd_povoa": 64,
    "ch_carvalhos": 62,
    "aa_espinho": 61,
    "sc_marinhense": 60,
    "ha_cambra": 58,
    # Clubes espanhóis (Taça Europeia)
    "fc_barcelona": 92,
    "liceo": 86,
    "reus": 85,
    "voltrega": 80,
}

# Competições de uma época
LIGA1, LIGA2, EUROPA = "liga1", "liga2", "europa"
NOMES_COMPETICAO = {LIGA1: "1.ª Divisão", LIGA2: "2.ª Divisão", EUROPA: "Taça Europeia"}
FASES_EUROPA = {1: "Quartos de final", 2: "Meias-finais", 3: "Final"}
SIGLAS_FASE = {1: "QF", 2: "MF", 3: "F"}
# Ordem das rondas da época: as eliminatórias europeias são jogadas entre as jornadas da liga.
# O número da ronda é o que fica na coluna "jornada" das partidas (1 a 10).
ORDEM_RONDAS = [("liga", 1), ("liga", 2), (EUROPA, 1), ("liga", 3), ("liga", 4), (EUROPA, 2),
                ("liga", 5), ("liga", 6), (EUROPA, 3), ("liga", 7)]

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
    do_jogador  INTEGER NOT NULL DEFAULT 0,      -- 1 = jogo da equipa do jogador
    simulado    INTEGER NOT NULL DEFAULT 0,      -- 1 = resultado simulado (não jogado pelo jogador)
    competicao  TEXT NOT NULL DEFAULT 'liga1' CHECK (competicao IN ('liga1', 'liga2', 'europa')),
    fase        INTEGER,                         -- jornada da liga, ou 1/2/3 = quartos/meias/final
    pen_casa    INTEGER,                         -- penáltis (só nas eliminatórias que acabam empatadas)
    pen_fora    INTEGER
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
    competicao      TEXT NOT NULL DEFAULT 'liga1',   -- divisão da equipa nesta época
    PRIMARY KEY (torneio_id, equipa_id)
);
CREATE TABLE IF NOT EXISTS jogador (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    equipa_id   TEXT NOT NULL REFERENCES equipa(id),
    nome        TEXT NOT NULL,
    numero      INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 99),
    posicao     TEXT NOT NULL CHECK (posicao IN ('guarda_redes', 'avancado', 'medio', 'defesa')),
    UNIQUE (equipa_id, nome)
);
CREATE TABLE IF NOT EXISTS estatistica (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    partida_id  INTEGER NOT NULL REFERENCES partida(id),
    jogador_id  INTEGER NOT NULL REFERENCES jogador(id),
    golos       INTEGER NOT NULL DEFAULT 0 CHECK (golos >= 0),
    UNIQUE (partida_id, jogador_id)
);
"""

# Probabilidade de cada posição marcar um golo num jogo simulado (o avançado marca mais)
PESO_GOLO_POSICAO = {"avancado": 0.40, "medio": 0.23, "defesa": 0.14}


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


# Parâmetros do modelo de simulação (afinados com ferramentas/analise_simulacao.py)
GOLOS_BASE = 3.1         # golos esperados de cada equipa num jogo equilibrado
PESO_FORCA = 0.24        # quanto a diferença de força muda os golos esperados
VANTAGEM_CASA = 0.3      # golos a mais, em média, para quem joga em casa
FORMA_DO_DIA = 4.5       # variação da força de jogo para jogo (desvio padrão)
PROB_CONVERSAO = 0.5     # probabilidade de uma oportunidade dar golo
MAX_GOLOS = 11
# Ajuste à força da equipa do jogador quando ele simula o seu jogo (a dificuldade conta)
AJUSTE_DIFICULDADE = {"facil": 5, "normal": 0, "dificil": -5}


def _golos(media: float, rnd: random.Random) -> int:
    """
    Número de golos de uma equipa. Em vez de uma distribuição de Poisson (que dava resultados
    estranhos como 14-3), cada equipa tem um certo número de oportunidades e cada uma dá golo
    com probabilidade PROB_CONVERSAO (distribuição binomial). A média é a mesma, mas os
    resultados variam menos e seguem mais a força das equipas.
    """
    oportunidades = max(1, round(media / PROB_CONVERSAO))
    p = media / oportunidades
    return min(MAX_GOLOS, sum(rnd.random() < p for _ in range(oportunidades)))


def simular_jogo(casa: str, fora: str, rnd: random.Random = random,
                 ajuste_casa: float = 0.0, ajuste_fora: float = 0.0) -> tuple[int, int]:
    """
    Resultado de um jogo simulado.
      1. Cada equipa tem a sua força (0-100), mais um ajuste (forma recente, dificuldade)
         e mais a "forma do dia" (um valor aleatório: às vezes a equipa joga melhor, às vezes pior).
      2. Os golos esperados de cada equipa dependem da diferença de forças:
            golos_esperados = GOLOS_BASE x e^(PESO_FORCA x diferença / 10)
         (a equipa da casa tem ainda um pequeno bónus).
      3. Os golos são sorteados à volta desse valor (ver _golos).
    Assim o mais forte ganha quase sempre, mas há surpresas de vez em quando (cerca de 5 %).
    """
    fc = FORCA_EQUIPAS.get(casa, 75) + ajuste_casa + rnd.gauss(0, FORMA_DO_DIA)
    ff = FORCA_EQUIPAS.get(fora, 75) + ajuste_fora + rnd.gauss(0, FORMA_DO_DIA)
    d = (fc - ff) / 10
    media_casa = GOLOS_BASE * math.exp(PESO_FORCA * d) + VANTAGEM_CASA
    media_fora = GOLOS_BASE * math.exp(-PESO_FORCA * d)
    return _golos(media_casa, rnd), _golos(media_fora, rnd)


def _penaltis(casa: str, fora: str, rnd: random.Random) -> tuple[int, int]:
    """
    Desempate por penáltis: 5 para cada lado e, se continuar empatado, um a um até alguém falhar.
    Cada penálti entra com 60 % de probabilidade, um pouco mais para a equipa mais forte.
    """
    dif = (FORCA_EQUIPAS.get(casa, 75) - FORCA_EQUIPAS.get(fora, 75)) / 200
    pc, pf = 0.6 + dif, 0.6 - dif
    a = sum(rnd.random() < pc for _ in range(5))
    b = sum(rnd.random() < pf for _ in range(5))
    while a == b:
        a += rnd.random() < pc
        b += rnd.random() < pf
    return a, b


class Campeonato:
    """Uma época (torneio) guardada na base de dados: duas divisões e a Taça Europeia."""

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
            # Bases de dados de versões antigas não têm a coluna "simulado": acrescentá-la
            colunas = [c["name"] for c in self.con.execute("PRAGMA table_info(partida)")]
            if "simulado" not in colunas:
                self.con.execute("ALTER TABLE partida ADD COLUMN simulado INTEGER NOT NULL DEFAULT 0")
            # ... nem as colunas das divisões e da Taça Europeia (versão 30)
            for coluna, tipo in (("competicao", "TEXT NOT NULL DEFAULT 'liga1'"), ("fase", "INTEGER"),
                                 ("pen_casa", "INTEGER"), ("pen_fora", "INTEGER")):
                if coluna not in colunas:
                    self.con.execute(f"ALTER TABLE partida ADD COLUMN {coluna} {tipo}")
            if "competicao" not in [c["name"] for c in self.con.execute("PRAGMA table_info(classificacao)")]:
                self.con.execute("ALTER TABLE classificacao ADD COLUMN competicao TEXT NOT NULL DEFAULT 'liga1'")
            # As equipas são sempre as mesmas: garantir que existem (INSERT OR IGNORE)
            self.con.executemany(
                "INSERT OR IGNORE INTO equipa (id, nome, sigla, forca) VALUES (?, ?, ?, ?)",
                [(e, EQUIPAS_INFO[e]["nome"], EQUIPAS_INFO[e]["sigla"], FORCA_EQUIPAS.get(e, 75))
                 for e in EQUIPAS_LISTA])
            # Jogadores dos planteis (team.py). Se um nome já existe, só atualiza o número e a posição
            # ("upsert"): assim os golos de épocas antigas não se perdem.
            for e in EQUIPAS_LISTA:
                plantel = obter_plantel(e)
                linhas = [(e, plantel["guarda_redes"], 1, "guarda_redes")]
                linhas += [(e, nome, num, pos) for nome, pos, num in plantel["jogadores"]]
                self.con.executemany(
                    "INSERT INTO jogador (equipa_id, nome, numero, posicao) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT (equipa_id, nome) DO UPDATE SET numero = excluded.numero, "
                    "posicao = excluded.posicao", linhas)
        self.torneio_id = None
        # Trocas no plantel (carreira de jogador): {equipa_id: (nome que sai, (nome, posição, número))}
        self.substituicoes = {}
        self._carregar_ativo()

    def campo(self, equipa_id: str) -> list:
        """Jogadores de campo da equipa [(nome, posição, número)], já com as trocas do plantel."""
        jogadores = list(obter_plantel(equipa_id)["jogadores"])
        troca = self.substituicoes.get(equipa_id)
        if troca:
            sai, entra = troca
            jogadores = [entra if nome == sai else (nome, pos, num) for nome, pos, num in jogadores]
        return jogadores

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

    def novo(self, equipa_jogador: str, dificuldade: str = "normal", semente: int | None = None,
             continuar: bool | None = None):
        """
        Cria uma época nova: torneio, calendários das duas divisões, quartos de final da Taça Europeia
        e classificações a zeros. Tudo numa só transação: ou fica tudo gravado, ou nada.
        'continuar' = época seguinte da mesma carreira (com as subidas e descidas da anterior).
        Por omissão continua quando é o mesmo clube e a época anterior acabou.
        """
        if equipa_jogador not in EQUIPAS_PORTUGUESAS:
            raise ValueError(f"equipa desconhecida: {equipa_jogador}")
        rnd = random.Random(semente)
        anterior = self.info if self.existe else None
        acabou = anterior is not None and anterior["estado"] == "terminado"
        mesma = acabou and anterior["equipa_jogador"] == equipa_jogador
        epoca = anterior["epoca"] + 1 if mesma else 1     # continua a carreira: época seguinte
        if continuar is None:
            continuar = mesma
        if continuar and acabou:
            liga1, liga2, europa_pt = self._divisoes_seguintes(anterior["id"])
        else:
            liga1, liga2 = list(EQUIPAS_1_DIVISAO), list(EQUIPAS_2_DIVISAO)
            # Na primeira época vão à Europa os 4 clubes portugueses mais fortes
            europa_pt = sorted(liga1, key=lambda e: -FORCA_EQUIPAS.get(e, 75))[:4]
        calendarios = {}
        for comp, equipas in ((LIGA1, liga1), (LIGA2, liga2)):
            equipas = list(equipas)
            rnd.shuffle(equipas)                          # calendário diferente em cada época
            calendarios[comp] = gerar_calendario(equipas)
        # Sorteio dos quartos de final: cada clube português joga contra um espanhol (como nas taças
        # europeias, os clubes do mesmo país não se encontram na primeira eliminatória)
        portugueses, espanhois = list(europa_pt), list(EQUIPAS_ESTRANGEIRAS)
        rnd.shuffle(portugueses)
        rnd.shuffle(espanhois)
        quartos = [(a, b) if rnd.random() < 0.5 else (b, a) for a, b in zip(portugueses, espanhois)]
        ano = 2026 + epoca - 1
        with self.con:
            if self.existe and not self.terminado:
                self.con.execute("UPDATE torneio SET estado = 'abandonado' WHERE id = ?", (self.torneio_id,))
            cur = self.con.execute(
                "INSERT INTO torneio (nome, equipa_jogador, dificuldade, epoca, data_inicio, estado) "
                "VALUES (?, ?, ?, ?, ?, 'em_curso')",
                (f"Época {ano}/{ano + 1}", equipa_jogador, dificuldade, epoca,
                 datetime.now().isoformat(timespec="seconds")))
            tid = cur.lastrowid
            for ronda, (tipo, fase) in enumerate(ORDEM_RONDAS, start=1):
                if tipo == "liga":
                    jogos = [(comp, j) for comp in (LIGA1, LIGA2) if fase <= len(calendarios[comp])
                             for j in calendarios[comp][fase - 1]]
                elif fase == 1:
                    jogos = [(EUROPA, j) for j in quartos]
                else:
                    continue                              # meias e final: criadas quando se sabem as equipas
                for comp, (casa, fora) in jogos:
                    self.con.execute(
                        "INSERT INTO partida (torneio_id, jornada, casa_id, fora_id, do_jogador, competicao, fase) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (tid, ronda, casa, fora, int(equipa_jogador in (casa, fora)), comp, fase))
            self.con.executemany(
                "INSERT INTO classificacao (torneio_id, equipa_id, competicao) VALUES (?, ?, ?)",
                [(tid, e, LIGA1) for e in liga1] + [(tid, e, LIGA2) for e in liga2])
        self.torneio_id = tid

    def _divisoes_seguintes(self, torneio_id: int):
        """
        Divisões da época seguinte: o campeão da 2.ª sobe e o último da 1.ª desce.
        Os 4 primeiros da 1.ª divisão vão à Taça Europeia. Devolve (liga1, liga2, europa).
        """
        liga1 = [l["equipa_id"] for l in self.classificacao(LIGA1, torneio_id)]
        liga2 = [l["equipa_id"] for l in self.classificacao(LIGA2, torneio_id)]
        europa = liga1[:4]
        if not liga2:                                     # época de uma versão antiga (só uma divisão)
            return liga1, [e for e in EQUIPAS_2_DIVISAO if e not in liga1], europa
        desce, sobe = liga1[-1], liga2[0]
        return ([e for e in liga1 if e != desce] + [sobe], [e for e in liga2 if e != sobe] + [desce], europa)

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

    @property
    def liga_do_jogador(self) -> str:
        """Divisão da equipa do jogador nesta época (LIGA1 ou LIGA2)."""
        linha = self.con.execute("SELECT competicao FROM classificacao WHERE torneio_id = ? AND equipa_id = ?",
                                 (self.torneio_id, self.equipa_jogador)).fetchone()
        return linha["competicao"] if linha else LIGA1

    def competicao_da_ronda(self, ronda: int) -> str:
        """EUROPA se a ronda é de uma eliminatória europeia; senão, a divisão do jogador."""
        linha = self.con.execute("SELECT 1 FROM partida WHERE torneio_id = ? AND jornada = ? AND competicao = ?",
                                 (self.torneio_id, ronda, EUROPA)).fetchone()
        return EUROPA if linha else self.liga_do_jogador

    def jogos_da_jornada(self, jornada: int, competicao: str | None = None) -> list:
        """Jogos de uma ronda: os da Taça Europeia, ou os da divisão do jogador."""
        competicao = competicao or self.competicao_da_ronda(jornada)
        return self.con.execute(
            "SELECT * FROM partida WHERE torneio_id = ? AND jornada = ? AND competicao = ? "
            "ORDER BY do_jogador DESC, id", (self.torneio_id, jornada, competicao)).fetchall()

    def partida(self, partida_id: int) -> sqlite3.Row:
        return self.con.execute("SELECT * FROM partida WHERE id = ?", (partida_id,)).fetchone()

    def jogos_europa(self) -> list:
        """Todos os jogos da Taça Europeia desta época, por fase."""
        return self.con.execute("SELECT * FROM partida WHERE torneio_id = ? AND competicao = ? ORDER BY fase, id",
                                (self.torneio_id, EUROPA)).fetchall()

    def na_europa(self, equipa_id: str) -> bool:
        return self.con.execute("SELECT 1 FROM partida WHERE torneio_id = ? AND competicao = ? AND "
                                "(casa_id = ? OR fora_id = ?)",
                                (self.torneio_id, EUROPA, equipa_id, equipa_id)).fetchone() is not None

    @staticmethod
    def vencedor(p) -> str | None:
        """Quem passa numa eliminatória (com os penáltis, se houve empate)."""
        if not p["jogada"]:
            return None
        gc, gf = p["golos_casa"], p["golos_fora"]
        if gc == gf and p["pen_casa"] is not None:
            gc, gf = p["pen_casa"], p["pen_fora"]
        return p["casa_id"] if gc > gf else p["fora_id"]

    @staticmethod
    def nome_ronda(p) -> str:
        """«Jornada 3» ou «Taça Europeia • Meias-finais»."""
        if p["competicao"] == EUROPA:
            return f"Taça Europeia  •  {FASES_EUROPA.get(p['fase'], '')}"
        return f"Jornada {p['fase'] or p['jornada']}"

    @staticmethod
    def nome_ronda_curto(p) -> str:
        """«Jornada 3» ou «Europa • Meias» (para os sítios com pouco espaço)."""
        if p["competicao"] == EUROPA:
            return "Europa  •  " + {1: "Quartos", 2: "Meias", 3: "Final"}.get(p["fase"], "")
        return f"Jornada {p['fase'] or p['jornada']}"

    @staticmethod
    def sigla_ronda(p) -> str:
        if p["competicao"] == EUROPA:
            return SIGLAS_FASE.get(p["fase"], "E")
        return f"J{p['fase'] or p['jornada']}"

    def resumo_epoca(self) -> dict:
        """No fim da época: campeões, quem sobe e quem desce, e quem ganhou a Taça Europeia."""
        l1, l2 = self.classificacao(LIGA1), self.classificacao(LIGA2)
        final = self.con.execute("SELECT * FROM partida WHERE torneio_id = ? AND competicao = ? AND fase = 3",
                                 (self.torneio_id, EUROPA)).fetchone()
        return {"campeao1": l1[0]["equipa_id"] if l1 else None, "campeao2": l2[0]["equipa_id"] if l2 else None,
                "sobe": l2[0]["equipa_id"] if l2 else None, "desce": l1[-1]["equipa_id"] if l2 and l1 else None,
                "europa": self.vencedor(final) if final else None}

    def jogos_do_jogador(self) -> list:
        return self.con.execute(
            "SELECT * FROM partida WHERE torneio_id = ? AND do_jogador = 1 ORDER BY jornada",
            (self.torneio_id,)).fetchall()

    def ultima_jornada_jogada(self) -> int:
        linha = self.con.execute(
            "SELECT MAX(jornada) FROM partida WHERE torneio_id = ? AND jogada = 1",
            (self.torneio_id,)).fetchone()
        return linha[0] or 0

    def forma(self, equipa_id: str, n: int = 5) -> list:
        """Últimos n resultados da equipa, do mais antigo para o mais recente: 'V', 'E' ou 'D'."""
        linhas = self.con.execute(
            "SELECT casa_id, golos_casa, golos_fora FROM partida "
            "WHERE torneio_id = ? AND jogada = 1 AND (casa_id = ? OR fora_id = ?) "
            "ORDER BY jornada DESC LIMIT ?", (self.torneio_id, equipa_id, equipa_id, n)).fetchall()
        res = []
        for l in reversed(linhas):
            meus, deles = ((l["golos_casa"], l["golos_fora"]) if l["casa_id"] == equipa_id
                           else (l["golos_fora"], l["golos_casa"]))
            res.append("V" if meus > deles else ("E" if meus == deles else "D"))
        return res

    def _ajuste_forma(self, equipa_id: str) -> float:
        """Equipas em boa forma jogam um pouco melhor: +1,5 por vitória (e -1,5 por derrota) nos últimos 3 jogos."""
        return sum({"V": 1.5, "E": 0.0, "D": -1.5}[r] for r in self.forma(equipa_id, 3))

    def _simular(self, casa: str, fora: str, rnd: random.Random, ajuste_jogador: float = 0.0):
        aj_c = self._ajuste_forma(casa) + (ajuste_jogador if casa == self.equipa_jogador else 0)
        aj_f = self._ajuste_forma(fora) + (ajuste_jogador if fora == self.equipa_jogador else 0)
        return simular_jogo(casa, fora, rnd, aj_c, aj_f)

    def classificacao(self, competicao: str | None = None, torneio_id: int | None = None) -> list:
        """
        Tabela classificativa de uma divisão (por omissão, a do jogador), ordenada:
        pontos, diferença de golos, golos marcados, nome.
        """
        tid = torneio_id or self.torneio_id
        if competicao is None:
            competicao = self.liga_do_jogador
        return self.con.execute(
            "SELECT c.*, e.nome, e.sigla, (c.golos_marcados - c.golos_sofridos) AS diferenca "
            "FROM classificacao c JOIN equipa e ON e.id = c.equipa_id "
            "WHERE c.torneio_id = ? AND c.competicao = ? "
            "ORDER BY c.pontos DESC, diferenca DESC, c.golos_marcados DESC, e.nome ASC",
            (tid, competicao)).fetchall()

    def posicao_do_jogador(self) -> int:
        for i, linha in enumerate(self.classificacao(), start=1):
            if linha["equipa_id"] == self.equipa_jogador:
                return i
        return 0

    # ------------------------------------------------------------------ #
    # Registar resultados                                                  #
    # ------------------------------------------------------------------ #

    def _id_jogador(self, equipa_id: str, nome: str) -> int:
        linha = self.con.execute("SELECT id FROM jogador WHERE equipa_id = ? AND nome = ?",
                                 (equipa_id, nome)).fetchone()
        if linha:
            return linha["id"]
        # Nome que não está no plantel (não devia acontecer): acrescenta-o
        return self.con.execute(
            "INSERT INTO jogador (equipa_id, nome, numero, posicao) VALUES (?, ?, 99, 'medio')",
            (equipa_id, nome)).lastrowid

    def _gravar_marcadores(self, partida_id: int, equipa_id: str, golos: int, nomes, rnd: random.Random):
        """
        Grava quem marcou os golos de uma equipa numa partida.
        'nomes' são os marcadores conhecidos (no jogo jogado vêm do Game); os golos que faltam
        são sorteados entre os jogadores de campo, com mais hipóteses para o avançado.
        """
        nomes = [n for n in (nomes or []) if n][:golos]
        campo = self.campo(equipa_id)
        pesos = [PESO_GOLO_POSICAO.get(pos, 0.2) for _n, pos, _num in campo]
        while len(nomes) < golos:
            nomes.append(rnd.choices([n for n, _p, _num in campo], weights=pesos)[0])
        contagem = {}
        for n in nomes:
            contagem[n] = contagem.get(n, 0) + 1
        for nome, g in contagem.items():
            self.con.execute(
                "INSERT INTO estatistica (partida_id, jogador_id, golos) VALUES (?, ?, ?) "
                "ON CONFLICT (partida_id, jogador_id) DO UPDATE SET golos = golos + excluded.golos",
                (partida_id, self._id_jogador(equipa_id, nome), g))

    def melhores_marcadores(self, n: int = 10) -> list:
        """Melhores marcadores da divisão do jogador (soma dos golos de todos os jogos da liga)."""
        return self.con.execute(
            "SELECT j.nome, j.equipa_id, j.posicao, SUM(e.golos) AS golos "
            "FROM estatistica e JOIN jogador j ON j.id = e.jogador_id "
            "JOIN partida p ON p.id = e.partida_id "
            "WHERE p.torneio_id = ? AND p.competicao = ? AND e.golos > 0 "
            "GROUP BY j.id ORDER BY golos DESC, j.nome ASC LIMIT ?",
            (self.torneio_id, self.liga_do_jogador, n)).fetchall()

    def _registar(self, partida_id: int, casa: str, fora: str, gc: int, gf: int, simulado: bool = False,
                  marc_casa=None, marc_fora=None, rnd: random.Random | None = None):
        """Grava o resultado de uma partida, os marcadores e atualiza a classificação das duas equipas."""
        if gc < 0 or gf < 0:
            raise ValueError("não pode haver golos negativos")
        rnd = rnd or random.Random()
        comp = self.con.execute("SELECT competicao FROM partida WHERE id = ?", (partida_id,)).fetchone()[0]
        pen_c = pen_f = None
        if comp == EUROPA and gc == gf:
            pen_c, pen_f = _penaltis(casa, fora, rnd)     # eliminatória empatada: penáltis
        self.con.execute(
            "UPDATE partida SET golos_casa = ?, golos_fora = ?, jogada = 1, simulado = ?, pen_casa = ?, "
            "pen_fora = ? WHERE id = ? AND jogada = 0", (gc, gf, int(simulado), pen_c, pen_f, partida_id))
        self._gravar_marcadores(partida_id, casa, gc, marc_casa, rnd)
        self._gravar_marcadores(partida_id, fora, gf, marc_fora, rnd)
        if comp == EUROPA:
            return                                        # a Taça Europeia não tem classificação
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
                                 semente: int | None = None, simulado: bool = False,
                                 marcadores_eu=None, marcadores_adv=None) -> int:
        """
        Grava o resultado do jogo do jogador (jogado ou simulado) e simula os outros jogos dessa
        ronda (das duas divisões ou da Taça Europeia). Rondas anteriores sem jogos do jogador
        (por exemplo, uma eliminatória europeia em que ele não está) são simuladas antes.
        Se o jogador já não tem mais jogos, simula o resto da época. Tudo numa transação.
        Devolve o número da ronda.
        """
        jogo = self.proximo_jogo()
        if jogo is None:
            raise RuntimeError("o campeonato já terminou")
        if jogo["casa_id"] == self.equipa_jogador:
            gc, gf = golos_jogador, golos_adversario
            mc, mf = marcadores_eu, marcadores_adv
        else:
            gc, gf = golos_adversario, golos_jogador
            mc, mf = marcadores_adv, marcadores_eu
        rnd = random.Random(semente)
        ronda = jogo["jornada"]
        with self.con:
            for r in range(1, ronda):
                self._simular_ronda(r, rnd)
            # Os outros jogos são simulados ANTES de gravar o do jogador, para a "forma"
            # de todas as equipas ser a do início da ronda (igual para todos)
            outros = [(p, self._simular(p["casa_id"], p["fora_id"], rnd)) for p in self._por_jogar(ronda)
                      if not p["do_jogador"]]
            self._registar(jogo["id"], jogo["casa_id"], jogo["fora_id"], gc, gf, simulado, mc, mf, rnd)
            for p, (a, b) in outros:
                self._registar(p["id"], p["casa_id"], p["fora_id"], a, b, True, rnd=rnd)
            self._criar_fases_europa()
            if self.proximo_jogo() is None:
                # O jogador acabou a época (ou foi eliminado da Europa e já não tem jogos): simula o resto
                r = ronda + 1
                while r <= self.total_jornadas:
                    self._simular_ronda(r, rnd)
                    r += 1
            por_jogar = self.con.execute(
                "SELECT COUNT(*) FROM partida WHERE torneio_id = ? AND jogada = 0",
                (self.torneio_id,)).fetchone()[0]
            if por_jogar == 0:
                self.con.execute("UPDATE torneio SET estado = 'terminado' WHERE id = ?", (self.torneio_id,))
        return ronda

    def _por_jogar(self, ronda: int) -> list:
        return self.con.execute("SELECT * FROM partida WHERE torneio_id = ? AND jornada = ? AND jogada = 0 "
                                "ORDER BY id", (self.torneio_id, ronda)).fetchall()

    def _simular_ronda(self, ronda: int, rnd: random.Random):
        """Simula todos os jogos que faltam de uma ronda (só jogos sem o jogador)."""
        jogos = [p for p in self._por_jogar(ronda) if not p["do_jogador"]]
        if not jogos:
            return
        resultados = [(p, self._simular(p["casa_id"], p["fora_id"], rnd)) for p in jogos]
        for p, (a, b) in resultados:
            self._registar(p["id"], p["casa_id"], p["fora_id"], a, b, True, rnd=rnd)
        self._criar_fases_europa()

    def _criar_fases_europa(self):
        """Quando uma eliminatória europeia acaba, cria a seguinte com os vencedores (pela ordem do quadro)."""
        for fase in (1, 2):
            jogos = self.con.execute(
                "SELECT * FROM partida WHERE torneio_id = ? AND competicao = ? AND fase = ? ORDER BY id",
                (self.torneio_id, EUROPA, fase)).fetchall()
            if not jogos or any(not p["jogada"] for p in jogos):
                continue
            ja_existe = self.con.execute(
                "SELECT COUNT(*) FROM partida WHERE torneio_id = ? AND competicao = ? AND fase = ?",
                (self.torneio_id, EUROPA, fase + 1)).fetchone()[0]
            if ja_existe:
                continue
            vencedores = [self.vencedor(p) for p in jogos]
            ronda = ORDEM_RONDAS.index((EUROPA, fase + 1)) + 1
            eu = self.equipa_jogador
            for i in range(0, len(vencedores) - 1, 2):
                casa, fora = vencedores[i], vencedores[i + 1]
                self.con.execute(
                    "INSERT INTO partida (torneio_id, jornada, casa_id, fora_id, do_jogador, competicao, fase) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (self.torneio_id, ronda, casa, fora, int(eu in (casa, fora)), EUROPA, fase + 1))

    def simular_jogo_do_jogador(self, semente: int | None = None) -> tuple[int, int, int]:
        """
        Simula o próximo jogo do jogador (em vez de o jogar) e o resto da jornada.
        A dificuldade escolhida conta: no «Difícil» a equipa do jogador fica um pouco mais fraca.
        Devolve (jornada, golos do jogador, golos do adversário).
        """
        jogo = self.proximo_jogo()
        if jogo is None:
            raise RuntimeError("o campeonato já terminou")
        rnd = random.Random(semente)
        ajuste = AJUSTE_DIFICULDADE.get(self.dificuldade, 0)
        gc, gf = self._simular(jogo["casa_id"], jogo["fora_id"], rnd, ajuste)
        eu_em_casa = jogo["casa_id"] == self.equipa_jogador
        g_eu, g_adv = (gc, gf) if eu_em_casa else (gf, gc)
        jornada = self.registar_jogo_do_jogador(g_eu, g_adv, rnd.randrange(1 << 30), simulado=True)
        return jornada, g_eu, g_adv

    def simular_resto_da_epoca(self, semente: int | None = None) -> int:
        """Simula todas as jornadas que faltam. Devolve quantas jornadas foram simuladas."""
        rnd = random.Random(semente)
        n = 0
        while self.proximo_jogo() is not None:
            self.simular_jogo_do_jogador(rnd.randrange(1 << 30))
            n += 1
        return n

    def probabilidades_proximo_jogo(self, n: int = 600) -> tuple[float, float, float]:
        """
        Probabilidades de vitória, empate e derrota da equipa do jogador no próximo jogo,
        calculadas simulando o jogo n vezes com o mesmo modelo (método de Monte Carlo).
        """
        jogo = self.proximo_jogo()
        if jogo is None:
            return 0.0, 0.0, 0.0
        eu = self.equipa_jogador
        ajuste = AJUSTE_DIFICULDADE.get(self.dificuldade, 0)
        casa, fora = jogo["casa_id"], jogo["fora_id"]
        aj_c = self._ajuste_forma(casa) + (ajuste if casa == eu else 0)
        aj_f = self._ajuste_forma(fora) + (ajuste if fora == eu else 0)
        rnd = random.Random(jogo["id"])
        v = e = 0
        for _ in range(n):
            gc, gf = simular_jogo(casa, fora, rnd, aj_c, aj_f)
            meus, deles = (gc, gf) if casa == eu else (gf, gc)
            v += meus > deles
            e += meus == deles
        return v / n, e / n, (n - v - e) / n
