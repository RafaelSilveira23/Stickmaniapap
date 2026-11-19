"""construir_msix.py - cria o pacote do StickMania para a Microsoft Store (StickMania.msix).

Executar (na pasta do projeto), depois do construir_app.py:
    python ferramentas/construir_app.py
    python ferramentas/construir_msix.py

Porquê: o Windows 11 (Controlo Inteligente de Aplicações) bloqueia programas sem assinatura digital.
Na Microsoft Store é a própria Microsoft que assina o pacote, por isso o jogo instala-se sem avisos.

O pacote usa a pasta build_app/dist/StickMania feita pelo construir_app.py, junta-lhe os ícones e o
AppxManifest.xml e empacota tudo com o makeappx.exe da Microsoft. O makeappx vem do Windows SDK ou do
pacote NuGet Microsoft.Windows.SDK.BuildTools: põe a pasta bin/<versão>/x64 desse pacote em
build_app/sdk, ou indica o caminho na variável de ambiente MAKEAPPX.

Os dados da identidade (Name, Publisher e PublisherDisplayName) são os que o Partner Center dá depois
de reservar o nome «StickMania» (Gestão de produtos -> Identidade do produto). Escrevem-se em
ferramentas/loja.json; sem eles o pacote é criado com valores de exemplo, que a Store recusa.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOGO = os.path.join(RAIZ, "hockey_game")
SAIDA = os.path.join(RAIZ, "build_app")
APP = os.path.join(SAIDA, "dist", "StickMania")
PASTA_MSIX = os.path.join(SAIDA, "msix")
LOJA = os.path.join(RAIZ, "ferramentas", "loja.json")

EXEMPLO = {
    "Name": "StickMania.Exemplo",
    "Publisher": "CN=00000000-0000-0000-0000-000000000000",
    "PublisherDisplayName": "Rafael Silveira",
}

# (nome do ficheiro, largura, altura, fração do lado ocupada pelo emblema)
ICONES = [
    ("StoreLogo.png", 50, 50, 0.9),
    ("Square44x44Logo.png", 44, 44, 0.95),
    ("Square44x44Logo.targetsize-256_altform-unplated.png", 256, 256, 0.95),
    ("Square150x150Logo.png", 150, 150, 0.7),
    ("Wide310x150Logo.png", 310, 150, 0.7),
    ("SplashScreen.png", 620, 300, 0.7),
]

MANIFESTO = """<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">
  <Identity Name="{Name}" Publisher="{Publisher}" Version="{versao}" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>StickMania</DisplayName>
    <PublisherDisplayName>{PublisherDisplayName}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <Description>Jogo de hóquei em patins: jogo rápido, jogo online, modo carreira e carreira de jogador.</Description>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="pt-PT" />
  </Resources>
  <Applications>
    <Application Id="StickMania" Executable="StickMania.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="StickMania" Description="Jogo de hóquei em patins"
        BackgroundColor="transparent" Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" ShortName="StickMania">
          <uap:ShowNameOnTiles>
            <uap:ShowOn Tile="square150x150Logo" />
            <uap:ShowOn Tile="wide310x150Logo" />
          </uap:ShowNameOnTiles>
        </uap:DefaultTile>
        <uap:SplashScreen Image="Assets\\SplashScreen.png" BackgroundColor="#070b1c" />
      </uap:VisualElements>
    </Application>
  </Applications>
  <Capabilities>
    <Capability Name="internetClient" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""


def versao_do_jogo() -> str:
    """A Store quer quatro números e o último tem de ser 0: a versão 37 do jogo dá 1.37.0.0."""
    sys.path.insert(0, JOGO)
    from settings import VERSAO_JOGO
    return f"1.{int(VERSAO_JOGO)}.0.0"


def identidade() -> dict:
    if os.path.exists(LOJA):
        with open(LOJA, encoding="utf-8") as f:
            return {**EXEMPLO, **json.load(f)}
    print("AVISO: falta ferramentas/loja.json; o pacote leva uma identidade de exemplo (só serve para testar).")
    return dict(EXEMPLO)


def criar_icones(pasta: str):
    from PIL import Image
    emblema = Image.open(os.path.join(JOGO, "assets", "ui", "emblema_sticks.png")).convert("RGBA")
    emblema = emblema.crop(emblema.getbbox())
    for nome, w, h, fracao in ICONES:
        lado = int(min(w, h) * fracao)
        img = emblema.copy()
        img.thumbnail((lado, lado), Image.LANCZOS)
        tela = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tela.paste(img, ((w - img.width) // 2, (h - img.height) // 2), img)
        tela.save(os.path.join(pasta, nome))


def encontrar_makeappx() -> str:
    candidatos = [os.environ.get("MAKEAPPX", "")]
    candidatos += glob.glob(os.path.join(SAIDA, "sdk", "**", "makeappx.exe"), recursive=True)
    candidatos += sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe"), reverse=True)
    for c in candidatos:
        if c and os.path.isfile(c):
            return c
    sys.exit("Não encontrei o makeappx.exe (ver as instruções no início deste ficheiro).")


if __name__ == "__main__":
    if not os.path.isdir(APP):
        sys.exit("Falta build_app/dist/StickMania: corre primeiro python ferramentas/construir_app.py")
    dados = identidade()
    dados["versao"] = versao_do_jogo()

    if os.path.isdir(PASTA_MSIX):
        shutil.rmtree(PASTA_MSIX)
    shutil.copytree(APP, PASTA_MSIX)
    os.makedirs(os.path.join(PASTA_MSIX, "Assets"))
    criar_icones(os.path.join(PASTA_MSIX, "Assets"))
    with open(os.path.join(PASTA_MSIX, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(MANIFESTO.format(**dados))

    pacote = os.path.join(SAIDA, f"StickMania_{dados['versao']}_x64.msix")
    subprocess.run([encontrar_makeappx(), "pack", "/o", "/h", "SHA256", "/d", PASTA_MSIX, "/p", pacote], check=True)
    print("Pacote:", pacote, f"({os.path.getsize(pacote) / 1e6:.1f} MB)", "versão", dados["versao"])
