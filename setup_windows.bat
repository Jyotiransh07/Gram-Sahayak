@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 (echo Please install Python 3.11 first. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
mkdir data\audio 2>nul
mkdir data\uploads 2>nul
echo Core setup finished. Install voice extras: pip install -r requirements-voice.txt
echo See README.md and API_SETUP.md for complete setup.
pause
