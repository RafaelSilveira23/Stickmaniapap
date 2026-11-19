"""servidor.py - servidor do jogo online do StickMania.

Corre na internet (no Render.com, ver o README) e todos os jogos StickMania ligam-se a ele.
Faz quatro coisas:
  1. conta quantas pessoas estão ligadas e quantas estão a jogar, e avisa todos os jogos;
  2. emparelhamento aleatório: quem carrega em JOGO ALEATÓRIO entra numa fila e, quando há
     dois, joga um contra o outro (o primeiro da fila é o anfitrião);
  3. salas privadas: quem cria uma sala recebe um código de 4 letras e o amigo entra com ele;
  4. depois de emparelhados, passa as mensagens de um jogador para o outro (o servidor não
     simula nada: quem simula o jogo é o anfitrião, como no modo online por endereço);
  5. contas (contas.py): entrar com alcunha e palavra-passe, guardar o progresso das carreiras
     na nuvem, ranking dos jogos online e desafios a um amigo pela alcunha.

A ligação é um WebSocket (funciona em qualquer rede, porque passa pela porta normal da web).
Cada mensagem é um dicionário em JSON com o tipo em "t".

Executar no próprio PC (para testar):   python servidor/servidor.py
O Render diz a porta na variável de ambiente PORT.
"""
import asyncio
import json
import logging
import os
import random
import time
from http import HTTPStatus

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from contas import BaseDados, Contas, ErroConta, TIPOS_SAVE

VERSAO = 3                  # tem de ser igual à VERSAO do jogo (hockey_game/rede.py)
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # sem O/0 e I/1, que se confundem
MAX_MENSAGEM = 2 * 1024 * 1024    # o progresso das carreiras vai numa mensagem só
MAX_FALHAS = 5                    # tentativas erradas de entrar antes de ter de esperar
ESPERA_FALHAS = 30.0
INTERVALO_CONTAGEM = 2.0    # segundos entre os avisos de quantos estão online

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("stickmania")


class Cliente:
    def __init__(self, ws):
        self.ws = ws
        self.estado = "lobby"       # lobby, fila, sala (à espera do amigo) ou jogo
        self.parceiro = None
        self.codigo = None
        self.pronto = False          # já disse "ola" com a versão certa
        self.papel = None            # "anfitriao" ou "convidado" (no jogo)
        self.conta_id = None         # conta com que entrou (contas.py)
        self.alcunha = None
        self.falhas = 0
        self.espera_ate = 0.0
        self.resultado = None        # resultado que este jogo enviou no fim da partida
        self.convites = set()        # quem o desafiou (clientes)

    async def enviar(self, msg):
        try:
            await self.ws.send(msg if isinstance(msg, str) else json.dumps(msg, separators=(",", ":")))
        except ConnectionClosed:
            pass


class Servidor:
    def __init__(self):
        self.clientes = set()
        self.fila = []               # à procura de jogo aleatório
        self.salas = {}              # código -> cliente que criou a sala
        self.inicio = time.time()
        self.contas = None           # fica None se a base de dados não abrir (o online continua)

    # ------------------------------------------------------------------ contagens
    def contagem(self) -> dict:
        prontos = [c for c in self.clientes if c.pronto]
        return {"t": "contagem", "online": len(prontos),
                "a_jogar": sum(1 for c in prontos if c.estado == "jogo"),
                "a_procurar": len(self.fila)}

    async def avisar_contagens(self):
        ultima, t_ultima = None, 0.0
        while True:
            await asyncio.sleep(INTERVALO_CONTAGEM)
            c = self.contagem()
            if c != ultima or time.time() - t_ultima > 15:
                ultima, t_ultima = c, time.time()
                texto = json.dumps(c)
                await asyncio.gather(*(cl.enviar(texto) for cl in list(self.clientes) if cl.pronto))

    # ------------------------------------------------------------------ emparelhar
    async def emparelhar(self, anfitriao: Cliente, convidado: Cliente, modo: str):
        for c in (anfitriao, convidado):
            self.sair_da_espera(c)
            c.estado = "jogo"
        anfitriao.parceiro, convidado.parceiro = convidado, anfitriao
        anfitriao.papel, convidado.papel = "anfitriao", "convidado"
        anfitriao.resultado = convidado.resultado = None
        await anfitriao.enviar({"t": "emparelhado", "papel": "anfitriao", "modo": modo,
                                "adversario": convidado.alcunha})
        await convidado.enviar({"t": "emparelhado", "papel": "convidado", "modo": modo,
                                "adversario": anfitriao.alcunha})
        await self.enviar_contagem_a(anfitriao, convidado)
        log.info("jogo %s começou (%d online)", modo, len(self.clientes))

    async def enviar_contagem_a(self, *clientes):
        c = self.contagem()
        for cl in clientes:
            await cl.enviar(c)

    def sair_da_espera(self, c: Cliente):
        if c in self.fila:
            self.fila.remove(c)
        if c.codigo and self.salas.get(c.codigo) is c:
            del self.salas[c.codigo]
        c.codigo = None
        if c.estado in ("fila", "sala"):
            c.estado = "lobby"

    async def sair_do_jogo(self, c: Cliente):
        p = c.parceiro
        c.parceiro = None
        if c.estado == "jogo":
            c.estado = "lobby"
        c.resultado = None
        if p is not None:
            p.parceiro = None
            p.resultado = None
            p.estado = "lobby"
            await p.enviar({"t": "saiu"})

    def novo_codigo(self) -> str:
        while True:
            codigo = "".join(random.choice(LETRAS) for _ in range(4))
            if codigo not in self.salas:
                return codigo

    # ------------------------------------------------------------------ mensagens
    async def mensagem(self, c: Cliente, msg: dict):
        t = msg.get("t")
        if t == "ola":
            if msg.get("versao") != VERSAO:
                await c.enviar({"t": "erro", "erro": "versao"})
                await c.ws.close()
                return
            c.pronto = True
            await c.enviar(self.contagem())
            return
        if not c.pronto:
            return
        if t == "jogo":
            if c.parceiro is not None:
                await c.parceiro.enviar({"t": "jogo", "m": msg.get("m")})
        elif t == "procurar":
            if c.estado == "jogo":
                await self.sair_do_jogo(c)
            self.sair_da_espera(c)
            outros = [o for o in self.fila if o is not c]
            if outros:
                await self.emparelhar(outros[0], c, "aleatorio")
            else:
                self.fila.append(c)
                c.estado = "fila"
                await self.enviar_contagem_a(c)
        elif t == "criar_sala":
            if c.estado == "jogo":
                await self.sair_do_jogo(c)
            self.sair_da_espera(c)
            c.codigo = self.novo_codigo()
            c.estado = "sala"
            self.salas[c.codigo] = c
            await c.enviar({"t": "sala", "codigo": c.codigo})
        elif t == "entrar_sala":
            codigo = str(msg.get("codigo", "")).upper().strip()
            dono = self.salas.get(codigo)
            if dono is None or dono is c:
                await c.enviar({"t": "erro", "erro": "sala"})
            else:
                if c.estado == "jogo":
                    await self.sair_do_jogo(c)
                await self.emparelhar(dono, c, "privado")
        elif t == "cancelar":
            self.sair_da_espera(c)
        elif t == "sair_jogo":
            await self.sair_do_jogo(c)
        elif isinstance(t, str) and t.startswith(("conta_", "nuvem_", "ranking", "historico", "resultado",
                                                  "desafiar", "aceitar", "recusar")):
            await self.mensagem_conta(c, t, msg)

    # ------------------------------------------------------------------ contas (contas.py)
    async def mensagem_conta(self, c: Cliente, t: str, msg: dict):
        pedido = msg.get("pedido")          # o jogo usa-o para saber a que pedido é a resposta

        async def resposta(dados: dict):
            await c.enviar({"t": "resposta", "pedido": pedido, "ok": True, **dados})

        async def erro(texto: str):
            await c.enviar({"t": "resposta", "pedido": pedido, "ok": False, "erro": texto})

        if self.contas is None:
            await erro("As contas não estão disponíveis neste momento. Tenta mais tarde.")
            return
        try:
            if t in ("conta_criar", "conta_entrar", "conta_recuperar"):
                if time.time() < c.espera_ate:
                    raise ErroConta("Tentaste muitas vezes. Espera um bocadinho e tenta outra vez.")
                try:
                    if t == "conta_criar":
                        r = await self.contas.criar(msg.get("alcunha", ""), msg.get("senha", ""))
                    elif t == "conta_entrar":
                        r = await self.contas.entrar(msg.get("alcunha", ""), msg.get("senha", ""))
                    else:
                        r = await self.contas.recuperar(msg.get("alcunha", ""), msg.get("codigo", ""),
                                                        msg.get("senha", ""))
                except ErroConta:
                    c.falhas += 1
                    if c.falhas >= MAX_FALHAS:
                        c.falhas, c.espera_ate = 0, time.time() + ESPERA_FALHAS
                    raise
                c.falhas = 0
                self._entrou(c, r["perfil"])
                await resposta(r)
            elif t == "conta_sessao":
                r = await self.contas.sessao(msg.get("token", ""))
                self._entrou(c, r["perfil"])
                await resposta(r)
            elif t == "conta_sair":
                await self.contas.sair(msg.get("token", ""))
                c.conta_id = c.alcunha = None
                await resposta({})
            elif t == "ranking":
                lista = await self.contas.ranking()
                eu = await self.contas.perfil(c.conta_id) if c.conta_id else None
                await resposta({"lista": lista, "eu": eu})
            elif c.conta_id is None:
                raise ErroConta("Entra na tua conta primeiro.")
            elif t == "conta_perfil":
                await resposta({"perfil": await self.contas.perfil(c.conta_id)})
            elif t == "historico":
                await resposta({"lista": await self.contas.historico(c.conta_id)})
            elif t == "nuvem_guardar":
                v = await self.contas.guardar(c.conta_id, msg.get("tipo"), msg.get("dados"), msg.get("versao", 0))
                await resposta({"tipo": msg.get("tipo"), "versao": v})
            elif t == "nuvem_versoes":
                await resposta({"versoes": await self.contas.versoes(c.conta_id)})
            elif t == "nuvem_carregar":
                if msg.get("tipo") not in TIPOS_SAVE:
                    raise ErroConta("Tipo de progresso desconhecido.")
                await resposta(await self.contas.carregar(c.conta_id, msg["tipo"]))
            elif t == "resultado":
                await self._resultado(c, msg)
            elif t == "desafiar":
                await self._desafiar(c, str(msg.get("alcunha", "")))
                await resposta({})
            elif t in ("aceitar", "recusar"):
                await self._responder_desafio(c, str(msg.get("de", "")), t == "aceitar")
        except ErroConta as e:
            await erro(str(e))
        except Exception:
            log.exception("erro nas contas")
            await erro("Houve um problema no servidor. Tenta outra vez.")

    def _entrou(self, c: Cliente, perfil: dict):
        c.conta_id, c.alcunha = perfil["id"], perfil["alcunha"]

    async def _resultado(self, c: Cliente, msg: dict):
        """Fim de um jogo online: só conta para o ranking quando os dois jogos dizem o mesmo resultado."""
        p = c.parceiro
        try:
            c.resultado = (int(msg["casa"]), int(msg["fora"]))
        except (KeyError, TypeError, ValueError):
            return
        if p is None or p.resultado is None or p.resultado != c.resultado:
            return
        casa, fora = c.resultado
        c.resultado = p.resultado = None
        anf, conv = (c, p) if c.papel == "anfitriao" else (p, c)
        if not anf.conta_id or not conv.conta_id or anf.conta_id == conv.conta_id:
            return
        d_casa, d_fora = await self.contas.registar_partida(anf.conta_id, conv.conta_id, casa, fora)
        for cl, delta in ((anf, d_casa), (conv, d_fora)):
            await cl.enviar({"t": "ranking_mudou", "delta": delta, "perfil": await self.contas.perfil(cl.conta_id)})
        log.info("jogo a contar para o ranking: %d-%d", casa, fora)

    async def _desafiar(self, c: Cliente, alcunha: str):
        alvo_min = " ".join(alcunha.split()).lower()
        alvo = next((o for o in self.clientes if o.pronto and o.alcunha and o.alcunha.lower() == alvo_min), None)
        if alvo is None:
            raise ErroConta(f"{alcunha} não está online (tem de estar no ecrã JOGAR ONLINE).")
        if alvo is c:
            raise ErroConta("Não te podes desafiar a ti próprio.")
        if alvo.estado == "jogo":
            raise ErroConta(f"{alvo.alcunha} está a meio de um jogo.")
        alvo.convites.add(c)
        await alvo.enviar({"t": "convite", "de": c.alcunha})

    async def _responder_desafio(self, c: Cliente, de: str, aceita: bool):
        de_min = " ".join(de.split()).lower()
        quem = next((o for o in c.convites if o.alcunha and o.alcunha.lower() == de_min), None)
        if quem is not None:
            c.convites.discard(quem)
        if quem is None or quem not in self.clientes or quem.estado == "jogo":
            await c.enviar({"t": "aviso", "texto": f"{de} já não está à espera."})
            return
        if aceita:
            if c.estado == "jogo":
                await self.sair_do_jogo(c)
            await self.emparelhar(quem, c, "desafio")
        else:
            await quem.enviar({"t": "aviso", "texto": f"{c.alcunha} recusou o desafio."})

    async def atender(self, ws):
        c = Cliente(ws)
        self.clientes.add(c)
        try:
            async for texto in ws:
                try:
                    msg = json.loads(texto)
                except (ValueError, TypeError):
                    continue
                if isinstance(msg, dict):
                    await self.mensagem(c, msg)
        except ConnectionClosed:
            pass
        finally:
            self.clientes.discard(c)
            for o in self.clientes:
                o.convites.discard(c)
            self.sair_da_espera(c)
            await self.sair_do_jogo(c)


def pagina(connection, request):
    """Pedidos normais (sem WebSocket), por exemplo a verificação do Render: responde «ok»."""
    if request.headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(HTTPStatus.OK, "StickMania - servidor online a funcionar\n")
    return None


async def main():
    porta = int(os.environ.get("PORT", "8765"))
    servidor = Servidor()
    try:
        bd = BaseDados()
        await bd.abrir()
        servidor.contas = Contas(bd)
        log.info("contas: %s", "Postgres" if bd.pg else "SQLite " + bd.ficheiro)
    except Exception:
        log.exception("as contas não estão disponíveis (o jogo online continua a funcionar)")
    async with serve(servidor.atender, "0.0.0.0", porta, process_request=pagina,
                     max_size=MAX_MENSAGEM, ping_interval=20, ping_timeout=30):
        log.info("servidor do StickMania na porta %d", porta)
        await servidor.avisar_contagens()


if __name__ == "__main__":
    asyncio.run(main())
