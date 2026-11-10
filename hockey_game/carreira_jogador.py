# -*- coding: utf-8 -*-
"""carreira_jogador.py - carreira de UM jogador (como o «Be a Pro» dos jogos de desporto).

Em vez de controlar a equipa toda, crias o teu jogador (nome, número, posição e clube) e nos
jogos só controlas esse jogador: os colegas são da IA (e passam-te a bola quando a pedes).

  • O campeonato é o mesmo do modo carreira (classe Campeonato), mas guardado noutra base de
    dados (saves/carreira_jogador.db), para não estragar o campeonato do modo carreira normal.
  • O teu jogador entra no plantel do clube, no lugar de um jogador da mesma posição: por isso
    também pode marcar nos jogos simulados e aparece na tabela dos melhores marcadores.
  • Em cada jogo tens uma NOTA (0 a 10) calculada com o que fizeste: golos, assistências,
    passes certos, bolas recuperadas, remates, bolas perdidas e o resultado.
  • A nota faz o jogador evoluir: o «geral» sobe (ou desce) e os atributos acompanham-no.
  • No fim da época, se a nota média for boa, há propostas de clubes mais fortes.
  • O jogador tem também uma VIDA (vida.py): forma, moral, confiança do treinador, fama, estudos e
    dinheiro, com eventos e escolhas em cada jornada que mexem no hóquei (atributos, lesões, banco).

Tabelas novas (além das do campeonato):
  atleta   - o jogador criado (um por carreira)
  atuacao  - o que o jogador fez em cada partida (golos, assistências, ..., nota)
"""
import math
import os
import random
from datetime import datetime

from carreira import Campeonato, PASTA_SAVES, FORCA_EQUIPAS, PESO_GOLO_POSICAO
from team import EQUIPAS_PORTUGUESAS, EQUIPAS_INFO

CAMINHO_BD_JOGADOR = os.path.join(PASTA_SAVES, "carreira_jogador.db")

POSICOES = ("avancado", "medio", "defesa")
NOME_POSICAO = {"avancado": "Avançado", "medio": "Médio", "defesa": "Defesa"}
GERAL_INICIAL = 64.0
GERAL_MIN, GERAL_MAX = 50.0, 95.0

# Cada posição tem os seus pontos fortes: atributo = geral + desvio
PERFIL_POSICAO = {
    "avancado": {"velocidade": 3, "remate": 7, "passe": -1, "defesa": -9},
    "medio":    {"velocidade": 0, "remate": -1, "passe": 7, "defesa": -2},
    "defesa":   {"velocidade": -2, "remate": -7, "passe": 1, "defesa": 9},
}
ATRIBUTOS = ("velocidade", "remate", "passe", "defesa")

# Nos jogos simulados: probabilidade de cada golo da equipa ser do jogador, e de ter a assistência
PROB_GOLO_SIMULADO = {"avancado": 0.38, "medio": 0.22, "defesa": 0.12}
PROB_ASSIST_SIMULADO = {"avancado": 0.20, "medio": 0.30, "defesa": 0.15}

_ESQUEMA_JOGADOR = """
CREATE TABLE IF NOT EXISTS atleta (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    numero      INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 99),
    posicao     TEXT NOT NULL CHECK (posicao IN ('avancado', 'medio', 'defesa')),
    equipa_id   TEXT NOT NULL REFERENCES equipa(id),
    geral       REAL NOT NULL CHECK (geral BETWEEN 0 AND 100),
    epoca       INTEGER NOT NULL DEFAULT 1,
    torneio_id  INTEGER REFERENCES torneio(id),
    data_inicio TEXT NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'ativo' CHECK (estado IN ('ativo', 'terminado'))
);
CREATE TABLE IF NOT EXISTS atuacao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    atleta_id     INTEGER NOT NULL REFERENCES atleta(id),
    partida_id    INTEGER NOT NULL REFERENCES partida(id),
    torneio_id    INTEGER NOT NULL REFERENCES torneio(id),
    equipa_id     TEXT NOT NULL REFERENCES equipa(id),
    golos         INTEGER NOT NULL DEFAULT 0 CHECK (golos >= 0),
    assistencias  INTEGER NOT NULL DEFAULT 0 CHECK (assistencias >= 0),
    remates       INTEGER NOT NULL DEFAULT 0 CHECK (remates >= 0),
    passes        INTEGER NOT NULL DEFAULT 0 CHECK (passes >= 0),
    recuperacoes  INTEGER NOT NULL DEFAULT 0 CHECK (recuperacoes >= 0),
    perdas        INTEGER NOT NULL DEFAULT 0 CHECK (perdas >= 0),
    nota          REAL NOT NULL CHECK (nota BETWEEN 0 AND 10),
    geral_depois  REAL NOT NULL,
    simulado      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (atleta_id, partida_id)
);
"""


def atributos(geral: float, posicao: str) -> dict:
    """Atributos (40-99) a partir do geral e da posição."""
    perfil = PERFIL_POSICAO.get(posicao, PERFIL_POSICAO["medio"])
    return {a: int(max(40, min(99, round(geral + perfil[a])))) for a in ATRIBUTOS}


def calcular_nota(est: dict, golos_equipa: int, golos_adversario: int) -> float:
    """
    Nota do jogo (0 a 10). Começa em 5,8 (jogo sem nada de especial) e:
      + 1,0 por golo, + 0,6 por assistência, + 0,2 por bola recuperada,
      + 0,05 por passe certo (até 12), + 0,08 por remate (até 6), − 0,15 por bola perdida,
      + 0,5 se a equipa ganhou, − 0,5 se perdeu.
    """
    nota = 5.8
    nota += 1.0 * est.get("golos", 0) + 0.6 * est.get("assistencias", 0)
    nota += 0.2 * est.get("recuperacoes", 0) + 0.05 * min(12, est.get("passes", 0))
    nota += 0.08 * min(6, est.get("remates", 0)) - 0.15 * est.get("perdas", 0)
    if golos_equipa > golos_adversario:
        nota += 0.5
    elif golos_equipa < golos_adversario:
        nota -= 0.5
    return round(max(3.0, min(10.0, nota)), 1)


def evolucao(nota: float) -> float:
    """Quanto o geral muda depois de um jogo: nota 6,5 = +0,25; nota 8 = +0,9; nota 5 = −0,4."""
    return 0.25 + (nota - 6.5) * 0.45


class CarreiraJogador:
    """A carreira de um jogador, guardada em SQLite (com o campeonato do clube onde joga)."""

    def __init__(self, caminho_bd: str = CAMINHO_BD_JOGADOR):
        self.camp = Campeonato(caminho_bd)
        self.con = self.camp.con
        with self.con:
            self.con.executescript(_ESQUEMA_JOGADOR)
        from vida import Vida
        self.vida = Vida(self)
        self.vida.garantir()
        self._aplicar_no_plantel()

    def fechar(self):
        self.camp.fechar()

    # ------------------------------------------------------------------ #
    # O jogador                                                          #
    # ------------------------------------------------------------------ #

    @property
    def atleta(self):
        return self.con.execute("SELECT * FROM atleta WHERE estado = 'ativo' ORDER BY id DESC LIMIT 1").fetchone()

    @property
    def existe(self) -> bool:
        return self.atleta is not None and self.camp.existe

    def atributos(self) -> dict:
        a = self.atleta
        return atributos(a["geral"], a["posicao"])

    def jogador_substituido(self, equipa_id: str, posicao: str) -> str | None:
        """Nome do jogador do plantel que dá o lugar ao teu (o primeiro da mesma posição)."""
        from team import obter_plantel
        for nome, pos, _num in obter_plantel(equipa_id)["jogadores"]:
            if pos == posicao:
                return nome
        return None

    def _aplicar_no_plantel(self):
        """Põe o jogador no plantel do clube (no lugar de um da mesma posição) e na tabela jogador."""
        a = self.atleta
        self.camp.substituicoes = {}
        if a is None:
            return
        sai = self.jogador_substituido(a["equipa_id"], a["posicao"])
        if sai:
            self.camp.substituicoes[a["equipa_id"]] = (sai, (a["nome"], a["posicao"], a["numero"]))
        with self.con:
            self.con.execute(
                "INSERT INTO jogador (equipa_id, nome, numero, posicao) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (equipa_id, nome) DO UPDATE SET numero = excluded.numero, posicao = excluded.posicao",
                (a["equipa_id"], a["nome"], a["numero"], a["posicao"]))

    def _id_na_tabela_jogador(self) -> int:
        a = self.atleta
        return self.camp._id_jogador(a["equipa_id"], a["nome"])

    def novo(self, nome: str, numero: int, posicao: str, equipa_id: str, semente: int | None = None):
        """Cria o jogador e a primeira época no clube escolhido (a carreira anterior fica terminada)."""
        nome = " ".join(nome.split())[:22]
        if not nome:
            raise ValueError("o jogador precisa de um nome")
        if posicao not in POSICOES:
            raise ValueError(f"posição desconhecida: {posicao}")
        if equipa_id not in EQUIPAS_PORTUGUESAS:
            raise ValueError(f"equipa desconhecida: {equipa_id}")
        numero = max(1, min(99, int(numero)))
        with self.con:
            self.con.execute("UPDATE atleta SET estado = 'terminado' WHERE estado = 'ativo'")
            self.con.execute(
                "INSERT INTO atleta (nome, numero, posicao, equipa_id, geral, epoca, data_inicio) "
                "VALUES (?, ?, ?, ?, ?, 1, ?)",
                (nome, numero, posicao, equipa_id, GERAL_INICIAL, datetime.now().isoformat(timespec="seconds")))
        self._nova_epoca(equipa_id, epoca=1, semente=semente)
        self.vida.garantir()
        with self.con:
            self.vida.registar(f"Assinaste o primeiro contrato, com o {EQUIPAS_INFO[equipa_id]['nome']}. "
                               f"Tens {self.vida.estado['idade']} anos.", {}, "inicio")

    def _nova_epoca(self, equipa_id: str, epoca: int, semente: int | None = None):
        # Da 2.ª época em diante o campeonato continua (subidas e descidas), mesmo mudando de clube
        self.camp.novo(equipa_id, "normal", semente, continuar=epoca > 1)
        tid = self.camp.torneio_id
        with self.con:
            # O número da época é o da carreira do jogador (mesmo que mude de clube)
            self.con.execute("UPDATE torneio SET epoca = ?, nome = ? WHERE id = ?",
                             (epoca, f"Campeonato Nacional {2026 + epoca - 1}/{2027 + epoca - 1}", tid))
            self.con.execute("UPDATE atleta SET equipa_id = ?, epoca = ?, torneio_id = ? WHERE id = ?",
                             (equipa_id, epoca, tid, self.atleta["id"]))
        self._aplicar_no_plantel()

    # ------------------------------------------------------------------ #
    # Jogos                                                               #
    # ------------------------------------------------------------------ #

    def _golos_na_partida(self, partida_id: int) -> int:
        """Golos do jogador numa partida, lidos da tabela estatistica (a mesma dos melhores marcadores)."""
        l = self.con.execute("SELECT golos FROM estatistica WHERE partida_id = ? AND jogador_id = ?",
                             (partida_id, self._id_na_tabela_jogador())).fetchone()
        return l["golos"] if l else 0

    def _gravar_atuacao(self, partida_id: int, est: dict, g_eu: int, g_adv: int, simulado: bool,
                        nota: float | None = None) -> dict:
        a = self.atleta
        est = dict(est, golos=self._golos_na_partida(partida_id))
        if nota is None:
            nota = calcular_nota(est, g_eu, g_adv)
        antes = a["geral"]
        depois = round(max(GERAL_MIN, min(GERAL_MAX, antes + evolucao(nota))), 2)
        self.con.execute(
            "INSERT INTO atuacao (atleta_id, partida_id, torneio_id, equipa_id, golos, assistencias, remates, "
            "passes, recuperacoes, perdas, nota, geral_depois, simulado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (a["id"], partida_id, self.camp.torneio_id, a["equipa_id"], est.get("golos", 0),
             est.get("assistencias", 0), est.get("remates", 0), est.get("passes", 0),
             est.get("recuperacoes", 0), est.get("perdas", 0), nota, depois, int(simulado)))
        self.con.execute("UPDATE atleta SET geral = ? WHERE id = ?", (depois, a["id"]))
        return {"nota": nota, "geral_antes": antes, "geral_depois": depois, "golos": est.get("golos", 0),
                "assistencias": est.get("assistencias", 0), "g_eu": g_eu, "g_adv": g_adv, "simulado": simulado}

    def registar_jogo(self, g_eu: int, g_adv: int, est: dict, marcadores_eu=None, marcadores_adv=None,
                      semente: int | None = None) -> dict:
        """Grava um jogo jogado: o resultado (no campeonato) e a atuação do jogador. Devolve o resumo."""
        jogo = self.camp.proximo_jogo()
        if jogo is None:
            raise RuntimeError("a época já terminou")
        jornada = self.camp.registar_jogo_do_jogador(g_eu, g_adv, semente, marcadores_eu=marcadores_eu,
                                                     marcadores_adv=marcadores_adv)
        with self.con:
            res = self._gravar_atuacao(jogo["id"], est, g_eu, g_adv, simulado=False)
            res["vida"] = self.vida.depois_do_jogo(True, res["nota"], g_eu, g_adv, res["golos"])
        res.update(jornada=jornada, casa=jogo["casa_id"], fora=jogo["fora_id"], ronda=Campeonato.nome_ronda_curto(jogo))
        return res

    def simular_jogo(self, semente: int | None = None) -> dict:
        """
        Simula o próximo jogo. O geral do jogador conta um pouco para a força da equipa, e os
        golos e assistências dele são sorteados conforme a posição e o geral.
        """
        jogo = self.camp.proximo_jogo()
        if jogo is None:
            raise RuntimeError("a época já terminou")
        if not self.vida.pode_jogar()[0]:
            return self.simular_sem_jogador(semente)
        rnd = random.Random(semente)
        a = self.atleta
        eu = a["equipa_id"]
        mod = self.vida.modificador()                         # forma e moral (−8 a +5)
        ajuste = (a["geral"] + mod - 72) * 0.12
        gc, gf = self.camp._simular(jogo["casa_id"], jogo["fora_id"], rnd, ajuste)
        em_casa = jogo["casa_id"] == eu
        g_eu, g_adv = (gc, gf) if em_casa else (gf, gc)
        k = 0.6 + (a["geral"] + mod) / 100 * 0.8               # geral 64 -> 1,1x ; geral 90 -> 1,3x
        p_golo = min(0.75, PROB_GOLO_SIMULADO[a["posicao"]] * k)
        meus = sum(rnd.random() < p_golo for _ in range(g_eu))
        assist = sum(rnd.random() < PROB_ASSIST_SIMULADO[a["posicao"]] * k for _ in range(g_eu - meus))
        # Os outros golos da equipa são dos colegas (senão o sorteio do campeonato podia dar-lhe mais)
        colegas = [(n, p) for n, p, _num in self.camp.campo(eu) if n != a["nome"]]
        pesos = [PESO_GOLO_POSICAO.get(p, 0.2) for _n, p in colegas]
        outros = [rnd.choices([n for n, _p in colegas], weights=pesos)[0] for _ in range(g_eu - meus)]
        jornada = self.camp.registar_jogo_do_jogador(g_eu, g_adv, rnd.randrange(1 << 30), simulado=True,
                                                     marcadores_eu=[a["nome"]] * meus + outros)
        meus = self._golos_na_partida(jogo["id"])           # (o sorteio dos outros golos pode dar-lhe mais)
        est = {"golos": meus, "assistencias": assist}
        nota = 6.0 + 1.0 * meus + 0.6 * assist + (0.4 if g_eu > g_adv else -0.4 if g_eu < g_adv else 0.0)
        nota += (a["geral"] + mod - 70) * 0.02 + rnd.gauss(0, 0.45)
        nota = round(max(3.0, min(10.0, nota)), 1)
        with self.con:
            res = self._gravar_atuacao(jogo["id"], est, g_eu, g_adv, simulado=True, nota=nota)
            res["vida"] = self.vida.depois_do_jogo(True, nota, g_eu, g_adv, res["golos"])
        res.update(jornada=jornada, casa=jogo["casa_id"], fora=jogo["fora_id"], ronda=Campeonato.nome_ronda_curto(jogo))
        return res

    def simular_sem_jogador(self, semente: int | None = None) -> dict:
        """Jornada em que o jogador não joga (lesionado ou no banco): a equipa joga sem ele."""
        jogo = self.camp.proximo_jogo()
        if jogo is None:
            raise RuntimeError("a época já terminou")
        motivo = self.vida.pode_jogar()[1]
        rnd = random.Random(semente)
        a = self.atleta
        eu = a["equipa_id"]
        gc, gf = self.camp._simular(jogo["casa_id"], jogo["fora_id"], rnd, -2.0)   # um jogador a menos
        g_eu, g_adv = (gc, gf) if jogo["casa_id"] == eu else (gf, gc)
        colegas = [(n, p) for n, p, _num in self.camp.campo(eu) if n != a["nome"]]
        pesos = [PESO_GOLO_POSICAO.get(p, 0.2) for _n, p in colegas]
        marcadores = [rnd.choices([n for n, _p in colegas], weights=pesos)[0] for _ in range(g_eu)]
        jornada = self.camp.registar_jogo_do_jogador(g_eu, g_adv, rnd.randrange(1 << 30), simulado=True,
                                                     marcadores_eu=marcadores)
        with self.con:
            frases = self.vida.depois_do_jogo(False, None, g_eu, g_adv)
        return {"jornada": jornada, "ronda": Campeonato.nome_ronda_curto(jogo), "casa": jogo["casa_id"],
                "fora": jogo["fora_id"], "g_eu": g_eu,
                "g_adv": g_adv, "simulado": True, "ausente": motivo, "vida": frases}

    def simular_resto_da_epoca(self, semente: int | None = None) -> int:
        rnd = random.Random(semente)
        n = 0
        while self.camp.proximo_jogo() is not None:
            self.simular_jogo(rnd.randrange(1 << 30))
            ev = self.vida.evento_atual()
            if ev:                                   # a simular a época, as escolhas são ao acaso
                self.vida.escolher(rnd.choice([i for i, ok in enumerate(ev["possivel"]) if ok]))
            n += 1
        return n

    # ------------------------------------------------------------------ #
    # Estatísticas                                                         #
    # ------------------------------------------------------------------ #

    def estatisticas_epoca(self, torneio_id: int | None = None) -> dict:
        """Jogos, golos, assistências e nota média do jogador numa época (por defeito, a atual)."""
        tid = torneio_id or self.camp.torneio_id
        l = self.con.execute(
            "SELECT COUNT(*) AS jogos, COALESCE(SUM(golos), 0) AS golos, "
            "COALESCE(SUM(assistencias), 0) AS assistencias, AVG(nota) AS nota "
            "FROM atuacao WHERE atleta_id = ? AND torneio_id = ?", (self.atleta["id"], tid)).fetchone()
        return {"jogos": l["jogos"], "golos": l["golos"], "assistencias": l["assistencias"],
                "nota": round(l["nota"], 2) if l["nota"] is not None else None}

    def ultimas_notas(self, n: int = 5) -> list:
        """Notas dos últimos n jogos (da mais antiga para a mais recente)."""
        linhas = self.con.execute("SELECT nota FROM atuacao WHERE atleta_id = ? ORDER BY id DESC LIMIT ?",
                                  (self.atleta["id"], n)).fetchall()
        return [l["nota"] for l in reversed(linhas)]

    def historico(self) -> list:
        """Uma linha por época: época, clube, jogos, golos, assistências, nota média, posição final."""
        a = self.atleta
        linhas = self.con.execute(
            "SELECT t.id AS torneio_id, t.epoca, at.equipa_id, COUNT(*) AS jogos, SUM(at.golos) AS golos, "
            "SUM(at.assistencias) AS assistencias, AVG(at.nota) AS nota "
            "FROM atuacao at JOIN torneio t ON t.id = at.torneio_id "
            "WHERE at.atleta_id = ? GROUP BY t.id ORDER BY t.id", (a["id"],)).fetchall()
        return [dict(l) for l in linhas]

    # ------------------------------------------------------------------ #
    # Fim da época: propostas                                              #
    # ------------------------------------------------------------------ #

    def propostas(self) -> list:
        """
        Clubes que querem o jogador no fim da época (só quando a época acabou).
        Com uma nota média boa, os clubes um pouco mais fortes do que o atual fazem proposta:
        quanto melhor a nota, maior o salto (nota 6,8 -> +6 de força; nota 8 -> +20).
        """
        if not self.camp.terminado:
            return []
        est = self.estatisticas_epoca()
        media = est["nota"] or 0.0
        atual = self.atleta["equipa_id"]
        f_atual = FORCA_EQUIPAS.get(atual, 75)
        fama = self.vida.estado["fama"]
        # A fama ajuda: com fama 100 basta nota média 6,4, e os clubes podem ser mais fortes
        limiar = 6.8 - fama / 250
        if media < limiar:
            return []
        salto = 6 + (media - limiar) * 12 + fama / 20
        if "agente" in self.vida.marcas():
            salto += 5                               # o agente arranja propostas de clubes maiores
        clubes = [e for e in EQUIPAS_PORTUGUESAS if e != atual and f_atual < FORCA_EQUIPAS.get(e, 75) <= f_atual + salto]
        clubes.sort(key=lambda e: -FORCA_EQUIPAS.get(e, 75))
        return clubes[:2]

    def continuar(self, equipa_id: str | None = None, semente: int | None = None):
        """Começa a época seguinte: no mesmo clube ou no clube da proposta aceite."""
        if not self.camp.terminado:
            raise RuntimeError("a época ainda não acabou")
        destino = equipa_id or self.atleta["equipa_id"]
        if destino != self.atleta["equipa_id"] and destino not in self.propostas():
            raise ValueError("esse clube não fez proposta")
        mudou_clube = destino != self.atleta["equipa_id"]
        self._nova_epoca(destino, self.atleta["epoca"] + 1, semente)
        frases = self.vida.nova_epoca()
        if mudou_clube:
            with self.con:
                self.vida.registar(f"Assinaste pelo {EQUIPAS_INFO[destino]['nome']}!", {}, "transferencia")
                self.vida.aplicar({"fama": 8, "treinador": 50 - self.vida.estado["treinador"]})
        return frases
