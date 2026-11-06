# -*- coding: utf-8 -*-
"""main.py - ponto de entrada do jogo de hóquei em patins.

O jogo é aberto pelo jogar.vbs com o pythonw (sem a janela preta da consola). Sem consola,
um erro não se veria: por isso, se o jogo fechar com um erro, a mensagem fica gravada em
saves/erro.txt e aparece numa janela do Windows.
"""
import os
import sys
import traceback

PASTA = os.path.dirname(os.path.abspath(__file__))
# Garante que a pasta hockey_game está sempre no sys.path e é a pasta atual
sys.path.insert(0, PASTA)
os.chdir(PASTA)


def _mostrar_erro(texto: str):
    try:
        from carreira import PASTA_SAVES     # no programa instalado é %APPDATA%\StickMania
    except Exception:
        PASTA_SAVES = os.path.join(PASTA, "saves")
    caminho = os.path.join(PASTA_SAVES, "erro.txt")
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        caminho = "(não foi possível gravar o ficheiro)"
    if sys.stderr is not None:
        print(texto, file=sys.stderr)
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "O StickMania fechou com um erro.\n\n" + texto[-900:] +
            f"\n\nA mensagem completa ficou em:\n{caminho}", "StickMania - erro", 0x10)


if __name__ == "__main__":
    try:
        from game import Game
        Game().run()
    except SystemExit:
        raise
    except Exception:
        _mostrar_erro(traceback.format_exc())
        sys.exit(1)
