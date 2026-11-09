# -*- coding: utf-8 -*-
"""online.py - modo online (dois jogadores em computadores diferentes).

Os dois jogos encontram-se através do servidor do jogo (rede.py / servidor/servidor.py):
  - JOGO ALEATÓRIO: o servidor junta duas pessoas que estejam à procura (as equipas são sorteadas);
  - SALA PRIVADA: um cria a sala e recebe um código de 4 letras; o amigo entra com esse código.
Quem criou a sala (ou estava há mais tempo na fila) é o anfitrião.

Como funciona (modelo "anfitrião com autoridade"):
  - O ANFITRIÃO corre o jogo inteiro (física, IA, golos, faltas), como num jogo normal.
    Ele controla a equipa da casa; um jogador da equipa de fora é controlado à distância.
  - O CONVIDADO não simula nada: envia as teclas que carrega (mover, passe, remate, trocar)
    e recebe, 30 vezes por segundo, o "estado" do jogo (onde está cada jogador, a bola,
    o resultado, os sons e os efeitos). Depois desenha esse estado com o código de sempre.
  - Entre dois estados o convidado continua o movimento de cada jogador com a velocidade
    que recebeu e corrige aos poucos (suavização), para não se ver aos saltos.
  - O jogador do PRÓPRIO convidado não espera pela rede (previsão): mexe-se logo com as teclas
    dele e vai sendo corrigido aos poucos pela posição que o anfitrião envia. Sem isto, cada
    tecla só se via ao fim de uma ida e volta ao servidor (0,2 a 0,4 s) e o jogador parecia
    "preso". Para corrigir bem, cada envio de teclas leva um número; o anfitrião devolve o último
    número que recebeu, o que dá o tempo de ida e volta (RTT). A posição do anfitrião é comparada
    com a posição que o convidado tinha há RTT segundos.
  - Remate com mira (os dois jogadores): manter X enche a barra de força, aponta-se com o rato e
    larga-se o X (ou clica-se) para rematar. O jogo não pára, ao contrário do remate na primeira
    pessoa, que só existe no jogo normal.

Assim os dois veem sempre o mesmo jogo (só existe uma simulação: a do anfitrião).
O Game herda desta classe (class Game(OnlineMixin)).
"""
import math
import random
import time
from collections import deque

import pygame

from settings import *
from ai import AgentIA
from ball import REMATE_FORCA, SPIN_RATE
from carreira import FORCA_EQUIPAS
from menu import MenuPausa, EcraFimJogo
from online_menu import EcraOnline
from rede import Servidor, VERSAO
from remate_pov import MEIA_BOCA
from sons import som
from team import EQUIPAS_LISTA

ESTADOS_POR_SEGUNDO = 30
DIFICULDADE_ONLINE = "normal"   # colegas e guarda-redes das duas equipas jogam ao mesmo nível


class OnlineMixin:

    def _online_iniciar(self, definicoes: dict):
        self.online = None               # None, "anfitriao" ou "convidado"
        self._servidor = None            # rede.Servidor (enquanto se está no ecrã JOGAR ONLINE ou a jogar)
        self.ligacao = None              # rede.Ligacao ao outro jogador, depois de emparelhados
        self._online_modo = None         # "aleatorio" ou "privado"
        self.ecra_online = None
        self.jogador_remoto = None       # anfitrião: o jogador da equipa de fora que o convidado controla
        self._input_remoto = (0, 0, False)
        self._acoes_remotas = []
        self._rede_t = 0.0
        self._rede_eventos_bola = []
        self._rede_x = []                # acontecimentos especiais (golo) para o convidado
        self._lista_rede = []            # convidado: jogadores pela ordem das mensagens
        self._input_enviado = None
        self._input_t = 0.0
        self._input_seq_remoto = 0       # anfitrião: número do último envio de teclas recebido
        # Convidado: previsão do próprio jogador
        self._seq_input = 0              # número do próximo envio de teclas
        self._envios = {}                # número -> instante em que foi enviado
        self._ultimo_ack = 0
        self._rtt = 0.15                 # tempo de ida e volta estimado (s)
        self._hist_pred = deque()        # (instante, x, y) do jogador previsto
        self._erro_pred = [0.0, 0.0]     # correção que falta aplicar aos poucos
        self._pred_jogador = None
        # Remate com mira (os dois)
        self._online_mira = False
        self._mira_rato0 = None

    # ================================================================== #
    # Ecrã "Jogar online"                                               #
    # ================================================================== #

    def abrir_online(self, erro: str = ""):
        self._online_largar_jogo()
        self.pausado = False
        self.jogo_ativo = False
        self.fim_jogo = False
        self.estado = "online"
        self.ecra_online = EcraOnline(self.screen, arena=self.rink._surf, servidor=self._online_servidor(),
                                      erro=erro)

    def _online_servidor(self) -> Servidor:
        """A ligação ao servidor do jogo (abre outra se ainda não há ou se caiu)."""
        if self._servidor is None or self._servidor.estado == "erro":
            if self._servidor is not None:
                self._servidor.fechar()
            self._servidor = Servidor()
            if self.ecra_online is not None:
                self.ecra_online.servidor = self._servidor
        return self._servidor

    def _online_eventos_ecra(self):
        ecra = self.ecra_online
        for event in pygame.event.get():
            acao = ecra.handle_event(event)
            self._som_acao(acao)
            if acao in ("aleatorio", "criar"):
                srv = self._online_servidor()
                if acao == "aleatorio":
                    srv.procurar()
                    ecra.mudar_fase("procurar")
                else:
                    srv.criar_sala()
                    ecra.mudar_fase("criar")
                ecra.erro = ""
            elif acao == "entrar":
                ecra.erro = ""
                ecra.mudar_fase("entrar")
            elif isinstance(acao, tuple) and acao[0] == "ligar":
                codigo = acao[1]
                if len(codigo) != 4:
                    ecra.erro = "O código tem 4 letras."
                    continue
                self._online_servidor().entrar_sala(codigo)
                ecra.erro = ""
                ecra.mudar_fase("a_ligar")
            elif acao == "cancelar":
                if self._servidor is not None:
                    self._servidor.cancelar()
                ecra.mudar_fase("inicio")
            elif acao == "voltar":
                self.ir_para_menu_principal()
                return
            elif acao == "sair":
                self._online_fechar_rede()
                self.running = False

    # ================================================================== #
    # Ligação: chamado no início de cada frame                            #
    # ================================================================== #

    def _online_tick(self, dt: float):
        if self.ligacao is None:
            if self._servidor is not None and self.estado == "online":
                self._online_esperar_adversario()
            return
        # Primeiro as mensagens que já chegaram (a última pode ser o "adeus" do outro jogador)
        ligacao = self.ligacao
        for msg in ligacao.mensagens():
            self._online_mensagem(msg)
            if self.ligacao is not ligacao:      # a ligação acabou a meio (ex.: "adeus")
                return
        if not ligacao.ativa:
            self._online_terminar(ligacao.erro or "O outro jogador saiu do jogo.")
            return
        if self.estado == "jogo":
            self._online_atualizar_mira(dt)
        if self.online == "anfitriao" and self.estado == "jogo":
            self._online_enviar_estado(dt)

    def _online_esperar_adversario(self):
        """No ecrã JOGAR ONLINE: vê se o servidor já encontrou adversário (ou se deu erro)."""
        srv, ecra = self._servidor, self.ecra_online
        if srv.aviso:                                # ex.: não existe sala com esse código
            ecra.erro, srv.aviso = srv.aviso, ""
            ecra.mudar_fase("entrar")
            return
        if srv.estado == "erro":
            if ecra.fase != "inicio":
                ecra.erro = srv.erro
                ecra.mudar_fase("inicio")
            return
        par = srv.tomar_emparelhamento()
        if par is None:
            return
        papel, self._online_modo = par
        self.online, self.ligacao = papel, srv.ligacao
        self.ligacao.enviar({"t": "ola", "versao": VERSAO})
        som.ui("confirmar")
        if papel == "convidado":
            ecra.modo = self._online_modo
            ecra.mudar_fase("espera")
        elif self._online_modo == "aleatorio":
            casa, fora = random.sample(EQUIPAS_LISTA, 2)     # jogo aleatório: equipas sorteadas
            self._online_comecar(casa, fora)
        else:
            self._online_abrir_sala()                # sala privada: o anfitrião escolhe as equipas

    def _online_mensagem(self, msg: dict):
        t = msg.get("t")
        if t == "ola":
            if msg.get("versao") != VERSAO:
                self._online_terminar("O outro jogador tem outra versão do jogo. Atualizem os dois.")
        elif t == "adeus":
            self._online_terminar("O outro jogador saiu do jogo.")
        elif self.online == "anfitriao":
            if t == "in":
                n = msg.get("n", 0)
                if n >= self._input_seq_remoto:          # ignora teclas antigas que cheguem atrasadas
                    dx, dy, sp = msg["d"]
                    self._input_remoto = (max(-1, min(1, dx)), max(-1, min(1, dy)), bool(sp))
                    self._input_seq_remoto = n
            elif t == "acao" and msg.get("a") in ("passe", "remate", "trocar"):
                self._acoes_remotas.append((msg["a"], msg.get("d"), msg.get("f")))
        else:
            if t == "inicio":
                self.iniciar_partida(msg["casa"], msg["fora"])
                self._online_preparar_convidado()
            elif t == "sala":
                # O anfitrião voltou à escolha das equipas: o convidado fica à espera
                self.pausado = self.fim_jogo = self.jogo_ativo = False
                self.estado = "online"
                self.ecra_online = EcraOnline(self.screen, arena=self.rink._surf, servidor=self._servidor)
                self.ecra_online.modo = "privado"
                self.ecra_online.mudar_fase("espera")
            elif t == "e" and self.estado == "jogo":
                self._online_aplicar_estado(msg)

    def _online_largar_jogo(self):
        """Sai do jogo com o outro jogador (despedindo-se dele), mas fica ligado ao servidor."""
        if self.ligacao is not None:
            self.ligacao.terminar()              # envia "adeus" ao outro jogador
        if self._servidor is not None:
            self._servidor.ligacao = None
        self.ligacao = None
        self.online = None
        self._online_modo = None
        self.jogador_remoto = None
        som.gravacao = None

    def _online_fechar_rede(self):
        """Sai do modo online: larga o jogo e fecha a ligação ao servidor."""
        self._online_largar_jogo()
        if self._servidor is not None:
            self._servidor.fechar()
            self._servidor = None

    def _online_sair(self):
        """O próprio jogador saiu (pausa → abandonar, ou no fim do jogo)."""
        self.abrir_online()

    def _online_terminar(self, erro: str):
        """A ligação acabou do outro lado: volta ao ecrã online com a explicação."""
        self.abrir_online(erro)

    # ================================================================== #
    # ANFITRIÃO                                                           #
    # ================================================================== #

    def _online_abrir_sala(self):
        """Escolha das equipas (só o anfitrião escolhe). O convidado fica à espera."""
        self.abrir_selecao_equipas()
        if self.ligacao is not None:
            self.ligacao.enviar({"t": "sala"})

    def _online_comecar(self, casa_id: str, fora_id: str):
        self.iniciar_partida(casa_id, fora_id)
        self.modo_carreira = False
        # As duas equipas iguais: colegas e guarda-redes no mesmo nível
        for a in self.agentes_vermelhos:
            a.definir_dificuldade(DIFICULDADE_ONLINE)
        self.gr_vermelho.definir_dificuldade(DIFICULDADE_ONLINE)
        # O convidado controla o primeiro jogador da equipa de fora
        remoto = list(self.equipa_vermelha)[0]
        self.agentes_vermelhos = [a for a in self.agentes_vermelhos if a.jogador is not remoto]
        remoto.humano = remoto.remoto = remoto.selecionado = True
        self.jogador_remoto = remoto
        self._input_remoto = (0, 0, False)
        self._input_seq_remoto = 0
        self._acoes_remotas = []
        self._online_mira = False
        som.gravacao = []
        self._rede_eventos_bola = []
        self._rede_x = []
        self._rede_t = 1.0                       # envia o primeiro estado logo
        self._msg_texto = "JOGO ONLINE  •  " + self._msg_texto
        self.ligacao.enviar({"t": "inicio", "casa": casa_id, "fora": fora_id})

    def _online_controlar_remoto(self):
        """Aplica ao jogador da equipa de fora os comandos que chegaram do convidado."""
        j = self.jogador_remoto
        if j is None:
            return
        dx, dy, sprint = self._input_remoto
        j.aplicar_controlo(dx, dy, sprint)
        for a, direcao, forca in self._acoes_remotas:
            if a == "passe":
                self._acao_passe(self.jogador_remoto)
            elif a == "remate":
                if direcao is not None and forca is not None:
                    self._remate_mira(self.jogador_remoto, direcao, forca)
                else:
                    self._remate_rapido(self.jogador_remoto)
            elif a == "trocar":
                self._trocar_remoto_proximo()
        self._acoes_remotas.clear()
        self._auto_selecionar_remoto()

    def _trocar_remoto(self, novo):
        """O controlo do convidado passa para outro jogador da equipa de fora (o antigo volta à IA)."""
        antigo = self.jogador_remoto
        if novo is antigo or antigo is None:
            return
        antigo.humano = antigo.remoto = antigo.selecionado = False
        antigo.set_target(0.0, 0.0)
        papel = getattr(antigo, "papel", "avancado")
        pos_base = getattr(antigo, "pos_tatica", self._pos_tatica_verm(papel, (antigo.pos_x, antigo.pos_y)))
        agente = AgentIA(antigo, papel, "vermelho", pos_base, self.rink.baliza_esq, self.rink.baliza_dir,
                         dificuldade=DIFICULDADE_ONLINE, gr_adversario=self.gr_azul)
        agente.definir_forca(FORCA_EQUIPAS.get(self.equipa_fora_id, 79))
        self.agentes_vermelhos = [a for a in self.agentes_vermelhos if a.jogador is not novo] + [agente]
        novo.humano = novo.remoto = novo.selecionado = True
        self.jogador_remoto = novo

    def _trocar_remoto_proximo(self):
        r = self.jogador_remoto
        outros = [j for j in self.equipa_vermelha if j is not r]
        if outros:
            b = self.bola
            self._trocar_remoto(min(outros, key=lambda j: math.hypot(j.pos_x - b.pos_x, j.pos_y - b.pos_y)))

    def _auto_selecionar_remoto(self):
        """Igual ao _auto_selecionar da equipa da casa, mas para o jogador do convidado."""
        b, r = self.bola, self.jogador_remoto
        if b.dono is not None:
            if b.dono in self.equipa_vermelha and b.dono is not r:
                self._trocar_remoto(b.dono)
            return
        if r.tem_bola or b.vel.length() > 220:
            return
        melhor, melhor_d = r, math.hypot(r.pos_x - b.pos_x, r.pos_y - b.pos_y)
        for j in self.equipa_vermelha:
            if j is not r:
                d = math.hypot(j.pos_x - b.pos_x, j.pos_y - b.pos_y)
                if d < melhor_d - 80:
                    melhor, melhor_d = j, d
        if melhor is not r:
            self._trocar_remoto(melhor)

    def _remate_rapido(self, j):
        """
        Online não há o ecrã do remate na primeira pessoa (pararia o jogo do outro jogador).
        O remate vai direto à baliza: para cima ou para baixo conforme a seta que se está a carregar.
        """
        if not self.jogo_ativo or not j.tem_bola:
            return
        r = self.rink
        gx = r.linha_golo_esq_x if j.equipa == "azul" else r.linha_golo_dir_x
        cy = r.rect.centery
        mira = max(-1.0, min(1.0, j.vetor_direcao.y))
        alvo_y = cy + mira * MEIA_BOCA * 0.8 + random.uniform(-12, 12)
        v = pygame.math.Vector2(gx - j.pos_x, alvo_y - j.pos_y)
        if v.length_squared() == 0:
            return
        forca = REMATE_FORCA * random.uniform(0.82, 1.0)
        j.fazer_remate_com_forca(self.bola, v.normalize(), forca)

    def _remate_mira(self, j, direcao, forca: float):
        """Remate com mira: direção escolhida com o rato e força da barra (0 a 1)."""
        if not self.jogo_ativo or not j.tem_bola:
            return
        try:
            v = pygame.math.Vector2(float(direcao[0]), float(direcao[1]))
            forca = max(0.0, min(1.0, float(forca)))
        except (TypeError, ValueError, IndexError):
            return
        if v.length_squared() < 1e-6:
            return
        # Igual ao remate com mira do jogo normal: entre 30 % e 100 % da força máxima
        j.fazer_remate_com_forca(self.bola, v.normalize(), (0.30 + 0.70 * forca) * REMATE_FORCA)

    def _online_enviar_estado(self, dt: float):
        self._rede_t += dt
        if self._rede_t < 1.0 / ESTADOS_POR_SEGUNDO:
            return
        self._rede_t = 0.0
        lista = list(self.equipa_azul) + list(self.equipa_vermelha)
        indice = {p: i for i, p in enumerate(lista)}
        b = self.bola

        def r(v):
            return round(float(v), 1)

        msg = {
            "t": "e",
            "j": [[r(p.pos_x), r(p.pos_y), r(p.vel_x), r(p.vel_y), round(p.vetor_direcao.x, 2),
                   round(p.vetor_direcao.y, 2), p._estado_action or "", round(p._action_timer, 2),
                   int(p.tem_bola), int(p.selecionado), int(p._sprint_ativo)] for p in lista],
            "g": [[r(g.pos_y), r(g.vel_y), round(g._defender_timer, 2)] for g in (self.gr_azul, self.gr_vermelho)],
            "b": [r(b.pos_x), r(b.pos_y), r(b.vel.x), r(b.vel.y), indice.get(b.dono, -1)],
            "p": [self.golos_azul, self.golos_vermelho, self.faltas_azul, self.faltas_vermelho,
                  r(self.tempo_restante), self.parte],
            "m": [self._msg_texto, r(self._msg_timer), getattr(self, "_msg_equipa", "azul")],
            "f": [int(self._falta_ativa), r(self._falta_timer), self._falta_tipo, self._msg_falta,
                  self._msg_falta_sub],
            "s": list(som.gravacao or []),
            "ev": [[t, r(f), r(x), r(y)] for t, f, x, y in self._rede_eventos_bola],
            "x": list(self._rede_x),
            "fim": int(self.fim_jogo),
            "n": self._input_seq_remoto,         # último envio de teclas do convidado (para o RTT)
        }
        if self.fim_jogo:
            msg["mc"] = self.marcadores
        self.ligacao.enviar(msg)
        if som.gravacao is not None:
            som.gravacao.clear()
        self._rede_eventos_bola.clear()
        self._rede_x.clear()

    # ================================================================== #
    # CONVIDADO                                                           #
    # ================================================================== #

    def _online_preparar_convidado(self):
        self.modo_carreira = False
        self.agentes_azul, self.agentes_vermelhos = [], []
        self._lista_rede = list(self.equipa_azul) + list(self.equipa_vermelha)
        for p in self._lista_rede:
            p.humano = p.selecionado = False
            p._rede = None
        self.jogador_humano = list(self.equipa_vermelha)[0]
        self.jogador_humano.selecionado = True
        self.bola._rede = None
        self._input_enviado = None
        self._input_t = 0.0
        # (o número dos envios de teclas nunca volta a 0: assim o anfitrião nunca o confunde
        # com um envio antigo de outro jogo)
        self._envios.clear()
        self._hist_pred.clear()
        self._erro_pred = [0.0, 0.0]
        self._pred_jogador = None
        self._online_mira = False
        self._msg_texto = "JOGO ONLINE  •  " + self._msg_texto

    def _online_aplicar_estado(self, msg: dict):
        agora = time.perf_counter()
        # Tempo de ida e volta: o anfitrião devolve o número do último envio de teclas que recebeu
        n = msg.get("n", 0)
        if n > self._ultimo_ack and n in self._envios:
            amostra = agora - self._envios[n]
            self._rtt = max(0.02, min(1.0, self._rtt * 0.8 + amostra * 0.2))
            self._ultimo_ack = n
        for p, d in zip(self._lista_rede, msg["j"]):
            x, y, vx, vy, dx, dy, acao, t_acao, tb, sel, sp = d
            if sel and p.equipa == "vermelho":
                self.jogador_humano = p
            if p._rede is None:                      # primeiro estado: põe logo no sítio
                p.pos_x, p.pos_y = x, y
            p._rede = (x, y, vx, vy, agora)
            p.tem_bola, p.selecionado = bool(tb), bool(sel)
            if acao and p._estado_action != acao:
                p._comecar_acao(acao, t_acao)
            if p is self.jogador_humano:
                self._corrigir_previsao(p, x, y, agora)
                continue                             # o próprio jogador mexe-se com as teclas locais
            p.vel_x, p.vel_y = vx, vy
            p._target_vx, p._target_vy = vx, vy
            p._sprint_ativo = bool(sp)
            if dx or dy:
                p.vetor_direcao.update(dx, dy)
        for g, (y, vy, t_def) in zip((self.gr_azul, self.gr_vermelho), msg["g"]):
            g._rede_y, g.vel_y, g._defender_timer = y, vy, t_def
        bx, by, bvx, bvy, dono = msg["b"]
        b = self.bola
        b.vel.update(bvx, bvy)
        b.dono = self._lista_rede[dono] if 0 <= dono < len(self._lista_rede) else None
        if b._rede is None:
            b.pos_x, b.pos_y = bx, by
        b._rede = (bx, by, agora)
        if b.dono is not None and b.dono._rede is not None:
            b._offset_dono = (bx - b.dono._rede[0], by - b.dono._rede[1])

        (self.golos_azul, self.golos_vermelho, self.faltas_azul, self.faltas_vermelho,
         self.tempo_restante, self.parte) = msg["p"]
        self._msg_texto, self._msg_timer, self._msg_equipa = msg["m"]
        falta_ativa, self._falta_timer, self._falta_tipo, self._msg_falta, self._msg_falta_sub = msg["f"]
        self._falta_ativa = bool(falta_ativa)

        # Sons e efeitos do que aconteceu desde o último estado
        for nome, volume, x in msg["s"]:
            som.tocar(nome, volume, x)
        cam = self.rink.camera
        for tipo, forca, x, y in msg["ev"]:
            sx, sy = cam.projetar(x, y)
            self._efeitos_bola(tipo, forca, sx, sy)
        for ev in msg["x"]:
            if ev[0] == "golo":
                self._festa_golo(ev[1], ev[2])

        if msg.get("fim") and not self.fim_jogo:
            self.marcadores = msg.get("mc", [])
            self.pausado = False
            self.jogo_ativo = False
            self.fim_jogo = True
            self.ecra_fim = EcraFimJogo(self.screen, online="convidado")

    # Erro a partir do qual o jogador previsto salta logo para a posição do anfitrião
    # (reposição depois de um golo, falta, choque forte)
    _SALTO_PREVISAO = 110

    def _corrigir_previsao(self, p, x: float, y: float, agora: float):
        """
        Compara a posição que o anfitrião enviou com a posição que o jogador previsto tinha há
        RTT segundos (é essa que o anfitrião já conhece) e guarda a diferença para a corrigir aos poucos.
        """
        if p is not self._pred_jogador:
            # Passou a controlar outro jogador: começa no sítio que o anfitrião diz
            self._pred_jogador = p
            self._hist_pred.clear()
            self._erro_pred = [0.0, 0.0]
            p.pos_x, p.pos_y = x, y
            return
        alvo = agora - self._rtt
        hx, hy = p.pos_x, p.pos_y
        for t, px, py in self._hist_pred:            # posição prevista mais perto desse instante
            hx, hy = px, py
            if t >= alvo:
                break
        self._erro_pred = [x - hx, y - hy]
        if math.hypot(*self._erro_pred) > self._SALTO_PREVISAO:
            p.pos_x += self._erro_pred[0]
            p.pos_y += self._erro_pred[1]
            self._erro_pred = [0.0, 0.0]
            self._hist_pred.clear()

    def _teclas_movimento(self):
        """(dx, dy, sprint) das teclas que se estão a carregar (0 se o jogo está parado)."""
        if self.pausado or self.fim_jogo:
            return 0, 0, False
        k = pygame.key.get_pressed()
        dx = int(k[pygame.K_RIGHT] or k[pygame.K_d]) - int(k[pygame.K_LEFT] or k[pygame.K_a])
        dy = int(k[pygame.K_DOWN] or k[pygame.K_s]) - int(k[pygame.K_UP] or k[pygame.K_w])
        return dx, dy, bool(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT])

    def _mover_previsto(self, p, dt: float, agora: float):
        """O jogador do convidado: anda logo com as teclas e é corrigido aos poucos pelo anfitrião."""
        if self._falta_ativa:
            # Numa falta o anfitrião põe os jogadores no sítio: segue-o sem prever
            x, y = p._rede[0], p._rede[1]
            p.vel_x = p.vel_y = 0.0
            p.pos_x += (x - p.pos_x) * min(1.0, dt * 10)
            p.pos_y += (y - p.pos_y) * min(1.0, dt * 10)
            self._hist_pred.clear()
            self._erro_pred = [0.0, 0.0]
        else:
            p.aplicar_controlo(*self._teclas_movimento())
            p._aplicar_inercia(dt)
            p._mover(dt, self.rink.rect, self.rink)
            # Correção aos poucos (cerca de 1/6 de segundo), para não se notar
            k = min(1.0, dt * 6)
            cx, cy = self._erro_pred[0] * k, self._erro_pred[1] * k
            p.pos_x += cx
            p.pos_y += cy
            self._erro_pred[0] -= cx
            self._erro_pred[1] -= cy
            if cx or cy:
                # O caminho guardado também é corrigido: senão, no estado seguinte, a mesma
                # diferença voltava a ser contada e o jogador passava do sítio certo
                self._hist_pred = deque((t, x + cx, y + cy) for t, x, y in self._hist_pred)
            self._hist_pred.append((agora, p.pos_x, p.pos_y))
            while self._hist_pred and self._hist_pred[0][0] < agora - 1.5:
                self._hist_pred.popleft()
        p.rect.center = (round(p.pos_x), round(p.pos_y))
        p._atualizar_animacao(dt)

    def _update_convidado(self, dt: float):
        if self.pausado:
            self.menu_pausa.update(dt)
        if self.fim_jogo:
            self.ecra_fim.update(dt)
        self.efeitos.tempo(dt)                 # só para as partículas e textos andarem
        self._online_enviar_input(dt)
        self._online_suavizar(dt)
        self._efeitos_posse()
        if self._msg_timer > 0:
            self._msg_timer -= dt

    def _online_enviar_input(self, dt: float):
        dx, dy, sprint = estado = self._teclas_movimento()
        self._input_t += dt
        # Envia logo que muda e, de 0,1 em 0,1 s, outra vez (para o caso de se perder alguma
        # coisa e para medir o tempo de ida e volta)
        if estado != self._input_enviado or self._input_t > 0.1:
            self._seq_input += 1
            agora = time.perf_counter()
            self._envios[self._seq_input] = agora
            if len(self._envios) > 60:                    # esquece os envios antigos
                for n in [n for n, t in self._envios.items() if t < agora - 2.0]:
                    del self._envios[n]
            self.ligacao.enviar({"t": "in", "d": [dx, dy, int(sprint)], "n": self._seq_input})
            self._input_enviado, self._input_t = estado, 0.0

    def _online_suavizar(self, dt: float):
        """Põe cada jogador e a bola no sítio, a partir do último estado recebido, sem saltos."""
        agora = time.perf_counter()
        k = min(1.0, dt * 14)
        for p in self._lista_rede:
            if p._rede is None:
                continue
            if p is self.jogador_humano and p is self._pred_jogador:
                self._mover_previsto(p, dt, agora)
                continue
            x, y, vx, vy, t0 = p._rede
            adiantar = min(agora - t0, 0.12)          # continua o movimento entre dois estados
            tx, ty = x + vx * adiantar, y + vy * adiantar
            if math.hypot(tx - p.pos_x, ty - p.pos_y) > 120:
                p.pos_x, p.pos_y = tx, ty               # muito longe (ex.: reposição): salta
            else:
                p.pos_x += (tx - p.pos_x) * k
                p.pos_y += (ty - p.pos_y) * k
            p.rect.center = (round(p.pos_x), round(p.pos_y))
            p._atualizar_animacao(dt)
        for g in (self.gr_azul, self.gr_vermelho):
            if hasattr(g, "_rede_y"):
                g.pos_y += (g._rede_y - g.pos_y) * k
                g._atualizar_animacao(dt, self.bola)
        b = self.bola
        if b._rede is None:
            return
        bx, by, t0 = b._rede
        if b.dono is not None:
            ox, oy = getattr(b, "_offset_dono", (0.0, 0.0))
            b.pos_x, b.pos_y = b.dono.pos_x + ox, b.dono.pos_y + oy
        else:
            adiantar = min(agora - t0, 0.12)
            tx, ty = bx + b.vel.x * adiantar, by + b.vel.y * adiantar
            if math.hypot(tx - b.pos_x, ty - b.pos_y) > 90:
                b.pos_x, b.pos_y = tx, ty
            else:
                kb = min(1.0, dt * 22)
                b.pos_x += (tx - b.pos_x) * kb
                b.pos_y += (ty - b.pos_y) * kb
            b._angulo = (b._angulo + b.vel.length() * dt * SPIN_RATE) % 360.0
            b.image = pygame.transform.rotate(b._imagem_base, b._angulo)
        b.rect = b.image.get_rect(center=(round(b.pos_x), round(b.pos_y)))

    # ================================================================== #
    # Teclas durante um jogo online (anfitrião e convidado)              #
    # ================================================================== #

    # ------------------------------------------------------------------ #
    # Remate com mira (manter X, apontar com o rato, largar)              #
    # ------------------------------------------------------------------ #

    def _online_iniciar_mira(self):
        j = self.jogador_humano
        if self._online_mira or j is None or not j.tem_bola or self.pausado or self.fim_jogo:
            return
        self._online_mira = True
        self._mira_forca, self._mira_forca_dir = 0.0, 1.0
        self._mira_rato0 = pygame.mouse.get_pos()
        # Até se mexer o rato, aponta ao meio da baliza adversária
        r = self.rink
        gx = r.linha_golo_esq_x if j.equipa == "azul" else r.linha_golo_dir_x
        v = pygame.math.Vector2(gx - j.pos_x, r.rect.centery - j.pos_y)
        self._mira_direcao = v.normalize() if v.length_squared() > 0 else pygame.math.Vector2(1, 0)

    def _online_atualizar_mira(self, dt: float):
        """Barra de força a subir e descer e direção pelo rato (o jogo continua: não há câmara lenta)."""
        if not self._online_mira:
            return
        j = self.jogador_humano
        if j is None or not j.tem_bola or self.pausado or self.fim_jogo:
            self._online_mira = False                # perdeu a bola: cancela
            return
        rato = pygame.mouse.get_pos()
        if rato != self._mira_rato0:
            mx, my = self.rink.camera.desprojetar(*rato)
            v = pygame.math.Vector2(mx - j.pos_x, my - j.pos_y)
            if v.length_squared() > 10:
                self._mira_direcao = v.normalize()
        self._mira_forca += self._mira_forca_dir * self._mira_vel * dt
        if self._mira_forca >= 1.0:
            self._mira_forca, self._mira_forca_dir = 1.0, -1.0
        elif self._mira_forca <= 0.0:
            self._mira_forca, self._mira_forca_dir = 0.0, 1.0

    def _online_rematar_mira(self):
        if not self._online_mira:
            return
        self._online_mira = False
        d, f = self._mira_direcao, self._mira_forca
        if self.online == "convidado":
            self.ligacao.enviar({"t": "acao", "a": "remate", "d": [round(d.x, 3), round(d.y, 3)],
                                 "f": round(f, 3)})
        else:
            self._remate_mira(self.jogador_humano, (d.x, d.y), f)

    def _online_acao(self, acao: str):
        if self.online == "convidado":
            self.ligacao.enviar({"t": "acao", "a": acao})
        elif acao == "passe":
            self._acao_passe()
        elif acao == "remate":
            self._remate_rapido(self.jogador_humano)
        elif acao == "trocar":
            self._selecionar_jogador_proximo()

    def _online_eventos_jogo(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._online_fechar_rede()
                self.running = False
                return
            if self.pausado:
                acao = self.menu_pausa.handle_event(event)
                self._som_acao(acao)
                if acao == "continuar":
                    self.pausado = False
                elif acao == "menu":
                    self._online_sair()
                    return
                elif acao == "sair":
                    self._online_fechar_rede()
                    self.running = False
                    return
                continue
            if self.fim_jogo:
                acao = self.ecra_fim.handle_event(event)
                self._som_acao(acao)
                if acao == "menu":
                    self._online_sair()
                    return
                if acao == "sair":
                    self._online_fechar_rede()
                    self.running = False
                    return
                if self.online == "anfitriao" and acao == "reiniciar":
                    self._online_comecar(self.equipa_casa_id, self.equipa_fora_id)
                    return
                if self.online == "anfitriao" and acao == "equipas":
                    self._online_abrir_sala()
                    return
                continue
            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE and self._online_mira:
                    self._online_mira = False            # ESC com a mira aberta só cancela o remate
                elif k in (pygame.K_ESCAPE, pygame.K_p, pygame.K_m):
                    self._online_mira = False
                    self.pausado = True
                    self.menu_pausa = MenuPausa(self.screen, modo_online=True)
                elif k == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif k == pygame.K_z:
                    self._online_acao("passe")
                elif k == pygame.K_x:
                    self._online_iniciar_mira()          # manter X: mira e força
                elif k in (pygame.K_TAB, pygame.K_c, pygame.K_SPACE):
                    self._online_acao("trocar")
            elif event.type == pygame.KEYUP and event.key == pygame.K_x:
                self._online_rematar_mira()              # largar X: remata
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._online_mira:
                    self._online_rematar_mira()          # ou clicar
                    continue
                if event.pos[0] >= WIDTH - 56 and event.pos[1] <= 56:
                    self.pausado = True
                    self.menu_pausa = MenuPausa(self.screen, modo_online=True)
                    continue
                for chave, btn in self.hud.btn_rects.items():
                    if btn["rect"].collidepoint(event.pos):
                        self._online_acao({"passe": "passe", "remate": "remate"}.get(chave, "trocar"))
                        break
