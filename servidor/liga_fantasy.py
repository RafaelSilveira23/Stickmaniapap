"""liga_fantasy.py - EQUIPA DE SONHO online: um jogo de fantasia com os jogos reais do campeonato.

Como funciona:
  • Os jogadores reais do Campeonato Placard (1.ª divisão) são cartas. Os dados vêm do portal
    da Federação (fpp.py): quem foi convocado, quem foi do cinco inicial, golos e cartões.
  • Cada jogador ganha pontos pelo que faz em cada jogo real (ver pontos_jogador).
  • Um amigo cria uma liga privada e recebe um código; os outros entram com esse código.
    Cada treinador recebe 5 cartas sorteadas e moedas.
  • Em cada jornada, o cinco inicial de cada treinador fica "fotografado" quando começa o
    primeiro jogo dessa jornada: só contam os pontos desses cinco.
  • Mercado: todos os dias há jogadores livres à venda; cada um faz a sua oferta (secreta) e,
    à hora de fecho, quem oferecer mais leva o jogador. Há cláusulas de rescisão (pagando-a,
    leva-se logo o jogador de outro treinador) e propostas entre treinadores.
  • Os pontos dão moedas, que servem para o mercado.

O servidor do Render adormece quando ninguém o usa, por isso não há um relógio a correr:
sempre que alguém abre a liga, o servidor vê se já passou tempo suficiente e atualiza os jogos
da FPP, fecha os leilões que já passaram da hora, tira a "fotografia" dos cincos das jornadas que
começaram e paga as moedas dos jogos novos.

Todas as alterações às ligas passam por um só cadeado (asyncio.Lock), para dois pedidos ao mesmo
tempo nunca gastarem as mesmas moedas ou levarem a mesma carta.
"""
import asyncio
import json
import logging
import os
import random
import secrets
import time
from datetime import datetime, timedelta, timezone

import fpp

log = logging.getLogger("stickmania")

# ── Regras (fáceis de afinar) ──
DINHEIRO_INICIAL = 30000
MAX_MEMBROS = 10
MAX_CARTAS = 8
MIN_CARTAS_DONO = 3          # uma cláusula nunca deixa um treinador com menos cartas do que isto
CARTAS_INICIAIS = 5
CARTAS_NO_MERCADO = 8
HORA_FECHO = 20              # os leilões fecham todos os dias às 20h (hora de Lisboa)
PASSO = 500
VENDA_IMEDIATA = 0.75
FATOR_CLAUSULA = 1.5
CUSTO_SUBIR_CLAUSULA = 0.5
PROTECAO_S = 24 * 3600       # carta acabada de comprar não pode ser levada durante 24 h
VALIDADE_PROPOSTA_S = 3 * 24 * 3600
MOEDAS_POR_PONTO = 200
INTERVALO_FPP_S = 20 * 60    # de quanto em quanto tempo (no máximo) se volta a ler a FPP
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Pontos de um jogador num jogo real
P_JOGOU, P_CINCO, P_GOLO = 1, 1, 3
P_VITORIA, P_EMPATE = 2, 1
P_AZUL, P_VERMELHO = -1, -3
P_GR_SOFREU = [(2, 4), (4, 2), (6, 0)]      # guarda-redes do cinco: até 2 golos sofridos +4, até 4 +2, até 6 0; mais -2
P_GR_DEFESA = 2                              # penálti ou livre direto falhado pelo adversário
P_CAMPO_SEGURO = 1                           # jogador do cinco: a equipa sofreu 2 golos ou menos

PASTA = os.path.dirname(os.path.abspath(__file__))

try:
    from zoneinfo import ZoneInfo
    LISBOA = ZoneInfo("Europe/Lisbon")
except Exception:                            # sem base de dados de fusos (alguns Windows)
    LISBOA = timezone.utc

_ESQUEMA = [
    """CREATE TABLE IF NOT EXISTS fpp_equipa (
        eid INTEGER PRIMARY KEY,
        nome TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS fpp_jogo (
        id INTEGER PRIMARY KEY,
        ficha INTEGER,
        jornada INTEGER NOT NULL,
        inicio BIGINT NOT NULL,
        casa_eid INTEGER NOT NULL,
        fora_eid INTEGER NOT NULL,
        golos_casa INTEGER,
        golos_fora INTEGER,
        lido INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS fpp_jogador (
        fed INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        numero INTEGER NOT NULL,
        eid INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS fpp_stats (
        jogo_id INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        eid INTEGER NOT NULL,
        cinco INTEGER NOT NULL,
        jogou INTEGER NOT NULL,
        golos INTEGER NOT NULL,
        azuis INTEGER NOT NULL,
        vermelhos INTEGER NOT NULL,
        marcados INTEGER NOT NULL,
        sofridos INTEGER NOT NULL,
        defesas INTEGER NOT NULL,
        pontos INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (jogo_id, fed))""",
    """CREATE TABLE IF NOT EXISTS fl_liga (
        id {ID},
        codigo TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        dono_id INTEGER NOT NULL,
        criada BIGINT NOT NULL,
        jornada_inicio INTEGER NOT NULL,
        fecho BIGINT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS fl_membro (
        liga_id INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        dinheiro INTEGER NOT NULL,
        entrou BIGINT NOT NULL,
        PRIMARY KEY (liga_id, conta_id))""",
    """CREATE TABLE IF NOT EXISTS fl_carta (
        liga_id INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        clausula INTEGER NOT NULL,
        titular INTEGER NOT NULL DEFAULT 0,
        protegida_ate BIGINT NOT NULL DEFAULT 0,
        PRIMARY KEY (liga_id, fed))""",
    """CREATE TABLE IF NOT EXISTS fl_mercado (
        liga_id INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        PRIMARY KEY (liga_id, fed))""",
    """CREATE TABLE IF NOT EXISTS fl_licitacao (
        liga_id INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor INTEGER NOT NULL,
        quando BIGINT NOT NULL,
        PRIMARY KEY (liga_id, fed, conta_id))""",
    """CREATE TABLE IF NOT EXISTS fl_proposta (
        id {ID},
        liga_id INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        de_id INTEGER NOT NULL,
        para_id INTEGER NOT NULL,
        valor INTEGER NOT NULL,
        criada BIGINT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS fl_onze (
        liga_id INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        jornada INTEGER NOT NULL,
        fed INTEGER NOT NULL,
        PRIMARY KEY (liga_id, conta_id, jornada, fed))""",
    """CREATE TABLE IF NOT EXISTS fl_fotografia (
        liga_id INTEGER NOT NULL,
        jornada INTEGER NOT NULL,
        PRIMARY KEY (liga_id, jornada))""",
    """CREATE TABLE IF NOT EXISTS fl_pago (
        liga_id INTEGER NOT NULL,
        jogo_id INTEGER NOT NULL,
        PRIMARY KEY (liga_id, jogo_id))""",
    """CREATE TABLE IF NOT EXISTS fl_noticia (
        id {ID},
        liga_id INTEGER NOT NULL,
        texto TEXT NOT NULL,
        tipo TEXT NOT NULL,
        data BIGINT NOT NULL)""",
]


class ErroLiga(Exception):
    """Erro para mostrar ao jogador (a mensagem já está em português)."""


def ler_guarda_redes() -> set:
    try:
        with open(os.path.join(PASTA, "guarda_redes.json"), encoding="utf-8") as f:
            return {int(k) for k in json.load(f) if k.isdigit()}
    except (OSError, ValueError):
        return set()


def moedas(v) -> str:
    """12500 -> '12 500' (para as mensagens)."""
    return f"{int(v):,}".replace(",", " ")


def arredondar(v: float, passo: int = PASSO) -> int:
    return int(max(passo, round(v / passo) * passo))


def valor_jogador(pontos: int, jogos: int) -> int:
    """Valor de mercado: cresce com a média de pontos por jogo e com o total da época."""
    media = pontos / jogos if jogos else 0
    return arredondar(2000 + 1200 * max(0.0, media) + 120 * max(0, pontos))


def pontos_jogador(s: dict, guarda_redes: bool) -> int:
    """
    Pontos de um jogador num jogo real:
      jogou +1, cinco inicial +1, golo +3, vitória +2, empate +1, azul -1, vermelho -3;
      guarda-redes do cinco: golos sofridos (até 2: +4, até 4: +2, até 6: 0, mais: -2) e
      +2 por cada penálti ou livre direto falhado pelo adversário;
      jogador de campo do cinco: +1 se a equipa sofreu 2 golos ou menos.
    Quem foi convocado mas não jogou tem 0.
    """
    if not s["jogou"]:
        return 0
    p = P_JOGOU + (P_CINCO if s["cinco"] else 0) + P_GOLO * s["golos"]
    if s["marcados"] > s["sofridos"]:
        p += P_VITORIA
    elif s["marcados"] == s["sofridos"]:
        p += P_EMPATE
    p += P_AZUL * s["azuis"] + P_VERMELHO * s["vermelhos"]
    if s["cinco"] and guarda_redes:
        bonus = -2
        for limite, b in P_GR_SOFREU:
            if s["sofridos"] <= limite:
                bonus = b
                break
        p += bonus + P_GR_DEFESA * s["defesas"]
    elif s["cinco"] and s["sofridos"] <= 2:
        p += P_CAMPO_SEGURO
    return p


def momento_lisboa(data: str, hora: str) -> int:
    """'2026-11-11', '20:00' (hora de Lisboa) -> segundos desde 1970."""
    try:
        d = datetime.strptime(f"{data} {hora or '00:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=LISBOA)
        return int(d.timestamp())
    except ValueError:
        return 0


def proximo_fecho(agora: float) -> int:
    """Próximas 20h de Lisboa depois de 'agora' (os leilões fecham todos os dias a essa hora)."""
    d = datetime.fromtimestamp(agora, LISBOA)
    f = d.replace(hour=HORA_FECHO, minute=0, second=0, microsecond=0)
    if f <= d + timedelta(minutes=5):
        f += timedelta(days=1)
    return int(f.timestamp())


class LigaFantasy:
    def __init__(self, bd, ler_fpp: bool = True):
        self.bd = bd
        self.ler_fpp = ler_fpp                   # nos testes lê-se de ficheiros em vez do site
        self.cadeado = asyncio.Lock()
        self._a_atualizar = asyncio.Lock()
        self._ultima_fpp = 0.0
        self.guarda_redes = ler_guarda_redes()
        self.fonte_jogos = fpp.ler_jogo           # (substituídas nos testes)
        self.fonte_calendario = fpp.ler_competicao

    async def criar_tabelas(self):
        ident = "SERIAL PRIMARY KEY" if self.bd.pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        for sql in _ESQUEMA:
            await self.bd.executar(sql.replace("{ID}", ident))

    # ================================================================== #
    # Dados da FPP                                                        #
    # ================================================================== #

    def a_atualizar(self) -> bool:
        return self._a_atualizar.locked()

    def precisa_atualizar(self) -> bool:
        return self.ler_fpp and time.time() - self._ultima_fpp > INTERVALO_FPP_S

    async def atualizar_fpp(self, forcar: bool = False) -> int:
        """Lê o calendário e os jogos acabados que ainda não tinha lido. Devolve quantos jogos leu."""
        if self._a_atualizar.locked() or (not forcar and time.time() - self._ultima_fpp < INTERVALO_FPP_S):
            return 0
        async with self._a_atualizar:
            self._ultima_fpp = time.time()
            try:
                cal = await asyncio.to_thread(self.fonte_calendario)
            except OSError as e:
                log.warning("FPP: não foi possível ler o calendário: %s", e)
                return 0
            for j in cal:
                for eid, nome in ((j["casa_id"], j["casa"]), (j["fora_id"], j["fora"])):
                    await self.bd.executar("INSERT INTO fpp_equipa (eid, nome) VALUES (?, ?) "
                                           "ON CONFLICT (eid) DO UPDATE SET nome = excluded.nome", eid, nome)
                if not j["numero"]:
                    continue
                # A chave é o número do jogo na competição (os jogos por jogar ainda não têm ficha)
                await self.bd.executar(
                    "INSERT INTO fpp_jogo (id, ficha, jornada, inicio, casa_eid, fora_eid, golos_casa, golos_fora) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET ficha = excluded.ficha, "
                    "jornada = excluded.jornada, inicio = excluded.inicio, golos_casa = excluded.golos_casa, "
                    "golos_fora = excluded.golos_fora",
                    j["numero"], j["id"], j["jornada"], momento_lisboa(j["data"], j["hora"]), j["casa_id"], j["fora_id"],
                    j["golos_casa"], j["golos_fora"])
            por_ler = await self.bd.todos(
                "SELECT * FROM fpp_jogo WHERE lido = 0 AND golos_casa IS NOT NULL AND ficha IS NOT NULL ORDER BY inicio")
            lidos = 0
            for jogo in por_ler:
                try:
                    d = await asyncio.to_thread(self.fonte_jogos, jogo["ficha"])
                except OSError as e:
                    log.warning("FPP: jogo %s por ler: %s", jogo["id"], e)
                    break
                if tuple(d.get("golos_lado", ())) != (jogo["golos_casa"], jogo["golos_fora"]):
                    # A cronologia ainda não está completa (ou mudou): volta-se a tentar mais tarde
                    log.warning("FPP: jogo %s com golos que não batem certo; fica para depois", jogo["id"])
                    continue
                await self._guardar_jogo(jogo, d)
                lidos += 1
                if self.ler_fpp:
                    await asyncio.sleep(fpp.PAUSA_ENTRE_PEDIDOS)
            if lidos:
                log.info("FPP: %d jogos novos lidos", lidos)
            return lidos

    async def _guardar_jogo(self, jogo: dict, d: dict):
        """Guarda os números de cada jogador num jogo e os pontos que fez."""
        falhados = [0, 0]           # penáltis / livres diretos falhados por cada lado
        for lado, evento, _fed in d.get("eventos", []):
            if lado is not None and "falhad" in evento:
                falhados[lado] += 1
        for i, (lado, eid) in enumerate((("casa", jogo["casa_eid"]), ("fora", jogo["fora_eid"]))):
            marc = jogo["golos_casa"] if i == 0 else jogo["golos_fora"]
            sofr = jogo["golos_fora"] if i == 0 else jogo["golos_casa"]
            for p in d[lado]:
                fed = int(p["fed"])
                await self.bd.executar(
                    "INSERT INTO fpp_jogador (fed, nome, numero, eid) VALUES (?, ?, ?, ?) ON CONFLICT (fed) DO "
                    "UPDATE SET nome = excluded.nome, numero = excluded.numero, eid = excluded.eid",
                    fed, p["nome"], int(p["numero"]), eid)
                s = {"cinco": int(p["cinco"]), "jogou": int(p["jogou"]),
                     "golos": int(d["golos"].get(fed, d["golos"].get(str(fed), 0))),
                     "azuis": int(d["azuis"].get(fed, d["azuis"].get(str(fed), 0))),
                     "vermelhos": int(d["vermelhos"].get(fed, d["vermelhos"].get(str(fed), 0))),
                     "marcados": marc, "sofridos": sofr, "defesas": falhados[1 - i]}
                pts = pontos_jogador(s, fed in self.guarda_redes)
                await self.bd.executar(
                    "INSERT INTO fpp_stats (jogo_id, fed, eid, cinco, jogou, golos, azuis, vermelhos, marcados, "
                    "sofridos, defesas, pontos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (jogo_id, fed) "
                    "DO UPDATE SET cinco = excluded.cinco, jogou = excluded.jogou, golos = excluded.golos, "
                    "azuis = excluded.azuis, vermelhos = excluded.vermelhos, marcados = excluded.marcados, "
                    "sofridos = excluded.sofridos, defesas = excluded.defesas, pontos = excluded.pontos",
                    jogo["id"], fed, eid, s["cinco"], s["jogou"], s["golos"], s["azuis"], s["vermelhos"],
                    marc, sofr, s["defesas"], pts)
        await self.bd.executar("UPDATE fpp_jogo SET lido = 1 WHERE id = ?", jogo["id"])

    async def recalcular_pontos(self):
        """Volta a calcular os pontos de todos os jogos (por exemplo, depois de mudar a lista de guarda-redes)."""
        self.guarda_redes = ler_guarda_redes()
        for s in await self.bd.todos("SELECT * FROM fpp_stats"):
            pts = pontos_jogador(s, s["fed"] in self.guarda_redes)
            if pts != s["pontos"]:
                await self.bd.executar("UPDATE fpp_stats SET pontos = ? WHERE jogo_id = ? AND fed = ?",
                                       pts, s["jogo_id"], s["fed"])

    # ================================================================== #
    # Jogadores                                                           #
    # ================================================================== #

    async def jogadores(self) -> dict:
        """Todos os jogadores conhecidos: {fed: {...com pontos, jogos, golos, valor, gr, equipa}}."""
        linhas = await self.bd.todos(
            "SELECT j.fed, j.nome, j.numero, j.eid, e.nome AS equipa, "
            "COALESCE(SUM(s.pontos), 0) AS pontos, COALESCE(SUM(s.jogou), 0) AS jogos, "
            "COALESCE(SUM(s.golos), 0) AS golos FROM fpp_jogador j "
            "JOIN fpp_equipa e ON e.eid = j.eid LEFT JOIN fpp_stats s ON s.fed = j.fed AND s.eid = j.eid "
            "GROUP BY j.fed, j.nome, j.numero, j.eid, e.nome")
        res = {}
        for l in linhas:
            l = dict(l)
            for k in ("pontos", "jogos", "golos"):
                l[k] = int(l[k])
            l["gr"] = l["fed"] in self.guarda_redes
            l["valor"] = valor_jogador(l["pontos"], l["jogos"])
            res[l["fed"]] = l
        return res

    async def jornada_atual(self) -> dict:
        """A próxima jornada (a primeira que ainda não começou) e quando começa; e a última que já começou."""
        agora = int(time.time())
        rs = await self.bd.todos("SELECT jornada, MIN(inicio) AS inicio FROM fpp_jogo GROUP BY jornada ORDER BY jornada")
        proxima = next((r for r in rs if r["inicio"] > agora), None)
        comecadas = [r for r in rs if r["inicio"] <= agora]
        return {"proxima": proxima["jornada"] if proxima else None,
                "inicio_proxima": int(proxima["inicio"]) if proxima else None,
                "ultima": comecadas[-1]["jornada"] if comecadas else 0,
                "total": rs[-1]["jornada"] if rs else 0}

    # ================================================================== #
    # Ligas                                                               #
    # ================================================================== #

    async def _membro(self, liga_id: int, conta_id: int) -> dict:
        m = await self.bd.um("SELECT * FROM fl_membro WHERE liga_id = ? AND conta_id = ?", liga_id, conta_id)
        if m is None:
            raise ErroLiga("Não estás nesta liga.")
        return m

    async def _noticia(self, liga_id: int, texto: str, tipo: str = "info"):
        await self.bd.executar("INSERT INTO fl_noticia (liga_id, texto, tipo, data) VALUES (?, ?, ?, ?)",
                               liga_id, texto, tipo, int(time.time()))

    async def _alcunha(self, conta_id: int) -> str:
        r = await self.bd.um("SELECT alcunha FROM conta WHERE id = ?", conta_id)
        return r["alcunha"] if r else "?"

    async def minhas_ligas(self, conta_id: int) -> list:
        rs = await self.bd.todos(
            "SELECT l.id, l.codigo, l.nome, (SELECT COUNT(*) FROM fl_membro m2 WHERE m2.liga_id = l.id) AS membros "
            "FROM fl_liga l JOIN fl_membro m ON m.liga_id = l.id WHERE m.conta_id = ? ORDER BY l.id", conta_id)
        return [dict(r, membros=int(r["membros"])) for r in rs]

    async def criar_liga(self, conta_id: int, nome: str) -> dict:
        nome = " ".join(str(nome).split())[:24]
        if len(nome) < 3:
            raise ErroLiga("O nome da liga tem de ter pelo menos 3 letras.")
        if len(await self.minhas_ligas(conta_id)) >= 5:
            raise ErroLiga("Já estás em 5 ligas. Sai de uma antes de criar outra.")
        if not await self.bd.um("SELECT fed FROM fpp_jogador LIMIT 1"):
            raise ErroLiga("Ainda não há jogadores do campeonato. Tenta daqui a um minuto.")
        jor = await self.jornada_atual()
        async with self.cadeado:
            for _ in range(20):
                codigo = "".join(secrets.choice(LETRAS) for _ in range(5))
                if not await self.bd.um("SELECT id FROM fl_liga WHERE codigo = ?", codigo):
                    break
            await self.bd.executar(
                "INSERT INTO fl_liga (codigo, nome, dono_id, criada, jornada_inicio, fecho) VALUES (?, ?, ?, ?, ?, ?)",
                codigo, nome, conta_id, int(time.time()), int(jor["proxima"] or jor["total"] + 1),
                proximo_fecho(time.time()))
            liga = await self.bd.um("SELECT * FROM fl_liga WHERE codigo = ?", codigo)
            await self._abrir_mercado(liga["id"])
        await self.entrar_liga(conta_id, codigo)
        return liga

    async def entrar_liga(self, conta_id: int, codigo: str) -> dict:
        codigo = "".join(ch for ch in str(codigo).upper() if ch.isalnum())
        liga = await self.bd.um("SELECT * FROM fl_liga WHERE codigo = ?", codigo)
        if liga is None:
            raise ErroLiga("Não há nenhuma liga com esse código.")
        async with self.cadeado:
            if await self.bd.um("SELECT 1 AS x FROM fl_membro WHERE liga_id = ? AND conta_id = ?", liga["id"], conta_id):
                return liga
            n = await self.bd.um("SELECT COUNT(*) AS n FROM fl_membro WHERE liga_id = ?", liga["id"])
            if int(n["n"]) >= MAX_MEMBROS:
                raise ErroLiga(f"Esta liga já tem {MAX_MEMBROS} treinadores.")
            await self.bd.executar("INSERT INTO fl_membro (liga_id, conta_id, dinheiro, entrou) VALUES (?, ?, ?, ?)",
                                   liga["id"], conta_id, DINHEIRO_INICIAL, int(time.time()))
            cartas = await self._sortear_iniciais(liga["id"], conta_id)
            await self._escolher_cinco(liga["id"], conta_id)
            nomes = ", ".join(c["nome"] for c in cartas)
            await self._noticia(liga["id"], f"{await self._alcunha(conta_id)} entrou na liga com: {nomes}.", "boa")
        return liga

    async def _livres(self, liga_id: int) -> list:
        js = await self.jogadores()
        donos = {r["fed"] for r in await self.bd.todos("SELECT fed FROM fl_carta WHERE liga_id = ?", liga_id)}
        return [j for f, j in js.items() if f not in donos]

    async def _sortear_iniciais(self, liga_id: int, conta_id: int) -> list:
        """1 guarda-redes e 4 jogadores de campo, sorteados entre os mais baratos (as estrelas vão ao mercado)."""
        livres = await self._livres(liga_id)
        rnd = random.Random()
        escolhidas = []
        for gr, n in ((True, 1), (False, CARTAS_INICIAIS - 1)):
            pool = sorted([j for j in livres if j["gr"] == gr], key=lambda j: j["valor"])
            pool = pool[:max(n, len(pool) * 2 // 3)]
            rnd.shuffle(pool)
            escolhidas += pool[:n]
        for c in escolhidas:
            await self._dar(liga_id, c["fed"], conta_id, c["valor"])          # protegidas 24 h
        return escolhidas

    async def _dar(self, liga_id: int, fed: int, conta_id: int, preco: int, proteger: bool = True):
        js = await self.jogadores()
        valor = js[fed]["valor"] if fed in js else preco
        clausula = arredondar(max(preco, valor) * FATOR_CLAUSULA)
        prot = int(time.time()) + PROTECAO_S if proteger else 0
        await self.bd.executar("DELETE FROM fl_mercado WHERE liga_id = ? AND fed = ?", liga_id, fed)
        await self.bd.executar("DELETE FROM fl_licitacao WHERE liga_id = ? AND fed = ?", liga_id, fed)
        await self.bd.executar("DELETE FROM fl_proposta WHERE liga_id = ? AND fed = ?", liga_id, fed)
        await self.bd.executar("DELETE FROM fl_carta WHERE liga_id = ? AND fed = ?", liga_id, fed)
        await self.bd.executar(
            "INSERT INTO fl_carta (liga_id, fed, conta_id, clausula, titular, protegida_ate) VALUES (?, ?, ?, ?, 0, ?)",
            liga_id, fed, conta_id, clausula, prot)

    async def _cartas(self, liga_id: int, conta_id: int) -> list:
        return await self.bd.todos("SELECT * FROM fl_carta WHERE liga_id = ? AND conta_id = ?", liga_id, conta_id)

    async def _escolher_cinco(self, liga_id: int, conta_id: int):
        """Preenche os lugares vazios do cinco com as melhores cartas (1 guarda-redes + 4 de campo)."""
        js = await self.jogadores()
        cartas = await self._cartas(liga_id, conta_id)
        tit = [c for c in cartas if c["titular"]]
        tem_gr = any(js.get(c["fed"], {}).get("gr") for c in tit)
        campo = sum(1 for c in tit if not js.get(c["fed"], {}).get("gr"))
        for c in sorted(cartas, key=lambda c: -js.get(c["fed"], {}).get("valor", 0)):
            if c["titular"]:
                continue
            gr = js.get(c["fed"], {}).get("gr")
            if gr and not tem_gr:
                tem_gr = True
            elif not gr and campo < 4:
                campo += 1
            else:
                continue
            await self.bd.executar("UPDATE fl_carta SET titular = 1 WHERE liga_id = ? AND fed = ?", liga_id, c["fed"])

    # ------------------------------------------------------------------ manutenção (fechar leilões, cincos, moedas)
    async def processar(self, liga_id: int):
        async with self.cadeado:
            liga = await self.bd.um("SELECT * FROM fl_liga WHERE id = ?", liga_id)
            if liga is None:
                raise ErroLiga("Esta liga já não existe.")
            agora = int(time.time())
            if agora >= liga["fecho"]:
                await self._fechar_leiloes(liga)
                await self.bd.executar("UPDATE fl_liga SET fecho = ? WHERE id = ?", proximo_fecho(agora), liga_id)
                await self._abrir_mercado(liga_id)
            await self._fotografar(liga)
            await self._pagar(liga)
            await self.bd.executar("DELETE FROM fl_proposta WHERE liga_id = ? AND criada < ?",
                                   liga_id, agora - VALIDADE_PROPOSTA_S)

    async def _abrir_mercado(self, liga_id: int):
        """Novos jogadores à venda: sorteados entre os livres, com mais hipóteses para os que jogam."""
        await self.bd.executar("DELETE FROM fl_mercado WHERE liga_id = ?", liga_id)
        livres = [j for j in await self._livres(liga_id) if j["jogos"] > 0] or await self._livres(liga_id)
        rnd = random.Random()
        pesos = [1 + j["jogos"] for j in livres]
        escolhidos = []
        while livres and len(escolhidos) < CARTAS_NO_MERCADO:
            i = rnd.choices(range(len(livres)), weights=pesos)[0]
            escolhidos.append(livres.pop(i))
            pesos.pop(i)
        for j in escolhidos:
            await self.bd.executar("INSERT INTO fl_mercado (liga_id, fed) VALUES (?, ?)", liga_id, j["fed"])

    async def _fechar_leiloes(self, liga: dict):
        js = await self.jogadores()
        for m in await self.bd.todos("SELECT fed FROM fl_mercado WHERE liga_id = ?", liga["id"]):
            ofertas = await self.bd.todos(
                "SELECT * FROM fl_licitacao WHERE liga_id = ? AND fed = ? ORDER BY valor DESC, quando ASC",
                liga["id"], m["fed"])
            for o in ofertas:
                mem = await self.bd.um("SELECT * FROM fl_membro WHERE liga_id = ? AND conta_id = ?",
                                       liga["id"], o["conta_id"])
                if mem and mem["dinheiro"] >= o["valor"] and len(await self._cartas(liga["id"], o["conta_id"])) < MAX_CARTAS:
                    await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro - ? WHERE liga_id = ? AND conta_id = ?",
                                           o["valor"], liga["id"], o["conta_id"])
                    await self._dar(liga["id"], m["fed"], o["conta_id"], o["valor"])
                    await self._escolher_cinco(liga["id"], o["conta_id"])
                    outros = len(ofertas) - 1
                    extra = f" ({outros} outra{'s' if outros != 1 else ''} oferta{'s' if outros != 1 else ''})" if outros else ""
                    await self._noticia(liga["id"], f"{await self._alcunha(o['conta_id'])} comprou "
                                        f"{js.get(m['fed'], {}).get('nome', '?')} por {moedas(o['valor'])} moedas{extra}.", "mercado")
                    break
        await self.bd.executar("DELETE FROM fl_licitacao WHERE liga_id = ?", liga["id"])

    async def _fotografar(self, liga: dict):
        """Quando uma jornada começa, guarda o cinco de cada treinador: só esses contam nessa jornada."""
        agora = int(time.time())
        rs = await self.bd.todos("SELECT jornada, MIN(inicio) AS inicio FROM fpp_jogo GROUP BY jornada")
        feitas = {r["jornada"] for r in await self.bd.todos(
            "SELECT jornada FROM fl_fotografia WHERE liga_id = ?", liga["id"])}
        membros = await self.bd.todos("SELECT conta_id FROM fl_membro WHERE liga_id = ?", liga["id"])
        for r in rs:
            j = r["jornada"]
            if j < liga["jornada_inicio"] or j in feitas or int(r["inicio"]) > agora:
                continue
            for m in membros:
                for c in await self._cartas(liga["id"], m["conta_id"]):
                    if c["titular"]:
                        await self.bd.executar(
                            "INSERT INTO fl_onze (liga_id, conta_id, jornada, fed) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT DO NOTHING", liga["id"], m["conta_id"], j, c["fed"])
            await self.bd.executar("INSERT INTO fl_fotografia (liga_id, jornada) VALUES (?, ?)", liga["id"], j)
            await self._noticia(liga["id"], f"Começou a jornada {j}: os cincos ficaram fechados.", "info")

    async def _pagar(self, liga: dict):
        """Moedas pelos pontos dos jogos que acabaram de ser lidos (cada jogo só se paga uma vez)."""
        jogos = await self.bd.todos(
            "SELECT g.id, g.jornada FROM fpp_jogo g WHERE g.lido = 1 AND g.jornada >= ? AND g.id NOT IN "
            "(SELECT jogo_id FROM fl_pago WHERE liga_id = ?) AND g.jornada IN "
            "(SELECT jornada FROM fl_fotografia WHERE liga_id = ?)", liga["jornada_inicio"], liga["id"], liga["id"])
        for g in jogos:
            rs = await self.bd.todos(
                "SELECT o.conta_id, SUM(s.pontos) AS p FROM fl_onze o JOIN fpp_stats s ON s.fed = o.fed "
                "WHERE o.liga_id = ? AND o.jornada = ? AND s.jogo_id = ? GROUP BY o.conta_id",
                liga["id"], g["jornada"], g["id"])
            for r in rs:
                ganho = max(0, int(r["p"])) * MOEDAS_POR_PONTO
                if ganho:
                    await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro + ? WHERE liga_id = ? AND conta_id = ?",
                                           ganho, liga["id"], r["conta_id"])
            await self.bd.executar("INSERT INTO fl_pago (liga_id, jogo_id) VALUES (?, ?)", liga["id"], g["id"])

    # ------------------------------------------------------------------ estado (tudo o que o ecrã mostra)
    async def estado(self, liga_id: int, conta_id: int) -> dict:
        await self._membro(liga_id, conta_id)
        await self.processar(liga_id)
        liga = await self.bd.um("SELECT * FROM fl_liga WHERE id = ?", liga_id)
        js = await self.jogadores()
        jor = await self.jornada_atual()
        membros = await self.bd.todos(
            "SELECT m.conta_id, m.dinheiro, c.alcunha FROM fl_membro m JOIN conta c ON c.id = m.conta_id "
            "WHERE m.liga_id = ?", liga_id)
        tot = {}
        por_jornada = {}
        for r in await self.bd.todos(
                "SELECT o.conta_id, o.jornada, SUM(s.pontos) AS p FROM fl_onze o "
                "JOIN fpp_stats s ON s.fed = o.fed JOIN fpp_jogo g ON g.id = s.jogo_id AND g.jornada = o.jornada "
                "WHERE o.liga_id = ? GROUP BY o.conta_id, o.jornada", liga_id):
            tot[r["conta_id"]] = tot.get(r["conta_id"], 0) + int(r["p"])
            por_jornada.setdefault(r["conta_id"], {})[int(r["jornada"])] = int(r["p"])
        ultima =max([j for d in por_jornada.values() for j in d] or [0])
        tabela = sorted(({"conta_id": m["conta_id"], "alcunha": m["alcunha"], "pontos": tot.get(m["conta_id"], 0),
                          "ultima": por_jornada.get(m["conta_id"], {}).get(ultima), "eu": m["conta_id"] == conta_id,
                          "dinheiro": m["dinheiro"]} for m in membros),
                        key=lambda t: (-t["pontos"], t["alcunha"].lower()))
        cartas = await self.bd.todos("SELECT * FROM fl_carta WHERE liga_id = ?", liga_id)
        agora = int(time.time())

        def carta(c):
            j = dict(js.get(c["fed"], {"fed": c["fed"], "nome": "?", "numero": 0, "equipa": "?", "eid": 0,
                                        "pontos": 0, "jogos": 0, "golos": 0, "gr": False, "valor": 2000}))
            j.update(dono=c["conta_id"], clausula=c["clausula"], titular=bool(c["titular"]),
                     protegida=c["protegida_ate"] > agora)
            return j
        minhas = [carta(c) for c in cartas if c["conta_id"] == conta_id]
        outras = [carta(c) for c in cartas if c["conta_id"] != conta_id]
        lic = {r["fed"]: r["valor"] for r in await self.bd.todos(
            "SELECT fed, valor FROM fl_licitacao WHERE liga_id = ? AND conta_id = ?", liga_id, conta_id)}
        n_ofertas = {r["fed"]: int(r["n"]) for r in await self.bd.todos(
            "SELECT fed, COUNT(*) AS n FROM fl_licitacao WHERE liga_id = ? GROUP BY fed", liga_id)}
        mercado = []
        for r in await self.bd.todos("SELECT fed FROM fl_mercado WHERE liga_id = ?", liga_id):
            if r["fed"] in js:
                mercado.append(dict(js[r["fed"]], minha_oferta=lic.get(r["fed"]), ofertas=n_ofertas.get(r["fed"], 0)))
        propostas = []
        for p in await self.bd.todos(
                "SELECT p.*, a.alcunha AS de, b.alcunha AS para FROM fl_proposta p JOIN conta a ON a.id = p.de_id "
                "JOIN conta b ON b.id = p.para_id WHERE p.liga_id = ? AND (p.para_id = ? OR p.de_id = ?) "
                "ORDER BY p.criada DESC", liga_id, conta_id, conta_id):
            propostas.append({"id": p["id"], "fed": p["fed"], "nome": js.get(p["fed"], {}).get("nome", "?"),
                              "valor": p["valor"], "de": p["de"], "para": p["para"],
                              "recebida": p["para_id"] == conta_id})
        # Pontos dos meus jogadores na última jornada com jogos
        meus_pontos = {}
        if jor["ultima"]:
            for r in await self.bd.todos(
                    "SELECT s.fed, s.pontos, s.golos FROM fpp_stats s JOIN fpp_jogo g ON g.id = s.jogo_id "
                    "WHERE g.jornada = ?", jor["ultima"]):
                meus_pontos[r["fed"]] = {"pontos": r["pontos"], "golos": r["golos"]}
        noticias = await self.bd.todos(
            "SELECT texto, tipo, data FROM fl_noticia WHERE liga_id = ? ORDER BY id DESC LIMIT 12", liga_id)
        resultados = []
        if jor["ultima"]:
            for g in await self.bd.todos(
                    "SELECT g.*, a.nome AS casa, b.nome AS fora FROM fpp_jogo g JOIN fpp_equipa a ON a.eid = g.casa_eid "
                    "JOIN fpp_equipa b ON b.eid = g.fora_eid WHERE g.jornada = ? ORDER BY g.inicio", jor["ultima"]):
                resultados.append({"casa": g["casa"], "fora": g["fora"], "golos_casa": g["golos_casa"],
                                   "golos_fora": g["golos_fora"], "inicio": int(g["inicio"])})
        eu = next(m for m in membros if m["conta_id"] == conta_id)
        return {
            "liga": {"id": liga["id"], "codigo": liga["codigo"], "nome": liga["nome"], "fecho": int(liga["fecho"]),
                     "jornada_inicio": liga["jornada_inicio"], "dono": liga["dono_id"] == conta_id},
            "jornada": jor, "dinheiro": eu["dinheiro"], "licitado": sum(lic.values()),
            "tabela": tabela, "cartas": minhas, "rivais": outras, "mercado": mercado,
            "propostas": propostas, "pontos_ultima": {str(k): v for k, v in meus_pontos.items()},
            "noticias": noticias, "resultados": resultados, "a_atualizar": self.a_atualizar(),
            "regras": {"max_cartas": MAX_CARTAS, "passo": PASSO, "venda": VENDA_IMEDIATA,
                       "custo_clausula": CUSTO_SUBIR_CLAUSULA, "moedas_por_ponto": MOEDAS_POR_PONTO},
        }

    async def jogador(self, fed: int) -> dict:
        """Ficha de um jogador: os pontos de cada jogo."""
        js = await self.jogadores()
        if fed not in js:
            raise ErroLiga("Jogador desconhecido.")
        jogos = await self.bd.todos(
            "SELECT s.*, g.jornada, g.inicio, a.nome AS casa, b.nome AS fora, g.golos_casa, g.golos_fora, "
            "g.casa_eid FROM fpp_stats s JOIN fpp_jogo g ON g.id = s.jogo_id "
            "JOIN fpp_equipa a ON a.eid = g.casa_eid JOIN fpp_equipa b ON b.eid = g.fora_eid "
            "WHERE s.fed = ? ORDER BY g.inicio", fed)
        return dict(js[fed], jogos_lista=[{
            "jornada": g["jornada"], "casa": g["casa"], "fora": g["fora"], "golos_casa": g["golos_casa"],
            "golos_fora": g["golos_fora"], "pontos": g["pontos"], "golos": g["golos"], "cinco": bool(g["cinco"]),
            "jogou": bool(g["jogou"]), "azuis": g["azuis"], "vermelhos": g["vermelhos"]} for g in jogos])

    # ------------------------------------------------------------------ ações do treinador
    async def titular(self, liga_id: int, conta_id: int, fed: int):
        """Põe ou tira um jogador do cinco (1 guarda-redes + 4 de campo). Vale a partir da próxima jornada."""
        await self._membro(liga_id, conta_id)
        await self.processar(liga_id)
        async with self.cadeado:
            cartas = await self._cartas(liga_id, conta_id)
            c = next((c for c in cartas if c["fed"] == fed), None)
            if c is None:
                raise ErroLiga("Esse jogador não é teu.")
            js = await self.jogadores()
            if c["titular"]:
                await self.bd.executar("UPDATE fl_carta SET titular = 0 WHERE liga_id = ? AND fed = ?", liga_id, fed)
                return "Saiu do cinco."
            gr = js.get(fed, {}).get("gr")
            tit = [x for x in cartas if x["titular"]]
            if gr:
                for x in tit:
                    if js.get(x["fed"], {}).get("gr"):
                        await self.bd.executar("UPDATE fl_carta SET titular = 0 WHERE liga_id = ? AND fed = ?",
                                               liga_id, x["fed"])
            elif sum(1 for x in tit if not js.get(x["fed"], {}).get("gr")) >= 4:
                raise ErroLiga("Já tens 4 jogadores de campo no cinco. Tira um primeiro.")
            await self.bd.executar("UPDATE fl_carta SET titular = 1 WHERE liga_id = ? AND fed = ?", liga_id, fed)
            return "Entrou no cinco."

    async def licitar(self, liga_id: int, conta_id: int, fed: int, valor: int):
        m = await self._membro(liga_id, conta_id)
        await self.processar(liga_id)
        async with self.cadeado:
            if not await self.bd.um("SELECT 1 AS x FROM fl_mercado WHERE liga_id = ? AND fed = ?", liga_id, fed):
                raise ErroLiga("Esse jogador já não está à venda.")
            js = await self.jogadores()
            valor = int(valor)
            if valor < js[fed]["valor"]:
                raise ErroLiga(f"A oferta mínima é {moedas(js[fed]['valor'])} moedas.")
            outras = await self.bd.todos("SELECT fed, valor FROM fl_licitacao WHERE liga_id = ? AND conta_id = ? AND fed != ?",
                                         liga_id, conta_id, fed)
            if len(await self._cartas(liga_id, conta_id)) + len(outras) + 1 > MAX_CARTAS:
                raise ErroLiga(f"O plantel só leva {MAX_CARTAS} jogadores. Vende um ou tira outra oferta.")
            if sum(o["valor"] for o in outras) + valor > m["dinheiro"]:
                raise ErroLiga("Não tens moedas para todas as tuas ofertas.")
            await self.bd.executar(
                "INSERT INTO fl_licitacao (liga_id, fed, conta_id, valor, quando) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (liga_id, fed, conta_id) DO UPDATE SET valor = excluded.valor, quando = excluded.quando",
                liga_id, fed, conta_id, valor, int(time.time() * 1000))
            return f"Ofereceste {moedas(valor)} moedas por {js[fed]['nome']}."

    async def retirar(self, liga_id: int, conta_id: int, fed: int):
        await self._membro(liga_id, conta_id)
        async with self.cadeado:
            await self.bd.executar("DELETE FROM fl_licitacao WHERE liga_id = ? AND fed = ? AND conta_id = ?",
                                   liga_id, fed, conta_id)
        return "Oferta retirada."

    async def vender(self, liga_id: int, conta_id: int, fed: int):
        await self._membro(liga_id, conta_id)
        await self.processar(liga_id)
        async with self.cadeado:
            cartas = await self._cartas(liga_id, conta_id)
            if not any(c["fed"] == fed for c in cartas):
                raise ErroLiga("Esse jogador não é teu.")
            js = await self.jogadores()
            preco = arredondar(js[fed]["valor"] * VENDA_IMEDIATA, 100)
            await self.bd.executar("DELETE FROM fl_carta WHERE liga_id = ? AND fed = ?", liga_id, fed)
            await self.bd.executar("DELETE FROM fl_proposta WHERE liga_id = ? AND fed = ?", liga_id, fed)
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro + ? WHERE liga_id = ? AND conta_id = ?",
                                   preco, liga_id, conta_id)
            await self._noticia(liga_id, f"{await self._alcunha(conta_id)} vendeu {js[fed]['nome']} ao mercado.", "mercado")
            return f"Vendeste {js[fed]['nome']} por {moedas(preco)} moedas."

    async def subir_clausula(self, liga_id: int, conta_id: int, fed: int):
        m = await self._membro(liga_id, conta_id)
        async with self.cadeado:
            c = await self.bd.um("SELECT * FROM fl_carta WHERE liga_id = ? AND fed = ? AND conta_id = ?",
                                 liga_id, fed, conta_id)
            if c is None:
                raise ErroLiga("Esse jogador não é teu.")
            js = await self.jogadores()
            aumento = arredondar(js[fed]["valor"] * 0.5)
            custo = arredondar(aumento * CUSTO_SUBIR_CLAUSULA, 100)
            lic = await self.bd.um("SELECT COALESCE(SUM(valor), 0) AS s FROM fl_licitacao WHERE liga_id = ? AND conta_id = ?",
                                   liga_id, conta_id)
            if custo > m["dinheiro"] - int(lic["s"]):
                raise ErroLiga("Não tens moedas para subir a cláusula.")
            await self.bd.executar("UPDATE fl_carta SET clausula = clausula + ? WHERE liga_id = ? AND fed = ?",
                                   aumento, liga_id, fed)
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro - ? WHERE liga_id = ? AND conta_id = ?",
                                   custo, liga_id, conta_id)
            return f"Cláusula +{moedas(aumento)} (pagaste {moedas(custo)} moedas)."

    async def pagar_clausula(self, liga_id: int, conta_id: int, fed: int):
        m = await self._membro(liga_id, conta_id)
        await self.processar(liga_id)
        async with self.cadeado:
            c = await self.bd.um("SELECT * FROM fl_carta WHERE liga_id = ? AND fed = ?", liga_id, fed)
            if c is None:
                raise ErroLiga("Esse jogador não é de ninguém: compra-o no mercado.")
            if c["conta_id"] == conta_id:
                raise ErroLiga("Esse jogador já é teu.")
            if c["protegida_ate"] > time.time():
                raise ErroLiga("Foi comprado há pouco: está protegido durante 24 horas.")
            if len(await self._cartas(liga_id, conta_id)) >= MAX_CARTAS:
                raise ErroLiga(f"O teu plantel já tem {MAX_CARTAS} jogadores.")
            if len(await self._cartas(liga_id, c["conta_id"])) <= MIN_CARTAS_DONO:
                raise ErroLiga("O dono ficava com poucos jogadores.")
            lic = await self.bd.um("SELECT COALESCE(SUM(valor), 0) AS s FROM fl_licitacao WHERE liga_id = ? AND conta_id = ?",
                                   liga_id, conta_id)
            if c["clausula"] > m["dinheiro"] - int(lic["s"]):
                raise ErroLiga("Não tens moedas para pagar a cláusula.")
            js = await self.jogadores()
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro - ? WHERE liga_id = ? AND conta_id = ?",
                                   c["clausula"], liga_id, conta_id)
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro + ? WHERE liga_id = ? AND conta_id = ?",
                                   c["clausula"], liga_id, c["conta_id"])
            await self._dar(liga_id, fed, conta_id, c["clausula"])
            await self._escolher_cinco(liga_id, conta_id)
            await self._noticia(liga_id, f"{await self._alcunha(conta_id)} pagou a cláusula de {js[fed]['nome']} "
                                f"({moedas(c['clausula'])} moedas) a {await self._alcunha(c['conta_id'])}!", "clausula")
            return f"{js[fed]['nome']} é teu!"

    async def propor(self, liga_id: int, conta_id: int, fed: int, valor: int):
        m = await self._membro(liga_id, conta_id)
        async with self.cadeado:
            c = await self.bd.um("SELECT * FROM fl_carta WHERE liga_id = ? AND fed = ?", liga_id, fed)
            if c is None or c["conta_id"] == conta_id:
                raise ErroLiga("Só se fazem propostas por jogadores de outros treinadores.")
            valor = int(valor)
            if valor < PASSO or valor > m["dinheiro"]:
                raise ErroLiga("Não tens moedas para essa proposta.")
            await self.bd.executar("DELETE FROM fl_proposta WHERE liga_id = ? AND fed = ? AND de_id = ?",
                                   liga_id, fed, conta_id)
            await self.bd.executar(
                "INSERT INTO fl_proposta (liga_id, fed, de_id, para_id, valor, criada) VALUES (?, ?, ?, ?, ?, ?)",
                liga_id, fed, conta_id, c["conta_id"], valor, int(time.time()))
            return "Proposta enviada."

    async def responder(self, liga_id: int, conta_id: int, proposta_id: int, aceitar: bool):
        await self._membro(liga_id, conta_id)
        async with self.cadeado:
            p = await self.bd.um("SELECT * FROM fl_proposta WHERE id = ? AND liga_id = ?", proposta_id, liga_id)
            if p is None:
                raise ErroLiga("Essa proposta já não existe.")
            if conta_id not in (p["para_id"], p["de_id"]):
                raise ErroLiga("Essa proposta não é tua.")
            await self.bd.executar("DELETE FROM fl_proposta WHERE id = ?", proposta_id)
            if not aceitar or conta_id == p["de_id"]:
                return "Proposta recusada." if conta_id == p["para_id"] else "Proposta retirada."
            c = await self.bd.um("SELECT * FROM fl_carta WHERE liga_id = ? AND fed = ? AND conta_id = ?",
                                 liga_id, p["fed"], conta_id)
            if c is None:
                raise ErroLiga("Esse jogador já não é teu.")
            comprador = await self.bd.um("SELECT * FROM fl_membro WHERE liga_id = ? AND conta_id = ?", liga_id, p["de_id"])
            if comprador is None or comprador["dinheiro"] < p["valor"]:
                raise ErroLiga("Quem fez a proposta já não tem moedas para ela.")
            if len(await self._cartas(liga_id, p["de_id"])) >= MAX_CARTAS:
                raise ErroLiga("Quem fez a proposta já tem o plantel cheio.")
            js = await self.jogadores()
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro - ? WHERE liga_id = ? AND conta_id = ?",
                                   p["valor"], liga_id, p["de_id"])
            await self.bd.executar("UPDATE fl_membro SET dinheiro = dinheiro + ? WHERE liga_id = ? AND conta_id = ?",
                                   p["valor"], liga_id, conta_id)
            await self._dar(liga_id, p["fed"], p["de_id"], p["valor"])
            await self._escolher_cinco(liga_id, p["de_id"])
            nome = js.get(p["fed"], {}).get("nome", "?")
            await self._noticia(liga_id, f"{await self._alcunha(conta_id)} vendeu {nome} a "
                                f"{await self._alcunha(p['de_id'])} por {moedas(p['valor'])} moedas.", "mercado")
            return f"Vendeste {nome} por {moedas(p['valor'])} moedas."
