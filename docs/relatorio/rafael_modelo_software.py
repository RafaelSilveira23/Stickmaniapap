# -*- coding: utf-8 -*-
"""
rafael_modelo_software.py - passa o relatório individual de Rafael da Hora Silveira para a estrutura
do modelo de SOFTWARE da escola (o relatório conjunto seguia o modelo de hardware).

É chamado pelo gerar_individuais.py, só para o relatório do Rafael, antes de numerar as figuras e as
tabelas. O que faz (pedido da professora):
  - tira as secções de hardware (2.5 Projeto do hardware, 2.5.1 a 2.5.3, 3.1 Montagem do hardware,
    3.3 Integração hardware-software e 4.2 Ensaios e calibração) e põe as secções do modelo de
    software: 2.5 Prototipagem e desenho da interface, 2.6 Arquitetura da solução e tecnologias,
    3.1 Ambiente de desenvolvimento, 3.2 Estrutura da aplicação e da base de dados, 3.3 Funcionalidades
    desenvolvidas e 4.2 Testes de usabilidade com utilizadores;
  - escreve a 5.2 Gestão de riscos (os riscos reais do projeto e o que se fez para os reduzir);
  - passa para anexo o pormenor da 3.2.1 (Anexo D) e a tabela completa dos testes (Anexo E);
  - corrige a orientadora na subcapa e nos agradecimentos.
"""
import copy
import re

from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

W_P, W_T, W_R, W_TBL = qn("w:p"), qn("w:t"), qn("w:r"), qn("w:tbl")


# ---------------------------------------------------------------------- ajudas
def texto(el) -> str:
    return "".join(t.text or "" for t in el.iter(W_T))


class Corpo:
    """Procura e mexe nos parágrafos e tabelas do corpo do relatório (a partir da Introdução)."""

    def __init__(self, d):
        self.d = d
        self.body = d.element.body
        todos = list(self.body.iter(W_P))
        def estilo(p):
            st = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
            return st.get(qn("w:val")) if st is not None else ""
        # o título a sério (não a linha do índice, que também começa por «1.  Introdução»)
        self.intro = next(p for p in todos if texto(p).startswith("1.  Introdução")
                          and estilo(p) in ("Ttulo1", "Heading1"))

    def depois_intro(self):
        el = self.intro
        while el is not None:
            yield el
            el = el.getnext()

    def achar(self, inicio: str, contem: bool = False, antes_intro: bool = False):
        fonte = self.body.iter(W_P) if antes_intro else self.depois_intro()
        achados = [el for el in fonte if el.tag == W_P and
                   ((inicio in texto(el)) if contem else texto(el).startswith(inicio))]
        if len(achados) != 1:
            raise SystemExit(f"rafael_modelo_software: procurei «{inicio}» e encontrei {len(achados)}")
        return achados[0]

    def tabela_depois(self, legenda_el):
        el = legenda_el.getnext()
        while el is not None and el.tag != W_TBL:
            el = el.getnext()
        return el


def apagar(*els):
    for el in els:
        if el is not None and el.getparent() is not None:
            el.getparent().remove(el)


def apagar_vazios_depois(el, n=3):
    """Apaga até n parágrafos vazios logo a seguir a el (os espaços que sobram ao tirar secções)."""
    for _ in range(n):
        seg = el.getnext()
        if seg is not None and seg.tag == W_P and not texto(seg).strip() and not list(seg.iter(qn("w:drawing"))):
            apagar(seg)
        else:
            break


def mudar_titulo(el, novo: str):
    """Muda o texto de um título, mantendo o «◆ MADS» se existir."""
    ts = list(el.iter(W_T))
    i_mads = next((i for i, t in enumerate(ts) if "◆" in (t.text or "")), len(ts))
    ts[0].text = novo + ("   " if i_mads < len(ts) else "")
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:i_mads]:
        t.text = ""


def copiar_titulo(modelo, depois, novo: str):
    el = copy.deepcopy(modelo)
    for b in list(el.iter(qn("w:bookmarkStart"))) + list(el.iter(qn("w:bookmarkEnd"))):
        b.getparent().remove(b)
    mudar_titulo(el, novo)
    depois.addnext(el)
    return el


def novo_par(modelo, depois, partes, *, antes=False):
    """
    Parágrafo novo com o formato de 'modelo'. partes: lista de textos; os que começam por «**»
    ficam a negrito (ex.: ["**Título. ", "corpo"]).
    """
    el = copy.deepcopy(modelo)
    rpr = None
    for r in el.iter(W_R):
        rpr = r.find(qn("w:rPr"))
        break
    for ch in list(el):
        if ch.tag != qn("w:pPr"):
            el.remove(ch)
    p = Paragraph(el, None)
    for parte in partes:
        negrito = parte.startswith("**")
        r = p.add_run(parte[2:] if negrito else parte)
        if rpr is not None:
            novo_rpr = copy.deepcopy(rpr)
            for b in novo_rpr.findall(qn("w:b")) + novo_rpr.findall(qn("w:bCs")):
                novo_rpr.remove(b)
            r._r.insert(0, novo_rpr)
        r.bold = True if negrito else None
    if antes:
        depois.addprevious(el)
    else:
        depois.addnext(el)
    return el


def trocar_texto(el, velho: str, novo: str):
    """Troca um pedaço de texto. Se estiver partido em várias linhas (runs), junta o texto todo na primeira."""
    for t in el.iter(W_T):
        if t.text and velho in t.text:
            t.text = t.text.replace(velho, novo)
            return
    ts = list(el.iter(W_T))
    tudo = "".join(t.text or "" for t in ts)
    if velho in tudo and ts:
        ts[0].text = tudo.replace(velho, novo)
        ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for t in ts[1:]:
            t.text = ""
        return
    raise SystemExit(f"rafael_modelo_software: não encontrei «{velho[:50]}» em «{texto(el)[:60]}»")


def mover(els, depois):
    """Move uma lista de elementos (pela ordem) para a seguir a 'depois'. Devolve o último."""
    for el in els:
        depois.addnext(el)
        depois = el
    return depois


def bloco(inicio_el, fim_el):
    """Elementos de inicio_el (incluído) até fim_el (excluído)."""
    out, el = [], inicio_el
    while el is not None and el is not fim_el:
        out.append(el)
        el = el.getnext()
    return out


def num_legenda(el) -> int:
    return int(re.match(r"(?:Figura|Tabela) (\d+)", texto(el)).group(1))


def legenda_com_figura(c: Corpo, legenda: str):
    """[parágrafo da imagem, legenda] de uma figura (a imagem está no parágrafo antes da legenda)."""
    leg = c.achar(legenda, contem=True)
    img = leg.getprevious()
    assert list(img.iter(qn("w:drawing"))), legenda
    return [img, leg]


# ---------------------------------------------------------------------- textos novos
RESUMO_RAFAEL = [
    ("Física e movimento. ", "A bola perde velocidade com o atrito do piso e ressalta nas tabelas; os jogadores aceleram "
     "e travam aos poucos, chocam uns com os outros e disputam a bola, e ganhar um desarme depende da defesa de um e da "
     "velocidade do outro."),
    ("Gráficos e câmara em perspetiva. ", "O jogo é calculado num campo plano visto de cima e só o desenho passa pela "
     "câmara, que estreita o rinque ao fundo como na televisão. Os equipamentos são pintados com as cores de cada "
     "clube e o rinque é desenhado uma só vez e guardado, para o jogo não ficar lento."),
    ("Remate na primeira pessoa e modo teste. ", "Com a tecla X a câmara passa para os olhos do jogador: aponta-se, "
     "carrega-se a força e remata-se (a stickada). Os defesas que estão à frente podem bloquear o remate e o "
     "guarda-redes defende consoante a mira, a força e a distância. O modo teste serve para treinar os remates, os "
     "passes e as fintas."),
    ("Faltas, cartões, fintas e guarda-redes. ", "Há livres, penáltis e livres diretos, cartões amarelo, azul e "
     "vermelho, duas fintas (o corte, com V, e a roleta, com F) e um guarda-redes que sai da baliza e se atira à bola."),
    ("Estilo arcade, repetição e comando. ", "Os golos têm festa e câmara lenta e, a seguir, a repetição do lance. "
     "Também se pode jogar com um comando e a dois no mesmo computador."),
    ("Jogo online e servidor. ", "Um dos computadores (o anfitrião) calcula o jogo e o outro envia as teclas e recebe o "
     "estado do jogo 30 vezes por segundo, através de um servidor nosso, na Europa. Há jogo aleatório, salas privadas "
     "com código e desafios pela alcunha; cada jogador escolhe a sua equipa e, se a internet falhar a meio, o jogo "
     "pára e volta a ligar sozinho."),
    ("Contas, nuvem e ranking. ", "A conta é só uma alcunha e uma palavra-passe, sem email. As carreiras e as "
     "conquistas ficam guardadas na nuvem e os jogos online contam para um ranking com pontos. Quem cria uma conta "
     "nova tem de fazer o tutorial."),
    ("Aplicação para Windows e site. ", "O jogo instala-se como uma aplicação normal, com um instalador feito por nós, e "
     "descarrega-se de um site publicado no GitHub Pages. A imagem fica nítida também em ecrãs com o zoom do Windows."),
]

TECNOLOGIAS = [
    ("Python 3 e pygame-ce: ", "linguagem que já conhecíamos e biblioteca simples para jogos 2D (janela, desenho, "
     "teclado, rato, comando e som)."),
    ("SQLite: ", "base de dados num só ficheiro, sem precisar de servidor, para o modo carreira e a carreira de jogador."),
    ("WebSocket: ", "ligação do jogo ao servidor que funciona como um pedido normal a um site, por isso passa pelas "
     "proteções da rede e não é preciso abrir portas."),
    ("Render e Neon: ", "alojamento gratuito na Europa para o servidor do jogo (Render) e para a base de dados das "
     "contas (Postgres, na Neon)."),
    ("PyInstaller: ", "junta o jogo, o Python e o pygame-ce num programa, para quem joga não precisar de instalar nada."),
]

ESTRUTURA = [
    ("partida: ", "bola, jogadores, guarda-redes, IA, faltas, fintas, câmara, remate na primeira pessoa, repetição e "
     "comando;"),
    ("modos: ", "modo carreira, carreira de jogador, tutorial, dois jogadores e conquistas;"),
    ("clubes: ", "equipas, plantéis, emblemas e cores dos equipamentos;"),
    ("ecras: ", "menus, painel do jogo e peças da interface (botões, ícones e fontes);"),
    ("multijogador: ", "ligação ao servidor, jogo online e contas;"),
    ("som: ", "efeitos sonoros e cânticos dos clubes;"),
    ("recursos: ", "imagens, sons, emblemas e desenhos dos jogadores."),
]

USABILIDADE = [
    ("Ecrã da conta. ", "Achámos o ecrã de criar conta confuso: abria em «Entrar» e o «Criar conta» passava "
     "despercebido. Passou a ter dois separadores e as regras da alcunha e da palavra-passe são verificadas enquanto "
     "se escreve."),
    ("Jogo online. ", "A jogar em dois computadores, o convidado sentia o jogo aos puxões e o anfitrião escolhia as "
     "duas equipas. Medimos o atraso e reduzimo-lo, e cada jogador passou a escolher a sua equipa."),
    ("Desafios pela alcunha. ", "Também a jogar em dois computadores, vimos que o convite para jogar não chegava ao "
     "amigo. Encontrámos a causa e o convite passou a aparecer também no menu principal."),
    ("Ecrãs com zoom. ", "Num portátil com o zoom do Windows a 200 %, os menus e as letras apareciam em blocos e o "
     "círculo do botão SAIR saía fora do botão. As duas coisas foram corrigidas."),
]

RISCOS = [
    ("Atraso no jogo online", "Alta", "Alto",
     "Anfitrião com autoridade, previsão do jogador do convidado, servidor na Europa e mensagens enviadas logo"),
    ("Internet a falhar a meio de um jogo online", "Média", "Alto",
     "O servidor guarda o jogo 45 s e o jogo volta a ligar sozinho"),
    ("Servidor gratuito a «adormecer»", "Alta", "Médio", "Aviso «a acordar o servidor» e espera até 90 s"),
    ("Câmara em perspetiva estragar a física e a IA", "Média", "Alto",
     "Física e IA num campo plano; só o desenho passa pela câmara; testes de ida e volta"),
    ("Perder o progresso ao mudar de computador", "Média", "Alto",
     "Carreiras e conquistas na nuvem; cópia do ficheiro antes de o substituir"),
    ("O Windows bloquear o instalador", "Alta", "Médio",
     "Explicação no site e no README; publicação na Microsoft Store em preparação"),
    ("Perder código ou uma alteração estragar o que funcionava", "Média", "Alto",
     "Tudo no GitHub; testes automáticos antes de cada versão; reverter com o Git"),
    ("Atrasos no cronograma", "Média", "Alto", "Versões pequenas e jogáveis; prioridades definidas"),
    ("Jogo lento em computadores fracos", "Baixa", "Médio", "Rinque desenhado uma só vez; medir os FPS"),
    ("Uso dos símbolos dos clubes", "Baixa", "Médio", "Uso apenas educativo, sem fins comerciais"),
    ("Ausência de um elemento do grupo", "Baixa", "Médio", "Código em módulos e repositório partilhado"),
]

RISCOS_REAIS = [
    ("Jogo online. ", "Foi o risco que mais vezes aconteceu. Primeiro, o convidado sentia o jogador «preso»: a "
     "mensagem demorava meio segundo a ir e voltar porque o servidor estava nos Estados Unidos, e mudámo-lo para a "
     "Europa. Depois medimos que a ligação juntava as mensagens pequenas antes de as enviar e desligámos isso (90 % das "
     "mensagens passaram a chegar em menos de 96 ms, em vez de 208 ms). Mais tarde, para a internet a falhar, o jogo "
     "passou a parar e a voltar a ligar sozinho em vez de acabar, e para os convites que se perdiam o servidor passou "
     "a mandá-los só para a ligação do jogo."),
    ("Câmara em perspetiva. ", "Passar o jogo todo para 3D podia estragar a física, as colisões e a IA, que já "
     "funcionavam. Para reduzir esse risco, a física continuou num campo plano e só o desenho passou pela câmara; "
     "para a pontaria com o rato escrevemos a conta inversa da câmara e testámos que um ponto do campo passado para o "
     "ecrã e de volta dá exatamente o mesmo ponto."),
    ("Progresso na nuvem. ", "Nos testes com dois computadores, um deles enviou a sua lista antiga de conquistas antes "
     "de receber a da nuvem e apagou lá as do outro. Passámos a juntar as listas, no jogo e no servidor, em vez de as "
     "substituir, e antes de trazer uma carreira da nuvem o jogo guarda uma cópia da que estava no computador."),
    ("Instalação no Windows. ", "Como o jogo não tem assinatura digital paga, o Windows pode mostrar «O Windows "
     "protegeu o computador» ou bloquear o instalador. Explicámos no site e no README o que fazer e estamos a preparar "
     "a publicação na Microsoft Store."),
]


# ---------------------------------------------------------------------- transformação
def aplicar(d):
    c = Corpo(d)
    h1_modelo = c.achar("3.  Implementação")
    h2_simples = c.achar("3.1  Montagem do hardware")
    h2_mads = c.achar("5.2  Gestão de riscos")
    par_negrito = c.achar("Física da bola.")
    par_simples = c.achar("Fizemos dois tipos de testes")
    marcador = c.achar("Linguagem: Python", contem=True)
    legenda_modelo = c.achar("– Gestão de riscos", contem=True)

    # ---- subcapa e agradecimentos: a orientadora é a professora Cristina Paes
    sub = c.achar("Sob o acompanhamento do Dr. Fernando Filipe", antes_intro=True)
    trocar_texto(sub, "Sob o acompanhamento do Dr. Fernando Filipe", "Sob o acompanhamento da Professora Cristina Paes")
    agr = c.achar("Agradecemos ao nosso orientador", antes_intro=True)
    trocar_texto(agr, "Agradecemos ao nosso orientador, Dr. Fernando Filipe, e à professora Cristina Paes pelo",
                 "Agradecemos à nossa orientadora, professora Cristina Paes, pelo")

    orient = c.achar("Orientadores: Dr. Fernando Filipe", contem=True)
    novo_par(marcador, orient, ["–\t", "**Orientadora: ", "professora Cristina Paes, que acompanhou e validou o "
                                                          "trabalho."])
    apagar(orient)

    # ---- 1.5 Estrutura do relatório
    est = c.achar("Depois desta introdução, o capítulo 2")
    novo_par(par_simples, est, [
        "Depois desta introdução, o capítulo 2 faz a análise do sistema: o problema, os intervenientes, os requisitos, "
        "a modelação com diagramas (casos de uso, classes, modelo de dados, estados e fluxogramas), a prototipagem e "
        "a arquitetura com as tecnologias escolhidas. O capítulo 3 descreve a implementação: as ferramentas, a "
        "estrutura da aplicação e da base de dados, as funcionalidades e as dificuldades ultrapassadas. O capítulo 4 "
        "apresenta o plano de testes, os testes com utilizadores e os resultados. O capítulo 5 trata da gestão do "
        "projeto (cronograma, riscos, controlo de versões e divisão de tarefas). Por fim, o capítulo 6 apresenta a "
        "conclusão e o capítulo 7 os anexos, onde estão o pormenor das funcionalidades (Anexo D) e a lista completa "
        "dos testes (Anexo E). A secção 3.3 está dividida em três partes: o trabalho feito por Rafael da Hora "
        "Silveira, o trabalho feito em conjunto e um resumo do trabalho feito por Vasco Andreia."])
    apagar(est)

    # ---- 2.x: títulos do modelo de software
    mudar_titulo(c.achar("2.1  Descrição do problema"), "2.1  Descrição do problema e do sistema atual")
    mudar_titulo(c.achar("2.2  Intervenientes"), "2.2  Intervenientes (stakeholders)")
    mudar_titulo(c.achar("2.3.2  Requisitos funcionais"), "2.3.2  Requisitos funcionais")
    mudar_titulo(c.achar("2.3.3  Requisitos não funcionais"), "2.3.3  Requisitos não funcionais")
    mudar_titulo(c.achar("2.4.1  Cenários de utilização"), "2.4.1  Diagrama de casos de uso e descrição dos principais")
    h242 = c.achar("2.4.2  Arquitetura do sistema")
    mudar_titulo(h242, "2.4.2  Modelo de dados (E-R) e diagrama de classes")
    mudar_titulo(c.achar("2.4.3  Modelação comportamental"),
                 "2.4.3  Modelação comportamental (diagramas de atividades e máquina de estados)")

    # A arquitetura sai da 2.4.2 (vai para a nova 2.6)
    arq_par = c.achar("O modelo «sensores → controlo → atuadores»")
    arq_fig = legenda_com_figura(c, "– Arquitetura do sistema em blocos")
    for el in [arq_par] + arq_fig:
        el.getparent().remove(el)

    # ---- tirar a 2.5 Projeto do hardware (a tabela dos requisitos vai para a 2.6)
    h25 = c.achar("2.5  Projeto do hardware")
    leg_req = c.achar("– Requisitos de hardware e software para correr o jogo", contem=True)
    tab_req = c.tabela_depois(leg_req)
    h26 = c.achar("2.6  Prototipagem")
    for el in bloco(h25, h26):
        if el is not leg_req and el is not tab_req:
            apagar(el)
    leg_req.getparent().remove(leg_req)
    tab_req.getparent().remove(tab_req)

    # 2.6 Prototipagem passa a 2.5 Prototipagem e desenho da interface
    mudar_titulo(h26, "2.5  Prototipagem e desenho da interface")
    proto = c.achar("Em vez de um protótipo físico, foram feitos protótipos jogáveis do próprio jogo.")
    trocar_texto(proto, "Em vez de um protótipo físico, foram feitos protótipos jogáveis do próprio jogo.",
                 "Foram feitos protótipos jogáveis do próprio jogo.")
    fig_jogo = c.achar("– O StickMania durante uma partida", contem=True)
    # os controlos (antes na 3.3 Integração hardware-software) fazem parte do desenho da interface
    leg_ctrl = c.achar("– Controlos do jogo", contem=True)
    tab_ctrl = c.tabela_depois(leg_ctrl)
    h33_int = c.achar("3.3  Integração hardware")
    int_par = h33_int.getnext()
    p_ctrl = novo_par(par_simples, fig_jogo, [
        "O jogo controla-se com o teclado e o rato ou com um comando (Xbox, PlayStation ou compatível) e desenha uma "
        f"imagem de 1280×720, 60 vezes por segundo, ampliada para o tamanho do ecrã. A Tabela {num_legenda(leg_ctrl)} "
        "mostra os controlos; também estão sempre nas Definições e o tutorial ensina-os."])
    leg_ctrl.getparent().remove(leg_ctrl)
    tab_ctrl.getparent().remove(tab_ctrl)
    mover([leg_ctrl, tab_ctrl], p_ctrl)
    for el in bloco(h33_int, c.achar("3.4  Decisões técnicas")):
        if el is not h33_int:
            apagar(el)
    apagar(h33_int)
    del int_par

    # ---- nova 2.6 Arquitetura da solução e tecnologias escolhidas (antes do capítulo 3)
    h3 = c.achar("3.  Implementação")
    ant = h3.getprevious()
    h26n = copiar_titulo(h2_simples, ant, "2.6  Arquitetura da solução e tecnologias escolhidas")
    p = novo_par(par_simples, h26n, [
        "A solução tem três partes: o jogo, que corre no computador de cada jogador; o servidor do jogo, na internet, "
        "que liga os jogadores e guarda as contas numa base de dados; e o site, de onde se descarrega o instalador. "
        "Dentro do jogo, a entrada (teclado, rato e comando) passa pelo ciclo principal, que atualiza a física, a IA e "
        "as regras e depois desenha o ecrã e toca os sons. O código está organizado em pastas por tema (partida, "
        "modos, ecrãs, multijogador, som e clubes), descritas na secção 3.2, e cada bloco da figura corresponde a uma "
        "pasta ou a poucos ficheiros, o que permite alterar uma parte sem estragar as outras."])
    p = mover(arq_fig, p)
    p = novo_par(par_simples, p, ["As tecnologias foram escolhidas assim:"])
    for titulo, corpo in TECNOLOGIAS:
        p = novo_par(marcador, p, ["–\t", "**" + titulo, corpo])
    p = novo_par(par_simples, p, [f"Para correr o jogo é preciso o equipamento da Tabela {num_legenda(leg_req)}."])
    mover([leg_req, tab_req], p)

    # ---- capítulo 3
    mudar_titulo(h3, "3.  Implementação da solução")
    h31 = c.achar("3.1  Montagem do hardware")
    mudar_titulo(h31, "3.1  Ambiente de desenvolvimento e ferramentas")
    p31 = c.achar("Não há hardware para montar.")
    trocar_texto(p31, "Não há hardware para montar. Em vez disso, foi preparado o ambiente de desenvolvimento:",
                 "Para desenvolver o jogo usámos estas ferramentas:")

    # nova 3.2 Estrutura da aplicação e da base de dados
    h32 = c.achar("3.2  Programação do controlo")
    ant = h32.getprevious()
    h32n = copiar_titulo(h2_simples, ant, "3.2  Estrutura da aplicação e da base de dados")
    p = novo_par(par_simples, h32n, [
        "O código do jogo está na pasta jogo, dividido em subpastas por tema. O ficheiro caminhos.py junta as "
        "subpastas ao Python, por isso cada ficheiro importa os outros só pelo nome:"])
    for titulo, corpo in ESTRUTURA:
        p = novo_par(marcador, p, ["–\t", "**" + titulo, corpo])
    fig_dados = c.achar("– Modelo de dados", contem=True)
    p = novo_par(par_simples, p, [
        "Fora da pasta do jogo ficam o servidor do jogo online (servidor), o site (site), os programas que criam a "
        "aplicação e fazem as análises (ferramentas) e a documentação (docs)."])
    novo_par(par_simples, p, [
        "Os dados ficam em dois sítios. No computador, o modo carreira e a carreira de jogador usam bases de dados "
        "SQLite (carreira.db e carreira_jogador.db) e as definições e as conquistas ficam em ficheiros JSON. No "
        "servidor, as contas, as carreiras guardadas na nuvem e o ranking ficam numa base de dados Postgres, na Neon, "
        f"com as tabelas Conta, Sessao, Progresso e Partida_online. As tabelas e as ligações estão na Figura "
        f"{num_legenda(fig_dados)} (secção 2.4.2)."])

    # 3.2 Programação passa a 3.3 Funcionalidades desenvolvidas
    mudar_titulo(h32, "3.3  Funcionalidades desenvolvidas (módulos principais)")
    intro32 = c.achar("O código está dividido em módulos, um por responsabilidade")
    novo_par(par_simples, intro32, [
        "O código está dividido em módulos, um por responsabilidade (ver a estrutura na secção 3.2 e a arquitetura na "
        "secção 2.6). Seguem-se as funcionalidades principais, divididas por quem as fez."])
    apagar(intro32)
    h321 = c.achar("3.2.1  Trabalho feito por Rafael")
    h322 = c.achar("3.2.2  Trabalho feito em conjunto")
    h323 = c.achar("3.2.3  Trabalho feito por Vasco")
    mudar_titulo(h321, "3.3.1  Trabalho feito por Rafael da Hora Silveira")
    mudar_titulo(h322, "3.3.2  Trabalho feito em conjunto")
    mudar_titulo(h323, "3.3.3  Trabalho feito por Vasco Andreia (resumo)")

    # O pormenor da 3.3.1 vai para o Anexo D; no corpo fica um resumo e duas figuras
    detalhe = bloco(h321.getnext(), h322)
    fig_remate = legenda_com_figura(c, "– Fase de remate:")
    fig_online = legenda_com_figura(c, "– Jogo online: o ecrã JOGAR ONLINE")
    for el in detalhe:
        el.getparent().remove(el)
    detalhe = [el for el in detalhe if el not in fig_remate and el not in fig_online]
    p = novo_par(par_simples, h321, [
        "Esta secção resume as partes do jogo programadas por Rafael da Hora Silveira. A explicação completa de cada "
        "uma, com as contas, as versões em que foram feitas e mais figuras, está no Anexo D."])
    for titulo, corpo in RESUMO_RAFAEL:
        p = novo_par(par_negrito, p, ["**" + titulo, corpo])
        if titulo.startswith("Remate"):
            p = mover(fig_remate, p)
        if titulo.startswith("Jogo online"):
            p = mover(fig_online, p)

    # ---- 3.4: referência ao pormenor que passou para o anexo
    trocar_texto(c.achar("Pontaria com o rato."), "descrita na secção 3.2", "descrita no Anexo D")

    # ---- 4.1: a tabela completa dos testes vai para o Anexo E
    leg_testes = c.achar("– Plano de testes", contem=True)
    tab_testes = c.tabela_depois(leg_testes)
    n_testes = len(tab_testes.findall(qn("w:tr"))) - 1
    for t in tab_testes.iter(W_T):                       # o jogar.bat já não existe (é o jogar.vbs)
        if t.text and "jogar.bat" in t.text:
            t.text = t.text.replace("jogar.bat", "jogar.vbs")
    intro41 = c.achar("Fizemos dois tipos de testes")
    trocar_texto(intro41, "A tabela resume o plano de testes.", "")
    novo_par(par_simples, intro41, [
        f"No total fizemos {n_testes} testes (T01 a T{n_testes:02d}), sobre todas as partes do jogo: física e colisões, "
        "IA, regras (golos, faltas e cartões), câmara, remate na primeira pessoa, menus, modo carreira e base de dados, "
        "carreira de jogador, jogo online e servidor, contas e nuvem, conquistas e aplicação para Windows. Para cada "
        "teste definimos antes o resultado esperado e, no fim, verificámos se o jogo fazia exatamente isso. A lista "
        f"completa, com o resultado esperado de cada teste, está no Anexo E (Tabela {num_legenda(leg_testes)})."])
    leg_testes.getparent().remove(leg_testes)
    tab_testes.getparent().remove(tab_testes)
    apagar_vazios_depois(intro41.getnext(), 2)

    # ---- 4.2 Ensaios e calibração sai; entra 4.2 Testes de usabilidade; as medições passam para a 4.3
    h42 = c.achar("4.2  Ensaios, calibração")
    h43 = c.achar("4.3  Resultados obtidos")
    h42n = copiar_titulo(h2_mads, h42.getprevious(), "4.2  Testes de usabilidade com utilizadores")
    p = novo_par(par_simples, h42n, [
        "Não fizemos um questionário formal. Os testes com utilizadores foram feitos a jogar, nós e colegas que "
        "experimentaram o jogo e deram opiniões, e a jogar os dois em computadores diferentes, observando onde "
        "havia dificuldades. Cada dificuldade encontrada deu origem a uma correção:"])
    for titulo, corpo in USABILIDADE:
        p = novo_par(par_negrito, p, ["**" + titulo, corpo])
    novo_par(par_simples, p, [
        "Para quem joga pela primeira vez, o jogo tem um tutorial com 8 missões curtas, que é obrigatório para quem "
        "cria uma conta nova."])
    mudar_titulo(h42, "4.3  Resultados obtidos e correções")
    apagar(h43)

    # ---- 5.2 Gestão de riscos: texto e riscos reais
    h52 = c.achar("5.2  Gestão de riscos")
    novo_par(par_simples, h52, [
        "Para cada risco estimámos a probabilidade de acontecer e o impacto no projeto, e definimos uma medida para o "
        f"reduzir (Tabela {num_legenda(legenda_modelo)}). Os riscos mais sérios foram os do jogo online e da câmara "
        "em perspetiva, e alguns aconteceram mesmo."])
    tab_riscos = c.tabela_depois(legenda_modelo)
    linhas = tab_riscos.findall(qn("w:tr"))
    modelo_linha = linhas[1]
    for tr in linhas[1:]:
        tab_riscos.remove(tr)
    for valores in RISCOS:
        tr = copy.deepcopy(modelo_linha)
        for tc, v in zip(tr.findall(qn("w:tc")), valores):
            ts = list(tc.iter(W_T))
            ts[0].text = v
            for t in ts[1:]:
                t.text = ""
        tab_riscos.append(tr)
    p = novo_par(par_simples, tab_riscos, ["O que aconteceu e o que fizemos nos riscos mais importantes:"])
    for titulo, corpo in RISCOS_REAIS:
        p = novo_par(par_negrito, p, ["**" + titulo, corpo])

    # ---- 5.4: referências às secções novas
    div = c.achar("estão a negrito as partes feitas por", contem=True)
    for velho, novo in (("descritas em pormenor na secção 3.2.1", "resumidas na secção 3.3.1 (com o pormenor no "
                                                                   "Anexo D)"),
                        ("na secção 3.2.2", "na secção 3.3.2"), ("na secção 3.2.3", "na secção 3.3.3")):
        trocar_texto(div, velho, novo)

    # ---- conclusão: o modo de dois jogadores já foi feito (versão 38)
    fut = c.achar("Como trabalho futuro gostávamos de")
    trocar_texto(fut, ", um modo de dois jogadores no mesmo computador", "")

    # ---- anexos D (pormenor da 3.3.1) e E (lista completa dos testes)
    anexo_c = c.achar("Anexo C – Código-fonte")
    p = novo_par(anexo_c, anexo_c, ["Anexo D – Pormenor das partes feitas por Rafael da Hora Silveira (complemento "
                                    "da secção 3.3.1)."])
    Paragraph(p, None).paragraph_format.page_break_before = True
    primeiro = detalhe[0]
    if texto(primeiro).startswith("Esta secção descreve em pormenor"):
        trocar_texto(primeiro, "Esta secção descreve em pormenor", "Este anexo descreve em pormenor")
    p = mover(detalhe, p)
    p = novo_par(anexo_c, p, ["Anexo E – Lista completa dos testes (complemento da secção 4.1)."])
    Paragraph(p, None).paragraph_format.page_break_before = True
    mover([leg_testes, tab_testes], p)

    # ---- verificação: não pode sobrar nada do modelo de hardware
    resto = " ".join(texto(el) for el in c.depois_intro() if el.tag == W_P)
    for proibido in ("Projeto do hardware", "Esquema elétrico", "Estrutura mecânica", "Montagem do hardware",
                     "Integração hardware", "Ensaios, calibração", "sensores → controlo", "secção 3.2.1",
                     "Fernando Filipe"):
        if proibido in resto:
            raise SystemExit(f"rafael_modelo_software: ainda há «{proibido}» no relatório do Rafael")
