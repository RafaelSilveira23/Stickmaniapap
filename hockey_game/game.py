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

        self.rink = Rink()
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

        # ── Estado do jogo ───────────────────────────────────────────────
        self.golos_azul     = 0
        self.golos_vermelho = 0
        self.parte          = 1
        self.tempo_restante = float(DURACAO_PARTE)
        self.jogo_ativo     = True
        self.fim_jogo       = False
        self._msg_texto     = ""
        self._msg_timer     = 0.0

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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_z:
                    self._acao_passe()
                elif event.key == pygame.K_x:
                    self._acao_remate()
                elif event.key in (pygame.K_TAB, pygame.K_c, pygame.K_SPACE):
                    self._selecionar_jogador_proximo()
                elif event.key == pygame.K_r and self.fim_jogo:
                    self.__init__()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        if self.jogador_humano.tem_bola and self.jogo_ativo:
            self.jogador_humano.fazer_remate(self.bola, self._direcao_vec(self.jogador_humano))

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
        if not self.jogo_ativo:
            return

        # Cronómetro
        self.tempo_restante -= dt
        if self.tempo_restante <= 0:
            self._fim_de_parte()
            return

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
    # Golos e Fim de Parte                                                #
    # ------------------------------------------------------------------ #

    def _golo(self, equipa: str):
        if equipa == "azul":
            self.golos_azul += 1
            self._msg_texto = "GOLO!  FC PORTO"
        else:
            self.golos_vermelho += 1
            self._msg_texto = "GOLO!  RIBA D'AVE"
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

        if self.golos_azul > self.golos_vermelho:
            txt_v, cor = "Vitória do FC Porto!", (100, 170, 255)
        elif self.golos_vermelho > self.golos_azul:
            txt_v, cor = "Vitória do Riba d'Ave!", (255, 80, 80)
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
