@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RELATORIO PULMAO
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
  pause
  exit /b 1
)
echo Verificando dependencias (na primeira vez pode demorar)...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo Abrindo o RELATORIO PULMAO no navegador...
echo.| python -m streamlit run main.py
pause
