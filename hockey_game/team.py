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


def _clube(cid, nome, sigla, cor1, cor2, logo, padrao=None):
    info = {"id": cid, "nome": nome, "sigla": sigla, "cor_primaria": cor1, "cor_secundaria": cor2,
            "ficheiros_logo": [logo]}
    if padrao:
        info["padrao"] = padrao
    return info


# 2.ª divisão e clubes estrangeiros (só jogam a Taça Europeia)
for _info in (
    _clube("hc_turquel", "HC Turquel", "HCT", (25, 25, 28), (255, 255, 255), "turquel.jpg"),
    _clube("paco_arcos", "Paço de Arcos", "PDA", (200, 30, 40), (255, 255, 255), "pacodearcos.jpg"),
    _clube("cd_povoa", "CD Póvoa", "CDP", (20, 60, 150), (255, 255, 255), "povoa.jpg", "riscas"),
    _clube("ch_carvalhos", "CH Carvalhos", "CHC", (20, 30, 120), (255, 255, 255), "carvalhos.png"),
    _clube("aa_espinho", "AA Espinho", "AAE", (30, 30, 35), (255, 255, 255), "espinho.jpg", "riscas"),
    _clube("sc_marinhense", "SC Marinhense", "SCM", (20, 130, 60), (255, 255, 255), "marinhense.jpg"),
    _clube("ha_cambra", "HA Cambra", "HAC", (235, 195, 20), (25, 25, 25), "cambra.jpg"),
    _clube("fc_barcelona", "FC Barcelona", "FCB", (0, 70, 150), (165, 0, 52), "barcelona.png", "riscas"),
    _clube("liceo", "Deportivo Liceo", "LIC", (0, 130, 70), (255, 255, 255), "liceo.jpg"),
    _clube("reus", "Reus Deportiu", "RDE", (200, 25, 35), (20, 20, 20), "reus.jpg", "riscas"),
    _clube("voltrega", "CP Voltregà", "CPV", (30, 70, 170), (255, 255, 255), "voltrega.jpg", "riscas"),
):
    EQUIPAS_INFO[_info["id"]] = _info

# ── Competições ──
EQUIPAS_1_DIVISAO = ["fc_porto", "riba_dave", "sporting", "benfica", "oc_barcelos", "ud_oliveirense",
                     "valongo", "crp_lavra"]
EQUIPAS_2_DIVISAO = ["hc_turquel", "paco_arcos", "cd_povoa", "ch_carvalhos", "aa_espinho", "sc_marinhense",
                     "ha_cambra"]
EQUIPAS_ESTRANGEIRAS = ["fc_barcelona", "liceo", "reus", "voltrega"]      # só jogam a Taça Europeia
EQUIPAS_PORTUGUESAS = EQUIPAS_1_DIVISAO + EQUIPAS_2_DIVISAO               # as que se podem treinar na carreira
# Separadores dos ecrãs de escolha: (nome, equipas)
COMPETICOES = [("1.ª DIVISÃO", EQUIPAS_1_DIVISAO), ("2.ª DIVISÃO", EQUIPAS_2_DIVISAO),
               ("EUROPA", EQUIPAS_ESTRANGEIRAS)]
# Todas as equipas (jogo rápido e jogo online)
EQUIPAS_LISTA = EQUIPAS_PORTUGUESAS + EQUIPAS_ESTRANGEIRAS


def competicao_da_equipa(equipa_id: str) -> int:
    """Índice em COMPETICOES do separador onde a equipa aparece (0 = 1.ª divisão)."""
    for i, (_nome, equipas) in enumerate(COMPETICOES):
        if equipa_id in equipas:
            return i
    return 0

# ── Planteis: guarda-redes + 4 jogadores de campo (como no hóquei em patins real) ──
# Os jogadores de campo estão pela ordem das posições da formação em losango:
#   avançado, médio (em cima), médio (em baixo), defesa.
# Para mudar um nome, basta editar aqui (o modo carreira atualiza a base de dados sozinho).
PLANTEIS = {
    "fc_porto": {
        "guarda_redes": "Xavi Malián",
        "jogadores": ["Hélder Nunes", "Gonçalo Alves", "Carlo di Benedetto", "Ezequiel Mena"],
    },
    "benfica": {
        "guarda_redes": "Pedro Henriques",
        "jogadores": ["Pau Bargalló", "Roberto di Benedetto", "Nil Roca", "Gonçalo Pinto"],
    },
    "sporting": {
        "guarda_redes": "Xano Edo",
        "jogadores": ['Gonzalo "Nolito" Romero', "Alessandro Verona", "Facundo Bridge", "Rafael Bessa"],
    },
    "oc_barcelos": {
        "guarda_redes": "Guillem Torrents",
        "jogadores": ["Luís Querido", "Miguel Rocha", "Carlos Ramos", "Pedro Silva"],
    },
    "ud_oliveirense": {
        "guarda_redes": "Bernardo Mendes",
        "jogadores": ["Bruno di Benedetto", "João Souto", "Joan Galbas", "Diogo Lemos"],
    },
    "valongo": {
        "guarda_redes": "Gonçalo Bento",
        "jogadores": ['Rui Silva "Folhetas"', "João Pedro", "João Maló", "Franco Pósito"],
    },
    "riba_dave": {
        "guarda_redes": "Álvaro Shedha",
        "jogadores": ["Pedro Martins", "Filipe Almeida", "Ivo Silva", "Martim Lopes"],
    },
    "crp_lavra": {
        "guarda_redes": "Santiago Morales",
        "jogadores": ["Rafael Silveira", "Tomás Teixeira", "Tiago Mendes", "Martim Constantino"],
    },
    # ── Clubes estrangeiros (nomes reais, procurados na Internet em novembro de 2026) ──
    # FC Barcelona: site do clube (fcbarcelona.es), com as posições
    "fc_barcelona": {
        "guarda_redes": "Arnau Martínez",
        "jogadores": ["Martí Casas", "Eloi Cervera", "Ignacio Alabart", "Sergi Aragonès"],
    },
    # Liceo: reforços de 2025/26 nas notícias; o defesa não foi encontrado (nome inventado)
    "liceo": {
        "guarda_redes": "Blai Roca",
        "jogadores": ['Fran Torres "Tombita"', "Toni Pérez", "Nuno Paiva", "Marc Julià"],
    },
    # Reus Deportiu: renovações e reforços nas notícias do Diari de Tarragona
    "reus": {
        "guarda_redes": "Cándid Ballart",
        "jogadores": ["Joan Salvat", "Roc Pujadas", "Carles Casas", "Pol Martínez"],
    },
    # Voltregà: nomes do site do clube (2026/27); o site não diz as posições, foram atribuídas
    "voltrega": {
        "guarda_redes": "Ferran Font",
        "jogadores": ["Jordi Burgaya", "Aleix Molas", "Humbert Serra", "Gerard Teixidó"],
    },
    # ── 2.ª divisão: os planteis não estão publicados na Internet, por isso os nomes são inventados ──
    # (basta trocar aqui pelos nomes verdadeiros)
    "hc_turquel": {
        "guarda_redes": "Rui Ferreira",
        "jogadores": ["Diogo Marques", "Tiago Lopes", "André Gaspar", "Hugo Vieira"],
    },
    "paco_arcos": {
        "guarda_redes": "Miguel Antunes",
        "jogadores": ["Ricardo Pinto", "Duarte Simões", "João Farinha", "Nuno Leal"],
    },
    "cd_povoa": {
        "guarda_redes": "Filipe Moreira",
        "jogadores": ["Gonçalo Brito", "Vasco Rebelo", "Daniel Faria", "Pedro Matos"],
    },
    "ch_carvalhos": {
        "guarda_redes": "Luís Barbosa",
        "jogadores": ["Rúben Teixeira", "Henrique Sousa", "Bruno Couto", "Afonso Pires"],
    },
    "aa_espinho": {
        "guarda_redes": "Sérgio Neves",
        "jogadores": ["Tomás Rocha", "Leonardo Dias", "Fábio Ramos", "Jorge Moura"],
    },
    "sc_marinhense": {
        "guarda_redes": "Carlos Vidal",
        "jogadores": ["Martim Carvalho", "Rodrigo Esteves", "Paulo Graça", "Simão Lourenço"],
    },
    "ha_cambra": {
        "guarda_redes": "Manuel Pacheco",
        "jogadores": ["Francisco Valente", "Gustavo Brandão", "Salvador Nogueira", "Ivo Correia"],
    },
}

# Posição e número da camisola de cada lugar da formação (o 1 é sempre do guarda-redes)
POSICOES_FORMACAO = [("avancado", 10), ("medio", 7), ("medio", 8), ("defesa", 4)]


def obter_plantel(equipa_id: str) -> dict:
    """
    Plantel de uma equipa: {"guarda_redes": nome, "jogadores": [(nome, posicao, numero), ...]}.
    Se a equipa não tiver plantel definido, usa nomes genéricos.
    """
    equipa_id = EQUIPAS_ALIASES.get(equipa_id, equipa_id)
    dados = PLANTEIS.get(equipa_id, {})
    nomes = list(dados.get("jogadores", []))
    nomes += [f"Jogador {i + 1}" for i in range(len(nomes), len(POSICOES_FORMACAO))]
    return {
        "guarda_redes": dados.get("guarda_redes", "Guarda-redes"),
        "jogadores": [(nome, pos, num) for nome, (pos, num) in zip(nomes, POSICOES_FORMACAO)],
    }


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
                # O emblema limpo (sem o fundo branco) fica guardado: limpar é lento (píxel a píxel)
                # e assim um tamanho novo só precisa de ser redimensionado
                limpo = _cache_logos.get(("limpo", caminho_encontrado))
                if limpo is None:
                    raw = pygame.image.load(caminho_encontrado)
                    # Se for JPG ou imagem com cantos brancos, remove a moldura branca exterior
                    c0 = raw.get_at((0, 0))
                    c_transparente = (len(c0) >= 4 and c0[3] == 0)
                    if not c_transparente and c0[0] > 235 and c0[1] > 235 and c0[2] > 235:
                        limpo = remover_fundo_branco_exterior(raw)
                    else:
                        limpo = raw.convert_alpha()
                    _cache_logos[("limpo", caminho_encontrado)] = limpo
                img = limpo

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
