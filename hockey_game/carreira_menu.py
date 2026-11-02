# -*- coding: utf-8 -*-
"""carreira_menu.py - ecrãs do modo carreira.

  • EcraCarreiraEscolha - escolher a equipa e a dificuldade para começar o campeonato
  • EcraCampeonato      - classificação (com a forma), próximo jogo (com as probabilidades),
                          resultados, calendário e os botões para jogar ou simular

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
from cores import cor_visivel_em_escuro, misturar, clarear, escurecer
from componentes import (fonte, texto, painel, Botao, gradiente_vertical,
                         COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE)
from graficos import luz, brilho_retangulo, icone, emblema_sticks
from menu import BotaoMenu, _fundo_arena
from sons import som

COR_LINHA_JOGADOR = (40, 80, 150)
COR_VITORIA, COR_EMPATE, COR_DERROTA = (90, 210, 120), (240, 200, 70), (230, 80, 80)
COR_RESULTADO = {"V": COR_VITORIA, "E": COR_EMPATE, "D": COR_DERROTA}


def _barra_forca(s, x, y, w, forca):
    """Barra com a força da equipa (60-95 ocupa a barra toda)."""
    t = max(0.0, min(1.0, (forca - 60) / 35))
    pygame.draw.rect(s, (25, 35, 65), (x, y, w, 8), border_radius=4)
    cor = misturar((230, 80, 70), (80, 220, 120), t)
    pygame.draw.rect(s, cor, (x, y, max(8, int(w * t)), 8), border_radius=4)


def _categoria(forca: int) -> str:
    if forca >= 86:
        return "Candidato ao título"
    if forca >= 78:
        return "Equipa de meio da tabela"
    return "Luta pela manutenção"


def _bolinhas_forma(s, forma: list, centro, n: int = 5, raio: int = 6, passo: int = 15):
    """Últimos resultados como bolinhas: verde = vitória, amarelo = empate, vermelho = derrota."""
    x0 = centro[0] - (n - 1) * passo / 2
    vazios = n - len(forma)
    for i in range(n):
        x = round(x0 + i * passo)
        if i < vazios:
            pygame.draw.circle(s, (55, 70, 105), (x, centro[1]), raio, 1)
        else:
            pygame.draw.circle(s, COR_RESULTADO[forma[i - vazios]], (x, centro[1]), raio)


_cache_vidro = {}


def _vidro(s, rect, raio=14, alpha=210, borda=(60, 90, 150)):
    """
    Painel de vidro escuro (como os botões do menu principal), com sombra.
    O painel é desenhado uma vez e guardado em cache: o ecrã é redesenhado 60 vezes por
    segundo e o gradiente é a parte mais lenta.
    """
    rect = pygame.Rect(rect)
    chave = (rect.size, raio, alpha, tuple(borda))
    if chave not in _cache_vidro:
        w, h = rect.size
        img = pygame.Surface((w + 3, h + 6), pygame.SRCALPHA)
        pygame.draw.rect(img, (0, 0, 0, 100), (3, 6, w, h), border_radius=raio)
        camada = pygame.Surface((w, h), pygame.SRCALPHA)
        gradiente_vertical(camada, camada.get_rect(), (20, 30, 58), (10, 16, 34), raio=raio)
        camada.set_alpha(alpha)
        img.blit(camada, (0, 0))
        pygame.draw.rect(img, borda, (0, 0, w, h), 2, border_radius=raio)
        _cache_vidro[chave] = img
    s.blit(_cache_vidro[chave], rect.topleft)


def _titulo_painel(s, rect, txt, cor=COR_DESTAQUE):
    texto(s, txt, 15, cor, (rect.left + 20, rect.top + 22), ancora="midleft")


# ====================================================================== #
# Escolha da equipa                                                      #
# ====================================================================== #

class EcraCarreiraEscolha:
    def __init__(self, screen: pygame.Surface, equipa_id: str = "fc_porto", dificuldade: str = "normal",
                 arena: pygame.Surface | None = None):
        self.screen = screen
        self.arena = arena
        self.idx = EQUIPAS_LISTA.index(equipa_id) if equipa_id in EQUIPAS_LISTA else 0
        self.dificuldade = dificuldade if dificuldade in DIFICULDADES else "normal"
        self.t = 0.0
        self._k = [0.0] * len(EQUIPAS_LISTA)     # animação de cada cartão (0 = normal, 1 = escolhido)

        self.btn_voltar = Botao((24, 20, 130, 40), "VOLTAR", "voltar", cor=(50, 140, 255),
                                tamanho_texto=15, icone="◄")
        cw, ch, gap = 262, 140, 18
        x0 = (WIDTH - (4 * cw + 3 * gap)) // 2
        self.cartoes = []
        for i, eq in enumerate(EQUIPAS_LISTA):
            r = pygame.Rect(x0 + (i % 4) * (cw + gap), 112 + (i // 4) * (ch + 18), cw, ch)
            self.cartoes.append((eq, r))
        cx = WIDTH // 2
        self.botoes_dif = [
            Botao((cx - 222, 474, 140, 38), "FÁCIL", "facil", cor=(40, 180, 90), tamanho_texto=17),
            Botao((cx - 70, 474, 140, 38), "NORMAL", "normal", cor=(50, 140, 255), tamanho_texto=17),
            Botao((cx + 82, 474, 140, 38), "DIFÍCIL", "dificil", cor=(230, 70, 70), tamanho_texto=17),
        ]
        self.btn_comecar = BotaoMenu((WIDTH // 2 - 230, 566, 460, 72), "COMEÇAR CAMPEONATO",
                                     "7 jornadas contra todas as outras equipas", "comecar",
                                     (40, 190, 100), "trofeu")

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
            antes = self.idx
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.idx = (self.idx - 1) % len(EQUIPAS_LISTA)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.idx = (self.idx + 1) % len(EQUIPAS_LISTA)
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.idx = (self.idx + 4) % len(EQUIPAS_LISTA)
            elif event.key == pygame.K_TAB:
                ordem = ["facil", "normal", "dificil"]
                self.dificuldade = ordem[(ordem.index(self.dificuldade) + 1) % 3]
                som.ui("mover")
            if self.idx != antes:
                som.ui("mover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_comecar.por_cima(event.pos):
                return "comecar"
            if self.btn_voltar.por_cima(event.pos):
                return "voltar"
            for b in self.botoes_dif:
                if b.por_cima(event.pos):
                    self.dificuldade = b.acao
                    som.ui("mover")
            for i, (eq, r) in enumerate(self.cartoes):
                if r.collidepoint(event.pos) and i != self.idx:
                    self.idx = i
                    som.ui("mover")
        return None

    def update(self, dt: float):
        self.t += dt
        for i in range(len(self._k)):
            self._k[i] += ((1.0 if i == self.idx else 0.0) - self._k[i]) * min(1.0, dt * 10)
        self.btn_comecar.animar(dt, self.btn_comecar.por_cima(pygame.mouse.get_pos()) or
                                math.sin(self.t * 2.5) > 0.2)

    def draw(self):
        s = self.screen
        mpos = pygame.mouse.get_pos()
        info = obter_info_equipa(self.equipa)
        s.blit(_fundo_arena(self.arena), (0, 0))
        # Brilho com a cor do clube escolhido
        brilho = luz(900, 500, info["cor_primaria"], 60)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 300)), special_flags=pygame.BLEND_RGB_ADD)

        emb = emblema_sticks(44)
        r_t = texto(s, "MODO CARREIRA", 36, COR_TEXTO, (WIDTH // 2 + 26, 40), sombra=True)
        s.blit(emb, emb.get_rect(center=(r_t.left - 32, 40)))
        texto(s, "Escolhe o clube que vais treinar  •  joga contra todas as outras equipas e tenta ser campeão",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, 78), negrito=False)
        self.btn_voltar.draw(s, mpos)

        for i, (eq, r) in enumerate(self.cartoes):
            self._cartao(i, eq, r, r.collidepoint(mpos))

        texto(s, "DIFICULDADE DOS ADVERSÁRIOS", 14, (200, 220, 255), (WIDTH // 2, 456))
        for b in self.botoes_dif:
            b.ativo = (b.acao == self.dificuldade)
            b.draw(s, mpos)
        texto(s, DIFICULDADES[self.dificuldade]["descricao"], 13, (160, 195, 240), (WIDTH // 2, 532),
              negrito=False)
        self.btn_comecar.draw(s)
        texto(s, "← → ↑ ↓  escolher clube     TAB  dificuldade     ENTER  começar     ESC  voltar",
              12, (120, 145, 195), (WIDTH // 2, 690), negrito=False)

    def _cartao(self, i, eq, r, hover):
        s = self.screen
        info = obter_info_equipa(eq)
        cor = info["cor_primaria"]
        k = self._k[i]
        rr = r.move(0, -round(6 * k) - (2 if hover else 0))
        if k > 0.02:
            halo = brilho_retangulo(rr.size, cor_visivel_em_escuro(cor), 14, 18, 170).copy()
            halo.set_alpha(int(255 * k))
            s.blit(halo, (rr.x - 18, rr.y - 18))
        borda = misturar((50, 80, 140), COR_DESTAQUE, k)
        if hover and k < 0.5:
            borda = misturar(cor_visivel_em_escuro(cor), (255, 255, 255), 0.2)
        _vidro(s, rr, alpha=225, borda=borda)
        # Faixa com as cores do clube no topo
        faixa = pygame.Rect(rr.left + 2, rr.top + 2, rr.width - 4, 8)
        pygame.draw.rect(s, cor, faixa, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(s, info["cor_secundaria"], (faixa.left, faixa.bottom - 2, faixa.width, 2))

        logo = carregar_logo_equipa(eq, (74, 74))
        if logo:
            s.blit(logo, logo.get_rect(center=(rr.left + 52, rr.top + 64)))
        texto(s, info["nome"], 17, COR_TEXTO, (rr.left + 100, rr.top + 34), ancora="midleft")
        forca = FORCA_EQUIPAS.get(eq, 75)
        texto(s, _categoria(forca), 11, COR_TEXTO_SUAVE, (rr.left + 100, rr.top + 55), ancora="midleft",
              negrito=False)
        texto(s, f"FORÇA {forca}", 11, (170, 200, 240), (rr.left + 100, rr.top + 78), ancora="midleft")
        _barra_forca(s, rr.left + 100, rr.top + 90, rr.width - 120, forca)
        if k > 0.05:
            et = pygame.Rect(rr.left + 16, rr.bottom - 30, rr.width - 32, 22)
            camada = pygame.Surface(et.size, pygame.SRCALPHA)
            pygame.draw.rect(camada, (*COR_DESTAQUE, int(255 * k)), camada.get_rect(), border_radius=6)
            s.blit(camada, et)
            texto(s, "A TUA EQUIPA", 12, (30, 25, 5), et.center)


# ====================================================================== #
# Ecrã do campeonato                                                     #
# ====================================================================== #

class EcraCampeonato:
    """
    camp      : objeto Campeonato (carreira.py)
    destaque  : número da jornada que acabou de ser jogada (para mostrar os resultados)
    aviso     : resultado de uma simulação, mostrado num cartão por uns segundos:
                {"tipo": "jogo", "jornada", "casa", "fora", "gc", "gf", "texto", "cor"} ou
                {"tipo": "epoca", "jornadas", "posicao", "texto", "cor"}
    """

    def __init__(self, screen: pygame.Surface, camp, destaque: int | None = None,
                 arena: pygame.Surface | None = None, aviso: tuple | None = None):
        self.screen = screen
        self.camp = camp
        self.arena = arena
        self.t = 0.0
        self.aba = "resultados"
        self.destaque = destaque
        self.aviso = aviso
        self._aviso_fechado = False
        self._confirmar = None             # botão que está à espera da 2.ª confirmação
        self._confetis = []
        # Dados lidos da base de dados uma vez (o ecrã é desenhado 60 vezes por segundo)
        self._tabela_cache = list(camp.classificacao())
        self._formas = {l["equipa_id"]: camp.forma(l["equipa_id"]) for l in self._tabela_cache}
        self._prob = None if camp.terminado else camp.probabilidades_proximo_jogo()
        self._criar_botoes()
        if self.camp.terminado and self.camp.posicao_do_jogador() == 1:
            rnd = random.Random(7)
            self._confetis = [[rnd.uniform(0, WIDTH), rnd.uniform(-HEIGHT, 0), rnd.uniform(40, 120),
                               rnd.uniform(-30, 30), rnd.choice([(255, 205, 60), (255, 255, 255),
                                                                 (80, 170, 255), (255, 90, 90)])]
                              for _ in range(140)]

    def _criar_botoes(self):
        camp = self.camp
        if camp.terminado:
            self.btn_principal = BotaoMenu((760, 312, 472, 64), "NOVA ÉPOCA",
                                           "Mesmo clube, calendário novo", "nova_epoca", (40, 190, 100), "jogar")
            self.btn_simular = None
        else:
            jogo = camp.proximo_jogo()
            local = "em casa" if jogo["casa_id"] == camp.equipa_jogador else "fora"
            self.btn_principal = BotaoMenu((760, 312, 272, 64), "JOGAR",
                                           f"Jornada {jogo['jornada']}  •  {local}", "jogar", (40, 190, 100), "jogar")
            self.btn_simular = BotaoMenu((1044, 312, 196, 64), "SIMULAR", "sem jogar", "simular",
                                         (255, 175, 40), "avancar", seta=False)
        self.btn_nova = BotaoMenu((40, 640, 270, 50), "NOVA CARREIRA", "", "nova_carreira",
                                  (255, 120, 60), "recomecar", seta=False, tamanho=18)
        self.btn_epoca = None if camp.terminado else BotaoMenu(
            (330, 640, 270, 50), "SIMULAR ÉPOCA", "", "simular_epoca", (255, 175, 40), "avancar",
            seta=False, tamanho=18)
        self.btn_menu = BotaoMenu((WIDTH - 310, 640, 270, 50), "MENU PRINCIPAL", "", "menu",
                                  (150, 110, 255), "casa", seta=False, tamanho=18)
        self.aba_res = pygame.Rect(1000, 398, 110, 28)
        self.aba_cal = pygame.Rect(1116, 398, 110, 28)
        self.foco = 0                       # 0 = jogar / nova época, 1 = simular (setas ← →)

    @property
    def _botoes(self):
        return [b for b in (self.btn_principal, self.btn_simular, self.btn_nova, self.btn_epoca, self.btn_menu)
                if b is not None]

    def _pedir_confirmacao(self, botao, texto_original) -> bool:
        """Ações que não se podem desfazer precisam de dois cliques."""
        if self._confirmar is botao:
            return True
        if self._confirmar is not None:
            self._confirmar.titulo = self._confirmar._titulo_original
        botao._titulo_original = texto_original
        botao.titulo = "TENS A CERTEZA?"
        self._confirmar = botao
        som.ui("mover")
        return False

    # ------------------------------------------------------------------ #
    @property
    def _aviso_visivel(self) -> bool:
        return bool(self.aviso) and not self._aviso_fechado and self.t < 3.5

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        # Enquanto o cartão do resultado está à vista, uma tecla ou um clique só o fecha
        if self._aviso_visivel and (event.type == pygame.KEYDOWN or
                                    (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
            self._aviso_fechado = True
            return None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.foco == 1 and self.btn_simular is not None:
                    return "simular"
                return self.btn_principal.acao
            if event.key == pygame.K_ESCAPE:
                return "menu"
            if event.key == pygame.K_TAB:
                self.aba = "calendario" if self.aba == "resultados" else "resultados"
                som.ui("mover")
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) and self.btn_simular:
                self.foco = 1 - self.foco
                som.ui("mover")
            if event.key == pygame.K_s and self.btn_simular is not None:
                return "simular"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.btn_principal.por_cima(p):
                return self.btn_principal.acao
            if self.btn_simular is not None and self.btn_simular.por_cima(p):
                return "simular"
            if self.btn_menu.por_cima(p):
                return "menu"
            if self.btn_nova.por_cima(p):
                # O campeonato atual perde-se: pede confirmação
                return "nova_carreira" if self._pedir_confirmacao(self.btn_nova, "NOVA CARREIRA") else None
            if self.btn_epoca is not None and self.btn_epoca.por_cima(p):
                return "simular_epoca" if self._pedir_confirmacao(self.btn_epoca, "SIMULAR ÉPOCA") else None
            if self.aba_res.collidepoint(p):
                self.aba = "resultados"
            elif self.aba_cal.collidepoint(p):
                self.aba = "calendario"
        elif event.type == pygame.MOUSEMOTION:
            if self.btn_simular is not None:
                if self.btn_simular.por_cima(event.pos):
                    self.foco = 1
                elif self.btn_principal.por_cima(event.pos):
                    self.foco = 0
        return None

    def update(self, dt: float):
        self.t += dt
        mpos = pygame.mouse.get_pos()
        for b in self._botoes:
            if b is self.btn_principal:
                focado = self.foco == 0
            elif b is self.btn_simular:
                focado = self.foco == 1
            else:
                focado = b.por_cima(mpos) or b is self._confirmar
            b.animar(dt, focado)
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
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(700, 420, info_eu["cor_primaria"], 50)
        s.blit(brilho, brilho.get_rect(center=(380, 330)), special_flags=pygame.BLEND_RGB_ADD)

        self._cabecalho()
        self._tabela(pygame.Rect(40, 100, 700, 520))
        if camp.terminado:
            self._cartao_campeao(pygame.Rect(760, 100, 480, 200))
        else:
            self._cartao_proximo(pygame.Rect(760, 100, 480, 200))
        self._painel_jogos(pygame.Rect(760, 388, 480, 232))

        for b in self._botoes:
            b.draw(s)
        dica = "ENTER  nova época" if camp.terminado else "ENTER  jogar     S  simular     ← →  escolher"
        texto(s, dica + "     TAB  resultados / calendário     ESC  menu principal", 12, (120, 145, 195),
              (WIDTH // 2, 704), negrito=False)

        for x, y, _, _, cor in self._confetis:
            pygame.draw.rect(s, cor, (int(x), int(y), 6, 10))

        if self._aviso_visivel:
            self._mostrar_aviso()

    def _cabecalho(self):
        s = self.screen
        camp = self.camp
        info_eu = obter_info_equipa(camp.equipa_jogador)
        logo = carregar_logo_equipa(camp.equipa_jogador, (60, 60))
        if logo:
            s.blit(logo, logo.get_rect(center=(72, 50)))
        texto(s, camp.info["nome"].upper(), 26, COR_TEXTO, (112, 36), ancora="midleft", sombra=True)
        dif = DIFICULDADES[camp.dificuldade]["nome"]
        texto(s, f"{info_eu['nome']}   •   Época {camp.info['epoca']}   •   Dificuldade {dif}", 14,
              COR_TEXTO_SUAVE, (112, 66), ancora="midleft", negrito=False)

        # Progresso da época: um segmento por jornada
        total = camp.total_jornadas
        jogadas = camp.ultima_jornada_jogada()
        etiqueta = "ÉPOCA TERMINADA" if camp.terminado else f"JORNADA {camp.jornada_atual} DE {total}"
        r = pygame.Rect(WIDTH - 330, 24, 290, 58)
        _vidro(s, r, 12, 220, COR_DESTAQUE)
        texto(s, etiqueta, 15, COR_DESTAQUE, (r.centerx, r.top + 18))
        larg = (r.width - 40 - (total - 1) * 6) / max(1, total)
        for i in range(total):
            seg = pygame.Rect(round(r.left + 20 + i * (larg + 6)), r.top + 36, round(larg), 8)
            if i < jogadas:
                cor = COR_DESTAQUE
            elif i == jogadas and not camp.terminado:
                cor = misturar((60, 80, 120), COR_DESTAQUE, 0.5 + 0.5 * math.sin(self.t * 4))
            else:
                cor = (45, 60, 95)
            pygame.draw.rect(s, cor, seg, border_radius=4)

    # ------------------------------------------------------------------ #
    def _tabela(self, caixa):
        s = self.screen
        _vidro(s, caixa, 14, 225)
        _titulo_painel(s, caixa, "CLASSIFICAÇÃO")
        colunas = [("J", 318), ("V", 352), ("E", 386), ("D", 420), ("GM", 460), ("GS", 500),
                   ("DG", 542), ("PTS", 588)]
        y = caixa.top + 50
        for nome, x in colunas:
            texto(s, nome, 12, (140, 170, 220), (caixa.left + x, y))
        texto(s, "FORMA", 12, (140, 170, 220), (caixa.left + 640, y))
        pygame.draw.line(s, (40, 65, 120), (caixa.left + 16, y + 14), (caixa.right - 16, y + 14), 1)

        eu = self.camp.equipa_jogador
        tabela = self._tabela_cache
        n = len(tabela)
        for i, l in enumerate(tabela, start=1):
            # As linhas entram a deslizar, uma de cada vez, quando o ecrã abre
            k = max(0.0, min(1.0, (self.t - (i - 1) * 0.05) / 0.3))
            desl = round((1 - k) ** 2 * 60)
            yy = y + 22 + (i - 1) * 54
            linha = pygame.Rect(caixa.left + 12 + desl, yy, caixa.width - 24, 48)
            if l["equipa_id"] == eu:
                gradiente_vertical(s, linha, (52, 100, 180), (32, 66, 132), raio=8)
                pygame.draw.rect(s, (120, 180, 255), linha, 2, border_radius=8)
            elif i % 2 == 0:
                pygame.draw.rect(s, (18, 28, 54), linha, border_radius=8)
            # Zonas: campeão a dourado, último lugar a vermelho
            if i == 1:
                pygame.draw.rect(s, COR_DESTAQUE, (linha.left, linha.top + 6, 4, linha.height - 12), border_radius=2)
            elif i == n:
                pygame.draw.rect(s, COR_DERROTA, (linha.left, linha.top + 6, 4, linha.height - 12), border_radius=2)
            cor_pos = COR_DESTAQUE if i == 1 else ((235, 90, 90) if i == n else COR_TEXTO)
            texto(s, f"{i}.", 18, cor_pos, (linha.left + 26, linha.centery))
            logo = carregar_logo_equipa(l["equipa_id"], (34, 34))
            if logo:
                s.blit(logo, logo.get_rect(center=(linha.left + 68, linha.centery)))
            texto(s, l["nome"], 16, COR_TEXTO, (linha.left + 96, linha.centery), ancora="midleft")
            valores = [l["jogos"], l["vitorias"], l["empates"], l["derrotas"], l["golos_marcados"],
                       l["golos_sofridos"], f"{l['diferenca']:+d}" if l["diferenca"] else "0", l["pontos"]]
            for (nome, x), v in zip(colunas, valores):
                negrito = nome == "PTS"
                cor = COR_DESTAQUE if negrito else (220, 230, 250)
                texto(s, str(v), 18 if negrito else 15, cor, (caixa.left + x + desl, linha.centery),
                      negrito=negrito)
            _bolinhas_forma(s, self._formas.get(l["equipa_id"], []), (caixa.left + 640 + desl, linha.centery),
                            raio=5, passo=13)

    def _cartao_proximo(self, caixa):
        s = self.screen
        camp = self.camp
        jogo = camp.proximo_jogo()
        _vidro(s, caixa, 14, 225)
        _titulo_painel(s, caixa, "PRÓXIMO JOGO")
        if jogo is None:
            return
        eu = camp.equipa_jogador
        em_casa = jogo["casa_id"] == eu
        texto(s, f"Jornada {jogo['jornada']}  •  {'EM CASA' if em_casa else 'FORA'}", 13,
              (150, 200, 255) if em_casa else (255, 170, 120), (caixa.right - 20, caixa.top + 22),
              ancora="midright")
        posicoes = {l["equipa_id"]: i for i, l in enumerate(self._tabela_cache, start=1)}
        for eq, cx in ((jogo["casa_id"], caixa.left + 110), (jogo["fora_id"], caixa.right - 110)):
            info = obter_info_equipa(eq)
            halo = luz(150, 150, info["cor_primaria"], 70)
            s.blit(halo, halo.get_rect(center=(cx, caixa.top + 80)), special_flags=pygame.BLEND_RGB_ADD)
            logo = carregar_logo_equipa(eq, (74, 74))
            if logo:
                s.blit(logo, logo.get_rect(center=(cx, caixa.top + 80)))
            cor = COR_DESTAQUE if eq == eu else COR_TEXTO
            texto(s, info["nome"], 16, cor, (cx, caixa.top + 132))
            texto(s, f"{posicoes.get(eq, '-')}.º lugar  •  força {FORCA_EQUIPAS.get(eq, 75)}", 11,
                  COR_TEXTO_SUAVE, (cx, caixa.top + 150), negrito=False)
            _bolinhas_forma(s, self._formas.get(eq, []), (cx, caixa.top + 168), raio=5, passo=13)
        pulso = 1 + 0.05 * math.sin(self.t * 4)
        pygame.draw.circle(s, (22, 38, 76), (caixa.centerx, caixa.top + 80), int(28 * pulso) + 4)
        pygame.draw.circle(s, COR_DESTAQUE, (caixa.centerx, caixa.top + 80), int(28 * pulso), 3)
        texto(s, "VS", 22, (255, 225, 70), (caixa.centerx, caixa.top + 80))
        # Probabilidades (calculadas com o mesmo modelo que simula os jogos)
        if self._prob:
            v, e, d = self._prob
            barra = pygame.Rect(caixa.centerx - 62, caixa.top + 128, 124, 10)
            x = barra.left
            for p, cor in ((v, COR_VITORIA), (e, COR_EMPATE), (d, COR_DERROTA)):
                w = round(barra.width * p)
                if w > 0:
                    pygame.draw.rect(s, cor, (x, barra.top, w, barra.height))
                x += w
            pygame.draw.rect(s, (20, 30, 60), barra, 1)
            texto(s, f"V {round(v * 100)}%   E {round(e * 100)}%   D {round(d * 100)}%", 11, COR_TEXTO_SUAVE,
                  (caixa.centerx, caixa.top + 152), negrito=False)
            texto(s, "se simulares", 10, (110, 135, 185), (caixa.centerx, caixa.top + 168), negrito=False)

    def _cartao_campeao(self, caixa):
        s = self.screen
        cl = self._tabela_cache
        campeao = cl[0]
        _vidro(s, caixa, 14, 230, COR_DESTAQUE)
        texto(s, "CAMPEÃO NACIONAL", 20, COR_DESTAQUE, (caixa.centerx, caixa.top + 24), sombra=True)
        info = obter_info_equipa(campeao["equipa_id"])
        halo = luz(260, 200, info["cor_primaria"], 90)
        s.blit(halo, halo.get_rect(center=(caixa.centerx, caixa.top + 92)), special_flags=pygame.BLEND_RGB_ADD)
        tr = icone("trofeu", 46, COR_DESTAQUE)
        s.blit(tr, tr.get_rect(center=(caixa.centerx - 90, caixa.top + 92)))
        s.blit(tr, tr.get_rect(center=(caixa.centerx + 90, caixa.top + 92)))
        logo = carregar_logo_equipa(campeao["equipa_id"], (90, 90))
        if logo:
            s.blit(logo, logo.get_rect(center=(caixa.centerx, caixa.top + 92)))
        texto(s, f"{campeao['nome']}  •  {campeao['pontos']} pontos", 19, COR_TEXTO, (caixa.centerx, caixa.top + 150))
        pos = self.camp.posicao_do_jogador()
        pts = next(l["pontos"] for l in cl if l["equipa_id"] == self.camp.equipa_jogador)
        if pos == 1:
            msg, cor = "PARABÉNS! A TUA EQUIPA É CAMPEÃ!", (120, 230, 140)
        else:
            msg, cor = f"A tua equipa ficou em {pos}.º lugar com {pts} pontos", COR_TEXTO_SUAVE
        texto(s, msg, 14, cor, (caixa.centerx, caixa.top + 178))

    def _painel_jogos(self, caixa):
        s = self.screen
        _vidro(s, caixa, 14, 225)
        for r, nome, aba in ((self.aba_res, "RESULTADOS", "resultados"), (self.aba_cal, "CALENDÁRIO", "calendario")):
            ativa = self.aba == aba
            pygame.draw.rect(s, (40, 80, 150) if ativa else (20, 32, 62), r, border_radius=8)
            pygame.draw.rect(s, (110, 170, 255) if ativa else (45, 70, 130), r, 1, border_radius=8)
            texto(s, nome, 12, COR_TEXTO if ativa else COR_TEXTO_SUAVE, r.center)
        y0 = caixa.top + 48
        eu = self.camp.equipa_jogador
        if self.aba == "resultados":
            j = self.destaque or self.camp.ultima_jornada_jogada()
            _titulo_painel(s, caixa, f"JORNADA {j}" if j else "RESULTADOS")
            if not j:
                texto(s, "Ainda não se jogou nenhuma jornada.", 14, COR_TEXTO_SUAVE,
                      (caixa.centerx, caixa.centery + 16), negrito=False)
                return
            for k, p in enumerate(self.camp.jogos_da_jornada(j)):
                self._linha_jogo(pygame.Rect(caixa.left + 14, y0 + k * 44, caixa.width - 28, 38), p, eu)
        else:
            _titulo_painel(s, caixa, "OS TEUS JOGOS")
            for k, p in enumerate(self.camp.jogos_do_jogador()):
                self._linha_jogo(pygame.Rect(caixa.left + 14, y0 + k * 25, caixa.width - 28, 23), p, eu,
                                 compacto=True)

    def _linha_jogo(self, r, p, eu, compacto=False):
        s = self.screen
        meu = eu in (p["casa_id"], p["fora_id"])
        if meu:
            pygame.draw.rect(s, COR_LINHA_JOGADOR, r, border_radius=6)
        tam = 13 if compacto else 15
        logo_t = 18 if compacto else 26
        if compacto:
            texto(s, f"J{p['jornada']}", 12, COR_TEXTO_SUAVE, (r.left + 18, r.centery))
        for eq, lado in ((p["casa_id"], -1), (p["fora_id"], 1)):
            info = obter_info_equipa(eq)
            x_logo = r.centerx + lado * 50
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
                cor = COR_VITORIA if meus > deles else (COR_DERROTA if meus < deles else COR_EMPATE)
                if p["simulado"]:
                    # Etiqueta "SIM" nos jogos do jogador que foram simulados
                    et = pygame.Rect(0, 0, 30, 15)
                    et.midright = (r.right - 6, r.centery)
                    pygame.draw.rect(s, (255, 175, 40), et, border_radius=4)
                    texto(s, "SIM", 9, (40, 25, 0), et.center)
        else:
            res, cor = "vs", COR_TEXTO_SUAVE
        texto(s, res, tam + 1, cor, r.center)

    def _mostrar_aviso(self):
        """Cartão com o resultado da simulação (fecha sozinho ao fim de 3,5 s ou com uma tecla)."""
        s = self.screen
        av = self.aviso
        a = max(0.0, min(1.0, self.t / 0.25, (3.5 - self.t) / 0.4))
        escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        escuro.fill((4, 8, 18, int(150 * a)))
        s.blit(escuro, (0, 0))

        cor = av["cor"]
        caixa = pygame.Rect(0, 0, 600, 250)
        caixa.center = (WIDTH // 2, HEIGHT // 2 - round(18 * (1 - a)))
        camada = pygame.Surface(caixa.size, pygame.SRCALPHA)
        gradiente_vertical(camada, camada.get_rect(), misturar((24, 34, 66), cor, 0.25), (10, 16, 34), raio=18)
        pygame.draw.rect(camada, clarear(cor, 0.2), camada.get_rect(), 3, border_radius=18)
        c = caixa.width // 2

        if av["tipo"] == "jogo":
            texto(camada, f"JORNADA {av['jornada']}  •  JOGO SIMULADO", 15, COR_TEXTO_SUAVE, (c, 30))
            for eq, x in ((av["casa"], c - 170), (av["fora"], c + 170)):
                logo = carregar_logo_equipa(eq, (86, 86))
                if logo:
                    camada.blit(logo, logo.get_rect(center=(x, 112)))
                cor_nome = COR_DESTAQUE if eq == self.camp.equipa_jogador else COR_TEXTO
                texto(camada, obter_info_equipa(eq)["nome"], 16, cor_nome, (x, 172))
            texto(camada, f"{av['gc']}  -  {av['gf']}", 54, COR_TEXTO, (c, 112), sombra=True)
        else:
            texto(camada, f"{av['jornadas']} JORNADAS SIMULADAS", 15, COR_TEXTO_SUAVE, (c, 30))
            tr = icone("trofeu", 70, COR_DESTAQUE if av["posicao"] == 1 else (150, 170, 210))
            camada.blit(tr, tr.get_rect(center=(c - 120, 112)))
            logo = carregar_logo_equipa(self.camp.equipa_jogador, (86, 86))
            if logo:
                camada.blit(logo, logo.get_rect(center=(c + 120, 112)))
            texto(camada, f"{av['posicao']}.º", 54, COR_TEXTO, (c, 112), sombra=True)
        # Faixa com o resultado (VITÓRIA / EMPATE / DERROTA / CAMPEÃO ...)
        faixa = pygame.Rect(c - 150, 196, 300, 36)
        pygame.draw.rect(camada, cor, faixa, border_radius=18)
        texto(camada, av["texto"], 18, (255, 255, 255), faixa.center, sombra=True)
        camada.set_alpha(int(255 * a))
        s.blit(camada, caixa)
