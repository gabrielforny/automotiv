from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    shortcut_name: str
    window_title_regex: str
    login_username: str
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
    model_config = ConfigDict(extra="allow")

    assets_dir: str = "assets/images"
    confidence: float = 0.85

    input_senha: str = "input_senha.png"
    input_nome_login: str = "input_nome_login.png"
    input_empresa_login: str = "input_empresa_login.PNG"
    login_button: str = "login_button.png"

    menu_cadastro: str = "menu_cadastro.png"
    menu_cliente: str = "menu_cliente.png"
    menu_materiais: str = "menu_materiais.png"
    menu_materiais_itens: str = "menu_materiais_itens.png"
    menu_orcamento: str = "menu_orcamento.png"
    menu_orcamento_submenu: str = "menu_orcamento_submenu.png"
    menu_orcamento_pesquisar: str = "menu_orcamento_pesquisar.png"
    menu_orcamento_novo: str = "menu_orcamento_novo.png"
    menu_imprimir: str = "menu_imprimir.png"
    menu_imprimir_orcamento_padrao: str = "menu_imprimir_orcamento_padrao.png"

    search_button: str = "search_button.png"
    search_f5_button: str = "search_f5_button.png"
    search_by_codigo_interno: str = "search_by_codigo_interno.png"
    search_by_cnpj_cpf: str = "search_by_cnpj_cpf.png"

    export_excel_button: str = "export_excel_button.png"
    btn_fechar_janela: str = "btn_fechar_janela.png"
    btn_fechar_aba: str = "btn_fechar_aba.png"
    btn_sair_grv: str = "btn_sair_grv.png"
    btn_sair_do_sistema: str = "btn_sair_do_sistema.png"
    
    message_modal: str = "modal_mensagem.png"
    message_modal_ok_button: str = "modal_mensagem_ok.png"
    modal_duplicado: str = "modal_duplicado.png"
    button_ok_duplicad: str = "button_ok_duplicad.png"
    save_error_modal_ok_button: str = "save_error_modal_ok_button.png"

    radio_inativo: str = "radio_inativo.png"
    radio_ativo: str = "radio_ativo.png"
    radio_todos: str = "radio_todos.png"

    campo_codigo_grade_orcamento: str = "campo_codigo_grade_orcamento.png"
    campo_quantidade_item: str = "campo_quantidade_item.png"
    campo_margem_item: str = "campo_margem_item.png"
    botao_nova_linha_grade: str = "botao_nova_linha_grade.png"
    aba_itens_orcamento: str = "aba_itens_orcamento.png"
    aba_dados_orcamento: str = "aba_dados_orcamento.png"
    aba_observacao_orcamento: str = "aba_observacao_orcamento.png"
    icone_obrigatorio: str = "icone_obrigatorio.png"
    campo_numero_pedido: str = "campo_numero_pedido.png"
    area_texto_observacao: str = "area_texto_observacao.png"
    botao_gravar_f3: str = "botao_gravar_f3.png"
    lupa_dentro_selecao: str = "lupa_dentro_selecao.png"
    lupa_fora_selecao: str = "lupa_fora_selecao.png"

    previous_orders_search_all_checkbox: str = "previous_orders_search_all_checkbox.png"
    previous_orders_client_code_field: str = "previous_orders_client_code_field.png"
    previous_orders_date_range_field: str = "previous_orders_date_range_field.png"
    previous_order_open_button: str = "previous_order_open_button.png"

    aba_padrao_cliente: str = "aba_padrao_cliente.png"
    btn_ok_exportacao: str = "btn_ok_exportacao.png"
    interrogacao_aba_padrao: str = "interrogacao_aba_padrao.png"
    filtro_por_cliente: str = "filtro_por_cliente.png"
    
    carrier_code_field: str = "carrier_code_field.png"
    carrier_pattern_tab: str = "carrier_pattern_tab.png"
    print_ok_button: str = "print_ok_button.png"

    site_search_field: str = "site_search_field.png"
    site_search_button: str = "site_search_button.png"
    site_result_found: str = "site_result_found.png"
    site_result_code_area: str = "site_result_code_area.png"

    filtrar_por_codigo: str = "filtrar_por_codigo.png"
    export_excel_pedidos_anchor: str = "export_excel_pedidos_anchor.PNG"
    sem_dados_na_busca: str = "sem_dados_na_busca.PNG"
    input_pesquisa_item_orcamento: str = "input_pesquisa_item_orcamento.PNG"
    limpar_pesquisa_item_orcamento: str = "limpar_pesquisa_item_orcamento.PNG"
    aba_transporte_orcamento: str = "aba_transporte_orcamento.PNG"

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
    previous_orders_max_to_check: int = 5
    save_retry_attempts: int = 2
    generate_pdf: bool = True
    # Offset em pixels do ícone âncora até o botão Excel na toolbar de pedidos
    export_excel_pedidos_offset_x: int = 60


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


def _bundle_base() -> Path:
    """Retorna a pasta com os arquivos bundled: sys._MEIPASS no exe, raiz do projeto em dev."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


def load_config(path: str | Path = "config/config.yaml") -> BotConfig:
    base = _bundle_base()
    config_path = base / path if not Path(str(path)).is_absolute() else Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file) or {}
    config = BotConfig.model_validate(raw)
    # Resolve assets_dir relativo à pasta do bundle quando empacotado
    if getattr(sys, "frozen", False) and not Path(config.images.assets_dir).is_absolute():
        config.images.assets_dir = str(base / config.images.assets_dir)
    return config
