@echo off
cd /d %~dp0
call .venv\Scripts\activate

REM Localiza o diretório do cv2 dentro do venv para copiar DLLs manualmente
for /f "tokens=*" %%i in ('python -c "import cv2, os; print(os.path.dirname(cv2.__file__))"') do set CV2_DIR=%%i
echo cv2 encontrado em: %CV2_DIR%

pyinstaller --noconfirm --clean --windowed --name AutomotivBot ^
  --add-data "config;config" ^
  --add-data "assets;assets" ^
  --add-data "data;data" ^
  --collect-all cv2 ^
  --collect-all numpy ^
  --hidden-import cv2 ^
  --add-binary "%CV2_DIR%\*.pyd;cv2" ^
  --manifest automotiv.manifest ^
  gui_launcher.py

pause
