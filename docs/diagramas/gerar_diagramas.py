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
    d = Diagrama("01_casos_de_uso", 1010, 690, "Casos de uso")
    d.caixa("sis", 190, 10, 630, 670, "Sistema: StickMania", "grupo", "cinza", tam=15)
    d.caixa("jog", 60, 290, 50, 90, "Jogador", "ator", "azul")
    d.caixa("ia", 905, 290, 50, 90, "Computador (IA)", "ator", "vermelho")

    esq = [("uc1", "Escolher equipas"), ("uc2", "Escolher dificuldade"), ("uc3", "Ver controlos"),
           ("uc4", "Jogar partida"), ("uc5", "Pausar / continuar"), ("uc6", "Ver resultado final"),
           ("uc7", "Jogar torneio\n(a implementar)"), ("uc8", "Consultar classificação\n(a implementar)")]
    for i, (id, txt) in enumerate(esq):
        planeado = "implementar" in txt
        d.caixa(id, 215, 55 + i * 78, 225, 54, txt, "elipse", "amarelo" if planeado else "azul",
                tracejado=planeado, negrito=(id == "uc4"))
        d.seta("jog", id, ponta=False, exato=True, pontos=[(110, 330), (215, 55 + i * 78 + 27)])

    dir_ = [("uc9", "Mover o jogador", 160), ("uc10", "Passar a bola", 230), ("uc11", "Rematar com mira", 300),
            ("uc12", "Trocar de jogador", 370)]
    for id, txt, y in dir_:
        d.caixa(id, 565, y, 200, 50, txt, "elipse", "verde")
        d.seta("uc4", id, "«include»", tracejado=True, pos_texto=0.62)

    d.caixa("uc13", 565, 480, 200, 54, "Controlar a equipa\nadversária", "elipse", "vermelho")
    d.caixa("uc14", 565, 560, 200, 54, "Defender a baliza\n(guarda-redes)", "elipse", "vermelho")
    d.seta("ia", "uc13", ponta=False, exato=True, pontos=[(905, 335), (765, 507)])
    d.seta("ia", "uc14", ponta=False, exato=True, pontos=[(905, 335), (765, 587)])
    d.seta("uc4", "uc13", "«include»", tracejado=True, pos_texto=0.6)
    return d


# ═══════════════════════════════════════════════════════════════════════
# 2. Arquitetura (diagrama de blocos: entrada → controlo → saída)
# ═══════════════════════════════════════════════════════════════════════
def arquitetura():
    d = Diagrama("02_arquitetura", 1100, 560, "Arquitetura do sistema")
    d.caixa("gE", 10, 50, 200, 310, "ENTRADA", "grupo", "cinza", tam=14)
    d.caixa("tec", 30, 110, 160, 70, "Teclado\nWASD · Z · X · TAB · ESC", "arredondado", "azul")
    d.caixa("rato", 30, 220, 160, 70, "Rato\npontaria do remate", "arredondado", "azul")

    d.caixa("gC", 270, 50, 520, 310, "CONTROLO — ciclo principal (game.py, 60 FPS)", "grupo", "cinza", tam=14)
    d.caixa("men", 290, 100, 230, 66, "Menus e estados do jogo\nmenu.py", "arredondado", "verde")
    d.caixa("reg", 540, 100, 230, 66, "Regras: tempo, golos, faltas\ngame.py", "arredondado", "verde")
    d.caixa("fis", 290, 190, 230, 66, "Física da bola e dos jogadores\nball.py · player.py", "arredondado", "verde")
    d.caixa("ia", 540, 190, 230, 66, "Inteligência artificial\nai.py · goalkeeper.py", "arredondado", "verde")
    d.caixa("ani", 290, 280, 480, 56, "Animações e equipamentos das equipas — animation.py · cores.py",
            "arredondado", "verde")

    d.caixa("gS", 850, 50, 240, 310, "SAÍDA", "grupo", "cinza", tam=14)
    d.caixa("ecr", 870, 100, 200, 66, "Ecrã 1280×720\ncamera.py · rink.py · baliza.py", "arredondado", "laranja")
    d.caixa("hud", 870, 190, 200, 66, "Interface (HUD)\nui.py · componentes.py", "arredondado", "laranja")
    d.caixa("som", 870, 280, 200, 56, "Som\n(a implementar)", "arredondado", "amarelo", tracejado=True)

    d.caixa("gD", 270, 420, 520, 130, "DADOS", "grupo", "cinza", tam=14)
    d.caixa("cfg", 290, 465, 150, 66, "Configuração\nsettings.py", "arredondado", "roxo")
    d.caixa("eq", 455, 465, 160, 66, "Equipas e símbolos\nteam.py · simbolos/", "arredondado", "roxo")
    d.caixa("spr", 630, 465, 140, 66, "Sprites\nsprites_v2/", "arredondado", "roxo")
    d.caixa("bd", 850, 440, 240, 90, "Base de dados SQLite\ntorneio e classificação\n(a implementar)",
            "arredondado", "amarelo", tracejado=True)

    d.seta("gE", "gC", "eventos")
    d.seta("gC", "gS", "desenho")
    d.seta("gD", "gC", "carrega")
    d.seta("gC", "bd", "grava\nresultados", tracejado=True, exato=True,
           pontos=[(790, 330), (820, 330), (820, 485), (850, 485)])
    return d


# ═══════════════════════════════════════════════════════════════════════
# 3. Máquina de estados do jogo
# ═══════════════════════════════════════════════════════════════════════
def estados_jogo():
    d = Diagrama("03_estados_jogo", 1210, 490, "Máquina de estados do jogo")
    d.caixa("i", 20, 73, 24, 24, "", "inicio")
    d.caixa("menu", 80, 55, 180, 60, "Menu principal", "arredondado", "azul", negrito=True)
    d.caixa("sel", 380, 55, 200, 60, "Seleção de equipas\ne dificuldade", "arredondado", "azul")
    d.caixa("jogo", 700, 55, 200, 60, "Partida a decorrer", "arredondado", "verde", negrito=True)
    d.caixa("pausa", 980, 55, 190, 60, "Pausa", "arredondado", "amarelo")
    d.caixa("ctrl", 80, 300, 180, 60, "Controlos", "arredondado", "azul")
    d.caixa("golo", 700, 300, 200, 60, "Golo / intervalo\n(repor posições)", "arredondado", "verde")
    d.caixa("fim", 980, 300, 190, 60, "Fim de jogo\n(resultado final)", "arredondado", "vermelho")
    d.caixa("f", 330, 195, 30, 30, "", "fim")

    d.seta("i", "menu")
    d.seta("menu", "sel", "Jogar", desvio=(0, -14))
    d.seta("sel", "menu", "Voltar", desvio=(0, 14))
    d.seta("sel", "jogo", "Começar")
    d.seta("jogo", "pausa", "ESC / P", desvio=(0, -14))
    d.seta("pausa", "jogo", "Continuar /\nReiniciar", desvio=(0, 14))
    d.seta("jogo", "golo", "golo ou fim\nda 1.ª parte", desvio=(-45, 0))
    d.seta("golo", "jogo", "recomeça", desvio=(45, 0))
    d.seta("jogo", "fim", "fim da 2.ª parte", desvio=(14, -12), pos_texto=0.3)
    d.seta("fim", "jogo", "Jogar de novo", desvio=(-14, 12), pos_texto=0.68)
    d.seta("menu", "ctrl", "Controlos", desvio=(-35, 0))
    d.seta("ctrl", "menu", "Voltar", desvio=(35, 0))
    d.seta("menu", "f", "Sair")
    d.seta("pausa", "menu", "Menu principal", exato=True,
           pontos=[(1075, 55), (1075, 22), (170, 22), (170, 55)])
    d.seta("pausa", "ctrl", "Controlos / voltar à pausa", exato=True, ambos=True,
           pontos=[(1170, 85), (1195, 85), (1195, 440), (170, 440), (170, 360)], pos_texto=0.55)
    d.seta("fim", "sel", "Mudar equipas", exato=True,
           pontos=[(1010, 360), (1010, 405), (480, 405), (480, 115)], pos_texto=0.4)
    d.seta("fim", "menu", "Menu principal", exato=True,
           pontos=[(1130, 360), (1130, 475), (30, 475), (30, 140), (110, 140), (110, 115)], pos_texto=0.3)
    return d


# ═══════════════════════════════════════════════════════════════════════
# 4. Fluxograma da decisão da IA
# ═══════════════════════════════════════════════════════════════════════
def fluxograma_ia():
    d = Diagrama("04_fluxograma_ia", 1050, 710, "Fluxograma da IA")
    d.caixa("ini", 370, 10, 260, 54, "Início do frame\n(para cada jogador da IA)", "terminal", "cinza")
    d.caixa("d1", 410, 100, 180, 90, "Tem a bola?", "losango", "amarelo")
    d.caixa("d2", 140, 215, 200, 100, "Perto da baliza\ne pode rematar?", "losango", "amarelo")
    d.caixa("rem", 20, 370, 180, 64, "ATACAR: rematar\n(com erro de mira)", "arredondado", "verde")
    d.caixa("d3", 260, 355, 180, 90, "Adversário\nno caminho?", "losango", "amarelo")
    d.caixa("pas", 180, 490, 180, 64, "ATACAR: passar ao\ncolega mais livre", "arredondado", "verde")
    d.caixa("av", 380, 490, 170, 64, "ATACAR: avançar\npara a baliza", "arredondado", "verde")
    d.caixa("d4", 660, 215, 200, 100, "Adversário\ntem a bola?", "losango", "amarelo")
    d.caixa("def", 880, 225, 160, 80, "DEFENDER\nvoltar à zona\n(depende do papel)", "arredondado", "vermelho")
    d.caixa("d5", 590, 355, 180, 90, "Colega\ntem a bola?", "losango", "amarelo")
    d.caixa("apo", 570, 490, 160, 70, "APOIAR\nir para a posição\ntática", "arredondado", "azul")
    d.caixa("per", 760, 490, 190, 70, "PERSEGUIR\nsó o mais perto\nvai à bola", "arredondado", "azul")
    d.caixa("fim", 360, 640, 300, 56, "Aplicar a velocidade ao jogador\n(player.py)", "terminal", "cinza")

    d.seta("ini", "d1")
    d.seta("d1", "d2", "Sim", exato=True, pontos=[(410, 145), (240, 145), (240, 215)])
    d.seta("d1", "d4", "Não", exato=True, pontos=[(590, 145), (760, 145), (760, 215)])
    d.seta("d2", "rem", "Sim", exato=True, pontos=[(140, 265), (110, 265), (110, 370)])
    d.seta("d2", "d3", "Não", exato=True, pontos=[(240, 315), (240, 400), (260, 400)])
    d.seta("d3", "pas", "Sim", exato=True, pontos=[(350, 445), (350, 470), (270, 470), (270, 490)])
    d.seta("d3", "av", "Não", exato=True, pontos=[(440, 400), (465, 400), (465, 490)])
    d.seta("d4", "def", "Sim", exato=True, pontos=[(860, 265), (880, 265)])
    d.seta("d4", "d5", "Não", exato=True, pontos=[(760, 315), (760, 335), (680, 335), (680, 355)])
    d.seta("d5", "apo", "Sim", exato=True, pontos=[(680, 445), (680, 470), (650, 470), (650, 490)])
    d.seta("d5", "per", "Não", exato=True, pontos=[(770, 400), (855, 400), (855, 490)])
    # Todas as ações acabam no mesmo sítio
    d.seta("rem", "fim", exato=True, pontos=[(110, 434), (110, 668), (360, 668)])
    d.seta("pas", "fim", exato=True, pontos=[(270, 554), (270, 610), (420, 610), (420, 640)])
    d.seta("av", "fim", exato=True, pontos=[(465, 554), (465, 640)])
    d.seta("apo", "fim", exato=True, pontos=[(620, 560), (620, 640)])
    d.seta("per", "fim", exato=True, pontos=[(855, 560), (855, 668), (660, 668)])
    d.seta("def", "per", exato=True, ponta=False, pontos=[(960, 305), (960, 668), (855, 668)])
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
    C("game", 420, 10, 300, 230, "Game",
      ["- estado: str", "- pausado: bool", "- golos_azul, golos_vermelho: int", "- parte: int",
       "- tempo_restante: float", "- dificuldade: str"],
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
    C("menus", 840, 180, 320, 120, "«menus» menu.py",
      ["MenuPrincipal · EcraControlos", "TeamSelectMenu · MenuPausa", "EcraFimJogo"],
      ["+ handle_event(event) → ação", "+ update(dt)", "+ draw()"], "cinza")
    C("ball", 380, 330, 260, 150, "Ball",
      ["- pos_x, pos_y: float", "- vel: Vector2", "- dono: Player"],
      ["+ update(dt, rink) → golo?", "+ definir_dono(jogador)", "+ libertar(velocidade)", "+ repor(pos)"])
    C("player", 700, 420, 290, 195, "Player",
      ["- pos_x, pos_y, vel_x, vel_y", "- equipa, numero, papel", "- tem_bola: bool", "- humano: bool"],
      ["+ update(dt, rink_rect, bola)", "+ set_target(vx, vy)", "+ fazer_passe(bola, dir)",
       "+ fazer_remate(bola, dir)", "+ sofrer_queda(...)", "+ empurrar_separar(outro)"])
    C("ia", 1040, 440, 130, 170, "AgentIA",
      ["- jogador", "- papel", "- cfg"],
      ["+ update(...)", "- _estado_atacar", "- _estado_defender", "- _estado_apoiar", "- _estado_perseguir"],
      "vermelho")
    C("gr", 380, 560, 260, 110, "Goalkeeper",
      ["- pos_x_fixo, pos_y", "- equipa, dificuldade"],
      ["+ update(dt, bola)", "+ bloquear_bola(bola)"])
    C("anim", 20, 540, 290, 110, "AnimationController",
      ["- estado: str", "- animacoes: dict"],
      ["+ update(dt)", "+ imagem: Surface"], "roxo")

    d.seta("game", "rink", "1")
    d.seta("rink", "cam", "1")
    d.seta("game", "hud", "1")
    d.seta("game", "menus", "1..5", pontos=[(780, 230)])
    d.seta("game", "ball", "1")
    d.seta("game", "player", "10", pontos=[(700, 330)])
    d.seta("game", "gr", "2", exato=True, pontos=[(440, 240), (440, 295), (345, 295), (345, 590), (380, 590)], pos_texto=0.55)
    d.seta("game", "ia", "9", exato=True, pontos=[(720, 150), (790, 150), (790, 395), (1105, 395), (1105, 440)], pos_texto=0.75)
    d.seta("ia", "player")
    d.caixa("tctrl", 985, 490, 60, 20, "controla", "texto", tam=11)
    d.seta("player", "anim", "1", exato=True, pontos=[(760, 615), (760, 715), (165, 715), (165, 650)], pos_texto=0.5)
    d.seta("gr", "anim", "1", exato=True, pontos=[(380, 630), (310, 630)])
    d.seta("ball", "player", "dono", tracejado=True, desvio=(0, 20))
    return d


# ═══════════════════════════════════════════════════════════════════════
# 7. Modelo de dados (base de dados SQLite do torneio — proposta)
# ═══════════════════════════════════════════════════════════════════════
def modelo_dados():
    d = Diagrama("07_modelo_dados", 1120, 440, "Modelo de dados (SQLite)")
    T = lambda id, x, y, w, h, t, campos, cor="roxo": d.caixa(id, x, y, w, h, tipo="classe", cor=cor, tam=12,
                                                              linhas=(t, [campos]))
    T("equipa", 20, 20, 240, 110, "Equipa",
      ["PK id", "nome", "cor_primaria", "cor_secundaria", "simbolo"])
    T("jogador", 20, 250, 240, 155, "Jogador",
      ["PK id", "FK equipa_id", "nome", "numero", "posicao", "velocidade", "remate", "passe"])
    T("torneio", 440, 20, 240, 95, "Torneio",
      ["PK id", "nome", "data_inicio", "estado"])
    T("partida", 440, 230, 240, 155, "Partida",
      ["PK id", "FK torneio_id", "FK casa_id", "FK fora_id", "golos_casa", "golos_fora", "dificuldade", "data"])
    T("estat", 860, 250, 240, 140, "Estatistica",
      ["PK id", "FK partida_id", "FK jogador_id", "golos", "remates", "passes", "faltas"])
    T("class", 860, 20, 240, 170, "Classificacao",
      ["PK, FK torneio_id", "PK, FK equipa_id", "jogos", "vitorias", "empates", "derrotas",
       "golos_marcados", "golos_sofridos", "pontos"])

    d.seta("equipa", "jogador", "1 : N", ponta=False)
    d.seta("torneio", "partida", "1 : N", ponta=False)
    d.seta("equipa", "partida", "1 : N\n(casa / fora)", ponta=False)
    d.seta("partida", "estat", "1 : N", ponta=False)
    d.seta("jogador", "estat", "1 : N", ponta=False, exato=True,
           pontos=[(140, 405), (140, 430), (980, 430), (980, 390)], pos_texto=0.5)
    d.seta("torneio", "class", "1 : N", ponta=False)
    d.seta("equipa", "class", "1 : N", ponta=False, exato=True,
           pontos=[(140, 20), (140, 5), (980, 5), (980, 20)], pos_texto=0.5)
    return d


if __name__ == "__main__":
    for f in (casos_de_uso, arquitetura, estados_jogo, fluxograma_ia, fluxograma_ciclo, classes, modelo_dados):
        dg = f()
        print(*dg.guardar(PASTA))
