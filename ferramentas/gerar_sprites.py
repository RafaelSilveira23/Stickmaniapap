# -*- coding: utf-8 -*-
"""gerar_sprites.py - gera as spritesheets do StickMania a partir de um "esqueleto".

Como funciona (resumo para o relatório da PAP):
  1. Cada frame é uma POSE: posição da anca, inclinação do tronco, posição dos patins
     e posição do stick.
  2. Os joelhos e os cotovelos são calculados com cinemática inversa (IK) de 2 ossos:
     sabendo onde está a anca e onde está o patim, a lei dos cossenos dá o joelho.
  3. O corpo é desenhado com formas simples (cápsulas e círculos) com contorno escuro,
     4 vezes maior do que o tamanho final, e depois reduzido com smoothscale
     (anti-aliasing = bordas suaves).
  4. As animações são funções: por exemplo, a patinagem é um ciclo em que cada perna
     empurra para trás e volta à frente no ar, com as pernas desfasadas meio ciclo.

O equipamento é desenhado em AZUL com riscas brancas: o jogo depois troca o azul pela
cor de cada equipa (ver hockey_game/cores.py).

Executar:  python ferramentas/gerar_sprites.py
Resultado: sprites_v3/ (spritesheets .png + .json, frames soltos e pré-visualização)
"""
import json
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

# ====================================================================== #
# Configuração                                                           #
# ====================================================================== #
S       = 4        # super-amostragem (desenhar 4x maior e reduzir)
CEL     = 96       # tamanho final de cada célula (px)
CHAO    = 90       # y do chão dentro da célula (base das rodas)
CONT    = 0.85     # espessura do contorno (px finais)
MARGEM  = 30       # desenhamos numa tela maior (para as quedas não ficarem cortadas)

COR_CONTORNO = (24, 18, 28)

PALETA_JOGADOR = {
    "kit":       (40, 86, 178),    # camisola (azul -> cor da equipa)
    "riscas":    (238, 242, 250),  # riscas brancas -> cor secundária
    "calcoes":   (30, 62, 140),
    "meia":      (36, 72, 160),
    "pele":      (238, 188, 148),
    "pele_esc":  (206, 150, 112),
    "cabelo":    (58, 38, 26),
    "luva":      (92, 62, 40),
    "joelheira": (112, 116, 124),
    "bota":      (36, 36, 42),
    "roda":      (64, 64, 72),
    "cubo":      (196, 198, 204),
    "travao":    (214, 196, 150),
    "stick":     (214, 168, 102),
    "fita":      (28, 28, 34),
}

PALETA_GR = dict(PALETA_JOGADOR)
PALETA_GR.update({
    "caneleira": (196, 132, 60),   # caneleiras de couro (castanho/caramelo)
    "caneleira_esc": (150, 96, 40),
    "capacete":  (52, 54, 62),
    "grelha":    (200, 204, 212),
    "luva":      (196, 132, 60),
})

# Comprimentos dos "ossos" (px finais)
COXA, CANELA = 15.0, 15.0
BRACO, ANTEBRACO = 10.5, 10.5
TRONCO = 19.0
OMBRO = 15.5
STICK = 34.0
PE_ALT = 9.6       # do tornozelo à base da roda


# ====================================================================== #
# Geometria                                                              #
# ====================================================================== #

def v_add(a, b): return (a[0] + b[0], a[1] + b[1])
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1])
def v_mul(a, k): return (a[0] * k, a[1] * k)
def v_len(a):    return math.hypot(a[0], a[1])


def v_norm(a):
    n = v_len(a) or 1.0
    return (a[0] / n, a[1] / n)


def v_rot(a, graus):
    """Roda um vetor (graus positivos = sentido dos ponteiros do relógio no ecrã)."""
    r = math.radians(graus)
    c, s = math.cos(r), math.sin(r)
    return (a[0] * c - a[1] * s, a[0] * s + a[1] * c)


def ik(raiz, alvo, l1, l2, preferir):
    """
    Cinemática inversa de 2 ossos (ex.: anca -> joelho -> tornozelo).
    Devolve (articulação_do_meio, ponta). 'preferir' escolhe para onde dobra:
    'frente' (x maior), 'tras' (x menor) ou 'baixo' (y maior).
    """
    d = v_sub(alvo, raiz)
    dist = v_len(d)
    dist_ok = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, dist))
    base = math.atan2(d[1], d[0])
    cos_a = (l1 * l1 + dist_ok * dist_ok - l2 * l2) / (2 * l1 * dist_ok)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    opcoes = []
    for sinal in (1, -1):
        ang = base + sinal * a
        opcoes.append((raiz[0] + l1 * math.cos(ang), raiz[1] + l1 * math.sin(ang)))
    if preferir == "frente":
        meio = max(opcoes, key=lambda p: p[0])
    elif preferir == "tras":
        meio = min(opcoes, key=lambda p: p[0])
    else:
        meio = max(opcoes, key=lambda p: p[1])
    ponta = v_add(raiz, v_mul(v_norm(d), dist_ok))
    # recalcular a ponta a partir do meio (mantém o 2.º osso com o comprimento certo)
    ponta = v_add(meio, v_mul(v_norm(v_sub(ponta, meio)), l2))
    return meio, ponta


# ====================================================================== #
# Primitivas de desenho (tudo em px finais; multiplicamos por S aqui)    #
# ====================================================================== #

def P(p):
    return ((p[0] + MARGEM) * S, (p[1] + MARGEM) * S)


def capsula(surf, a, b, r, cor):
    """Segmento grosso com pontas redondas."""
    a, b = P(a), P(b)
    r *= S
    d = v_sub(b, a)
    if v_len(d) > 0.01:
        n = v_norm((-d[1], d[0]))
        pts = [v_add(a, v_mul(n, r)), v_add(b, v_mul(n, r)),
               v_sub(b, v_mul(n, r)), v_sub(a, v_mul(n, r))]
        pygame.draw.polygon(surf, cor, pts)
    pygame.draw.circle(surf, cor, a, r)
    pygame.draw.circle(surf, cor, b, r)


def circulo(surf, c, r, cor):
    pygame.draw.circle(surf, cor, P(c), r * S)


def poligono(surf, pts, cor):
    pygame.draw.polygon(surf, cor, [P(p) for p in pts])


def escurecer(cor, f):
    return tuple(max(0, min(255, int(c * f))) for c in cor)


def grupo(surf, formas, longe=False):
    """
    Desenha um grupo de formas: primeiro TODOS os contornos, depois os preenchimentos.
    Assim não aparecem linhas pretas nas articulações (joelho, cotovelo).
    formas: lista de ("c", a, b, r, cor) cápsula | ("o", c, r, cor) círculo | ("p", pts, cor)
    """
    f = 0.78 if longe else 1.0
    for fm in formas:
        if fm[0] == "c":
            capsula(surf, fm[1], fm[2], fm[3] + CONT, COR_CONTORNO)
        elif fm[0] == "o":
            circulo(surf, fm[1], fm[2] + CONT, COR_CONTORNO)
        elif fm[0] == "p":
            # contorno do polígono: cápsulas à volta das arestas
            pts = fm[1]
            for i in range(len(pts)):
                capsula(surf, pts[i], pts[(i + 1) % len(pts)], CONT, COR_CONTORNO)
            poligono(surf, pts, COR_CONTORNO)
    for fm in formas:
        if fm[0] == "c":
            capsula(surf, fm[1], fm[2], fm[3], escurecer(fm[4], f))
        elif fm[0] == "o":
            circulo(surf, fm[1], fm[2], escurecer(fm[3], f))
        elif fm[0] == "p":
            poligono(surf, fm[1], escurecer(fm[2], f))


# ====================================================================== #
# Partes do corpo                                                        #
# ====================================================================== #

def formas_patim(tornozelo, ang, pal):
    """Patim de 4 rodas visto de lado (só se veem 2 rodas). x local = para a frente."""
    def L(x, y):
        return v_add(tornozelo, v_rot((x, y), ang))
    bota = [L(-3.2, -2.5), L(2.8, -2.5), L(7.4, 2.6), L(7.6, 5.0), L(-3.6, 5.0), L(-3.8, 0.0)]
    return [
        ("p", bota, pal["bota"]),
        ("c", L(-3.8, 5.6), L(8.0, 5.6), 0.9, (90, 92, 100)),   # chassis
        ("o", L(-1.4, 7.3), 2.3, pal["roda"]),
        ("o", L(5.8, 7.3), 2.3, pal["roda"]),
        ("o", L(8.7, 5.3), 1.3, pal["travao"]),                 # travão da frente
    ]


def cubos_patim(surf, tornozelo, ang, pal, longe):
    """Os cubos claros das rodas (desenhados por cima, sem contorno)."""
    f = 0.78 if longe else 1.0
    for x in (-1.4, 5.8):
        circulo(surf, v_add(tornozelo, v_rot((x, 7.3), ang)), 0.9, escurecer(pal["cubo"], f))


def formas_perna(anca, joelho, tornozelo, pal, gr=False):
    meio_coxa = v_add(anca, v_mul(v_sub(joelho, anca), 0.62))
    if gr:
        return [
            ("c", anca, meio_coxa, 4.4, pal["calcoes"]),
            ("c", meio_coxa, joelho, 3.4, pal["meia"]),
            ("c", joelho, v_add(tornozelo, (0.8, -1.0)), 4.9, pal["caneleira"]),
            ("o", joelho, 4.6, pal["caneleira_esc"]),
        ]
    return [
        ("c", anca, meio_coxa, 3.9, pal["calcoes"]),
        ("c", meio_coxa, joelho, 3.0, pal["pele"]),
        ("c", joelho, tornozelo, 3.0, pal["meia"]),
        ("o", joelho, 3.2, pal["joelheira"]),
    ]


def formas_braco(ombro, cotovelo, mao, pal, gr=False, luva_grande=False):
    r_luva = 3.6 if luva_grande else 2.8
    return [
        ("c", ombro, cotovelo, 3.0 if gr else 2.7, pal["kit"]),
        ("c", cotovelo, mao, 2.3, pal["kit"] if gr else pal["pele"]),
        ("o", mao, r_luva, pal["luva"]),
    ]


def desenhar_cabeca(surf, pescoco, centro, ang, pal, gr=False):
    """Cabeça de perfil virada para a direita. 'ang' inclina a cara."""
    def L(x, y):
        return v_add(centro, v_rot((x, y), ang))
    if gr:
        grupo(surf, [("c", pescoco, centro, 2.6, pal["pele_esc"]),
                     ("o", centro, 7.0, pal["capacete"])])
        # Grelha do capacete (frente da cara)
        cara = L(3.2, 1.0)
        circulo(surf, cara, 4.6, (30, 30, 36))
        for i in range(-3, 4):
            capsula(surf, L(1.0, 1.0 + i * 1.3), L(7.3, 1.0 + i * 1.3), 0.35, pal["grelha"])
        for i in range(0, 4):
            capsula(surf, L(1.6 + i * 1.8, -3.2), L(1.6 + i * 1.8, 5.2), 0.35, pal["grelha"])
        capsula(surf, L(-4.5, -3.5), L(2.0, -6.2), 0.9, (110, 114, 126))   # brilho
        return
    grupo(surf, [
        ("c", pescoco, centro, 2.3, pal["pele_esc"]),
        ("o", L(-1.0, -1.4), 6.3, pal["cabelo"]),
        ("o", centro, 6.0, pal["pele"]),
        ("o", L(5.4, 0.8), 1.3, pal["pele"]),          # nariz
    ])
    # Cabelo por cima (parte de trás e de cima da cabeça)
    circulo(surf, L(-1.3, -1.6), 5.9, pal["cabelo"])
    circulo(surf, L(1.6, 1.3), 4.9, pal["pele"])
    circulo(surf, L(4.6, 0.6), 1.1, pal["pele"])
    capsula(surf, L(-0.5, -5.2), L(5.6, -3.3), 1.5, pal["cabelo"])      # franja
    # Orelha, olho, sobrancelha, boca
    circulo(surf, L(-0.6, 0.9), 1.5, COR_CONTORNO)
    circulo(surf, L(-0.6, 0.9), 1.0, pal["pele_esc"])
    pygame.draw.ellipse(surf, COR_CONTORNO,
                        pygame.Rect(P(L(2.9, -1.2)), (1.3 * S, 1.9 * S)))
    capsula(surf, L(2.4, -2.4), L(4.6, -2.6), 0.35, pal["cabelo"])
    capsula(surf, L(3.4, 3.4), L(4.6, 3.2), 0.3, escurecer(pal["pele_esc"], 0.8))


def formas_stick(topo, calcanhar):
    """Stick de hóquei em patins: cabo direito e pá curva junto ao chão."""
    d = v_norm(v_sub(calcanhar, topo))
    f = (d[1], -d[0])                     # perpendicular virada para a frente
    if f[0] < 0:
        f = (-f[0], -f[1])
    def B(a, b):
        return v_add(calcanhar, v_add(v_mul(f, a), v_mul(d, b)))
    pa = [B(0, 0), B(1.6, 1.8), B(4.6, 2.9), B(7.6, 2.4)]
    formas = [("c", topo, calcanhar, 1.15, PALETA_JOGADOR["stick"])]
    for i in range(3):
        formas.append(("c", pa[i], pa[i + 1], 1.35, PALETA_JOGADOR["stick"]))
    return formas, pa


# ====================================================================== #
# Pose -> imagem                                                         #
# ====================================================================== #

POSE_BASE = {
    "anca": (44.0, 57.0),
    "incl": 22.0,          # inclinação do tronco (graus, + = para a frente)
    "cabeca": 0.0,         # inclinação extra da cabeça
    "perto": (52.0, 0.0, 0.0),   # patim da perna mais perto da câmara: (x, levantar, ângulo)
    "longe": (40.0, 0.0, 0.0),
    "stick": (66.0, 87.0, 38.0), # calcanhar da pá (x, y) e ângulo do cabo (+ = topo para trás)
    "mao_perto": None,     # alvo livre para a mão de perto (None = agarra o stick)
    "mao_longe": None,
    "frac": 0.30,          # onde a mão de perto agarra o stick (0 = topo)
    "rot": 0.0,            # rodar o corpo todo (quedas), à volta dos patins
    "assentar": False,     # depois de rodar, pousar no chão
    "dx": 0.0, "dy": 0.0,
}


def _ponto_alcancavel(ombro, topo, d, frac_pref, alcance):
    """Escolhe onde a mão agarra o stick: o mais perto possível de frac_pref, mas ao alcance."""
    melhor, melhor_custo = None, 1e9
    for i in range(0, 61):
        fr = i / 100
        p = v_add(topo, v_mul(d, STICK * fr))
        dist = v_len(v_sub(p, ombro))
        custo = abs(fr - frac_pref) + max(0.0, dist - alcance) * 0.2
        if custo < melhor_custo:
            melhor, melhor_custo = p, custo
    return melhor


def desenhar_pose(pose, pal, gr=False):
    pz = dict(POSE_BASE)
    pz.update(pose)
    surf = pygame.Surface(((CEL + 2 * MARGEM) * S, (CEL + 2 * MARGEM) * S), pygame.SRCALPHA)

    anca = pz["anca"]
    eixo = v_rot((0, -1), pz["incl"])           # direção do tronco (para cima)
    pescoco = v_add(anca, v_mul(eixo, TRONCO))
    ombro_perto = v_add(anca, v_mul(eixo, OMBRO))
    ombro_longe = v_add(ombro_perto, (-1.5, 0.4))
    cabeca = v_add(pescoco, v_rot((1.2, -6.4), pz["incl"] * 0.45 + pz["cabeca"]))
    ang_cara = pz["incl"] * 0.25 + pz["cabeca"]

    # Pernas (IK anca -> tornozelo)
    pernas = {}
    for lado, desl in (("perto", 1.0), ("longe", -1.0)):
        x, lev, ang = pz[lado]
        tornozelo_alvo = (x, CHAO - PE_ALT - lev)
        raiz = v_add(anca, (desl, 0))
        joelho, tornozelo = ik(raiz, tornozelo_alvo, COXA, CANELA, "frente")
        pernas[lado] = (raiz, joelho, tornozelo, ang)

    # Stick e mãos
    sx, sy, sang = pz["stick"]
    calc = (sx, sy)
    d = (math.sin(math.radians(sang)), math.cos(math.radians(sang)))
    topo = v_sub(calc, v_mul(d, STICK))
    alcance = BRACO + ANTEBRACO - 0.3
    alvo_longe = pz["mao_longe"] or _ponto_alcancavel(ombro_longe, topo, d, 0.03, alcance)
    alvo_perto = pz["mao_perto"] or _ponto_alcancavel(ombro_perto, topo, d, pz["frac"], alcance)
    cot_l, mao_l = ik(ombro_longe, alvo_longe, BRACO, ANTEBRACO, "baixo")
    cot_p, mao_p = ik(ombro_perto, alvo_perto, BRACO, ANTEBRACO, "baixo")
    # O stick fica sempre preso às mãos. Quem o agarra depende das mãos que estão livres:
    livre_p, livre_l = pz["mao_perto"] is not None, pz["mao_longe"] is not None
    if livre_p and livre_l:
        # festejar: o stick passa pelas duas mãos (levantado)
        dir_s = v_norm(v_sub(mao_p, mao_l))
        topo = v_sub(mao_l, v_mul(dir_s, 1.5))
        calc = v_add(topo, v_mul(dir_s, STICK))
    elif livre_p:
        # sprint: só a mão de longe agarra, o stick pende dela com o ângulo pedido
        topo = v_sub(mao_l, v_mul(d, 1.5))
        calc = v_add(topo, v_mul(d, STICK))
    elif livre_l:
        # guarda-redes: a luva está livre, a mão de perto agarra o stick
        topo = v_sub(mao_p, v_mul(d, STICK * pz["frac"]))
        calc = v_add(topo, v_mul(d, STICK))
    else:
        # as duas mãos no stick: o stick passa por elas (se a direção fizer sentido)
        dir_s = v_norm(v_sub(mao_p, mao_l))
        if v_len(v_sub(mao_p, mao_l)) < 1.0 or dir_s[0] * d[0] + dir_s[1] * d[1] < 0.6:
            dir_s = d
        topo = v_sub(mao_l, v_mul(dir_s, 1.5))
        calc = v_add(topo, v_mul(dir_s, STICK))

    # ---------- Desenho, de trás para a frente ----------
    # 1. braço de longe
    grupo(surf, formas_braco(ombro_longe, cot_l, mao_l, pal, gr, luva_grande=gr), longe=True)
    # 2. perna de longe + patim
    r, j, t, a = pernas["longe"]
    grupo(surf, formas_perna(r, j, t, pal, gr) + formas_patim(t, a, pal), longe=True)
    cubos_patim(surf, t, a, pal, True)
    # 3. tronco (camisola) com riscas
    largura = 8.2 if gr else 6.9
    grupo(surf, [("c", v_add(anca, v_mul(eixo, 2.0)), v_add(anca, v_mul(eixo, TRONCO - 3.5)),
                  largura, pal["kit"])])
    if not gr:
        perp = (eixo[1] * -1, eixo[0])
        for off in (-2.4, 2.4):
            capsula(surf, v_add(v_add(anca, v_mul(eixo, 1.0)), v_mul(perp, off)),
                    v_add(v_add(anca, v_mul(eixo, TRONCO - 3.6)), v_mul(perp, off * 0.85)),
                    1.15, pal["riscas"])
        # sombra nas costas
        capsula(surf, v_add(v_add(anca, v_mul(eixo, 1.5)), v_mul(perp, -5.6)),
                v_add(v_add(anca, v_mul(eixo, TRONCO - 4)), v_mul(perp, -5.4)),
                1.1, escurecer(pal["kit"], 0.75))
    else:
        # GR: peitilho mais largo e número claro
        perp = (eixo[1] * -1, eixo[0])
        capsula(surf, v_add(anca, v_mul(eixo, 5)), v_add(anca, v_mul(eixo, 13)), 3.0, pal["riscas"])
    # 4. calções
    grupo(surf, [("c", v_add(anca, v_mul(eixo, 1.5)), v_add(anca, (2.5, 2.5)),
                  5.6 if gr else 5.0, pal["calcoes"])])
    # 5. cabeça
    desenhar_cabeca(surf, pescoco, cabeca, ang_cara, pal, gr)
    # 6. perna de perto + patim
    r, j, t, a = pernas["perto"]
    grupo(surf, formas_perna(r, j, t, pal, gr) + formas_patim(t, a, pal))
    cubos_patim(surf, t, a, pal, False)
    # 7. stick
    formas_s, pa = formas_stick(topo, calc)
    grupo(surf, formas_s)
    capsula(surf, pa[1], pa[3], 1.2, pal["fita"])          # fita na pá
    capsula(surf, topo, v_add(topo, v_mul(v_norm(v_sub(calc, topo)), 3)), 1.3, pal["fita"])
    # 8. luva de longe por cima do stick (está a agarrá-lo)
    grupo(surf, [("o", mao_l, 3.8 if gr else 2.8, pal["luva"])], longe=True)
    # 9. braço de perto
    grupo(surf, formas_braco(ombro_perto, cot_p, mao_p, pal, gr, luva_grande=gr))

    # ---------- Rotação do corpo todo (quedas) ----------
    if pz["rot"]:
        pivo = P(((pernas["perto"][2][0] + pernas["longe"][2][0]) / 2, CHAO))
        rodada = pygame.transform.rotate(surf, pz["rot"])
        # manter o pivô no mesmo sítio
        centro = surf.get_rect().center
        vec = v_sub(pivo, centro)
        vec_r = v_rot(vec, -pz["rot"])
        nova = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        rr = rodada.get_rect(center=(centro[0] + vec[0] - vec_r[0] + 0, centro[1] + vec[1] - vec_r[1]))
        nova.blit(rodada, rr)
        surf = nova
    if pz["assentar"]:
        caixa = surf.get_bounding_rect()
        desloc_y = (CHAO + MARGEM) * S - caixa.bottom
        desloc_x = (CEL // 2 + MARGEM) * S - caixa.centerx
        nova = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        nova.blit(surf, (desloc_x, desloc_y))
        surf = nova
    if pz["dx"] or pz["dy"]:
        nova = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        nova.blit(surf, (pz["dx"] * S, pz["dy"] * S))
        surf = nova

    final = surf.subsurface((MARGEM * S, MARGEM * S, CEL * S, CEL * S))
    return pygame.transform.smoothscale(final, (CEL, CEL))


# ====================================================================== #
# Animações                                                              #
# ====================================================================== #

def suave(t):
    """Easing: começa e acaba devagar."""
    return t * t * (3 - 2 * t)


def misturar_pose(a, b, t):
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, POSE_BASE[k]), b.get(k, POSE_BASE[k])
        if isinstance(va, tuple) and isinstance(vb, tuple):
            out[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            out[k] = va + (vb - va) * t
        else:
            out[k] = vb if t >= 0.5 else va
    return out


def passada(fase, ax, frente, tras, altura, empurrar=0.6):
    """Posição de um patim no ciclo de patinagem (fase 0..1)."""
    if fase < empurrar:                      # patim no chão a empurrar para trás
        t = suave(fase / empurrar)
        x = frente + (tras - frente) * t
        return (ax + x, 0.0, 14.0 * t * t)   # no fim do empurrão o calcanhar levanta
    t = (fase - empurrar) / (1 - empurrar)   # patim no ar a voltar à frente
    x = tras + (frente - tras) * suave(t)
    return (ax + x, altura * math.sin(math.pi * t), 14.0 * (1 - t) - 6 * math.sin(math.pi * t))


def ciclo_patinar(n, incl, frente, tras, altura, bob, anca_y, stick_fn=None, extra=None):
    frames = []
    for i in range(n):
        p = i / n
        ax = 44.0
        pose = {
            "anca": (ax, anca_y + bob * math.cos(4 * math.pi * p)),
            "incl": incl + 1.5 * math.sin(4 * math.pi * p),
            "perto": passada(p, ax, frente, tras, altura),
            "longe": passada((p + 0.5) % 1, ax, frente, tras, altura),
            "stick": (ax + 23, 87.0, 40 + 3 * math.sin(2 * math.pi * p)),
        }
        if stick_fn:
            pose.update(stick_fn(p, ax))
        if extra:
            pose.update(extra(p, ax))
        frames.append(pose)
    return frames


def keyframes(chaves, n):
    """Interpola uma lista de poses-chave em n frames."""
    frames = []
    for i in range(n):
        t = i / (n - 1) * (len(chaves) - 1)
        k = min(int(t), len(chaves) - 2)
        frames.append(misturar_pose(chaves[k], chaves[k + 1], suave(t - k)))
    return frames


PARADO = {"anca": (44, 56), "incl": 14, "perto": (50, 0, 0), "longe": (39, 0, 0),
          "stick": (64, 87, 36)}
DEITADO = {"anca": (44, 58), "incl": 0, "cabeca": -10, "perto": (52, 4, 30), "longe": (36, 0, -20),
           "stick": (70, 80, 70), "rot": 90, "assentar": True}


def animacoes_jogador():
    A = {}
    # Parado: respiração e o stick a bater levemente no chão
    A["parado"] = ([{**PARADO, "anca": (44, 56 + 0.6 * math.sin(i / 4 * 2 * math.pi)),
                     "stick": (64, 87 - (1.0 if i == 2 else 0), 36 + 1.5 * math.sin(i / 4 * 2 * math.pi))}
                    for i in range(4)], 4.0, True)

    # Patinar: 8 frames, pernas alternadas
    A["patinar"] = (ciclo_patinar(8, 24, 9, -17, 5, 0.9, 57), 10.0, True)

    # Sprint: mais inclinado, passadas maiores, braço livre a balançar
    def sprint_extra(p, ax):
        return {"mao_perto": (ax + 8 + 9 * math.sin(2 * math.pi * p), 52 + 3 * math.cos(2 * math.pi * p)),
                "stick": (ax + 26, 86.0, 52)}
    A["sprint"] = (ciclo_patinar(6, 32, 12, -20, 7, 1.2, 59, extra=sprint_extra), 12.0, True)

    # Travar: corpo para trás, patins à frente e de lado, a raspar
    A["travar"] = ([{"anca": (42, 60 + 0.5 * i), "incl": -6 + 2 * i, "perto": (56, 0, -12), "longe": (36, 0, 8),
                     "stick": (62, 86, 20)} for i in range(2)], 12.0, True)

    # Com bola: patinar com a pá a mexer de um lado para o outro (a conduzir a bola)
    def conduzir(p, ax):
        return {"stick": (ax + 21 + 4 * math.sin(4 * math.pi * p), 87.0, 42 + 4 * math.sin(4 * math.pi * p))}
    A["com_bola"] = (ciclo_patinar(8, 27, 8, -15, 4, 0.8, 58, stick_fn=conduzir), 10.0, True)

    # Passe: puxar o stick atrás, varrer para a frente, acompanhar
    A["passe"] = (keyframes([
        {**PARADO, "incl": 22, "stick": (64, 87, 40)},
        {**PARADO, "incl": 18, "stick": (46, 86, 15)},
        {**PARADO, "incl": 28, "stick": (72, 86, 55)},
        {**PARADO, "incl": 26, "stick": (80, 80, 72)},
        {**PARADO, "incl": 20, "stick": (66, 87, 42)},
    ], 5), 14.0, False)

    # Remate: levantar o stick bem atrás, descer com força, acompanhar alto
    A["remate"] = (keyframes([
        {**PARADO, "incl": 20, "stick": (62, 87, 38)},
        {**PARADO, "incl": 8, "anca": (42, 56), "stick": (30, 58, -60)},
        {**PARADO, "incl": 4, "anca": (41, 57), "stick": (28, 50, -85)},
        {**PARADO, "incl": 30, "anca": (46, 58), "stick": (66, 87, 30)},
        {**PARADO, "incl": 30, "anca": (47, 58), "stick": (82, 64, 105)},
        {**PARADO, "incl": 22, "stick": (66, 87, 40)},
    ], 6), 14.0, False)

    # Desarme: esticar o stick lá à frente, rente ao chão
    A["desarme"] = (keyframes([
        {**PARADO, "incl": 24, "stick": (64, 87, 40)},
        {**PARADO, "incl": 40, "anca": (46, 60), "perto": (58, 0, 0), "longe": (30, 0, 12),
         "stick": (84, 87, 66), "frac": 0.45},
        {**PARADO, "incl": 40, "anca": (46, 60), "perto": (58, 0, 0), "longe": (30, 0, 12),
         "stick": (86, 87, 70), "frac": 0.45},
        {**PARADO, "incl": 24, "stick": (64, 87, 40)},
    ], 4), 12.0, False)

    # Queda: desequilibra para trás e cai no chão
    A["queda"] = (keyframes([
        {**PARADO, "incl": 10, "stick": (66, 84, 50)},
        {**PARADO, "incl": -10, "cabeca": 10, "stick": (70, 76, 70), "rot": 20},
        {**PARADO, "incl": -5, "cabeca": 0, "perto": (56, 6, -20), "stick": (72, 72, 80), "rot": 55},
        DEITADO,
        {**DEITADO, "dy": 0.0, "cabeca": -4},
    ], 5), 10.0, False)

    # Levantar: de deitado, ajoelhar e ficar de pé
    ajoelhado = {"anca": (42, 72), "incl": 18, "perto": (54, 0, 0), "longe": (28, 0, 70),
                 "stick": (64, 87, 30)}
    A["levantar"] = ([
        {**DEITADO, "rot": 60, "cabeca": 0},
        ajoelhado,
        {**PARADO, "anca": (43, 63), "incl": 26},
        PARADO,
    ], 7.0, False)

    # Festejar: stick no ar, aos saltinhos
    fest = []
    for i in range(6):
        salto = abs(math.sin(i / 6 * 2 * math.pi)) * 4
        fest.append({"anca": (44, 54 - salto), "incl": -4, "cabeca": -10,
                     "perto": (50, salto, -10), "longe": (39, salto * 0.6, 6),
                     "mao_perto": (56, 20 - salto + (2 if i % 2 else -1)),
                     "mao_longe": (38, 22 - salto + (-1 if i % 2 else 2)),
                     "stick": (64, 30 - salto, -150)})
    A["festejar"] = (fest, 8.0, True)
    return A


def animacoes_gr():
    A = {}
    base = {"anca": (42, 57), "incl": 18, "perto": (53, 0, -4), "longe": (45, 0, 4),
            "stick": (62, 87, 18), "mao_longe": (53, 46), "frac": 0.45}
    A["parado"] = ([{**base, "anca": (42, 57 + 0.6 * math.sin(i / 4 * 2 * math.pi)),
                     "mao_longe": (53, 46 + 0.6 * math.sin(i / 4 * 2 * math.pi))}
                    for i in range(4)], 4.0, True)
    # Deslizar de lado: pequenos passos alternados
    mov = []
    for i in range(4):
        p = i / 4
        mov.append({**base, "anca": (42, 57 + 0.8 * math.cos(4 * math.pi * p)),
                    "perto": (53 + 2 * math.sin(2 * math.pi * p), 2 * max(0, math.sin(2 * math.pi * p)), -6),
                    "longe": (45 - 2 * math.sin(2 * math.pi * p), 2 * max(0, -math.sin(2 * math.pi * p)), 6)})
    A["mover"] = (mov, 10.0, True)
    # Defender em baixo ("borboleta"): joelhos no chão e caneleiras abertas
    borb = {"anca": (42, 73), "incl": 8, "perto": (58, 0, 40), "longe": (24, 0, 70),
            "stick": (62, 87, 10), "mao_longe": (54, 56)}
    A["defender"] = (keyframes([base, borb, borb], 3), 12.0, False)
    # Defesa alta: luva no ar
    alta = {**base, "anca": (42, 58), "incl": 2, "mao_longe": (48, 20), "perto": (56, 2, -10)}
    A["defesa_alta"] = (keyframes([base, alta, alta], 3), 12.0, False)
    # Festejar
    fest = []
    for i in range(4):
        s = 3 if i % 2 else 0
        fest.append({**base, "anca": (42, 58 - s), "incl": -2, "mao_longe": (36, 24 - s),
                     "mao_perto": (54, 22 - s), "stick": (62, 32 - s, -150),
                     "perto": (54, s, 0), "longe": (32, s, 0)})
    A["festejar"] = (fest, 6.0, True)
    return A


# ====================================================================== #
# Exportar                                                               #
# ====================================================================== #

def exportar(nome, anims, pal, gr, pasta):
    colunas = max(len(f) for f, _, _ in anims.values())
    folha = pygame.Surface((colunas * CEL, len(anims) * CEL), pygame.SRCALPHA)
    info = {"celula": [CEL, CEL], "ancora_pes": [CEL // 2, CHAO],
            "virado_para": "direita", "animacoes": {}}
    pasta_frames = os.path.join(pasta, "frames", nome)
    os.makedirs(pasta_frames, exist_ok=True)
    for linha, (anim, (poses, fps, loop)) in enumerate(anims.items()):
        for col, pose in enumerate(poses):
            img = desenhar_pose(pose, pal, gr)
            folha.blit(img, (col * CEL, linha * CEL))
            pygame.image.save(img, os.path.join(pasta_frames, f"{anim}_{col + 1:02d}.png"))
        info["animacoes"][anim] = {"row": linha, "frames": len(poses), "fps": fps, "loop": loop}
    pygame.image.save(folha, os.path.join(pasta, f"{nome}.png"))
    with open(os.path.join(pasta, f"{nome}.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"{nome}: {len(anims)} animações, {sum(len(p) for p, _, _ in anims.values())} frames")
    return folha, info


def gif_preview(pasta, folhas, escala=2):
    """
    Cria preview.gif com todas as animações a mexer (precisa do Pillow: pip install pillow).
    folhas: lista de (nome, info) já exportadas.
    """
    try:
        from PIL import Image
    except ImportError:
        print("(Pillow não instalado: preview.gif não foi criado)")
        return
    linhas = []
    for nome, info in folhas:
        for anim, a in info["animacoes"].items():
            linhas.append((nome, anim, a))
    colunas = 6
    n_linhas = (len(linhas) + colunas - 1) // colunas
    lado = CEL * escala
    imagens = []
    for t in range(24):
        quadro = Image.new("RGBA", (colunas * lado, n_linhas * (lado + 14)), (226, 180, 124, 255))
        for k, (nome, anim, a) in enumerate(linhas):
            # cada animação anda à sua velocidade (o GIF corre a 12 fps)
            idx = int(t * a["fps"] / 12)
            idx = idx % a["frames"] if a["loop"] else min(idx % (a["frames"] + 4), a["frames"] - 1)
            f = Image.open(os.path.join(pasta, "frames", nome, f"{anim}_{idx + 1:02d}.png"))
            f = f.resize((lado, lado), Image.LANCZOS)
            x, y = (k % colunas) * lado, (k // colunas) * (lado + 14)
            quadro.alpha_composite(f, (x, y))
        imagens.append(quadro.convert("RGB"))
    imagens[0].save(os.path.join(pasta, "preview.gif"), save_all=True,
                    append_images=imagens[1:], duration=83, loop=0)
    print("preview.gif criado")


def main():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pasta = os.path.join(raiz, "sprites_v3")
    os.makedirs(pasta, exist_ok=True)
    pygame.init()
    _, info_j = exportar("jogador", animacoes_jogador(), PALETA_JOGADOR, False, pasta)
    _, info_g = exportar("guarda_redes", animacoes_gr(), PALETA_GR, True, pasta)
    gif_preview(pasta, [("jogador", info_j), ("guarda_redes", info_g)])


if __name__ == "__main__":
    main()
