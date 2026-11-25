# -*- coding: utf-8 -*-
"""sonho_menu.py - EQUIPA DE SONHO: liga de fantasia online com os jogos reais do campeonato.

Os jogadores reais do Campeonato Placard (1.ª divisão) são cartas e ganham pontos com o que fazem
nos jogos verdadeiros (golos, vitórias, cinco inicial, cartões...). Os dados vêm do portal da
Federação e são lidos pelo servidor do jogo (servidor/fpp.py e servidor/liga_fantasy.py).

Ecrãs (como os outros menus: handle_event(event) -> ação, update(dt) e draw()):
  • EcraSonhoLigas - as minhas ligas, criar uma liga (dá um código) ou entrar com um código
  • EcraSonhoLiga  - o painel do treinador, com 4 separadores:
        PLANTEL  - o cinco da próxima jornada e os jogadores (titular, cláusula, vender, ver jogos)
        MERCADO  - jogadores à venda (ofertas secretas que fecham às 20h) e propostas
        RIVAIS   - os jogadores dos outros treinadores: pagar a cláusula ou fazer uma proposta
        LIGA     - classificação, resultados reais da última jornada e notícias da liga
  • SonhoMixin     - o que a classe Game precisa: abrir o modo e falar com o servidor

As ações que mexem na liga devolvem ("pedido", tipo, dados): o SonhoMixin envia-as ao servidor
e, quando chega a resposta, o ecrã recebe o estado novo da liga.
"""
import time
import zlib
from datetime import datetime

import pygame

from settings import WIDTH, HEIGHT
from team import EQUIPAS_INFO, obter_info_equipa, carregar_logo_equipa
from cores import misturar, clarear, escurecer
from componentes import (fonte, texto, gradiente_vertical, painel_vidro, ListaBotoes,
                         COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE)
from graficos import luz, icone
from menu import BotaoMenu, _fundo_arena
from sons import som

VERDE, VERMELHO, LARANJA, AZUL = (60, 200, 110), (235, 85, 80), (255, 170, 50), (90, 160, 255)
COR_NOTICIA = {"boa": VERDE, "clausula": VERMELHO, "mercado": LARANJA, "info": AZUL}
# Cores das cartas: (topo, base, letras)
CORES_RARIDADE = {"ouro": ((255, 225, 125), (170, 120, 25), (45, 30, 5)),
                  "prata": ((238, 241, 248), (140, 148, 166), (30, 34, 45)),
                  "bronze": ((232, 170, 112), (128, 76, 38), (255, 245, 230))}
PASSO = 500
SEM_RESPOSTA_S = 15.0    # segundos (com a ligação feita) até dizer que o servidor não respondeu


def _moedas(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def _hora(ts) -> str:
    return datetime.fromtimestamp(int(ts)).strftime("%d/%m %H:%M") if ts else "-"


def _falta(ts) -> str:
    """Quanto falta até 'ts', em palavras curtas (ex.: «3 h 12 min»)."""
    s = max(0, int(ts - time.time()))
    if s >= 86400:
        return f"{s // 86400} d {s % 86400 // 3600} h"
    if s >= 3600:
        return f"{s // 3600} h {s % 3600 // 60} min"
    return f"{s // 60} min"


# ====================================================================== #
# Clubes reais -> clubes do jogo (para os emblemas)                       #
# ====================================================================== #

CLUBES_DO_JOGO = [("porto", "fc_porto"), ("benfica", "benfica"), ("sporting", "sporting"),
                  ("barcelos", "oc_barcelos"), ("oliveirense", "ud_oliveirense"), ("valongo", "valongo"),
                  ("riba d", "riba_dave"), ("lavra", "crp_lavra"), ("turquel", "hc_turquel"),
                  ("arcos", "paco_arcos"), ("póvoa", "cd_povoa"), ("carvalhos", "ch_carvalhos"),
                  ("espinho", "aa_espinho"), ("marinhense", "sc_marinhense"), ("cambra", "ha_cambra")]


def clube_id(nome_fpp: str) -> str:
    """
    Clube do jogo com o mesmo nome (para usar o emblema). Os clubes que o jogo não tem ficam
    com um "clube" novo só com o nome e a sigla (o jogo desenha um círculo com a sigla).
    """
    baixo = (nome_fpp or "").lower()
    for chave, cid in CLUBES_DO_JOGO:
        if chave in baixo:
            return cid
    nome = (nome_fpp or "?").split(" / ")[0].split(" SAD")[0].strip() or "?"
    cid = "fpp_" + "".join(ch for ch in nome.lower() if ch.isalnum())
    if cid not in EQUIPAS_INFO:
        palavras = [p for p in nome.replace(".", " ").split() if p[:1].isalpha()]
        sigla = "".join(p[0] for p in palavras).upper()[:3] if len(palavras) > 1 else nome[:3].upper()
        h = zlib.crc32(cid.encode())
        cor = (40 + h % 120, 50 + (h >> 8) % 110, 70 + (h >> 16) % 120)
        EQUIPAS_INFO[cid] = {"id": cid, "nome": nome, "sigla": sigla, "cor_primaria": cor,
                             "cor_secundaria": (255, 255, 255), "ficheiros_logo": []}
    return cid


def raridade(valor: int) -> str:
    return "ouro" if valor >= 14000 else ("prata" if valor >= 7000 else "bronze")


# ====================================================================== #
# Desenho de uma carta                                                    #
# ====================================================================== #

_cache_cartas = {}


def _texto_que_cabe(txt: str, largura: int, tamanho: int, minimo: int = 9) -> tuple[str, int]:
    """Diminui a letra até o texto caber; se mesmo assim não couber, fica só o último nome."""
    for t in range(tamanho, minimo - 1, -1):
        if fonte(t).size(txt)[0] <= largura:
            return txt, t
    return txt.replace('"', "").split()[-1], minimo


def imagem_carta(c: dict, w: int, h: int) -> pygame.Surface:
    """A carta: pontos da época, posição, emblema do clube e nome (guardada em cache)."""
    rar = raridade(c["valor"])
    chave = (c["fed"], c["pontos"], rar, w, h)
    if chave in _cache_cartas:
        return _cache_cartas[chave]
    topo, base, cor_txt = CORES_RARIDADE[rar]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    gradiente_vertical(surf, surf.get_rect(), topo, base, raio=10)
    brilho = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(brilho, (255, 255, 255, 38), [(0, h * 0.18), (w, 0), (w, h * 0.12), (0, h * 0.32)])
    surf.blit(brilho, (0, 0))
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=10)
    surf.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(surf, escurecer(base, 0.35), surf.get_rect(), 2, border_radius=10)
    pygame.draw.rect(surf, clarear(topo, 0.4), surf.get_rect().inflate(-8, -8), 1, border_radius=8)
    tg = max(14, round(w * 0.2))
    tp = max(8, round(w * 0.07))
    texto(surf, str(c["pontos"]), tg, cor_txt, (round(w * 0.08), round(h * 0.04)), ancora="topleft")
    texto(surf, "PTS", tp, cor_txt, (round(w * 0.1), round(h * 0.04) + tg + 1), ancora="topleft")
    texto(surf, "GR" if c["gr"] else "JOG", max(9, round(w * 0.09)), cor_txt,
          (round(w * 0.1), round(h * 0.04) + tg + tp + 5), ancora="topleft")
    lado = round(w * 0.48)
    cid = clube_id(c["equipa"])
    logo = carregar_logo_equipa(cid, (lado, lado))
    centro = (w // 2 + round(w * 0.1), round(h * 0.4))
    if logo is not None:
        surf.blit(logo, logo.get_rect(center=centro))
    else:
        info = obter_info_equipa(cid)
        pygame.draw.circle(surf, info["cor_primaria"], centro, lado // 2)
        pygame.draw.circle(surf, (255, 255, 255), centro, lado // 2, 2)
        texto(surf, info["sigla"], max(10, lado // 4), (255, 255, 255), centro)
    pygame.draw.line(surf, escurecer(base, 0.2), (10, round(h * 0.69)), (w - 10, round(h * 0.69)), 1)
    nome, tn = _texto_que_cabe(c["nome"], w - 12, max(10, round(w * 0.1)))
    texto(surf, nome, tn, cor_txt, (w // 2, round(h * 0.78)))
    clube, tc = _texto_que_cabe(obter_info_equipa(cid)["nome"], w - 12, max(8, round(w * 0.07)), 7)
    texto(surf, clube, tc, cor_txt, (w // 2, round(h * 0.89)), negrito=False)
    _cache_cartas[chave] = surf
    return surf


def desenhar_carta(s, r: pygame.Rect, c: dict, selecionada: bool = False, titular: bool = False,
                   badge: str | None = None, cor_badge=VERDE, canto: str | None = None):
    if selecionada:
        halo = luz(r.w + 60, r.h + 60, COR_DESTAQUE, 90)
        s.blit(halo, halo.get_rect(center=r.center), special_flags=pygame.BLEND_RGB_ADD)
    sombra = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(sombra, (0, 0, 0, 110), sombra.get_rect(), border_radius=10)
    s.blit(sombra, (r.x + 3, r.y + 5))
    s.blit(imagem_carta(c, r.w, r.h), r)
    if selecionada:
        pygame.draw.rect(s, COR_DESTAQUE, r.inflate(6, 6), 3, border_radius=12)
    if titular:
        centro = (r.right - 14, r.top + 14)
        pygame.draw.circle(s, (20, 30, 60), centro, 11)
        img = icone("estrela", 14, COR_DESTAQUE)
        s.blit(img, img.get_rect(center=centro))
    if canto:
        img = fonte(10).render(canto, True, (255, 255, 255))
        caixa = pygame.Rect(0, 0, img.get_width() + 10, 16)
        caixa.topright = (r.right - 4, r.top + 4)
        pygame.draw.rect(s, (40, 150, 80), caixa, border_radius=8)
        s.blit(img, img.get_rect(center=caixa.center))
    if badge:
        img = fonte(11).render(badge, True, (255, 255, 255))
        caixa = pygame.Rect(0, 0, img.get_width() + 12, 18)
        caixa.midtop = (r.centerx, r.bottom - 9)
        pygame.draw.rect(s, cor_badge, caixa, border_radius=9)
        s.blit(img, img.get_rect(center=caixa.center))


def _botao(s, r: pygame.Rect, txt: str, cor, mpos, ativo: bool = True, tamanho: int = 13):
    por_cima = ativo and r.collidepoint(mpos)
    if not ativo:
        fundo, borda, cor_t = (28, 34, 52), (55, 62, 85), (110, 118, 140)
    else:
        fundo = misturar(cor, (20, 28, 50), 0.35 if por_cima else 0.6)
        borda, cor_t = clarear(cor, 0.3 if por_cima else 0.0), (255, 255, 255)
    pygame.draw.rect(s, fundo, r, border_radius=8)
    pygame.draw.rect(s, borda, r, 2 if por_cima else 1, border_radius=8)
    texto(s, txt, tamanho, cor_t, r.center)


def _caixa(s, r, titulo=None):
    pygame.draw.rect(s, (14, 22, 44), r, border_radius=12)
    pygame.draw.rect(s, (45, 70, 130), r, 1, border_radius=12)
    if titulo:
        texto(s, titulo, 14, COR_DESTAQUE, (r.left + 16, r.top + 20), ancora="midleft")


def _toast(s, msg, cor):
    img = fonte(15).render(msg, True, cor)
    caixa = img.get_rect(center=(WIDTH // 2, 612)).inflate(30, 14)
    pygame.draw.rect(s, (10, 16, 34), caixa, border_radius=14)
    pygame.draw.rect(s, cor, caixa, 1, border_radius=14)
    s.blit(img, img.get_rect(center=caixa.center))


REGRAS_PONTOS = [
    ("jogar", "Jogou: +1  •  do cinco inicial: +1"),
    ("estrela", "Cada golo: +3"),
    ("trofeu", "Vitória da equipa: +2  •  empate: +1"),
    ("escudo", "Guarda-redes: poucos golos sofridos até +4; penálti ou livre falhado pelo rival +2"),
    ("cruz", "Cartão azul: -1  •  vermelho: -3"),
]


# ====================================================================== #
# As minhas ligas                                                         #
# ====================================================================== #

class EcraSonhoLigas:
    def __init__(self, screen, arena=None, ligada: bool = False):
        self.screen = screen
        self.arena = arena
        self.ligada = ligada
        self.t = 0.0
        self.ligas = None            # None = ainda não chegou a lista
        self.a_atualizar = False     # o servidor está a ler os jogos da FPP
        self.ocupado = False
        self.a_acordar = False
        self.erro = ""               # erro do formulário (nome ou código)
        self.aviso_servidor = ""     # problema com o servidor (aparece na caixa das ligas)
        self.campos = ["", ""]       # nome da liga nova, código para entrar
        self.campo = 0
        self.r_campos = [pygame.Rect(700, 196, 390, 48), pygame.Rect(700, 330, 390, 48)]
        self.r_criar = pygame.Rect(1100, 196, 134, 48)
        self.r_entrar = pygame.Rect(1100, 330, 134, 48)
        self.zonas = []
        self.btn_voltar = BotaoMenu((40, 648, 230, 50), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                                    seta=False, tamanho=18)
        self.btn_conta = BotaoMenu((WIDTH // 2 - 230, 400, 460, 64), "ENTRAR NA CONTA",
                                   "A liga é online: precisas de uma conta", "conta", (40, 200, 210), "jogador")
        if ligada:
            try:
                pygame.key.start_text_input()
            except pygame.error:
                pass

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "voltar"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_voltar.por_cima(event.pos):
                return "voltar"
            if not self.ligada:
                return "conta" if self.btn_conta.por_cima(event.pos) else None
            for r, acao in self.zonas:
                if r.collidepoint(event.pos):
                    return self._acao(acao)
            for i, r in enumerate(self.r_campos):
                if r.collidepoint(event.pos):
                    self.campo = i
            if self.r_criar.collidepoint(event.pos):
                return self._acao(("criar",))
            if self.r_entrar.collidepoint(event.pos):
                return self._acao(("entrar",))
        if not self.ligada:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return "conta"
            return None
        if event.type == pygame.TEXTINPUT:
            limite = 24 if self.campo == 0 else 5
            if event.text.isprintable() and len(self.campos[self.campo]) < limite:
                self.campos[self.campo] += event.text.upper() if self.campo == 1 else event.text
                self.erro = ""
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.campos[self.campo] = self.campos[self.campo][:-1]
            elif event.key in (pygame.K_TAB, pygame.K_DOWN, pygame.K_UP):
                self.campo = 1 - self.campo
                som.ui("mover")
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._acao(("criar",) if self.campo == 0 else ("entrar",))
        return None

    def _acao(self, acao):
        if self.ocupado:
            return None
        if acao[0] == "criar":
            if len(self.campos[0].strip()) < 3:
                self.erro = "Escreve um nome para a liga (pelo menos 3 letras)."
                return None
            return ("criar", self.campos[0].strip())
        if acao[0] == "entrar":
            if len(self.campos[1].strip()) != 5:
                self.erro = "O código tem 5 letras (pede-o a quem criou a liga)."
                return None
            return ("entrar", self.campos[1].strip())
        return acao

    def update(self, dt):
        self.t += dt
        mpos = pygame.mouse.get_pos()
        self.btn_voltar.animar(dt, self.btn_voltar.por_cima(mpos))
        self.btn_conta.animar(dt, True)

    def draw(self):
        s = self.screen
        mpos = pygame.mouse.get_pos()
        self.zonas = []
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(1000, 420, COR_DESTAQUE, 30)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 60)), special_flags=pygame.BLEND_RGB_ADD)
        texto(s, "EQUIPA DE SONHO", 32, COR_TEXTO, (40, 46), ancora="midleft", sombra=True)
        texto(s, "Fantasy com os jogos reais do Campeonato Placard: os teus jogadores ganham pontos com o que "
                 "fazem nos jogos verdadeiros.", 14, COR_TEXTO_SUAVE, (40, 80), ancora="midleft", negrito=False)
        if not self.ligada:
            painel_vidro(s, pygame.Rect(WIDTH // 2 - 330, 220, 660, 280), 18, 230)
            texto(s, "Precisas de uma conta", 24, COR_TEXTO, (WIDTH // 2, 270))
            texto(s, "As ligas são jogadas online com os teus amigos.", 15, COR_TEXTO_SUAVE, (WIDTH // 2, 310),
                  negrito=False)
            texto(s, "Entra (ou cria uma conta) e volta aqui.", 15, COR_TEXTO_SUAVE, (WIDTH // 2, 334),
                  negrito=False)
            self.btn_conta.draw(s)
            self.btn_voltar.draw(s)
            return

        esq = pygame.Rect(40, 120, 600, 510)
        _caixa(s, esq, "AS MINHAS LIGAS")
        if self.ligas is None:
            pontos = "." * (1 + int(self.t * 2) % 3)
            msg = "O servidor está a acordar" if self.a_acordar else "A ligar ao servidor"
            texto(s, msg + pontos, 15, COR_TEXTO_SUAVE, esq.center, negrito=False)
        elif not self.ligas and self.aviso_servidor:
            s.blit(icone("cruz", 30, VERMELHO), (esq.centerx - 15, esq.top + 70))
            linhas, linha = [], ""
            for palavra in self.aviso_servidor.split():
                if fonte(15, False).size(linha + " " + palavra)[0] > esq.w - 60:
                    linhas.append(linha)
                    linha = palavra
                else:
                    linha = (linha + " " + palavra).strip()
            linhas.append(linha)
            for i, l in enumerate(linhas):
                texto(s, l, 15, COR_TEXTO, (esq.centerx, esq.top + 130 + i * 22), negrito=False)
        elif not self.ligas:
            texto(s, "Ainda não estás em nenhuma liga.", 16, COR_TEXTO_SUAVE, (esq.centerx, esq.top + 100), negrito=False)
            texto(s, "Cria uma e dá o código aos teus amigos,", 14, COR_TEXTO_SUAVE, (esq.centerx, esq.top + 130),
                  negrito=False)
            texto(s, "ou entra com o código que te deram.", 14, COR_TEXTO_SUAVE, (esq.centerx, esq.top + 152),
                  negrito=False)
        for i, l in enumerate(self.ligas or []):
            r = pygame.Rect(esq.left + 16, esq.top + 46 + i * 70, esq.w - 32, 60)
            sim = r.collidepoint(mpos)
            pygame.draw.rect(s, (40, 70, 130) if sim else (22, 32, 60), r, border_radius=10)
            pygame.draw.rect(s, (110, 170, 255) if sim else (45, 70, 130), r, 1, border_radius=10)
            s.blit(icone("trofeu", 26, COR_DESTAQUE), (r.left + 14, r.centery - 13))
            texto(s, l["nome"], 18, COR_TEXTO, (r.left + 54, r.top + 20), ancora="midleft")
            texto(s, f"Código {l['codigo']}  •  {l['membros']} treinador{'es' if l['membros'] != 1 else ''}", 13,
                  COR_TEXTO_SUAVE, (r.left + 54, r.top + 42), ancora="midleft", negrito=False)
            s.blit(icone("jogar", 18, COR_TEXTO), (r.right - 34, r.centery - 9))
            self.zonas.append((r, ("abrir", l["id"])))
        if self.a_atualizar:
            texto(s, "O servidor está a ler os jogos da Federação (pode demorar um minuto)...", 12, LARANJA,
                  (esq.centerx, esq.bottom - 18), negrito=False)

        for i, (titulo, sub, vazio, r_btn, txt_btn, cor) in enumerate((
                ("CRIAR UMA LIGA", "Recebes um código para dares aos teus amigos.", "Nome da liga...",
                 self.r_criar, "CRIAR", VERDE),
                ("ENTRAR NUMA LIGA", "Escreve o código de 5 letras da liga de um amigo.", "Código...",
                 self.r_entrar, "ENTRAR", AZUL))):
            r = self.r_campos[i]
            texto(s, titulo, 15, COR_DESTAQUE, (r.left, r.top - 42), ancora="midleft")
            texto(s, sub, 12, COR_TEXTO_SUAVE, (r.left, r.top - 20), ancora="midleft", negrito=False)
            painel_vidro(s, r, 10, 230, COR_DESTAQUE if self.campo == i else (60, 90, 150))
            cursor = "|" if self.campo == i and int(self.t * 2) % 2 == 0 else ""
            if self.campos[i]:
                texto(s, self.campos[i] + cursor, 20, (255, 255, 255), (r.left + 14, r.centery), ancora="midleft")
            else:
                texto(s, vazio + cursor, 17, (120, 135, 170), (r.left + 14, r.centery), ancora="midleft", negrito=False)
            _botao(s, r_btn, txt_btn, cor, mpos, not self.ocupado, 15)
        if self.erro:
            texto(s, self.erro, 13, VERMELHO, (700, 404), ancora="midleft")

        regras = pygame.Rect(680, 430, 560, 200)
        _caixa(s, regras, "COMO SE GANHAM PONTOS (EM CADA JOGO REAL)")
        for i, (ic, linha) in enumerate(REGRAS_PONTOS):
            y = regras.top + 52 + i * 29
            s.blit(icone(ic, 16, COR_DESTAQUE), (regras.left + 18, y - 8))
            texto(s, linha, 13, COR_TEXTO, (regras.left + 46, y), ancora="midleft", negrito=False)
        self.btn_voltar.draw(s)
        texto(s, "TAB  mudar de campo     ENTER  confirmar     ESC  voltar", 12, (120, 145, 195),
              (WIDTH // 2, HEIGHT - 12), negrito=False)


# ====================================================================== #
# O painel da liga                                                        #
# ====================================================================== #

ABAS = ["PLANTEL", "MERCADO", "RIVAIS", "LIGA"]
QUADRO = pygame.Rect(46, 140, 400, 476)
LUGARES = [(246, 222), (136, 332), (356, 332), (246, 442)]   # os 4 jogadores de campo, em losango
LUGAR_GR = (246, 552)
MINI = (84, 108)


class EcraSonhoLiga:
    def __init__(self, screen, estado: dict, arena=None):
        self.screen = screen
        self.arena = arena
        self.t = 0.0
        self.aba = 0
        self.sel = None
        self.rival = None            # conta_id do rival escolhido no separador RIVAIS
        self.valor = 0               # oferta / proposta que se está a preparar
        self.ocupado = False
        self.msg, self.msg_cor, self.msg_t = "", COR_TEXTO, 0.0
        self.confirmar = None        # (pergunta, ação)
        self.ficha = None            # ficha de um jogador (jogos e pontos)
        self.zonas = []
        self._r_sim = pygame.Rect(0, 0, 0, 0)
        self.lista = ListaBotoes([
            BotaoMenu((30, 640, 390, 58), "ATUALIZAR", "Ver se há jogos novos", "atualizar", (40, 190, 100),
                      "recomecar", seta=False),
            BotaoMenu((440, 640, 400, 58), "AS MINHAS LIGAS", "Criar ou entrar noutra liga", "ligas",
                      (255, 170, 40), "trofeu", seta=False),
            BotaoMenu((860, 640, 390, 58), "MENU", "", "menu", (150, 110, 255), "casa", seta=False, tamanho=19)])
        self.receber(estado)

    # ------------------------------------------------------------------ dados
    def receber(self, estado: dict):
        self.e = estado
        self.cartas = sorted(estado["cartas"], key=lambda c: (not c["gr"], -c["pontos"]))
        self.mercado = sorted(estado["mercado"], key=lambda c: -c["valor"])
        self.livres = estado["dinheiro"] - estado.get("licitado", 0)
        rivais = {}
        for c in estado["rivais"]:
            rivais.setdefault(c["dono"], []).append(c)
        self.rivais = rivais
        self.tabela = estado["tabela"]
        if self.rival not in {t["conta_id"] for t in self.tabela if not t["eu"]}:
            self.rival = next((t["conta_id"] for t in self.tabela if not t["eu"]), None)
        ids = {c["fed"] for c in self.cartas + self.mercado + estado["rivais"]}
        if self.sel not in ids:
            self.sel = None
        c = next((c for c in self.mercado if c["fed"] == self.sel), None)
        if c is not None and self.aba == 1:
            self.valor = c.get("minha_oferta") or max(self.valor, c["valor"])

    def mensagem(self, ok: bool, txt: str):
        self.msg, self.msg_cor, self.msg_t = txt, (VERDE if ok else VERMELHO), 3.5
        som.ui("confirmar" if ok else "mover")

    def _carta(self, fed):
        return next((c for c in self.cartas + self.mercado + self.e["rivais"] if c["fed"] == fed), None)

    # ------------------------------------------------------------------ eventos
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if self.ficha is not None:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.ficha = None
            return None
        if self.confirmar is not None:
            sim = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
            nao = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sim = self._r_sim.collidepoint(event.pos)
                nao = not sim
            if sim:
                acao, self.confirmar = self.confirmar[1], None
                return acao if not self.ocupado else None
            if nao:
                self.confirmar = None
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "ligas"
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self._mudar_aba(event.key - pygame.K_1)
                return None
            if event.key in (pygame.K_q, pygame.K_e):
                self._mudar_aba((self.aba + (1 if event.key == pygame.K_e else -1)) % len(ABAS))
                return None
        if event.type == pygame.MOUSEWHEEL and self.sel:
            self._mudar_valor(PASSO * (1 if event.y > 0 else -1))
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, acao in reversed(self.zonas):
                if r.collidepoint(event.pos):
                    return self._clicar(acao)
        return self.lista.handle_event(event)

    def _mudar_aba(self, aba):
        if aba != self.aba:
            self.aba, self.sel = aba, None
            som.ui("mover")

    def _mudar_valor(self, d):
        c = self._carta(self.sel)
        if c is not None and self.aba in (1, 2):
            minimo = c["valor"] if self.aba == 1 else PASSO
            self.valor = max(minimo, self.valor + d)
            som.ui("mover")

    def _clicar(self, acao):
        tipo = acao[0]
        if tipo == "aba":
            self._mudar_aba(acao[1])
        elif tipo == "carta":
            self.sel = acao[1]
            c = self._carta(acao[1])
            if self.aba == 1:
                self.valor = c.get("minha_oferta") or c["valor"]
            elif self.aba == 2:
                self.valor = c["valor"]
            som.ui("mover")
        elif tipo == "rival":
            self.rival, self.sel = acao[1], None
            som.ui("mover")
        elif tipo == "valor":
            self._mudar_valor(acao[1])
        elif tipo == "confirmar":
            self.confirmar = (acao[1], acao[2])
        elif tipo == "pedido":
            return acao if not self.ocupado else None
        return None

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        mpos = pygame.mouse.get_pos()
        for b in self.lista.botoes:
            b.animar(dt, b.por_cima(mpos))

    # ------------------------------------------------------------------ desenho
    def draw(self):
        s = self.screen
        mpos = pygame.mouse.get_pos()
        self.zonas = []
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(1000, 400, COR_DESTAQUE, 26)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 60)), special_flags=pygame.BLEND_RGB_ADD)
        self._topo(s)
        for i, nome in enumerate(ABAS):
            r = pygame.Rect(30 + i * 182, 84, 172, 36)
            sim = i == self.aba
            pygame.draw.rect(s, (40, 80, 150) if sim else (20, 32, 62), r, border_radius=10)
            borda = (110, 170, 255) if sim else ((90, 120, 190) if r.collidepoint(mpos) else (45, 70, 130))
            pygame.draw.rect(s, borda, r, 2 if sim else 1, border_radius=10)
            texto(s, f"{i + 1}  {nome}", 15, COR_TEXTO if sim else COR_TEXTO_SUAVE, r.center)
            n = sum(1 for p in self.e["propostas"] if p["recebida"]) if i == 1 else 0
            if n:
                pygame.draw.circle(s, VERMELHO, (r.right - 10, r.top + 4), 10)
                texto(s, str(n), 12, (255, 255, 255), (r.right - 10, r.top + 4))
            self.zonas.append((r, ("aba", i)))
        if self.ocupado or self.e.get("a_atualizar"):
            txt = "A falar com o servidor..." if self.ocupado else "O servidor está a ler jogos novos da Federação..."
            texto(s, txt, 12, LARANJA, (1244, 102), ancora="midright", negrito=False)
        else:
            texto(s, "Q / E ou 1-4  separadores", 12, (110, 130, 175), (1244, 102), ancora="midright", negrito=False)
        painel_vidro(s, pygame.Rect(30, 126, 1220, 502), 16, 215)
        [self._plantel, self._mercado, self._rivais, self._liga][self.aba](s, mpos)
        self.lista.draw(s)
        if self.msg_t > 0:
            _toast(s, self.msg, self.msg_cor)
        if self.ficha is not None:
            self._desenhar_ficha(s)
        elif self.confirmar is not None:
            self._desenhar_confirmar(s, mpos)

    def _topo(self, s):
        e = self.e
        liga, jor = e["liga"], e["jornada"]
        s.blit(icone("trofeu", 40, COR_DESTAQUE), (34, 24))
        texto(s, liga["nome"].upper(), 26, COR_TEXTO, (86, 36), ancora="midleft", sombra=True)
        if jor.get("proxima"):
            sub = f"Código {liga['codigo']}  •  Jornada {jor['proxima']} começa {_hora(jor['inicio_proxima'])}"
        else:
            sub = f"Código {liga['codigo']}  •  Época terminada"
        texto(s, sub, 14, COR_TEXTO_SUAVE, (86, 64), ancora="midleft", negrito=False)
        r = texto(s, _moedas(e["dinheiro"]), 26, COR_DESTAQUE, (1244, 36), ancora="midright", sombra=True)
        s.blit(icone("moeda", 24, COR_DESTAQUE), (r.left - 32, r.centery - 12))
        extra = f"  •  {_moedas(e['licitado'])} em ofertas" if e.get("licitado") else ""
        texto(s, f"Leilões fecham às 20:00 (daqui a {_falta(liga['fecho'])}){extra}", 13, COR_TEXTO_SUAVE,
              (1244, 64), ancora="midright", negrito=False)

    # ------------------------------------------------------------------ PLANTEL
    def _plantel(self, s, mpos):
        pygame.draw.rect(s, (16, 40, 70), QUADRO, border_radius=14)
        pygame.draw.rect(s, (60, 110, 170), QUADRO, 2, border_radius=14)
        pygame.draw.rect(s, (60, 110, 170), (QUADRO.centerx - 70, QUADRO.bottom - 70, 140, 70), 1)
        texto(s, "O TEU CINCO", 13, COR_DESTAQUE, (QUADRO.left + 16, QUADRO.top + 20), ancora="midleft")
        jor = self.e["jornada"].get("proxima")
        texto(s, f"para a jornada {jor}" if jor else "", 12, COR_TEXTO_SUAVE, (QUADRO.right - 16, QUADRO.top + 20),
              ancora="midright", negrito=False)
        tit = [c for c in self.cartas if c["titular"]]
        gr = next((c for c in tit if c["gr"]), None)
        campo = [c for c in tit if not c["gr"]][:4]
        lugares = [(LUGARES[i], campo[i] if i < len(campo) else None, "Jogador") for i in range(4)]
        lugares.append((LUGAR_GR, gr, "Guarda-redes"))
        for centro, c, nome in lugares:
            r = pygame.Rect(0, 0, *MINI)
            r.center = centro
            if c is None:
                vazio = pygame.Surface(r.size, pygame.SRCALPHA)
                pygame.draw.rect(vazio, (255, 255, 255, 18), vazio.get_rect(), border_radius=10)
                s.blit(vazio, r)
                pygame.draw.rect(s, (110, 130, 175), r, 1, border_radius=10)
                texto(s, "+", 30, (140, 160, 200), (r.centerx, r.centery - 8))
                texto(s, nome, 11, (140, 160, 200), (r.centerx, r.bottom - 18), negrito=False)
                continue
            desenhar_carta(s, r, c, selecionada=c["fed"] == self.sel)
            self.zonas.append((r, ("carta", c["fed"])))

        x0, y0 = 480, 146
        texto(s, f"OS TEUS JOGADORES  ({len(self.cartas)}/{self.e['regras']['max_cartas']})", 15, COR_DESTAQUE,
              (x0, y0 + 8), ancora="midleft")
        ult = self.e["jornada"].get("ultima")
        pts_ult = self.e.get("pontos_ultima", {})
        w, h, gap = 132, 176, 14
        for i in range(self.e["regras"]["max_cartas"]):
            r = pygame.Rect(x0 + (i % 4) * (w + gap), y0 + 28 + (i // 4) * (h + 18), w, h)
            if i >= len(self.cartas):
                pygame.draw.rect(s, (40, 55, 90), r, 1, border_radius=10)
                texto(s, "vazio", 12, (80, 95, 130), r.center, negrito=False)
                continue
            c = self.cartas[i]
            p = pts_ult.get(str(c["fed"]))
            desenhar_carta(s, r, c, selecionada=c["fed"] == self.sel, titular=c["titular"],
                           badge=f"J{ult}: {p['pontos']} pts" if p else None, cor_badge=(60, 90, 160))
            self.zonas.append((r, ("carta", c["fed"])))
        texto(s, "A estrela marca o cinco, que fecha quando começa o 1.º jogo da jornada.", 12, COR_TEXTO_SUAVE,
              (x0, 590), ancora="midleft", negrito=False)
        texto(s, "O número grande de cada carta são os pontos da época.", 12, COR_TEXTO_SUAVE,
              (x0, 607), ancora="midleft", negrito=False)

        det = pygame.Rect(1066, 146, 168, 466)
        _caixa(s, det)
        c = next((c for c in self.cartas if c["fed"] == self.sel), None)
        if c is None:
            for i, linha in enumerate(["Escolhe um", "jogador", "", "Só o cinco ganha", "pontos na jornada.",
                                       "", "Cláusula: o preço", "para um rival te", "levar o jogador."]):
                texto(s, linha, 12, COR_TEXTO_SUAVE, (det.centerx, det.top + 40 + i * 19), negrito=False)
            return
        self._detalhe(s, det, c, mpos, meu=True)

    def _detalhe(self, s, det, c, mpos, meu: bool):
        cx = det.centerx
        nome, tn = _texto_que_cabe(c["nome"], det.w - 16, 15)
        texto(s, nome, tn, COR_TEXTO, (cx, det.top + 22))
        clube, tc = _texto_que_cabe(c["equipa"], det.w - 16, 12, 9)
        texto(s, clube, tc, COR_TEXTO_SUAVE, (cx, det.top + 42), negrito=False)
        linhas = [("Posição", "Guarda-redes" if c["gr"] else "Jogador"), ("Pontos", str(c["pontos"])),
                  ("Jogos", str(c["jogos"])), ("Golos", str(c["golos"])), ("Valor", _moedas(c["valor"]))]
        if "clausula" in c:
            linhas.append(("Cláusula", _moedas(c["clausula"])))
        for i, (rot, val) in enumerate(linhas):
            y = det.top + 70 + i * 21
            texto(s, rot, 12, COR_TEXTO_SUAVE, (det.left + 12, y), ancora="midleft", negrito=False)
            texto(s, val, 13, LARANJA if rot == "Cláusula" else COR_TEXTO, (det.right - 12, y), ancora="midright")
        if c.get("protegida"):
            texto(s, "Protegido (24 h)", 11, VERDE, (cx, det.top + 70 + len(linhas) * 21), negrito=False)
        y = det.top + 230
        r = pygame.Rect(det.left + 10, y, det.w - 20, 32)
        _botao(s, r, "VER JOGOS", AZUL, mpos, not self.ocupado, 12)
        self.zonas.append((r, ("pedido", "fantasy_jogador", {"fed": c["fed"]})))
        if not meu:
            return
        regras = self.e["regras"]
        aumento = max(PASSO, round(c["valor"] * 0.5 / PASSO) * PASSO)
        custo = max(100, round(aumento * regras["custo_clausula"] / 100) * 100)
        venda = max(100, round(c["valor"] * regras["venda"] / 100) * 100)
        botoes = [("TIRAR DO CINCO" if c["titular"] else "PÔR NO CINCO",
                   ("pedido", "fantasy_titular", {"fed": c["fed"]}), AZUL, None),
                  ("SUBIR CLÁUSULA", ("pedido", "fantasy_subir_clausula", {"fed": c["fed"]}), LARANJA,
                   f"+{_moedas(aumento)} por {_moedas(custo)}"),
                  ("VENDER JÁ", ("confirmar", f"Vender {c['nome']} ao mercado por {_moedas(venda)} moedas?",
                                 ("pedido", "fantasy_vender", {"fed": c["fed"]})), VERMELHO, f"recebes {_moedas(venda)}")]
        for i, (txt, acao, cor, nota) in enumerate(botoes):
            r = pygame.Rect(det.left + 10, y + 44 + i * 58, det.w - 20, 34)
            _botao(s, r, txt, cor, mpos, not self.ocupado, 12)
            self.zonas.append((r, acao))
            if nota:
                texto(s, nota, 11, COR_TEXTO_SUAVE, (r.centerx, r.bottom + 10), negrito=False)

    # ------------------------------------------------------------------ MERCADO
    def _mercado(self, s, mpos):
        texto(s, "À VENDA HOJE", 15, COR_DESTAQUE, (54, 154), ancora="midleft")
        texto(s, "Ofertas secretas: às 20:00 quem oferecer mais leva o jogador.", 12, COR_TEXTO_SUAVE,
              (180, 154), ancora="midleft", negrito=False)
        w, h, gap = 112, 148, 18
        for i, c in enumerate(self.mercado[:8]):
            r = pygame.Rect(54 + (i % 4) * (w + gap), 176 + (i // 4) * (h + 22), w, h)
            desenhar_carta(s, r, c, selecionada=c["fed"] == self.sel, badge=_moedas(c["valor"]),
                           cor_badge=(60, 90, 160), canto="OFERTASTE" if c.get("minha_oferta") else None)
            self.zonas.append((r, ("carta", c["fed"])))
        if not self.mercado:
            texto(s, "Não há jogadores à venda.", 15, COR_TEXTO_SUAVE, (310, 330), negrito=False)
        c = next((c for c in self.mercado if c["fed"] == self.sel), None)
        det = pygame.Rect(586, 146, 250, 360)
        _caixa(s, det)
        if c is None:
            texto(s, "Escolhe um jogador", 14, COR_TEXTO_SUAVE, (det.centerx, det.top + 40), negrito=False)
            texto(s, "para fazeres uma oferta.", 14, COR_TEXTO_SUAVE, (det.centerx, det.top + 62), negrito=False)
        else:
            self._detalhe(s, det, c, mpos, meu=False)
            n = c.get("ofertas", 0)
            texto(s, f"{n} oferta{'s' if n != 1 else ''} até agora", 12, LARANJA, (det.centerx, det.top + 290),
                  negrito=False)
        caixa = pygame.Rect(54, 516, 782, 92)
        _caixa(s, caixa)
        if c is None:
            texto(s, f"Moedas livres: {_moedas(self.livres)}", 15, COR_TEXTO_SUAVE, caixa.center, negrito=False)
        else:
            livres = self.livres + (c.get("minha_oferta") or 0)
            texto(s, f"A tua oferta por {c['nome']}  (mínimo {_moedas(c['valor'])}  •  livres {_moedas(livres)})",
                  13, COR_TEXTO_SUAVE, (caixa.left + 16, caixa.top + 18), ancora="midleft", negrito=False)
            self._controlo_valor(s, mpos, caixa.left + 16, caixa.top + 36, c["valor"])
            r_of = pygame.Rect(caixa.left + 330, caixa.top + 36, 190, 44)
            _botao(s, r_of, "MUDAR OFERTA" if c.get("minha_oferta") else "FAZER OFERTA", VERDE, mpos,
                   not self.ocupado, 14)
            self.zonas.append((r_of, ("pedido", "fantasy_licitar", {"fed": c["fed"], "valor": self.valor})))
            if c.get("minha_oferta"):
                r_ret = pygame.Rect(caixa.left + 532, caixa.top + 36, 150, 44)
                _botao(s, r_ret, "RETIRAR", VERMELHO, mpos, not self.ocupado, 14)
                self.zonas.append((r_ret, ("pedido", "fantasy_retirar", {"fed": c["fed"]})))
        col = pygame.Rect(852, 146, 382, 462)
        _caixa(s, col, "PROPOSTAS")
        props = self.e["propostas"]
        if not props:
            texto(s, "Ainda não há propostas.", 13, COR_TEXTO_SUAVE, (col.centerx, col.top + 70), negrito=False)
            texto(s, "Faz uma no separador RIVAIS.", 12, (120, 135, 170), (col.centerx, col.top + 92), negrito=False)
        for i, p in enumerate(props[:5]):
            r = pygame.Rect(col.left + 12, col.top + 42 + i * 82, col.w - 24, 74)
            pygame.draw.rect(s, (22, 32, 60), r, border_radius=10)
            if p["recebida"]:
                texto(s, f"{p['de']} quer {p['nome']}", 13, LARANJA, (r.left + 12, r.top + 16), ancora="midleft")
                texto(s, f"Oferece {_moedas(p['valor'])} moedas", 12, COR_TEXTO, (r.left + 12, r.top + 36),
                      ancora="midleft", negrito=False)
                r_a = pygame.Rect(r.right - 196, r.bottom - 30, 90, 24)
                r_r = pygame.Rect(r.right - 100, r.bottom - 30, 90, 24)
                _botao(s, r_a, "ACEITAR", VERDE, mpos, not self.ocupado, 12)
                _botao(s, r_r, "RECUSAR", VERMELHO, mpos, not self.ocupado, 12)
                self.zonas += [(r_a, ("pedido", "fantasy_responder", {"proposta": p["id"], "aceitar": True})),
                               (r_r, ("pedido", "fantasy_responder", {"proposta": p["id"], "aceitar": False}))]
            else:
                texto(s, f"Pediste {p['nome']} a {p['para']}", 13, COR_TEXTO, (r.left + 12, r.top + 16), ancora="midleft")
                texto(s, f"Ofereceste {_moedas(p['valor'])} moedas  •  à espera", 12, COR_TEXTO_SUAVE,
                      (r.left + 12, r.top + 36), ancora="midleft", negrito=False)
                r_r = pygame.Rect(r.right - 100, r.bottom - 30, 90, 24)
                _botao(s, r_r, "RETIRAR", VERMELHO, mpos, not self.ocupado, 12)
                self.zonas.append((r_r, ("pedido", "fantasy_responder", {"proposta": p["id"], "aceitar": False})))

    def _controlo_valor(self, s, mpos, x, y, minimo):
        r_m = pygame.Rect(x, y, 46, 44)
        r_p = pygame.Rect(x + 254, y, 46, 44)
        _botao(s, r_m, "−", AZUL, mpos, self.valor > minimo, 24)
        _botao(s, r_p, "+", AZUL, mpos, True, 24)
        texto(s, _moedas(self.valor), 24, COR_DESTAQUE, ((r_m.right + r_p.left) // 2, r_m.centery))
        self.zonas += [(r_m, ("valor", -PASSO)), (r_p, ("valor", PASSO))]

    # ------------------------------------------------------------------ RIVAIS
    def _rivais(self, s, mpos):
        esq = pygame.Rect(46, 146, 300, 462)
        _caixa(s, esq, "TREINADORES")
        outros = [t for t in self.tabela if not t["eu"]]
        if not outros:
            texto(s, "Ainda estás sozinho.", 13, COR_TEXTO_SUAVE, (esq.centerx, esq.top + 70), negrito=False)
            texto(s, f"Dá o código {self.e['liga']['codigo']}", 13, COR_DESTAQUE, (esq.centerx, esq.top + 94))
            texto(s, "aos teus amigos.", 13, COR_TEXTO_SUAVE, (esq.centerx, esq.top + 116), negrito=False)
        for i, t in enumerate(outros[:9]):
            r = pygame.Rect(esq.left + 10, esq.top + 40 + i * 46, esq.w - 20, 40)
            sim = t["conta_id"] == self.rival
            pygame.draw.rect(s, (40, 80, 150) if sim else (22, 32, 60), r, border_radius=8)
            texto(s, t["alcunha"], 14, COR_TEXTO, (r.left + 12, r.centery), ancora="midleft")
            texto(s, f"{t['pontos']} pts", 12, COR_TEXTO_SUAVE, (r.right - 12, r.centery), ancora="midright",
                  negrito=False)
            self.zonas.append((r, ("rival", t["conta_id"])))
        dir_ = pygame.Rect(360, 146, 874, 462)
        _caixa(s, dir_)
        cartas = sorted(self.rivais.get(self.rival, []), key=lambda c: (not c["gr"], -c["pontos"]))
        c_sel = next((c for c in cartas if c["fed"] == self.sel), None)
        if c_sel is None:
            texto(s, "PROPOR: o dono decide se vende.   PAGAR: pagas a cláusula e o jogador passa logo para ti.",
                  12, COR_TEXTO_SUAVE, (dir_.left + 16, dir_.top + 24), ancora="midleft", negrito=False)
        else:
            texto(s, f"Proposta por {c_sel['nome']}:", 13, COR_TEXTO, (dir_.left + 16, dir_.top + 26), ancora="midleft")
            self._controlo_valor(s, mpos, dir_.left + 270, dir_.top + 4, PASSO)
            r_env = pygame.Rect(dir_.left + 590, dir_.top + 4, 160, 44)
            _botao(s, r_env, "ENVIAR", VERDE, mpos, not self.ocupado, 14)
            self.zonas.append((r_env, ("pedido", "fantasy_propor", {"fed": c_sel["fed"], "valor": self.valor})))
        for i, c in enumerate(cartas[:8]):
            r = pygame.Rect(dir_.left + 10, dir_.top + 56 + i * 50, dir_.w - 20, 46)
            sim = c["fed"] == self.sel
            pygame.draw.rect(s, (40, 70, 130) if sim else ((22, 32, 60) if i % 2 == 0 else (18, 27, 52)), r,
                             border_radius=8)
            topo, base, cor_t = CORES_RARIDADE[raridade(c["valor"])]
            rg = pygame.Rect(r.left + 6, r.top + 6, 40, 34)
            gradiente_vertical(s, rg, topo, base, raio=6)
            texto(s, str(c["pontos"]), 15, cor_t, rg.center)
            texto(s, c["nome"], 14, COR_TEXTO, (r.left + 58, r.top + 15), ancora="midleft")
            info = f"{'Guarda-redes' if c['gr'] else 'Jogador'}  •  {c['equipa']}{'  •  no cinco' if c['titular'] else ''}"
            texto(s, info, 11, COR_TEXTO_SUAVE, (r.left + 58, r.top + 33), ancora="midleft", negrito=False)
            texto(s, f"Valor {_moedas(c['valor'])}", 12, COR_TEXTO_SUAVE, (r.right - 290, r.centery), ancora="midright",
                  negrito=False)
            texto(s, f"Cláusula {_moedas(c['clausula'])}", 13, LARANJA, (r.right - 168, r.centery), ancora="midright")
            r_p = pygame.Rect(r.right - 158, r.top + 9, 70, 28)
            _botao(s, r_p, "PROTEG." if c["protegida"] else "PAGAR", VERDE, mpos,
                   not c["protegida"] and c["clausula"] <= self.livres and not self.ocupado, 11)
            self.zonas.append((r_p, ("confirmar", f"Pagar {_moedas(c['clausula'])} moedas pela cláusula de {c['nome']}?",
                                     ("pedido", "fantasy_pagar_clausula", {"fed": c["fed"]}))))
            r_v = pygame.Rect(r.right - 80, r.top + 9, 70, 28)
            _botao(s, r_v, "PROPOR", AZUL, mpos, not self.ocupado, 11)
            self.zonas.append((r_v, ("carta", c["fed"])))

    # ------------------------------------------------------------------ LIGA
    def _liga(self, s, mpos):
        esq = pygame.Rect(46, 146, 570, 462)
        _caixa(s, esq, "CLASSIFICAÇÃO")
        texto(s, "PTS", 12, COR_TEXTO_SUAVE, (esq.right - 150, esq.top + 20), negrito=False)
        texto(s, "ÚLT.", 12, COR_TEXTO_SUAVE, (esq.right - 90, esq.top + 20), negrito=False)
        for i, t in enumerate(self.tabela[:10]):
            r = pygame.Rect(esq.left + 10, esq.top + 38 + i * 41, esq.w - 20, 36)
            pygame.draw.rect(s, (40, 70, 130) if t["eu"] else (22, 32, 60), r, border_radius=8)
            texto(s, f"{i + 1}.º", 15, COR_DESTAQUE if i == 0 else COR_TEXTO, (r.left + 24, r.centery))
            texto(s, t["alcunha"], 15, COR_TEXTO, (r.left + 56, r.centery), ancora="midleft")
            texto(s, str(t["pontos"]), 16, COR_TEXTO, (r.right - 140, r.centery))
            if t.get("ultima") is not None:
                texto(s, f"+{t['ultima']}", 13, VERDE, (r.right - 80, r.centery))
        texto(s, f"Só contam as jornadas a partir da {self.e['liga']['jornada_inicio']}.ª (quando a liga foi criada).",
              11, COR_TEXTO_SUAVE, (esq.centerx, esq.bottom - 14), negrito=False)
        res = pygame.Rect(632, 146, 602, 250)
        ult = self.e["jornada"].get("ultima")
        _caixa(s, res, f"CAMPEONATO PLACARD  •  JORNADA {ult}" if ult else "CAMPEONATO PLACARD")
        for i, g in enumerate(self.e["resultados"][:7]):
            y = res.top + 50 + i * 28
            casa, tc = _texto_que_cabe(g["casa"], 230, 12, 9)
            fora, tf = _texto_que_cabe(g["fora"], 230, 12, 9)
            texto(s, casa, tc, COR_TEXTO, (res.centerx - 34, y), ancora="midright")
            texto(s, fora, tf, COR_TEXTO, (res.centerx + 34, y), ancora="midleft")
            rs = f"{g['golos_casa']} - {g['golos_fora']}" if g["golos_casa"] is not None else _hora(g["inicio"])[:5]
            texto(s, rs, 13, COR_DESTAQUE, (res.centerx, y))
        nots = pygame.Rect(632, 408, 602, 200)
        _caixa(s, nots, "NOTÍCIAS DA LIGA")
        for i, n in enumerate(self.e["noticias"][:5]):
            y = nots.top + 48 + i * 30
            pygame.draw.circle(s, COR_NOTICIA.get(n["tipo"], AZUL), (nots.left + 20, y), 5)
            txt, tn = _texto_que_cabe(n["texto"], nots.w - 50, 12, 9)
            if txt != n["texto"]:
                txt = n["texto"][:80] + "…"
            texto(s, txt, tn, COR_TEXTO, (nots.left + 34, y), ancora="midleft", negrito=False)

    # ------------------------------------------------------------------ caixas por cima
    def _desenhar_confirmar(self, s, mpos):
        escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        escuro.fill((5, 8, 18, 190))
        s.blit(escuro, (0, 0))
        caixa = pygame.Rect(WIDTH // 2 - 340, 250, 680, 190)
        painel_vidro(s, caixa, 16, 245, COR_DESTAQUE)
        pergunta = self.confirmar[0]
        t = next((t for t in range(18, 11, -1) if fonte(t).size(pergunta)[0] <= caixa.w - 40), 12)
        texto(s, pergunta, t, COR_TEXTO, (caixa.centerx, caixa.top + 60))
        self._r_sim = pygame.Rect(caixa.centerx - 190, caixa.bottom - 76, 170, 48)
        r_nao = pygame.Rect(caixa.centerx + 20, caixa.bottom - 76, 170, 48)
        _botao(s, self._r_sim, "SIM", VERDE, mpos, tamanho=16)
        _botao(s, r_nao, "NÃO", VERMELHO, mpos, tamanho=16)

    def _desenhar_ficha(self, s):
        f = self.ficha
        escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        escuro.fill((5, 8, 18, 210))
        s.blit(escuro, (0, 0))
        caixa = pygame.Rect(WIDTH // 2 - 420, 90, 840, 520)
        painel_vidro(s, caixa, 18, 245, COR_DESTAQUE)
        desenhar_carta(s, pygame.Rect(caixa.left + 30, caixa.top + 30, 150, 200), f)
        texto(s, f["nome"], 26, COR_TEXTO, (caixa.left + 210, caixa.top + 50), ancora="midleft")
        texto(s, f"{f['equipa']}  •  {'Guarda-redes' if f['gr'] else 'Jogador'}  •  N.º {f['numero']}", 14,
              COR_TEXTO_SUAVE, (caixa.left + 210, caixa.top + 80), ancora="midleft", negrito=False)
        texto(s, f"{f['pontos']} pontos em {f['jogos']} jogos  •  {f['golos']} golos  •  valor {_moedas(f['valor'])}",
              15, COR_DESTAQUE, (caixa.left + 210, caixa.top + 110), ancora="midleft")
        y0 = caixa.top + 250
        for x, cab in zip((50, 130, 560, 640, 740), ("JORNADA", "JOGO", "", "GOLOS", "PONTOS")):
            texto(s, cab, 11, COR_TEXTO_SUAVE, (caixa.left + x, y0), ancora="midleft")
        jogos = f.get("jogos_lista", [])
        if not jogos:
            texto(s, "Ainda não jogou nenhum jogo do campeonato.", 14, COR_TEXTO_SUAVE, (caixa.centerx, y0 + 50),
                  negrito=False)
        for i, g in enumerate(jogos[-9:]):
            y = y0 + 26 + i * 25
            texto(s, f"J{g['jornada']}", 13, COR_TEXTO, (caixa.left + 50, y), ancora="midleft")
            jogo, tj = _texto_que_cabe(f"{g['casa']}  {g['golos_casa']}-{g['golos_fora']}  {g['fora']}", 420, 13, 9)
            texto(s, jogo, tj, COR_TEXTO, (caixa.left + 130, y), ancora="midleft", negrito=False)
            estado = "cinco inicial" if g["cinco"] else ("entrou" if g["jogou"] else "não jogou")
            texto(s, estado, 12, COR_TEXTO_SUAVE, (caixa.left + 560, y), ancora="midleft", negrito=False)
            texto(s, str(g["golos"]), 13, COR_TEXTO, (caixa.left + 655, y))
            texto(s, str(g["pontos"]), 14, VERDE if g["pontos"] > 0 else VERMELHO, (caixa.left + 760, y))
        texto(s, "Clica ou carrega numa tecla para fechar", 12, (150, 170, 210), (caixa.centerx, caixa.bottom - 18),
              negrito=False)


# ====================================================================== #
# Ligação à classe Game                                                   #
# ====================================================================== #

class SonhoMixin:
    """Métodos do modo EQUIPA DE SONHO usados pela classe Game (game.py)."""

    def _sonho_iniciar(self):
        self.ecra_sonho = None           # o painel de uma liga
        self.ecra_sonho_ligas = None     # a lista das minhas ligas
        self._sonho_liga = None          # id da liga aberta
        self._sonho_pend = {}            # pedido ao servidor -> tipo
        self._sonho_espera = {}          # pedido -> segundos à espera (com a ligação feita)

    def abrir_sonho(self):
        """Menu principal -> Equipa de Sonho: as minhas ligas (é preciso ter a conta aberta)."""
        self._cancelar_mira()
        self.pausado = self.jogo_ativo = self.fim_jogo = False
        self.ecra_sonho_ligas = EcraSonhoLigas(self.screen, arena=self.rink._surf, ligada=self.conta.ligada)
        self.estado = "sonho_ligas"
        self._sonho_liga = None
        self._sonho_pend.clear()
        self._sonho_espera.clear()
        if self.conta.ligada:
            self._sonho_pedir("fantasy_ligas")

    def _sonho_ecra(self):
        return self.ecra_sonho if self.estado == "sonho" else self.ecra_sonho_ligas

    def _sonho_draw(self):
        self._sonho_ecra().draw()

    def _sonho_pedir(self, tipo: str, **dados):
        srv = self._online_servidor()
        if self._sonho_liga is not None:
            dados.setdefault("liga", self._sonho_liga)
        pid = srv.pedir(tipo, **dados)
        self._sonho_pend[pid] = tipo
        self._sonho_ecra().ocupado = True

    def _sonho_abrir_liga(self, liga_id: int):
        self._sonho_liga = liga_id
        self._sonho_pedir("fantasy_estado", liga=liga_id)

    def _sonho_fechar_texto(self):
        try:
            pygame.key.stop_text_input()
        except pygame.error:
            pass

    def _sonho_eventos(self):
        ecra = self._sonho_ecra()
        for event in pygame.event.get():
            acao = ecra.handle_event(event)
            if acao is None:
                continue
            nome = acao[0] if isinstance(acao, tuple) else acao
            self._som_acao("confirmar" if nome == "pedido" else nome)
            if nome == "sair":
                self.running = False
            elif nome in ("voltar", "menu"):
                self._sonho_fechar_texto()
                self.ir_para_menu_principal()
            elif nome == "conta":
                self.abrir_conta()
            elif nome == "ligas":
                self.abrir_sonho()
            elif nome == "abrir":
                self._sonho_abrir_liga(acao[1])
            elif nome == "criar":
                self._sonho_pedir("fantasy_criar", nome=acao[1])
            elif nome == "entrar":
                self._sonho_pedir("fantasy_entrar", codigo=acao[1])
            elif nome == "atualizar":
                self._sonho_pedir("fantasy_estado")
            elif nome == "pedido":
                self._sonho_pedir(acao[1], **acao[2])
            if self.estado not in ("sonho", "sonho_ligas") or self._sonho_ecra() is not ecra:
                return

    def _sonho_update(self, dt: float):
        ecra = self._sonho_ecra()
        ecra.update(dt)
        srv = self._servidor
        if srv is None or not self._sonho_pend:
            return
        if isinstance(ecra, EcraSonhoLigas):
            ecra.a_acordar = srv.a_acordar()
        if srv.estado == "erro":
            self._sonho_pend.clear()
            ecra.ocupado = False
            msg = srv.erro or "Não foi possível ligar ao servidor."
            if isinstance(ecra, EcraSonhoLigas):
                ecra.aviso_servidor = msg
                if ecra.ligas is None:
                    ecra.ligas = []
            else:
                ecra.mensagem(False, msg)
            return
        for pid, tipo in list(self._sonho_pend.items()):
            r = srv.resposta(pid)
            if r is None:
                # Só se conta o tempo com a ligação feita (o servidor gratuito pode demorar a acordar)
                if srv.estado == "ligado":
                    self._sonho_espera[pid] = self._sonho_espera.get(pid, 0.0) + dt
                if self._sonho_espera.get(pid, 0.0) > SEM_RESPOSTA_S:
                    self._sonho_sem_resposta(ecra)
                    return
                continue
            del self._sonho_pend[pid]
            self._sonho_espera.pop(pid, None)
            self._sonho_resposta(tipo, r)
        if not self._sonho_pend:
            self._sonho_ecra().ocupado = False

    def _sonho_sem_resposta(self, ecra):
        """
        O servidor está ligado mas não respondeu: provavelmente é uma versão antiga, sem a Equipa
        de Sonho (um servidor antigo ignora os pedidos que não conhece). Em vez de ficar à espera
        para sempre, avisa.
        """
        self._sonho_pend.clear()
        self._sonho_espera.clear()
        ecra.ocupado = False
        msg = "O servidor não respondeu. Pode ainda não ter a Equipa de Sonho: tenta mais tarde."
        if isinstance(ecra, EcraSonhoLigas):
            if ecra.ligas is None:
                ecra.ligas, ecra.aviso_servidor = [], msg
            else:
                ecra.erro = msg
        else:
            ecra.mensagem(False, msg)

    def _sonho_resposta(self, tipo: str, r: dict):
        if self.estado == "sonho_ligas":
            ecra = self.ecra_sonho_ligas
            if not r.get("ok"):
                ecra.erro = r.get("erro", "Houve um problema.")
                if ecra.ligas is None:
                    ecra.ligas = []
                return
            if tipo == "fantasy_ligas":
                ecra.ligas, ecra.a_atualizar = r["ligas"], r.get("a_atualizar", False)
            elif tipo in ("fantasy_criar", "fantasy_entrar"):
                self._sonho_abrir_liga(r["liga"]["id"])
            elif tipo == "fantasy_estado":
                self._sonho_fechar_texto()
                self.ecra_sonho = EcraSonhoLiga(self.screen, r["estado"], arena=self.rink._surf)
                self.estado = "sonho"
                som.ui("confirmar")
            return
        ecra = self.ecra_sonho
        if ecra is None:
            return
        if not r.get("ok"):
            ecra.mensagem(False, r.get("erro", "Houve um problema."))
            return
        if tipo == "fantasy_jogador":
            ecra.ficha = r["jogador"]
            return
        if r.get("estado"):
            ecra.receber(r["estado"])
        if r.get("mensagem"):
            ecra.mensagem(True, r["mensagem"])
