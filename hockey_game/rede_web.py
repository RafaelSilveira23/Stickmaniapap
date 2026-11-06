"""rede_web.py - ligação do modo online na versão do browser (WebRTC com PeerJS).

No browser não se podem abrir ligações TCP (o rede.py não funciona). Os browsers têm o WebRTC,
que liga dois browsers diretamente um ao outro. Para se encontrarem é preciso um "intermediário"
que só troca os dados iniciais da ligação: usa-se o servidor público e gratuito do PeerJS.

Em vez de um endereço IP, o anfitrião recebe um CÓDIGO de 4 letras (ex.: K7QZ). O convidado
escreve esse código e o PeerJS põe os dois browsers em contacto. Depois disso as mensagens vão
diretamente de um browser para o outro.

O código em JavaScript (em baixo) é posto na página pelo Python; o jogo chama-o com
platform.window.eval(...) e lê as mensagens recebidas em cada frame (como no rede.py, nada
fica à espera da rede). As classes têm a mesma "interface" das do rede.py, por isso o
online.py funciona igual no computador e no browser.
"""
import json

PREFIXO = "stickmania-pap-v1-"
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # sem O/0 nem I/1, para não se confundirem
TEMPO_LIGAR = 15.0

_JS = r"""
window.stickRede = window.stickRede || (function () {
  const R = {estado: "", erro: "", fila: [], conn: null, peer: null, t0: 0};
  const PREF = "%PREFIXO%";
  function carregar(cb) {
    if (window.Peer) { cb(); return; }
    const s = document.createElement("script");
    s.src = "https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js";
    s.onload = cb;
    s.onerror = function () { R.estado = "erro"; R.erro = "sem_peerjs"; };
    document.head.appendChild(s);
  }
  function usar(c) {
    R.conn = c;
    c.on("open", function () { R.estado = "ligado"; });
    c.on("data", function (d) { R.fila.push(String(d)); });
    c.on("close", function () { if (R.estado !== "fechado") R.estado = "caiu"; });
    c.on("error", function (e) { R.estado = "caiu"; R.erro = String(e); });
  }
  R.fechar = function () {
    R.estado = "fechado";
    try { if (R.conn) R.conn.close(); } catch (e) {}
    try { if (R.peer) R.peer.destroy(); } catch (e) {}
    R.conn = null; R.peer = null;
  };
  R.limpar = function () { R.fechar(); R.estado = ""; R.erro = ""; R.fila = []; };
  R.criar = function (codigo) {
    R.limpar(); R.estado = "a_preparar";
    carregar(function () {
      const p = new Peer(PREF + codigo, {debug: 0});
      R.peer = p;
      p.on("open", function () { if (R.estado === "a_preparar") R.estado = "espera"; });
      p.on("connection", function (c) {
        if (R.conn) { c.close(); return; }          // só um convidado
        usar(c);
      });
      p.on("error", function (e) {
        if (R.estado === "ligado") return;
        R.estado = "erro"; R.erro = e.type || String(e);
      });
    });
  };
  R.entrar = function (codigo) {
    R.limpar(); R.estado = "a_ligar"; R.t0 = Date.now();
    carregar(function () {
      const p = new Peer({debug: 0});
      R.peer = p;
      p.on("open", function () {
        usar(p.connect(PREF + codigo, {reliable: true, serialization: "raw"}));
      });
      p.on("error", function (e) {
        if (R.estado === "ligado") { R.estado = "caiu"; return; }
        R.estado = "erro"; R.erro = e.type || String(e);
      });
    });
  };
  R.enviar = function (txt) { if (R.conn && R.conn.open) R.conn.send(txt); };
  R.receber = function () { const f = R.fila; R.fila = []; return JSON.stringify(f); };
  R.terminar = function () {
    try { R.enviar(JSON.stringify({t: "adeus"})); } catch (e) {}
    setTimeout(R.fechar, 400);
  };
  R.info = function () { return JSON.stringify([R.estado, R.erro]); };
  return R;
})();
""".replace("%PREFIXO%", PREFIXO)

ERROS = {
    "sem_peerjs": "Não foi possível preparar a ligação (há internet?).",
    "peer-unavailable": "Não existe nenhum jogo com esse código. Confirma as letras.",
    "unavailable-id": "codigo_ocupado",
    "network": "Sem ligação ao servidor de ligações (há internet?).",
    "server-error": "O servidor de ligações não respondeu. Tenta outra vez daqui a pouco.",
    "browser-incompatible": "Este browser não suporta jogo online. Usa o Chrome, o Edge ou o Firefox.",
}


def _js(codigo: str):
    import platform          # no pygbag, platform.window é a janela do browser (JavaScript)
    return platform.window.eval(codigo)


def _preparar():
    _js(_JS)


def _info() -> tuple[str, str]:
    estado, erro = json.loads(str(_js("stickRede.info()")))
    return estado, erro


def _erro_legivel(erro: str) -> str:
    return ERROS.get(erro, "Não foi possível ligar ao outro jogador (" + erro + ").")


def novo_codigo() -> str:
    # O Math.random do browser garante códigos diferentes mesmo que o Python comece sempre igual
    n = int(float(_js("Math.random()")) * len(LETRAS) ** 4)
    letras = ""
    for _ in range(4):
        n, i = divmod(n, len(LETRAS))
        letras += LETRAS[i]
    return letras


class LigacaoWeb:
    """Igual à rede.Ligacao: enviar(dict), mensagens(), ativa, erro, terminar(), fechar()."""

    def __init__(self):
        self.erro = ""
        self._fechada = False

    @property
    def ativa(self) -> bool:
        if self._fechada:
            return False
        estado, _ = _info()
        if estado != "ligado":
            self.erro = "A ligação ao outro jogador caiu."
            return False
        return True

    def enviar(self, msg: dict):
        if not self._fechada:
            _js("stickRede.enviar(" + json.dumps(json.dumps(msg, separators=(",", ":"))) + ")")

    def mensagens(self) -> list:
        if self._fechada:
            return []
        return [json.loads(m) for m in json.loads(str(_js("stickRede.receber()")))]

    def terminar(self):
        if not self._fechada:
            self._fechada = True
            _js("stickRede.terminar()")

    def fechar(self, erro: str = ""):
        if erro:
            self.erro = erro
        self._fechada = True
        _js("stickRede.fechar()")


class AnfitriaoWeb:
    """Cria o jogo com um código. 'pronto' fica True quando o código já está registado."""

    def __init__(self):
        self.erro = ""
        self.codigo = novo_codigo()
        self._ligacao = None
        self._tentativas = 0
        try:
            _preparar()
            _js(f"stickRede.criar('{self.codigo}')")
        except Exception as e:                       # sem JavaScript (não devia acontecer no browser)
            self.erro = f"O jogo online não está disponível aqui ({e})."

    @property
    def pronto(self) -> bool:
        return _info()[0] in ("espera", "ligado")

    @property
    def ligacao(self):
        if self._ligacao is None and not self.erro:
            estado, erro = _info()
            if estado == "ligado":
                self._ligacao = LigacaoWeb()
            elif estado == "erro":
                if ERROS.get(erro) == "codigo_ocupado" and self._tentativas < 5:
                    # Por azar o código já estava a ser usado: escolhe outro
                    self._tentativas += 1
                    self.codigo = novo_codigo()
                    _js(f"stickRede.criar('{self.codigo}')")
                else:
                    self.erro = _erro_legivel(erro)
        return self._ligacao

    def fechar(self):
        _js("stickRede.fechar()")


class ConvidadoWeb:
    """Entra no jogo com o código. 'estado' passa de 'a_ligar' para 'ligado' ou 'erro'."""

    def __init__(self, codigo: str):
        self._estado = "a_ligar"
        self.erro = ""
        self.ligacao = None
        codigo = "".join(c for c in codigo.upper() if c in LETRAS)
        if len(codigo) != 4:
            self._estado, self.erro = "erro", "O código tem 4 letras ou números (ex.: K7QZ)."
            return
        try:
            _preparar()
            _js(f"stickRede.entrar('{codigo}')")
            self._t0 = float(_js("Date.now()"))
        except Exception as e:
            self._estado, self.erro = "erro", f"O jogo online não está disponível aqui ({e})."

    @property
    def estado(self) -> str:
        if self._estado == "a_ligar":
            estado, erro = _info()
            if estado == "ligado":
                self.ligacao = LigacaoWeb()
                self._estado = "ligado"
            elif estado in ("erro", "caiu"):
                self._estado, self.erro = "erro", _erro_legivel(erro)
                _js("stickRede.fechar()")
            elif float(_js("Date.now()")) - self._t0 > TEMPO_LIGAR * 1000:
                self._estado = "erro"
                self.erro = "O anfitrião não respondeu. A rede de um dos dois pode estar a bloquear a ligação."
                _js("stickRede.fechar()")
        return self._estado

    def fechar(self):
        _js("stickRede.fechar()")
