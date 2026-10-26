# -*- coding: utf-8 -*-
"""menu.py - Ecrã de Seleção de Equipas oficial (StickMania PAP).

Permite ao jogador escolher a sua equipa (Casa) e a equipa adversária (Visitante)
a partir de todas as equipas disponíveis com logótipos oficiais e cores reais.
"""
import math
import pygame
from settings import WIDTH, HEIGHT, TITLE
from team import EQUIPAS_LISTA, obter_info_equipa, carregar_logo_equipa


class TeamSelectMenu:
    def __init__(self, screen: pygame.Surface, casa_id: str = "fc_porto", fora_id: str = "riba_dave"):
        self.screen = screen
        self.casa_idx = EQUIPAS_LISTA.index(casa_id) if casa_id in EQUIPAS_LISTA else 0
        self.fora_idx = EQUIPAS_LISTA.index(fora_id) if fora_id in EQUIPAS_LISTA else 1

        # Fontes
        self.font_header = pygame.font.SysFont("Arial", 32, bold=True)
        self.font_sub = pygame.font.SysFont("Arial", 16)
        self.font_card_title = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_team_name = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_team_sub = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_vs = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_grid = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_hint = pygame.font.SysFont("Arial", 12)

        # Retângulos interativos
        self._setup_rects()
        self.anim_t = 0.0

    def _setup_rects(self):
        # Cartão Equipa da Casa
        self.rect_casa = pygame.Rect(180, 115, 360, 260)
        self.btn_casa_prev = pygame.Rect(self.rect_casa.left + 16, self.rect_casa.top + 105, 36, 44)
        self.btn_casa_next = pygame.Rect(self.rect_casa.right - 52, self.rect_casa.top + 105, 36, 44)

        # Cartão Equipa Visitante
        self.rect_fora = pygame.Rect(740, 115, 360, 260)
        self.btn_fora_prev = pygame.Rect(self.rect_fora.left + 16, self.rect_fora.top + 105, 36, 44)
        self.btn_fora_next = pygame.Rect(self.rect_fora.right - 52, self.rect_fora.top + 105, 36, 44)

        # Botão Jogar
        self.btn_jogar = pygame.Rect(WIDTH // 2 - 140, 622, 280, 52)

        # Grelha de Equipas (8 equipas)
        card_w, card_h = 118, 92
        gap = 14
        total_w = len(EQUIPAS_LISTA) * card_w + (len(EQUIPAS_LISTA) - 1) * gap
        start_x = (WIDTH - total_w) // 2
        grid_y = 485

        self.grid_rects = []
        for i, eq_id in enumerate(EQUIPAS_LISTA):
            rx = start_x + i * (card_w + gap)
            self.grid_rects.append((eq_id, i, pygame.Rect(rx, grid_y, card_w, card_h)))

    def mudar_casa(self, delta: int):
        self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)
        # Se for igual à de fora, salta mais um
        if self.casa_idx == self.fora_idx:
            self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)

    def mudar_fora(self, delta: int):
        self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)
        # Se for igual à de casa, salta mais um
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)

    def get_equipas(self) -> tuple[str, str]:
        return EQUIPAS_LISTA[self.casa_idx], EQUIPAS_LISTA[self.fora_idx]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        Retorna 'iniciar' se o utilizador confirmou a partida,
        'sair' se fechou a janela, ou None para continuar no menu.
        """
        if event.type == pygame.QUIT:
            return "sair"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return "iniciar"
            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.mudar_casa(-1)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.mudar_casa(1)
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                self.mudar_fora(-1)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.mudar_fora(1)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                               pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8):
                idx = event.key - pygame.K_1
                if 0 <= idx < len(EQUIPAS_LISTA):
                    self.casa_idx = idx

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            mpos = event.pos

            # Botão Iniciar Partida
            if self.btn_jogar.collidepoint(mpos) and event.button == 1:
                return "iniciar"

            # Setas Equipa Casa
            if self.btn_casa_prev.collidepoint(mpos):
                self.mudar_casa(-1)
            elif self.btn_casa_next.collidepoint(mpos):
                self.mudar_casa(1)

            # Setas Equipa Visitante
            elif self.btn_fora_prev.collidepoint(mpos):
                self.mudar_fora(-1)
            elif self.btn_fora_next.collidepoint(mpos):
                self.mudar_fora(1)

            # Clicar nos cartões da grelha de equipas
            for eq_id, idx, r in self.grid_rects:
                if r.collidepoint(mpos):
                    if event.button == 1:
                        # Clique esquerdo: seleciona Equipa da Casa
                        self.casa_idx = idx
                        if self.fora_idx == self.casa_idx:
                            self.fora_idx = (self.casa_idx + 1) % len(EQUIPAS_LISTA)
                    elif event.button == 3:
                        # Clique direito: seleciona Equipa Visitante
                        self.fora_idx = idx
                        if self.casa_idx == self.fora_idx:
                            self.casa_idx = (self.fora_idx + 1) % len(EQUIPAS_LISTA)
                    break

        return None

    def update(self, dt: float):
        self.anim_t += dt

    def draw(self):
        screen = self.screen
        screen.fill((10, 16, 32))

        # ── 1. Título do Cabeçalho ──────────────────────────────────────
        # Faixa decorativa no topo
        pygame.draw.rect(screen, (15, 26, 52), (0, 0, WIDTH, 75))
        pygame.draw.line(screen, (35, 70, 140), (0, 75), (WIDTH, 75), 2)

        t_title = self.font_header.render("STICKMANIA PAP  •  SELEÇÃO DE EQUIPAS", True, (255, 255, 255))
        screen.blit(t_title, (WIDTH // 2 - t_title.get_width() // 2, 12))

        t_sub = self.font_sub.render("Escolhe a tua equipa e a equipa adversária para entrar no ringue", True, (140, 180, 240))
        screen.blit(t_sub, (WIDTH // 2 - t_sub.get_width() // 2, 48))

        # ── 2. Cartões Principais (Casa vs Visitante) ───────────────────
        id_casa, id_fora = self.get_equipas()
        info_casa = obter_info_equipa(id_casa)
        info_fora = obter_info_equipa(id_fora)

        # Cartão Casa
        self._desenhar_card_equipa(
            self.rect_casa, "A TUA EQUIPA (CASA / HUMANO)", info_casa,
            self.btn_casa_prev, self.btn_casa_next, is_casa=True
        )

        # Insígnia VS no Centro
        vs_x = WIDTH // 2
        vs_y = self.rect_casa.centery
        pulso = 1.0 + 0.04 * math.sin(self.anim_t * 4.0)
        raio_vs = int(32 * pulso)

        pygame.draw.circle(screen, (22, 38, 76), (vs_x, vs_y), raio_vs + 4)
        pygame.draw.circle(screen, (220, 180, 40), (vs_x, vs_y), raio_vs, 3)
        t_vs = self.font_vs.render("VS", True, (255, 225, 70))
        screen.blit(t_vs, (vs_x - t_vs.get_width() // 2, vs_y - t_vs.get_height() // 2))

        # Cartão Visitante
        self._desenhar_card_equipa(
            self.rect_fora, "EQUIPA ADVERSÁRIA (VISITANTE / IA)", info_fora,
            self.btn_fora_prev, self.btn_fora_next, is_casa=False
        )

        # ── 3. Grelha Inferior de Todas as Equipas ──────────────────────
        sub_grid = self.font_card_title.render("TODAS AS EQUIPAS DISPONÍVEIS (Clica com o rato para selecionar):", True, (170, 200, 255))
        screen.blit(sub_grid, (WIDTH // 2 - sub_grid.get_width() // 2, 458))

        mpos = pygame.mouse.get_pos()
        for eq_id, idx, r in self.grid_rects:
            info = obter_info_equipa(eq_id)
            is_c = (idx == self.casa_idx)
            is_f = (idx == self.fora_idx)
            hover = r.collidepoint(mpos)

            # Cor de fundo e borda
            if is_c:
                cor_bg = (20, 50, 110)
                cor_borda = (60, 160, 255)
                borda_w = 3
            elif is_f:
                cor_bg = (80, 20, 25)
                cor_borda = (255, 70, 80)
                borda_w = 3
            elif hover:
                cor_bg = (25, 40, 75)
                cor_borda = (140, 190, 255)
                borda_w = 2
            else:
                cor_bg = (14, 22, 44)
                cor_borda = (35, 55, 100)
                borda_w = 1

            pygame.draw.rect(screen, cor_bg, r, border_radius=8)
            pygame.draw.rect(screen, cor_borda, r, borda_w, border_radius=8)

            # Emblema pequeno
            logo_sm = carregar_logo_equipa(eq_id, (44, 44))
            if logo_sm:
                lw, lh = logo_sm.get_size()
                screen.blit(logo_sm, (r.centerx - lw // 2, r.top + 8 + (44 - lh) // 2))

            # Nome curto / Sigla
            t_nm = self.font_grid.render(info["sigla"], True, (255, 255, 255))
            screen.blit(t_nm, (r.centerx - t_nm.get_width() // 2, r.bottom - 32))

            # Tag de Casa / Fora
            if is_c:
                tag = self.font_hint.render("CASA", True, (100, 200, 255))
                screen.blit(tag, (r.centerx - tag.get_width() // 2, r.bottom - 16))
            elif is_f:
                tag = self.font_hint.render("FORA", True, (255, 120, 120))
                screen.blit(tag, (r.centerx - tag.get_width() // 2, r.bottom - 16))
            else:
                tag = self.font_hint.render(f"#{idx+1}", True, (90, 120, 170))
                screen.blit(tag, (r.centerx - tag.get_width() // 2, r.bottom - 16))

        # ── 4. Botão Grande Iniciar Partida ─────────────────────────────
        hover_jogar = self.btn_jogar.collidepoint(mpos)
        if hover_jogar:
            cor_btn_bg = (30, 160, 80)
            cor_btn_bd = (90, 240, 140)
        else:
            cor_btn_bg = (20, 130, 60)
            cor_btn_bd = (50, 200, 100)

        pygame.draw.rect(screen, cor_btn_bg, self.btn_jogar, border_radius=10)
        pygame.draw.rect(screen, cor_btn_bd, self.btn_jogar, 2, border_radius=10)

        t_jogar = self.font_btn.render("INICIAR PARTIDA  ►", True, (255, 255, 255))
        screen.blit(t_jogar, (self.btn_jogar.centerx - t_jogar.get_width() // 2,
                              self.btn_jogar.centery - t_jogar.get_height() // 2))

        # Atalhos rápidos de teclado
        hint = self.font_hint.render("Atalhos: [A/D ou Setas Esq/Dir] Muda Casa  |  [W/S ou Setas Cima/Baixo] Muda Fora  |  [ENTER] Começar", True, (120, 150, 200))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 686))

    def _desenhar_card_equipa(self, rect: pygame.Rect, titulo: str, info: dict,
                              btn_prev: pygame.Rect, btn_next: pygame.Rect, is_casa: bool):
        screen = self.screen
        cor_primaria = info.get("cor_primaria", (20, 50, 120))
        mpos = pygame.mouse.get_pos()

        # Fundo do cartão com contorno com a cor da equipa
        pygame.draw.rect(screen, (14, 22, 44), rect, border_radius=12)
        # Cabeçalho do cartão com a cor da equipa
        header_r = pygame.Rect(rect.left, rect.top, rect.width, 36)
        pygame.draw.rect(screen, cor_primaria, header_r, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(screen, (50, 90, 180), rect, 2, border_radius=12)

        t_tit = self.font_card_title.render(titulo, True, (255, 255, 255))
        screen.blit(t_tit, (rect.centerx - t_tit.get_width() // 2, rect.top + 9))

        # Logótipo Oficial Grande (100x100)
        logo = carregar_logo_equipa(info["id"], (106, 106))
        logo_y = rect.top + 52
        if logo is not None:
            lw, lh = logo.get_size()
            screen.blit(logo, (rect.centerx - lw // 2, logo_y + (106 - lh) // 2))

        # Nome da Equipa
        t_nm = self.font_team_name.render(info["nome"], True, (255, 255, 255))
        screen.blit(t_nm, (rect.centerx - t_nm.get_width() // 2, rect.top + 172))

        # Sigla e Detalhes
        sigla_txt = f"SIGLA OFICIAL: {info['sigla']}   •   CORES DO CLUBE"
        t_sig = self.font_team_sub.render(sigla_txt, True, (150, 185, 240))
        screen.blit(t_sig, (rect.centerx - t_sig.get_width() // 2, rect.top + 206))

        # Amostras das cores oficiais do clube
        cor_p = info.get("cor_primaria", (255, 255, 255))
        cor_s = info.get("cor_secundaria", (255, 255, 255))
        c_x = rect.centerx - 24
        c_y = rect.top + 228
        pygame.draw.rect(screen, cor_p, (c_x, c_y, 22, 14), border_radius=3)
        pygame.draw.rect(screen, (255, 255, 255), (c_x, c_y, 22, 14), 1, border_radius=3)
        pygame.draw.rect(screen, cor_s, (c_x + 28, c_y, 22, 14), border_radius=3)
        pygame.draw.rect(screen, (255, 255, 255), (c_x + 28, c_y, 22, 14), 1, border_radius=3)

        # Botões de seta < e >
        for btn, seta in [(btn_prev, "◄"), (btn_next, "►")]:
            hover = btn.collidepoint(mpos)
            bg_c = (35, 65, 130) if hover else (22, 38, 76)
            bd_c = (80, 140, 255) if hover else (45, 80, 160)
            pygame.draw.rect(screen, bg_c, btn, border_radius=6)
            pygame.draw.rect(screen, bd_c, btn, 1, border_radius=6)
            t_seta = self.font_btn.render(seta, True, (255, 255, 255))
            screen.blit(t_seta, (btn.centerx - t_seta.get_width() // 2, btn.centery - t_seta.get_height() // 2))
