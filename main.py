# -*- coding: utf-8 -*-
"""Ponto de entrada na raiz do projeto para executar o jogo diretamente."""
import os
import sys

pasta_jogo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hockey_game")
sys.path.insert(0, pasta_jogo)
os.chdir(pasta_jogo)

from game import Game

if __name__ == "__main__":
    Game().run()
