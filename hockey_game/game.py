# -*- coding: utf-8 -*-
"""game.py - game loop com IA real, posicionamento tático e seleção automática de jogador."""
import os
import math
import pygame
from settings import *
from rink import Rink
from player import Player
from ball import Ball
from ai import AgentIA
from goalkeeper import Goalkeeper

DURACAO_PARTE = 60 * 5   # 5 minutos por parte


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_hud = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_num = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 28, bold=True)

        self.rink = Rink()

        # Marcador UI
        _ui = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "sprites_v2", "extras_ui")
        raw_marc = pygame.image.load(os.path.join(_ui, "marcador_ui.png")).convert_alpha()
        marc_h = HUD_H - 8
        marc_w = int(raw_marc.get_width() * marc_h / raw_marc.get_height())
        self._marcador_ui   = pygame.transform.scale(raw_marc, (marc_w, marc_h))
        self._marcador_rect = self._marcador_ui.get_rect(center=(WIDTH // 2, HUD_H // 2))

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
    # Criação das equipas com posições táticas                            #
    # ================================================================== #

    def _criar_equipas(self):
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2

        r = self.rink
        # Balizas: azul ataca à direita, vermelho ataca à esquerda
        # (a equipa azul começa no lado direito)
        bal_azul_ataca   = r.baliza_dir   # azul tenta marcar aqui? NÃO —
        # Azul joga da direita para a esquerda:
        #   baliza própria = direita, baliza adversária = esquerda
        # Vermelho: baliza própria = esquerda, adversária = direita
        bal_prop_azul  = r.baliza_dir
        bal_adv_azul   = r.baliza_esq
        bal_prop_verm  = r.baliza_esq
        bal_adv_verm   = r.baliza_dir

        # ── Equipa azul (lado direito do campo) ──────────────────────────
        # Formato: [avançado, avançado, médio, defesa, defesa]
        # Posições: x > cx (lado direito)
        dados_azul = [
            # (pos_inicial, papel, numero, nome)
            ((cx + 80,  cy),       "avancado", 10, "Silva"),
            ((cx + 240, cy - 110), "avancado",  9, "Costa"),
            ((cx + 240, cy + 110), "medio",     8, "Ramos"),
            ((cx + 400, cy - 80),  "defesa",    4, "Faria"),
            ((cx + 400, cy + 80),  "defesa",    5, "Neves"),
        ]

        self.equipa_azul  = pygame.sprite.Group()
        self.agentes_azul = []
        self.jogador_humano = None

        for i, (pos, papel, num, nome) in enumerate(dados_azul):
            humano = (i == 0)
            p = Player("azul", pos, numero=num, nome=nome, humano=humano, teclas="wasd")
            p.papel = papel
            pos_base = self._pos_tatica_azul(papel, pos)
            p.pos_tatica = pos_base
            self.equipa_azul.add(p)
            if humano:
                self.jogador_humano = p
                p.selecionado = True
            else:
                agente = AgentIA(p, papel, "azul", pos_base,
                                 bal_prop_azul, bal_adv_azul)
                self.agentes_azul.append(agente)

        # ── Equipa vermelha (lado esquerdo do campo) — toda IA ──────────
        dados_verm = [
            ((cx - 80,  cy),       "avancado",  9, "López"),
            ((cx - 240, cy - 110), "avancado", 10, "García"),
            ((cx - 240, cy + 110), "medio",     8, "Martín"),
            ((cx - 400, cy - 80),  "defesa",    4, "Pérez"),
            ((cx - 400, cy + 80),  "defesa",    5, "Ruiz"),
        ]

        self.equipa_vermelha   = pygame.sprite.Group()
        self.agentes_vermelhos = []
        self.jogador_humano2   = None   # sem jogador 2

        for pos, papel, num, nome in dados_verm:
            p = Player("vermelho", pos, numero=num, nome=nome, humano=False)
            self.equipa_vermelha.add(p)
            pos_base = self._pos_tatica_verm(papel, pos)
            agente = AgentIA(p, papel, "vermelho", pos_base,
                             bal_prop_verm, bal_adv_verm)
            self.agentes_vermelhos.append(agente)

        self.todos_jogadores = pygame.sprite.Group(
            *self.equipa_azul, *self.equipa_vermelha
        )

        # ── Guarda-redes ─────────────────────────────────────────────────
        cy_rink = RINK_Y + RINK_H // 2
        r = self.rink

        # GR azul: defende a baliza direita, fica ligeiramente dentro do campo
        self.gr_azul = Goalkeeper(
            equipa="azul", lado="dir",
            baliza_rect=r.zona_gr_dir,
            pos_x_fixo=r.rect.right - 18
        )
        # GR vermelho: defende a baliza esquerda
        self.gr_vermelho = Goalkeeper(
            equipa="vermelho", lado="esq",
            baliza_rect=r.zona_gr_esq,
            pos_x_fixo=r.rect.left + 18
        )
        self.grupo_gr = pygame.sprite.Group(self.gr_azul, self.gr_vermelho)

    def _pos_tatica_azul(self, papel: str, pos_inicial: tuple) -> tuple:
        """Posição tática de referência para a IA azul."""
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        if papel == "avancado":
            return (cx + 120, pos_inicial[1])
        elif papel == "medio":
            return (cx + 280, pos_inicial[1])
        else:  # defesa
            return (cx + 400, pos_inicial[1])

    def _pos_tatica_verm(self, papel: str, pos_inicial: tuple) -> tuple:
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        if papel == "avancado":
            return (cx - 120, pos_inicial[1])
        elif papel == "medio":
            return (cx - 280, pos_inicial[1])
        else:
            return (cx - 400, pos_inicial[1])

    # ================================================================== #
    # Game loop                                                            #
    # ================================================================== #

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
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
                elif event.key == pygame.K_TAB:
                    self._selecionar_jogador_proximo()
                elif event.key == pygame.K_r and self.fim_jogo:
                    self.__init__()

    # ================================================================== #
    # Ações do humano                                                      #
    # ================================================================== #

    def _direcao_vec(self, jogador=None) -> pygame.math.Vector2:
        if jogador is None:
            jogador = self.jogador_humano
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            return pygame.math.Vector2(jogador.vetor_direcao)
        mapa = {"direita":(1,0),"esquerda":(-1,0),"cima":(0,-1),"baixo":(0,1)}
        return pygame.math.Vector2(mapa.get(jogador.direcao, (1, 0)))

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
                if 30 < dist < 480:
                    dot = direcao.dot(to_j.normalize())
                    if dot > 0.35:  # no cone da direção apontada
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

    def _acao_passe2(self):
        if self.jogador_humano2 and self.jogador_humano2.tem_bola and self.jogo_ativo:
            self.jogador_humano2.fazer_passe(self.bola, self._direcao_vec(self.jogador_humano2))

    def _acao_remate2(self):
        if self.jogador_humano2 and self.jogador_humano2.tem_bola and self.jogo_ativo:
            self.jogador_humano2.fazer_remate(self.bola, self._direcao_vec(self.jogador_humano2))

    def _selecionar_jogador_proximo(self):
        """TAB: passa o controlo para o jogador azul mais perto da bola."""
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
        """Troca o jogador controlado pelo humano mantendo os papéis táticos corretos."""
        if novo == self.jogador_humano:
            return

        antigo = self.jogador_humano
        antigo.humano      = False
        antigo.selecionado = False
        antigo.set_target(0.0, 0.0)

        # Preserva o papel tático e posição de referência original do jogador anterior
        papel    = getattr(antigo, "papel", "avancado")
        pos_base = getattr(antigo, "pos_tatica", self._pos_tatica_azul(papel, (antigo.pos_x, antigo.pos_y)))
        agente   = AgentIA(antigo, papel, "azul", pos_base,
                           self.rink.baliza_dir, self.rink.baliza_esq)
        self.agentes_azul.append(agente)

        # Ativa o controlo humano no novo jogador
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

        # Seleção automática: se a bola estiver livre, seleciona o azul mais perto
        self._auto_selecionar()

        # IA vermelha
        lista_verm = list(self.equipa_vermelha)
        lista_azul = list(self.equipa_azul)
        for agente in self.agentes_vermelhos:
            colegas = [j for j in lista_verm if j != agente.jogador]
            agente.update(dt, self.bola, colegas, lista_azul)

        # IA azul (jogadores não humanos)
        for agente in self.agentes_azul:
            # Incluir o jogador humano na lista de "colegas" para o cálculo de quem persegue
            colegas_com_humano = [j for j in lista_azul if j != agente.jogador]
            agente.update(dt, self.bola, colegas_com_humano, lista_verm)

        # Update de todos os jogadores (movimento + animação)
        for j in self.todos_jogadores:
            j.update(dt, self.rink.rect, self.bola)

        # Colisões entre jogadores (separação física)
        todos = list(self.todos_jogadores)
        for i in range(len(todos)):
            for k in range(i + 1, len(todos)):
                todos[i].empurrar_separar(todos[k], self.bola)

        # Bola
        resultado = self.bola.update(
            dt, self.rink.rect,
            self.rink.baliza_esq, self.rink.baliza_dir,
            todos_jogadores=todos
        )

        # Guarda-redes: update + bloquear bola
        self.gr_azul.update(dt, self.bola)
        self.gr_vermelho.update(dt, self.bola)
        self.gr_azul.bloquear_bola(self.bola)
        self.gr_vermelho.bloquear_bola(self.bola)

        # A baliza direita é do Azul (logo golo da equipa Vermelha)
        # A baliza esquerda é do Vermelho (logo golo da equipa Azul)
        if resultado == "golo_dir":
            self._golo("vermelho")
        elif resultado == "golo_esq":
            self._golo("azul")

        if self._msg_timer > 0:
            self._msg_timer -= dt

    def _auto_selecionar(self):
        """
        Gere a troca de controlo do jogador azul:
        1. Se um colega azul tem a bola, o humano passa a controlá-lo de imediato.
        2. Se a bola está livre e lenta, seleciona o jogador azul mais próximo sem oscilação.
        """
        # Se a bola está com um colega azul, passa o controlo imediatamente para ele
        if self.bola.dono is not None:
            if self.bola.dono in self.equipa_azul and self.bola.dono != self.jogador_humano:
                self._trocar_humano(self.bola.dono)
            return

        if self.jogador_humano.tem_bola:
            return

        # Durante um remate/passe veloz, não muda de jogador no meio da trajetória
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
            if d < melhor_dist - 80:   # margem para evitar alternâncias bruscas
                melhor_dist = d
                melhor = j
        if melhor != self.jogador_humano:
            self._trocar_humano(melhor)

    # ------------------------------------------------------------------ #
    # Golos e partes                                                       #
    # ------------------------------------------------------------------ #

    def _golo(self, equipa: str):
        if equipa == "azul":
            self.golos_azul += 1
            self._msg_texto = "GOLO!  Equipa Azul"
        else:
            self.golos_vermelho += 1
            self._msg_texto = "GOLO!  Equipa Vermelha"
        self._msg_timer = 2.5
        self._repor_posicoes()

    def _repor_posicoes(self):
        """Volta todos ao centro após golo."""
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola.repor((cx, cy))

        posicoes_azul = [
            (cx + 80,  cy),
            (cx + 240, cy - 110),
            (cx + 240, cy + 110),
            (cx + 400, cy - 80),
            (cx + 400, cy + 80),
        ]
        posicoes_verm = [
            (cx - 80,  cy),
            (cx - 240, cy - 110),
            (cx - 240, cy + 110),
            (cx - 400, cy - 80),
            (cx - 400, cy + 80),
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

        # Dá a bola ao jogador humano e posiciona-a de imediato
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # Repor guarda-redes ao centro das balizas
        self.gr_azul.pos_y     = float(self.rink.baliza_dir.centery)
        self.gr_vermelho.pos_y = float(self.rink.baliza_esq.centery)

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
    # Desenho                                                              #
    # ================================================================== #

    def draw(self):
        self.screen.fill(COR_FUNDO)
        self.rink.draw(self.screen)

        # Guarda-redes atrás das balizas frontais mas à frente do campo
        self.grupo_gr.draw(self.screen)

        self.todos_jogadores.draw(self.screen)
        self.sprites_bola.draw(self.screen)
        self.rink.draw_frente(self.screen)

        for j in self.todos_jogadores:
            j.draw_extra(self.screen, self.font_num)
        for gr in self.grupo_gr:
            gr.draw_extra(self.screen, self.font_num)

        self._draw_hud()

        if self._msg_timer > 0:
            self._draw_mensagem(self._msg_texto)
        if self.fim_jogo:
            self._draw_fim_jogo()
        if self.show_debug:
            self._draw_debug()

        pygame.display.flip()

    # ------------------------------------------------------------------ #
    # HUD                                                                  #
    # ------------------------------------------------------------------ #

    def _draw_hud(self):
        # ── Fundo da barra ───────────────────────────────────────────────
        pygame.draw.rect(self.screen, (15, 22, 45), (0, 0, WIDTH, HUD_H))
        pygame.draw.line(self.screen, (40, 65, 140), (0, HUD_H), (WIDTH, HUD_H), 2)

        # ── Layout do marcador (igual ao mockup) ─────────────────────────
        # Bloco central do marcador: começa a 300px da esquerda, 980px de largura
        marc_x  = 260
        marc_w  = WIDTH - 520
        linha_h = HUD_H // 2   # cada linha tem metade da altura do HUD

        # Linha 1 — Equipa Azul (casa)  ─────────────────────────────────
        cor_azul = (40, 90, 190)
        pygame.draw.rect(self.screen, cor_azul,
                         (marc_x, 0, marc_w, linha_h))

        # Linha 2 — Equipa Vermelha (fora) ──────────────────────────────
        cor_verm = (160, 25, 25)
        pygame.draw.rect(self.screen, cor_verm,
                         (marc_x, linha_h, marc_w, linha_h))

        # Separador horizontal entre as duas linhas
        pygame.draw.line(self.screen, (0,0,0,80),
                         (marc_x, linha_h), (marc_x + marc_w, linha_h), 1)

        # ── Quadrado colorido (escudo placeholder) ───────────────────────
        esc_w = 28
        pygame.draw.rect(self.screen, (200, 210, 255),
                         (marc_x + 8, 6, esc_w, linha_h - 12), border_radius=3)
        pygame.draw.rect(self.screen, (220, 60, 60),
                         (marc_x + 8, linha_h + 6, esc_w, linha_h - 12), border_radius=3)

        # ── Nomes das equipas ────────────────────────────────────────────
        font_nome = pygame.font.SysFont("Arial", 15, bold=True)
        t = font_nome.render("Equipa Azul", True, (255, 255, 255))
        self.screen.blit(t, (marc_x + 8 + esc_w + 6, linha_h // 2 - t.get_height() // 2))
        t = font_nome.render("Equipa Vermelha", True, (255, 255, 255))
        self.screen.blit(t, (marc_x + 8 + esc_w + 6, linha_h + linha_h // 2 - t.get_height() // 2))

        # ── Resultado (grande, no lado direito do bloco) ─────────────────
        font_golo = pygame.font.SysFont("Arial", 32, bold=True)
        res_x = marc_x + marc_w - 60

        t_az = font_golo.render(str(self.golos_azul), True, (255, 255, 255))
        self.screen.blit(t_az, (res_x - t_az.get_width() // 2,
                                 linha_h // 2 - t_az.get_height() // 2))

        t_vm = font_golo.render(str(self.golos_vermelho), True, (255, 255, 255))
        self.screen.blit(t_vm, (res_x - t_vm.get_width() // 2,
                                 linha_h + linha_h // 2 - t_vm.get_height() // 2))

        # ── Cronómetro + Parte (à direita do bloco central) ──────────────
        mins = max(0, int(self.tempo_restante)) // 60
        segs = max(0, int(self.tempo_restante)) % 60
        cx_time = marc_x + marc_w + 80

        font_time = pygame.font.SysFont("Arial", 28, bold=True)
        t_time = font_time.render(f"{mins:02d}:{segs:02d}", True, (255, 255, 255))
        self.screen.blit(t_time, (cx_time - t_time.get_width() // 2, 12))

        font_parte = pygame.font.SysFont("Arial", 13)
        t_parte = font_parte.render(f"{self.parte}.ª Parte", True, (160, 180, 220))
        self.screen.blit(t_parte, (cx_time - t_parte.get_width() // 2,
                                    HUD_H - t_parte.get_height() - 8))

        # ── Controlos (canto inferior esquerdo do ecrã) ──────────────────
        font_ctrl = pygame.font.SysFont("Arial", 12)
        for i, txt in enumerate(["WASD / Setas  Mover",
                                  "SHIFT  Sprint",
                                  "Z  Passe    X  Remate",
                                  "TAB  Trocar jogador"]):
            t = font_ctrl.render(txt, True, (100, 125, 165))
            self.screen.blit(t, (10, HEIGHT - (4 - i) * 16))

        # ── Jogador controlado ────────────────────────────────────────────
        font_ctrl2 = pygame.font.SysFont("Arial", 13, bold=True)
        j1 = self.jogador_humano
        t1 = font_ctrl2.render(f"#{j1.numero} {j1.nome}", True, (180, 210, 255))
        self.screen.blit(t1, (WIDTH - t1.get_width() - 12, HEIGHT - 18))

    # ------------------------------------------------------------------ #
    # Mensagens                                                            #
    # ------------------------------------------------------------------ #

    def _draw_mensagem(self, texto: str):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        self.screen.blit(ov, (0, 0))
        for cor, off in [((0,0,0), 3), ((255,220,50), 0)]:
            t = self.font_big.render(texto, True, cor)
            self.screen.blit(t, (WIDTH//2 - t.get_width()//2 + off,
                                  HEIGHT//2 - t.get_height()//2 + off))

    def _draw_fim_jogo(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        if self.golos_azul > self.golos_vermelho:
            txt_v, cor = "Vitória da Equipa Azul!", (100,160,255)
        elif self.golos_vermelho > self.golos_azul:
            txt_v, cor = "Vitória da Equipa Vermelha!", (255,80,80)
        else:
            txt_v, cor = "Empate!", (255,220,50)

        linhas = [
            (self.font_big.render("FIM DO JOGO", True, (255,255,255))),
            (self.font_big.render(txt_v, True, cor)),
            (self.font_med.render(f"{self.golos_azul} — {self.golos_vermelho}", True, (255,255,255))),
            (self.font_num.render("Prima  R  para recomeçar", True, (180,180,180))),
        ]
        for i, t in enumerate(linhas):
            self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 90 + i*55))

    def _draw_debug(self):
        fps = self.font_num.render(f"FPS: {self.clock.get_fps():.0f}", True, (255,255,100))
        self.screen.blit(fps, (WIDTH - 80, 4))
        # Mostrar dono da bola
        dono = self.bola.dono.nome if self.bola.dono else "livre"
        db = self.font_num.render(f"Bola: {dono}", True, (200,255,200))
        self.screen.blit(db, (WIDTH - 150, 20))
