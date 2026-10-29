# -*- coding: utf-8 -*-
"""team.py - gestão de equipas, emblemas e configurações de jogo (PAP)."""
import os
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_SIMBOLOS = os.path.join(BASE_DIR, "simbolos")
PASTA_TEAMS = os.path.join(BASE_DIR, "assets", "teams")

EQUIPAS_INFO = {
    "fc_porto": {
        "id": "fc_porto",
        "nome": "FC Porto",
        "sigla": "FCP",
        "cor_primaria": (15, 60, 160),
        "cor_secundaria": (255, 255, 255),
        "padrao": "riscas",   # "riscas" = camisola às riscas; "liso" = uma só cor
        "ficheiros_logo": ["Porto.jpg", "porto.png", "fc_porto.png", "fcp.png"],
    },
    "riba_dave": {
        "id": "riba_dave",
        "nome": "Riba d'Ave",
        "sigla": "RDA",
        "cor_primaria": (135, 20, 25),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["ribadave.png", "riba_dave.png", "riba_de_ave.png", "rda.png"],
    },
    "sporting": {
        "id": "sporting",
        "nome": "Sporting CP",
        "sigla": "SCP",
        "cor_primaria": (0, 120, 60),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["Sporting.png", "sporting.png", "sporting_cp.png", "scp.png"],
    },
    "benfica": {
        "id": "benfica",
        "nome": "SL Benfica",
        "sigla": "SLB",
        "cor_primaria": (200, 25, 30),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["Benfica.png", "benfica.png", "sl_benfica.png", "slb.png"],
    },
    "oc_barcelos": {
        "id": "oc_barcelos",
        "nome": "Óquei Barcelos",
        "sigla": "OCB",
        "cor_primaria": (220, 180, 20),
        "cor_secundaria": (20, 50, 140),
        "ficheiros_logo": ["Barcelos.png", "barcelos.png", "oc_barcelos.png", "ocb.png"],
    },
    "ud_oliveirense": {
        "id": "ud_oliveirense",
        "nome": "Oliveirense",
        "sigla": "UDO",
        "cor_primaria": (180, 30, 40),
        "cor_secundaria": (20, 50, 140),
        "ficheiros_logo": ["Oliveirense.png", "oliveirense.png", "ud_oliveirense.png", "udo.png"],
    },
    "valongo": {
        "id": "valongo",
        "nome": "AD Valongo",
        "sigla": "ADV",
        "cor_primaria": (30, 80, 180),
        "cor_secundaria": (255, 255, 255),
        "ficheiros_logo": ["Valongo.jpg", "valongo.png", "ad_valongo.png", "adv.png"],
    },
    "crp_lavra": {
        "id": "crp_lavra",
        "nome": "CRP Lavra",
        "sigla": "CPL",
        "cor_primaria": (25, 25, 30),
        "cor_secundaria": (220, 180, 30),
        "ficheiros_logo": ["crpflavra.webp", "crpflavra.png", "crp_lavra.png", "lavra.png"],
    },
}

EQUIPAS_LISTA = [
    "fc_porto",
    "riba_dave",
    "sporting",
    "benfica",
    "oc_barcelos",
    "ud_oliveirense",
    "valongo",
    "crp_lavra",
]

EQUIPAS_ALIASES = {
    "porto": "fc_porto",
    "fcp": "fc_porto",
    "fcporto": "fc_porto",
    "ribadave": "riba_dave",
    "rda": "riba_dave",
    "sporting_cp": "sporting",
    "scp": "sporting",
    "sl_benfica": "benfica",
    "slb": "benfica",
    "barcelos": "oc_barcelos",
    "ocb": "oc_barcelos",
    "oliveirense": "ud_oliveirense",
    "udo": "ud_oliveirense",
    "ad_valongo": "valongo",
    "adv": "valongo",
    "crpflavra": "crp_lavra",
    "crp_lavra": "crp_lavra",
    "lavra": "crp_lavra",
    "cpl": "crp_lavra",
}

_cache_logos = {}


def remover_fundo_branco_exterior(img: pygame.Surface) -> pygame.Surface:
    """
    Remove o fundo branco exterior dos cantos/bordas via flood-fill,
    mantendo intactos os detalhes brancos no interior do emblema/escudo.
    """
    img = img.convert_alpha()
    w, h = img.get_size()
    visited = bytearray(w * h)
    queue = []

    # Verificar pixels das bordas exteriores
    for x in range(w):
        for y in (0, h - 1):
            c = img.get_at((x, y))
            if c.r > 235 and c.g > 235 and c.b > 235:
                queue.append((x, y))
                visited[y * w + x] = 1

    for y in range(h):
        for x in (0, w - 1):
            if not visited[y * w + x]:
                c = img.get_at((x, y))
                if c.r > 235 and c.g > 235 and c.b > 235:
                    queue.append((x, y))
                    visited[y * w + x] = 1

    head = 0
    while head < len(queue):
        cx, cy = queue[head]
        head += 1
        img.set_at((cx, cy), (0, 0, 0, 0))

        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx]:
                    visited[idx] = 1
                    c = img.get_at((nx, ny))
                    if c.r > 230 and c.g > 230 and c.b > 230:
                        queue.append((nx, ny))

    return img


def carregar_logo_equipa(equipa_id: str, tamanho: tuple[int, int]) -> pygame.Surface | None:
    """
    Carrega o logótipo/emblema da equipa a partir de simbolos/ ou assets/teams/.
    Aplica remoção inteligente de fundo branco quando aplicável e preserva
    o aspect ratio original no redimensionamento.
    """
    equipa_id = EQUIPAS_ALIASES.get(equipa_id.lower(), equipa_id)
    chave = (equipa_id, tamanho)
    if chave in _cache_logos:
        return _cache_logos[chave]

    info = EQUIPAS_INFO.get(equipa_id, {})
    nomes = list(info.get("ficheiros_logo", [])) + [f"{equipa_id}.png", f"{equipa_id}.jpg", f"{equipa_id}.webp"]

    pastas = [PASTA_SIMBOLOS, PASTA_TEAMS]

    for pasta in pastas:
        if not os.path.exists(pasta):
            continue

        ficheiros_pasta = os.listdir(pasta)
        ficheiros_lower = {f.lower(): f for f in ficheiros_pasta}

        caminho_encontrado = None
        for n in nomes:
            n_lower = n.lower()
            if n_lower in ficheiros_lower:
                caminho_encontrado = os.path.join(pasta, ficheiros_lower[n_lower])
                break

        # Fallback se não bater nos nomes esperados: procura qualquer ficheiro com o nome da equipa
        if not caminho_encontrado:
            id_limpo = equipa_id.replace("fc_", "").replace("oc_", "").replace("ud_", "").replace("ad_", "")
            for f_low, f_real in ficheiros_lower.items():
                if id_limpo in f_low:
                    caminho_encontrado = os.path.join(pasta, f_real)
                    break

        if caminho_encontrado:
            try:
                raw = pygame.image.load(caminho_encontrado)
                # Se for JPG ou imagem com cantos brancos, remove a moldura branca exterior
                c0 = raw.get_at((0, 0))
                c_transparente = (len(c0) >= 4 and c0[3] == 0)

                if not c_transparente and c0[0] > 235 and c0[1] > 235 and c0[2] > 235:
                    img = remover_fundo_branco_exterior(raw)
                else:
                    img = raw.convert_alpha()

                # Redimensionar preservando o aspecto visual (aspect-ratio)
                orig_w, orig_h = img.get_size()
                if orig_w > 0 and orig_h > 0:
                    scale = min(tamanho[0] / orig_w, tamanho[1] / orig_h)
                    tw = max(1, int(orig_w * scale))
                    th = max(1, int(orig_h * scale))
                    img = pygame.transform.smoothscale(img, (tw, th))
                    _cache_logos[chave] = img
                    return img
            except Exception as e:
                print(f"Erro ao carregar emblema {caminho_encontrado}: {e}")

    return None


def obter_info_equipa(equipa_id: str) -> dict:
    equipa_id = EQUIPAS_ALIASES.get(equipa_id.lower(), equipa_id)
    return EQUIPAS_INFO.get(equipa_id, {
        "id": equipa_id,
        "nome": equipa_id.replace("_", " ").title(),
        "sigla": equipa_id[:3].upper(),
        "cor_primaria": (30, 80, 180),
        "cor_secundaria": (255, 255, 255),
    })
