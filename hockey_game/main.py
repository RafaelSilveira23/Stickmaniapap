# -*- coding: utf-8 -*-
"""main.py - ponto de entrada do jogo de hóquei em patins."""
import os
import sys

# Garante que a pasta hockey_game está sempre no sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import Game

if __name__ == "__main__":
    Game().run()
