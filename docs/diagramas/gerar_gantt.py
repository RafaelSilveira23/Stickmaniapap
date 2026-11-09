# -*- coding: utf-8 -*-
"""gerar_gantt.py - gera o diagrama de Gantt do projeto em dois formatos:

  • 09_gantt.png      - imagem para o relatório da PAP (desenhada com pygame), com a cor de
                        cada barra a mostrar quem fez a tarefa (divisão de tarefas da dupla);
  • ../GANTT.md       - o mesmo diagrama em Mermaid, que o site do GitHub desenha sozinho
                        (abre docs/GANTT.md no GitHub para o ver).

Executar:  python gerar_gantt.py
As tarefas são as da Tabela 10 (Cronograma do projeto). Para mudar uma data,
basta alterar a lista TAREFAS em baixo e voltar a correr o script (os dois ficam iguais).
"""
import os
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

PASTA = os.path.dirname(os.path.abspath(__file__))

INICIO = date(2026, 9, 1)
FIM = date(2027, 7, 1)
MESES = ["set.", "out.", "nov.", "dez.", "jan.", "fev.", "mar.", "abr.", "mai.", "jun."]

# Divisão de tarefas: a cor de cada barra diz quem fez a tarefa -> (nome, preenchimento, contorno)
VASCO, RAFAEL, DOIS = "V", "R", "D"
PESSOAS = {
    VASCO: ("Vasco Andreia", "#A9C4EB", "#4A6FA5"),
    RAFAEL: ("Rafael da Hora Silveira", "#FFCE9F", "#C47F00"),
    DOIS: ("Os dois", "#B9E0A5", "#5E9447"),
}
CURTO = {VASCO: "Vasco", RAFAEL: "Rafael", DOIS: "Os dois"}
# O estado vê-se pelo padrão da barra: cheia (concluído), com riscas (em curso) ou só o contorno (planeado)
ESTADOS = ["Concluído", "Em curso", "Planeado"]

# (fase, tarefa, início, fim, estado, quem fez)
TAREFAS = [
    ("Análise e planeamento", None, None, None, None, None),
    ("", "Anteprojeto, requisitos e escolha das tecnologias", date(2026, 9, 15), date(2026, 10, 10), "Concluído", DOIS),

    ("Desenvolvimento (versões 1 a 28)", None, None, None, None, None),
    ("", "Protótipo: rinque, jogadores, bola e física", date(2026, 10, 1), date(2026, 10, 10), "Concluído", RAFAEL),
    ("", "Interface do mockup, símbolos e seleção de equipas", date(2026, 10, 6), date(2026, 10, 15), "Concluído", VASCO),
    ("", "IA com três níveis de dificuldade", date(2026, 10, 11), date(2026, 10, 20), "Concluído", VASCO),
    ("", "Mira de remate e faltas", date(2026, 10, 11), date(2026, 10, 20), "Concluído", RAFAEL),
    ("", "Animações, balizas, câmara e bancadas", date(2026, 10, 16), date(2026, 10, 24), "Concluído", RAFAEL),
    ("", "Correção das colisões", date(2026, 10, 21), date(2026, 10, 28), "Concluído", RAFAEL),
    ("", "IA tática e guarda-redes", date(2026, 10, 21), date(2026, 10, 28), "Concluído", VASCO),
    ("", "Correção da bola no stick e da ordem de desenho", date(2026, 10, 25), date(2026, 10, 31), "Concluído", RAFAEL),
    ("", "Modo carreira: campeonato e calendário", date(2026, 11, 1), date(2026, 11, 8), "Concluído", DOIS),
    ("", "Base de dados SQLite", date(2026, 11, 1), date(2026, 11, 8), "Concluído", VASCO),
    ("", "Menu novo, definições e ecrã inteiro", date(2026, 11, 4), date(2026, 11, 11), "Concluído", VASCO),
    ("", "Gráficos do rinque e do pavilhão", date(2026, 11, 4), date(2026, 11, 11), "Concluído", RAFAEL),
    ("", "Sons criados por síntese", date(2026, 11, 8), date(2026, 11, 15), "Concluído", VASCO),
    ("", "Simulação dos jogos e ecrãs da carreira", date(2026, 11, 8), date(2026, 11, 15), "Concluído", DOIS),
    ("", "Planteis reais, marcadores e melhores marcadores", date(2026, 11, 11), date(2026, 11, 18), "Concluído", DOIS),
    ("", "Estilo arcade (golos e impactos)", date(2026, 11, 15), date(2026, 11, 21), "Concluído", DOIS),
    ("", "Remate na primeira pessoa e modo teste", date(2026, 11, 18), date(2026, 11, 24), "Concluído", VASCO),
    ("", "Remate em movimento, defesas e bloqueio", date(2026, 11, 21), date(2026, 11, 27), "Concluído", VASCO),
    ("", "Ecrã do remate (pavilhão, placas, stick)", date(2026, 11, 24), date(2026, 11, 30), "Concluído", VASCO),
    ("", "Defesas no remate: perspetiva e sprites HD", date(2026, 11, 27), date(2026, 12, 3), "Concluído", VASCO),
    ("", "Carreira de jogador (só o meu jogador)", date(2026, 12, 4), date(2026, 12, 18), "Concluído", VASCO),
    ("", "Vida do jogador: escolhas, eventos e atividades", date(2026, 12, 14), date(2026, 12, 31), "Concluído", VASCO),
    ("", "Menus: pausa, fim de jogo e transições", date(2026, 12, 28), date(2027, 1, 10), "Concluído", VASCO),
    ("", "Vida: pessoas, consequências e conquistas", date(2027, 1, 11), date(2027, 1, 24), "Concluído", VASCO),
    ("", "Otimização, arranque sem consola e limpeza", date(2027, 1, 25), date(2027, 1, 31), "Concluído", DOIS),
    ("", "Modo online: jogar contra um amigo pela internet", date(2027, 2, 1), date(2027, 2, 14), "Concluído", RAFAEL),
    ("", "Versão para o browser (site) e online com código", date(2027, 2, 15), date(2027, 2, 28), "Concluído", RAFAEL),
    ("", "Aplicação para Windows, instalador e servidor online", date(2027, 3, 1), date(2027, 3, 14), "Concluído", RAFAEL),
    ("", "Guarda-redes no ecrã do remate (animação)", date(2027, 3, 15), date(2027, 3, 21), "Concluído", VASCO),
    ("", "Stickada no online e servidor na Europa", date(2027, 3, 22), date(2027, 3, 28), "Concluído", RAFAEL),

    ("Novas funcionalidades", None, None, None, None, None),
    ("", "Estatísticas da partida e modo de 2 jogadores", date(2026, 11, 16), date(2026, 12, 31), "Planeado", DOIS),
    ("", "Mais estatísticas e transferências", date(2027, 1, 7), date(2027, 3, 31), "Planeado", DOIS),

    ("Validação e entrega", None, None, None, None, None),
    ("", "Testes com colegas, correção de erros, sprites", date(2027, 3, 1), date(2027, 4, 30), "Planeado", DOIS),
    ("", "Relatório final, manual e apresentação", date(2027, 4, 1), date(2027, 5, 31), "Em curso", DOIS),
    ("", "Defesa da PAP", date(2027, 6, 1), date(2027, 6, 30), "Planeado", DOIS),
]

# Medidas (em píxeis do diagrama; a imagem final sai com o dobro)
R = 4          # super-amostragem
SAIDA = 2
COL_T = 360    # largura da coluna das tarefas
COL = COL_T + 62   # + coluna "Quem fez"
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
    H = TOPO + len(TAREFAS) * LINHA + 80
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

    def riscas(x, y, w, h, cor):
        """Riscas na diagonal dentro do retângulo (barras em curso e planeadas)."""
        r = pygame.Rect(*p(x, y), round(w * R), round(h * R))
        surf.set_clip(r)
        passo = round(6 * R)
        for k in range(r.left - r.height, r.right + passo, passo):
            pygame.draw.line(surf, rgb(cor), (k, r.bottom), (k + r.height, r.top), max(1, round(1.4 * R)))
        surf.set_clip(None)

    def barra(x, y, w, h, estado, cor, contorno):
        if estado == "Concluído":
            ret(x, y, w, h, cor, contorno, 1.2)
        elif estado == "Em curso":
            ret(x, y, w, h, cor)
            riscas(x, y, w, h, contorno)
            ret(x, y, w, h, None, contorno, 1.2)
        else:  # planeado: só o contorno e riscas claras
            ret(x, y, w, h, "#FFFFFF")
            riscas(x, y, w, h, cor)
            ret(x, y, w, h, None, contorno, 1.2)

    def xdia(d):
        return COL + (d - INICIO).days * DIA

    # Título
    texto("Diagrama de Gantt — StickMania (set. 2026 a jun. 2027), com a divisão de tarefas",
          W / 2, 12, 16, True, centro=True)

    # Cabeçalho dos meses e linhas verticais
    y0 = TOPO - 36
    ret(0, y0, W, 36, "#F5F5F5", "#666666")
    texto("Tarefa", 8, y0 + 18, 12, True)
    texto("Quem fez", (COL_T + COL) / 2, y0 + 18, 12, True, centro=True)
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
    for i, (fase, tarefa, d1, d2, estado, quem) in enumerate(TAREFAS):
        y = TOPO + i * LINHA
        pygame.draw.line(surf, rgb("#E3E3E3"), p(0, y + LINHA), p(W, y + LINHA), R // 2)
        if tarefa is None:  # cabeçalho de fase
            ret(0, y, COL, LINHA, "#E1D5E7")
            texto(fase, 8, y + LINHA / 2, 12, True, (60, 40, 80))
            continue
        _, cor, contorno = PESSOAS[quem]
        texto(tarefa, 18, y + LINHA / 2, 11)
        ret(COL_T + 4, y + 4, COL - COL_T - 8, LINHA - 8, cor, contorno, 1)   # etiqueta com a cor da pessoa
        texto(CURTO[quem], (COL_T + COL) / 2, y + LINHA / 2, 10, True, rgb(contorno) if quem != RAFAEL else (140, 85, 0),
              centro=True)
        x1, x2 = xdia(d1), xdia(d2) + DIA
        barra(x1, y + 5, x2 - x1, LINHA - 10, estado, cor, contorno)

    # Contorno da tabela e separadores das colunas
    ret(0, y0, W, 36 + len(TAREFAS) * LINHA, None, "#666666")
    for x in (COL_T, COL):
        pygame.draw.line(surf, rgb("#666666"), p(x, y0), p(x, TOPO + len(TAREFAS) * LINHA), R)

    # Legenda: quem fez (cor) e estado (padrão da barra)
    ly = TOPO + len(TAREFAS) * LINHA + 25
    lx = COL
    texto("Quem fez:", lx - 85, ly, 12, True)
    for nome, cor, contorno in PESSOAS.values():
        ret(lx, ly - 7, 30, 14, cor, contorno, 1.2)
        texto(nome, lx + 38, ly, 12)
        lx += 70 + fonte(12).size(nome)[0] / R
    ly += 28
    lx = COL
    texto("Estado:", lx - 85, ly, 12, True)
    for estado in ESTADOS:
        barra(lx, ly - 7, 30, 14, estado, "#DDDDDD", "#777777")
        texto(estado, lx + 38, ly, 12)
        lx += 140

    final = pygame.transform.smoothscale(surf, (surf.get_width() * SAIDA // R, surf.get_height() * SAIDA // R))
    caminho = os.path.join(PASTA, "09_gantt.png")
    pygame.image.save(final, caminho)
    return caminho


ESTADO_MERMAID = {"Concluído": "done", "Em curso": "active", "Planeado": ""}


def gerar_mermaid() -> str:
    """Escreve docs/GANTT.md com o diagrama em Mermaid (o GitHub mostra-o como um Gantt)."""
    linhas = ["gantt",
              "    title StickMania - Diagrama de Gantt (set. 2026 a jun. 2027)",
              "    dateFormat YYYY-MM-DD",
              "    axisFormat %m/%Y",
              "    tickInterval 1month",
              "    todayMarker off"]
    n = 0
    tabela = []
    fase_atual = ""
    for fase, tarefa, d1, d2, estado, quem in TAREFAS:
        if tarefa is None:
            fase_atual = fase
            linhas.append(f"    section {fase}")
            continue
        n += 1
        nome = tarefa.replace(":", " -").replace("#", "")      # ":" e "#" têm significado no Mermaid
        etiqueta = ESTADO_MERMAID[estado]
        prefixo = f"{etiqueta}, " if etiqueta else ""
        linhas.append(f"    {nome} ({CURTO[quem]}) :{prefixo}t{n}, {d1.isoformat()}, {d2.isoformat()}")
        tabela.append(f"| {n} | {fase_atual} | {tarefa} | **{PESSOAS[quem][0]}** | {d1.strftime('%d/%m/%Y')} | "
                      f"{d2.strftime('%d/%m/%Y')} | {estado} |")
    contagem = {q: sum(1 for t in TAREFAS if t[5] == q) for q in PESSOAS}
    texto = "\n".join([
        "# Diagrama de Gantt — StickMania",
        "",
        "Planeamento do projeto da PAP, de setembro de 2026 a junho de 2027. O GitHub desenha o diagrama",
        "a partir do código Mermaid abaixo. As barras escuras são tarefas concluídas, as realçadas estão",
        "em curso e as claras estão planeadas.",
        "",
        "**Divisão de tarefas:** o projeto é feito em dupla. Cada tarefa diz entre parênteses quem a fez "
        f"(Vasco Andreia: {contagem[VASCO]} tarefas; Rafael da Hora Silveira: {contagem[RAFAEL]}; os dois: {contagem[DOIS]}). "
        "Na imagem do relatório ([`09_gantt.png`](diagramas/09_gantt.png)) a cor de cada barra mostra quem "
        "fez a tarefa.",
        "",
        "> Este ficheiro é gerado pelo script [`docs/diagramas/gerar_gantt.py`](diagramas/gerar_gantt.py),",
        "> o mesmo que faz a imagem do relatório ([`09_gantt.png`](diagramas/09_gantt.png)): os dois têm",
        "> sempre as mesmas datas.",
        "",
        "```mermaid",
        *linhas,
        "```",
        "",
        "## Tarefas",
        "",
        "| N.º | Fase | Tarefa | Quem fez | Início | Fim | Estado |",
        "|---|---|---|---|---|---|---|",
        *tabela,
        "",
    ])
    caminho = os.path.join(PASTA, "..", "GANTT.md")
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return os.path.normpath(caminho)


if __name__ == "__main__":
    print("Gerado:", gerar())
    print("Gerado:", gerar_mermaid())
