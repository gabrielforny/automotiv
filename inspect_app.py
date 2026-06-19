"""
Ferramenta de inspeção UIA — rode na máquina do cliente com o GRV aberto.
Salva a árvore de controles em inspect_output.txt para mapear os elementos da tela.

Uso:
    python inspect_app.py           # despeja a janela principal
    python inspect_app.py --popup   # despeja popups/dialogs visíveis
    python inspect_app.py --screenshot  # salva screenshot da tela atual
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    from pywinauto import Desktop, Application
    from pywinauto.controls.uiawrapper import UIAWrapper
except ImportError:
    print("pywinauto não instalado. Rode: pip install pywinauto")
    sys.exit(1)

TITLE_REGEX = r".*(CPS|GRV|AUTOMOTIV).*"
OUTPUT_FILE = Path("inspect_output.txt")


def dump_control(control, depth: int = 0, max_depth: int = 8) -> list[str]:
    if depth > max_depth:
        return []
    lines = []
    try:
        indent = "  " * depth
        rect = control.rectangle()
        info = (
            f"{indent}[{control.friendly_class_name()}] "
            f"title={control.window_text()!r} "
            f"auto_id={getattr(control, 'automation_id', lambda: '')()!r} "
            f"class={control.class_name()!r} "
            f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom})"
        )
        lines.append(info)
    except Exception as exc:
        lines.append(f"{'  ' * depth}<erro ao ler controle: {exc}>")
        return lines

    try:
        for child in control.children():
            lines.extend(dump_control(child, depth + 1, max_depth))
    except Exception:
        pass
    return lines


def take_screenshot() -> None:
    try:
        import pyautogui
        path = Path("inspect_screenshot.png")
        pyautogui.screenshot(str(path))
        print(f"Screenshot salvo em: {path.resolve()}")
    except Exception as exc:
        print(f"Erro ao tirar screenshot: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--popup", action="store_true", help="Inspeciona popups/dialogs visíveis")
    parser.add_argument("--screenshot", action="store_true", help="Salva screenshot da tela atual")
    parser.add_argument("--depth", type=int, default=8, help="Profundidade máxima (padrão: 8)")
    parser.add_argument("--filter", type=str, default="", help="Filtra linhas que contenham este texto")
    args = parser.parse_args()

    if args.screenshot:
        take_screenshot()

    desktop = Desktop(backend="uia")

    if args.popup:
        print("Procurando todas as janelas visíveis (exceto a janela principal do GRV)...")
        targets = []
        for win in desktop.windows():
            try:
                if not win.is_visible():
                    continue
                cls = win.class_name()
                text = win.window_text()
                rect = win.rectangle()
                # Ignora a janela principal do GRV
                import re as _re
                if _re.search(r"CPS|GRV|AUTOMOTIV", text):
                    continue
                # Ignora janelas minúsculas (ícones de bandeja, etc.)
                if rect.width() < 50 or rect.height() < 50:
                    continue
                targets.append(win)
                print(f"  Encontrado: [{cls}] {text!r} rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
            except Exception:
                pass
        if not targets:
            print("Nenhuma janela extra encontrada. Tentando a janela principal.")
    else:
        targets = []

    if not targets:
        print(f"Conectando à janela GRV ({TITLE_REGEX})...")
        try:
            window = desktop.window(title_re=TITLE_REGEX)
            window.set_focus()
            time.sleep(0.5)
            targets = [window]
            print(f"  Encontrado: {window.window_text()!r}")
        except Exception as exc:
            print(f"Janela GRV não encontrada: {exc}")
            print("Certifique-se de que o sistema GRV está aberto antes de rodar este script.")
            sys.exit(1)

    all_lines: list[str] = []
    for target in targets:
        try:
            name = target.window_text()
            all_lines.append(f"\n{'='*60}")
            all_lines.append(f"JANELA: {name!r}")
            all_lines.append(f"{'='*60}")
            all_lines.extend(dump_control(target, max_depth=args.depth))
        except Exception as exc:
            all_lines.append(f"Erro ao inspecionar janela: {exc}")

    if args.filter:
        filtered = [l for l in all_lines if args.filter.lower() in l.lower() or l.startswith("=")]
        all_lines = filtered

    output = "\n".join(all_lines)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"\nÁrvore de controles salva em: {OUTPUT_FILE.resolve()}")
    print(f"Total de linhas: {len(all_lines)}")

    if not args.filter:
        print("\n--- Prévia (primeiras 50 linhas) ---")
        for line in all_lines[:50]:
            print(line)


if __name__ == "__main__":
    main()
