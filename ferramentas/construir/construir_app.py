"""construir_app.py - cria o programa do StickMania para Windows e o instalador.

Executar (na pasta do projeto; precisa do PyInstaller: pip install pyinstaller):
    python ferramentas/construir/construir_app.py

Passos:
  1. o PyInstaller transforma o jogo (jogo/main.py e os módulos que ele usa) num
     programa, StickMania.exe, com o Python e o pygame lá dentro: quem o usa não precisa de
     instalar o Python;
  2. junta-lhe as imagens, os sons, os emblemas e os sprites (jogo/recursos);
  3. comprime tudo num StickMania.zip;
  4. cria o instalador, StickMania-Instalar.exe (ferramentas/construir/instalador.py + o zip), que é o
     ficheiro que se dá às pessoas.
O resultado fica em build_app/ (não vai para o Git). O instalador é copiado para download/.
"""
import os
import shutil
import subprocess
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
JOGO = os.path.join(RAIZ, "jogo")
RECURSOS = os.path.join(JOGO, "recursos")
SUBPASTAS = ("partida", "modos", "clubes", "ecras", "multijogador", "som")   # as de jogo/caminhos.py
SAIDA = os.path.join(RAIZ, "build_app")
DIST = os.path.join(SAIDA, "dist")
SEP = ";" if os.name == "nt" else ":"


def pyinstaller(*args):
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--distpath", DIST, "--workpath", os.path.join(SAIDA, "work"), "--specpath", SAIDA, *args],
                   check=True, cwd=RAIZ)


def criar_icone():
    """O emblema dos sticks cruzados em .ico (vários tamanhos) e um logo para a janela do instalador."""
    from PIL import Image
    img = Image.open(os.path.join(RECURSOS, "ui", "emblema_sticks.png")).convert("RGBA")
    lado = max(img.size)
    quadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    quadrado.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
    ico = os.path.join(SAIDA, "stickmania.ico")
    quadrado.save(ico, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    quadrado.resize((96, 96), Image.LANCZOS).save(os.path.join(SAIDA, "logo.png"))
    return ico


def construir_jogo(ico: str):
    pyinstaller("--windowed", "--name", "StickMania", "--icon", ico,
                "--paths", JOGO, *[a for s in SUBPASTAS for a in ("--paths", os.path.join(JOGO, s))],
                *[a for p in ("ui", "sons", "simbolos")
                  for a in ("--add-data", f"{os.path.join(RECURSOS, p)}{SEP}{os.path.join('recursos', p)}")],
                "--exclude-module", "tkinter",
                os.path.join(JOGO, "main.py"))
    app = os.path.join(DIST, "StickMania")
    # Os sprites vão para recursos/sprites, dentro da pasta do programa (ver jogo/caminhos.py),
    # sem as imagens de exemplo
    shutil.copytree(os.path.join(RECURSOS, "sprites"), os.path.join(app, "_internal", "recursos", "sprites"),
                    ignore=shutil.ignore_patterns("antes_depois_*", "exemplos_*", "README.md", "spritesheet_nova.png"))
    return app


def comprimir(app: str) -> str:
    zip_ = os.path.join(SAIDA, "StickMania.zip")
    with zipfile.ZipFile(zip_, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for raiz, _, ficheiros in os.walk(app):
            for f in ficheiros:
                caminho = os.path.join(raiz, f)
                z.write(caminho, os.path.relpath(caminho, app))
    return zip_


def construir_instalador(ico: str, zip_: str) -> str:
    pyinstaller("--onefile", "--windowed", "--name", "StickMania-Instalar", "--icon", ico,
                "--add-data", f"{zip_}{SEP}.",
                "--add-data", f"{ico}{SEP}.",
                "--add-data", f"{os.path.join(SAIDA, 'logo.png')}{SEP}.",
                os.path.join(AQUI, "instalador.py"))
    exe = os.path.join(DIST, "StickMania-Instalar.exe")
    pasta_download = os.path.join(RAIZ, "download")
    os.makedirs(pasta_download, exist_ok=True)
    shutil.copy2(exe, pasta_download)
    return os.path.join(pasta_download, "StickMania-Instalar.exe")


if __name__ == "__main__":
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(SAIDA, exist_ok=True)
    icone = criar_icone()
    pasta_app = construir_jogo(icone)
    print("Programa:", pasta_app)
    z = comprimir(pasta_app)
    print("Zip:", z, f"({os.path.getsize(z) / 1e6:.1f} MB)")
    inst = construir_instalador(icone, z)
    print("Instalador:", inst, f"({os.path.getsize(inst) / 1e6:.1f} MB)")
