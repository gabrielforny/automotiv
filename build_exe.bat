@echo off
cd /d %~dp0
call .venv\Scripts\activate
pyinstaller --noconfirm --clean --windowed --name AutomotivBot --add-data "config;config" --add-data "data;data" gui_launcher.py
pause
