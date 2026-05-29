from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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

    input_senha: str = "input_senha.png"
    input_nome_login: str = "input_nome_login.png"
    login_button: str = "login_button.png"

    menu_cadastro: str = "menu_cadastro.png"
    menu_cliente: str = "menu_cliente.png"
    menu_materiais: str = "menu_materiais.png"
    menu_materiais_itens: str = "menu_materiais_itens.png"
    menu_orcamento: str = "menu_orcamento.png"
    menu_orcamento_novo: str = "menu_orcamento_novo.png"
    menu_orcamento_pesquisar: str = "menu_orcamento_pesquisar.png"
    menu_imprimir: str = "menu_imprimir.png"
    menu_imprimir_orcamento_padrao: str = "menu_imprimir_orcamento_padrao.png"

    search_button: str = "botao_pesquisar.png"
    search_f5_button: str = "search_f5_button.png"
    search_by_codigo_interno: str = "search_by_codigo_interno.png"
    search_by_cnpj_cpf: str = "search_by_cnpj_cpf.png"

    export_excel_button: str = "export_excel_button.png"
    btn_fechar_janela: str = "btn_fechar_janela.png"
    btn_fechar_aba: str = "btn_fechar_aba.png"

    message_modal: str = "modal_mensagem.png"
    message_modal_ok_button: str = "modal_mensagem_ok.png"
    modal_duplicado: str = "modal_duplicado.png"
    button_ok_duplicad: str = "button_ok_duplicad.png"
    save_error_modal_ok_button: str = "save_error_modal_ok_button.png"

    radio_inativo: str = "radio_inativo.png"
    radio_ativo: str = "radio_ativo.png"
    radio_todos: str = "radio_todos.png"

    budget_blank_area: str = "budget_blank_area.png"
    budget_quantity_field: str = "budget_quantity_field.png"
    budget_margin_field: str = "budget_margin_field.png"
    budget_add_next_line_area: str = "budget_add_next_line_area.png"
    budget_tab_items: str = "budget_tab_items.png"
    budget_tab_data: str = "budget_tab_data.png"
    budget_tab_observation: str = "budget_tab_observation.png"
    budget_order_number_field: str = "budget_order_number_field.png"
    budget_observation_text_area: str = "budget_observation_text_area.png"
    budget_save_f3_button: str = "budget_save_f3_button.png"

    previous_orders_search_all_checkbox: str = "previous_orders_search_all_checkbox.png"
    previous_orders_client_code_field: str = "previous_orders_client_code_field.png"
    previous_orders_date_range_field: str = "previous_orders_date_range_field.png"
    previous_order_open_button: str = "previous_order_open_button.png"

    carrier_code_field: str = "carrier_code_field.png"
    carrier_pattern_tab: str = "carrier_pattern_tab.png"
    print_ok_button: str = "print_ok_button.png"

    site_search_field: str = "site_search_field.png"
    site_search_button: str = "site_search_button.png"
    site_result_found: str = "site_result_found.png"
    site_result_code_area: str = "site_result_code_area.png"


class SiteSearchConfig(BaseModel):
    wait_after_open_seconds: float = 3.0
    wait_after_search_seconds: float = 2.0


class ExportConfig(BaseModel):
    download_dir: str = "C:/Users/User/Documents/automotiv/data/exportados"
    exported_file_prefix: str = "automotiv_material"
    wait_timeout_seconds: int = 90


class PathsConfig(BaseModel):
    data_dir: str = "data"
    pending_dir: str = "data/a_processar"
    processed_dir: str = "data/processados"
    history_dir: str = "data/historico"
    export_dir: str = "data/exportados"
    pdf_dir: str = "data/pdfs"


class WorkflowConfig(BaseModel):
    enable_budget_flow: bool = True
    default_margin: str = ""
    observation_placeholder: str = "-"
    previous_orders_months_back: int = 12
    save_retry_attempts: int = 2
    generate_pdf: bool = True


class BotConfig(BaseModel):
    app: AppConfig
    excel: ExcelConfig
    search: SearchConfig
    runtime: RuntimeConfig
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    site_search: SiteSearchConfig = Field(default_factory=SiteSearchConfig)


def load_config(path: str | Path = "config/config.yaml") -> BotConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file) or {}
    return BotConfig.model_validate(raw)
