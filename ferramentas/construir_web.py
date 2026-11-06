"""construir_web.py - cria a versão do StickMania que corre no browser (pygbag).

Executar (na pasta do projeto):
    python ferramentas/construir_web.py            -> cria build_web/site (o site pronto a publicar)
    python ferramentas/construir_web.py --testar   -> cria e abre um servidor em http://localhost:8000

O pygbag transforma um jogo pygame numa página web: o Python e o pygame-ce correm no browser
(WebAssembly). Como o pygbag empacota uma só pasta, este script junta numa pasta temporária
(build_web/stickmania) o jogo (hockey_game), os sprites (sprites_v2) e um main.py próprio para o
browser, e depois chama o pygbag.
"""
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "build_web")
APP = os.path.join(SAIDA, "stickmania")

MAIN_WEB = '''# main.py da versão web (gerado por ferramentas/construir_web.py)
import asyncio
import os
import sys

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hockey_game")
sys.path.insert(0, PASTA)
os.chdir(PASTA)


async def main():
    import pygame
    import pygame.font
    import pygame.mixer
    pygame.init()
    import navegador
    navegador.preparar()          # posição do rato certa em ecrãs com zoom
    from game import Game
    await Game().run_async()


asyncio.run(main())
'''

IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", "saves", "*.db", "requirements.txt")


def preparar():
    if os.path.isdir(APP):
        shutil.rmtree(APP)
    os.makedirs(APP)
    shutil.copytree(os.path.join(RAIZ, "hockey_game"), os.path.join(APP, "hockey_game"), ignore=IGNORAR)
    # Só os sprites que o jogo usa (as imagens de comparação soltas ficam de fora)
    shutil.copytree(os.path.join(RAIZ, "sprites_v2"), os.path.join(APP, "sprites_v2"),
                    ignore=shutil.ignore_patterns("antes_depois_*", "exemplos_*", "README.md", "spritesheet_nova.png"))
    os.makedirs(os.path.join(APP, "hockey_game", "saves"))
    with open(os.path.join(APP, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN_WEB)
    for nome in ("template.tmpl", "favicon.png"):
        origem = os.path.join(RAIZ, "web", nome)
        if os.path.exists(origem):
            shutil.copy(origem, os.path.join(APP, nome))


def construir(testar: bool):
    args = [sys.executable, "-m", "pygbag", "--title", "StickMania", "--app_name", "stickmania",
            "--ume_block", "0", "--package", "pt.stickmania.pap",
            # Os sons são WAV (gerados pelo sons.py); o Chrome, o Edge e o Firefox tocam-nos bem
            "--disable-sound-format-error"]
    if os.path.exists(os.path.join(APP, "template.tmpl")):
        args += ["--template", "template.tmpl"]
    if not testar:
        args.append("--build")
    args.append(APP)
    subprocess.run(args, check=True, cwd=SAIDA)
    site = os.path.join(SAIDA, "site")
    if os.path.isdir(site):
        shutil.rmtree(site)
    shutil.copytree(os.path.join(APP, "build", "web"), site)
    ajustar_pagina(os.path.join(site, "index.html"))
    with open(os.path.join(site, ".nojekyll"), "w"):
        pass                                   # o GitHub Pages serve os ficheiros tal como estão
    print("Site pronto em", site)


# Acrescentado à página do pygbag: o jogo ocupa a janela sem se deformar (16:9, centrado), também
# em ecrãs com mais píxeis por ponto (portáteis com zoom de 125-200 %), e textos em português.
ESTILO = """
<meta name="description" content="StickMania: jogo de hóquei em patins em 2D, feito em Python (pygame) para a PAP.
Joga contra o computador ou online contra um amigo, diretamente no browser.">
<style>
  html, body { background: #05080f !important; overflow: hidden; }
  canvas#canvas {
    position: fixed !important; inset: 0 !important; margin: auto !important;
    width: min(100vw, calc(100vh * 16 / 9)) !important;
    height: min(100vh, calc(100vw * 9 / 16)) !important;
  }
  #infobox { background: #12305e !important; color: #ffffff !important; border-radius: 10px;
             font-family: Arial, sans-serif !important; }
  #status { color: #9fb4dd !important; }
</style>
"""


def ajustar_pagina(caminho: str):
    with open(caminho, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</head>", ESTILO + "</head>", 1)
    html = html.replace("Loading, please wait ...", "A carregar o StickMania...")
    html = html.replace('<html lang="en-us">', '<html lang="pt">', 1)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    preparar()
    construir("--testar" in sys.argv)
