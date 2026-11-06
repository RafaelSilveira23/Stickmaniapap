"""rede.py - ligação entre dois computadores para o modo online (TCP).

Quem cria o jogo é o ANFITRIÃO: abre uma porta e fica à espera. O CONVIDADO liga-se ao
endereço do anfitrião. Depois de ligados, os dois trocam mensagens (dicionários do Python
convertidos em JSON). Cada mensagem vai com 4 bytes à frente a dizer o tamanho, porque o
TCP é um "tubo" de bytes e não separa as mensagens sozinho.

A rede corre em threads à parte: o jogo nunca fica à espera da internet.
  - uma thread lê as mensagens que chegam e põe-nas numa fila;
  - outra envia as mensagens que o jogo deixa noutra fila.
O jogo, em cada frame, só tira o que estiver nas filas.
"""
import json
import queue
import socket
import struct
import threading

PORTA = 50555
VERSAO = 1                  # os dois jogos têm de ter a mesma versão do modo online
TEMPO_LIGAR = 8.0           # segundos até desistir de ligar


class Ligacao:
    """Uma ligação TCP já aberta, com filas de entrada e de saída."""

    def __init__(self, sock: socket.socket):
        sock.settimeout(None)
        try:
            # Sem o algoritmo de Nagle: as mensagens pequenas saem logo (menos atraso)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.sock = sock
        self.ativa = True
        self.erro = ""
        self._entrada = queue.Queue()
        self._saida = queue.Queue()
        threading.Thread(target=self._ler, daemon=True).start()
        threading.Thread(target=self._escrever, daemon=True).start()

    # ------------------------------------------------------------------ #
    def enviar(self, msg: dict):
        """Põe a mensagem na fila de saída (não espera pela rede)."""
        if not self.ativa:
            return
        # Se a internet estiver lenta e a fila crescer, os estados antigos já não interessam
        if msg.get("t") == "e" and self._saida.qsize() > 6:
            return
        self._saida.put(msg)

    def mensagens(self) -> list:
        """Todas as mensagens que chegaram desde a última vez."""
        lista = []
        while True:
            try:
                lista.append(self._entrada.get_nowait())
            except queue.Empty:
                return lista

    def terminar(self):
        """Despede-se do outro jogador e fecha a ligação logo a seguir (sem o jogo esperar)."""
        if self.ativa:
            self._saida.put({"t": "adeus"})
            self._saida.put("fechar")

    def fechar(self, erro: str = ""):
        if self.ativa and erro:
            self.erro = erro
        self.ativa = False
        self._saida.put(None)               # acorda a thread de envio para ela acabar
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    # ------------------------------------------------------------------ #
    def _receber_exato(self, n: int) -> bytes:
        dados = b""
        while len(dados) < n:
            parte = self.sock.recv(n - len(dados))
            if not parte:
                raise ConnectionError("ligação fechada")
            dados += parte
        return dados

    def _ler(self):
        try:
            while self.ativa:
                (n,) = struct.unpack("!I", self._receber_exato(4))
                if n > 1_000_000:
                    raise ValueError("mensagem demasiado grande")
                self._entrada.put(json.loads(self._receber_exato(n).decode("utf-8")))
        except (OSError, ConnectionError, ValueError):
            self.fechar("A ligação ao outro jogador caiu.")

    def _escrever(self):
        try:
            while self.ativa:
                msg = self._saida.get()
                if msg is None:
                    break
                if msg == "fechar":
                    self.fechar()
                    break
                dados = json.dumps(msg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                self.sock.sendall(struct.pack("!I", len(dados)) + dados)
        except OSError:
            self.fechar("A ligação ao outro jogador caiu.")


class Anfitriao:
    """Abre a porta e espera que um convidado se ligue (numa thread, sem bloquear o jogo)."""

    def __init__(self, porta: int = PORTA):
        self.porta = porta
        self.ligacao = None
        self.erro = ""
        self._servidor = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", porta))
            s.listen(1)
            self._servidor = s
            threading.Thread(target=self._esperar, daemon=True).start()
        except OSError:
            self.erro = f"Não foi possível abrir a porta {porta} (já está a ser usada?)."

    def _esperar(self):
        try:
            sock, _ = self._servidor.accept()
        except OSError:
            return                          # cancelado (o servidor foi fechado)
        self.ligacao = Ligacao(sock)
        try:
            self._servidor.close()          # só aceitamos um convidado
        except OSError:
            pass

    def fechar(self):
        if self._servidor is not None:
            try:
                self._servidor.close()
            except OSError:
                pass
        if self.ligacao is not None:
            self.ligacao.fechar()


class Convidado:
    """Liga-se ao anfitrião numa thread. 'estado' passa de 'a_ligar' para 'ligado' ou 'erro'."""

    def __init__(self, endereco: str):
        self.estado = "a_ligar"
        self.erro = ""
        self.ligacao = None
        self._cancelado = False
        try:
            self.host, self.porta = separar_endereco(endereco)
        except ValueError as e:
            self.estado, self.erro = "erro", str(e)
            return
        threading.Thread(target=self._ligar, daemon=True).start()

    def _ligar(self):
        try:
            sock = socket.create_connection((self.host, self.porta), timeout=TEMPO_LIGAR)
        except socket.gaierror:
            self.estado, self.erro = "erro", "Endereço desconhecido. Confirma o que escreveste."
            return
        except (socket.timeout, TimeoutError):
            self.estado, self.erro = "erro", "O anfitrião não respondeu. A porta pode estar fechada (ver o README)."
            return
        except OSError:
            self.estado, self.erro = "erro", "Não foi possível ligar. O anfitrião já criou o jogo?"
            return
        if self._cancelado:
            sock.close()
            return
        self.ligacao = Ligacao(sock)
        self.estado = "ligado"

    def fechar(self):
        self._cancelado = True
        if self.ligacao is not None:
            self.ligacao.fechar()


def separar_endereco(texto: str) -> tuple[str, int]:
    """'192.168.1.5' ou '192.168.1.5:50555' ou 'xyz.joinmc.link:12345' -> (host, porta)."""
    texto = texto.strip()
    if not texto:
        raise ValueError("Escreve o endereço do anfitrião.")
    host, porta = texto, PORTA
    if texto.count(":") == 1:
        host, p = texto.split(":")
        if not p.isdigit() or not 0 < int(p) < 65536:
            raise ValueError("A porta (depois dos dois pontos) tem de ser um número.")
        porta = int(p)
    if not host:
        raise ValueError("Escreve o endereço do anfitrião.")
    return host, porta


def enderecos_locais() -> list[str]:
    """Os endereços IPv4 deste computador (rede de casa/escola, VPN como o Radmin, ...)."""
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    # O endereço que o PC usa para sair para a internet (não envia nada, só escolhe a rota)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip in ips:
            ips.remove(ip)
        ips.insert(0, ip)
    except OSError:
        pass
    # As VPN de jogos (Radmin 26.x, ZeroTier, Tailscale 100.x) primeiro: são as que servem pela internet
    ips.sort(key=lambda ip: 0 if ip.startswith(("26.", "100.")) else 1)
    return ips or ["127.0.0.1"]
