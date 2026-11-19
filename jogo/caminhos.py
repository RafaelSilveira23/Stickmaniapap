# -*- coding: utf-8 -*-
"""caminhos.py - onde está cada coisa do jogo (o primeiro módulo a ser importado).

O código está organizado em subpastas por tema:
    partida/       o que acontece no rinque: bola, jogadores, guarda-redes, IA, faltas, fintas...
    modos/         modo carreira, carreira de jogador, tutorial e dois jogadores no mesmo PC
    clubes/        equipas, planteis, emblemas e cores dos equipamentos
    ecras/         menus, painel do jogo e peças da interface
    multijogador/  jogo online (ligação ao servidor) e contas
    som/           efeitos sonoros e cânticos dos clubes
    recursos/      imagens, sons, emblemas e sprites
As subpastas são só para organizar: este módulo junta-as ao caminho do Python (sys.path), por isso
cada ficheiro continua a importar os outros só pelo nome (ex.: "import comando").

No programa instalado (StickMania.exe, feito pelo PyInstaller) os recursos estão dentro da pasta
do programa (sys._MEIPASS) e os jogos gravados ficam em %APPDATA%\\StickMania.
"""
import os
import sys

PASTA_JOGO = os.path.dirname(os.path.abspath(__file__))
SUBPASTAS = ("partida", "modos", "clubes", "ecras", "multijogador", "som")
for _sub in SUBPASTAS:
    _caminho = os.path.join(PASTA_JOGO, _sub)
    if _caminho not in sys.path:
        sys.path.append(_caminho)

INSTALADO = bool(getattr(sys, "frozen", False))
RECURSOS = os.path.join(getattr(sys, "_MEIPASS", PASTA_JOGO) if INSTALADO else PASTA_JOGO, "recursos")
PASTA_UI = os.path.join(RECURSOS, "ui")                 # stick, bola e emblema do ecrã do remate e dos menus
PASTA_SONS = os.path.join(RECURSOS, "sons")             # efeitos sonoros (.wav) e cânticos (sons/canticos)
PASTA_SIMBOLOS = os.path.join(RECURSOS, "simbolos")     # emblemas dos clubes
PASTA_SPRITES = os.path.join(RECURSOS, "sprites")       # sprites dos jogadores, guarda-redes e bola

if INSTALADO:
    # Programa instalado: os jogos gravados ficam em %APPDATA%\\StickMania, para não se perderem
    # quando se instala uma versão nova
    PASTA_SAVES = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "StickMania")
else:
    PASTA_SAVES = os.path.join(PASTA_JOGO, "saves")
