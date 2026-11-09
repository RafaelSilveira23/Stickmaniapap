"""servidor.py - servidor do jogo online do StickMania.

Corre na internet (no Render.com, ver o README) e todos os jogos StickMania ligam-se a ele.
Faz quatro coisas:
  1. conta quantas pessoas estão ligadas e quantas estão a jogar, e avisa todos os jogos;
  2. emparelhamento aleatório: quem carrega em JOGO ALEATÓRIO entra numa fila e, quando há
     dois, joga um contra o outro (o primeiro da fila é o anfitrião);
  3. salas privadas: quem cria uma sala recebe um código de 4 letras e o amigo entra com ele;
  4. depois de emparelhados, passa as mensagens de um jogador para o outro (o servidor não
     simula nada: quem simula o jogo é o anfitrião, como no modo online por endereço).

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

VERSAO = 3                  # tem de ser igual à VERSAO do jogo (hockey_game/rede.py)
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # sem O/0 e I/1, que se confundem
MAX_MENSAGEM = 256 * 1024
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
        await anfitriao.enviar({"t": "emparelhado", "papel": "anfitriao", "modo": modo})
        await convidado.enviar({"t": "emparelhado", "papel": "convidado", "modo": modo})
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
        if p is not None:
            p.parceiro = None
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
    async with serve(servidor.atender, "0.0.0.0", porta, process_request=pagina,
                     max_size=MAX_MENSAGEM, ping_interval=20, ping_timeout=30):
        log.info("servidor do StickMania na porta %d", porta)
        await servidor.avisar_contagens()


if __name__ == "__main__":
    asyncio.run(main())
