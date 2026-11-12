# -*- coding: utf-8 -*-
"""ui.py - Interface durante o jogo.

  1. Marcador ao centro, em cima, como numa transmissão de televisão: emblema, nome e faltas de
     cada equipa dos lados, os golos junto ao relógio e a parte por baixo do tempo.
  2. Painel de baixo com três cartões: mini-mapa (radar com os jogadores e a bola), cartão do
     jogador controlado (retrato, número, nome, posição e atributos com o valor) e as teclas das
     ações (acendem quando se carrega nelas e também funcionam com o rato).
  3. Aviso de falta.
"""
import pygame
import fontes
from settings import *
from team import carregar_logo_equipa, obter_info_equipa
from cores import cor_texto_sobre, cor_visivel_em_escuro, clarear, escurecer, misturar

COR_DOURADO = (255, 205, 60)
NOME_PAPEL = {"avancado": "AVANÇADO", "medio": "MÉDIO", "defesa": "DEFESA", "guarda_redes": "GUARDA-REDES"}


class HUDController:
    # Marcador: posição e medidas (ao centro do ecrã)
    PLACAR_W, PLACAR_H, PLACAR_Y = 500, 52, 8
    LADO_W, GOLOS_W = 170, 38                   # bloco de cada equipa e caixa dos golos

    def __init__(self):
        f = fontes.SysFont
        self.font_time = f("Arial", 21, bold=True)
        self.font_title = f("Arial", 15, bold=True)
        self.font_score = f("Arial", 28, bold=True)
        self.font_card_nome = f("Arial", 20, bold=True)
        self.font_card_role = f("Arial", 11, bold=True)
        self.font_stat = f("Arial", 12, bold=True)
        self.font_btn = f("Arial", 12, bold=True)
        self.font_key = f("Arial", 10, bold=True)
        self.font_mini = f("Arial", 9, bold=True)
        self.font_parte = f("Arial", 10, bold=True)

        # Cartões do painel de baixo
        y = HUD_BAIXO_Y + 14
        self.r_mapa = pygame.Rect(28, y, 236, 156)
        self.r_cartao = pygame.Rect(282, y, 520, 156)
        self.r_acoes = pygame.Rect(820, y, 432, 156)
        # Botões de ação (também se pode clicar neles com o rato)
        self.btn_rects = {}
        self._setup_buttons()

    def _setup_buttons(self):
        botoes = [
            ("remate",   "Remate", "X",     (220, 60, 60)),
            ("passe",    "Passe",  "Z",     (40, 140, 240)),
            ("acelerar", "Sprint", "SHIFT", (40, 200, 100)),
            ("defender", "Trocar", "C",     (230, 160, 30)),
        ]
        raio = 28
        passo = self.r_acoes.width // len(botoes)
        for i, (chave, label, atalho, cor) in enumerate(botoes):
            cx = self.r_acoes.left + passo // 2 + i * passo
            cy = self.r_acoes.top + 62
            self.btn_rects[chave] = {
                "center": (cx, cy), "raio": raio, "label": label, "atalho": atalho, "cor": cor,
                "rect": pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2),
            }

    # ================================================================== #
    # Marcador (em cima, ao centro)                                       #
    # ================================================================== #

    def draw_top_bar(self, screen: pygame.Surface, game):
        """
        Marcador, tempo, dificuldade e botão de pausa. Só muda uma vez por segundo (ou num golo,
        falta, ...), por isso é desenhado numa camada guardada e refeito apenas quando algo muda.
        """
        teste = getattr(game, "teste", {}) if getattr(game, "modo_teste", False) else None
        chave = (getattr(game, "equipa_casa_id", ""), getattr(game, "equipa_fora_id", ""),
                 str(getattr(game, "kit_casa", "")), str(getattr(game, "kit_fora", "")),
                 game.golos_azul, game.golos_vermelho, getattr(game, "faltas_azul", 0),
                 getattr(game, "faltas_vermelho", 0), max(0, int(game.tempo_restante)), game.parte,
                 getattr(game, "dificuldade", "normal"), str(teste), getattr(game, "teste_variante", ""),
                 bool(getattr(game, "online", None)))
        if chave != getattr(self, "_chave_topo", None):
            camada = pygame.Surface((WIDTH, 72), pygame.SRCALPHA)
            self._desenhar_topo(camada, game)
            self._camada_topo, self._chave_topo = camada, chave
        screen.blit(self._camada_topo, (0, 0))

    def _desenhar_topo(self, screen: pygame.Surface, game):
        W, H, y0 = self.PLACAR_W, self.PLACAR_H, self.PLACAR_Y
        x0 = (WIDTH - W) // 2
        lado, gw = self.LADO_W, self.GOLOS_W
        centro_w = W - 2 * (lado + gw)
        raio = 12

        info_casa = obter_info_equipa(getattr(game, "equipa_casa_id", "fc_porto"))
        info_fora = obter_info_equipa(getattr(game, "equipa_fora_id", "riba_dave"))
        # Cores dos blocos = cores do equipamento usado nesta partida
        kit_casa, kit_fora = getattr(game, "kit_casa", None), getattr(game, "kit_fora", None)
        cor_casa = kit_casa["principal"] if kit_casa else info_casa.get("cor_primaria", (15, 60, 160))
        cor_fora = kit_fora["principal"] if kit_fora else info_fora.get("cor_primaria", (135, 20, 25))

        # Sombra por baixo do marcador
        sombra = pygame.Surface((W + 8, H + 8), pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 120), (4, 6, W, H), border_radius=raio)
        screen.blit(sombra, (x0 - 4, y0 - 2))

        # ── Blocos das equipas (casa à esquerda, visitante à direita) ──
        dados = ((info_casa, cor_casa, getattr(game, "faltas_azul", 0), game.golos_azul, False),
                 (info_fora, cor_fora, getattr(game, "faltas_vermelho", 0), game.golos_vermelho, True))
        for info, cor, faltas, golos, direita in dados:
            bx = x0 + W - lado if direita else x0
            bloco = pygame.Rect(bx, y0, lado, H)
            cantos = (dict(border_top_right_radius=raio, border_bottom_right_radius=raio) if direita
                      else dict(border_top_left_radius=raio, border_bottom_left_radius=raio))
            pygame.draw.rect(screen, cor, bloco, **cantos)
            # Meio de baixo um pouco mais escuro (dá volume, como um botão)
            baixo = pygame.Surface((lado, H // 2), pygame.SRCALPHA)
            baixo.fill((0, 0, 0, 34))
            screen.blit(baixo, (bx, y0 + H // 2))
            pygame.draw.rect(screen, cor, bloco, 1, **cantos)
            txt = cor_texto_sobre(cor)

            # Emblema (do lado de fora) e nome; se o nome não couber, usa-se a sigla
            x_logo = bloco.right - 34 if direita else bloco.left + 8
            self._desenhar_logo_placar(screen, info["id"], x_logo, y0 + (H - 26) // 2, info)
            nome = info["nome"]
            if self.font_title.size(nome)[0] > lado - 50:
                nome = info["sigla"]
            t_nome = self.font_title.render(nome, True, txt)
            muitas = faltas >= 8                 # perto do livre direto: etiqueta vermelha
            cor_f = (255, 255, 255) if muitas else misturar(txt, cor, 0.3)
            t_f = self.font_mini.render(f"FALTAS  {faltas}", True, cor_f)
            x_nome = bloco.right - 42 - t_nome.get_width() if direita else bloco.left + 42
            x_f = bloco.right - 42 - t_f.get_width() if direita else bloco.left + 42
            screen.blit(t_nome, (x_nome, y0 + 9))
            if muitas:
                pygame.draw.rect(screen, (200, 40, 40), (x_f - 5, y0 + 29, t_f.get_width() + 10, 15),
                                 border_radius=7)
            screen.blit(t_f, (x_f, y0 + 31))

            # Golos, numa caixa escura junto ao relógio
            gx = bloco.left - gw if direita else bloco.right
            caixa_g = pygame.Rect(gx, y0, gw, H)
            pygame.draw.rect(screen, (8, 12, 26), caixa_g)
            pygame.draw.rect(screen, cor_visivel_em_escuro(cor, 110), (gx, y0 + H - 4, gw, 4))
            t_g = self.font_score.render(str(golos), True, (255, 255, 255))
            screen.blit(t_g, t_g.get_rect(center=(caixa_g.centerx, caixa_g.centery - 2)))

        # ── Relógio e parte, ao centro ──
        cx0 = x0 + lado + gw
        centro = pygame.Rect(cx0, y0, centro_w, H)
        pygame.draw.rect(screen, (16, 26, 54), centro)
        pygame.draw.line(screen, COR_DOURADO, (cx0, y0 + H - 2), (cx0 + centro_w - 1, y0 + H - 2), 2)
        if getattr(game, "modo_teste", False):
            # MODO TESTE: em vez do tempo, mostra golos / remates
            t = game.teste
            t_cron = self.font_time.render(f"{t['golos']}/{t['remates']}", True, (255, 220, 80))
            nome = {"colega": "TESTE + COLEGA", "adversario": "TESTE vs DEFESA"}.get(
                getattr(game, "teste_variante", "sozinho"), "MODO TESTE")
            t_parte = self.font_mini.render(nome, True, (170, 195, 235))
        else:
            mins, segs = divmod(max(0, int(game.tempo_restante)), 60)
            # Último minuto: o tempo fica dourado
            cor_t = COR_DOURADO if game.tempo_restante < 60 else (255, 255, 255)
            t_cron = self.font_time.render(f"{mins:02d}:{segs:02d}", True, cor_t)
            t_parte = self.font_parte.render(f"{game.parte}.ª PARTE", True, (170, 195, 235))
        screen.blit(t_cron, t_cron.get_rect(center=(centro.centerx, y0 + 19)))
        screen.blit(t_parte, t_parte.get_rect(center=(centro.centerx, y0 + 38)))

        # Moldura do marcador completo
        pygame.draw.rect(screen, (70, 105, 175), (x0, y0, W, H), 1, border_radius=raio)

        # ── Dificuldade da IA (canto superior esquerdo; no online não há IA) ──
        if not getattr(game, "online", None):
            dif_str = getattr(game, "dificuldade", "normal").lower()
            nomes_dif = {"facil": "FÁCIL", "normal": "NORMAL", "dificil": "DIFÍCIL"}
            cores_dif = {"facil": (60, 210, 110), "normal": (70, 160, 255), "dificil": (255, 75, 75)}
            cor_badge = cores_dif.get(dif_str, (70, 160, 255))
            txt_b = self.font_key.render(f"IA  {nomes_dif.get(dif_str, 'NORMAL')}", True, (255, 255, 255))
            badge = pygame.Rect(24, 22, txt_b.get_width() + 30, 24)
            pygame.draw.rect(screen, (12, 22, 42), badge, border_radius=12)
            pygame.draw.rect(screen, cor_badge, badge, 1, border_radius=12)
            pygame.draw.circle(screen, cor_badge, (badge.left + 12, badge.centery), 4)
            screen.blit(txt_b, (badge.left + 22, badge.centery - txt_b.get_height() // 2))

        # ── Botão de pausa (canto superior direito) ──
        pause_r = pygame.Rect(WIDTH - 52, 14, 38, 38)
        pygame.draw.rect(screen, (16, 26, 52), pause_r, border_radius=8)
        pygame.draw.rect(screen, (70, 105, 175), pause_r, 1, border_radius=8)
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 44, 23, 6, 20), border_radius=2)
        pygame.draw.rect(screen, (240, 245, 255), (WIDTH - 34, 23, 6, 20), border_radius=2)

    def _desenhar_logo_placar(self, surf, equipa_id: str, x: int, y: int, info: dict, lado: int = 26):
        """Desenha o emblema da equipa (ou um círculo com a sigla, se a imagem não existir)."""
        logo = carregar_logo_equipa(equipa_id, (lado, lado))
        if logo is not None:
            lw, lh = logo.get_size()
            surf.blit(logo, (x + (lado - lw) // 2, y + (lado - lh) // 2))
        else:
            cor_bg = info.get("cor_secundaria", (255, 255, 255))
            cor_fg = info.get("cor_primaria", (20, 60, 180))
            r = pygame.Rect(x, y, lado, lado)
            pygame.draw.circle(surf, cor_bg, r.center, lado // 2 - 1)
            pygame.draw.circle(surf, cor_fg, r.center, lado // 2 - 1, 2)
            t = self.font_mini.render(info.get("sigla", "?")[:3], True, cor_fg)
            surf.blit(t, t.get_rect(center=r.center))

    # ================================================================== #
    # Painel de baixo                                                     #
    # ================================================================== #

    def _fundo_painel(self) -> pygame.Surface:
        """Fundo do painel e molduras dos três cartões (feito uma só vez)."""
        img = getattr(self, "_img_painel", None)
        if img is None:
            img = pygame.Surface((WIDTH, HUD_BAIXO_H))
            for y in range(HUD_BAIXO_H):                      # gradiente de cima para baixo
                t = y / (HUD_BAIXO_H - 1)
                pygame.draw.line(img, misturar((16, 24, 46), (6, 9, 20), t), (0, y), (WIDTH, y))
            pygame.draw.line(img, (50, 85, 160), (0, 0), (WIDTH, 0), 2)
            pygame.draw.line(img, (20, 34, 70), (0, 2), (WIDTH, 2), 1)
            for r in (self.r_mapa, self.r_cartao, self.r_acoes):
                rr = r.move(0, -HUD_BAIXO_Y)
                pygame.draw.rect(img, (4, 6, 14), rr.move(2, 4), border_radius=12)       # sombra
                pygame.draw.rect(img, (12, 20, 42), rr, border_radius=12)
                brilho = pygame.Surface((rr.width - 8, 22), pygame.SRCALPHA)              # reflexo de vidro
                pygame.draw.rect(brilho, (255, 255, 255, 10), brilho.get_rect(), border_radius=9)
                img.blit(brilho, (rr.left + 4, rr.top + 4))
                pygame.draw.rect(img, (45, 80, 160), rr, 2, border_radius=12)
            self._img_painel = img
        return img

    def draw_bottom_panel(self, screen: pygame.Surface, game):
        screen.blit(self._fundo_painel(), (0, HUD_BAIXO_Y))
        self._draw_minimap(screen, game, self.r_mapa)
        self._draw_player_card(screen, game.jogador_humano, self.r_cartao)
        self._draw_action_buttons(screen, game)

    # ------------------------------------------------------------------ #
    # Mini-mapa (radar)                                                    #
    # ------------------------------------------------------------------ #

    def _draw_minimap(self, screen: pygame.Surface, game, rect: pygame.Rect):
        map_r = rect.inflate(-24, -24)
        map_w, map_h = map_r.size
        pygame.draw.rect(screen, (15, 25, 50), map_r, border_radius=8)
        pygame.draw.rect(screen, (50, 110, 230), map_r, 1, border_radius=8)

        # Linha central e círculo central (na cor das linhas do ringue da casa)
        cor_linhas = cor_visivel_em_escuro(getattr(game.rink, "cor_linhas", (50, 110, 230)), 80)
        mcx, mcy = map_r.center
        pygame.draw.line(screen, cor_linhas, (mcx, map_r.top + 2), (mcx, map_r.bottom - 2), 1)
        pygame.draw.circle(screen, cor_linhas, (mcx, mcy), 15, 1)

        # Cores dos pontos = cores dos equipamentos (clareadas para se verem no fundo escuro)
        kit_c = getattr(game, "kit_casa", None)
        kit_f = getattr(game, "kit_fora", None)
        cor_c = cor_visivel_em_escuro(kit_c["principal"] if kit_c else (40, 130, 240))
        cor_f = cor_visivel_em_escuro(kit_f["principal"] if kit_f else (240, 50, 50))

        r = game.rink.rect
        sx, sy = map_w / r.width, map_h / r.height

        def to_map(px, py):
            return int(map_r.left + (px - r.left) * sx), int(map_r.top + (py - r.top) * sy)

        # Balizas
        bal_esq_x, bal_esq_y = to_map(game.rink.linha_golo_esq_x, r.centery)
        bal_dir_x, bal_dir_y = to_map(game.rink.linha_golo_dir_x, r.centery)
        pygame.draw.rect(screen, (220, 60, 60), (bal_esq_x - 6, bal_esq_y - 9, 6, 18), 1)
        pygame.draw.rect(screen, (220, 60, 60), (bal_dir_x, bal_dir_y - 9, 6, 18), 1)

        # Equipa visitante e o seu guarda-redes (quadrado, para se distinguir)
        for j in game.equipa_vermelha:
            pos = to_map(j.pos_x, j.pos_y)
            pygame.draw.circle(screen, (0, 0, 0), pos, 5)
            pygame.draw.circle(screen, cor_f, pos, 4)
        gx, gy = to_map(game.gr_vermelho.pos_x, game.gr_vermelho.pos_y)
        pygame.draw.rect(screen, clarear(cor_f, 0.3), (gx - 3, gy - 3, 7, 7))

        # Equipa da casa (o jogador controlado tem um anel branco)
        for j in game.equipa_azul:
            pos = to_map(j.pos_x, j.pos_y)
            if j == game.jogador_humano:
                pygame.draw.circle(screen, (255, 255, 255), pos, 8, 2)
            pygame.draw.circle(screen, (0, 0, 0), pos, 5)
            pygame.draw.circle(screen, cor_c, pos, 4)
        gx, gy = to_map(game.gr_azul.pos_x, game.gr_azul.pos_y)
        pygame.draw.rect(screen, clarear(cor_c, 0.3), (gx - 3, gy - 3, 7, 7))

        # Bola (ponto amarelo com contorno)
        bx, by = to_map(game.bola.pos_x, game.bola.pos_y)
        pygame.draw.circle(screen, (0, 0, 0), (bx, by), 4)
        pygame.draw.circle(screen, (255, 235, 80), (bx, by), 3)

    # ------------------------------------------------------------------ #
    # Cartão do jogador controlado                                        #
    # ------------------------------------------------------------------ #

    def _draw_player_card(self, screen: pygame.Surface, jogador, rect: pygame.Rect):
        kit = getattr(jogador, "kit", None)
        cor_kit = cor_visivel_em_escuro(kit["principal"]) if kit else (60, 120, 230)

        # Retrato (o sprite do jogador ampliado, sem suavizar, para manter os píxeis)
        av = pygame.Rect(rect.left + 16, rect.top + 16, 96, 124)
        pygame.draw.rect(screen, escurecer(cor_kit, 0.72), av, border_radius=8)
        if hasattr(jogador, "image"):
            thumb = pygame.transform.scale(jogador.image, (88, 88))
            screen.blit(thumb, thumb.get_rect(midbottom=(av.centerx, av.bottom - 20)))
        # Número numa faixa por baixo do retrato
        faixa = pygame.Rect(av.left, av.bottom - 24, av.width, 24)
        pygame.draw.rect(screen, cor_kit, faixa, border_bottom_left_radius=8, border_bottom_right_radius=8)
        t_num = self.font_title.render(f"N.º {jogador.numero}", True, cor_texto_sobre(cor_kit))
        screen.blit(t_num, t_num.get_rect(center=faixa.center))
        pygame.draw.rect(screen, cor_kit, av, 2, border_radius=8)

        # Nome, posição e emblema
        x = av.right + 18
        t_nome = self.font_card_nome.render(jogador.nome, True, (255, 255, 255))
        screen.blit(t_nome, (x, rect.top + 14))
        papel = NOME_PAPEL.get(getattr(jogador, "papel", "avancado"), "JOGADOR")
        t_role = self.font_card_role.render(papel, True, (120, 175, 255))
        pilula = pygame.Rect(x, rect.top + 41, t_role.get_width() + 16, 18)
        pygame.draw.rect(screen, (20, 36, 78), pilula, border_radius=9)
        pygame.draw.rect(screen, (60, 100, 190), pilula, 1, border_radius=9)
        screen.blit(t_role, (pilula.left + 8, pilula.centery - t_role.get_height() // 2))
        logo_card = carregar_logo_equipa(getattr(jogador, "equipa_id", "fc_porto"), (40, 40))
        if logo_card is not None:
            screen.blit(logo_card, logo_card.get_rect(center=(rect.right - 36, rect.top + 36)))

        # Atributos: barra e valor
        stats = [
            ("Velocidade", getattr(jogador, "stat_velocidade", 85), (40, 210, 240)),
            ("Remate",     getattr(jogador, "stat_remate", 80),     (240, 90, 90)),
            ("Passe",      getattr(jogador, "stat_passe", 75),      (80, 160, 255)),
            ("Defesa",     getattr(jogador, "stat_defesa", 65),     (60, 220, 130)),
        ]
        bar_x = x + 84
        bar_w = rect.right - 58 - bar_x
        for idx, (label, val, cor) in enumerate(stats):
            by = rect.top + 72 + idx * 19
            t_lab = self.font_stat.render(label, True, (180, 200, 240))
            screen.blit(t_lab, (x, by - 3))
            pygame.draw.rect(screen, (20, 32, 60), (bar_x, by, bar_w, 9), border_radius=4)
            preench_w = int(bar_w * (max(0, min(100, val)) / 100.0))
            if preench_w > 0:
                pygame.draw.rect(screen, cor, (bar_x, by, preench_w, 9), border_radius=4)
            t_val = self.font_stat.render(str(int(round(val))), True, (255, 255, 255))
            screen.blit(t_val, (bar_x + bar_w + 12, by - 3))

    # ------------------------------------------------------------------ #
    # Teclas das ações                                                    #
    # ------------------------------------------------------------------ #

    def _draw_action_buttons(self, screen: pygame.Surface, game=None):
        keys = pygame.key.get_pressed()
        passe_clique = getattr(game, "tipo_passe", "tecla") == "clique"

        for chave, btn in self.btn_rects.items():
            cx, cy = btn["center"]
            raio = btn["raio"]
            cor = btn["cor"]

            # A tecla está a ser premida?
            ativo = ((chave == "remate" and keys[pygame.K_x]) or
                     (chave == "passe" and keys[pygame.K_z]) or
                     (chave == "acelerar" and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])) or
                     (chave == "defender" and (keys[pygame.K_c] or keys[pygame.K_SPACE] or keys[pygame.K_TAB])))

            pygame.draw.circle(screen, (4, 6, 14), (cx + 1, cy + 3), raio)                 # sombra
            pygame.draw.circle(screen, cor if ativo else escurecer(cor, 0.72), (cx, cy), raio)
            pygame.draw.circle(screen, clarear(cor, 0.35) if ativo else cor, (cx, cy), raio, 2)
            self._desenhar_icone_acao(screen, chave, cx, cy, ativo)

            # Nome da ação e a tecla, numa "tecla" desenhada
            t_lbl = self.font_btn.render(btn["label"], True, (240, 245, 255))
            screen.blit(t_lbl, (cx - t_lbl.get_width() // 2, cy + raio + 8))
            atalho = "CLIQUE" if chave == "passe" and passe_clique else btn["atalho"]
            t_key = self.font_key.render(atalho, True, (200, 215, 245))
            tecla = pygame.Rect(0, 0, max(26, t_key.get_width() + 14), 18)
            tecla.midtop = (cx, cy + raio + 27)
            pygame.draw.rect(screen, (26, 38, 72), tecla, border_radius=5)
            pygame.draw.rect(screen, (80, 110, 170), tecla, 1, border_radius=5)
            pygame.draw.line(screen, (10, 16, 34), (tecla.left + 3, tecla.bottom - 1),
                             (tecla.right - 4, tecla.bottom - 1), 2)
            screen.blit(t_key, t_key.get_rect(center=(tecla.centerx, tecla.centery - 1)))

    def _desenhar_icone_acao(self, screen: pygame.Surface, tipo: str, cx: int, cy: int, ativo: bool):
        cor = (255, 255, 255) if ativo else (215, 228, 255)

        if tipo == "remate":
            # Stick inclinado
            pygame.draw.line(screen, cor, (cx - 10, cy - 9), (cx + 6, cy + 8), 3)
            pygame.draw.line(screen, cor, (cx + 6, cy + 8), (cx + 13, cy + 5), 3)
            pygame.draw.circle(screen, cor, (cx - 4, cy + 8), 3)
        elif tipo == "passe":
            # Bola com rasto de passe
            pygame.draw.circle(screen, cor, (cx + 5, cy - 3), 5)
            pygame.draw.line(screen, cor, (cx - 11, cy + 7), (cx + 1, cy), 2)
            pygame.draw.line(screen, cor, (cx - 9, cy + 1), (cx - 3, cy - 2), 2)
        elif tipo == "acelerar":
            # Dupla seta de velocidade >>
            pygame.draw.polygon(screen, cor, [(cx - 9, cy - 8), (cx - 1, cy), (cx - 9, cy + 8)])
            pygame.draw.polygon(screen, cor, [(cx + 2, cy - 8), (cx + 10, cy), (cx + 2, cy + 8)])
        elif tipo == "defender":
            # Trocar de jogador: duas setas em sentidos contrários
            pygame.draw.line(screen, cor, (cx - 10, cy - 5), (cx + 6, cy - 5), 3)
            pygame.draw.polygon(screen, cor, [(cx + 5, cy - 11), (cx + 12, cy - 5), (cx + 5, cy + 1)])
            pygame.draw.line(screen, cor, (cx + 10, cy + 6), (cx - 6, cy + 6), 3)
            pygame.draw.polygon(screen, cor, [(cx - 5, cy), (cx - 12, cy + 6), (cx - 5, cy + 12)])

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
        f_ico = fontes.SysFont("Arial", 18, bold=True)
        t_ico = f_ico.render("!", True, (10, 16, 32))
        screen.blit(t_ico, (cx_ico - t_ico.get_width() // 2, cy_ico - t_ico.get_height() // 2))

        # Título da Falta
        f_tit = fontes.SysFont("Arial", 17, bold=True)
        msg_tit = getattr(game, "_msg_falta", "FALTA!")
        t_tit = f_tit.render(msg_tit, True, cor_titulo)
        screen.blit(t_tit, (bx + 66, by + 12))

        # Subtítulo com detalhes
        f_sub = fontes.SysFont("Arial", 12)
        msg_sub = getattr(game, "_msg_falta_sub", "")
        t_sub = f_sub.render(msg_sub, True, (220, 235, 255))
        screen.blit(t_sub, (bx + 66, by + 40))
