# -*- coding: utf-8 -*-
"""menu.py - Ecrãs de menu do StickMania PAP.

  • MenuPrincipal   - ecrã inicial (Jogar, Controlos, Sair)
  • EcraControlos   - lista de teclas
  • TeamSelectMenu  - seleção das equipas, do equipamento e da dificuldade
  • MenuPausa       - pausa durante a partida
  • EcraFimJogo     - resultado final

Cada ecrã tem handle_event(event) -> ação (str) ou None, update(dt) e draw().
Quem decide o que fazer com a ação é a classe Game (game.py).
"""
import math
import pygame

from settings import WIDTH, HEIGHT
from team import EQUIPAS_LISTA, obter_info_equipa, carregar_logo_equipa
from ai import DIFICULDADES
from cores import (definir_equipamentos, cor_linhas_campo, cor_visivel_em_escuro,
                   cor_texto_sobre, misturar)
from componentes import (fonte, texto, painel, fundo_menu, Botao, ListaBotoes,
                         sprite_equipamento, amostra_cor, faixa_equipa, escurecer_ecra,
                         COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE, COR_PAINEL)


# ====================================================================== #
# Menu Principal                                                         #
# ====================================================================== #

class MenuPrincipal:
    def __init__(self, screen: pygame.Surface, casa_id: str = "fc_porto", fora_id: str = "riba_dave"):
        self.screen = screen
        self.casa_id = casa_id
        self.fora_id = fora_id
        self.t = 0.0
        bw, bh, x = 340, 58, WIDTH // 2 - 170
        self.lista = ListaBotoes([
            Botao((x, 340, bw, bh), "JOGAR", "jogar", cor=(40, 190, 100), tamanho_texto=24, icone="►"),
            Botao((x, 414, bw, bh), "CONTROLOS", "controlos", cor=(50, 140, 255), tamanho_texto=22),
            Botao((x, 488, bw, bh), "SAIR", "sair", cor=(230, 70, 70), tamanho_texto=22),
        ])

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt

    def draw(self):
        s = self.screen
        kit_casa, kit_fora = definir_equipamentos(self.casa_id, self.fora_id)
        fundo_menu(s, self.t, kit_casa["principal"], kit_fora["principal"])

        # Título com um ligeiro "respirar"
        escala = 1.0 + 0.015 * math.sin(self.t * 2.0)
        f = fonte(int(86 * escala))
        titulo = f.render("STICKMANIA", True, COR_TEXTO)
        sombra = f.render("STICKMANIA", True, (0, 0, 0))
        tr = titulo.get_rect(center=(WIDTH // 2, 150))
        s.blit(sombra, (tr.x + 4, tr.y + 5))
        s.blit(titulo, tr)
        # Sublinhado dourado
        pygame.draw.rect(s, COR_DESTAQUE, (WIDTH // 2 - 150, tr.bottom + 4, 300, 4), border_radius=2)
        texto(s, "HÓQUEI EM PATINS 2D", 24, COR_DESTAQUE, (WIDTH // 2, tr.bottom + 32))
        texto(s, "Escolhe o teu clube, entra no ringue e marca golos!", 15, COR_TEXTO_SUAVE,
              (WIDTH // 2, tr.bottom + 62), negrito=False)

        # Jogadores decorativos com os equipamentos das equipas escolhidas
        for kit, eq_id, cx, virar in ((kit_casa, self.casa_id, 230, False),
                                      (kit_fora, self.fora_id, WIDTH - 230, True)):
            pygame.draw.ellipse(s, (0, 0, 0), (cx - 70, 548, 140, 22))
            img = sprite_equipamento(kit, 220, self.t, virar=virar)
            s.blit(img, img.get_rect(midbottom=(cx, 572)))
            logo = carregar_logo_equipa(eq_id, (70, 70))
            if logo:
                s.blit(logo, logo.get_rect(center=(cx, 345)))
            texto(s, obter_info_equipa(eq_id)["nome"], 16, COR_TEXTO, (cx, 600))

        self.lista.draw(s)

        texto(s, "↑ ↓ para escolher  •  ENTER para confirmar", 13, (110, 140, 190),
              (WIDTH // 2, 580), negrito=False)
        texto(s, "Projeto PAP  •  Rafael Silveira  •  2026/2027", 13, (90, 115, 160),
              (WIDTH // 2, HEIGHT - 24), negrito=False)


# ====================================================================== #
# Ecrã de Controlos                                                      #
# ====================================================================== #

CONTROLOS = [
    ("MOVIMENTO", [
        ("W A S D  /  Setas", "Mover o jogador"),
        ("SHIFT", "Sprint (correr mais rápido)"),
        ("C  /  TAB  /  ESPAÇO", "Trocar para o jogador mais perto da bola"),
    ]),
    ("COM A BOLA", [
        ("Z", "Passe para o colega mais bem colocado"),
        ("X", "Abrir a mira de remate"),
        ("X  /  Clique", "Rematar (a força depende da barra)"),
        ("Rato", "Apontar o remate"),
    ]),
    ("JOGO", [
        ("ESC  /  P", "Pausa (ESC também cancela a mira)"),
        ("F4", "Mudar a dificuldade da IA"),
        ("F3", "Modo de depuração (FPS)"),
    ]),
]


class EcraControlos:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.t = 0.0
        self.btn_voltar = Botao((WIDTH // 2 - 140, HEIGHT - 92, 280, 52), "VOLTAR", "voltar",
                                cor=(50, 140, 255), icone="◄")

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                                          pygame.K_KP_ENTER, pygame.K_BACKSPACE):
            return "voltar"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.btn_voltar.por_cima(event.pos):
            return "voltar"
        return None

    def update(self, dt: float):
        self.t += dt

    def draw(self, por_cima_do_jogo: bool = False):
        s = self.screen
        if por_cima_do_jogo:
            escurecer_ecra(s, 200)
        else:
            fundo_menu(s, self.t)

        texto(s, "CONTROLOS", 44, COR_TEXTO, (WIDTH // 2, 70), sombra=True)
        pygame.draw.rect(s, COR_DESTAQUE, (WIDTH // 2 - 90, 100, 180, 4), border_radius=2)

        caixa = pygame.Rect(170, 130, WIDTH - 340, 470)
        painel(s, caixa, alpha=235)

        y = caixa.top + 28
        for secao, linhas in CONTROLOS:
            texto(s, secao, 15, COR_DESTAQUE, (caixa.left + 40, y), ancora="midleft")
            pygame.draw.line(s, (40, 65, 120), (caixa.left + 40, y + 14), (caixa.right - 40, y + 14), 1)
            y += 34
            for tecla, descricao in linhas:
                # "Tecla" desenhada como uma tecla de teclado
                f = fonte(14)
                img = f.render(tecla, True, (255, 255, 255))
                tecla_r = pygame.Rect(caixa.left + 40, y - 14, img.get_width() + 22, 28)
                pygame.draw.rect(s, (30, 48, 92), tecla_r, border_radius=6)
                pygame.draw.rect(s, (90, 130, 210), tecla_r, 1, border_radius=6)
                pygame.draw.line(s, (12, 20, 40), (tecla_r.left + 4, tecla_r.bottom), (tecla_r.right - 4, tecla_r.bottom), 2)
                s.blit(img, img.get_rect(center=tecla_r.center))
                texto(s, descricao, 15, (210, 225, 250), (caixa.left + 290, y), ancora="midleft", negrito=False)
                y += 34
            y += 10

        self.btn_voltar.draw(s, pygame.mouse.get_pos())


# ====================================================================== #
# Seleção de Equipas                                                     #
# ====================================================================== #

class TeamSelectMenu:
    def __init__(self, screen: pygame.Surface, casa_id: str = "fc_porto",
                 fora_id: str = "riba_dave", dificuldade: str = "normal"):
        self.screen = screen
        self.casa_idx = EQUIPAS_LISTA.index(casa_id) if casa_id in EQUIPAS_LISTA else 0
        self.fora_idx = EQUIPAS_LISTA.index(fora_id) if fora_id in EQUIPAS_LISTA else 1
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.casa_idx + 1) % len(EQUIPAS_LISTA)
        self.dificuldade = dificuldade if dificuldade in DIFICULDADES else "normal"
        self.anim_t = 0.0
        self._setup_rects()

    # ------------------------------------------------------------------ #
    def _setup_rects(self):
        self.btn_voltar = Botao((24, 18, 130, 40), "VOLTAR", "voltar", cor=(50, 140, 255),
                                tamanho_texto=15, icone="◄")

        self.rect_casa = pygame.Rect(130, 96, 420, 252)
        self.rect_fora = pygame.Rect(WIDTH - 130 - 420, 96, 420, 252)
        for nome, card in (("casa", self.rect_casa), ("fora", self.rect_fora)):
            prev = pygame.Rect(card.left + 12, card.top + 104, 34, 46)
            nxt = pygame.Rect(card.right - 46, card.top + 104, 34, 46)
            setattr(self, f"btn_{nome}_prev", prev)
            setattr(self, f"btn_{nome}_next", nxt)

        # Grelha com todas as equipas
        card_w, card_h, gap = 118, 88, 14
        total_w = len(EQUIPAS_LISTA) * card_w + (len(EQUIPAS_LISTA) - 1) * gap
        start_x = (WIDTH - total_w) // 2
        self.grid_rects = []
        for i, eq_id in enumerate(EQUIPAS_LISTA):
            r = pygame.Rect(start_x + i * (card_w + gap), 384, card_w, card_h)
            self.grid_rects.append((eq_id, i, r))

        # Dificuldade
        cx = WIDTH // 2
        self.botoes_dif = [
            Botao((cx - 222, 512, 140, 38), "FÁCIL", "facil", cor=(40, 180, 90), tamanho_texto=17),
            Botao((cx - 70, 512, 140, 38), "NORMAL", "normal", cor=(50, 140, 255), tamanho_texto=17),
            Botao((cx + 82, 512, 140, 38), "DIFÍCIL", "dificil", cor=(230, 70, 70), tamanho_texto=17),
        ]
        self.btn_jogar = Botao((WIDTH // 2 - 160, 596, 320, 56), "INICIAR PARTIDA", "iniciar",
                               cor=(40, 190, 100), tamanho_texto=22, icone="►")

    # ------------------------------------------------------------------ #
    # Lógica                                                             #
    # ------------------------------------------------------------------ #
    def mudar_casa(self, delta: int):
        self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)
        if self.casa_idx == self.fora_idx:
            self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)

    def mudar_fora(self, delta: int):
        self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)

    def escolher_casa(self, idx: int):
        """Escolhe a equipa da casa; se for a mesma da visitante, a visitante passa à seguinte."""
        self.casa_idx = idx
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.casa_idx + 1) % len(EQUIPAS_LISTA)

    def escolher_fora(self, idx: int):
        self.fora_idx = idx
        if self.casa_idx == self.fora_idx:
            self.casa_idx = (self.fora_idx + 1) % len(EQUIPAS_LISTA)

    def get_equipas(self) -> tuple[str, str]:
        return EQUIPAS_LISTA[self.casa_idx], EQUIPAS_LISTA[self.fora_idx]

    def get_dificuldade(self) -> str:
        return self.dificuldade

    def ciclar_dificuldade(self):
        ordem = ["facil", "normal", "dificil"]
        idx = ordem.index(self.dificuldade) if self.dificuldade in ordem else 1
        self.dificuldade = ordem[(idx + 1) % len(ordem)]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Devolve 'iniciar', 'voltar', 'sair' ou None."""
        if event.type == pygame.QUIT:
            return "sair"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return "iniciar"
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "voltar"
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.mudar_casa(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.mudar_casa(1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.mudar_fora(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.mudar_fora(1)
            elif event.key == pygame.K_TAB:
                self.ciclar_dificuldade()
            elif event.key in (pygame.K_f, pygame.K_F1):
                self.dificuldade = "facil"
            elif event.key in (pygame.K_n, pygame.K_F2):
                self.dificuldade = "normal"
            elif event.key in (pygame.K_g, pygame.K_F3):
                self.dificuldade = "dificil"
            elif pygame.K_1 <= event.key <= pygame.K_8:
                idx = event.key - pygame.K_1
                if 0 <= idx < len(EQUIPAS_LISTA):
                    self.escolher_casa(idx)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            mpos = event.pos
            if event.button == 1:
                if self.btn_jogar.por_cima(mpos):
                    return "iniciar"
                if self.btn_voltar.por_cima(mpos):
                    return "voltar"
                for b in self.botoes_dif:
                    if b.por_cima(mpos):
                        self.dificuldade = b.acao
                        return None
                if self.btn_casa_prev.collidepoint(mpos):
                    self.mudar_casa(-1)
                elif self.btn_casa_next.collidepoint(mpos):
                    self.mudar_casa(1)
                elif self.btn_fora_prev.collidepoint(mpos):
                    self.mudar_fora(-1)
                elif self.btn_fora_next.collidepoint(mpos):
                    self.mudar_fora(1)

            for eq_id, idx, r in self.grid_rects:
                if r.collidepoint(mpos):
                    if event.button == 1:
                        self.escolher_casa(idx)     # clique esquerdo = casa
                    else:
                        self.escolher_fora(idx)     # clique direito = visitante
                    break
        return None

    def update(self, dt: float):
        self.anim_t += dt

    # ------------------------------------------------------------------ #
    # Desenho                                                            #
    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        id_casa, id_fora = self.get_equipas()
        info_casa, info_fora = obter_info_equipa(id_casa), obter_info_equipa(id_fora)
        kit_casa, kit_fora = definir_equipamentos(id_casa, id_fora)
        mpos = pygame.mouse.get_pos()

        fundo_menu(s, self.anim_t, kit_casa["principal"], kit_fora["principal"])

        # Cabeçalho
        texto(s, "SELEÇÃO DE EQUIPAS", 34, COR_TEXTO, (WIDTH // 2, 34), sombra=True)
        texto(s, "Escolhe a tua equipa e o adversário  •  as cores do equipamento e do ringue mudam com a escolha",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, 68), negrito=False)
        self.btn_voltar.draw(s, mpos)

        # Cartões principais
        self._desenhar_card(self.rect_casa, "A TUA EQUIPA  •  CASA", info_casa, kit_casa,
                            self.btn_casa_prev, self.btn_casa_next, virar=False)
        self._desenhar_card(self.rect_fora, "ADVERSÁRIO  •  VISITANTE (IA)", info_fora, kit_fora,
                            self.btn_fora_prev, self.btn_fora_next, virar=True)

        # VS + pré-visualização do ringue
        self._desenhar_centro(info_casa)

        # Grelha
        texto(s, "TODAS AS EQUIPAS   •   clique esquerdo = casa   •   clique direito = visitante",
              13, (170, 200, 255), (WIDTH // 2, 368))
        for eq_id, idx, r in self.grid_rects:
            self._desenhar_mini_card(eq_id, idx, r, mpos)

        # Dificuldade
        texto(s, "DIFICULDADE DA IA", 14, (200, 220, 255), (WIDTH // 2, 496))
        for b in self.botoes_dif:
            b.ativo = (b.acao == self.dificuldade)
            b.draw(s, mpos)
        desc = DIFICULDADES.get(self.dificuldade, {}).get("descricao", "")
        texto(s, desc, 13, (160, 195, 240), (WIDTH // 2, 568), negrito=False)

        # Botão principal (pulsa ligeiramente para chamar a atenção)
        self.btn_jogar.draw(s, mpos, focado=(math.sin(self.anim_t * 3) > 0.6))

        texto(s, "[A/D] casa   [W/S] visitante   [1-8] escolher casa   [TAB] dificuldade   [ENTER] começar   [ESC] voltar",
              12, (110, 140, 190), (WIDTH // 2, 682), negrito=False)

    def _desenhar_card(self, rect, titulo, info, kit, btn_prev, btn_next, virar: bool):
        s = self.screen
        cor = info.get("cor_primaria", (20, 50, 120))
        mpos = pygame.mouse.get_pos()

        painel(s, rect, cor=COR_PAINEL, borda=misturar(cor_visivel_em_escuro(cor), (255, 255, 255), 0.2),
               largura_borda=2)
        faixa_equipa(s, (rect.left, rect.top, rect.width, 38), cor)
        texto(s, titulo, 14, cor_texto_sobre(cor), (rect.centerx, rect.top + 19))

        # Emblema (esquerda) e jogador com o equipamento (direita)
        logo = carregar_logo_equipa(info["id"], (104, 104))
        if logo:
            s.blit(logo, logo.get_rect(center=(rect.left + 140, rect.top + 108)))
        cx_kit = rect.right - 140
        pygame.draw.ellipse(s, (6, 10, 22), (cx_kit - 34, rect.top + 156, 68, 12))
        jogador = sprite_equipamento(kit, 120, self.anim_t, virar=virar)
        s.blit(jogador, jogador.get_rect(midbottom=(cx_kit, rect.top + 166)))

        # Nome e detalhes
        texto(s, info["nome"], 24, COR_TEXTO, (rect.centerx, rect.top + 190))
        linha = f"{info['sigla']}   •   EQUIPAMENTO {'ALTERNATIVO' if kit['alternativo'] else 'PRINCIPAL'}"
        cor_linha = COR_DESTAQUE if kit["alternativo"] else (150, 185, 240)
        texto(s, linha, 12, cor_linha, (rect.centerx, rect.top + 216))

        # Amostras de cor: camisola e detalhes
        x0 = rect.centerx - 26
        amostra_cor(s, kit["principal"], (x0, rect.top + 228, 22, 14))
        amostra_cor(s, kit["secundaria"], (x0 + 30, rect.top + 228, 22, 14))

        for btn, seta in ((btn_prev, "◄"), (btn_next, "►")):
            hover = btn.collidepoint(mpos)
            pygame.draw.rect(s, (35, 65, 130) if hover else (22, 38, 76), btn, border_radius=8)
            pygame.draw.rect(s, (110, 160, 255) if hover else (45, 80, 160), btn, 1, border_radius=8)
            texto(s, seta, 18, (255, 255, 255), btn.center)

    def _desenhar_centro(self, info_casa):
        s = self.screen
        cx = WIDTH // 2
        cy = 150
        pulso = 1.0 + 0.05 * math.sin(self.anim_t * 4.0)
        raio = int(36 * pulso)
        pygame.draw.circle(s, (22, 38, 76), (cx, cy), raio + 5)
        pygame.draw.circle(s, COR_DESTAQUE, (cx, cy), raio, 3)
        texto(s, "VS", 30, (255, 225, 70), (cx, cy))

        # Mini ringue com as linhas na cor da equipa da casa
        r = pygame.Rect(cx - 78, 222, 156, 88)
        cor_l = cor_linhas_campo(info_casa.get("cor_primaria", (30, 95, 210)))
        pygame.draw.rect(s, (235, 238, 245), r.inflate(8, 8), border_radius=18)
        pygame.draw.rect(s, (224, 178, 122), r, border_radius=14)
        for y in range(r.top + 6, r.bottom, 8):
            pygame.draw.line(s, (210, 165, 110), (r.left + 6, y), (r.right - 6, y), 1)
        pygame.draw.line(s, cor_l, (r.centerx, r.top + 2), (r.centerx, r.bottom - 2), 2)
        pygame.draw.circle(s, cor_l, r.center, 16, 2)
        pygame.draw.rect(s, cor_l, (r.left + 14, r.centery - 24, 26, 48), 2)
        pygame.draw.rect(s, cor_l, (r.right - 40, r.centery - 24, 26, 48), 2)
        texto(s, "RINGUE DA CASA", 11, (170, 200, 255), (cx, r.bottom + 18))

    def _desenhar_mini_card(self, eq_id, idx, r, mpos):
        s = self.screen
        info = obter_info_equipa(eq_id)
        e_casa, e_fora = idx == self.casa_idx, idx == self.fora_idx
        hover = r.collidepoint(mpos)

        if e_casa:
            bg, borda, bw = (20, 50, 110), (80, 170, 255), 3
        elif e_fora:
            bg, borda, bw = (80, 20, 30), (255, 90, 100), 3
        elif hover:
            bg, borda, bw = (25, 40, 75), (140, 190, 255), 2
        else:
            bg, borda, bw = (14, 22, 44), (35, 55, 100), 1

        sobe = -3 if hover else 0
        rr = r.move(0, sobe)
        pygame.draw.rect(s, bg, rr, border_radius=10)
        # Faixa inferior com as cores do clube
        cor_p, cor_s = info.get("cor_primaria", (40, 40, 40)), info.get("cor_secundaria", (255, 255, 255))
        pygame.draw.rect(s, cor_p, (rr.left + 10, rr.bottom - 7, rr.width // 2 - 10, 3))
        pygame.draw.rect(s, cor_s, (rr.centerx, rr.bottom - 7, rr.width // 2 - 10, 3))
        pygame.draw.rect(s, borda, rr, bw, border_radius=10)

        logo = carregar_logo_equipa(eq_id, (42, 42))
        if logo:
            s.blit(logo, logo.get_rect(center=(rr.centerx, rr.top + 28)))
        texto(s, info["sigla"], 12, (255, 255, 255), (rr.centerx, rr.bottom - 32))

        if e_casa:
            etiqueta, cor_et = "CASA", (110, 200, 255)
        elif e_fora:
            etiqueta, cor_et = "FORA", (255, 130, 130)
        else:
            etiqueta, cor_et = f"#{idx + 1}", (90, 120, 170)
        texto(s, etiqueta, 11, cor_et, (rr.centerx, rr.bottom - 17))


# ====================================================================== #
# Menu de Pausa                                                          #
# ====================================================================== #

class MenuPausa:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.t = 0.0
        bw, bh, x = 300, 50, WIDTH // 2 - 150
        y0 = 248
        self.lista = ListaBotoes([
            Botao((x, y0, bw, bh), "CONTINUAR", "continuar", cor=(40, 190, 100), icone="►"),
            Botao((x, y0 + 62, bw, bh), "REINICIAR PARTIDA", "reiniciar", cor=(255, 180, 40)),
            Botao((x, y0 + 124, bw, bh), "CONTROLOS", "controlos", cor=(50, 140, 255)),
            Botao((x, y0 + 186, bw, bh), "MENU PRINCIPAL", "menu", cor=(150, 110, 255)),
            Botao((x, y0 + 248, bw, bh), "SAIR DO JOGO", "sair", cor=(230, 70, 70)),
        ])

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            return "continuar"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt

    def draw(self, game):
        s = self.screen
        escurecer_ecra(s, 165)
        caixa = pygame.Rect(WIDTH // 2 - 200, 110, 400, 470)
        painel(s, caixa, alpha=240)
        texto(s, "PAUSA", 40, COR_TEXTO, (WIDTH // 2, caixa.top + 44), sombra=True)

        # Resultado atual
        info_c = obter_info_equipa(game.equipa_casa_id)
        info_f = obter_info_equipa(game.equipa_fora_id)
        mins, segs = divmod(max(0, int(game.tempo_restante)), 60)
        resumo = f"{info_c['sigla']}  {game.golos_azul} - {game.golos_vermelho}  {info_f['sigla']}"
        texto(s, resumo, 18, COR_DESTAQUE, (WIDTH // 2, caixa.top + 88))
        texto(s, f"{game.parte}.ª parte  •  faltam {mins:02d}:{segs:02d}", 13, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 112), negrito=False)

        self.lista.draw(s)


# ====================================================================== #
# Fim de Jogo                                                            #
# ====================================================================== #

class EcraFimJogo:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.t = 0.0
        y, bw, bh = 506, 230, 52
        cx = WIDTH // 2
        self.lista = ListaBotoes([
            Botao((cx - bw - bw // 2 - 16, y, bw, bh), "JOGAR DE NOVO", "reiniciar", cor=(40, 190, 100), icone="►"),
            Botao((cx - bw // 2, y, bw, bh), "MUDAR EQUIPAS", "equipas", cor=(50, 140, 255)),
            Botao((cx + bw // 2 + 16, y, bw, bh), "MENU PRINCIPAL", "menu", cor=(150, 110, 255)),
        ])

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return "reiniciar"
            if event.key == pygame.K_ESCAPE:
                return "menu"
            # Botões estão lado a lado: esquerda/direita também navegam
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.lista.foco = (self.lista.foco - 1) % len(self.lista.botoes)
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.lista.foco = (self.lista.foco + 1) % len(self.lista.botoes)
                return None
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt

    def draw(self, game):
        s = self.screen
        escurecer_ecra(s, 175)
        caixa = pygame.Rect(WIDTH // 2 - 420, 90, 840, 510)
        painel(s, caixa, alpha=242)
        texto(s, "FIM DO JOGO", 42, COR_TEXTO, (WIDTH // 2, caixa.top + 48), sombra=True)

        info_c = obter_info_equipa(game.equipa_casa_id)
        info_f = obter_info_equipa(game.equipa_fora_id)
        kit_c, kit_f = game.kit_casa, game.kit_fora

        # Equipas lado a lado com o resultado no meio
        for info, kit, cx, virar in ((info_c, kit_c, caixa.left + 190, False),
                                     (info_f, kit_f, caixa.right - 190, True)):
            logo = carregar_logo_equipa(info["id"], (110, 110))
            if logo:
                s.blit(logo, logo.get_rect(center=(cx - 50 if not virar else cx + 50, caixa.top + 190)))
            jog = sprite_equipamento(kit, 110, self.t, virar=virar)
            s.blit(jog, jog.get_rect(midbottom=(cx + 60 if not virar else cx - 60, caixa.top + 250)))
            texto(s, info["nome"], 22, COR_TEXTO, (cx, caixa.top + 286))

        resultado = f"{game.golos_azul}  -  {game.golos_vermelho}"
        texto(s, resultado, 64, (255, 255, 255), (WIDTH // 2, caixa.top + 196), sombra=True)

        if game.golos_azul > game.golos_vermelho:
            msg, cor = f"VITÓRIA DO {info_c['nome'].upper()}!", cor_visivel_em_escuro(kit_c["principal"], 120)
        elif game.golos_vermelho > game.golos_azul:
            msg, cor = f"VITÓRIA DO {info_f['nome'].upper()}!", cor_visivel_em_escuro(kit_f["principal"], 120)
        else:
            msg, cor = "EMPATE!", COR_DESTAQUE
        texto(s, msg, 30, cor, (WIDTH // 2, caixa.top + 350), sombra=True)

        faltas = f"Faltas:  {info_c['sigla']} {game.faltas_azul}   •   {info_f['sigla']} {game.faltas_vermelho}"
        texto(s, faltas, 14, COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 392), negrito=False)

        self.lista.draw(s)
        texto(s, "[R] jogar de novo   [ESC] menu principal", 12, (110, 140, 190),
              (WIDTH // 2, caixa.bottom - 18), negrito=False)

