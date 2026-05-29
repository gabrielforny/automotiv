from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class AppConfig(BaseModel):
    shortcut_name: str
    window_title_regex: str
    login_password: str
    wait_after_login_seconds: int = 15
    wait_after_open_screen_seconds: int = 5


class ExcelColumnsConfig(BaseModel):
    code_or_reference: str
    quantity: str
    item: str | None = None


class ExcelConfig(BaseModel):
    default_path: str
    header_row: int = 7
    first_data_row: int = 8
    columns: ExcelColumnsConfig


class SearchConfig(BaseModel):
    fallback_site: str
    active_first: bool = True
    try_inactive_when_not_found: bool = True
    min_grid_rows_to_consider_found: int = 1


class RuntimeConfig(BaseModel):
    dry_run: bool = False
    use_image_fallback: bool = True
    pause_between_actions_seconds: float = 0.5
    log_level: str = "INFO"

class ImagesConfig(BaseModel):
    assets_dir: str = "assets/images"
    confidence: float = 0.85
    login_button: str = "login_button.png"
    password_input: str = "input_senha.png"
    nome_login_input: str = "input_nome_login.png"
    menu_cadastro: str = "menu_cadastro.png"
    menu_materiais: str = "menu_materiais.png"
    menu_materiais_itens: str = "menu_materiais_itens.png"
    search_button: str = "search_button.png"
    message_modal: str = "modal_mensagem.png"
    message_modal_ok_button: str = "modal_mensagem_ok.png"
    radio_inativo: str = "radio_inativo.png"
    search_by_codigo_interno: str = "search_by_codigo_interno.png"
    search_f5_button: str = "search_f5_button.png"
    export_excel_button: str = "export_excel_button.png"
    modal_duplicado: str = "modal_duplicado.png"
    button_ok_duplicad: str = "button_ok_duplicad.png"
    btn_fechar_janela: str = "btn_fechar_janela.png"

class ExportConfig(BaseModel):
    download_dir: str = "C:/Users/User/Downloads"

class BotConfig(BaseModel):
    app: AppConfig
    excel: ExcelConfig
    search: SearchConfig
    runtime: RuntimeConfig
    images: ImagesConfig = ImagesConfig()
    export: ExportConfig = ExportConfig()


def load_config(path: str | Path = "config/config.yaml") -> BotConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file)
    return BotConfig.model_validate(raw)
