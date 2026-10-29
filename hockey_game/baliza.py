# -*- coding: utf-8 -*-
"""baliza.py - desenha as balizas de hóquei em patins no próprio código.

Porquê desenhar em vez de usar um PNG?
  - Os PNG antigos estavam em perspetiva de lado e não combinavam com o ringue visto de cima.
  - Desenhada no código, a baliza fica do tamanho EXATO da boca da baliza do jogo.
  - Podemos separá-la em duas camadas:
        fundo  -> desenhado ANTES dos jogadores (rede de trás, poste do fundo)
        frente -> desenhado DEPOIS (barra de cima, poste da frente, rede do lado)
    Assim a bola e o guarda-redes parecem estar mesmo DENTRO da baliza.

Vista: ligeiramente de cima e de frente (3/4), como os jogadores.
Tudo é desenhado ao dobro do tamanho e depois reduzido com smoothscale,
para as linhas ficarem suaves (anti-aliasing).
"""
import pygame

# Cores da estrutura
COR_TUBO        = (214, 38, 38)
COR_TUBO_ESCURO = (120, 16, 20)
COR_TUBO_BRILHO = (255, 150, 140)
COR_REDE        = (245, 245, 250)

_ESCALA = 2   # desenhar ao dobro e reduzir no fim


def _pontos(boca_h, altura, profundidade, margem):
    """
    Calcula os pontos da baliza (já na escala de desenho), virada para a DIREITA.
    A boca fica em x = gx; a baliza estende-se para trás (para a esquerda).
    """
    E = _ESCALA
    gx = (profundidade + margem) * E
    topo = (altura + margem) * E
    base = topo + boca_h * E
    H = altura * E
    D = profundidade * E
    estreito = 4 * E          # a parte de trás é um pouco mais estreita

    return {
        # No chão
        "F1": (gx, topo),                       # poste de cima (longe da câmara)
        "F2": (gx, base),                       # poste de baixo (perto da câmara)
        "B1": (gx - D, topo + estreito),        # canto de trás em cima
        "B2": (gx - D, base - estreito),        # canto de trás em baixo
        # No ar (somamos a altura para cima no ecrã)
        "C1": (gx, topo - H),                   # topo do poste de cima
        "C2": (gx, base - H),                   # topo do poste de baixo
        "R1": (gx - D * 0.5, topo - H * 0.8 + estreito // 2),   # fim da barra de cima
        "R2": (gx - D * 0.5, base - H * 0.8 - estreito // 2),
    }


def _painel_rede(tamanho, poligono, espaco, alpha_fundo=40, alpha_linha=150):
    """Uma superfície com rede (malha em losango) recortada no formato do polígono."""
    w, h = tamanho
    rede = pygame.Surface((w, h), pygame.SRCALPHA)
    rede.fill((*COR_REDE, alpha_fundo))
    for i in range(-h, w + h, espaco):
        pygame.draw.line(rede, (*COR_REDE, alpha_linha), (i, 0), (i + h, h), 2)
        pygame.draw.line(rede, (*COR_REDE, alpha_linha), (i, h), (i + h, 0), 2)

    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mascara, (255, 255, 255, 255), poligono)
    rede.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    # Contorno da rede, um pouco mais marcado
    pygame.draw.polygon(rede, (*COR_REDE, alpha_linha // 2), poligono, 2)
    return rede


def _tubo(surf, a, b, grossura=7):
    """Um tubo da estrutura: contorno escuro, cor e um brilho fino em cima."""
    pygame.draw.line(surf, COR_TUBO_ESCURO, a, b, grossura + 4)
    for p in (a, b):
        pygame.draw.circle(surf, COR_TUBO_ESCURO, p, (grossura + 4) // 2)
    pygame.draw.line(surf, COR_TUBO, a, b, grossura)
    for p in (a, b):
        pygame.draw.circle(surf, COR_TUBO, p, grossura // 2)
    brilho_a = (a[0] - 1, a[1] - 2)
    brilho_b = (b[0] - 1, b[1] - 2)
    pygame.draw.line(surf, COR_TUBO_BRILHO, brilho_a, brilho_b, 2)


def criar_baliza(boca_h: int, altura: int = 22, profundidade: int = 38,
                 virada_para: str = "direita"):
    """
    Cria as duas camadas da baliza.

    boca_h       : abertura da baliza em píxeis (distância entre os postes)
    altura       : altura dos postes no ecrã
    profundidade : quanto a baliza se estende para trás
    virada_para  : 'direita' (baliza da esquerda) ou 'esquerda' (baliza da direita)

    Devolve (fundo, frente, ancora) em que 'ancora' é o ponto da superfície
    que fica no meio da linha de golo (entre os dois postes, no chão).
    """
    margem = 8
    E = _ESCALA
    w = (profundidade + 2 * margem) * E
    h = (altura + boca_h + 2 * margem) * E
    P = _pontos(boca_h, altura, profundidade, margem)

    fundo  = pygame.Surface((w, h), pygame.SRCALPHA)
    frente = pygame.Surface((w, h), pygame.SRCALPHA)

    # ── 1. Sombra no chão (luz a vir de cima/esquerda) ────────────────────
    sombra = pygame.Surface((w, h), pygame.SRCALPHA)
    desloc = (6 * E, 5 * E)
    chao = [P["F1"], P["B1"], P["B2"], P["F2"]]
    pygame.draw.polygon(sombra, (30, 15, 5, 90),
                        [(x + desloc[0] * 0.3, y + desloc[1]) for x, y in chao])
    # Sombra suave: reduzir e voltar a aumentar desfoca a imagem
    pequena = pygame.transform.smoothscale(sombra, (w // 6, h // 6))
    fundo.blit(pygame.transform.smoothscale(pequena, (w, h)), (0, 0))

    espaco = 7 * E

    # ── 2. Camada de FUNDO: rede de trás, rede do lado de cima, tubos do chão ──
    fundo.blit(_painel_rede((w, h), [P["R1"], P["R2"], P["B2"], P["B1"]], espaco, 55, 170), (0, 0))
    fundo.blit(_painel_rede((w, h), [P["C1"], P["R1"], P["B1"], P["F1"]], espaco, 35, 140), (0, 0))
    # Chão da baliza (área dentro, ligeiramente mais escura)
    dentro = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(dentro, (60, 30, 10, 45), chao)
    fundo.blit(dentro, (0, 0))

    _tubo(fundo, P["B1"], P["B2"], 5)           # tubo de trás no chão
    _tubo(fundo, P["F1"], P["B1"], 5)           # tubo do chão em cima
    _tubo(fundo, P["R1"], P["B1"], 5)           # tubo inclinado de cima
    _tubo(fundo, P["C1"], P["R1"], 6)           # barra de cima do lado de cima
    _tubo(fundo, P["F1"], P["C1"], 7)           # poste de cima (longe)

    # ── 3. Camada da FRENTE: teto da rede, lado de baixo, postes da frente ────
    frente.blit(_painel_rede((w, h), [P["C1"], P["C2"], P["R2"], P["R1"]], espaco, 30, 120), (0, 0))
    frente.blit(_painel_rede((w, h), [P["C2"], P["R2"], P["B2"], P["F2"]], espaco, 30, 130), (0, 0))

    _tubo(frente, P["F2"], P["B2"], 5)          # tubo do chão em baixo
    _tubo(frente, P["R2"], P["B2"], 5)          # tubo inclinado de baixo
    _tubo(frente, P["C2"], P["R2"], 6)          # barra de cima do lado de baixo
    _tubo(frente, P["C1"], P["C2"], 7)          # TRAVESSA (barra da frente)
    _tubo(frente, P["F2"], P["C2"], 7)          # poste de baixo (perto)

    # Reduzir para o tamanho final (fica suave)
    tam = (w // E, h // E)
    fundo  = pygame.transform.smoothscale(fundo, tam)
    frente = pygame.transform.smoothscale(frente, tam)
    ancora = (profundidade + margem, altura + margem + boca_h // 2)

    if virada_para == "esquerda":
        fundo  = pygame.transform.flip(fundo, True, False)
        frente = pygame.transform.flip(frente, True, False)
        ancora = (tam[0] - ancora[0], ancora[1])

    return fundo, frente, ancora


def guardar_png(pasta: str, boca_h: int = 66):
    """Exporta as balizas para PNG (útil para o relatório da PAP ou para editar)."""
    import os
    for lado in ("direita", "esquerda"):
        fundo, frente, _ = criar_baliza(boca_h, virada_para=lado)
        junta = fundo.copy()
        junta.blit(frente, (0, 0))
        nome = "baliza_esq.png" if lado == "direita" else "baliza_dir.png"
        pygame.image.save(junta, os.path.join(pasta, nome))
