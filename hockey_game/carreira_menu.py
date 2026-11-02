# -*- coding: utf-8 -*-
"""carreira_menu.py - ecrãs do modo carreira.

  • EcraCarreiraEscolha - escolher a equipa e a dificuldade para começar o campeonato
  • EcraCampeonato      - classificação, próximo jogo, resultados e calendário

Tal como os outros menus, cada ecrã tem handle_event(event) -> ação, update(dt) e draw().
Quem decide o que fazer com a ação é a classe Game (game.py).
"""
import math
import random

import pygame

from settings import WIDTH, HEIGHT
from team import EQUIPAS_LISTA, obter_info_equipa, carregar_logo_equipa
from ai import DIFICULDADES
from carreira import FORCA_EQUIPAS
from cores import definir_equipamentos, cor_visivel_em_escuro, cor_texto_sobre, misturar
from componentes import (fonte, texto, painel, fundo_menu, Botao, sprite_equipamento,
                         faixa_equipa, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE, COR_PAINEL)

COR_LINHA_JOGADOR = (40, 80, 150)


def _barra_forca(s, x, y, w, forca):
    """Barra com a força da equipa (60-95 ocupa a barra toda)."""
    t = max(0.0, min(1.0, (forca - 60) / 35))
    pygame.draw.rect(s, (25, 35, 65), (x, y, w, 8), border_radius=4)
    cor = misturar((230, 80, 70), (80, 220, 120), t)
    pygame.draw.rect(s, cor, (x, y, max(8, int(w * t)), 8), border_radius=4)


# ====================================================================== #
# Escolha da equipa                                                      #
# ====================================================================== #

class EcraCarreiraEscolha:
    def __init__(self, screen: pygame.Surface, equipa_id: str = "fc_porto", dificuldade: str = "normal"):
        self.screen = screen
        self.idx = EQUIPAS_LISTA.index(equipa_id) if equipa_id in EQUIPAS_LISTA else 0
        self.dificuldade = dificuldade if dificuldade in DIFICULDADES else "normal"
        self.t = 0.0

        self.btn_voltar = Botao((24, 18, 130, 40), "VOLTAR", "voltar", cor=(50, 140, 255),
                                tamanho_texto=15, icone="◄")
        cw, ch, gap = 250, 150, 24
        x0 = (WIDTH - (4 * cw + 3 * gap)) // 2
        self.cartoes = []
        for i, eq in enumerate(EQUIPAS_LISTA):
            r = pygame.Rect(x0 + (i % 4) * (cw + gap), 112 + (i // 4) * (ch + 20), cw, ch)
            self.cartoes.append((eq, r))
        cx = WIDTH // 2
        self.botoes_dif = [
            Botao((cx - 222, 486, 140, 38), "FÁCIL", "facil", cor=(40, 180, 90), tamanho_texto=17),
            Botao((cx - 70, 486, 140, 38), "NORMAL", "normal", cor=(50, 140, 255), tamanho_texto=17),
            Botao((cx + 82, 486, 140, 38), "DIFÍCIL", "dificil", cor=(230, 70, 70), tamanho_texto=17),
        ]
        self.btn_comecar = Botao((WIDTH // 2 - 210, 590, 420, 60), "COMEÇAR CAMPEONATO", "comecar",
                                 cor=(40, 190, 100), tamanho_texto=22, icone="►")

    @property
    def equipa(self) -> str:
        return EQUIPAS_LISTA[self.idx]

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return "comecar"
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "voltar"
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.idx = (self.idx - 1) % len(EQUIPAS_LISTA)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.idx = (self.idx + 1) % len(EQUIPAS_LISTA)
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.idx = (self.idx + 4) % len(EQUIPAS_LISTA)
            elif event.key == pygame.K_TAB:
                ordem = ["facil", "normal", "dificil"]
                self.dificuldade = ordem[(ordem.index(self.dificuldade) + 1) % 3]
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_comecar.por_cima(event.pos):
                return "comecar"
            if self.btn_voltar.por_cima(event.pos):
                return "voltar"
            for b in self.botoes_dif:
                if b.por_cima(event.pos):
                    self.dificuldade = b.acao
            for i, (eq, r) in enumerate(self.cartoes):
                if r.collidepoint(event.pos):
                    self.idx = i
        return None

    def update(self, dt: float):
        self.t += dt

    def draw(self):
        s = self.screen
        mpos = pygame.mouse.get_pos()
        info = obter_info_equipa(self.equipa)
        fundo_menu(s, self.t, info["cor_primaria"], info["cor_primaria"])
        texto(s, "MODO CARREIRA", 36, COR_TEXTO, (WIDTH // 2, 36), sombra=True)
        texto(s, "Escolhe o clube que vais treinar  •  joga contra todas as outras equipas e tenta ser campeão",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, 72), negrito=False)
        self.btn_voltar.draw(s, mpos)

        for i, (eq, r) in enumerate(self.cartoes):
            self._cartao(eq, r, i == self.idx, r.collidepoint(mpos))

        texto(s, "DIFICULDADE DOS ADVERSÁRIOS", 14, (200, 220, 255), (WIDTH // 2, 470))
        for b in self.botoes_dif:
            b.ativo = (b.acao == self.dificuldade)
            b.draw(s, mpos)
        texto(s, DIFICULDADES[self.dificuldade]["descricao"], 13, (160, 195, 240), (WIDTH // 2, 542),
              negrito=False)
        self.btn_comecar.draw(s, mpos, focado=(math.sin(self.t * 3) > 0.6))
        texto(s, "[←/→/↑/↓] escolher equipa   [TAB] dificuldade   [ENTER] começar   [ESC] voltar",
              12, (110, 140, 190), (WIDTH // 2, 680), negrito=False)

    def _cartao(self, eq, r, escolhido, hover):
        s = self.screen
        info = obter_info_equipa(eq)
        cor = info["cor_primaria"]
        rr = r.move(0, -4 if (hover or escolhido) else 0)
        borda = COR_DESTAQUE if escolhido else (misturar(cor_visivel_em_escuro(cor), (255, 255, 255), 0.2)
                                                 if hover else (40, 65, 120))
        painel(s, rr, cor=COR_PAINEL, borda=borda, largura_borda=3 if escolhido else 2)
        faixa_equipa(s, (rr.left, rr.top, rr.width, 8), cor)
        logo = carregar_logo_equipa(eq, (70, 70))
        if logo:
            s.blit(logo, logo.get_rect(center=(rr.left + 56, rr.top + 64)))
        texto(s, info["nome"], 17, COR_TEXTO, (rr.left + 104, rr.top + 40), ancora="midleft")
        texto(s, info["sigla"], 12, COR_TEXTO_SUAVE, (rr.left + 104, rr.top + 62), ancora="midleft")
        forca = FORCA_EQUIPAS.get(eq, 75)
        texto(s, f"FORÇA {forca}", 11, (170, 200, 240), (rr.left + 104, rr.top + 86), ancora="midleft")
        _barra_forca(s, rr.left + 104, rr.top + 98, rr.width - 124, forca)
        if escolhido:
            pygame.draw.rect(s, COR_DESTAQUE, (rr.left + 16, rr.bottom - 30, rr.width - 32, 22), border_radius=6)
            texto(s, "A TUA EQUIPA", 12, (30, 25, 5), (rr.centerx, rr.bottom - 19))


# ====================================================================== #
# Ecrã do campeonato                                                     #
# ====================================================================== #

class EcraCampeonato:
    """
    camp      : objeto Campeonato (carreira.py)
    destaque  : número da jornada que acabou de ser jogada (para mostrar os resultados)
    """

    def __init__(self, screen: pygame.Surface, camp, destaque: int | None = None):
        self.screen = screen
        self.camp = camp
        self.t = 0.0
        self.aba = "resultados"
        self.destaque = destaque
        self._confirmar_nova = False
        self._confetis = []
        self._criar_botoes()
        if self.camp.terminado and self.camp.posicao_do_jogador() == 1:
            rnd = random.Random(7)
            self._confetis = [[rnd.uniform(0, WIDTH), rnd.uniform(-HEIGHT, 0), rnd.uniform(40, 120),
                               rnd.uniform(-30, 30), rnd.choice([(255, 205, 60), (255, 255, 255),
                                                                 (80, 170, 255), (255, 90, 90)])]
                              for _ in range(140)]

    def _criar_botoes(self):
        if self.camp.terminado:
            principal = Botao((WIDTH // 2 - 190, 600, 380, 60), "NOVA ÉPOCA", "nova_epoca",
                              cor=(40, 190, 100), tamanho_texto=22, icone="►")
        else:
            principal = Botao((WIDTH // 2 - 190, 600, 380, 60), f"JOGAR JORNADA {self.camp.jornada_atual}",
                              "jogar", cor=(40, 190, 100), tamanho_texto=22, icone="►")
        self.btn_principal = principal
        self.btn_nova = Botao((40, 606, 250, 50), "NOVA CARREIRA", "nova_carreira", cor=(255, 150, 40),
                              tamanho_texto=17)
        self.btn_menu = Botao((WIDTH - 290, 606, 250, 50), "MENU PRINCIPAL", "menu", cor=(150, 110, 255),
                              tamanho_texto=17)
        self.aba_res = pygame.Rect(776, 338, 150, 30)
        self.aba_cal = pygame.Rect(932, 338, 150, 30)

    # ------------------------------------------------------------------ #
    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.btn_principal.acao
            if event.key == pygame.K_ESCAPE:
                return "menu"
            if event.key == pygame.K_TAB:
                self.aba = "calendario" if self.aba == "resultados" else "resultados"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.btn_principal.por_cima(p):
                return self.btn_principal.acao
            if self.btn_menu.por_cima(p):
                return "menu"
            if self.btn_nova.por_cima(p):
                # Pede confirmação: o campeonato atual perde-se
                if self._confirmar_nova:
                    return "nova_carreira"
                self._confirmar_nova = True
                self.btn_nova.texto = "TENS A CERTEZA?"
                return None
            if self.aba_res.collidepoint(p):
                self.aba = "resultados"
            elif self.aba_cal.collidepoint(p):
                self.aba = "calendario"
        return None

    def update(self, dt: float):
        self.t += dt
        for c in self._confetis:
            c[1] += c[2] * dt
            c[0] += c[3] * dt
            if c[1] > HEIGHT:
                c[1] -= HEIGHT + 20

    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        camp = self.camp
        eu = camp.equipa_jogador
        info_eu = obter_info_equipa(eu)
        fundo_menu(s, self.t, info_eu["cor_primaria"], info_eu["cor_primaria"])
        mpos = pygame.mouse.get_pos()

        # Cabeçalho
        logo = carregar_logo_equipa(eu, (60, 60))
        if logo:
            s.blit(logo, logo.get_rect(center=(80, 50)))
        texto(s, camp.info["nome"].upper(), 28, COR_TEXTO, (122, 36), ancora="midleft", sombra=True)
        dif = DIFICULDADES[camp.dificuldade]["nome"]
        texto(s, f"{info_eu['nome']}   •   Época {camp.info['epoca']}   •   Dificuldade {dif}", 14,
              COR_TEXTO_SUAVE, (122, 66), ancora="midleft", negrito=False)
        if camp.terminado:
            etiqueta = "CAMPEONATO TERMINADO"
        else:
            etiqueta = f"JORNADA {camp.jornada_atual} DE {camp.total_jornadas}"
        r_et = pygame.Rect(WIDTH - 300, 30, 260, 40)
        pygame.draw.rect(s, (20, 34, 70), r_et, border_radius=10)
        pygame.draw.rect(s, COR_DESTAQUE, r_et, 2, border_radius=10)
        texto(s, etiqueta, 16, COR_DESTAQUE, r_et.center)

        self._tabela(pygame.Rect(40, 100, 700, 480))
        if camp.terminado:
            self._cartao_campeao(pygame.Rect(760, 100, 480, 220))
        else:
            self._cartao_proximo(pygame.Rect(760, 100, 480, 220))
        self._painel_jogos(pygame.Rect(760, 332, 480, 248))

        self.btn_principal.draw(s, mpos, focado=(math.sin(self.t * 3) > 0.6))
        self.btn_nova.draw(s, mpos)
        self.btn_menu.draw(s, mpos)
        texto(s, "[ENTER] " + ("nova época" if camp.terminado else "jogar") +
              "   [TAB] resultados / calendário   [ESC] menu principal", 12, (110, 140, 190),
              (WIDTH // 2, 690), negrito=False)

        for x, y, _, _, cor in self._confetis:
            pygame.draw.rect(s, cor, (int(x), int(y), 6, 10))

    # ------------------------------------------------------------------ #
    def _tabela(self, caixa):
        s = self.screen
        painel(s, caixa, alpha=235)
        texto(s, "CLASSIFICAÇÃO", 16, COR_DESTAQUE, (caixa.left + 20, caixa.top + 22), ancora="midleft")
        colunas = [("J", 380), ("V", 420), ("E", 460), ("D", 500), ("GM", 548), ("GS", 594),
                   ("DG", 640), ("PTS", 676)]
        y = caixa.top + 52
        for nome, x in colunas:
            texto(s, nome, 13, (140, 170, 220), (caixa.left + x, y), ancora="center")
        pygame.draw.line(s, (40, 65, 120), (caixa.left + 16, y + 14), (caixa.right - 16, y + 14), 1)

        eu = self.camp.equipa_jogador
        tabela = self.camp.classificacao()
        n = len(tabela)
        for i, l in enumerate(tabela, start=1):
            yy = y + 22 + (i - 1) * 50
            linha = pygame.Rect(caixa.left + 12, yy, caixa.width - 24, 46)
            if l["equipa_id"] == eu:
                pygame.draw.rect(s, COR_LINHA_JOGADOR, linha, border_radius=8)
                pygame.draw.rect(s, (110, 170, 255), linha, 2, border_radius=8)
            elif i % 2 == 0:
                pygame.draw.rect(s, (18, 28, 54), linha, border_radius=8)
            # Posição (1.º lugar a dourado, último a vermelho)
            cor_pos = COR_DESTAQUE if i == 1 else ((235, 90, 90) if i == n else COR_TEXTO)
            texto(s, f"{i}.", 18, cor_pos, (linha.left + 26, linha.centery))
            logo = carregar_logo_equipa(l["equipa_id"], (34, 34))
            if logo:
                s.blit(logo, logo.get_rect(center=(linha.left + 70, linha.centery)))
            texto(s, l["nome"], 17, COR_TEXTO, (linha.left + 98, linha.centery), ancora="midleft")
            valores = [l["jogos"], l["vitorias"], l["empates"], l["derrotas"], l["golos_marcados"],
                       l["golos_sofridos"], f"{l['diferenca']:+d}" if l["diferenca"] else "0", l["pontos"]]
            for (nome, x), v in zip(colunas, valores):
                negrito = nome == "PTS"
                cor = COR_DESTAQUE if negrito else (220, 230, 250)
                texto(s, str(v), 18 if negrito else 15, cor, (caixa.left + x, linha.centery), negrito=negrito)

    def _cartao_proximo(self, caixa):
        s = self.screen
        jogo = self.camp.proximo_jogo()
        painel(s, caixa, alpha=235)
        texto(s, "PRÓXIMO JOGO", 16, COR_DESTAQUE, (caixa.left + 20, caixa.top + 22), ancora="midleft")
        if jogo is None:
            return
        eu = self.camp.equipa_jogador
        em_casa = jogo["casa_id"] == eu
        texto(s, f"Jornada {jogo['jornada']}  •  {'EM CASA' if em_casa else 'FORA'}", 14,
              (150, 200, 255) if em_casa else (255, 170, 120), (caixa.right - 20, caixa.top + 22),
              ancora="midright")
        for eq, cx in ((jogo["casa_id"], caixa.left + 120), (jogo["fora_id"], caixa.right - 120)):
            info = obter_info_equipa(eq)
            logo = carregar_logo_equipa(eq, (92, 92))
            if logo:
                s.blit(logo, logo.get_rect(center=(cx, caixa.top + 104)))
            cor = COR_DESTAQUE if eq == eu else COR_TEXTO
            texto(s, info["nome"], 17, cor, (cx, caixa.top + 170))
            texto(s, "CASA" if eq == jogo["casa_id"] else "FORA", 11, COR_TEXTO_SUAVE, (cx, caixa.top + 192))
        pulso = 1 + 0.05 * math.sin(self.t * 4)
        pygame.draw.circle(s, (22, 38, 76), (caixa.centerx, caixa.top + 104), int(30 * pulso) + 4)
        pygame.draw.circle(s, COR_DESTAQUE, (caixa.centerx, caixa.top + 104), int(30 * pulso), 3)
        texto(s, "VS", 24, (255, 225, 70), (caixa.centerx, caixa.top + 104))
        # Como está o adversário na tabela
        adv = jogo["fora_id"] if em_casa else jogo["casa_id"]
        for i, l in enumerate(self.camp.classificacao(), start=1):
            if l["equipa_id"] == adv:
                texto(s, f"Adversário: {i}.º lugar, {l['pontos']} pts", 12, COR_TEXTO_SUAVE,
                      (caixa.centerx, caixa.top + 150), negrito=False)

    def _cartao_campeao(self, caixa):
        s = self.screen
        cl = self.camp.classificacao()
        campeao = cl[0]
        painel(s, caixa, alpha=235, borda=COR_DESTAQUE)
        texto(s, "CAMPEÃO NACIONAL", 20, COR_DESTAQUE, (caixa.centerx, caixa.top + 26), sombra=True)
        logo = carregar_logo_equipa(campeao["equipa_id"], (96, 96))
        if logo:
            s.blit(logo, logo.get_rect(center=(caixa.centerx, caixa.top + 98)))
        texto(s, campeao["nome"], 22, COR_TEXTO, (caixa.centerx, caixa.top + 160))
        pos = self.camp.posicao_do_jogador()
        pts = next(l["pontos"] for l in cl if l["equipa_id"] == self.camp.equipa_jogador)
        if pos == 1:
            msg, cor = "PARABÉNS! A TUA EQUIPA É CAMPEÃ!", (120, 230, 140)
        else:
            msg, cor = f"A tua equipa ficou em {pos}.º lugar com {pts} pontos", COR_TEXTO_SUAVE
        texto(s, msg, 15, cor, (caixa.centerx, caixa.top + 194))

    def _painel_jogos(self, caixa):
        s = self.screen
        painel(s, caixa, alpha=235)
        for r, nome, aba in ((self.aba_res, "RESULTADOS", "resultados"), (self.aba_cal, "CALENDÁRIO", "calendario")):
            ativa = self.aba == aba
            pygame.draw.rect(s, (40, 80, 150) if ativa else (20, 32, 62), r, border_radius=8)
            pygame.draw.rect(s, (110, 170, 255) if ativa else (45, 70, 130), r, 1, border_radius=8)
            texto(s, nome, 13, COR_TEXTO if ativa else COR_TEXTO_SUAVE, r.center)
        y0 = caixa.top + 52
        eu = self.camp.equipa_jogador
        if self.aba == "resultados":
            j = self.destaque or self.camp.ultima_jornada_jogada()
            if not j:
                texto(s, "Ainda não se jogou nenhuma jornada.", 14, COR_TEXTO_SUAVE,
                      (caixa.centerx, caixa.centery + 20), negrito=False)
                return
            texto(s, f"Jornada {j}", 13, COR_TEXTO_SUAVE, (caixa.right - 20, caixa.top + 21), ancora="midright")
            for k, p in enumerate(self.camp.jogos_da_jornada(j)):
                self._linha_jogo(pygame.Rect(caixa.left + 14, y0 + k * 46, caixa.width - 28, 40), p, eu)
        else:
            jogos = self.camp.jogos_do_jogador()
            for k, p in enumerate(jogos):
                self._linha_jogo(pygame.Rect(caixa.left + 14, y0 + k * 27, caixa.width - 28, 25), p, eu,
                                 compacto=True)

    def _linha_jogo(self, r, p, eu, compacto=False):
        s = self.screen
        meu = eu in (p["casa_id"], p["fora_id"])
        if meu:
            pygame.draw.rect(s, COR_LINHA_JOGADOR, r, border_radius=6)
        tam = 13 if compacto else 15
        logo_t = 20 if compacto else 28
        if compacto:
            texto(s, f"J{p['jornada']}", 12, COR_TEXTO_SUAVE, (r.left + 18, r.centery))
        for eq, lado in ((p["casa_id"], -1), (p["fora_id"], 1)):
            info = obter_info_equipa(eq)
            x_logo = r.centerx + lado * 52
            logo = carregar_logo_equipa(eq, (logo_t, logo_t))
            if logo:
                s.blit(logo, logo.get_rect(center=(x_logo, r.centery)))
            ancora = "midright" if lado < 0 else "midleft"
            cor = COR_DESTAQUE if eq == eu else COR_TEXTO
            texto(s, info["nome"], tam, cor, (x_logo + lado * (logo_t // 2 + 8), r.centery), ancora=ancora)
        if p["jogada"]:
            res = f"{p['golos_casa']} - {p['golos_fora']}"
            cor = COR_TEXTO
            if meu:
                meus = p["golos_casa"] if p["casa_id"] == eu else p["golos_fora"]
                deles = p["golos_fora"] if p["casa_id"] == eu else p["golos_casa"]
                cor = (120, 230, 140) if meus > deles else ((235, 90, 90) if meus < deles else COR_DESTAQUE)
        else:
            res, cor = "vs", COR_TEXTO_SUAVE
        texto(s, res, tam + 1, cor, r.center)
