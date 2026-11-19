# -*- coding: utf-8 -*-
"""
dois_jogadores.py - dois jogadores no mesmo computador (jogo rápido).

O jogador 1 fica com a equipa da casa e o jogador 2 com a de fora. Os colegas e os guarda-redes
das duas equipas jogam no nível normal, para ser justo.

Controlos do jogador 2:
  - com um comando ligado, o jogador 2 usa o último comando (o jogador 1 joga com o teclado ou
    com o outro comando). Botões iguais aos do jogador 1: A passe, B remate, X trocar, Y finta,
    LB roleta, RB / gatilhos acelerar, START pausa;
  - sem comando, os dois jogam no mesmo teclado: o jogador 1 com WASD e as teclas da esquerda
    (Z, X, C, V, F, SHIFT esquerdo) e o jogador 2 com as setas e as teclas da direita
    (, passe  . remate  - finta  CTRL direito roleta  ENTER trocar  SHIFT direito acelerar).

O jogador 2 é controlado como o convidado do jogo online (online.py): o jogo guarda o que ele
carrega em _input_remoto / _acoes_remotas e o _online_controlar_remoto aplica-o ao jogador.
"""
import pygame

import comando
from remate_pov import RematePOV

NIVEL_2J = "normal"

# Teclado do jogador 2 (as do teclado numérico também servem)
TECLAS_J2 = {
    "passe": (pygame.K_COMMA, pygame.K_KP1),
    "remate": (pygame.K_PERIOD, pygame.K_KP2),
    "finta": (pygame.K_MINUS, pygame.K_SLASH, pygame.K_KP3),
    "roleta": (pygame.K_RCTRL, pygame.K_KP0),
    "trocar": (pygame.K_RETURN, pygame.K_KP_ENTER),
}
TECLA_ACAO_J2 = {k: acao for acao, teclas in TECLAS_J2.items() for k in teclas}
SETAS = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
WASD = (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)
BOTOES_J2 = {"a": "passe", "b": "remate", "x": "trocar", "y": "finta", "lb": "roleta",
             "start": "pausa", "back": "pausa"}


class DoisJogadoresMixin:

    def _dois_reiniciar(self):
        """Desliga o modo (no início de cada partida e ao sair para os menus)."""
        self.dois_jogadores = False
        self._j2_comando = False
        self._pov_j2 = False
        comando.reservar_j2(False)
        comando.mascarar(())

    def _dois_comecar(self):
        """Chamado logo a seguir ao iniciar_partida: o jogador 2 fica com a equipa de fora."""
        self.dois_jogadores = True
        self._j2_comando = comando.reservar_j2(True)
        self.dificuldade = NIVEL_2J            # (sem o aviso «Dificuldade da IA»)
        for a in self.agentes_vermelhos:
            a.definir_dificuldade(NIVEL_2J)
        self.gr_vermelho.definir_dificuldade(NIVEL_2J)
        remoto = list(self.equipa_vermelha)[0]
        self.agentes_vermelhos = [a for a in self.agentes_vermelhos if a.jogador is not remoto]
        remoto.humano = remoto.remoto = remoto.selecionado = True
        self.jogador_remoto = remoto
        self._input_remoto = (0, 0, False)
        self._acoes_remotas = []
        self._msg_texto = "2 JOGADORES  •  " + self._msg_texto
        self._dois_mascara()

    # ------------------------------------------------------------------ #
    # Ler o jogador 2 (uma vez por frame, no handle_events)                #
    # ------------------------------------------------------------------ #

    def _dois_mascara(self):
        """Teclas do teclado que o jogador 1 não pode usar (são do jogador 2), conforme o momento."""
        if self.remate_pov is not None and self._pov_j2:
            # Remate do jogador 2: o teclado do jogador 1 não mexe na mira
            comando.mascarar(WASD + (pygame.K_x, pygame.K_SPACE) +
                             (() if not self._j2_comando else SETAS + (pygame.K_RETURN,)))
        elif self._j2_comando:
            comando.mascarar(())
        else:
            comando.mascarar(SETAS + (pygame.K_RSHIFT,) + tuple(TECLA_ACAO_J2))

    def _dois_ler(self):
        """Movimento e botões do jogador 2 (do comando dele ou do lado direito do teclado)."""
        self._dois_mascara()
        a_jogar = self.jogo_ativo and not self.pausado and not self.fim_jogo and self.remate_pov is None
        if self._j2_comando:
            dx, dy, sprint, novos = comando.j2()
            acoes = [BOTOES_J2[b] for b in novos if b in BOTOES_J2]
        else:
            k = pygame.key.get_pressed()
            dx = int(k[pygame.K_RIGHT]) - int(k[pygame.K_LEFT])
            dy = int(k[pygame.K_DOWN]) - int(k[pygame.K_UP])
            sprint = bool(k[pygame.K_RSHIFT])
            acoes = []                            # as teclas chegam como eventos (_dois_evento)
        self._input_remoto = (dx, dy, sprint) if a_jogar else (0, 0, False)
        if a_jogar:
            for a in acoes:
                self._dois_acao(a)

    def _dois_evento(self, event) -> bool:
        """Teclas do jogador 2 no teclado. Devolve True se o evento era dele."""
        if self._j2_comando or event.type != pygame.KEYDOWN or getattr(event, "comando", False):
            return False
        acao = TECLA_ACAO_J2.get(event.key)
        if acao is None:
            return False
        self._dois_acao(acao)
        return True

    def _dois_acao(self, acao: str):
        if acao == "pausa":
            self.abrir_pausa()
            return
        bp = self._bola_parada
        j = self.jogador_remoto
        if bp is not None:
            # Jogo parado numa falta: o jogador 2 só joga se for ele a marcar o livre
            if bp["tipo"] == "livre" and bp["marcador"] is j and j.tem_bola:
                if acao == "passe":
                    self._acao_passe(j)
                elif acao == "remate":
                    self._dois_remate()
            return
        if acao == "remate":
            self._dois_remate()
        else:
            self._acoes_remotas.append((acao, None, None))

    # ------------------------------------------------------------------ #
    # Remate do jogador 2 (ataca a baliza da direita)                      #
    # ------------------------------------------------------------------ #

    def _dois_remate(self, defensores=None, limite: float = 5.0):
        j = self.jogador_remoto
        if j is None or not j.tem_bola or self.remate_pov is not None or not self.jogo_ativo:
            return
        if self.rink.linha_golo_dir_x - j.pos_x < 30:
            self._remate_rapido(j)              # atrás da linha de golo não se vê a baliza
            return
        self.remate_pov = RematePOV(self.screen, self.rink, j, self.gr_azul, NIVEL_2J, limite_tempo=limite,
                                    cor_linhas=self.rink.cor_linhas,
                                    defensores=list(self.equipa_azul) if defensores is None else defensores,
                                    velocidade=(j.vel_x, j.vel_y), placar=self._placar_pov(), baliza="dir")
        self._pov_j2 = True
        self._dois_mascara()

    def _dois_eventos_pov(self, event):
        """No remate de um dos jogadores, só as teclas de quem remata contam."""
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            return None if self._pov_j2 else event
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return event
        do_comando = getattr(event, "comando", False)
        if self._pov_j2:
            if self._j2_comando:
                return event if do_comando or event.key == pygame.K_ESCAPE else None
            if event.key in TECLAS_J2["remate"]:   # a tecla de remate do jogador 2 faz de X
                return pygame.event.Event(event.type, key=pygame.K_x, mod=0, unicode="", scancode=0)
            return event if event.key in SETAS + (pygame.K_ESCAPE,) else None
        # Remate do jogador 1: as teclas do jogador 2 não contam
        if not self._j2_comando and (event.key in TECLA_ACAO_J2 or event.key in SETAS):
            return None
        return event

    def _dois_fechar_pov(self) -> bool:
        """O remate acabou: se era do jogador 2, aplica-o na baliza da direita. True se tratou."""
        if not self._pov_j2:
            return False
        self._pov_j2 = False
        self._aplicar_remate(self.remate_pov.resultado, self.jogador_remoto, "dir")
        self._dois_mascara()
        return True

    # ------------------------------------------------------------------ #
    # Faltas e cartões                                                     #
    # ------------------------------------------------------------------ #

    def _dois_bola_parada(self, marcador) -> str | None:
        """
        Bola parada da equipa do jogador 2: passa a controlar quem a marca.
        Devolve "livre" se o jogador 2 escolhe o que fazer, "penalti" se abriu o remate, ou None.
        """
        if not self.dois_jogadores or marcador.equipa != "vermelho":
            return None
        if marcador is not self.jogador_remoto:
            self._trocar_remoto(marcador)
        bp = self._bola_parada
        if bp is not None and bp["tipo"] == "livre":
            dx, dy, _ = self._input_remoto
            if dx or dy:
                marcador.vetor_direcao = pygame.math.Vector2(dx, dy).normalize()
                marcador._olhar_para(marcador.vetor_direcao)
            return "livre"
        self._dois_remate(defensores=[], limite=6.0)
        return "penalti"

    def _dois_cartao(self, j):
        """O jogador do jogador 2 levou cartão: o controlo passa para o colega mais perto."""
        if not self.dois_jogadores or j is not self.jogador_remoto:
            return
        outros = [c for c in self.equipa_vermelha if c is not j]
        if outros:
            self._trocar_remoto(min(outros, key=lambda c: (c.pos_x - j.pos_x) ** 2 + (c.pos_y - j.pos_y) ** 2))

    # ------------------------------------------------------------------ #
    # Desenho                                                              #
    # ------------------------------------------------------------------ #

    def _desenhar_dois(self, screen):
        """«J1» e «J2» por cima dos jogadores controlados."""
        if not self.dois_jogadores:
            return
        from componentes import texto
        cam = self.rink.camera
        for j, nome, cor in ((self.jogador_humano, "J1", (40, 120, 230)),
                             (self.jogador_remoto, "J2", (220, 70, 60))):
            if j is None or not j.alive():
                continue
            sx, sy = cam.projetar(j.pos_x, j.pos_y)
            caixa = pygame.Rect(0, 0, 30, 18)
            caixa.midbottom = (round(sx), round(sy) - round(72 * cam.escala(j.pos_y)))
            pygame.draw.rect(screen, (10, 14, 24), caixa.inflate(4, 4), border_radius=7)
            pygame.draw.rect(screen, cor, caixa, border_radius=6)
            texto(screen, nome, 13, (255, 255, 255), caixa.center)
