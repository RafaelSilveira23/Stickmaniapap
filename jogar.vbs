' jogar.vbs - abre o StickMania sem a janela preta da consola (cmd).
'
' 1. Procura um Python 3.10 ou mais recente que ja tenha o pygame-ce, usando a versao
'    "sem janela" do Python (pythonw / pyw).
' 2. Se encontrar, abre o jogo escondendo a consola.
' 3. Se nao encontrar, explica numa janela o que falta (para so jogar, o melhor e o instalador).
' Se o jogo fechar com um erro, o proprio jogo mostra a mensagem numa janela (ver jogo/main.py).
Option Explicit

Dim sh, fso, pasta, candidatos, c, codigo, py, teste
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

pasta = fso.GetParentFolderName(WScript.ScriptFullName)
If Not fso.FileExists(pasta & "\jogo\main.py") Then
    MsgBox "Nao encontrei a pasta jogo ao lado do jogar.vbs." & vbCrLf & _
           "O jogar.vbs tem de estar na pasta principal do projeto.", vbCritical, "StickMania"
    WScript.Quit 1
End If
sh.CurrentDirectory = pasta & "\jogo"

candidatos = Array(sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Python\bin\pythonw.exe", "pyw", "pythonw")
teste = " -c ""import sys, pygame; sys.exit(sys.version_info < (3, 10))"""
py = ""
For Each c In candidatos
    If InStr(c, "\") = 0 Or fso.FileExists(c) Then
        On Error Resume Next
        codigo = sh.Run("""" & c & """" & teste, 0, True)
        If Err.Number = 0 And codigo = 0 Then py = c
        Err.Clear
        On Error GoTo 0
    End If
    If py <> "" Then Exit For
Next

If py <> "" Then
    ' 1 = janela normal. O pythonw nunca abre a consola, por isso nao aparece o cmd.
    ' (Com 0 o Windows escondia tambem a janela do proprio jogo: o jogo corria, mas invisivel.)
    sh.Run """" & py & """ main.py", 1, False
Else
    ' Falta o Python ou o pygame-ce: explica o que fazer
    MsgBox "Para abrir o StickMania a partir do codigo e preciso o Python 3.10 (ou mais recente) " & _
           "com o pygame-ce." & vbCrLf & vbCrLf & _
           "Para so jogar, o mais simples e o instalador:" & vbCrLf & _
           "   download\StickMania-Instalar.exe" & vbCrLf & vbCrLf & _
           "Para instalar o que falta, abre uma linha de comandos nesta pasta e escreve:" & vbCrLf & _
           "   pip install -r jogo\requirements.txt", vbExclamation, "StickMania"
End If
