# -*- coding: utf-8 -*-
"""game.py - game loop com IA real, posicionamento tático, mini-mapa e cartão de jogador."""
import os
import math
import pygame
from settings import *
from rink import Rink
from player import Player
from ball import Ball
from ai import AgentIA
from goalkeeper import Goalkeeper
from ui import HUDController
from team import EQUIPAS_LISTA, obter_info_equipa
from menu import TeamSelectMenu

DURACAO_PARTE = 60 * 5   # 5 minutos por parte


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_num = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 44, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 26, bold=True)

        self.equipa_casa_id = "fc_porto"
        self.equipa_fora_id = "riba_dave"

        self.rink = Rink(equipa_casa=self.equipa_casa_id)
        self.hud  = HUDController()

        # ── Criar jogadores e agentes IA ─────────────────────────────────
        self._criar_equipas()

        # ── Bola ─────────────────────────────────────────────────────────
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola = Ball((cx, cy))
        self.sprites_bola = pygame.sprite.GroupSingle(self.bola)

        # Jogador humano começa com a bola
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # ── Estado do jogo e Menu de Seleção ─────────────────────────────
        self.estado         = "menu_selecao"  # "menu_selecao" ou "jogo"
        self.menu           = TeamSelectMenu(self.screen, self.equipa_casa_id, self.equipa_fora_id)

        self.golos_azul     = 0
        self.golos_vermelho = 0
        self.parte          = 1
        self.tempo_restante = float(DURACAO_PARTE)
        self.jogo_ativo     = False
        self.fim_jogo       = False
        self._msg_texto     = ""
        self._msg_timer     = 0.0

        # ── Sistema de Mira de Remate ────────────────────────────────────
        self._mira_ativa        = False      # True quando está em modo de mira
        self._mira_forca        = 0.0       # 0.0 a 1.0 — posição atual da barra
        self._mira_forca_dir    = 1.0       # direção da oscilação (+1 ou -1)
        self._mira_vel          = 1.2       # velocidade de oscilação da barra (ciclos/s)
        self._mira_direcao      = pygame.math.Vector2(1, 0)  # direção apontada
        self._mira_confirmada   = False

        self.running    = True
        self.show_debug = False

    # ================================================================== #
    # Criação das equipas com posições táticas e atributos                #
    # ================================================================== #

    def _criar_equipas(self):
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        r  = self.rink

        bal_prop_azul = r.baliza_dir
        bal_adv_azul  = r.baliza_esq
        bal_prop_verm = r.baliza_esq
        bal_adv_verm  = r.baliza_dir

        # ── Equipa Azul (FC Porto) — lado direito ────────────────────────
        # (pos, papel, numero, nome, (vel, rem, pas, def))
        dados_azul = [
            ((cx + 70,  cy),       "avancado", 10, "Silva", (88, 85, 76, 58)),
            ((cx + 200, cy - 90),  "avancado",  9, "Costa", (84, 88, 72, 55)),
            ((cx + 200, cy + 90),  "medio",     8, "Ramos", (80, 78, 88, 74)),
            ((cx + 360, cy - 70),  "defesa",    4, "Faria", (76, 68, 78, 87)),
            ((cx + 360, cy + 70),  "defesa",    5, "Neves", (74, 62, 74, 90)),
        ]

        self.equipa_azul    = pygame.sprite.Group()
        self.agentes_azul   = []
        self.jogador_humano = None

        for i, (pos, papel, num, nome, stats) in enumerate(dados_azul):
            humano = (i == 0)
            p = Player("azul", pos, numero=num, nome=nome, humano=humano, teclas="wasd")
            p.equipa_id       = self.equipa_casa_id
            p.papel           = papel
            p.stat_velocidade = stats[0]
            p.stat_remate     = stats[1]
            p.stat_passe      = stats[2]
            p.stat_defesa     = stats[3]
            pos_base          = self._pos_tatica_azul(papel, pos)
            p.pos_tatica      = pos_base

            self.equipa_azul.add(p)
            if humano:
                self.jogador_humano = p
                p.selecionado = True
            else:
                agente = AgentIA(p, papel, "azul", pos_base,
                                 bal_prop_azul, bal_adv_azul)
                self.agentes_azul.append(agente)

        # ── Equipa Vermelha (Riba d'Ave) — lado esquerdo (toda IA) ───────
        dados_verm = [
            ((cx - 70,  cy),       "avancado",  9, "López",  (86, 86, 74, 56)),
            ((cx - 200, cy - 90),  "avancado", 10, "García", (83, 87, 70, 54)),
            ((cx - 200, cy + 90),  "medio",     8, "Martín", (79, 76, 85, 72)),
            ((cx - 360, cy - 70),  "defesa",    4, "Pérez",  (75, 66, 76, 86)),
            ((cx - 360, cy + 70),  "defesa",    5, "Ruiz",   (73, 60, 72, 88)),
        ]

        self.equipa_vermelha   = pygame.sprite.Group()
        self.agentes_vermelhos = []
        self.jogador_humano2   = None

        for pos, papel, num, nome, stats in dados_verm:
            p = Player("vermelho", pos, numero=num, nome=nome, humano=False)
            p.equipa_id       = self.equipa_fora_id
            p.papel           = papel
            p.stat_velocidade = stats[0]
            p.stat_remate     = stats[1]
            p.stat_passe      = stats[2]
            p.stat_defesa     = stats[3]
            pos_base          = self._pos_tatica_verm(papel, pos)
            p.pos_tatica      = pos_base

            self.equipa_vermelha.add(p)
            agente = AgentIA(p, papel, "vermelho", pos_base,
                             bal_prop_verm, bal_adv_verm)
            self.agentes_vermelhos.append(agente)

        self.todos_jogadores = pygame.sprite.Group(
            *self.equipa_azul, *self.equipa_vermelha
        )

        # ── Guarda-redes (posicionados sobre as linhas de golo) ──────────
        self.gr_azul = Goalkeeper(
            equipa="azul", lado="dir",
            baliza_rect=r.zona_gr_dir,
            pos_x_fixo=r.linha_golo_dir_x - 4
        )
        self.gr_vermelho = Goalkeeper(
            equipa="vermelho", lado="esq",
            baliza_rect=r.zona_gr_esq,
            pos_x_fixo=r.linha_golo_esq_x + 4
        )
        self.grupo_gr = pygame.sprite.Group(self.gr_azul, self.gr_vermelho)

    def _pos_tatica_azul(self, papel: str, pos_inicial: tuple) -> tuple:
        cx = RINK_X + RINK_W // 2
        if papel == "avancado":
            return (cx + 90, pos_inicial[1])
        elif papel == "medio":
            return (cx + 220, pos_inicial[1])
        else:
            return (cx + 360, pos_inicial[1])

    def _pos_tatica_verm(self, papel: str, pos_inicial: tuple) -> tuple:
        cx = RINK_X + RINK_W // 2
        if papel == "avancado":
            return (cx - 90, pos_inicial[1])
        elif papel == "medio":
            return (cx - 220, pos_inicial[1])
        else:
            return (cx - 360, pos_inicial[1])

    # ================================================================== #
    # Game Loop                                                            #
    # ================================================================== #

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    # ================================================================== #
    # Eventos                                                              #
    # ================================================================== #

    def handle_events(self):
        if self.estado == "menu_selecao":
            for event in pygame.event.get():
                res = self.menu.handle_event(event)
                if res == "iniciar":
                    c_id, f_id = self.menu.get_equipas()
                    self.iniciar_partida(c_id, f_id)
                elif res == "sair":
                    self.running = False
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_m):
                    self.voltar_ao_menu()
                elif event.key == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_z:
                    self._acao_passe()
                elif event.key == pygame.K_x:
                    self._acao_remate()
                elif event.key == pygame.K_ESCAPE and self._mira_ativa:
                    self._mira_ativa = False  # cancelar mira sem rematar
                elif event.key in (pygame.K_TAB, pygame.K_c, pygame.K_SPACE):
                    self._selecionar_jogador_proximo()
                elif event.key == pygame.K_r and self.fim_jogo:
                    self.iniciar_partida(self.equipa_casa_id, self.equipa_fora_id)
                elif event.key == pygame.K_t:
                    self.alternar_equipa_casa()
                elif event.key == pygame.K_y:
                    self.alternar_equipa_fora()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                   pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8):
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(EQUIPAS_LISTA):
                        self.mudar_equipa_casa(EQUIPAS_LISTA[idx])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Confirmar mira com clique esquerdo
                if self._mira_ativa and event.button == 1:
                    mpos = pygame.mouse.get_pos()
                    bx = round(self.jogador_humano.pos_x)
                    by = round(self.jogador_humano.pos_y)
                    v = pygame.math.Vector2(mpos[0] - bx, mpos[1] - by)
                    if v.length_squared() > 0:
                        self._mira_direcao = v.normalize()
                    self._confirmar_remate()
                    continue  # não processar clique noutros elementos
                # Botão de pausa superior direito (volta ao menu de seleção)
                if event.pos[0] >= WIDTH - 56 and event.pos[1] <= 56:
                    self.voltar_ao_menu()
                else:
                    self._tratar_clique_botoes(event.pos)

    def _tratar_clique_botoes(self, pos):
        for chave, btn in self.hud.btn_rects.items():
            if btn["rect"].collidepoint(pos):
                if chave == "passe":
                    self._acao_passe()
                elif chave == "remate":
                    self._acao_remate()
                elif chave in ("defender", "acelerar"):
                    self._selecionar_jogador_proximo()
                return

    # ================================================================== #
    # Ações do Jogador Humano                                              #
    # ================================================================== #

    def _direcao_vec(self, jogador=None) -> pygame.math.Vector2:
        if jogador is None:
            jogador = self.jogador_humano
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            return pygame.math.Vector2(jogador.vetor_direcao)
        mapa = {"direita":(1,0),"esquerda":(-1,0),"cima":(0,-1),"baixo":(0,1)}
        return pygame.math.Vector2(mapa.get(jogador.direcao, (-1, 0)))

    def _acao_passe(self):
        if self.jogador_humano.tem_bola and self.jogo_ativo:
            direcao = self._direcao_vec(self.jogador_humano)
            melhor_colega = None
            melhor_score = -1.0

            # Procura o colega azul mais bem posicionado na direção apontada
            for j in self.equipa_azul:
                if j == self.jogador_humano:
                    continue
                to_j = pygame.math.Vector2(j.pos_x - self.jogador_humano.pos_x,
                                           j.pos_y - self.jogador_humano.pos_y)
                dist = to_j.length()
                if 30 < dist < 500:
                    dot = direcao.dot(to_j.normalize())
                    if dot > 0.35:
                        score = dot * (1.0 - (dist / 1200.0))
                        if score > melhor_score:
                            melhor_score = score
                            melhor_colega = j

            if melhor_colega:
                dir_passe = pygame.math.Vector2(melhor_colega.pos_x - self.jogador_humano.pos_x,
                                                melhor_colega.pos_y - self.jogador_humano.pos_y).normalize()
                self.jogador_humano.fazer_passe(self.bola, dir_passe)
            else:
                self.jogador_humano.fazer_passe(self.bola, direcao)

    def _acao_remate(self):
        """Ao premir X: entra em modo de mira. Ao premir novamente: confirma e remata."""
        if not self.jogo_ativo:
            return
        if not self.jogador_humano.tem_bola:
            return

        if not self._mira_ativa:
            # Entrar em modo de mira
            self._mira_ativa     = True
            self._mira_forca     = 0.3
            self._mira_forca_dir = 1.0
            # Direção inicial: para a baliza adversária
            bx = self.jogador_humano.pos_x
            by = self.jogador_humano.pos_y
            # Equipa azul ataca para a esquerda; outros para a direita
            if self.jogador_humano.equipa == "azul":
                alvo_x = self.rink.linha_golo_esq_x
            else:
                alvo_x = self.rink.linha_golo_dir_x
            alvo_y = (self.rink.baliza_topo_y + self.rink.baliza_base_y) / 2
            v = pygame.math.Vector2(alvo_x - bx, alvo_y - by)
            if v.length_squared() > 0:
                self._mira_direcao = v.normalize()
        else:
            # Confirmar remate
            self._confirmar_remate()

    def _confirmar_remate(self):
        if not self._mira_ativa:
            return
        self._mira_ativa = False
        from ball import REMATE_FORCA
        # Força entre 30% e 100% da força máxima
        forca_real = (0.30 + self._mira_forca * 0.70) * REMATE_FORCA
        vec = pygame.math.Vector2(self._mira_direcao)
        if vec.length_squared() == 0:
            vec = pygame.math.Vector2(1, 0)
        self.jogador_humano.fazer_remate_com_forca(self.bola, vec.normalize(), forca_real)

    def _selecionar_jogador_proximo(self):
        """TAB / C: passa o controlo para o jogador azul mais perto da bola."""
        melhor = None
        melhor_dist = float("inf")
        for j in self.equipa_azul:
            if j.humano:
                continue
            d = math.hypot(j.pos_x - self.bola.pos_x, j.pos_y - self.bola.pos_y)
            if d < melhor_dist:
                melhor_dist = d
                melhor = j
        if melhor:
            self._trocar_humano(melhor)

    def _trocar_humano(self, novo: Player):
        if novo == self.jogador_humano:
            return

        antigo = self.jogador_humano
        antigo.humano      = False
        antigo.selecionado = False
        antigo.set_target(0.0, 0.0)

        papel    = getattr(antigo, "papel", "avancado")
        pos_base = getattr(antigo, "pos_tatica", self._pos_tatica_azul(papel, (antigo.pos_x, antigo.pos_y)))
        agente   = AgentIA(antigo, papel, "azul", pos_base,
                           self.rink.baliza_dir, self.rink.baliza_esq)
        self.agentes_azul.append(agente)

        self.agentes_azul = [a for a in self.agentes_azul if a.jogador != novo]
        novo.humano      = True
        novo.selecionado = True
        self.jogador_humano = novo

    # ================================================================== #
    # Update                                                               #
    # ================================================================== #

    def update(self, dt: float):
        if self.estado == "menu_selecao":
            self.menu.update(dt)
            return

        if not self.jogo_ativo:
            return

        # Cronómetro
        self.tempo_restante -= dt
        if self.tempo_restante <= 0:
            self._fim_de_parte()
            return

        # Modo de mira ativa: slow-motion e atualizar direção pelo rato
        if self._mira_ativa:
            dt_real = dt
            dt = dt_real * 0.15  # slow-motion durante a mira

            # Atualizar direção pelo rato em tempo real
            mpos = pygame.mouse.get_pos()
            bx = round(self.jogador_humano.pos_x)
            by = round(self.jogador_humano.pos_y)
            v = pygame.math.Vector2(mpos[0] - bx, mpos[1] - by)
            if v.length_squared() > 10:
                self._mira_direcao = v.normalize()

            # Oscilar a barra de força
            self._mira_forca += self._mira_forca_dir * self._mira_vel * dt_real
            if self._mira_forca >= 1.0:
                self._mira_forca = 1.0
                self._mira_forca_dir = -1.0
            elif self._mira_forca <= 0.0:
                self._mira_forca = 0.0
                self._mira_forca_dir = 1.0

        # Auto-seleção inteligente
        self._auto_selecionar()

        # IA Vermelha
        lista_verm = list(self.equipa_vermelha)
        lista_azul = list(self.equipa_azul)
        for agente in self.agentes_vermelhos:
            colegas = [j for j in lista_verm if j != agente.jogador]
            agente.update(dt, self.bola, colegas, lista_azul)

        # IA Azul (colegas de equipa)
        for agente in self.agentes_azul:
            colegas_com_humano = [j for j in lista_azul if j != agente.jogador]
            agente.update(dt, self.bola, colegas_com_humano, lista_verm)

        # Atualizar todos os jogadores (com colisão contra as balizas do campo)
        for j in self.todos_jogadores:
            j.update(dt, self.rink.rect, self.bola, self.rink)

        # Colisões físicas entre jogadores (separação + perda de bola)
        todos = list(self.todos_jogadores)
        for i in range(len(todos)):
            for k in range(i + 1, len(todos)):
                todos[i].empurrar_separar(todos[k], self.bola)

        # Atualizar bola (com física de tabelas e balizas)
        resultado = self.bola.update(dt, self.rink, todos_jogadores=todos)

        # Guarda-redes
        self.gr_azul.update(dt, self.bola)
        self.gr_vermelho.update(dt, self.bola)
        self.gr_azul.bloquear_bola(self.bola)
        self.gr_vermelho.bloquear_bola(self.bola)

        # Golos
        if resultado == "golo_azul":
            self._golo("azul")
        elif resultado == "golo_vermelho":
            self._golo("vermelho")

        if self._msg_timer > 0:
            self._msg_timer -= dt

    def _auto_selecionar(self):
        # Se um colega apanhou a bola, passa o controlo imediatamente para ele
        if self.bola.dono is not None:
            if self.bola.dono in self.equipa_azul and self.bola.dono != self.jogador_humano:
                self._trocar_humano(self.bola.dono)
            return

        if self.jogador_humano.tem_bola:
            return

        # Durante um remate ou passe rápido, não troca a meio da trajetória
        if self.bola.vel.length() > 220:
            return

        dist_humano = math.hypot(
            self.jogador_humano.pos_x - self.bola.pos_x,
            self.jogador_humano.pos_y - self.bola.pos_y
        )
        melhor = self.jogador_humano
        melhor_dist = dist_humano
        for j in self.equipa_azul:
            if j == self.jogador_humano:
                continue
            d = math.hypot(j.pos_x - self.bola.pos_x, j.pos_y - self.bola.pos_y)
            if d < melhor_dist - 80:
                melhor_dist = d
                melhor = j
        if melhor != self.jogador_humano:
            self._trocar_humano(melhor)

    # ------------------------------------------------------------------ #
    # Gestão e Alternância de Equipas                                     #
    # ------------------------------------------------------------------ #

    def iniciar_partida(self, casa_id: str, fora_id: str):
        """Inicia uma partida completa com as equipas selecionadas no menu."""
        self.equipa_casa_id = casa_id
        self.equipa_fora_id = fora_id

        # Atualizar o ringue com o emblema oficial da equipa da casa
        self.rink.definir_equipa_casa(self.equipa_casa_id)

        # Recriar os jogadores de campo e guarda-redes com as novas equipas
        self._criar_equipas()

        # Repor bola no centro e dar a posse ao jogador humano
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola.repor((cx, cy))
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # Reiniciar marcador e cronómetro
        self.golos_azul     = 0
        self.golos_vermelho = 0
        self.parte          = 1
        self.tempo_restante = float(DURACAO_PARTE)
        self.jogo_ativo     = True
        self.fim_jogo       = False
        self.estado         = "jogo"

        info_c = obter_info_equipa(casa_id)
        info_f = obter_info_equipa(fora_id)
        self._msg_texto     = f"{info_c['nome']}  vs  {info_f['nome']}"
        self._msg_timer     = 2.5

    def voltar_ao_menu(self):
        """Pausa o jogo e regressa ao ecrã de seleção de equipas."""
        self.estado = "menu_selecao"
        self.jogo_ativo = False
        self.menu = TeamSelectMenu(self.screen, self.equipa_casa_id, self.equipa_fora_id)

    def mudar_equipa_casa(self, equipa_id: str):
        self.equipa_casa_id = equipa_id
        self.rink.definir_equipa_casa(equipa_id)
        for j in self.equipa_azul:
            j.equipa_id = equipa_id
        info = obter_info_equipa(equipa_id)
        self._msg_texto = f"Equipa da Casa: {info['nome']}"
        self._msg_timer = 2.0

    def mudar_equipa_fora(self, equipa_id: str):
        self.equipa_fora_id = equipa_id
        for j in self.equipa_vermelha:
            j.equipa_id = equipa_id
        info = obter_info_equipa(equipa_id)
        self._msg_texto = f"Equipa Visitante: {info['nome']}"
        self._msg_timer = 2.0

    def alternar_equipa_casa(self):
        idx = EQUIPAS_LISTA.index(self.equipa_casa_id) if self.equipa_casa_id in EQUIPAS_LISTA else 0
        prox_idx = (idx + 1) % len(EQUIPAS_LISTA)
        self.mudar_equipa_casa(EQUIPAS_LISTA[prox_idx])

    def alternar_equipa_fora(self):
        idx = EQUIPAS_LISTA.index(self.equipa_fora_id) if self.equipa_fora_id in EQUIPAS_LISTA else 0
        prox_idx = (idx + 1) % len(EQUIPAS_LISTA)
        self.mudar_equipa_fora(EQUIPAS_LISTA[prox_idx])

    # ------------------------------------------------------------------ #
    # Golos e Fim de Parte                                                #
    # ------------------------------------------------------------------ #

    def _golo(self, equipa: str):
        info_casa = obter_info_equipa(self.equipa_casa_id)
        info_fora = obter_info_equipa(self.equipa_fora_id)
        if equipa == "azul":
            self.golos_azul += 1
            self._msg_texto = f"GOLO!  {info_casa['nome'].upper()}"
        else:
            self.golos_vermelho += 1
            self._msg_texto = f"GOLO!  {info_fora['nome'].upper()}"
        self._msg_timer = 2.5
        self._repor_posicoes()

    def _repor_posicoes(self):
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola.repor((cx, cy))

        posicoes_azul = [
            (cx + 70,  cy),
            (cx + 200, cy - 90),
            (cx + 200, cy + 90),
            (cx + 360, cy - 70),
            (cx + 360, cy + 70),
        ]
        posicoes_verm = [
            (cx - 70,  cy),
            (cx - 200, cy - 90),
            (cx - 200, cy + 90),
            (cx - 360, cy - 70),
            (cx - 360, cy + 70),
        ]
        for j, pos in zip(list(self.equipa_azul), posicoes_azul):
            j.pos_x, j.pos_y = float(pos[0]), float(pos[1])
            j.vel_x = j.vel_y = 0.0
            j.set_target(0.0, 0.0)
            j.rect.center = pos
            j.tem_bola = False

        for j, pos in zip(list(self.equipa_vermelha), posicoes_verm):
            j.pos_x, j.pos_y = float(pos[0]), float(pos[1])
            j.vel_x = j.vel_y = 0.0
            j.set_target(0.0, 0.0)
            j.rect.center = pos
            j.tem_bola = False

        # Dá a bola ao jogador humano
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # Repor guarda-redes
        self.gr_azul.pos_y     = float(self.rink.rect.centery)
        self.gr_vermelho.pos_y = float(self.rink.rect.centery)

    def _fim_de_parte(self):
        if self.parte == 1:
            self.parte = 2
            self.tempo_restante = float(DURACAO_PARTE)
            self._msg_texto = "Intervalo  —  2.ª Parte"
            self._msg_timer = 3.0
            self._repor_posicoes()
        else:
            self.jogo_ativo = False
            self.fim_jogo   = True

    # ================================================================== #
    # Desenho Principal                                                    #
    # ================================================================== #

    def draw(self):
        if self.estado == "menu_selecao":
            self.menu.draw()
            pygame.display.flip()
            return

        self.screen.fill(COR_FUNDO)

        # 1. Ringue e Balizas traseiras
        self.rink.draw(self.screen)

        # 2. Guarda-redes
        self.grupo_gr.draw(self.screen)

        # 3. Jogadores de campo e bola
        self.todos_jogadores.draw(self.screen)
        self.sprites_bola.draw(self.screen)

        # 4. Postes frontais e travessas das balizas
        self.rink.draw_frente(self.screen)

        # 5. Indicadores por cima dos jogadores
        for j in self.todos_jogadores:
            j.draw_extra(self.screen, self.font_num, self.show_debug)
        for gr in self.grupo_gr:
            gr.draw_extra(self.screen, self.font_num)

        # 6. Marcador Superior do Mockup
        self._draw_mira()
        self.hud.draw_top_bar(self.screen, self)

        # 7. Painel Inferior (Mini-mapa, Cartão de Jogador e Controlos)
        self.hud.draw_bottom_panel(self.screen, self)

        # 8. Mensagens de Golo / Fim de Jogo
        if self._msg_timer > 0:
            self._draw_mensagem(self._msg_texto)
        if self.fim_jogo:
            self._draw_fim_jogo()
        if self.show_debug:
            self._draw_debug()

        pygame.display.flip()

    def _draw_mensagem(self, texto: str):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        self.screen.blit(ov, (0, 0))
        for cor, off in [((0,0,0), 3), ((255, 220, 50), 0)]:
            t = self.font_big.render(texto, True, cor)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2 + off,
                                  RINK_Y + RINK_H // 2 - t.get_height() // 2 + off))

    def _draw_fim_jogo(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        info_casa = obter_info_equipa(self.equipa_casa_id)
        info_fora = obter_info_equipa(self.equipa_fora_id)

        if self.golos_azul > self.golos_vermelho:
            txt_v, cor = f"Vitória do {info_casa['nome']}!", info_casa.get("cor_primaria", (100, 170, 255))
        elif self.golos_vermelho > self.golos_azul:
            txt_v, cor = f"Vitória do {info_fora['nome']}!", info_fora.get("cor_primaria", (255, 80, 80))
        else:
            txt_v, cor = "Empate!", (255, 220, 50)

        linhas = [
            (self.font_big.render("FIM DO JOGO", True, (255, 255, 255))),
            (self.font_big.render(txt_v, True, cor)),
            (self.font_med.render(f"{self.golos_azul} — {self.golos_vermelho}", True, (255, 255, 255))),
            (self.font_num.render("Prima  R  para recomeçar", True, (180, 180, 180))),
        ]
        for i, t in enumerate(linhas):
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2,
                                  RINK_Y + 70 + i * 50))

    def _draw_debug(self):
        fps = self.font_num.render(f"FPS: {self.clock.get_fps():.0f}", True, (255, 255, 100))
        self.screen.blit(fps, (WIDTH - 120, HUD_H + 8))
        dono = self.bola.dono.nome if self.bola.dono else "livre"
        db = self.font_num.render(f"Bola: {dono}", True, (200, 255, 200))
        self.screen.blit(db, (WIDTH - 120, HUD_H + 24))

    def _draw_mira(self):
        """Desenha a linha de mira e barra de força estilo 8 Ball Pool."""
        if not self._mira_ativa or not self.jogador_humano.tem_bola:
            return

        screen = self.screen
        bx = round(self.jogador_humano.pos_x)
        by = round(self.jogador_humano.pos_y)
        direc = self._mira_direcao

        # ── 1. Linha tracejada de trajetória ──────────────────────────────
        comprimento_linha = 220
        num_tracos = 14
        taco = comprimento_linha / (num_tracos * 2)
        surf_linha = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for i in range(num_tracos):
            t_ini = (i * 2)       * taco
            t_fim = (i * 2 + 1.2) * taco
            px_ini = bx + direc.x * t_ini
            py_ini = by + direc.y * t_ini
            px_fim = bx + direc.x * t_fim
            py_fim = by + direc.y * t_fim
            # Cor varia com a força: verde (fraco) → amarelo → vermelho (forte)
            f = self._mira_forca
            r = int(255 * min(f * 2, 1.0))
            g = int(255 * min((1 - f) * 2, 1.0))
            cor_linha = (r, g, 30, 210)
            pygame.draw.line(surf_linha, cor_linha,
                             (int(px_ini), int(py_ini)),
                             (int(px_fim), int(py_fim)), 3)

        screen.blit(surf_linha, (0, 0))

        # ── 2. Círculo de mira no fim da linha ────────────────────────────
        alvo_x = int(bx + direc.x * comprimento_linha)
        alvo_y = int(by + direc.y * comprimento_linha)
        pygame.draw.circle(screen, (255, 255, 100, 180), (alvo_x, alvo_y), 8, 2)

        # ── 3. Barra de Força (estilo 8 Ball Pool) ────────────────────────
        bar_x  = bx - 60
        bar_y  = by + 36
        bar_w  = 120
        bar_h  = 14

        # Fundo da barra
        pygame.draw.rect(screen, (20, 20, 20), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=8)
        pygame.draw.rect(screen, (50, 50, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=6)

        # Preenchimento da barra com gradiente de cor
        fill_w = int(bar_w * self._mira_forca)
        if fill_w > 0:
            f = self._mira_forca
            r = int(255 * min(f * 2, 1.0))
            g = int(255 * min((1 - f) * 2, 1.0))
            pygame.draw.rect(screen, (r, g, 20), (bar_x, bar_y, fill_w, bar_h), border_radius=6)

        # Borda da barra
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

        # Texto "FORÇA"
        f_txt = pygame.font.SysFont("Arial", 11, bold=True)
        pct = int(self._mira_forca * 100)
        t = f_txt.render(f"FORÇA  {pct}%", True, (255, 255, 255))
        screen.blit(t, (bar_x + bar_w // 2 - t.get_width() // 2, bar_y - 18))

        # ── 4. Instrução ──────────────────────────────────────────────────
        fi = pygame.font.SysFont("Arial", 13, bold=True)
        ti = fi.render("[X] ou Clique para rematar  •  [ESC] para cancelar", True, (220, 220, 100))
        screen.blit(ti, (WIDTH // 2 - ti.get_width() // 2, HEIGHT - 30))
