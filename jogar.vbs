' jogar.vbs - abre o StickMania sem a janela preta da consola (cmd).
'
' 1. Procura um Python 3.10 ou mais recente que ja tenha o pygame-ce, usando a versao
'    "sem janela" do Python (pythonw / pyw).
' 2. Se encontrar, abre o jogo escondendo a consola.
' 3. Se nao encontrar, abre o jogar_com_consola.bat, que mostra o que falta e instala o pygame-ce.
Option Explicit

Dim sh, fso, pasta, candidatos, c, codigo, py, teste
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

pasta = fso.GetParentFolderName(WScript.ScriptFullName)
If Not fso.FileExists(pasta & "\hockey_game\main.py") Then
    MsgBox "Nao encontrei a pasta hockey_game ao lado do jogar.vbs." & vbCrLf & _
           "O jogar.vbs tem de estar na pasta principal do projeto.", vbCritical, "StickMania"
    WScript.Quit 1
End If
sh.CurrentDirectory = pasta & "\hockey_game"

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
    ' Falta o Python ou o pygame-ce: a versao com consola mostra o que se passa e instala o que falta
    sh.Run """" & pasta & "\jogar_com_consola.bat""", 1, False
End If
