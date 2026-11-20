# -*- coding: utf-8 -*-
"""gerar_diagramas.py - gera todos os diagramas do relatório da PAP.

Executar:  python gerar_diagramas.py
Resultado: um ficheiro .drawio (editável em app.diagrams.net) e um .png por diagrama.
"""
import os
from motor_diagramas import Diagrama

PASTA = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════
# 1. Casos de uso
# ═══════════════════════════════════════════════════════════════════════
def casos_de_uso():
    d = Diagrama("01_casos_de_uso", 1180, 1060, "Casos de uso")
    d.caixa("sis", 180, 10, 830, 1040, "Sistema: StickMania", "grupo", "cinza", tam=15)
    d.caixa("jog", 60, 470, 50, 90, "Jogador", "ator", "azul")
    d.caixa("ia", 1085, 520, 50, 90, "Computador (IA)", "ator", "vermelho")
    d.caixa("amigo", 1085, 690, 50, 90, "Amigo", "ator", "verde")
    d.caixa("srv", 1085, 880, 50, 90, "Servidor do jogo\n(Render + Neon)", "ator", "laranja")

    esq = [("uc1", "Escolher equipas\ne dificuldade"), ("uc3", "Ver definições\n(controlos, som, ecrã)"),
           ("uc4", "Jogar partida"), ("uc5", "Pausar / continuar"),
           ("uc7", "Jogar o modo carreira"), ("uc16", "Jogar a carreira\nde jogador"),
           ("uc15", "Treinar no modo teste"), ("uc18", "Fazer o tutorial\n(8 missões)"),
           ("uc19", "Jogar a dois\nno mesmo PC"), ("uc17", "Jogar online (aleatório,\nsala ou desafio)"),
           ("uc20", "Criar conta / entrar"), ("uc21", "Guardar as carreiras\nna nuvem"),
           ("uc22", "Ver o ranking\ne os últimos jogos")]
    ys = {}
    for i, (id, txt) in enumerate(esq):
        y = 40 + i * 77
        ys[id] = y + 27
        d.caixa(id, 210, y, 240, 54, txt, "elipse", "azul", negrito=(id == "uc4"))
        d.seta("jog", id, ponta=False, exato=True, pontos=[(110, 515), (210, y + 27)])

    inc = [("uc9", "Mover o jogador"), ("uc10", "Passar a bola"), ("uc11", "Rematar na 1.ª pessoa"),
           ("uc23", "Fintar (corte e roleta)"), ("uc12", "Trocar de jogador")]
    for i, (id, txt) in enumerate(inc):
        d.caixa(id, 540, 40 + i * 72, 210, 50, txt, "elipse", "verde")
        d.seta("uc4", id, "«include»", tracejado=True, pos_texto=0.62)

    d.caixa("uc13", 790, 470, 200, 54, "Controlar a equipa\nadversária", "elipse", "vermelho")
    d.caixa("uc14", 790, 550, 200, 54, "Defender a baliza\n(guarda-redes)", "elipse", "vermelho")
    d.seta("ia", "uc13", ponta=False, exato=True, pontos=[(1085, 565), (990, 497)])
    d.seta("ia", "uc14", ponta=False, exato=True, pontos=[(1085, 565), (990, 577)])
    d.seta("uc4", "uc13", "«include»", tracejado=True, exato=True,
           pontos=[(450, 230), (495, 230), (495, 497), (790, 497)], pos_texto=0.75)

    for alvo in ("uc19", "uc17"):
        d.seta("amigo", alvo, ponta=False, exato=True, pontos=[(1085, 735), (450, ys[alvo])])
    for alvo in ("uc17", "uc20", "uc21", "uc22"):
        d.seta("srv", alvo, ponta=False, exato=True, pontos=[(1085, 925), (450, ys[alvo])])
    return d


# ═══════════════════════════════════════════════════════════════════════
# 2. Arquitetura (diagrama de blocos: entrada → controlo → saída)
# ═══════════════════════════════════════════════════════════════════════
def arquitetura():
    d = Diagrama("02_arquitetura", 1200, 790, "Arquitetura do sistema")
    d.caixa("gE", 10, 50, 200, 380, "ENTRADA", "grupo", "cinza", tam=14)
    d.caixa("tec", 30, 105, 160, 70, "Teclado\nWASD · Z · X · V · F · ESC", "arredondado", "azul")
    d.caixa("rato", 30, 205, 160, 70, "Rato\npontaria do remate", "arredondado", "azul")
    d.caixa("cmd", 30, 305, 160, 80, "Comando\nXbox / PlayStation\npartida/comando.py", "arredondado", "azul")

    d.caixa("gC", 260, 50, 640, 380, "CONTROLO — ciclo principal (jogo/game.py, 60 vezes por segundo)",
            "grupo", "cinza", tam=14)
    d.caixa("par", 280, 100, 295, 80, "partida/\nbola, jogadores, guarda-redes, IA,\nfaltas, fintas, remate, repetição",
            "arredondado", "verde")
    d.caixa("mod", 590, 100, 290, 80, "modos/\nmodo carreira, carreira de jogador,\ntutorial, dois jogadores",
            "arredondado", "verde")
    d.caixa("ecr_", 280, 200, 295, 80, "ecras/\nmenus, painel do jogo\ne peças da interface",
            "arredondado", "verde")
    d.caixa("mul", 590, 200, 290, 80, "multijogador/\njogo online (anfitrião e convidado)\ne contas",
            "arredondado", "verde")
    d.caixa("som_", 280, 300, 295, 80, "som/\nsons e cânticos criados no código", "arredondado", "verde")
    d.caixa("clu", 590, 300, 290, 80, "clubes/\nequipas, planteis, emblemas\ne cores dos equipamentos",
            "arredondado", "verde")

    d.caixa("gS", 950, 50, 240, 380, "SAÍDA", "grupo", "cinza", tam=14)
    d.caixa("ecr", 970, 120, 200, 90, "Ecrã 1280×720\ncâmara em perspetiva\n(partida/camera.py)", "arredondado", "laranja")
    d.caixa("som", 970, 270, 200, 90, "Som\nefeitos e cânticos\n(recursos/sons)", "arredondado", "laranja")

    d.caixa("gD", 260, 490, 640, 140, "DADOS DO JOGO", "grupo", "cinza", tam=14)
    d.caixa("cfg", 280, 540, 180, 70, "Configuração\nsettings.py", "arredondado", "roxo")
    d.caixa("cam_", 480, 540, 190, 70, "Onde está cada pasta\ncaminhos.py", "arredondado", "roxo")
    d.caixa("rec", 690, 540, 190, 70, "recursos/\nimagens, sons, sprites", "arredondado", "roxo")
    d.caixa("bd", 950, 490, 240, 140, "Base de dados SQLite (no PC)\ncarreiras gravadas\nsaves/carreira.db\nsaves/carreira_jogador.db",
            "arredondado", "roxo")

    d.caixa("gI", 10, 490, 200, 290, "INTERNET", "grupo", "cinza", tam=14)
    d.caixa("srv", 25, 540, 170, 100, "Servidor do jogo\n(Render, Frankfurt)\nservidor.py · contas.py", "arredondado",
            "laranja")
    d.caixa("neon", 25, 680, 170, 85, "Base de dados\nPostgres (Neon)\ncontas · nuvem · ranking", "arredondado", "roxo")

    d.seta("gE", "gC", "eventos")
    d.seta("gC", "gS", "desenho\ne som")
    d.seta("gD", "gC", "carrega")
    d.seta("srv", "neon", "SQL", ambos=True)
    d.seta("srv", "gC", "teclas, estado do jogo,\ncontas e ranking\n(WebSocket)", exato=True, ambos=True,
           pontos=[(195, 590), (235, 590), (235, 400), (260, 400)], pos_texto=0.25)
    d.seta("gC", "bd", "grava e lê\nas carreiras", exato=True, ambos=True,
           pontos=[(900, 400), (925, 400), (925, 560), (950, 560)], pos_texto=0.5)
    return d


# ═══════════════════════════════════════════════════════════════════════
# 3. Máquina de estados do jogo
# ═══════════════════════════════════════════════════════════════════════
def estados_jogo():
    d = Diagrama("03_estados_jogo", 1240, 650, "Máquina de estados do jogo")
    d.caixa("i", 20, 73, 24, 24, "", "inicio")
    d.caixa("menu", 80, 55, 180, 60, "Menu principal", "arredondado", "azul", negrito=True)
    d.caixa("sel", 380, 55, 200, 60, "Seleção de equipas\n(1 ou 2 jogadores)", "arredondado", "azul")
    d.caixa("jogo", 700, 55, 200, 60, "Partida a decorrer", "arredondado", "verde", negrito=True)
    d.caixa("pausa", 1010, 55, 190, 60, "Pausa", "arredondado", "amarelo")
    d.caixa("ctrl", 40, 250, 170, 60, "Definições\n(controlos, som, ecrã)", "arredondado", "azul")
    d.caixa("onl", 380, 250, 200, 60, "Jogar online\n(aleatório, sala, desafio)", "arredondado", "azul")
    d.caixa("conta", 380, 430, 200, 60, "Conta\n(nuvem e ranking)", "arredondado", "azul")
    d.caixa("golo", 610, 250, 170, 60, "Golo\n(festa)", "arredondado", "verde")
    d.caixa("rep", 820, 250, 170, 60, "Repetição do golo\n(câmara lenta)", "arredondado", "verde")
    d.caixa("fim", 1010, 250, 190, 60, "Fim de jogo\n(resultado final)", "arredondado", "vermelho")
    d.caixa("f", 30, 170, 30, 30, "", "fim")

    d.seta("i", "menu")
    d.seta("menu", "sel", "Jogo rápido", desvio=(0, -14))
    d.seta("sel", "menu", "Voltar", desvio=(0, 14))
    d.seta("sel", "jogo", "Começar")
    d.seta("jogo", "pausa", "ESC", desvio=(0, -14))
    d.seta("pausa", "jogo", "Continuar /\nReiniciar", desvio=(0, 14))
    d.seta("menu", "f", "Sair", exato=True, pontos=[(95, 115), (95, 185), (60, 185)], pos_texto=0.3)
    d.seta("menu", "ctrl", "Engrenagem", exato=True, pontos=[(115, 115), (115, 250)], pos_texto=0.5)
    d.seta("ctrl", "menu", "Voltar", exato=True, pontos=[(185, 250), (185, 115)], pos_texto=0.5)
    d.seta("menu", "onl", "Jogar online", exato=True, pontos=[(245, 115), (245, 280), (380, 280)], pos_texto=0.75)
    d.seta("menu", "conta", "Conta", exato=True, pontos=[(230, 115), (230, 460), (380, 460)], pos_texto=0.8)
    d.seta("onl", "sel", "emparelhados: cada um\nescolhe a sua equipa", exato=True,
           pontos=[(480, 250), (480, 115)], pos_texto=0.5)
    d.seta("jogo", "golo", "golo", exato=True, pontos=[(735, 115), (735, 250)])
    d.seta("golo", "rep", "fim da\nfesta")
    d.seta("rep", "jogo", "acaba ou\nqualquer tecla", exato=True, pontos=[(865, 250), (865, 115)], pos_texto=0.28)
    d.seta("jogo", "fim", "fim da 2.ª parte", exato=True,
           pontos=[(885, 115), (885, 180), (1050, 180), (1050, 250)], pos_texto=0.55)
    d.seta("fim", "jogo", "Jogar de novo", exato=True,
           pontos=[(1160, 250), (1160, 150), (895, 150), (895, 115)], pos_texto=0.25)
    d.seta("pausa", "menu", "Menu principal", exato=True,
           pontos=[(1105, 55), (1105, 22), (170, 22), (170, 55)])
    d.seta("fim", "menu", "Menu principal", exato=True,
           pontos=[(1105, 310), (1105, 560), (10, 560), (10, 108), (80, 108)], pos_texto=0.3)
    d.seta("pausa", "ctrl", "Definições / voltar à pausa", exato=True, ambos=True,
           pontos=[(1200, 85), (1225, 85), (1225, 620), (125, 620), (125, 310)], pos_texto=0.55)
    return d


# ═══════════════════════════════════════════════════════════════════════
# 4. Fluxograma da decisão da IA
# ═══════════════════════════════════════════════════════════════════════
def fluxograma_ia():
    d = Diagrama("04_fluxograma_ia", 1410, 810, "Fluxograma da IA")
    d.caixa("ini", 480, 10, 280, 54, "Início do frame\n(para cada jogador da IA)", "terminal", "cinza")
    d.caixa("d1", 530, 95, 180, 90, "Tem a bola?", "losango", "amarelo")
    # ── Com bola (ATACAR) ──
    d.caixa("d2", 220, 202, 220, 96, "Atrás da linha\nde golo?", "losango", "amarelo")
    d.caixa("cont", 10, 218, 155, 60, "ATACAR: contornar\na baliza", "arredondado", "verde")
    d.caixa("d3", 220, 332, 220, 96, "Perto, com ângulo\ne linha livre?", "losango", "amarelo")
    d.caixa("rem", 10, 350, 155, 60, "ATACAR: rematar ao\ncanto longe do GR", "arredondado", "verde")
    d.caixa("d4", 220, 462, 220, 96, "Pressionado ou colega\nmelhor colocado?", "losango", "amarelo")
    d.caixa("pas", 10, 480, 155, 60, "ATACAR: passar ao\ncolega livre", "arredondado", "verde")
    d.caixa("cond", 245, 590, 170, 64, "ATACAR: conduzir e\nfintar até à zona\nde remate", "arredondado", "verde")
    # ── Sem bola ──
    d.caixa("d5", 690, 202, 220, 96, "Adversário\ntem a bola?", "losango", "amarelo")
    d.caixa("d6", 980, 202, 220, 96, "Lugar na fila\npara o portador?", "losango", "amarelo")
    d.caixa("pre", 1250, 220, 145, 60, "DEFENDER:\npressionar", "arredondado", "vermelho")
    d.caixa("cob", 1250, 330, 145, 60, "DEFENDER: cobrir\n(bola ↔ baliza)", "arredondado", "vermelho")
    d.caixa("fec", 1250, 440, 145, 60, "DEFENDER: fechar\nespaços", "arredondado", "vermelho")
    d.caixa("d7", 690, 352, 220, 96, "Colega\ntem a bola?", "losango", "amarelo")
    d.caixa("apo", 470, 370, 170, 60, "APOIAR: abrir espaço\npara receber", "arredondado", "azul")
    d.caixa("d8", 680, 488, 240, 104, "Passe para mim ou\nsou o mais perto?", "losango", "amarelo")
    d.caixa("per", 965, 510, 180, 60, "PERSEGUIR: ir onde\na bola vai estar", "arredondado", "azul")
    d.caixa("for", 715, 630, 170, 60, "Ir para a posição\nna formação", "arredondado", "azul")
    d.caixa("fim", 450, 740, 500, 60, "Aplicar a velocidade ao jogador\n(afasta-se dos colegas e desvia-se dos adversários)",
            "terminal", "cinza")

    d.seta("ini", "d1")
    d.seta("d1", "d2", "Sim", exato=True, pontos=[(530, 140), (330, 140), (330, 202)])
    d.seta("d1", "d5", "Não", exato=True, pontos=[(710, 140), (800, 140), (800, 202)])
    d.seta("d2", "cont", "Sim", exato=True, pontos=[(220, 250), (165, 250)])
    d.seta("d2", "d3", "Não")
    d.seta("d3", "rem", "Sim", exato=True, pontos=[(220, 380), (165, 380)])
    d.seta("d3", "d4", "Não")
    d.seta("d4", "pas", "Sim", exato=True, pontos=[(220, 510), (165, 510)])
    d.seta("d4", "cond", "Não")
    d.seta("d5", "d6", "Sim", exato=True, pontos=[(910, 250), (980, 250)])
    d.seta("d6", "pre", "1.º", exato=True, pontos=[(1200, 250), (1250, 250)])
    d.seta("d6", "cob", "2.º", exato=True, pontos=[(1090, 298), (1090, 360), (1250, 360)], pos_texto=0.75)
    d.seta("d6", "fec", "outros", exato=True, pontos=[(1090, 298), (1090, 470), (1250, 470)], pos_texto=0.8)
    d.seta("d5", "d7", "Não")
    d.seta("d7", "apo", "Sim", exato=True, pontos=[(690, 400), (640, 400)])
    d.seta("d7", "d8", "Não")
    d.seta("d8", "per", "Sim", exato=True, pontos=[(920, 540), (965, 540)])
    d.seta("d8", "for", "Não")
    # Todas as ações acabam no mesmo sítio
    d.seta("cont", "fim", exato=True, pontos=[(10, 248), (0, 248), (0, 770), (450, 770)])
    d.seta("rem", "cont", exato=True, ponta=False, pontos=[(10, 380), (0, 380)])
    d.seta("pas", "cont", exato=True, ponta=False, pontos=[(10, 510), (0, 510)])
    d.seta("cond", "fim", exato=True, ponta=False, pontos=[(330, 654), (330, 770)])
    d.seta("apo", "fim", exato=True, pontos=[(555, 430), (555, 740)])
    d.seta("for", "fim", exato=True, pontos=[(800, 690), (800, 740)])
    d.seta("pre", "fim", exato=True, pontos=[(1390, 250), (1404, 250), (1404, 770), (950, 770)])
    d.seta("cob", "fim", exato=True, ponta=False, pontos=[(1390, 360), (1404, 360)])
    d.seta("fec", "fim", exato=True, ponta=False, pontos=[(1390, 470), (1404, 470)])
    d.seta("per", "fim", exato=True, ponta=False, pontos=[(1055, 570), (1055, 770)])
    return d


# ═══════════════════════════════════════════════════════════════════════
# 5. Fluxograma do ciclo principal do jogo
# ═══════════════════════════════════════════════════════════════════════
def fluxograma_ciclo():
    d = Diagrama("05_fluxograma_ciclo", 860, 1090, "Fluxograma do ciclo principal")
    d.caixa("ini", 230, 10, 200, 44, "Início", "terminal", "cinza", negrito=True)
    d.caixa("n2", 180, 85, 300, 60, "Iniciar pygame e a janela 1280×720;\ncarregar equipas, sprites e ringue", "retangulo", "azul")
    d.caixa("n3", 180, 175, 300, 50, "Ler eventos do teclado e do rato", "retangulo", "azul")
    d.caixa("n4", 230, 255, 200, 90, "Fechar janela\nou «Sair»?", "losango", "amarelo")
    d.caixa("sai", 560, 278, 150, 44, "Fim", "terminal", "cinza", negrito=True)
    d.caixa("n5", 215, 375, 230, 100, "Partida a decorrer\n(sem pausa)?", "losango", "amarelo")
    d.caixa("n5b", 560, 395, 220, 60, "Atualizar o menu, a pausa\nou o ecrã final", "retangulo", "azul")
    d.caixa("n6", 180, 505, 300, 44, "Descontar o tempo da parte (dt)", "retangulo", "verde")
    d.caixa("n7", 180, 570, 300, 56, "Mover os jogadores (humano + IA)\ne os guarda-redes", "retangulo", "verde")
    d.caixa("n8", 180, 645, 300, 56, "Mover a bola: atrito, ressaltos,\ncolisões e faltas", "retangulo", "verde")
    d.caixa("n9", 260, 725, 140, 80, "Golo?", "losango", "amarelo")
    d.caixa("n9b", 560, 735, 200, 60, "Somar o golo e\nrepor as posições", "retangulo", "verde")
    d.caixa("n10", 230, 832, 200, 90, "Tempo da parte\nacabou?", "losango", "amarelo")
    d.caixa("n10b", 560, 847, 220, 60, "1.ª parte → intervalo\n2.ª parte → fim de jogo", "retangulo", "verde")
    d.caixa("n11", 180, 952, 300, 56, "Desenhar: ringue em perspetiva,\njogadores, bola e HUD", "retangulo", "laranja")
    d.caixa("n12", 180, 1035, 300, 44, "Esperar pelo próximo frame (60 FPS)", "retangulo", "laranja")

    d.seta("ini", "n2"); d.seta("n2", "n3"); d.seta("n3", "n4")
    d.seta("n4", "sai", "Sim")
    d.seta("n4", "n5", "Não")
    d.seta("n5", "n5b", "Não")
    d.seta("n5", "n6", "Sim")
    d.seta("n6", "n7"); d.seta("n7", "n8"); d.seta("n8", "n9")
    d.seta("n9", "n9b", "Sim")
    d.seta("n9", "n10", "Não")
    d.seta("n9b", "n10", exato=True, ponta=False, pontos=[(660, 795), (660, 816), (330, 816)])
    d.seta("n10", "n10b", "Sim")
    d.seta("n10", "n11", "Não")
    d.seta("n10b", "n11", exato=True, ponta=False, pontos=[(670, 907), (670, 935), (330, 935)])
    d.seta("n5b", "n11", exato=True, pontos=[(780, 425), (830, 425), (830, 980), (480, 980)])
    d.seta("n11", "n12")
    d.seta("n12", "n3", "repetir", exato=True, pontos=[(180, 1057), (120, 1057), (120, 200), (180, 200)])
    return d


# ═══════════════════════════════════════════════════════════════════════
# 6. Diagrama de classes
# ═══════════════════════════════════════════════════════════════════════
def classes():
    d = Diagrama("06_classes", 1180, 730, "Diagrama de classes")
    C = lambda id, x, y, w, h, t, a, m, cor="azul": d.caixa(id, x, y, w, h, tipo="classe", cor=cor, tam=12,
                                                            linhas=(t, [a, m]))
    C("game", 400, 10, 340, 290, "Game",
      ["- estado: str", "- pausado: bool", "- golos_azul, golos_vermelho: int", "- parte: int",
       "- tempo_restante: float", "- dificuldade: str", "«junta» OnlineMixin · FaltasMixin · FintasMixin",
       "DoisJogadoresMixin · RepeticaoMixin", "TutorialMixin · ContaMixin"],
      ["+ run()", "+ handle_events()", "+ update(dt)", "+ draw()", "+ iniciar_partida(casa, fora)",
       "+ assinalar_falta(infrator, vitima)"], "verde")
    C("rink", 20, 10, 290, 150, "Rink",
      ["- rect: Rect", "- camera: Camera", "- linha_golo_esq_x / dir_x", "- equipa_casa: str"],
      ["+ draw(screen)", "+ draw_frente(screen)", "+ definir_equipa_casa(id)"])
    C("cam", 20, 230, 290, 150, "Camera",
      ["- topo, base: float", "- f_topo, f_base: float"],
      ["+ fator(wy)", "+ escala(wy)", "+ ecra_y(wy)", "+ projetar(wx, wy)", "+ desprojetar(sx, sy)"])
    C("hud", 840, 10, 320, 110, "HUDController",
      ["- fontes, cores"],
      ["+ draw_top_bar(screen, game)", "+ draw_bottom_panel(screen, game)", "+ draw_foul_banner(...)"])
    C("menus", 840, 180, 320, 120, "«ecrãs» (pasta ecras/ e menus dos modos)",
      ["MenuPrincipal · EcraControlos · MenuPausa", "TeamSelectMenu · EcraFimJogo",
       "EcraCampeonato · EcraOnline · EcraConta"],
      ["+ handle_event(event) → ação", "+ update(dt)", "+ draw()"], "cinza")
    C("camp", 20, 395, 290, 135, "Campeonato (carreira.py)",
      ["- torneio_id: int", "- con: sqlite3.Connection"],
      ["+ novo(equipa, dificuldade)", "+ proximo_jogo()", "+ registar_jogo_do_jogador(g1, g2)",
       "+ classificacao()"], "roxo")
    C("ball", 380, 330, 260, 150, "Ball",
      ["- pos_x, pos_y: float", "- vel: Vector2", "- dono: Player"],
      ["+ update(dt, rink) → golo?", "+ definir_dono(jogador)", "+ libertar(velocidade)", "+ repor(pos)"])
    C("player", 700, 420, 290, 195, "Player",
      ["- pos_x, pos_y, vel_x, vel_y", "- equipa, numero, papel", "- tem_bola: bool", "- humano: bool"],
      ["+ update(dt, rink_rect, bola)", "+ set_target(vx, vy)", "+ fazer_passe(bola, dir)",
       "+ fazer_remate(bola, dir)", "+ comecar_finta(lado, tipo)", "+ empurrar_separar(outro)"])
    C("ia", 1040, 440, 130, 170, "AgentIA",
      ["- jogador", "- papel", "- cfg"],
      ["+ update(...)", "- _estado_atacar", "- _estado_defender", "- _estado_apoiar", "- _estado_perseguir"],
      "vermelho")
    C("gr", 380, 560, 260, 110, "Goalkeeper",
      ["- pos_x, pos_y", "- equipa, dificuldade"],
      ["+ update(dt, bola)", "+ repor()"])
    C("anim", 20, 540, 290, 110, "AnimationController",
      ["- estado: str", "- animacoes: dict"],
      ["+ update(dt)", "+ imagem: Surface"], "roxo")

    d.seta("game", "rink", "1")
    d.seta("rink", "cam", "1")
    d.seta("game", "hud", "1")
    d.seta("game", "menus", "1..7", pontos=[(780, 230)])
    d.seta("game", "camp", "0..1", exato=True, pontos=[(400, 285), (362, 285), (362, 460), (310, 460)],
           pos_texto=0.55)
    d.seta("game", "ball", "1")
    d.seta("game", "player", "8", pontos=[(700, 330)])
    d.seta("game", "gr", "2", exato=True, pontos=[(420, 300), (420, 315), (345, 315), (345, 590), (380, 590)], pos_texto=0.55)
    d.seta("game", "ia", "7", exato=True, pontos=[(740, 150), (815, 150), (815, 395), (1105, 395), (1105, 440)], pos_texto=0.75)
    d.seta("ia", "player")
    d.caixa("tctrl", 985, 490, 60, 20, "controla", "texto", tam=11)
    d.seta("player", "anim", "1", exato=True, pontos=[(760, 615), (760, 715), (165, 715), (165, 650)], pos_texto=0.5)
    d.seta("gr", "anim", "1", exato=True, pontos=[(380, 630), (310, 630)])
    d.seta("ball", "player", "dono", tracejado=True, desvio=(0, 20))
    return d


# ═══════════════════════════════════════════════════════════════════════
# 7. Modelo de dados (base de dados SQLite do modo carreira)
# ═══════════════════════════════════════════════════════════════════════
def modelo_dados():
    d = Diagrama("07_modelo_dados", 1120, 1520, "Modelo de dados (SQLite no PC e Postgres no servidor)")
    T = lambda id, x, y, w, h, t, campos, cor="roxo", tr=False: d.caixa(
        id, x, y, w, h, tipo="classe", cor=cor, tam=12, linhas=(t, [campos]), tracejado=tr)
    T("equipa", 20, 20, 240, 100, "Equipa",
      ["PK id", "nome", "sigla", "forca"])
    T("torneio", 440, 20, 240, 145, "Torneio",
      ["PK id", "nome", "FK equipa_jogador", "dificuldade", "epoca", "data_inicio", "estado"])
    T("class", 860, 20, 240, 188, "Classificacao",
      ["PK, FK torneio_id", "PK, FK equipa_id", "competicao", "jogos", "vitorias", "empates", "derrotas",
       "golos_marcados", "golos_sofridos", "pontos"])
    T("partida", 440, 220, 240, 221, "Partida",
      ["PK id", "FK torneio_id", "jornada", "FK casa_id", "FK fora_id", "golos_casa", "golos_fora",
       "jogada", "do_jogador", "simulado", "competicao, fase", "pen_casa, pen_fora"])
    T("jogador", 20, 260, 240, 115, "Jogador",
      ["PK id", "FK equipa_id", "nome", "numero", "posicao"])
    T("estat", 860, 260, 240, 100, "Estatistica",
      ["PK id", "FK partida_id", "FK jogador_id", "golos"])
    # Carreira de jogador (saves/carreira_jogador.db: as mesmas tabelas e mais estas duas)
    T("atleta", 20, 510, 240, 190, "Atleta (carreira de jogador)",
      ["PK id", "nome", "numero", "posicao", "FK equipa_id", "geral", "epoca", "FK torneio_id", "estado"],
      cor="verde")
    T("atuacao", 440, 495, 240, 235, "Atuacao",
      ["PK id", "FK atleta_id", "FK partida_id", "FK torneio_id", "golos", "assistencias", "remates",
       "passes", "recuperacoes", "perdas", "nota", "geral_depois"], cor="verde")
    d.seta("atleta", "atuacao", "1 : N", ponta=False, exato=True, pontos=[(260, 605), (440, 605)])
    d.seta("partida", "atuacao", "1 : N", ponta=False, exato=True, pontos=[(560, 441), (560, 495)], pos_texto=0.6)
    d.seta("equipa", "atleta", "1 : N", ponta=False, exato=True,
           pontos=[(20, 70), (6, 70), (6, 590), (20, 590)], pos_texto=0.5)
    # Vida do jogador (vida.py): os valores da vida e o diário
    T("vida", 860, 455, 240, 260, "Vida",
      ["PK, FK atleta_id", "idade", "forma", "moral", "treinador", "fama", "estudos", "dinheiro", "lesao",
       "banco", "evento_pendente", "atividade_feita"], cor="laranja")
    T("diario", 440, 790, 240, 140, "Diario",
      ["PK id", "FK atleta_id", "epoca", "jornada", "evento", "texto", "efeitos"], cor="laranja")
    d.seta("atleta", "vida", "1 : 1", ponta=False, exato=True,
           pontos=[(200, 700), (200, 755), (980, 755), (980, 715)], pos_texto=0.7)
    d.seta("atleta", "diario", "1 : N", ponta=False, exato=True,
           pontos=[(80, 700), (80, 860), (440, 860)], pos_texto=0.75)
    # Pessoas da vida, consequências à espera e marcas (bens e conquistas)
    T("pessoa", 20, 970, 240, 160, "Pessoa",
      ["PK id", "FK atleta_id", "papel", "nome", "relacao", "interagiu", "ativa"], cor="laranja")
    T("seguimento", 440, 970, 240, 100, "Seguimento",
      ["PK id", "FK atleta_id", "evento", "jornadas"], cor="laranja")
    T("marca", 860, 970, 240, 100, "Marca",
      ["PK, FK atleta_id", "PK chave", "epoca"], cor="laranja")
    for alvo, x in (("pessoa", 200), ("seguimento", 560), ("marca", 980)):
        d.seta("atleta", alvo, "1 : N", ponta=False, exato=True,
               pontos=[(140, 700), (140, 945), (x, 945), (x, 970)], pos_texto=0.97)

    # Servidor do jogo (servidor/contas.py): Postgres na Neon
    d.caixa("gsrv", 8, 1155, 1104, 360, "SERVIDOR DO JOGO — Postgres na Neon (servidor/contas.py)", "grupo", "cinza",
            tam=14)
    T("conta", 20, 1205, 240, 280, "Conta",
      ["PK id", "alcunha", "alcunha_min (única)", "senha_hash", "rec_hash", "criada", "pontos", "jogos", "vitorias",
       "empates", "derrotas", "golos_marcados", "golos_sofridos"], cor="azul")
    T("sessao", 440, 1205, 240, 100, "Sessao",
      ["PK token_hash", "FK conta_id", "criada"], cor="azul")
    T("progresso", 440, 1345, 240, 120, "Progresso (nuvem)",
      ["PK, FK conta_id", "PK tipo", "dados", "versao"], cor="azul")
    T("ponline", 860, 1205, 240, 195, "Partida_online",
      ["PK id", "FK casa_id", "FK fora_id", "golos_casa", "golos_fora", "pontos_casa", "pontos_fora", "data"],
      cor="azul")
    d.seta("conta", "sessao", "1 : N", ponta=False, exato=True, pontos=[(260, 1255), (440, 1255)])
    d.seta("conta", "progresso", "1 : N", ponta=False, exato=True, pontos=[(260, 1405), (440, 1405)])
    d.seta("conta", "ponline", "1 : N\n(casa / fora)", ponta=False, exato=True,
           pontos=[(260, 1470), (260, 1495), (980, 1495), (980, 1400)], pos_texto=0.5)

    d.seta("equipa", "torneio", "1 : N\n(equipa do jogador)", ponta=False, exato=True,
           pontos=[(260, 70), (440, 70)])
    d.seta("torneio", "partida", "1 : N", ponta=False)
    d.seta("equipa", "partida", "1 : N\n(casa / fora)", ponta=False, exato=True,
           pontos=[(200, 120), (200, 190), (380, 190), (380, 300), (440, 300)], pos_texto=0.45)
    d.seta("torneio", "class", "1 : N", ponta=False, exato=True, pontos=[(680, 100), (860, 100)])
    d.seta("equipa", "class", "1 : N", ponta=False, exato=True,
           pontos=[(140, 20), (140, 5), (980, 5), (980, 20)], pos_texto=0.5)
    d.seta("equipa", "jogador", "1 : N", ponta=False, exato=True,
           pontos=[(80, 120), (80, 260)])
    d.seta("partida", "estat", "1 : N", ponta=False, exato=True,
           pontos=[(680, 330), (860, 330)])
    d.seta("jogador", "estat", "1 : N", ponta=False, exato=True,
           pontos=[(140, 375), (140, 448), (980, 448), (980, 360)], pos_texto=0.2)
    return d


# ═══════════════════════════════════════════════════════════════════════
# 8. Fluxograma do modo carreira
# ═══════════════════════════════════════════════════════════════════════
def fluxograma_carreira():
    d = Diagrama("08_fluxograma_carreira", 700, 1100, "Fluxograma do modo carreira")
    d.caixa("ini", 190, 10, 280, 50, "Menu principal → MODO CARREIRA", "terminal", "cinza", negrito=True)
    d.caixa("d1", 220, 90, 220, 96, "Há um campeonato\nguardado?", "losango", "amarelo")
    d.caixa("esc", 195, 222, 270, 56, "Escolher o clube (1.ª ou 2.ª\ndivisão) e a dificuldade", "retangulo", "azul")
    d.caixa("cri", 180, 312, 300, 76, "Criar a época: calendários das 2\ndivisões, quartos da Taça Europeia\ne classificações, em SQLite",
            "retangulo", "roxo")
    d.caixa("hub", 180, 420, 300, 72, "Ecrã do campeonato: classificações,\npróximo jogo, resultados,\ncalendário e quadro europeu",
            "arredondado", "laranja", negrito=False)
    d.caixa("d2", 220, 525, 220, 96, "Campeonato\nterminado?", "losango", "amarelo")
    d.caixa("fim", 15, 545, 170, 56, "Campeões, quem sobe,\nquem desce e a Europa", "retangulo", "laranja")
    d.caixa("d4", 220, 655, 220, 90, "Jogar ou\nsimular?", "losango", "amarelo")
    d.caixa("jog", 90, 780, 230, 56, "Jogar o jogo da ronda\n(liga ou Taça Europeia)", "retangulo", "verde")
    d.caixa("sim", 360, 780, 290, 56, "Simular o jogo: força das equipas,\nforma e dificuldade", "retangulo", "verde")
    d.caixa("d3", 95, 870, 220, 90, "Desistiu\nna pausa?", "losango", "amarelo")
    d.caixa("reg", 150, 1000, 400, 76, "Gravar o resultado (penáltis se a eliminatória\nempatar), simular os outros jogos e criar\na fase europeia seguinte — numa transação",
            "retangulo", "roxo")

    d.seta("ini", "d1")
    d.seta("d1", "esc", "Não")
    d.seta("esc", "cri")
    d.seta("cri", "hub")
    d.seta("d1", "hub", "Sim (continuar)", exato=True,
           pontos=[(440, 138), (540, 138), (540, 432), (480, 432)], pos_texto=0.3)
    d.seta("hub", "d2")
    d.seta("d2", "d4", "Não")
    d.seta("d2", "fim", "Sim", exato=True, pontos=[(220, 573), (185, 573)])
    d.seta("fim", "cri", "Nova época", exato=True, pontos=[(100, 545), (100, 350), (180, 350)], pos_texto=0.4)
    d.seta("d4", "jog", "Jogar", exato=True, pontos=[(220, 700), (205, 700), (205, 780)])
    d.seta("d4", "sim", "Simular", exato=True, pontos=[(440, 700), (505, 700), (505, 780)])
    d.seta("jog", "d3")
    d.seta("d3", "reg", "Não", exato=True, pontos=[(205, 960), (205, 1000)])
    d.seta("sim", "reg", exato=True, pontos=[(505, 836), (505, 1000)])
    d.seta("d3", "hub", "Sim\n(não conta)", exato=True,
           pontos=[(95, 915), (8, 915), (8, 480), (180, 480)], pos_texto=0.94)
    d.seta("reg", "hub", "ronda seguinte", exato=True,
           pontos=[(550, 1038), (665, 1038), (665, 450), (480, 450)], pos_texto=0.25)
    return d


if __name__ == "__main__":
    for f in (casos_de_uso, arquitetura, estados_jogo, fluxograma_ia, fluxograma_ciclo, classes, modelo_dados,
              fluxograma_carreira):
        dg = f()
        print(*dg.guardar(PASTA))
