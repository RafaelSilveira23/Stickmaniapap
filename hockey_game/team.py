# -*- coding: utf-8 -*-
"""team.py - gestão de equipas, emblemas e configurações de jogo (PAP)."""
import os
import pygame

PASTA_TEAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "teams")

EQUIPAS_INFO = {
    "fc_porto": {
        "id": "fc_porto",
        "nome": "FC Porto",
        "sigla": "FCP",
        "cor_primaria": (15, 60, 160),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["fc_porto.png", "porto.png", "fcp.png"],
    },
    "riba_dave": {
        "id": "riba_dave",
        "nome": "Riba d'Ave",
        "sigla": "RDA",
        "cor_primaria": (135, 20, 25),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["riba_dave.png", "riba_de_ave.png", "rda.png"],
    },
    "sporting": {
        "id": "sporting",
        "nome": "Sporting CP",
        "sigla": "SCP",
        "cor_primaria": (0, 120, 60),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["sporting.png", "sporting_cp.png", "scp.png"],
    },
    "benfica": {
        "id": "benfica",
        "nome": "SL Benfica",
        "sigla": "SLB",
        "cor_primaria": (200, 25, 30),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["benfica.png", "sl_benfica.png", "slb.png"],
    },
    "oc_barcelos": {
        "id": "oc_barcelos",
        "nome": "Óquei Barcelos",
        "sigla": "OCB",
        "cor_primaria": (220, 180, 20),
        "cor_secundaria": (20, 50, 140),
        "ficheiros_logo": ["barcelos.png", "oc_barcelos.png", "ocb.png"],
    },
    "ud_oliveirense": {
        "id": "ud_oliveirense",
        "nome": "Oliveirense",
        "sigla": "UDO",
        "cor_primaria": (180, 30, 40),
        "cor_secundaria": (20, 50, 140),
        "ficheiros_logo": ["oliveirense.png", "ud_oliveirense.png", "udo.png"],
    },
    "valongo": {
        "id": "valongo",
        "nome": "AD Valongo",
        "sigla": "ADV",
        "cor_primaria": (30, 80, 180),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["valongo.png", "ad_valongo.png", "adv.png"],
    },
}

_cache_logos = {}


def carregar_logo_equipa(equipa_id: str, tamanho: tuple[int, int]) -> pygame.Surface | None:
    """
    Carrega o logótipo/emblema da equipa a partir de assets/teams/.
    Suporta PNGs com transparência e faz cache em memória.
    """
    chave = (equipa_id, tamanho)
    if chave in _cache_logos:
        return _cache_logos[chave]

    info = EQUIPAS_INFO.get(equipa_id, {})
    nomes = info.get("ficheiros_logo", [f"{equipa_id}.png"])

    # Garantir que a pasta existe
    if os.path.exists(PASTA_TEAMS):
        # Tenta corresponder ficheiros sem case-sensitivity
        ficheiros_pasta = os.listdir(PASTA_TEAMS)
        ficheiros_lower = {f.lower(): f for f in ficheiros_pasta}

        for n in nomes:
            n_lower = n.lower()
            if n_lower in ficheiros_lower:
                caminho = os.path.join(PASTA_TEAMS, ficheiros_lower[n_lower])
                try:
                    img = pygame.image.load(caminho).convert_alpha()
                    img = pygame.transform.smoothscale(img, tamanho)
                    _cache_logos[chave] = img
                    return img
                except Exception:
                    pass

    return None


def obter_info_equipa(equipa_id: str) -> dict:
    return EQUIPAS_INFO.get(equipa_id, {
        "id": equipa_id,
        "nome": equipa_id.replace("_", " ").title(),
        "sigla": equipa_id[:3].upper(),
        "cor_primaria": (30, 80, 180),
        "cor_secundaria": (255, 255, 255),
    })
