"""instalador.py - o instalador do StickMania (StickMania-Instalar.exe).

O ferramentas/construir_app.py junta este ficheiro e o jogo já pronto (StickMania.zip) num só
.exe. Quando alguém o abre:
  1. mostra uma janela com o botão INSTALAR;
  2. descomprime o jogo para %LOCALAPPDATA%\\Programs\\StickMania (não precisa de administrador);
  3. cria os atalhos no menu Iniciar e no ambiente de trabalho;
  4. regista o jogo nas "Aplicações instaladas" do Windows, com o desinstalador.
Os jogos gravados ficam em %APPDATA%\\StickMania e não se perdem ao instalar uma versão nova.

Opções (para testar):  --pasta X  --sem-atalhos  --sem-registo  --silencioso  --desinstalar
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile

NOME = "StickMania"
VERSAO = "33"
EDITOR = "Rafael da Hora Silveira e Vasco Andreia (PAP)"
CHAVE_REGISTO = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StickMania"
SEM_JANELA = 0x08000000                     # CREATE_NO_WINDOW (o PowerShell não abre consola)


def recurso(nome: str) -> str:
    """Ficheiros que vêm dentro do instalador (o PyInstaller põe-nos em sys._MEIPASS)."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), nome)


def pasta_padrao() -> str:
    return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", NOME)


def opcao(nome: str):
    if nome in sys.argv:
        i = sys.argv.index(nome)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else True
    return None


def powershell(comando: str):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
                   creationflags=SEM_JANELA, check=False)


def caminhos_atalhos() -> list:
    """Menu Iniciar e ambiente de trabalho (pergunta ao Windows, por causa do OneDrive)."""
    iniciar = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                           capture_output=True, text=True, creationflags=SEM_JANELA)
        ambiente = r.stdout.strip() or os.path.join(os.path.expanduser("~"), "Desktop")
    except OSError:
        ambiente = os.path.join(os.path.expanduser("~"), "Desktop")
    return [os.path.join(iniciar, NOME + ".lnk"), os.path.join(ambiente, NOME + ".lnk")]


def criar_atalho(lnk: str, alvo: str, pasta: str):
    def q(t):
        return t.replace("'", "''")
    powershell(f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{q(lnk)}'); "
               f"$s.TargetPath = '{q(alvo)}'; $s.WorkingDirectory = '{q(pasta)}'; "
               f"$s.IconLocation = '{q(alvo)},0'; $s.Description = 'Jogo de hóquei em patins'; $s.Save()")


def registar(pasta: str, exe: str, desinstalador: str):
    import winreg
    tamanho = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(pasta) for f in fs) // 1024
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CHAVE_REGISTO) as k:
        for nome, valor in (("DisplayName", NOME), ("DisplayVersion", VERSAO), ("Publisher", EDITOR),
                            ("DisplayIcon", exe), ("InstallLocation", pasta),
                            ("UninstallString", f'"{desinstalador}" --desinstalar')):
            winreg.SetValueEx(k, nome, 0, winreg.REG_SZ, valor)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, tamanho)
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def instalar(pasta: str, atalhos: bool, registo: bool, progresso=lambda f: None) -> str:
    """Descomprime o jogo e cria atalhos e registo. Devolve o caminho do StickMania.exe."""
    # Versão antiga: apaga-se (os jogos gravados estão noutra pasta e ficam)
    if os.path.isdir(pasta):
        shutil.rmtree(pasta, ignore_errors=True)
    os.makedirs(pasta, exist_ok=True)
    with zipfile.ZipFile(recurso("StickMania.zip")) as z:
        nomes = z.namelist()
        for i, n in enumerate(nomes):
            z.extract(n, pasta)
            if i % 25 == 0:
                progresso(0.9 * i / len(nomes))
    exe = os.path.join(pasta, NOME + ".exe")
    desinstalador = os.path.join(pasta, "Desinstalar.exe")
    if getattr(sys, "frozen", False):
        shutil.copy2(sys.executable, desinstalador)
    progresso(0.93)
    if atalhos:
        for lnk in caminhos_atalhos():
            os.makedirs(os.path.dirname(lnk), exist_ok=True)
            criar_atalho(lnk, exe, pasta)
    progresso(0.97)
    if registo:
        registar(pasta, exe, desinstalador)
    progresso(1.0)
    return exe


def desinstalar(silencioso: bool = False):
    import winreg
    pasta = os.path.dirname(os.path.abspath(sys.executable))
    # Segurança: só apaga a pasta se for mesmo a do jogo (tem o StickMania.exe)
    if not os.path.isfile(os.path.join(pasta, NOME + ".exe")):
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "O desinstalador tem de estar na pasta do StickMania.", NOME, 0x10)
        return
    if not silencioso:
        import ctypes
        r = ctypes.windll.user32.MessageBoxW(None, "Queres desinstalar o StickMania?\n\nOs jogos gravados "
                                             "(modo carreira) ficam guardados.", "StickMania", 0x24)
        if r != 6:          # 6 = Sim
            return
    for lnk in caminhos_atalhos():
        try:
            os.remove(lnk)
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CHAVE_REGISTO)
    except OSError:
        pass
    # O próprio desinstalador está dentro da pasta: apaga-a um pouco depois de fechar
    for item in os.listdir(pasta):
        caminho = os.path.join(pasta, item)
        if os.path.abspath(caminho) != os.path.abspath(sys.executable):
            shutil.rmtree(caminho, ignore_errors=True) if os.path.isdir(caminho) else _apagar(caminho)
    subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{pasta}"', creationflags=SEM_JANELA,
                     cwd=tempfile.gettempdir())
    if not silencioso:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "O StickMania foi desinstalado.", "StickMania", 0x40)


def _apagar(caminho):
    try:
        os.remove(caminho)
    except OSError:
        pass


# ---------------------------------------------------------------------- janela
def janela():
    import tkinter as tk
    from tkinter import ttk

    pasta = opcao("--pasta") or pasta_padrao()
    raiz = tk.Tk()
    raiz.title("Instalar o StickMania")
    raiz.configure(bg="#0b1426")
    raiz.resizable(False, False)
    try:
        raiz.iconbitmap(recurso("stickmania.ico"))
    except tk.TclError:
        pass
    largura, altura = 520, 400
    raiz.geometry(f"{largura}x{altura}+{(raiz.winfo_screenwidth() - largura) // 2}+"
                  f"{(raiz.winfo_screenheight() - altura) // 3}")

    try:
        logo = tk.PhotoImage(file=recurso("logo.png"))
        tk.Label(raiz, image=logo, bg="#0b1426").pack(pady=(22, 6))
    except tk.TclError:
        pass
    tk.Label(raiz, text="StickMania", font=("Arial", 26, "bold"), fg="white", bg="#0b1426").pack()
    tk.Label(raiz, text="Jogo de hóquei em patins  •  versão " + VERSAO, font=("Arial", 11),
             fg="#9fb4dd", bg="#0b1426").pack(pady=(0, 14))
    info = tk.Label(raiz, text="Vai ser instalado em:\n" + pasta, font=("Arial", 9), fg="#c8d4ee", bg="#0b1426",
                    justify="center", wraplength=460)
    info.pack()
    atalho = tk.BooleanVar(value=True)
    tk.Checkbutton(raiz, text="Criar atalho no ambiente de trabalho", variable=atalho, font=("Arial", 10),
                   fg="white", bg="#0b1426", selectcolor="#12305e", activebackground="#0b1426",
                   activeforeground="white").pack(pady=10)
    barra = ttk.Progressbar(raiz, length=420, mode="determinate", maximum=1.0)
    barra.pack(pady=(4, 12))
    botao = tk.Button(raiz, text="INSTALAR", font=("Arial", 14, "bold"), fg="white", bg="#27ae60",
                      activebackground="#2ecc71", activeforeground="white", relief="flat", width=18,
                      cursor="hand2")
    botao.pack()
    estado = {"exe": None, "erro": None}

    def progresso(f):
        raiz.after(0, lambda: barra.configure(value=f))

    def trabalho():
        try:
            estado["exe"] = instalar(pasta, atalhos=not opcao("--sem-atalhos"), registo=not opcao("--sem-registo"),
                                     progresso=progresso)
        except Exception as e:          # mostra o erro na janela em vez de fechar
            estado["erro"] = str(e)
        raiz.after(0, terminado)

    def terminado():
        if estado["erro"]:
            info.configure(text="Não foi possível instalar:\n" + estado["erro"], fg="#ff8070")
            botao.configure(text="FECHAR", bg="#c0392b", state="normal", command=raiz.destroy)
            return
        info.configure(text="O StickMania está instalado!\nTambém o encontras no menu Iniciar.", fg="#7be3a0")
        botao.configure(text="JOGAR AGORA", state="normal", command=abrir)

    def abrir():
        subprocess.Popen([estado["exe"]], cwd=os.path.dirname(estado["exe"]))
        raiz.destroy()

    def comecar():
        botao.configure(state="disabled", text="A INSTALAR...")
        threading.Thread(target=trabalho, daemon=True).start()

    botao.configure(command=comecar)
    raiz.mainloop()


if __name__ == "__main__":
    if opcao("--desinstalar"):
        desinstalar(silencioso=bool(opcao("--silencioso")))
    elif opcao("--silencioso"):
        print(instalar(opcao("--pasta") or pasta_padrao(), atalhos=not opcao("--sem-atalhos"),
                       registo=not opcao("--sem-registo")))
    else:
        janela()
