# -*- coding: utf-8 -*-
"""ui.py - Interface do jogo (Mini-mapa tático, Cartão do Jogador, Joystick e Botões de Ação).

Desenvolvido para corresponder à interface moderna do mockup:
  1. Mini-mapa em tempo real (radar tático com jogadores e bola)
  2. Cartão do jogador selecionado (foto/avatar, número, nome, atributos)
  3. Joystick virtual / D-pad com setas direcionais reativas
  4. Botões de ação arcade (Remate, Passe, Acelerar, Defender)
"""
import pygame
from settings import *
from team import carregar_logo_equipa, obter_info_equipa
from cores import cor_texto_sobre, cor_visivel_em_escuro, clarear


class HUDController:
    def __init__(self):
        self.font_time = pygame.font.SysFont("Arial", 19, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_score = pygame.font.SysFont("Arial", 20, bold=True)
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
    # Marcador Superior Idêntico ao Mockup                                #
    # ================================================================== #

    def draw_top_bar(self, screen: pygame.Surface, game):
        # O marcador fica sobreposto à bancada de público no canto superior esquerdo
        sc_x = 28
        sc_y = 12
        card_w = 230
        timer_w = 95
        total_h = 52
        linha_h = total_h // 2

        info_casa = obter_info_equipa(getattr(game, "equipa_casa_id", "fc_porto"))
        info_fora = obter_info_equipa(getattr(game, "equipa_fora_id", "riba_dave"))

        # Cores das linhas = cores do equipamento usado nesta partida
        kit_casa = getattr(game, "kit_casa", None)
        kit_fora = getattr(game, "kit_fora", None)

        # ── 1. Linha da Equipa da Casa ───────────────────────────────────
        cor_casa = kit_casa["principal"] if kit_casa else info_casa.get("cor_primaria", (15, 60, 160))
        txt_casa = cor_texto_sobre(cor_casa)
        r_casa = pygame.Rect(sc_x, sc_y, card_w, linha_h)
        pygame.draw.rect(screen, cor_casa, r_casa, border_top_left_radius=8)

        # Logótipo da equipa da casa
        self._desenhar_logo_placar(screen, info_casa["id"], sc_x + 8, sc_y + 2, info_casa)

        # Nome da equipa
        t_casa = self.font_title.render(info_casa["nome"], True, txt_casa)
        screen.blit(t_casa, (sc_x + 38, sc_y + 4))

        # Faltas e Resultado da equipa da casa
        f_casa = getattr(game, "faltas_azul", 0)
        cor_f_c = (255, 195, 60) if f_casa >= 8 else txt_casa
        t_f_casa = self.font_key.render(f"F:{f_casa}", True, cor_f_c)
        screen.blit(t_f_casa, (sc_x + card_w - 58, sc_y + 8))

        g_casa = self.font_score.render(str(game.golos_azul), True, txt_casa)
        screen.blit(g_casa, (sc_x + card_w - 24, sc_y + 2))

        # ── 2. Linha da Equipa Visitante ─────────────────────────────────
        cor_fora = kit_fora["principal"] if kit_fora else info_fora.get("cor_primaria", (135, 20, 25))
        txt_fora = cor_texto_sobre(cor_fora)
        r_fora = pygame.Rect(sc_x, sc_y + linha_h, card_w, linha_h)
        pygame.draw.rect(screen, cor_fora, r_fora, border_bottom_left_radius=8)

        # Logótipo da equipa visitante
        self._desenhar_logo_placar(screen, info_fora["id"], sc_x + 8, sc_y + linha_h + 2, info_fora)

        # Nome da equipa
        t_fora = self.font_title.render(info_fora["nome"], True, txt_fora)
        screen.blit(t_fora, (sc_x + 38, sc_y + linha_h + 4))

        # Faltas e Resultado da equipa visitante
        f_fora = getattr(game, "faltas_vermelho", 0)
        cor_f_f = (255, 195, 60) if f_fora >= 8 else txt_fora
        t_f_fora = self.font_key.render(f"F:{f_fora}", True, cor_f_f)
        screen.blit(t_f_fora, (sc_x + card_w - 58, sc_y + linha_h + 8))

        g_fora = self.font_score.render(str(game.golos_vermelho), True, txt_fora)
        screen.blit(g_fora, (sc_x + card_w - 24, sc_y + linha_h + 2))

        # Divisória subtil entre as duas linhas
        pygame.draw.line(screen, (0, 0, 0, 100), (sc_x, sc_y + linha_h), (sc_x + card_w, sc_y + linha_h), 1)

        # ── 3. Bloco do Cronómetro e Parte (à direita do placar) ────────
        time_x = sc_x + card_w
        # Fundo azul escuro translúcido com cantos direitos arredondados
        surf_timer = pygame.Surface((timer_w, total_h), pygame.SRCALPHA)
        pygame.draw.rect(surf_timer, (10, 18, 36, 235), (0, 0, timer_w, total_h),
                         border_top_right_radius=8, border_bottom_right_radius=8)
        screen.blit(surf_timer, (time_x, sc_y))

        # Tempo (ex: 12:34)
        mins = max(0, int(game.tempo_restante)) // 60
        segs = max(0, int(game.tempo_restante)) % 60
        t_cron = self.font_time.render(f"{mins:02d}:{segs:02d}", True, (255, 255, 255))
        screen.blit(t_cron, (time_x + timer_w // 2 - t_cron.get_width() // 2, sc_y + 4))

        # Parte (ex: 1.ª Parte / 2.ª Parte)
        f_parte = pygame.font.SysFont("Arial", 11, bold=True)
        t_parte = f_parte.render(f"{game.parte}.ª Parte", True, (160, 190, 230))
        screen.blit(t_parte, (time_x + timer_w // 2 - t_parte.get_width() // 2, sc_y + 28))

        # Moldura exterior do placar completo
        placar_completo = pygame.Rect(sc_x, sc_y, card_w + timer_w, total_h)
        pygame.draw.rect(screen, (40, 75, 140), placar_completo, 1, border_radius=8)

        # ── 4. Badge de Dificuldade da IA ──────────────────────────────
        dif_str = getattr(game, "dificuldade", "normal").lower()
        nomes_dif = {"facil": "FÁCIL", "normal": "NORMAL", "dificil": "DIFÍCIL"}
        cores_dif = {"facil": (60, 210, 110), "normal": (70, 160, 255), "dificil": (255, 75, 75)}
        lbl_dif = nomes_dif.get(dif_str, "NORMAL")
        cor_badge = cores_dif.get(dif_str, (70, 160, 255))

        f_badge = pygame.font.SysFont("Arial", 10, bold=True)
        txt_b = f_badge.render(f"IA: {lbl_dif}", True, (255, 255, 255))
        bw = txt_b.get_width() + 16
        bh = 22
        bx = time_x + timer_w + 10
        by = sc_y + (total_h - bh) // 2
        pygame.draw.rect(screen, (12, 22, 42), (bx, by, bw, bh), border_radius=5)
        pygame.draw.rect(screen, cor_badge, (bx, by, bw, bh), 1, border_radius=5)
        screen.blit(txt_b, (bx + 8, by + 4))

        # ── 5. Botão de Pausa (canto superior direito) ──────────────────
        pause_r = pygame.Rect(WIDTH - 52, 14, 38, 38)
        pygame.draw.rect(screen, (16, 26, 52), pause_r, border_radius=6)
        pygame.draw.rect(screen, (40, 80, 160), pause_r, 1, border_radius=6)
        # Ícone ||
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 44, 23, 6, 20), border_radius=2)
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 34, 23, 6, 20), border_radius=2)

    def _desenhar_logo_placar(self, surf, equipa_id: str, x: int, y: int, info: dict):
        """Desenha o logótipo oficial ou um emblema estilizado se a imagem não existir."""
        logo = carregar_logo_equipa(equipa_id, (22, 22))
        if logo is not None:
            lw, lh = logo.get_size()
            surf.blit(logo, (x + (22 - lw) // 2, y + (22 - lh) // 2))
        else:
            # Emblema de recurso com escudo circular
            cor_bg = info.get("cor_secundaria", (255, 255, 255))
            cor_fg = info.get("cor_primaria", (20, 60, 180))
            r = pygame.Rect(x, y, 22, 22)
            pygame.draw.circle(surf, cor_bg, r.center, 10)
            pygame.draw.circle(surf, cor_fg, r.center, 10, 2)
            f = pygame.font.SysFont("Arial", 8, bold=True)
            sigla = info.get("sigla", "FCP")
            t = f.render(sigla[:3], True, cor_fg)
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

        # Linha central e círculo central (na cor das linhas do ringue da casa)
        cor_linhas = cor_visivel_em_escuro(getattr(game.rink, "cor_linhas", (50, 110, 230)), 80)
        mcx = map_r.centerx
        mcy = map_r.centery
        pygame.draw.line(screen, cor_linhas, (mcx, map_r.top + 2), (mcx, map_r.bottom - 2), 1)
        pygame.draw.circle(screen, cor_linhas, (mcx, mcy), 14, 1)

        # Cores dos pontos = cores dos equipamentos (clareadas para se verem no fundo escuro)
        kit_c = getattr(game, "kit_casa", None)
        kit_f = getattr(game, "kit_fora", None)
        cor_c = cor_visivel_em_escuro(kit_c["principal"] if kit_c else (40, 130, 240))
        cor_f = cor_visivel_em_escuro(kit_f["principal"] if kit_f else (240, 50, 50))

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

        # Equipa visitante
        for j in game.equipa_vermelha:
            pos = to_map(j.pos_x, j.pos_y)
            pygame.draw.circle(screen, (0, 0, 0), pos, 4)
            pygame.draw.circle(screen, cor_f, pos, 3)

        # Guarda-redes visitante (quadrado para se distinguir)
        gx, gy = to_map(game.gr_vermelho.pos_x, game.gr_vermelho.pos_y)
        pygame.draw.rect(screen, clarear(cor_f, 0.3), (gx - 3, gy - 3, 6, 6))

        # Equipa da casa
        for j in game.equipa_azul:
            pos = to_map(j.pos_x, j.pos_y)
            if j == game.jogador_humano:
                # Jogador controlado: realçado com um anel branco
                pygame.draw.circle(screen, (255, 255, 255), pos, 6, 1)
            pygame.draw.circle(screen, (0, 0, 0), pos, 4)
            pygame.draw.circle(screen, cor_c, pos, 3)

        # Guarda-redes da casa
        gx, gy = to_map(game.gr_azul.pos_x, game.gr_azul.pos_y)
        pygame.draw.rect(screen, clarear(cor_c, 0.3), (gx - 3, gy - 3, 6, 6))

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
        kit = getattr(jogador, "kit", None)
        cor_kit = cor_visivel_em_escuro(kit["principal"]) if kit else (60, 120, 230)
        pygame.draw.rect(screen, (20, 35, 75), av_rect, border_radius=6)
        pygame.draw.rect(screen, cor_kit, av_rect, 2, border_radius=6)

        # Desenhar avatar estilizado (sprite recortado ou cabeça do jogador)
        if hasattr(jogador, "image"):
            # Escalar sprite do jogador centrado no quadrado do avatar
            thumb = pygame.transform.scale(jogador.image, (64, 64))
            screen.blit(thumb, (av_rect.centerx - 32, av_rect.centery - 32))

        # Nome e Número
        t_nome = self.font_card_nome.render(f"{jogador.numero}  {jogador.nome}", True, (255, 255, 255))
        screen.blit(t_nome, (rect.left + 104, rect.top + 14))

        # Emblema da equipa do jogador no canto do cartão
        eq_id = getattr(jogador, "equipa_id", "fc_porto")
        logo_card = carregar_logo_equipa(eq_id, (32, 32))
        if logo_card is not None:
            lw, lh = logo_card.get_size()
            screen.blit(logo_card, (rect.right - 44 + (32 - lw) // 2, rect.top + 14 + (32 - lh) // 2))

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

    def draw_foul_banner(self, screen: pygame.Surface, game):
        """Desenha a notificação oficial quando é assinalada uma falta, livre ou penálti."""
        if not getattr(game, "_falta_ativa", False) or getattr(game, "_falta_timer", 0.0) <= 0:
            return

        tipo = getattr(game, "_falta_tipo", "livre")
        bw = 540
        bh = 72
        bx = (WIDTH - bw) // 2
        by = RINK_Y + 16

        if tipo == "penalti":
            cor_borda = (255, 70, 70)
            cor_bg = (55, 12, 18, 235)
            cor_titulo = (255, 110, 110)
        elif tipo == "livre_direto":
            cor_borda = (255, 185, 30)
            cor_bg = (52, 38, 10, 235)
            cor_titulo = (255, 220, 60)
        else:
            cor_borda = (245, 205, 55)
            cor_bg = (18, 32, 60, 235)
            cor_titulo = (255, 235, 80)

        surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(surf, cor_bg, (0, 0, bw, bh), border_radius=10)
        pygame.draw.rect(surf, cor_borda, (0, 0, bw, bh), 2, border_radius=10)
        screen.blit(surf, (bx, by))

        # Ícone de Apito / Alerta
        cx_ico = bx + 36
        cy_ico = by + bh // 2
        pygame.draw.circle(screen, cor_borda, (cx_ico, cy_ico), 18)
        f_ico = pygame.font.SysFont("Arial", 18, bold=True)
        t_ico = f_ico.render("!", True, (10, 16, 32))
        screen.blit(t_ico, (cx_ico - t_ico.get_width() // 2, cy_ico - t_ico.get_height() // 2))

        # Título da Falta
        f_tit = pygame.font.SysFont("Arial", 17, bold=True)
        msg_tit = getattr(game, "_msg_falta", "FALTA!")
        t_tit = f_tit.render(msg_tit, True, cor_titulo)
        screen.blit(t_tit, (bx + 66, by + 12))

        # Subtítulo com detalhes
        f_sub = pygame.font.SysFont("Arial", 12)
        msg_sub = getattr(game, "_msg_falta_sub", "")
        t_sub = f_sub.render(msg_sub, True, (220, 235, 255))
        screen.blit(t_sub, (bx + 66, by + 40))
