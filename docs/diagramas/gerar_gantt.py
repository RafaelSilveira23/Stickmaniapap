# -*- coding: utf-8 -*-
"""gerar_gantt.py - gera o diagrama de Gantt do relatório da PAP (09_gantt.png).

Executar:  python gerar_gantt.py
As tarefas são as da Tabela 10 (Cronograma do projeto). Para mudar uma data,
basta alterar a lista TAREFAS em baixo e voltar a correr o script.
"""
import os
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

PASTA = os.path.dirname(os.path.abspath(__file__))

INICIO = date(2026, 9, 1)
FIM = date(2027, 7, 1)
MESES = ["set.", "out.", "nov.", "dez.", "jan.", "fev.", "mar.", "abr.", "mai.", "jun."]

# Estado -> (preenchimento, contorno), as mesmas cores dos outros diagramas
ESTADOS = {
    "Concluído": ("#D5E8D4", "#82B366"),
    "Em curso":  ("#DAE8FC", "#6C8EBF"),
    "Planeado":  ("#FFF2CC", "#D6B656"),
}

# (fase, tarefa, início, fim, estado)
TAREFAS = [
    ("Análise e planeamento", None, None, None, None),
    ("", "Anteprojeto, requisitos e escolha das tecnologias", date(2026, 9, 15), date(2026, 10, 10), "Concluído"),

    ("Desenvolvimento (versões 1 a 15)", None, None, None, None),
    ("", "Protótipo: rinque, jogadores, bola e física", date(2026, 10, 1), date(2026, 10, 10), "Concluído"),
    ("", "Interface do mockup, símbolos e seleção de equipas", date(2026, 10, 6), date(2026, 10, 15), "Concluído"),
    ("", "Mira de remate, IA com dificuldades e faltas", date(2026, 10, 11), date(2026, 10, 20), "Concluído"),
    ("", "Animações, balizas, câmara e bancadas", date(2026, 10, 16), date(2026, 10, 24), "Concluído"),
    ("", "Correção das colisões, IA tática e guarda-redes", date(2026, 10, 21), date(2026, 10, 28), "Concluído"),
    ("", "Correção da bola no stick e da ordem de desenho", date(2026, 10, 25), date(2026, 10, 31), "Concluído"),
    ("", "Modo carreira com SQLite", date(2026, 11, 1), date(2026, 11, 8), "Concluído"),
    ("", "Menu novo, definições, ecrã inteiro e gráficos", date(2026, 11, 4), date(2026, 11, 11), "Concluído"),
    ("", "Sons, simulação dos jogos e ecrãs da carreira", date(2026, 11, 8), date(2026, 11, 15), "Concluído"),
    ("", "Planteis reais, marcadores e melhores marcadores", date(2026, 11, 11), date(2026, 11, 18), "Concluído"),
    ("", "Estilo arcade (golos e impactos)", date(2026, 11, 15), date(2026, 11, 21), "Concluído"),
    ("", "Remate na primeira pessoa e modo teste", date(2026, 11, 18), date(2026, 11, 24), "Concluído"),
    ("", "Remate em movimento, defesas e bloqueio", date(2026, 11, 21), date(2026, 11, 27), "Concluído"),
    ("", "Ecrã do remate (pavilhão, placas, stick)", date(2026, 11, 24), date(2026, 11, 30), "Concluído"),
    ("", "Defesas no remate: perspetiva e sprites HD", date(2026, 11, 27), date(2026, 12, 3), "Concluído"),
    ("", "Carreira de jogador (só o meu jogador)", date(2026, 12, 4), date(2026, 12, 18), "Concluído"),

    ("Novas funcionalidades", None, None, None, None),
    ("", "Estatísticas da partida e modo de 2 jogadores", date(2026, 11, 16), date(2026, 12, 31), "Planeado"),
    ("", "Mais estatísticas e transferências", date(2027, 1, 7), date(2027, 3, 31), "Planeado"),

    ("Validação e entrega", None, None, None, None),
    ("", "Testes com colegas, correção de erros, sprites", date(2027, 3, 1), date(2027, 4, 30), "Planeado"),
    ("", "Relatório final, manual e apresentação", date(2027, 4, 1), date(2027, 5, 31), "Em curso"),
    ("", "Defesa da PAP", date(2027, 6, 1), date(2027, 6, 30), "Planeado"),
]

# Medidas (em píxeis do diagrama; a imagem final sai com o dobro)
R = 4          # super-amostragem
SAIDA = 2
COL = 370      # largura da coluna das tarefas
DIA = 2.6      # largura de um dia
LINHA = 26     # altura de cada linha
TOPO = 70      # título + cabeçalho dos meses
M = 20         # margem


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gerar():
    pygame.init()
    dias = (FIM - INICIO).days
    W = COL + dias * DIA
    H = TOPO + len(TAREFAS) * LINHA + 50
    surf = pygame.Surface((round((W + 2 * M) * R), round((H + 2 * M) * R)))
    surf.fill((255, 255, 255))
    fontes = {}

    def fonte(tam, negrito=False):
        k = (tam, negrito)
        if k not in fontes:
            fontes[k] = pygame.font.SysFont("arial", round(tam * R * 1.02), bold=negrito)
        return fontes[k]

    def p(x, y):
        return round((x + M) * R), round((y + M) * R)

    def ret(x, y, w, h, preench=None, contorno=None, larg=1):
        r = pygame.Rect(*p(x, y), round(w * R), round(h * R))
        if preench:
            pygame.draw.rect(surf, rgb(preench), r)
        if contorno:
            pygame.draw.rect(surf, rgb(contorno), r, max(1, round(larg * R)))

    def texto(t, x, y, tam, negrito=False, cor=(20, 20, 20), centro=False):
        img = fonte(tam, negrito).render(t, True, cor)
        px, py = p(x, y)
        if centro:
            px -= img.get_width() // 2
        surf.blit(img, (px, py - img.get_height() // 2))

    def xdia(d):
        return COL + (d - INICIO).days * DIA

    # Título
    texto("Diagrama de Gantt — StickMania (set. 2026 a jun. 2027)", W / 2, 12, 16, True, centro=True)

    # Cabeçalho dos meses e linhas verticais
    y0 = TOPO - 36
    ret(0, y0, W, 36, "#F5F5F5", "#666666")
    texto("Tarefa", 8, y0 + 18, 12, True)
    for i, nome in enumerate(MESES):
        ano, mes = (2026, 9 + i) if 9 + i <= 12 else (2027, i - 3)
        d1 = date(ano, mes, 1)
        d2 = date(ano + (mes == 12), mes % 12 + 1, 1)
        x1, x2 = xdia(d1), xdia(d2)
        texto(f"{nome} {str(ano)[2:]}", (x1 + x2) / 2, y0 + 18, 12, True, centro=True)
        if i % 2 == 0:
            ret(x1, TOPO, x2 - x1, len(TAREFAS) * LINHA, "#FAFAFA")
    for i in range(len(MESES) + 1):
        ano, mes = (2026, 9 + i) if 9 + i <= 12 else (2027, i - 3)
        x = xdia(date(ano, mes, 1)) if i < len(MESES) else xdia(FIM)
        pygame.draw.line(surf, rgb("#CCCCCC"), p(x, y0), p(x, TOPO + len(TAREFAS) * LINHA), R)

    # Linhas das tarefas
    for i, (fase, tarefa, d1, d2, estado) in enumerate(TAREFAS):
        y = TOPO + i * LINHA
        pygame.draw.line(surf, rgb("#E3E3E3"), p(0, y + LINHA), p(W, y + LINHA), R // 2)
        if tarefa is None:  # cabeçalho de fase
            ret(0, y, COL, LINHA, "#E1D5E7")
            texto(fase, 8, y + LINHA / 2, 12, True, (60, 40, 80))
            continue
        texto(tarefa, 18, y + LINHA / 2, 11)
        cor, contorno = ESTADOS[estado]
        x1, x2 = xdia(d1), xdia(d2) + DIA
        ret(x1, y + 5, x2 - x1, LINHA - 10, cor, contorno, 1.2)

    # Contorno da tabela e separador da coluna das tarefas
    ret(0, y0, W, 36 + len(TAREFAS) * LINHA, None, "#666666")
    pygame.draw.line(surf, rgb("#666666"), p(COL, y0), p(COL, TOPO + len(TAREFAS) * LINHA), R)

    # Legenda
    ly = TOPO + len(TAREFAS) * LINHA + 25
    lx = COL
    texto("Legenda:", lx - 75, ly, 12, True)
    for estado, (cor, contorno) in ESTADOS.items():
        ret(lx, ly - 7, 30, 14, cor, contorno, 1.2)
        texto(estado, lx + 38, ly, 12)
        lx += 140

    final = pygame.transform.smoothscale(surf, (surf.get_width() * SAIDA // R, surf.get_height() * SAIDA // R))
    caminho = os.path.join(PASTA, "09_gantt.png")
    pygame.image.save(final, caminho)
    return caminho


if __name__ == "__main__":
    print("Gerado:", gerar())
