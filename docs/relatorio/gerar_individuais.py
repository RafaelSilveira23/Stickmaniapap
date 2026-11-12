"""gerar_individuais.py - cria o relatório individual de cada elemento do grupo.

O projeto é feito em dupla e cada aluno entrega o seu relatório, com a divisão de tarefas.
Os dois relatórios são gerados a partir do relatório conjunto (Relatorio_PAP_StickMania.docx),
que continua a ser o único que se edita à mão:

    python docs/relatorio/gerar_individuais.py          -> cria os dois .docx
    python docs/relatorio/gerar_individuais.py --pdf    -> cria também os PDF (precisa do Word)

Em cada relatório individual:
  - a capa e o resumo têm só o nome do aluno (e com quem fez o projeto);
  - a secção 3.2 fica dividida em três: o trabalho feito pelo aluno (em pormenor), o trabalho
    feito em conjunto e um resumo do trabalho feito pelo colega;
  - a secção 3.4 só tem as decisões das partes do aluno e das partes feitas em conjunto;
  - há uma secção nova, 5.4 Divisão de tarefas, com uma tabela de quem fez cada parte;
  - a conclusão tem um parágrafo com o contributo individual;
  - as figuras e as tabelas são renumeradas (e os índices atualizados).

Quando se acrescenta um parágrafo novo às secções 3.2 ou 3.4 do relatório conjunto, é preciso
dizer aqui de quem é (DONO_32 ou DONO_34); se faltar, o script pára e diz qual é.
"""
import copy
import os
import re
import subprocess
import sys

import docx
from docx.oxml.ns import qn
from docx.shared import Pt, Twips
from docx.table import Table
from docx.text.paragraph import Paragraph

PASTA = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(PASTA, "Relatorio_PAP_StickMania.docx")

V, R, C = "vasco", "rafael", "conjunto"
ALUNOS = {
    V: dict(nome="Vasco Andreia", curto="Vasco", ficheiro="Relatorio_PAP_StickMania_Vasco_Andreia"),
    R: dict(nome="Rafael da Hora Silveira", curto="Rafael", ficheiro="Relatorio_PAP_StickMania_Rafael_Silveira"),
}
COLEGA = {V: R, R: V}

# ---------------------------------------------------------------- quem fez cada parte
# Parágrafos da secção 3.2 (pelo título a negrito)
DONO_32 = {
    "Ciclo principal": C,
    "Física da bola": R, "Bola no stick": R, "Movimento e colisões dos jogadores": R, "Desarmes": R,
    "Inteligência artificial": V, "Guarda-redes": V, "Defesas sem falhas": V,
    "Ordem de desenho": R, "Câmara em perspetiva": R, "Equipamentos das equipas": R, "Animações": R,
    "Modo carreira": C, "Calendário": C, "Duas divisões, subidas e descidas": C, "Taça Europeia": C,
    "Ecrã da época": C, "Clubes novos e planteis": C, "Jogos simulados": C, "Probabilidades e forma": C, "Planteis": C,
    "Marcadores": C, "Força das equipas no jogo": C,
    "Base de dados": V,
    "Menu principal e definições": V, "Escolha das equipas por divisão": V,
    "Marcador e painel do jogo": V, "Estatísticas da partida": V, "Menu principal com mais espaço": V,
    "Gráficos": R,
    "Sons": V, "Sons no jogo": V, "Cânticos dos clubes": V, "Cânticos no jogo": V,
    "Estilo arcade": C, "Tempo de jogo e ecrã a tremer": C,
    "Remate na primeira pessoa": V, "Perspetiva na primeira pessoa": V, "Guarda-redes no remate": V,
    "Modo teste": V, "Remate em movimento": V, "Defesas no ecrã": V, "Defesas do tamanho certo": V,
    "Bloqueio do remate": V, "Aspeto do ecrã do remate": V, "Stick e bola": V, "Animação da stickada": V,
    "Animação do guarda-redes no remate": V,
    "Carreira de jogador": V, "Nota e evolução": V, "Base de dados da carreira de jogador": V,
    "A vida do jogador": V, "Eventos e atividades": V, "Como a vida mexe no hóquei": V,
    "Pessoas e relações": V, "Escolhas com consequências": V, "Bens e conquistas": V,
    "Menus com o mesmo estilo": V, "Transições entre ecrãs": V,
    "Otimização": C, "Arranque sem consola": C, "Limpeza do repositório": C,
    "Jogo online": R, "Anfitrião com autoridade": R, "Comunicação": R, "Diferenças no jogo online": R,
    "Servidor do jogo": R, "Emparelhamento aleatório e salas privadas": R,
    "Aplicação para Windows e instalador": R, "Da versão do browser à aplicação": R,
    "Stickada no jogo online": R, "Servidor na Europa": R,
}
# Figuras da secção 3.2 (número no relatório conjunto)
DONO_FIG = {10: C, 11: C, 12: C, 13: C, 14: V, 15: V, 16: V, 17: V, 18: C, 19: V,
            **{n: V for n in range(20, 30)}, **{n: R for n in range(30, 34)}}
# Parágrafos da secção 3.4
DONO_34 = {
    "Perspetiva sem mudar a física": R, "Balizas desenhadas no código": R, "Desempenho": R,
    "Pontaria com o rato": R, "Sprites": R, "Cabelo igual em todos os frames": R,
    "Bola presa e jogadores colados": R,
    "Colisões e IA com comportamentos estranhos": C, "Bola e guarda-redes": C,
    "Porquê SQLite": V, "Regras do modo carreira": C, "Porquê eliminatórias de um só jogo": C, "Porquê sons sintetizados": V, "Porquê cânticos feitos por código": V, "Flash branco no remate": V,
    "Quatro jogadores de campo": C, "Afinar a simulação com dados": C,
    "Porquê um anfitrião com autoridade": R, "Porquê uma aplicação com um servidor próprio": R, "Quem decide a stickada no online": R,
}

# Tabela da divisão de tarefas (secção 5.4)
DIVISAO = [
    ("Inteligência artificial e guarda-redes", "ai.py, goalkeeper.py", V),
    ("Menus e interface", "menu.py, ui.py, componentes.py, graficos.py", V),
    ("Sons e cânticos dos clubes", "sons.py, canticos.py", V),
    ("Base de dados (SQLite)", "carreira.py, carreira_jogador.py (parte da base de dados)", V),
    ("Carreira de jogador e vida do jogador", "carreira_jogador.py, carreira_jogador_menu.py, vida.py", V),
    ("Remate na primeira pessoa e modo teste", "remate_pov.py, pavilhao_pov.py", V),
    ("Física da bola e dos jogadores, regras", "ball.py, player.py, baliza.py", R),
    ("Gráficos, sprites e câmara em perspetiva", "camera.py, rink.py, animation.py", R),
    ("Jogo online, servidor e aplicação para Windows",
     "rede.py, online.py, online_menu.py, servidor/servidor.py, construir_app.py, instalador.py", R),
    ("Ciclo principal do jogo", "game.py, settings.py", C),
    ("Modo carreira", "carreira.py, carreira_menu.py, team.py", C),
    ("Estilo arcade", "efeitos.py", C),
    ("Análise, diagramas, testes e relatório", "docs/, ferramentas/", C),
]
QUEM = {V: "Vasco Andreia", R: "Rafael da Hora Silveira", C: "Os dois"}

# O que cada um fez, em poucas palavras (para a secção 3.2.1)
LISTA = {
    V: "a inteligência artificial dos jogadores e dos guarda-redes, a base de dados, os menus e a "
       "interface, os sons, o remate na primeira pessoa com o modo teste e a carreira de jogador com a "
       "vida do jogador",
    R: "a física da bola e dos jogadores, os gráficos com a câmara em perspetiva, o jogo online com o "
       "servidor do jogo (jogo aleatório e salas privadas) e a aplicação para Windows com o instalador",
}

# Resumo do trabalho de cada um, para o relatório do colega (secção 3.2.3)
RESUMO = {
    R: [
        ("Física e regras.", "A bola anda com o atrito do piso e ressalta nas tabelas; quando um jogador a "
         "tem, fica presa ao stick, do lado para onde ele olha. Os jogadores aceleram aos poucos até à "
         "velocidade pretendida, chocam uns com os outros sem se sobreporem e, quando um defensor choca "
         "com quem tem a bola, pode desarmá-lo, com uma probabilidade que depende dos atributos dos dois. "
         "O código está em ball.py e player.py."),
        ("Gráficos e câmara.", "A física é calculada num campo plano visto de cima e a câmara (camera.py) "
         "só muda o desenho, mostrando o rinque em perspetiva, como numa transmissão de televisão. Os "
         "jogadores e a bola são desenhados por ordem de profundidade, as cores dos equipamentos são "
         "trocadas nos sprites ao carregar a partida e as animações acompanham a velocidade de cada "
         "jogador. O rinque, as tabelas e as bancadas são desenhados uma só vez e guardados em cache, "
         "para o jogo não ficar mais lento."),
        ("Jogo online e servidor.", "Só o anfitrião simula o jogo e envia o estado ao outro jogador 30 "
         "vezes por segundo (online.py). Os dois jogos ligam-se a um servidor próprio, em Python, alojado no "
         "Render (servidor/servidor.py), que mostra quantos jogadores estão online, junta duas pessoas no "
         "jogo aleatório e cria salas privadas com um código de 4 letras."),
        ("Aplicação para Windows.", "Com o PyInstaller o jogo passou a ser um programa (StickMania.exe), "
         "que não precisa do Python, e o instalador (StickMania-Instalar.exe) instala-o, cria os atalhos e "
         "regista-o nas aplicações do Windows. Antes disso, na versão 21, o jogo esteve num site, a correr "
         "no browser, mas o grupo preferiu uma aplicação instalada."),
    ],
    V: [
        ("Inteligência artificial e guarda-redes.", "Cada jogador da IA tem um papel (avançado, médio ou "
         "defesa) e em cada frame escolhe entre atacar, defender, apoiar ou perseguir; antes de passar ou "
         "rematar verifica se a linha está livre. Os três níveis de dificuldade mudam a velocidade, o "
         "tempo de reação e a pontaria. O guarda-redes move-se sobre a linha de golo e reage ao que viu "
         "há alguns décimos de segundo, por isso não é perfeito. O código está em ai.py e goalkeeper.py."),
        ("Base de dados.", "O modo carreira e a carreira de jogador guardam tudo numa base de dados "
         "SQLite (classificação, jogos, marcadores e o jogador criado); a classificação é lida ordenada "
         "por pontos, diferença de golos e golos marcados."),
        ("Menus, interface e sons.", "O menu principal tem botões grandes com ícone e as definições "
         "(teclas, ecrã inteiro, estilo arcade e volume) ficam gravadas num ficheiro JSON. Todos os ecrãs "
         "usam as mesmas peças (painel de vidro e botões com ícone, em componentes.py), a pausa e o fim de "
         "jogo mostram o jogo desfocado por trás e há transições suaves entre ecrãs. Os 14 sons (apito, "
         "tacadas, tabela, poste, público e buzina do golo) são criados por síntese em sons.py, a partir "
         "de ondas sinusoidais e ruído, sem ficheiros de fora."),
        ("Remate na primeira pessoa.", "Ao carregar em X com a bola, a câmara passa para os olhos do "
         "jogador: aponta-se a qualquer ponto da baliza e escolhe-se a força, e os defesas que estão à "
         "frente podem bloquear o remate (remate_pov.py). O modo teste deixa treinar o remate só contra o "
         "guarda-redes."),
        ("Carreira de jogador.", "O utilizador cria o seu jogador e joga a época só com ele, com uma nota "
         "em cada jogo e propostas de outros clubes no fim. Fora do rinque tem uma vida (vida.py): forma, "
         "moral, confiança do treinador, fama, estudos e dinheiro, eventos com escolhas e consequências, "
         "pessoas com quem se relaciona e conquistas."),
    ],
}

CONTRIBUTO = {
    V: "No StickMania, o Vasco Andreia programou a inteligência artificial dos jogadores e dos "
       "guarda-redes, a base de dados, os menus e a interface, os sons, o remate na primeira pessoa com o "
       "modo teste e a carreira de jogador com a vida do jogador. Nestas partes, as maiores dificuldades "
       "foram pôr a IA a jogar de forma credível sem ser perfeita (tempo de reação e erros do "
       "guarda-redes), a perspetiva e o bloqueio dos defesas no ecrã do remate, e criar os sons só com "
       "matemática. O modo carreira, o estilo arcade, a análise, os testes e o relatório foram feitos em "
       "conjunto com o Rafael da Hora Silveira.",
    R: "No StickMania, o Rafael da Hora Silveira programou a física da bola e dos jogadores (atrito, "
       "ressaltos, colisões e desarmes), os gráficos, os sprites e a câmara em perspetiva, o jogo online "
       "com o servidor do jogo (jogo aleatório, jogadores online e salas privadas) e a aplicação para "
       "Windows com o instalador. Nestas partes, as maiores dificuldades foram as colisões (a bola a "
       "atravessar as tabelas e os jogadores colados uns aos outros), a câmara em perspetiva sem mudar a "
       "física e pôr dois computadores a ver o mesmo jogo pela internet. O modo carreira, o estilo arcade, a análise, os testes e o relatório foram feitos em "
       "conjunto com o Vasco Andreia.",
}


# ---------------------------------------------------------------- ajudas
def texto(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def procurar(d, inicio, ultimo=False):
    ps = [p for p in d.paragraphs if p.text.startswith(inicio)]
    if not ps:
        raise SystemExit(f"Não encontrei no relatório o parágrafo que começa por «{inicio}»")
    return ps[-1] if ultimo else ps[0]


def titulo(p):
    """Título a negrito no início do parágrafo («Sons.», «Modo teste.»), ou None."""
    if p.runs and p.runs[0].bold and ". " in p.text:
        return p.text.split(". ")[0].strip()
    return None


def novo_paragrafo(modelo, depois, partes):
    """Copia o parágrafo-modelo para depois de «depois» e põe-lhe o texto (uma parte por run)."""
    n = copy.deepcopy(modelo._p)
    for b in n.findall(qn("w:bookmarkStart")) + n.findall(qn("w:bookmarkEnd")):
        n.remove(b)
    depois.addnext(n)
    p = Paragraph(n, modelo._parent)
    runs = p.runs                        # ficam os últimos runs (o primeiro pode ser o título a negrito)
    for r in runs[:max(0, len(runs) - len(partes))]:
        r._r.getparent().remove(r._r)
    for r, t in zip(p.runs, partes):
        r.text = t
    return p


class Cursor:
    """Vai inserindo elementos uns a seguir aos outros."""

    def __init__(self, el):
        self.el = el

    def por(self, el):
        self.el.addnext(el)
        self.el = el

    def par(self, modelo, partes):
        p = novo_paragrafo(modelo, self.el, partes)
        self.el = p._p
        return p


def elementos_entre(inicio_el, fim_el):
    lista, el = [], inicio_el.getnext()
    while el is not fim_el:
        lista.append(el)
        el = el.getnext()
    while lista and lista[-1].tag == qn("w:p") and not texto(lista[-1]).strip() \
            and not lista[-1].findall(".//" + qn("w:drawing")):
        lista.pop()                      # linhas vazias antes do título seguinte ficam onde estão
    return lista


# ---------------------------------------------------------------- relatório de um aluno
def gerar(aluno):
    a, b = ALUNOS[aluno], ALUNOS[COLEGA[aluno]]
    d = docx.Document(BASE)
    modelo_txt = procurar(d, "Porquê SQLite.")          # título a negrito + texto
    modelo_h2 = procurar(d, "5.3  Controlo de versões")
    modelo_h3 = procurar(d, "2.3.1  Técnicas")

    # Capa, resumo e intervenientes
    for p in d.paragraphs[:60]:
        if p.text.strip() in ("Rafael da Hora Silveira", "Rafael da Hora Silveira e Vasco Andreia"):
            dupla = "Vasco" in p.text
            p.runs[0].text = a["nome"]
            for r in p.runs[1:]:
                r.text = ""
            if dupla:                        # segunda capa: diz com quem foi feito o projeto
                data = Paragraph(p._p.getnext(), p._parent)
                novo_paragrafo(data, p._p, [f"Projeto realizado em dupla com {b['nome']}"])
    resumo = procurar(d, "Este relatório descreve o StickMania")
    novo_paragrafo(resumo, resumo._p, [
        f"Este é o relatório individual de {a['nome']}. O StickMania foi desenvolvido em dupla com "
        f"{b['nome']}: a divisão de tarefas está na secção 5.4 e o capítulo 3 descreve em pormenor as "
        f"partes feitas por {a['nome']}."])
    est = procurar(d, "Depois desta introdução, o capítulo 2")
    est.runs[-1].text = est.runs[-1].text.replace(
        "(cronograma, riscos e controlo de versões)", "(cronograma, riscos, controlo de versões e divisão de tarefas)")
    est.runs[-1].text += (f" A secção 3.2 está dividida em três partes: o trabalho feito por {a['nome']}, o "
                          f"trabalho feito em conjunto e um resumo do trabalho feito por {b['nome']}.")
    equipa = procurar(d, "–\tEquipa de desenvolvimento")
    equipa.runs[-1].text += " A divisão de tarefas está na secção 5.4."

    # Secção 3.2: o trabalho do aluno, o trabalho em conjunto e o resumo do colega
    h32, h33 = procurar(d, "3.2  Programação", True), procurar(d, "3.3  Integração", True)
    intro = h32._p.getnext()
    grupos = {V: [], R: [], C: []}
    dono, anterior = None, None
    for el in elementos_entre(intro, h33._p):
        p = Paragraph(el, h32._parent) if el.tag == qn("w:p") else None
        t = titulo(p) if p is not None else None
        fig = re.match(r"Figura (\d+) –", p.text) if p is not None else None
        if t:
            if t not in DONO_32:
                raise SystemExit(f"Parágrafo novo na secção 3.2: «{t}». Diz de quem é em DONO_32.")
            dono = DONO_32[t]
        if fig:
            n = int(fig.group(1))
            if n not in DONO_FIG:
                raise SystemExit(f"Figura nova na secção 3.2: Figura {n}. Diz de quem é em DONO_FIG.")
            grupos[dono].remove(anterior)             # a imagem vem antes da legenda
            grupos[DONO_FIG[n]] += [anterior, el]
        elif dono is None:
            raise SystemExit("A secção 3.2 tem de começar por um parágrafo com título a negrito")
        else:
            grupos[dono].append(el)
        anterior = el
    for lista in grupos.values():
        for el in lista:
            el.getparent().remove(el)

    cur = Cursor(intro)
    cur.par(modelo_h3, [f"3.2.1  Trabalho feito por {a['nome']}"])
    cur.par(modelo_txt, [f"Esta secção descreve em pormenor as partes do jogo programadas por {a['nome']}: "
                         f"{LISTA[aluno]}."])
    for el in grupos[aluno]:
        cur.por(el)
    cur.par(modelo_h3, ["3.2.2  Trabalho feito em conjunto"])
    cur.par(modelo_txt, ["Estas partes foram feitas pelos dois elementos do grupo: o ciclo principal do jogo, "
                         "o modo carreira, o estilo arcade, a otimização e a organização do projeto."])
    for el in grupos[C]:
        cur.por(el)
    cur.par(modelo_h3, [f"3.2.3  Trabalho feito por {b['nome']} (resumo)"])
    cur.par(modelo_txt, [f"As partes seguintes foram feitas por {b['nome']}. Estão aqui só resumidas, para se "
                         f"perceber o jogo completo; estão descritas em pormenor no relatório de {b['nome']}."])
    for t, corpo in RESUMO[COLEGA[aluno]]:
        cur.par(modelo_txt, [t + " ", corpo])

    # Secção 3.4: só as decisões do aluno e as feitas em conjunto
    h34, h4 = procurar(d, "3.4  Decisões", True), procurar(d, "4.  Testes", True)
    for el in elementos_entre(h34._p, h4._p):
        t = titulo(Paragraph(el, h34._parent)) if el.tag == qn("w:p") else None
        if t is None:
            continue
        if t not in DONO_34:
            raise SystemExit(f"Parágrafo novo na secção 3.4: «{t}». Diz de quem é em DONO_34.")
        if DONO_34[t] == COLEGA[aluno]:
            el.getparent().remove(el)
        elif aluno == V and t == "Colisões e IA com comportamentos estranhos":
            # o parágrafo anterior (bola presa e jogadores colados) é do Rafael e não está neste relatório
            for r in Paragraph(el, h34._parent).runs:
                r.text = r.text.replace("Mesmo depois disso, os jogadores",
                                        "Mesmo depois de corrigidas as colisões básicas (bola a atravessar as "
                                        "tabelas e jogadores presos uns nos outros), os jogadores")
    novo_paragrafo(modelo_txt, h34._p, [
        f"Seguem-se as decisões e as dificuldades das partes feitas por {a['nome']} e das partes feitas em "
        f"conjunto. As das partes feitas por {b['nome']} estão no relatório de {b['nome']}."])

    # Secção 5.4: divisão de tarefas, com uma tabela
    h53, h6 = procurar(d, "5.3  Controlo de versões", True), procurar(d, "6. Conclusão", True)
    fim53 = elementos_entre(h53._p, h6._p)[-1]
    cur = Cursor(fim53)
    cur.par(modelo_h2, ["5.4  Divisão de tarefas"])
    # Número da figura do Gantt no relatório conjunto (é renumerada depois, como as outras)
    legenda_gantt = [p.text for p in d.paragraphs if re.match(r"Figura \d+ – Diagrama de Gantt", p.text)][-1]
    n_gantt = re.match(r"Figura (\d+)", legenda_gantt).group(1)
    cur.par(modelo_txt, [
        "O projeto foi feito em dupla. O trabalho foi dividido por partes do jogo, cada uma com os seus "
        "módulos, para cada elemento poder trabalhar sem estragar o trabalho do outro (Tabela 99). A base do "
        "jogo, o modo carreira, o estilo arcade, a análise, os diagramas, os testes e o relatório foram feitos "
        "pelos dois. As alterações de cada um foram juntadas no repositório do GitHub. O diagrama de Gantt "
        f"(Figura {n_gantt}, na secção 5.1) também mostra quem fez cada tarefa e quando."])
    leg_modelo = procurar(d, "Tabela 10 – Cronograma", True)
    cur.par(leg_modelo, ["Tabela 99 – Divisão de tarefas entre os dois elementos do grupo"])
    tab_modelo = [t for t in d.tables if t.rows[0].cells[0].text == "Período"][0]
    tbl = copy.deepcopy(tab_modelo._tbl)
    cur.por(tbl)
    linhas = tbl.findall(qn("w:tr"))
    for tr in linhas[2:]:
        tbl.remove(tr)
    larguras = [2900, 4200, 1600]
    for gc, w in zip(tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol")), larguras):
        gc.set(qn("w:w"), str(w))
    dados = linhas[1]
    tbl.remove(dados)
    for parte, modulos, quem in DIVISAO:
        tr = copy.deepcopy(dados)
        tbl.append(tr)
    tabela = Table(tbl, h53._parent)
    for i, linha in enumerate(tabela.rows):
        valores = ("Parte do projeto", "Módulos (ficheiros)", "Quem fez") if i == 0 else DIVISAO[i - 1][:2] + (
            QUEM[DIVISAO[i - 1][2]],)
        for c, txt, w in zip(linha.cells, valores, larguras):
            c.width = Twips(w)
            rs = c.paragraphs[0].runs
            for r in rs[1:]:
                r._r.getparent().remove(r._r)
            rs[0].text = txt
            if i > 0 and DIVISAO[i - 1][2] == aluno:
                rs[0].bold = True
    depois = cur.par(modelo_txt, [
        f"Na Tabela 99 estão a negrito as partes feitas por {a['nome']}. Neste relatório, essas partes estão "
        f"descritas em pormenor na secção 3.2.1, as feitas em conjunto na secção 3.2.2, e as feitas por "
        f"{b['nome']} estão resumidas na secção 3.2.3."])
    depois.paragraph_format.space_before = Pt(12)          # não fica colado à tabela
    idx_tab = procurar(d, "Tabela 11 – Gestão de riscos")
    novo_paragrafo(idx_tab, idx_tab._p, ["Tabela 99 – Divisão de tarefas"])

    # Conclusão: contributo individual
    concl = procurar(d, "O projeto permitiu aplicar")
    novo_paragrafo(modelo_txt, concl._p, ["Contributo individual. ", CONTRIBUTO[aluno]])

    renumerar(d, "Figura")
    renumerar(d, "Tabela")
    caminho = os.path.join(PASTA, a["ficheiro"] + ".docx")
    d.save(caminho)
    return caminho


def renumerar(d, tipo):
    """Numera as figuras (ou tabelas) pela ordem em que aparecem e corrige as referências e o índice."""
    corpo = d.element.body
    intro = procurar(d, "1.  Introdução")._p
    todos = list(corpo.iter(qn("w:p")))
    i0 = todos.index(intro)
    padrao = re.compile(tipo + r" (\d+) –")
    legendas = [int(m.group(1)) for el in todos[i0:] if (m := padrao.match(texto(el)))]
    mapa = {velho: novo for novo, velho in enumerate(legendas, 1)}

    def trocar(m):
        n = int(m.group(1))
        if n not in mapa:
            raise SystemExit(f"Ficou uma referência à {tipo} {n}, que não existe neste relatório")
        return f"{tipo} {mapa[n]}"

    # Índice (antes da introdução): apaga as entradas que saíram e ordena as outras
    entradas = [el for el in todos[:i0] if padrao.match(texto(el))]
    if entradas:
        antes = entradas[0].getprevious()
        for el in entradas:
            el.getparent().remove(el)
        entradas = [el for el in entradas if int(padrao.match(texto(el)).group(1)) in mapa]
        entradas.sort(key=lambda el: mapa[int(padrao.match(texto(el)).group(1))])
        for el in entradas:
            antes.addnext(el)
            antes = el
    ref = re.compile(tipo + r" (\d+)")
    for el in corpo.iter(qn("w:p")):
        p = Paragraph(el, None)
        if re.search(tipo + r"s \d", p.text):
            raise SystemExit(f"Referência no plural ({tipo}s ...) não suportada: {p.text[:60]}")
        if not ref.search(p.text):
            continue
        esperado = ref.sub(trocar, p.text)
        for r in p.runs:
            r.text = ref.sub(trocar, r.text)
        if p.text != esperado:
            raise SystemExit(f"Referência partida em vários pedaços: {p.text[:60]}")


def para_pdf(caminho):
    """Atualiza o índice e cria o PDF com o Word (só no Windows, com o Word instalado)."""
    pdf = caminho[:-5] + ".pdf"
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{caminho}'); "
          f"foreach ($t in $d.TablesOfContents) {{ $t.Update() }}; $null = $d.Fields.Update(); $d.Save(); "
          f"$d.ExportAsFixedFormat('{pdf}', 17); $d.Close(); $w.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return pdf


if __name__ == "__main__":
    for aluno in (V, R):
        c = gerar(aluno)
        print("Criado", c)
        if "--pdf" in sys.argv:
            print("Criado", para_pdf(c))
