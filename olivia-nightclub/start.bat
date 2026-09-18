@echo off
rem Lance OLIVIA Nightclubs (Windows). Double-clic ou "start.bat" dans un terminal.
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=py
"%PY%" -X utf8 -m pip install -q -r requirements.txt
echo.
echo   OLIVIA Nightclubs -- http://localhost:8000
echo.
"%PY%" -X utf8 run.py
