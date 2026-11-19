# -*- coding: utf-8 -*-
"""cores.py - cores dos equipamentos, contraste e recoloração dos sprites.

Ideia principal:
  Os sprites originais da equipa "azul" têm a camisola e os calções em tons de azul.
  Para cada equipa, trocamos esses tons de azul pela cor principal da equipa,
  mantendo o sombreado (zonas escuras continuam escuras, zonas claras continuam claras).
  As riscas brancas da camisola passam a ter a cor secundária (ou a principal,
  se o equipamento da equipa for liso).

  Se as duas equipas tiverem cores parecidas (ex.: Benfica vs Oliveirense),
  a equipa visitante joga com o equipamento alternativo.
"""
import colorsys
import pygame

from team import obter_info_equipa

# Brilho de referência dos tons de azul da camisola original (0..1).
# Pixels com este brilho ficam exatamente com a cor da equipa.
_BRILHO_REF_KIT = 0.70
_BRILHO_REF_RISCAS = 0.90

# Intervalo de matiz (hue) dos azuis da camisola original (0..1 -> 0..360 graus)
_HUE_MIN = 180 / 360
_HUE_MAX = 260 / 360

# Distância mínima entre cores para não haver confusão entre equipas
_DIST_MIN_EQUIPAS = 150


# ====================================================================== #
# Utilitários de cor                                                     #
# ====================================================================== #

def luminancia(cor) -> float:
    """Brilho percebido de uma cor (0 = preto, 255 = branco)."""
    r, g, b = cor[0], cor[1], cor[2]
    return 0.299 * r + 0.587 * g + 0.114 * b


def distancia_cores(c1, c2) -> float:
    """Distância entre duas cores, aproximada à perceção humana ('redmean')."""
    rm = (c1[0] + c2[0]) / 2
    dr, dg, db = c1[0] - c2[0], c1[1] - c2[1], c1[2] - c2[2]
    return ((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db) ** 0.5


def misturar(c1, c2, t: float) -> tuple:
    """Mistura c1 com c2 (t=0 -> c1, t=1 -> c2)."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def clarear(cor, t: float) -> tuple:
    return misturar(cor, (255, 255, 255), t)


def escurecer(cor, t: float) -> tuple:
    return misturar(cor, (0, 0, 0), t)


def cor_texto_sobre(fundo) -> tuple:
    """Devolve texto preto ou branco, consoante o que se lê melhor sobre o fundo."""
    return (20, 24, 32) if luminancia(fundo) > 150 else (255, 255, 255)


def cor_visivel_em_escuro(cor, minimo: float = 90) -> tuple:
    """Clareia cores muito escuras para se verem sobre fundos escuros (mini-mapa, menus)."""
    cor = tuple(cor[:3])
    passo = 0
    while luminancia(cor) < minimo and passo < 10:
        cor = clarear(cor, 0.18)
        passo += 1
    return cor


def cor_linhas_campo(cor, lum_piso: float = 175, contraste_min: float = 70) -> tuple:
    """
    Ajusta a cor da equipa para ser usada nas linhas do piso de madeira.
    Cores demasiado parecidas com a madeira (ex.: amarelo) são escurecidas
    até terem contraste suficiente, mantendo a tonalidade da equipa.
    """
    cor = tuple(cor[:3])
    passo = 0
    while abs(luminancia(cor) - lum_piso) < contraste_min and passo < 12:
        cor = escurecer(cor, 0.12)
        passo += 1
    return cor


# ====================================================================== #
# Equipamentos                                                           #
# ====================================================================== #

def kit_principal(equipa_id: str) -> dict:
    info = obter_info_equipa(equipa_id)
    return {
        "principal":   tuple(info.get("cor_primaria", (30, 80, 180))),
        "secundaria":  tuple(info.get("cor_secundaria", (255, 255, 255))),
        "padrao":      info.get("padrao", "liso"),
        "alternativo": False,
    }


def kit_alternativo(equipa_id: str) -> dict:
    """Equipamento alternativo: as cores principal e secundária trocam de lugar."""
    k = kit_principal(equipa_id)
    return {
        "principal":   k["secundaria"],
        "secundaria":  k["principal"],
        "padrao":      k["padrao"],
        "alternativo": True,
    }


def definir_equipamentos(casa_id: str, fora_id: str) -> tuple[dict, dict]:
    """
    Escolhe os equipamentos da partida.
    A equipa da casa joga sempre com o principal; a visitante usa o alternativo
    se as cores principais forem parecidas.
    """
    kit_casa = kit_principal(casa_id)
    kit_fora = kit_principal(fora_id)

    if distancia_cores(kit_casa["principal"], kit_fora["principal"]) < _DIST_MIN_EQUIPAS:
        alt = kit_alternativo(fora_id)
        if distancia_cores(kit_casa["principal"], alt["principal"]) >= _DIST_MIN_EQUIPAS:
            kit_fora = alt
        else:
            # Último recurso: equipamento neutro (branco ou escuro) com a cor principal nos detalhes
            neutra = (245, 245, 245) if luminancia(kit_casa["principal"]) < 140 else (30, 32, 40)
            kit_fora = {
                "principal":   neutra,
                "secundaria":  kit_fora["principal"],
                "padrao":      "liso",
                "alternativo": True,
            }
    return kit_casa, kit_fora


def chave_kit(kit: dict) -> tuple:
    """Chave única de um equipamento (usada nas caches de imagens)."""
    return (tuple(kit["principal"]), tuple(kit["secundaria"]), kit.get("padrao", "liso"))


# ====================================================================== #
# Recoloração de sprites                                                 #
# ====================================================================== #

def _tom(cor, fator: float) -> tuple:
    """Aplica sombreado (fator < 1) ou brilho (fator > 1) a uma cor."""
    # Cores muito escuras (preto) não mostrariam sombreado: damos-lhes um pouco de luz
    if luminancia(cor) < 60:
        cor = misturar(cor, (70, 70, 78), 0.4)
    if fator <= 1.0:
        return tuple(int(c * fator) for c in cor)
    return clarear(cor, min(1.0, (fator - 1.0) * 0.8))


def recolorir_superficie(surf: pygame.Surface, kit: dict) -> pygame.Surface:
    """Devolve uma cópia do sprite com o equipamento pintado nas cores do kit."""
    principal = kit["principal"]
    if kit.get("padrao", "liso") == "riscas":
        riscas = kit["secundaria"]
    else:
        riscas = clarear(principal, 0.12)

    out = surf.copy()
    w, h = out.get_size()
    e_kit = [[False] * h for _ in range(w)]

    out.lock()
    # 1.ª passagem: tons de azul -> cor principal
    for x in range(w):
        for y in range(h):
            r, g, b, a = out.get_at((x, y))
            if a == 0:
                continue
            hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if _HUE_MIN <= hue <= _HUE_MAX and sat >= 0.25:
                e_kit[x][y] = True
                out.set_at((x, y), (*_tom(principal, val / _BRILHO_REF_KIT), a))

    # 2.ª passagem: brancos rodeados de camisola (as riscas) -> cor das riscas
    for x in range(w):
        for y in range(h):
            if e_kit[x][y]:
                continue
            r, g, b, a = surf.get_at((x, y))
            if a == 0:
                continue
            hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if sat < 0.2 and val > 0.6:
                vizinhos = 0
                for i in range(max(0, x - 1), min(w, x + 2)):
                    for j in range(max(0, y - 1), min(h, y + 2)):
                        if e_kit[i][j]:
                            vizinhos += 1
                if vizinhos >= 2:
                    out.set_at((x, y), (*_tom(riscas, val / _BRILHO_REF_RISCAS), a))
    out.unlock()
    return out


_cache_frames = {}


def recolorir_frames(chave_origem, frames: list, kit: dict) -> list:
    """Recolore uma lista de frames, guardando o resultado em cache."""
    chave = (chave_origem, chave_kit(kit))
    if chave not in _cache_frames:
        _cache_frames[chave] = [recolorir_superficie(f, kit) for f in frames]
    return _cache_frames[chave]


# ====================================================================== #
# Stick mais escuro (madeira castanha, como na imagem de referência)     #
# ====================================================================== #

_cache_stick = {}


def escurecer_stick(chave, frames: list, sat_min: float = 0.2) -> list:
    """
    Escurece a madeira do stick nos sprites.
    A pele e o stick têm cores parecidas; separamo-los assim:
      - o stick é mais amarelado (matiz >= 29°) e a pele mais avermelhada;
      - só mexemos abaixo da cabeça (a partir de 40% da altura do sprite).
    """
    if chave in _cache_stick:
        return _cache_stick[chave]
    novos = []
    for f in frames:
        out = f.copy()
        w, h = out.get_size()
        out.lock()
        for y in range(int(h * 0.40), h):
            for x in range(w):
                r, g, b, a = out.get_at((x, y))
                if a == 0:
                    continue
                hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if 29 / 360 <= hue <= 50 / 360 and sat > sat_min and val > 0.35:
                    out.set_at((x, y), (int(r * 0.74), int(g * 0.60), int(b * 0.50), a))
        out.unlock()
        novos.append(out)
    _cache_stick[chave] = novos
    return novos
