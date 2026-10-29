@echo off
setlocal
title StickMania PAP - Hoquei em Patins
cd /d "%~dp0hockey_game" 2>nul
if not exist "main.py" goto sem_pasta

rem --- 1. Procurar um Python 3.10+ que ja tenha o pygame-ce ---
set "PYEXE="
call :testar "%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PYEXE call :testar py
if not defined PYEXE call :testar python
if not defined PYEXE call :testar python3
if defined PYEXE goto jogar

rem --- 2. Nenhum tem o pygame: procurar qualquer Python 3.10+ e instalar ---
set "PYBASE="
call :base "%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PYBASE call :base py
if not defined PYBASE call :base python
if not defined PYBASE call :base python3
if not defined PYBASE goto sem_python

echo O pygame-ce nao esta instalado. A instalar com: %PYBASE%
"%PYBASE%" -m pip install pygame-ce
call :testar "%PYBASE%"
if not defined PYEXE goto sem_pygame

:jogar
echo A usar o Python: %PYEXE%
"%PYEXE%" main.py
if errorlevel 1 goto erro_jogo
exit /b 0

rem ---------------------------------------------------------------
:testar
"%~1" -c "import sys, pygame; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if not errorlevel 1 set "PYEXE=%~1"
exit /b

:base
"%~1" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if not errorlevel 1 set "PYBASE=%~1"
exit /b

:sem_pasta
echo [ERRO] Nao encontrei a pasta hockey_game ao lado deste ficheiro.
echo O jogar.bat tem de estar na pasta principal do projeto.
pause
exit /b 1

:sem_python
echo [ERRO] Nao encontrei o Python 3.10 ou mais recente.
echo Instala o Python em https://www.python.org/downloads/ e marca "Add python.exe to PATH".
pause
exit /b 1

:sem_pygame
echo [ERRO] Nao foi possivel instalar o pygame-ce.
echo Tenta numa linha de comandos: python -m pip install pygame-ce
pause
exit /b 1

:erro_jogo
echo.
echo [ERRO] O jogo fechou com um erro. Copia a mensagem acima e envia-a.
pause
exit /b 1
