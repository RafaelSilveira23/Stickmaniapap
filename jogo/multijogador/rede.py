"""rede.py - ligação ao servidor do jogo online (WebSocket).

Todos os jogos StickMania ligam-se ao mesmo servidor (servidor/servidor.py, alojado no Render).
O servidor conta quantas pessoas estão online, faz o emparelhamento aleatório e as salas
privadas, e depois passa as mensagens de um jogador para o outro.

A rede corre em threads à parte, para o jogo nunca ficar à espera da internet:
  - uma thread liga-se ao servidor e lê as mensagens que chegam;
  - outra envia as mensagens que o jogo deixa numa fila.
O jogo, em cada frame, só lê os valores que as threads foram atualizando.

Classes:
  Servidor  - a ligação ao servidor (fica aberta enquanto se está no ecrã JOGAR ONLINE);
  Ligacao   - a "ligação" ao outro jogador depois de emparelhados. Tem os mesmos métodos que
              a ligação direta antiga (enviar, mensagens, ativa, terminar), por isso o resto do
              modo online (online.py) não precisou de mudar.

Voltar a ligar (online.py): ao ser emparelhado, o jogo recebe uma chave secreta. Se a ligação cair
a meio da partida, cria-se um Servidor novo com retomar=chave e o servidor põe-no outra vez no
mesmo jogo ("retomado"). eco() e t_rx servem para saber se a ligação está viva: o servidor
responde logo a cada eco, por isso, se passarem uns segundos sem chegar nada, a ligação caiu.

Contas (conta.py): o jogo faz pedidos com pedir() e vai buscar a resposta com resposta(). Se o
jogador tem a conta aberta, o Servidor envia logo o token da sessão quando se liga, por isso os
jogos online ficam associados à conta (ranking) e pode receber desafios de amigos.
"""
import json
import os
import queue
import threading
import time

# Endereço do servidor. Para testar com o servidor no próprio PC:
#   set STICKMANIA_SERVIDOR=ws://localhost:8765
SERVIDOR = os.environ.get("STICKMANIA_SERVIDOR", "wss://stickmania-eu.onrender.com")
VERSAO = 5                  # tem de ser igual à do servidor e à do outro jogo
TEMPO_LIGAR = 90.0          # o servidor gratuito do Render "adormece" e pode demorar ~1 min a acordar


class Ligacao:
    """O outro jogador (as mensagens passam pelo servidor)."""

    def __init__(self, servidor: "Servidor"):
        self._srv = servidor
        self.ativa = True
        self.erro = ""
        self.adversario_caiu = False     # o servidor avisou que a ligação do outro caiu (à espera que volte)
        self._entrada = queue.Queue()

    def enviar(self, msg: dict):
        if not self.ativa:
            return
        # Se a internet estiver lenta e a fila crescer, os estados antigos já não interessam
        if msg.get("t") == "e" and self._srv._saida.qsize() > 6:
            return
        self._srv._enviar({"t": "jogo", "m": msg})

    def mensagens(self) -> list:
        lista = []
        while True:
            try:
                lista.append(self._entrada.get_nowait())
            except queue.Empty:
                return lista

    def terminar(self):
        """Despede-se do outro jogador e volta ao "átrio" do servidor (a ligação ao servidor continua)."""
        if self.ativa:
            self._srv._enviar({"t": "jogo", "m": {"t": "adeus"}})
            self._srv._enviar({"t": "sair_jogo"})
            self.ativa = False

    def fechar(self, erro: str = ""):
        if self.ativa and erro:
            self.erro = erro
        self.ativa = False


class Servidor:
    """
    Liga-se ao servidor numa thread. 'estado' passa de 'a_ligar' para 'ligado' ou 'erro'.
    online / a_jogar / a_procurar: contagens que o servidor envia de 2 em 2 segundos.
    """

    def __init__(self, endereco: str = None, token: str = None, retomar: str = None, presenca: bool = False):
        self.endereco = endereco or SERVIDOR
        self.estado = "a_ligar"
        self.erro = ""
        self.aviso = ""              # ex.: código de sala errado (o ecrã mostra e apaga)
        self.online = self.a_jogar = self.a_procurar = None
        self.codigo = None           # código da sala privada que criámos
        self.ligacao = None          # Ligacao ao outro jogador, depois de emparelhados
        self._emparelhado = None     # (papel, modo) até o jogo o ir buscar
        self.t_inicio = time.perf_counter()
        self._ws = None
        self._fechado = False
        self._saida = queue.Queue()
        # Contas (conta.py)
        self.perfil = None           # perfil da conta com que se entrou (alcunha, pontos, ...)
        self.sessao_erro = ""        # o token já não é válido (é preciso entrar outra vez)
        self.adversario = None       # alcunha do adversário no jogo online (se tiver conta)
        self.convites = []           # alcunhas de quem nos desafiou
        self.aviso_desafio = ""      # ex.: «X recusou o desafio»
        self.ranking_mudou = None    # (pontos ganhos ou perdidos, perfil) no fim de um jogo online
        self._respostas = {}
        self._n_pedido = 0
        # Voltar a ligar
        self.chave = retomar         # chave secreta do jogo em que se está (o servidor dá-a ao emparelhar)
        self.retomado = None         # None à espera; True voltou ao jogo; False o jogo já não existe
        self.t_rx = time.perf_counter()   # quando chegou a última mensagem do servidor
        self._enviar({"t": "ola", "versao": VERSAO})
        if presenca:
            # É a ligação do jogo aberto (não uma ligação curta da nuvem): os desafios vêm para aqui
            self._enviar({"t": "presenca"})
        if token:
            self._enviar({"t": "conta_sessao", "token": token, "pedido": "sessao"})
        if retomar:
            self._enviar({"t": "retomar", "chave": retomar})
        threading.Thread(target=self._correr, daemon=True).start()

    # ------------------------------------------------------------------ pedidos do jogo
    def procurar(self):
        """Entra na fila do jogo aleatório."""
        self._largar()
        self._enviar({"t": "procurar"})

    def criar_sala(self):
        self._largar()
        self._enviar({"t": "criar_sala"})

    def entrar_sala(self, codigo: str):
        self._largar()
        self._enviar({"t": "entrar_sala", "codigo": codigo.upper()})

    def cancelar(self):
        """Sai da fila ou fecha a sala que estava à espera do amigo."""
        self._largar()
        self._enviar({"t": "cancelar"})

    def pedir(self, tipo_msg: str, /, **dados) -> str:
        """Pedido às contas (ex.: pedir("conta_entrar", alcunha=..., senha=...)). Devolve o número do pedido."""
        self._n_pedido += 1
        pid = str(self._n_pedido)
        self._enviar({"t": tipo_msg, "pedido": pid, **dados})
        return pid

    def resposta(self, pid: str):
        """A resposta ao pedido (dicionário com "ok" e os dados ou o "erro"), ou None se ainda não chegou."""
        return self._respostas.pop(pid, None)

    def tomar_emparelhamento(self):
        """(papel, modo) quando se encontrou adversário; senão None. Só devolve uma vez."""
        par, self._emparelhado = self._emparelhado, None
        return par

    def a_acordar(self) -> bool:
        """Está a demorar a ligar: o servidor gratuito estava a dormir."""
        return self.estado == "a_ligar" and time.perf_counter() - self.t_inicio > 4

    def eco(self):
        """Pede ao servidor que responda logo (para saber se a ligação ainda está viva)."""
        self._enviar({"t": "eco"})

    def fechar(self, despedir: bool = True):
        """Fecha a ligação. despedir=False: sem avisar o outro jogador (a ligação caiu e vai-se voltar)."""
        self._fechado = True
        if self.ligacao is not None:
            if despedir:
                self.ligacao.terminar()
            else:
                self.ligacao.fechar()
        self._saida.put(None)
        if self._ws is not None:
            threading.Thread(target=self._fechar_ws, daemon=True).start()

    # ------------------------------------------------------------------ interno
    def _largar(self):
        self.codigo = None
        self._emparelhado = None
        self.aviso = ""
        if self.ligacao is not None:
            self.ligacao.terminar()
            self.ligacao = None

    def _enviar(self, msg: dict):
        self._saida.put(msg)

    def _fechar_ws(self):
        try:
            self._ws.close()
        except Exception:
            pass

    def _correr(self):
        try:
            # Só aqui, para o resto do jogo funcionar mesmo sem o módulo websockets instalado
            from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidURI
            from websockets.sync.client import connect
        except ImportError:
            self.estado = "erro"
            self.erro = "Falta o módulo websockets: pip install websockets"
            return
        try:
            self._ws = connect(self.endereco, open_timeout=TEMPO_LIGAR, close_timeout=2,
                               compression=None, max_size=2 ** 20)
        except (OSError, InvalidHandshake, InvalidURI, TimeoutError) as e:
            if not self._fechado:
                self.estado = "erro"
                self.erro = ("Não foi possível ligar ao servidor do jogo. Confirma a ligação à internet."
                             if not isinstance(e, InvalidHandshake) else
                             "O servidor do jogo não está disponível. Tenta daqui a pouco.")
            return
        if self._fechado:
            self._fechar_ws()
            return
        try:
            # Sem isto o TCP junta as mensagens pequenas (algoritmo de Nagle) e atrasa-as: medimos
            # 90 % das mensagens a chegar em menos de 208 ms sem esta opção e de 96 ms com ela
            import socket
            self._ws.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass
        self.estado = "ligado"
        threading.Thread(target=self._escrever, daemon=True).start()
        try:
            for texto in self._ws:
                try:
                    self._receber(json.loads(texto))
                except (ValueError, KeyError, TypeError):
                    continue
        except (ConnectionClosed, OSError):
            pass
        if not self._fechado:
            if self.estado != "erro":
                self.estado = "erro"
                self.erro = "Perdeu-se a ligação ao servidor do jogo."
            if self.ligacao is not None:
                self.ligacao.fechar("A ligação à internet caiu.")
        self._saida.put(None)

    def _escrever(self):
        from websockets.exceptions import ConnectionClosed
        try:
            while True:
                msg = self._saida.get()
                if msg is None:
                    break
                self._ws.send(json.dumps(msg, separators=(",", ":"), ensure_ascii=False))
        except (ConnectionClosed, OSError):
            pass

    def _receber(self, msg: dict):
        self.t_rx = time.perf_counter()
        t = msg.get("t")
        if t == "eco":
            return
        if t == "jogo":
            if self.ligacao is not None and isinstance(msg.get("m"), dict):
                self.ligacao._entrada.put(msg["m"])
        elif t == "contagem":
            self.online, self.a_jogar, self.a_procurar = msg["online"], msg["a_jogar"], msg["a_procurar"]
        elif t == "sala":
            self.codigo = msg["codigo"]
        elif t == "resposta":
            if msg.get("ok") and isinstance(msg.get("perfil"), dict):
                self.perfil = msg["perfil"]
            if msg.get("pedido") == "sessao":
                if not msg.get("ok"):
                    self.sessao_erro = msg.get("erro", "")
            else:
                self._respostas[str(msg.get("pedido"))] = msg
        elif t == "convite":
            if msg.get("de") and msg["de"] not in self.convites:
                self.convites.append(msg["de"])
        elif t == "aviso":
            self.aviso_desafio = msg.get("texto", "")
        elif t == "ranking_mudou":
            self.perfil = msg.get("perfil") or self.perfil
            self.ranking_mudou = (msg.get("delta", 0), self.perfil)
        elif t == "emparelhado":
            self.adversario = msg.get("adversario")
            self.codigo = None
            self.chave = msg.get("chave")
            self.ligacao = Ligacao(self)
            self._emparelhado = (msg["papel"], msg["modo"])
        elif t == "retomado":
            self.ligacao = Ligacao(self)
            self.retomado = True
        elif t == "retomar_falhou":
            self.retomado = False
        elif t == "caiu":
            if self.ligacao is not None:
                self.ligacao.adversario_caiu = True
        elif t == "voltou":
            if self.ligacao is not None:
                self.ligacao.adversario_caiu = False
        elif t == "saiu":
            if self.ligacao is not None:
                self.ligacao.fechar("O outro jogador perdeu a ligação e não voltou." if msg.get("motivo") == "caiu"
                                    else "O outro jogador saiu do jogo.")
        elif t == "erro":
            if msg.get("erro") == "sala":
                self.aviso = "Não existe nenhuma sala com esse código. Confirma as letras."
            elif msg.get("erro") == "versao":
                self.estado = "erro"
                self.erro = "Há uma versão nova do StickMania. Instala a última versão para jogar online."
