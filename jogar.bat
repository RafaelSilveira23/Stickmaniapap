@echo off
title StickMania PAP - Hoquei em Patins
cd /d "%~dp0\hockey_game"
"C:\Users\Heito\AppData\Local\Python\bin\python.exe" main.py
if errorlevel 1 pause
