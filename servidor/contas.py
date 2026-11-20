"""contas.py - contas dos jogadores, progresso guardado na nuvem e ranking.

Cada conta tem uma alcunha e uma palavra-passe (não se pede email: não se guardam dados pessoais).
Quando se cria a conta, o servidor dá um código de recuperação, para o caso de a pessoa se esquecer
da palavra-passe.

Segurança:
  - as palavras-passe e os códigos de recuperação nunca ficam guardados: guarda-se só um "hash"
    PBKDF2-SHA256 com sal (é preciso adivinhar a palavra-passe para o refazer);
  - depois de entrar, o jogo recebe um "token" de sessão (fica guardado no PC); no servidor também
    só fica o hash do token;
  - todas as consultas são parametrizadas (nunca se junta texto do jogador ao SQL).

A base de dados:
  - no Render, Postgres na Neon (a variável de ambiente DATABASE_URL tem o endereço; nunca está
    nos ficheiros do projeto);
  - sem DATABASE_URL (no PC, para testar), um ficheiro SQLite (servidor/contas_local.db).
O SQL está escrito com "?" e é convertido para "$1, $2..." no Postgres.

Ranking: cada conta começa com 1000 pontos. Nos jogos online entre duas contas, os pontos mudam
como no xadrez (sistema Elo): ganhar a quem tem mais pontos dá mais, perder com quem tem menos tira
mais.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import zlib

ITERACOES = 200_000
PONTOS_INICIAIS = 1000
K_ELO = 32
MAX_SAVE = 1_500_000            # bytes do save (comprimido, em base64)
TIPOS_SAVE = ("carreira", "carreira_jogador", "conquistas")
LETRAS_REC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_ESQUEMA = [
    """CREATE TABLE IF NOT EXISTS conta (
        id {ID},
        alcunha TEXT NOT NULL,
        alcunha_min TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        rec_hash TEXT NOT NULL,
        criada BIGINT NOT NULL,
        pontos INTEGER NOT NULL DEFAULT 1000,
        jogos INTEGER NOT NULL DEFAULT 0,
        vitorias INTEGER NOT NULL DEFAULT 0,
        empates INTEGER NOT NULL DEFAULT 0,
        derrotas INTEGER NOT NULL DEFAULT 0,
        golos_marcados INTEGER NOT NULL DEFAULT 0,
        golos_sofridos INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS sessao (
        token_hash TEXT PRIMARY KEY,
        conta_id INTEGER NOT NULL REFERENCES conta(id) ON DELETE CASCADE,
        criada BIGINT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS progresso (
        conta_id INTEGER NOT NULL REFERENCES conta(id) ON DELETE CASCADE,
        tipo TEXT NOT NULL,
        dados TEXT NOT NULL,
        versao BIGINT NOT NULL,
        PRIMARY KEY (conta_id, tipo))""",
    """CREATE TABLE IF NOT EXISTS partida_online (
        id {ID},
        casa_id INTEGER NOT NULL REFERENCES conta(id) ON DELETE CASCADE,
        fora_id INTEGER NOT NULL REFERENCES conta(id) ON DELETE CASCADE,
        golos_casa INTEGER NOT NULL,
        golos_fora INTEGER NOT NULL,
        pontos_casa INTEGER NOT NULL,
        pontos_fora INTEGER NOT NULL,
        data BIGINT NOT NULL)""",
]


class ErroConta(Exception):
    """Erro para mostrar ao jogador (a mensagem já está em português)."""


# ---------------------------------------------------------------------- hashes
def _hash_senha(senha: str, sal: bytes = None) -> str:
    sal = sal or secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return f"pbkdf2${ITERACOES}${sal.hex()}${h.hex()}"


def _confere(senha: str, guardado: str) -> bool:
    try:
        _nome, it, sal, h = guardado.split("$")
        novo = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), int(it))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(novo.hex(), h)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _novo_codigo_rec() -> str:
    """Código de recuperação, ex.: STK-7F3K-92QX (fácil de escrever num papel)."""
    partes = ["".join(secrets.choice(LETRAS_REC) for _ in range(4)) for _ in range(2)]
    return "STK-" + "-".join(partes)


def _limpar_codigo(codigo: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(codigo).upper())


def validar_alcunha(alcunha: str) -> str:
    a = " ".join(str(alcunha).split())
    if not 3 <= len(a) <= 16:
        raise ErroConta("A alcunha tem de ter entre 3 e 16 letras.")
    if not all(ch.isalnum() or ch in " _-." for ch in a):
        raise ErroConta("A alcunha só pode ter letras, números, espaços e _ - .")
    return a


def validar_senha(senha: str):
    if not 6 <= len(str(senha)) <= 64:
        raise ErroConta("A palavra-passe tem de ter entre 6 e 64 caracteres.")


def juntar_conquistas(antigo: str, novo: str) -> str:
    """
    As conquistas nunca se substituem: junta as que já estavam na nuvem com as que chegaram
    (fica a data mais antiga de cada uma e o maior valor de cada contador).
    """
    def ler(dados):
        d = json.loads(zlib.decompress(base64.b64decode(dados)))
        return dict(d.get("ganhas", {})), dict(d.get("contadores", {}))
    try:
        g_novo, c_novo = ler(novo)
    except (ValueError, TypeError, zlib.error, AttributeError):
        raise ErroConta("As conquistas não vieram bem.")
    try:
        g_ant, c_ant = ler(antigo)
    except (ValueError, TypeError, zlib.error, AttributeError):
        return novo
    for k, t in g_ant.items():
        g_novo[k] = min(t, g_novo.get(k, t))
    for k, v in c_ant.items():
        c_novo[k] = max(v, c_novo.get(k, v))
    bruto = json.dumps({"ganhas": g_novo, "contadores": c_novo}).encode("utf-8")
    return base64.b64encode(zlib.compress(bruto, 9)).decode("ascii")


def elo(pontos_a: int, pontos_b: int, resultado_a: float) -> int:
    """Quantos pontos ganha (ou perde) A. resultado_a: 1 vitória, 0.5 empate, 0 derrota."""
    esperado = 1 / (1 + 10 ** ((pontos_b - pontos_a) / 400))
    return round(K_ELO * (resultado_a - esperado))


# ---------------------------------------------------------------------- base de dados
class BaseDados:
    """Postgres (asyncpg) com DATABASE_URL; senão SQLite num ficheiro (para testar no PC)."""

    def __init__(self, url: str = None, ficheiro: str = None):
        self.url = url if url is not None else os.environ.get("DATABASE_URL", "")
        self.ficheiro = ficheiro or os.environ.get("STICKMANIA_BD") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "contas_local.db")
        self.pg = bool(self.url)
        self._pool = None
        self._sqlite = None
        self._lock = asyncio.Lock()

    async def abrir(self):
        if not self.pg and os.environ.get("RENDER"):
            # No Render o disco apaga-se quando o servidor reinicia: sem a base de dados da Neon
            # as contas ficam desligadas (em vez de se perderem)
            raise RuntimeError("falta a variável DATABASE_URL (base de dados da Neon)")
        if self.pg:
            import asyncpg
            # A Neon põe "channel_binding" no endereço, que o asyncpg não conhece; e com o "pooler"
            # da Neon não se podem guardar consultas preparadas (statement_cache_size=0)
            url = re.sub(r"([?&])channel_binding=[^&]*&?", r"\1", self.url).rstrip("?&")
            self._pool = await asyncpg.create_pool(url, min_size=1, max_size=4, statement_cache_size=0)
            ident = "SERIAL PRIMARY KEY"
        else:
            import sqlite3
            self._sqlite = sqlite3.connect(self.ficheiro, check_same_thread=False)
            self._sqlite.row_factory = sqlite3.Row
            self._sqlite.execute("PRAGMA foreign_keys = ON")
            ident = "INTEGER PRIMARY KEY AUTOINCREMENT"
        for sql in _ESQUEMA:
            await self.executar(sql.replace("{ID}", ident))

    async def fechar(self):
        if self._pool is not None:
            await self._pool.close()
        if self._sqlite is not None:
            self._sqlite.close()

    @staticmethod
    def _pg(sql: str) -> str:
        n = 0

        def troca(_m):
            nonlocal n
            n += 1
            return f"${n}"
        return re.sub(r"\?", troca, sql)

    async def executar(self, sql: str, *args):
        if self.pg:
            async with self._pool.acquire() as con:
                await con.execute(self._pg(sql), *args)
        else:
            async with self._lock:
                with self._sqlite:
                    self._sqlite.execute(sql, args)

    async def um(self, sql: str, *args):
        if self.pg:
            async with self._pool.acquire() as con:
                r = await con.fetchrow(self._pg(sql), *args)
            return dict(r) if r is not None else None
        async with self._lock:
            r = self._sqlite.execute(sql, args).fetchone()
        return dict(r) if r is not None else None

    async def todos(self, sql: str, *args) -> list:
        if self.pg:
            async with self._pool.acquire() as con:
                rs = await con.fetch(self._pg(sql), *args)
            return [dict(r) for r in rs]
        async with self._lock:
            rs = self._sqlite.execute(sql, args).fetchall()
        return [dict(r) for r in rs]


# ---------------------------------------------------------------------- regras das contas
_CAMPOS_PERFIL = "id, alcunha, pontos, jogos, vitorias, empates, derrotas, golos_marcados, golos_sofridos"


class Contas:
    def __init__(self, bd: BaseDados):
        self.bd = bd

    async def perfil(self, conta_id: int) -> dict:
        p = await self.bd.um(f"SELECT {_CAMPOS_PERFIL} FROM conta WHERE id = ?", conta_id)
        if p is None:
            raise ErroConta("Esta conta já não existe.")
        acima = await self.bd.um("SELECT COUNT(*) AS n FROM conta WHERE pontos > ?", p["pontos"])
        p["posicao"] = int(acima["n"]) + 1
        return p

    async def _nova_sessao(self, conta_id: int) -> str:
        token = secrets.token_urlsafe(32)
        await self.bd.executar("INSERT INTO sessao (token_hash, conta_id, criada) VALUES (?, ?, ?)",
                               _hash_token(token), conta_id, int(time.time()))
        return token

    async def criar(self, alcunha: str, senha: str) -> dict:
        alcunha = validar_alcunha(alcunha)
        validar_senha(senha)
        if await self.bd.um("SELECT id FROM conta WHERE alcunha_min = ?", alcunha.lower()):
            raise ErroConta("Essa alcunha já está a ser usada. Escolhe outra.")
        codigo = _novo_codigo_rec()
        senha_h, rec_h = await asyncio.gather(asyncio.to_thread(_hash_senha, senha),
                                              asyncio.to_thread(_hash_senha, _limpar_codigo(codigo)))
        try:
            await self.bd.executar(
                "INSERT INTO conta (alcunha, alcunha_min, senha_hash, rec_hash, criada, pontos) "
                "VALUES (?, ?, ?, ?, ?, ?)", alcunha, alcunha.lower(), senha_h, rec_h, int(time.time()),
                PONTOS_INICIAIS)
        except Exception as e:                    # duas pessoas a criar a mesma alcunha ao mesmo tempo
            if "unique" in str(e).lower():
                raise ErroConta("Essa alcunha já está a ser usada. Escolhe outra.")
            raise
        conta = await self.bd.um("SELECT id FROM conta WHERE alcunha_min = ?", alcunha.lower())
        token = await self._nova_sessao(conta["id"])
        return {"token": token, "recuperacao": codigo, "perfil": await self.perfil(conta["id"])}

    async def entrar(self, alcunha: str, senha: str) -> dict:
        conta = await self.bd.um("SELECT id, senha_hash FROM conta WHERE alcunha_min = ?",
                                 " ".join(str(alcunha).split()).lower())
        ok = conta is not None and await asyncio.to_thread(_confere, str(senha), conta["senha_hash"])
        if not ok:
            raise ErroConta("Alcunha ou palavra-passe erradas.")
        token = await self._nova_sessao(conta["id"])
        return {"token": token, "perfil": await self.perfil(conta["id"])}

    async def sessao(self, token: str) -> dict:
        s = await self.bd.um("SELECT conta_id FROM sessao WHERE token_hash = ?", _hash_token(str(token)))
        if s is None:
            raise ErroConta("A sessão terminou. Entra outra vez na conta.")
        return {"perfil": await self.perfil(s["conta_id"])}

    async def recuperar(self, alcunha: str, codigo: str, senha_nova: str) -> dict:
        validar_senha(senha_nova)
        conta = await self.bd.um("SELECT id, rec_hash FROM conta WHERE alcunha_min = ?",
                                 " ".join(str(alcunha).split()).lower())
        ok = conta is not None and await asyncio.to_thread(_confere, _limpar_codigo(codigo), conta["rec_hash"])
        if not ok:
            raise ErroConta("Alcunha ou código de recuperação errados.")
        novo_codigo = _novo_codigo_rec()
        senha_h, rec_h = await asyncio.gather(asyncio.to_thread(_hash_senha, str(senha_nova)),
                                              asyncio.to_thread(_hash_senha, _limpar_codigo(novo_codigo)))
        await self.bd.executar("UPDATE conta SET senha_hash = ?, rec_hash = ? WHERE id = ?", senha_h, rec_h, conta["id"])
        await self.bd.executar("DELETE FROM sessao WHERE conta_id = ?", conta["id"])   # sai dos outros PCs
        token = await self._nova_sessao(conta["id"])
        return {"token": token, "recuperacao": novo_codigo, "perfil": await self.perfil(conta["id"])}

    async def sair(self, token: str):
        await self.bd.executar("DELETE FROM sessao WHERE token_hash = ?", _hash_token(str(token)))

    # ------------------------------------------------------------------ progresso na nuvem
    async def guardar(self, conta_id: int, tipo: str, dados: str, versao: int) -> int:
        if tipo not in TIPOS_SAVE:
            raise ErroConta("Tipo de progresso desconhecido.")
        if not isinstance(dados, str) or len(dados) > MAX_SAVE:
            raise ErroConta("O progresso é grande demais para guardar.")
        versao = int(versao)
        existe = await self.bd.um("SELECT versao, dados FROM progresso WHERE conta_id = ? AND tipo = ?",
                                  conta_id, tipo)
        if tipo == "conquistas":
            dados = juntar_conquistas(existe["dados"] if existe else "", dados)
        if existe is None:
            await self.bd.executar("INSERT INTO progresso (conta_id, tipo, dados, versao) VALUES (?, ?, ?, ?)",
                                   conta_id, tipo, dados, versao)
        else:
            await self.bd.executar("UPDATE progresso SET dados = ?, versao = ? WHERE conta_id = ? AND tipo = ?",
                                   dados, versao, conta_id, tipo)
        return versao

    async def versoes(self, conta_id: int) -> dict:
        rs = await self.bd.todos("SELECT tipo, versao FROM progresso WHERE conta_id = ?", conta_id)
        return {r["tipo"]: int(r["versao"]) for r in rs}

    async def carregar(self, conta_id: int, tipo: str) -> dict:
        r = await self.bd.um("SELECT dados, versao FROM progresso WHERE conta_id = ? AND tipo = ?", conta_id, tipo)
        if r is None:
            raise ErroConta("Não há progresso guardado na nuvem.")
        return {"tipo": tipo, "dados": r["dados"], "versao": int(r["versao"])}

    # ------------------------------------------------------------------ ranking
    async def ranking(self, limite: int = 20) -> list:
        return await self.bd.todos(
            f"SELECT {_CAMPOS_PERFIL} FROM conta ORDER BY pontos DESC, vitorias DESC, id ASC LIMIT ?",
            int(limite))

    async def historico(self, conta_id: int, limite: int = 10) -> list:
        rs = await self.bd.todos(
            "SELECT p.golos_casa, p.golos_fora, p.pontos_casa, p.pontos_fora, p.data, p.casa_id, "
            "c.alcunha AS casa, f.alcunha AS fora FROM partida_online p "
            "JOIN conta c ON c.id = p.casa_id JOIN conta f ON f.id = p.fora_id "
            "WHERE p.casa_id = ? OR p.fora_id = ? ORDER BY p.data DESC, p.id DESC LIMIT ?",
            conta_id, conta_id, int(limite))
        lista = []
        for r in rs:
            sou_casa = r["casa_id"] == conta_id
            eu, ele = (r["golos_casa"], r["golos_fora"]) if sou_casa else (r["golos_fora"], r["golos_casa"])
            lista.append({"adversario": r["fora"] if sou_casa else r["casa"], "eu": eu, "ele": ele,
                          "pontos": r["pontos_casa"] if sou_casa else r["pontos_fora"], "data": int(r["data"])})
        return lista

    async def registar_partida(self, casa_id: int, fora_id: int, golos_casa: int, golos_fora: int) -> tuple:
        """Jogo online entre duas contas: atualiza os pontos e as estatísticas. Devolve (delta_casa, delta_fora)."""
        a = await self.bd.um("SELECT pontos FROM conta WHERE id = ?", casa_id)
        b = await self.bd.um("SELECT pontos FROM conta WHERE id = ?", fora_id)
        if a is None or b is None:
            return 0, 0
        res = 1.0 if golos_casa > golos_fora else (0.5 if golos_casa == golos_fora else 0.0)
        d_casa = elo(a["pontos"], b["pontos"], res)
        d_fora = elo(b["pontos"], a["pontos"], 1.0 - res)
        for cid, delta, gm, gs, r in ((casa_id, d_casa, golos_casa, golos_fora, res),
                                      (fora_id, d_fora, golos_fora, golos_casa, 1.0 - res)):
            await self.bd.executar(
                "UPDATE conta SET pontos = pontos + ?, jogos = jogos + 1, vitorias = vitorias + ?, "
                "empates = empates + ?, derrotas = derrotas + ?, golos_marcados = golos_marcados + ?, "
                "golos_sofridos = golos_sofridos + ? WHERE id = ?",
                delta, int(r == 1.0), int(r == 0.5), int(r == 0.0), gm, gs, cid)
        await self.bd.executar(
            "INSERT INTO partida_online (casa_id, fora_id, golos_casa, golos_fora, pontos_casa, pontos_fora, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", casa_id, fora_id, golos_casa, golos_fora, d_casa, d_fora, int(time.time()))
        return d_casa, d_fora
