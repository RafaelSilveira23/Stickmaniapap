# -*- coding: utf-8 -*-
"""fontes.py - fontes do sistema com cache.

Criar uma fonte com pygame.font.SysFont demora cerca de 0,25 ms (procura o ficheiro da fonte).
Algumas partes do jogo criavam a mesma fonte em todos os frames; com esta função cada fonte
é criada uma só vez e depois reaproveitada.
"""
import pygame
import pygame.font     # no browser (pygbag) o submódulo tem de ser importado à parte

_cache = {}


def SysFont(nome: str, tamanho: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Igual a pygame.font.SysFont, mas guarda a fonte para a próxima vez."""
    chave = (nome, tamanho, bool(bold), bool(italic))
    f = _cache.get(chave)
    if f is None:
        f = _cache[chave] = pygame.font.SysFont(nome, tamanho, bold=bold, italic=italic)
    return f
