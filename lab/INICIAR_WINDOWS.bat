@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
 py -3 -m pip install -r requirements.txt
 py -3 aulaos_lab.py
) else (
 where python >nul 2>&1
 if %errorlevel%==0 (
  python -m pip install -r requirements.txt
  python aulaos_lab.py
 ) else (
  echo Falta Python. Descargalo de https://www.python.org/downloads/windows/
  echo En versiones posteriores distribuiremos un .exe sin instalar Python.
  pause
 )
)
