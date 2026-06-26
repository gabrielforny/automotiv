import ctypes
import sys

# Declara DPI awareness antes de qualquer import de UI ou PyAutoGUI.
# Sem isso, o Windows aplica virtualização de DPI no .exe (escala 125%/150%)
# e o PyAutoGUI captura screenshots em resolução menor que a real,
# fazendo todas as imagens falharem na escala 1.0 e cair nos 5 fallbacks lentos.
# PROCESS_PER_MONITOR_DPI_AWARE (valor 2) = sem virtualização, pixels reais.
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from src.app_gui import run_gui

if __name__ == "__main__":
    run_gui()
