# -*- coding: utf-8 -*-
"""
conta.py - a conta do jogador no jogo (o servidor está em servidor/contas.py).

  - ContaLocal: o que fica guardado no PC (conta.json, na pasta dos jogos gravados): a alcunha,
    o token da sessão (nunca a palavra-passe) e o estado da sincronização de cada conta.
  - ContaMixin: junta ao Game o ecrã da conta (conta_menu.py) e o progresso na nuvem.

Progresso na nuvem: as carreiras são ficheiros SQLite (carreira.db e carreira_jogador.db).
São comprimidos (zlib) e enviados em base64. Depois de este PC estar "sincronizado" com a conta,
sempre que um destes ficheiros muda (no fim de um jogo da carreira), é enviado sozinho, em fundo,
quando se está nos menus. Antes de trazer um progresso da nuvem, o ficheiro do PC é guardado
como cópia (.antes_da_nuvem).

Na primeira vez que se entra num PC:
  - se a nuvem não tem nada, este PC fica sincronizado (passa a enviar);
  - se a nuvem tem progresso e o PC não, traz-se logo da nuvem;
  - se os dois têm, o jogador escolhe no ecrã da conta (para não se perder nada sem querer).
"""
import base64
import json
import os
import shutil
import time
import zlib

import pygame

from carreira import CAMINHO_BD, PASTA_SAVES
from carreira_jogador import CAMINHO_BD_JOGADOR
from rede import Servidor

FICHEIRO = os.path.join(PASTA_SAVES, "conta.json")
FICHEIROS_SAVE = {"carreira": CAMINHO_BD, "carreira_jogador": CAMINHO_BD_JOGADOR}
NOMES_SAVE = {"carreira": "Modo carreira", "carreira_jogador": "Carreira de jogador"}
VERIFICAR_S = 4.0            # de quanto em quanto tempo se vê se os ficheiros mudaram
DESISTIR_S = 150.0           # se o envio em fundo não acabar (sem internet), desiste


class ContaLocal:
    def __init__(self, ficheiro: str = FICHEIRO):
        self.ficheiro = ficheiro
        self.alcunha = None
        self.token = None
        self.perfil = None           # último perfil recebido (para o menu mostrar logo)
        self.sinc = {}               # alcunha (minúsculas) -> {"ok", "versoes", "mtimes"}
        try:
            with open(ficheiro, encoding="utf-8") as f:
                d = json.load(f)
            self.alcunha, self.token = d.get("alcunha"), d.get("token")
            self.perfil, self.sinc = d.get("perfil"), d.get("sinc", {})
        except (OSError, ValueError, AttributeError):
            pass

    def gravar(self):
        try:
            os.makedirs(os.path.dirname(self.ficheiro), exist_ok=True)
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump({"alcunha": self.alcunha, "token": self.token, "perfil": self.perfil,
                           "sinc": self.sinc}, f, ensure_ascii=False)
        except OSError:
            pass

    @property
    def ligada(self) -> bool:
        return bool(self.token)

    def entrou(self, alcunha: str, token: str, perfil: dict):
        self.alcunha, self.token, self.perfil = alcunha, token, perfil
        self.gravar()

    def saiu(self):
        self.token = None
        self.perfil = None
        self.gravar()

    def estado_sinc(self) -> dict:
        return self.sinc.setdefault((self.alcunha or "").lower(), {"ok": False, "versoes": {}, "mtimes": {}})

    # ------------------------------------------------------------------ ficheiros
    @staticmethod
    def existe(tipo: str) -> bool:
        return os.path.exists(FICHEIROS_SAVE[tipo])

    @staticmethod
    def mtime(tipo: str) -> float:
        try:
            return os.path.getmtime(FICHEIROS_SAVE[tipo])
        except OSError:
            return 0.0

    @staticmethod
    def ler(tipo: str) -> str | None:
        try:
            with open(FICHEIROS_SAVE[tipo], "rb") as f:
                return base64.b64encode(zlib.compress(f.read(), 9)).decode("ascii")
        except OSError:
            return None

    @staticmethod
    def escrever(tipo: str, dados: str):
        caminho = FICHEIROS_SAVE[tipo]
        bruto = zlib.decompress(base64.b64decode(dados))
        if not bruto.startswith(b"SQLite format 3"):
            raise ValueError("o progresso da nuvem não é uma base de dados")
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        if os.path.exists(caminho):
            shutil.copy2(caminho, caminho + ".antes_da_nuvem")
        temp = caminho + ".novo"
        with open(temp, "wb") as f:
            f.write(bruto)
        os.replace(temp, caminho)


def data_curta(t: float | int | None) -> str:
    if not t:
        return "—"
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(t))


class ContaMixin:

    def _conta_iniciar(self):
        self.conta = ContaLocal()
        self.ecra_conta = None
        self._conta_pedidos = {}         # pedido -> (o que é, dados)
        self._nuvem_srv = None           # ligação só para os envios em fundo
        self._nuvem_pedidos = {}         # pedido -> (tipo, mtime, versao)
        self._nuvem_t = 0.0
        self._nuvem_inicio = 0.0
        self._nuvem_ultimo = ""          # aviso do último envio (para o ecrã da conta)
        self._resultado_enviado = False  # jogo online: resultado enviado para o ranking
        self._desafio_pid = None         # pedido de desafio a um amigo (online.py)

    # ------------------------------------------------------------------ servidor
    def _conta_srv(self) -> Servidor:
        """A ligação ao servidor (a mesma do jogo online), com a sessão da conta."""
        return self._online_servidor()

    def _fechar_carreiras(self):
        """Fecha as bases de dados das carreiras (antes de as trocar pelas da nuvem)."""
        for nome in ("carreira", "carreira_jog"):
            obj = getattr(self, nome, None)
            if obj is not None:
                try:
                    obj.fechar()
                except Exception:
                    pass
                setattr(self, nome, None)

    # ------------------------------------------------------------------ ecrã da conta
    def abrir_conta(self):
        from conta_menu import EcraConta
        self.estado = "conta"
        self.ecra_conta = EcraConta(self.screen, arena=self.rink._surf, conta=self.conta)
        self._conta_pedidos = {}
        if self.conta.ligada:
            srv = self._conta_srv()
            self.ecra_conta.servidor = srv
            self._conta_pedir("versoes", "nuvem_versoes")
        else:
            self.ecra_conta.servidor = self._conta_srv()

    def _conta_pedir(self, oque: str, tipo_msg: str, extra=None, /, **dados):
        pid = self._conta_srv().pedir(tipo_msg, **dados)
        self._conta_pedidos[pid] = (oque, extra)
        if self.ecra_conta is not None:
            self.ecra_conta.ocupado = True
        return pid

    def _conta_eventos(self):
        ecra = self.ecra_conta
        for event in pygame.event.get():
            acao = ecra.handle_event(event)
            self._som_acao(acao if isinstance(acao, str) else (acao[0] if acao else None))
            if acao is None:
                continue
            nome = acao[0] if isinstance(acao, tuple) else acao
            if nome == "sair":
                self._online_fechar_rede()
                self.running = False
                return
            if nome == "voltar":
                self.ir_para_menu_principal()
                return
            if ecra.ocupado and nome in ("entrar", "criar", "recuperar", "enviar_nuvem", "trazer_nuvem"):
                continue                     # à espera de uma resposta do servidor
            ecra.erro = ecra.info = ""
            if nome == "entrar":
                _, alcunha, senha = acao
                self._conta_pedir("entrou", "conta_entrar", alcunha=alcunha, senha=senha)
            elif nome == "criar":
                _, alcunha, senha, senha2 = acao
                if senha != senha2:
                    ecra.erro = "As duas palavras-passe não são iguais."
                    continue
                self._conta_pedir("entrou", "conta_criar", alcunha=alcunha, senha=senha)
            elif nome == "recuperar":
                _, alcunha, codigo, senha = acao
                self._conta_pedir("entrou", "conta_recuperar", alcunha=alcunha, codigo=codigo, senha=senha)
            elif nome == "sair_conta":
                if self.conta.token:
                    self._conta_srv().pedir("conta_sair", token=self.conta.token)
                self.conta.saiu()
                self._online_fechar_rede()          # a ligação estava com a sessão antiga
                self.abrir_conta()
                self.ecra_conta.info = "Saíste da conta neste computador."
            elif nome == "enviar_nuvem":
                self._nuvem_enviar_tudo(manual=True)
            elif nome == "trazer_nuvem":
                self._conta_pedir("trazer", "nuvem_versoes")
            elif nome == "ranking":
                ecra.mudar_fase("ranking")
                self._conta_pedir("ranking", "ranking")
                self._conta_pedir("historico", "historico")
            elif nome in ("voltar_dentro", "continuar"):
                ecra.mudar_fase("dentro" if self.conta.ligada else "fora")
                if self.conta.ligada:
                    self._conta_pedir("versoes", "nuvem_versoes")

    def _conta_update(self, dt: float):
        ecra = self.ecra_conta
        ecra.update(dt)
        srv = self._servidor
        if srv is None:
            return
        if srv.sessao_erro and self.conta.ligada:
            # O token já não serve (ex.: recuperou a palavra-passe noutro PC)
            self.conta.saiu()
            srv.sessao_erro = ""
            ecra.mudar_fase("fora")
            ecra.erro = "A sessão terminou. Entra outra vez na tua conta."
        if srv.perfil and self.conta.ligada and srv.perfil != self.conta.perfil:
            self.conta.perfil = srv.perfil
            self.conta.gravar()
        if srv.estado == "erro" and self._conta_pedidos:
            self._conta_pedidos.clear()
            ecra.ocupado = False
            ecra.erro = srv.erro
        for pid in list(self._conta_pedidos):
            r = srv.resposta(pid)
            if r is None:
                continue
            oque, extra = self._conta_pedidos.pop(pid)
            ecra.ocupado = bool(self._conta_pedidos)
            if not r.get("ok"):
                ecra.erro = r.get("erro", "Não foi possível.")
                continue
            self._conta_resposta(oque, extra, r)

    def _conta_resposta(self, oque, extra, r: dict):
        ecra = self.ecra_conta
        if oque == "entrou":
            perfil = r["perfil"]
            self.conta.entrou(perfil["alcunha"], r["token"], perfil)
            ecra.limpar_campos()
            if r.get("recuperacao"):
                ecra.codigo_rec = r["recuperacao"]
                ecra.mudar_fase("codigo")
            else:
                ecra.mudar_fase("dentro")
            self._conta_pedir("primeira", "nuvem_versoes")
        elif oque in ("versoes", "primeira", "trazer"):
            versoes = r.get("versoes", {})
            ecra.versoes_nuvem = versoes
            sinc = self.conta.estado_sinc()
            if oque == "primeira" and not sinc["ok"]:
                locais = [t for t in versoes if self.conta.existe(t)]
                if not versoes:
                    sinc["ok"] = True                     # nuvem vazia: este PC passa a enviar
                    self._nuvem_t = VERIFICAR_S
                elif not locais:
                    oque = "trazer"                       # o PC não tem nada: traz da nuvem
                else:
                    ecra.escolher = True                  # os dois têm progresso: o jogador escolhe
                self.conta.gravar()
            if oque == "trazer":
                if not versoes:
                    ecra.info = "Ainda não há progresso guardado na nuvem."
                for tipo in versoes:
                    self._conta_pedir("carregado", "nuvem_carregar", tipo, tipo=tipo)
        elif oque == "carregado":
            try:
                self._fechar_carreiras()
                ContaLocal.escrever(r["tipo"], r["dados"])
            except (OSError, ValueError, zlib.error) as e:
                ecra.erro = f"Não foi possível trazer o progresso: {e}"
                return
            sinc = self.conta.estado_sinc()
            sinc["ok"] = True
            sinc["versoes"][r["tipo"]] = r["versao"]
            sinc["mtimes"][r["tipo"]] = ContaLocal.mtime(r["tipo"])
            self.conta.gravar()
            ecra.escolher = False
            ecra.info = f"{NOMES_SAVE[r['tipo']]}: trouxeste o progresso da nuvem para este PC."
        elif oque == "enviado":
            tipo, mtime = extra
            sinc = self.conta.estado_sinc()
            sinc["ok"] = True
            sinc["versoes"][tipo] = r["versao"]
            sinc["mtimes"][tipo] = mtime
            ecra.versoes_nuvem[tipo] = r["versao"]
            self.conta.gravar()
            ecra.escolher = False
            ecra.info = "O progresso deste PC ficou guardado na nuvem."
        elif oque == "ranking":
            ecra.ranking = r.get("lista", [])
            ecra.eu = r.get("eu")
        elif oque == "historico":
            ecra.historico = r.get("lista", [])

    # ------------------------------------------------------------------ progresso na nuvem
    def _nuvem_enviar_tudo(self, manual: bool = False):
        enviou = False
        for tipo in FICHEIROS_SAVE:
            dados = ContaLocal.ler(tipo)
            if dados is None:
                continue
            versao = int(time.time())
            self._conta_pedir("enviado", "nuvem_guardar", (tipo, ContaLocal.mtime(tipo)),
                              tipo=tipo, dados=dados, versao=versao)
            enviou = True
        if manual and not enviou:
            self.ecra_conta.info = "Ainda não tens progresso neste PC para guardar."

    def _nuvem_tick(self, dt: float):
        """Nos menus: se uma carreira mudou desde o último envio, envia-a em fundo."""
        srv = self._nuvem_srv
        if srv is not None:
            for pid in list(self._nuvem_pedidos):
                r = srv.resposta(pid)
                if r is None:
                    continue
                tipo, mtime, _v = self._nuvem_pedidos.pop(pid)
                if r.get("ok"):
                    sinc = self.conta.estado_sinc()
                    sinc["versoes"][tipo] = r["versao"]
                    sinc["mtimes"][tipo] = mtime
                    self.conta.gravar()
                    self._nuvem_ultimo = f"{NOMES_SAVE[tipo]} guardado na nuvem às {time.strftime('%H:%M')}"
            if srv.sessao_erro:
                self.conta.saiu()
                self._nuvem_pedidos.clear()
            if not self._nuvem_pedidos or srv.estado == "erro" or time.time() - self._nuvem_inicio > DESISTIR_S:
                srv.fechar()
                self._nuvem_srv = None
                self._nuvem_pedidos.clear()
            return
        self._nuvem_t += dt
        if self._nuvem_t < VERIFICAR_S or not self.conta.ligada:
            return
        self._nuvem_t = 0.0
        sinc = self.conta.estado_sinc()
        if not sinc["ok"]:
            return
        mudados = [t for t in FICHEIROS_SAVE
                   if ContaLocal.existe(t) and ContaLocal.mtime(t) > sinc["mtimes"].get(t, 0.0) + 0.5]
        if not mudados:
            return
        self._nuvem_srv = Servidor(token=self.conta.token)
        self._nuvem_inicio = time.time()
        for tipo in mudados:
            dados = ContaLocal.ler(tipo)
            if dados is None:
                continue
            v = int(time.time())
            pid = self._nuvem_srv.pedir("nuvem_guardar", tipo=tipo, dados=dados, versao=v)
            self._nuvem_pedidos[pid] = (tipo, ContaLocal.mtime(tipo), v)

    # ------------------------------------------------------------------ ranking no fim do jogo online
    def _desenhar_ranking_online(self, s):
        srv = self._servidor
        if srv is None or srv.ranking_mudou is None:
            return
        from componentes import texto
        delta, perfil = srv.ranking_mudou
        cor = (90, 230, 130) if delta > 0 else ((255, 120, 100) if delta < 0 else (220, 230, 250))
        txt = (f"RANKING:  {'+' if delta > 0 else ''}{delta} pontos  •  agora {perfil.get('pontos', '?')} "
               f"({perfil.get('posicao', '?')}.º lugar)")
        caixa = pygame.Rect(0, 0, 560, 40)
        caixa.midtop = (s.get_width() // 2, 76)
        pygame.draw.rect(s, (10, 16, 34), caixa, border_radius=20)
        pygame.draw.rect(s, cor, caixa, 2, border_radius=20)
        texto(s, txt, 17, cor, caixa.center)
