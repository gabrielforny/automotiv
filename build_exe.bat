@echo off
cd /d %~dp0
call .venv\Scripts\activate
pyinstaller --noconfirm --clean --windowed --name AutomotivBot ^
  --add-data "config;config" ^
  --add-data "assets;assets" ^
  --add-data "data;data" ^
  --collect-all cv2 ^
  gui_launcher.py
pause
