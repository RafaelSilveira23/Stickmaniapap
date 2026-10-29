# -*- coding: utf-8 -*-
"""componentes.py - peças reutilizáveis da interface (botões, painéis, fundos, textos).

Todos os menus (principal, seleção de equipas, pausa, fim de jogo) usam estas
funções, para o jogo ter um aspeto coerente em todos os ecrãs.
"""
import math
import os
import pygame

from settings import WIDTH, HEIGHT
from cores import misturar, clarear, escurecer, cor_texto_sobre, recolorir_frames

# Paleta base da interface
COR_FUNDO_TOPO  = (8, 12, 26)
COR_FUNDO_BASE  = (16, 30, 62)
COR_PAINEL      = (14, 22, 44)
COR_BORDA       = (45, 80, 160)
COR_DESTAQUE    = (255, 205, 60)     # dourado
COR_TEXTO       = (240, 245, 255)
COR_TEXTO_SUAVE = (150, 180, 230)

_cache_fontes = {}


def fonte(tamanho: int, negrito: bool = True) -> pygame.font.Font:
    """Fonte Arial com cache (criar fontes a cada frame é lento)."""
    chave = (tamanho, negrito)
    if chave not in _cache_fontes:
        _cache_fontes[chave] = pygame.font.SysFont("Arial", tamanho, bold=negrito)
    return _cache_fontes[chave]


# ====================================================================== #
# Texto                                                                  #
# ====================================================================== #

def texto(surf, txt: str, tamanho: int, cor, pos, ancora: str = "center",
          negrito: bool = True, sombra: bool = False) -> pygame.Rect:
    """Escreve texto. 'ancora' pode ser center, midleft, midright, topleft, midtop..."""
    f = fonte(tamanho, negrito)
    img = f.render(txt, True, cor)
    r = img.get_rect(**{ancora: (int(pos[0]), int(pos[1]))})
    if sombra:
        sombra_img = f.render(txt, True, (0, 0, 0))
        surf.blit(sombra_img, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


# ====================================================================== #
# Formas                                                                 #
# ====================================================================== #

def gradiente_vertical(surf, rect, cor_topo, cor_base, raio: int = 0):
    """Preenche um retângulo com um gradiente vertical (com cantos arredondados opcionais)."""
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0:
        return
    camada = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        pygame.draw.line(camada, misturar(cor_topo, cor_base, t), (0, y), (rect.width, y))
    if raio > 0:
        mascara = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, *rect.size), border_radius=raio)
        camada.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(camada, rect.topleft)


def painel(surf, rect, cor=COR_PAINEL, borda=COR_BORDA, raio: int = 12,
           alpha: int = 255, largura_borda: int = 2):
    """Painel (caixa) com fundo, borda e uma pequena sombra."""
    rect = pygame.Rect(rect)
    sombra = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
    pygame.draw.rect(sombra, (0, 0, 0, 90), (4, 6, rect.width, rect.height), border_radius=raio)
    surf.blit(sombra, (rect.x - 4, rect.y - 4))
    if alpha < 255:
        camada = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(camada, (*cor, alpha), (0, 0, *rect.size), border_radius=raio)
        surf.blit(camada, rect.topleft)
    else:
        pygame.draw.rect(surf, cor, rect, border_radius=raio)
    if largura_borda:
        pygame.draw.rect(surf, borda, rect, largura_borda, border_radius=raio)


def escurecer_ecra(surf, alpha: int = 150):
    """Camada escura por cima de tudo (usada na pausa e no fim de jogo)."""
    camada = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    camada.fill((4, 8, 18, alpha))
    surf.blit(camada, (0, 0))


# ====================================================================== #
# Fundo animado dos menus                                                #
# ====================================================================== #

_fundo_cache = None


def _construir_fundo() -> pygame.Surface:
    fundo = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        pygame.draw.line(fundo, misturar(COR_FUNDO_TOPO, COR_FUNDO_BASE, t), (0, y), (WIDTH, y))

    # Desenho subtil de um ringue de hóquei no fundo
    linhas = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cor = (70, 120, 220, 38)
    ringue = pygame.Rect(90, 130, WIDTH - 180, HEIGHT - 200)
    pygame.draw.rect(linhas, cor, ringue, 3, border_radius=70)
    pygame.draw.line(linhas, cor, (ringue.centerx, ringue.top), (ringue.centerx, ringue.bottom), 3)
    pygame.draw.circle(linhas, cor, ringue.center, 95, 3)
    area_w, area_h = 170, 290
    pygame.draw.rect(linhas, cor, (ringue.left + 120, ringue.centery - area_h // 2, area_w, area_h), 3)
    pygame.draw.rect(linhas, cor, (ringue.right - 120 - area_w, ringue.centery - area_h // 2, area_w, area_h), 3)
    fundo.blit(linhas, (0, 0))
    return fundo


def fundo_menu(surf, t: float, cor_esq=None, cor_dir=None):
    """
    Fundo animado comum a todos os menus.
    cor_esq / cor_dir: cores das equipas para um brilho suave nos lados.
    """
    global _fundo_cache
    if _fundo_cache is None:
        _fundo_cache = _construir_fundo()
    surf.blit(_fundo_cache, (0, 0))

    # Brilho com as cores das equipas
    brilho = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pulso = 0.5 + 0.5 * math.sin(t * 1.6)
    for cor, x in ((cor_esq, 0), (cor_dir, WIDTH)):
        if cor is None:
            continue
        for i in range(6):
            raio = 420 - i * 60
            a = int((10 + 6 * pulso) * (i + 1) / 6)
            pygame.draw.circle(brilho, (*cor[:3], a), (x, HEIGHT // 2), raio)
    surf.blit(brilho, (0, 0))

    # Faixas de luz diagonais que atravessam o ecrã devagar
    faixas = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(3):
        x = int(((t * 60 + i * 520) % (WIDTH + 600)) - 300)
        pts = [(x, 0), (x + 90, 0), (x - 210, HEIGHT), (x - 300, HEIGHT)]
        pygame.draw.polygon(faixas, (120, 170, 255, 10), pts)
    surf.blit(faixas, (0, 0))


# ====================================================================== #
# Botão                                                                  #
# ====================================================================== #

class Botao:
    """Botão com efeito de hover / foco do teclado e cor de destaque."""

    def __init__(self, rect, texto_btn: str, acao: str, cor=(50, 140, 255),
                 tamanho_texto: int = 20, icone: str = ""):
        self.rect = pygame.Rect(rect)
        self.texto = texto_btn
        self.acao = acao
        self.cor = cor
        self.tamanho_texto = tamanho_texto
        self.icone = icone
        self.ativo = False   # usado em grupos de opções (ex.: dificuldade)

    def por_cima(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surf, mpos, focado: bool = False):
        destacado = focado or self.por_cima(mpos)
        r = self.rect
        if self.ativo:
            topo, base, borda, cor_txt = clarear(self.cor, 0.15), self.cor, (255, 255, 255), cor_texto_sobre(self.cor)
        elif destacado:
            topo, base = misturar(self.cor, (30, 48, 90), 0.35), misturar(self.cor, (16, 26, 50), 0.55)
            borda, cor_txt = clarear(self.cor, 0.3), (255, 255, 255)
        else:
            topo, base, borda, cor_txt = (24, 38, 74), (14, 22, 44), misturar(self.cor, (30, 50, 100), 0.6), (200, 215, 245)

        # Sombra
        sombra = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 100), (0, 0, r.width, r.height), border_radius=10)
        surf.blit(sombra, (r.x + 2, r.y + 4))

        gradiente_vertical(surf, r, topo, base, raio=10)
        pygame.draw.rect(surf, borda, r, 2, border_radius=10)

        # Barra de destaque à esquerda quando o botão está selecionado
        if destacado and not self.ativo:
            pygame.draw.rect(surf, self.cor, (r.x + 8, r.y + 10, 4, r.height - 20), border_radius=2)

        rotulo = f"{self.icone}  {self.texto}" if self.icone else self.texto
        texto(surf, rotulo, self.tamanho_texto, cor_txt, r.center)


class ListaBotoes:
    """Grupo vertical de botões com navegação por teclado (↑ ↓ ENTER) e rato."""

    def __init__(self, botoes: list):
        self.botoes = botoes
        self.foco = 0
        self._ultimo_mouse = None

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.foco = (self.foco - 1) % len(self.botoes)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.foco = (self.foco + 1) % len(self.botoes)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.botoes[self.foco].acao
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, b in enumerate(self.botoes):
                if b.por_cima(event.pos):
                    self.foco = i
                    return b.acao
        return None

    def draw(self, surf):
        mpos = pygame.mouse.get_pos()
        # O rato passa a mandar no foco quando se mexe por cima de um botão
        if mpos != self._ultimo_mouse:
            self._ultimo_mouse = mpos
            for i, b in enumerate(self.botoes):
                if b.por_cima(mpos):
                    self.foco = i
        for i, b in enumerate(self.botoes):
            b.draw(surf, (-1, -1), focado=(i == self.foco))


# ====================================================================== #
# Pré-visualização do equipamento                                        #
# ====================================================================== #

_PASTA_AZUL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "sprites_v2", "hd", "frames", "azul")
_cache_preview = {}


_cache_ampliado = {}


def sprite_equipamento(kit: dict, tamanho: int, t: float = 0.0, virar: bool = False) -> pygame.Surface:
    """
    Jogador parado com o equipamento da equipa (animado com 3 frames).
    Para ser rápido, a recoloração é feita numa imagem pequena (metade do tamanho)
    e só depois ampliada - o estilo pixel-art mantém-se nítido.
    """
    base = max(48, tamanho // 2)
    chave = (base, virar)
    if chave not in _cache_preview:
        frames = []
        for i in (1, 2, 3):
            img = pygame.image.load(os.path.join(_PASTA_AZUL, f"parado_{i:02d}.png")).convert_alpha()
            img = pygame.transform.scale(img, (base, base))
            if virar:
                img = pygame.transform.flip(img, True, False)
            frames.append(img)
        _cache_preview[chave] = frames
    pequenos = recolorir_frames(("preview", base, virar), _cache_preview[chave], kit)
    idx = int(t * 2.5) % len(pequenos)
    chave_amp = (id(pequenos[idx]), tamanho)
    if chave_amp not in _cache_ampliado:
        _cache_ampliado[chave_amp] = pygame.transform.scale(pequenos[idx], (tamanho, tamanho))
    return _cache_ampliado[chave_amp]


def amostra_cor(surf, cor, rect):
    """Quadradinho com uma cor (amostra das cores do clube)."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, cor, rect, border_radius=4)
    pygame.draw.rect(surf, (255, 255, 255), rect, 1, border_radius=4)


def faixa_equipa(surf, rect, cor, raio: int = 12, so_topo: bool = True):
    """Cabeçalho com gradiente na cor da equipa."""
    rect = pygame.Rect(rect)
    camada = pygame.Surface(rect.size, pygame.SRCALPHA)
    gradiente_vertical(camada, (0, 0, *rect.size), clarear(cor, 0.12), escurecer(cor, 0.25))
    mascara = pygame.Surface(rect.size, pygame.SRCALPHA)
    if so_topo:
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, *rect.size),
                         border_top_left_radius=raio, border_top_right_radius=raio)
    else:
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, *rect.size), border_radius=raio)
    camada.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(camada, rect.topleft)
