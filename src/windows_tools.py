from __future__ import annotations

import os
from pathlib import Path


def find_desktop_shortcut(shortcut_name: str) -> Path:
    candidates = [
        Path.home() / "Desktop" / shortcut_name,
        Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop" / shortcut_name,
        Path.home() / "OneDrive" / "Área de Trabalho" / shortcut_name,
        Path.home() / "OneDrive" / "Desktop" / shortcut_name,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Atalho não encontrado. Verifique se o atalho existe na Área de Trabalho: "
        f"{shortcut_name}. Caminhos testados: {', '.join(str(c) for c in candidates)}"
    )
