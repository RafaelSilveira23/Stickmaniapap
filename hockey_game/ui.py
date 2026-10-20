# -*- coding: utf-8 -*-
"""ui.py - Interface do jogo (Mini-mapa tático, Cartão do Jogador, Joystick e Botões de Ação).

Desenvolvido para corresponder à interface moderna do mockup:
  1. Mini-mapa em tempo real (radar tático com jogadores e bola)
  2. Cartão do jogador selecionado (foto/avatar, número, nome, atributos)
  3. Joystick virtual / D-pad com setas direcionais reativas
  4. Botões de ação arcade (Remate, Passe, Acelerar, Defender)
"""
import math
import pygame
from settings import *


class HUDController:
    def __init__(self):
        self.font_time = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_score = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_card_nome = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_card_role = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_stat = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_key = pygame.font.SysFont("Arial", 9, bold=True)

        # Botões de ação (retângulos para clique do rato)
        self.btn_rects = {}
        self._setup_buttons()

    def _setup_buttons(self):
        # 4 botões circulares no canto inferior direito
        base_x = 940
        base_y = HUD_BAIXO_Y + 28
        espaco_x = 78
        raio = 26

        botoes = [
            ("remate",   "Remate",   "X",     (220, 60, 60)),
            ("passe",    "Passe",    "Z",     (40, 140, 240)),
            ("acelerar", "Acelerar", "SHIFT", (40, 200, 100)),
            ("defender", "Defender", "C",     (230, 160, 30)),
        ]

        for i, (chave, label, atalho, cor) in enumerate(botoes):
            cx = base_x + i * espaco_x
            cy = base_y + 36
            self.btn_rects[chave] = {
                "center": (cx, cy),
                "raio": raio,
                "label": label,
                "atalho": atalho,
                "cor": cor,
                "rect": pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2)
            }

    # ================================================================== #
    # Marcador Superior (Top Bar)                                         #
    # ================================================================== #

    def draw_top_bar(self, screen: pygame.Surface, game):
        # Fundo da barra superior
        pygame.draw.rect(screen, (10, 16, 32), (0, 0, WIDTH, HUD_H))
        pygame.draw.line(screen, (35, 60, 120), (0, HUD_H), (WIDTH, HUD_H), 2)

        # ── Bloco Central do Marcador ────────────────────────────────────
        marc_x = 240
        marc_w = 420
        linha_h = HUD_H // 2

        # Linha 1: Equipa da Casa (FC Porto / Azul)
        pygame.draw.rect(screen, (30, 75, 170), (marc_x, 0, marc_w, linha_h))
        # Linha 2: Equipa Visitante (Riba d'Ave / Vermelho)
        pygame.draw.rect(screen, (170, 30, 30), (marc_x, linha_h, marc_w, linha_h))

        # Divisória horizontal
        pygame.draw.line(screen, (15, 25, 50), (marc_x, linha_h), (marc_x + marc_w, linha_h), 2)

        # Emblemas simplificados
        self._desenhar_emblema(screen, marc_x + 10, 6, (230, 240, 255), (20, 60, 180), "FCP")
        self._desenhar_emblema(screen, marc_x + 10, linha_h + 6, (255, 220, 220), (180, 20, 20), "RDA")

        # Nomes das equipas
        t_azul = self.font_title.render("FC Porto", True, (255, 255, 255))
        t_verm = self.font_title.render("Riba d'Ave", True, (255, 255, 255))
        screen.blit(t_azul, (marc_x + 48, linha_h // 2 - t_azul.get_height() // 2))
        screen.blit(t_verm, (marc_x + 48, linha_h + linha_h // 2 - t_verm.get_height() // 2))

        # Golos
        g_az = self.font_score.render(str(game.golos_azul), True, (255, 255, 255))
        g_vm = self.font_score.render(str(game.golos_vermelho), True, (255, 255, 255))
        screen.blit(g_az, (marc_x + marc_w - 40, linha_h // 2 - g_az.get_height() // 2))
        screen.blit(g_vm, (marc_x + marc_w - 40, linha_h + linha_h // 2 - g_vm.get_height() // 2))

        # ── Cronómetro e Parte ───────────────────────────────────────────
        time_x = marc_x + marc_w + 30
        mins = max(0, int(game.tempo_restante)) // 60
        segs = max(0, int(game.tempo_restante)) % 60
        t_cron = self.font_time.render(f"{mins:02d}:{segs:02d}", True, (255, 255, 255))
        screen.blit(t_cron, (time_x, 10))

        font_sub = pygame.font.SysFont("Arial", 12, bold=True)
        t_parte = font_sub.render(f"{game.parte}.ª Parte", True, (150, 180, 230))
        screen.blit(t_parte, (time_x + 8, 38))

        # ── Botão de Pausa (canto superior direito) ──────────────────────
        pause_r = pygame.Rect(WIDTH - 50, 14, 34, 34)
        pygame.draw.rect(screen, (25, 40, 80), pause_r, border_radius=6)
        pygame.draw.rect(screen, (50, 90, 180), pause_r, 1, border_radius=6)
        # Símbolo ||
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 42, 22, 5, 18), border_radius=2)
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 33, 22, 5, 18), border_radius=2)

    def _desenhar_emblema(self, surf, x, y, cor_bg, cor_fg, sigla):
        r = pygame.Rect(x, y, 28, 20)
        pygame.draw.rect(surf, cor_bg, r, border_radius=4)
        pygame.draw.rect(surf, cor_fg, r, 2, border_radius=4)
        f = pygame.font.SysFont("Arial", 9, bold=True)
        t = f.render(sigla, True, cor_fg)
        surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

    # ================================================================== #
    # Painel Inferior (Bottom Dashboard)                                  #
    # ================================================================== #

    def draw_bottom_panel(self, screen: pygame.Surface, game):
        # Fundo escuro do painel inferior
        pygame.draw.rect(screen, (10, 16, 30), (0, HUD_BAIXO_Y, WIDTH, HUD_BAIXO_H))
        pygame.draw.line(screen, (30, 55, 110), (0, HUD_BAIXO_Y), (WIDTH, HUD_BAIXO_Y), 2)

        # 1. Joystick Virtual (D-Pad)
        self._draw_joystick(screen, (100, HUD_BAIXO_Y + 86))

        # 2. Mini-mapa Tático
        self._draw_minimap(screen, game, pygame.Rect(210, HUD_BAIXO_Y + 14, 210, 156))

        # 3. Cartão do Jogador Ativo
        self._draw_player_card(screen, game.jogador_humano, pygame.Rect(440, HUD_BAIXO_Y + 14, 460, 156))

        # 4. Botões de Ação
        self._draw_action_buttons(screen)

    # ------------------------------------------------------------------ #
    # 1. Joystick Virtual (D-Pad)                                          #
    # ------------------------------------------------------------------ #

    def _draw_joystick(self, screen: pygame.Surface, center: tuple):
        cx, cy = center
        keys = pygame.key.get_pressed()

        # Círculo base exterior
        pygame.draw.circle(screen, (18, 28, 55), (cx, cy), 58)
        pygame.draw.circle(screen, (40, 70, 140), (cx, cy), 58, 2)
        pygame.draw.circle(screen, (12, 18, 36), (cx, cy), 22)

        # Setas direcionais (acendem quando a tecla correspondente é premida)
        cima_ativo    = keys[pygame.K_UP]    or keys[pygame.K_w]
        baixo_ativo   = keys[pygame.K_DOWN]  or keys[pygame.K_s]
        esq_ativo     = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        dir_ativo     = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        cor_ativo   = (60, 200, 255)
        cor_inativo = (70, 95, 150)

        # Cima
        c = cor_ativo if cima_ativo else cor_inativo
        pygame.draw.polygon(screen, c, [(cx, cy - 46), (cx - 12, cy - 28), (cx + 12, cy - 28)])
        # Baixo
        c = cor_ativo if baixo_ativo else cor_inativo
        pygame.draw.polygon(screen, c, [(cx, cy + 46), (cx - 12, cy + 28), (cx + 12, cy + 28)])
        # Esquerda
        c = cor_ativo if esq_ativo else cor_inativo
        pygame.draw.polygon(screen, c, [(cx - 46, cy), (cx - 28, cy - 12), (cx - 28, cy + 12)])
        # Direita
        c = cor_ativo if dir_ativo else cor_inativo
        pygame.draw.polygon(screen, c, [(cx + 46, cy), (cx + 28, cy - 12), (cx + 28, cy + 12)])

    # ------------------------------------------------------------------ #
    # 2. Mini-mapa Tático (Radar)                                          #
    # ------------------------------------------------------------------ #

    def _draw_minimap(self, screen: pygame.Surface, game, rect: pygame.Rect):
        # Moldura com cantos arredondados
        pygame.draw.rect(screen, (8, 14, 28), rect, border_radius=8)
        pygame.draw.rect(screen, (40, 80, 170), rect, 2, border_radius=8)

        # Área interior do campo reduzida proporcionalmente
        pad_x, pad_y = 12, 12
        map_w = rect.width - pad_x * 2
        map_h = rect.height - pad_y * 2
        map_r = pygame.Rect(rect.left + pad_x, rect.top + pad_y, map_w, map_h)

        # Fundo do campo reduzido
        pygame.draw.rect(screen, (15, 25, 50), map_r, border_radius=6)
        pygame.draw.rect(screen, (50, 110, 230), map_r, 1, border_radius=6)

        # Linha central e círculo central
        mcx = map_r.centerx
        mcy = map_r.centery
        pygame.draw.line(screen, (50, 110, 230), (mcx, map_r.top + 2), (mcx, map_r.bottom - 2), 1)
        pygame.draw.circle(screen, (50, 110, 230), (mcx, mcy), 14, 1)

        # Fatores de escala campo real -> mini-mapa
        r = game.rink.rect
        sx = map_w / r.width
        sy = map_h / r.height

        def to_map(px, py):
            return (
                int(map_r.left + (px - r.left) * sx),
                int(map_r.top  + (py - r.top)  * sy)
            )

        # Desenhar balizas no mini-mapa
        bal_esq_x, bal_esq_y = to_map(game.rink.linha_golo_esq_x, game.rink.rect.centery)
        bal_dir_x, bal_dir_y = to_map(game.rink.linha_golo_dir_x, game.rink.rect.centery)
        pygame.draw.rect(screen, (220, 60, 60), (bal_esq_x - 6, bal_esq_y - 8, 6, 16), 1)
        pygame.draw.rect(screen, (220, 60, 60), (bal_dir_x,     bal_dir_y - 8, 6, 16), 1)

        # Jogadores Vermelhos (pontos vermelhos)
        for j in game.equipa_vermelha:
            pos = to_map(j.pos_x, j.pos_y)
            pygame.draw.circle(screen, (240, 50, 50), pos, 3)

        # Guarda-redes Vermelho
        pos_gr_v = to_map(game.gr_vermelho.pos_x, game.gr_vermelho.pos_y)
        pygame.draw.circle(screen, (255, 120, 80), pos_gr_v, 3)

        # Jogadores Azuis (pontos azuis)
        for j in game.equipa_azul:
            pos = to_map(j.pos_x, j.pos_y)
            if j == game.jogador_humano:
                # Jogador controlado: círculo pulsante ou realçado
                pygame.draw.circle(screen, (255, 255, 255), pos, 5, 1)
                pygame.draw.circle(screen, (40, 180, 255), pos, 3)
            else:
                pygame.draw.circle(screen, (40, 130, 240), pos, 3)

        # Guarda-redes Azul
        pos_gr_a = to_map(game.gr_azul.pos_x, game.gr_azul.pos_y)
        pygame.draw.circle(screen, (80, 220, 255), pos_gr_a, 3)

        # Bola (ponto amarelo brilhante)
        bx, by = to_map(game.bola.pos_x, game.bola.pos_y)
        pygame.draw.circle(screen, (255, 235, 80), (bx, by), 3)

    # ------------------------------------------------------------------ #
    # 3. Cartão do Jogador Ativo (Player Card)                            #
    # ------------------------------------------------------------------ #

    def _draw_player_card(self, screen: pygame.Surface, jogador, rect: pygame.Rect):
        # Moldura futurista do cartão
        pygame.draw.rect(screen, (12, 20, 42), rect, border_radius=8)
        pygame.draw.rect(screen, (35, 75, 160), rect, 2, border_radius=8)

        # Avatar do Jogador (Retângulo de retrato no lado esquerdo)
        av_rect = pygame.Rect(rect.left + 16, rect.top + 16, 72, 72)
        pygame.draw.rect(screen, (20, 35, 75), av_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 120, 230), av_rect, 1, border_radius=6)

        # Desenhar avatar estilizado (sprite recortado ou cabeça do jogador)
        if hasattr(jogador, "image"):
            # Escalar sprite do jogador centrado no quadrado do avatar
            thumb = pygame.transform.scale(jogador.image, (64, 64))
            screen.blit(thumb, (av_rect.centerx - 32, av_rect.centery - 32))

        # Nome e Número
        t_nome = self.font_card_nome.render(f"{jogador.numero}  {jogador.nome}", True, (255, 255, 255))
        screen.blit(t_nome, (rect.left + 104, rect.top + 14))

        # Posição / Papel tático
        papel = getattr(jogador, "papel", "avancado").upper()
        t_role = self.font_card_role.render(f"POSIÇÃO: {papel}", True, (120, 175, 255))
        screen.blit(t_role, (rect.left + 106, rect.top + 38))

        # ── 4 Barras de Atributos ────────────────────────────────────────
        stats = [
            ("Velocidade", getattr(jogador, "stat_velocidade", 85), (40, 210, 240)),
            ("Remate",     getattr(jogador, "stat_remate", 80),     (240, 90, 90)),
            ("Passe",      getattr(jogador, "stat_passe", 75),      (80, 160, 255)),
            ("Defesa",     getattr(jogador, "stat_defesa", 65),     (60, 220, 130)),
        ]

        bar_x = rect.left + 195
        bar_w = 230
        bar_h = 10
        start_y = rect.top + 60

        for idx, (label, val, cor) in enumerate(stats):
            by = start_y + idx * 22
            # Label
            t_lab = self.font_stat.render(label, True, (180, 200, 240))
            screen.blit(t_lab, (rect.left + 106, by - 2))

            # Fundo da barra
            pygame.draw.rect(screen, (20, 32, 60), (bar_x, by, bar_w, bar_h), border_radius=4)
            # Preenchimento da barra
            preench_w = int(bar_w * (max(0, min(100, val)) / 100.0))
            if preench_w > 0:
                pygame.draw.rect(screen, cor, (bar_x, by, preench_w, bar_h), border_radius=4)

    # ------------------------------------------------------------------ #
    # 4. Botões de Ação Arcade                                            #
    # ------------------------------------------------------------------ #

    def _draw_action_buttons(self, screen: pygame.Surface):
        keys = pygame.key.get_pressed()

        for chave, btn in self.btn_rects.items():
            cx, cy = btn["center"]
            raio = btn["raio"]
            cor = btn["cor"]

            # Verificar se a tecla correspondente está a ser premida
            ativo = False
            if chave == "remate"   and keys[pygame.K_x]: ativo = True
            elif chave == "passe"  and keys[pygame.K_z]: ativo = True
            elif chave == "acelerar" and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]): ativo = True
            elif chave == "defender" and (keys[pygame.K_c] or keys[pygame.K_SPACE]): ativo = True

            # Botão circular exterior
            cor_circ = cor if ativo else (25, 40, 80)
            pygame.draw.circle(screen, cor_circ, (cx, cy), raio)
            pygame.draw.circle(screen, cor if ativo else (60, 100, 180), (cx, cy), raio, 2)

            # Ícone estilizado
            self._desenhar_icone_acao(screen, chave, cx, cy, ativo)

            # Legenda e Atalho por baixo do botão
            t_lbl = self.font_btn.render(btn["label"], True, (240, 245, 255))
            screen.blit(t_lbl, (cx - t_lbl.get_width() // 2, cy + raio + 4))

            t_key = self.font_key.render(f"[{btn['atalho']}]", True, (130, 165, 220))
            screen.blit(t_key, (cx - t_key.get_width() // 2, cy + raio + 17))

    def _desenhar_icone_acao(self, screen: pygame.Surface, tipo: str, cx: int, cy: int, ativo: bool):
        cor = (255, 255, 255) if ativo else (180, 210, 255)

        if tipo == "remate":
            # Stick inclinado / remate
            pygame.draw.line(screen, cor, (cx - 10, cy - 8), (cx + 6, cy + 8), 3)
            pygame.draw.line(screen, cor, (cx + 6, cy + 8), (cx + 12, cy + 5), 3)
        elif tipo == "passe":
            # Bola com rasto de passe
            pygame.draw.circle(screen, cor, (cx + 4, cy - 2), 5)
            pygame.draw.line(screen, cor, (cx - 10, cy + 6), (cx + 2, cy - 1), 2)
        elif tipo == "acelerar":
            # Dupla seta de velocidade / sprint >>
            pygame.draw.polygon(screen, cor, [(cx - 8, cy - 8), (cx, cy), (cx - 8, cy + 8)], 2)
            pygame.draw.polygon(screen, cor, [(cx + 2, cy - 8), (cx + 10, cy), (cx + 2, cy + 8)], 2)
        elif tipo == "defender":
            # Escudo de defesa
            pts = [(cx, cy - 9), (cx + 8, cy - 6), (cx + 7, cy + 3), (cx, cy + 9), (cx - 7, cy + 3), (cx - 8, cy - 6)]
            pygame.draw.polygon(screen, cor, pts, 2)
