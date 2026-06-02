from __future__ import annotations

import re
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import pyautogui
import pyperclip
import yaml
from openpyxl import load_workbook
from pywinauto import Application, Desktop, keyboard

from src.config import BotConfig
from src.image_automation import ImageAutomation
from src.windows_tools import find_desktop_shortcut


class AutomotivApp:
    def __init__(self, config: BotConfig, logger: Any):
        self.config = config
        self.logger = logger
        self.app: Application | None = None
        self.image_config = self._load_image_config()
        self.image = ImageAutomation(
            assets_dir=self.image_config.get("assets_dir", config.images.assets_dir),
            logger=logger,
            confidence=float(self.image_config.get("confidence", config.images.confidence)),
        )
        pyautogui.PAUSE = config.runtime.pause_between_actions_seconds

    def start(self) -> None:
        shortcut = find_desktop_shortcut(self.config.app.shortcut_name)
        self.logger.info("Abrindo atalho: %s", shortcut)

        if self.config.runtime.dry_run:
            self.logger.info("DRY RUN: não vou abrir o sistema.")
            return

        subprocess.Popen([str(shortcut)], shell=True)
        self.app = Application(backend="uia").connect(
            title_re=self.config.app.window_title_regex,
            timeout=60,
        )
        self.logger.info("Sistema aberto/conectado.")

    def login(self) -> None:
        self.logger.info("Efetuando login.")
        if self.config.runtime.dry_run:
            return

        self._fill_password_field()
        self.click_login()
        time.sleep(self.config.app.wait_after_login_seconds)

    def _fill_password_field(self) -> None:
        self.logger.info("Localizando campo de nome/login por imagem.")
        clicked = self.image.click(
            image_name=self._get_required_image_name("input_nome_login"),
            timeout=15,
            confidence=self._get_confidence(),
        )
        if not clicked:
            raise RuntimeError("Não foi possível localizar o campo de login por imagem.")

        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        pyperclip.copy(self.config.app.login_password)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(0.5)
        self.logger.info("Senha preenchida com sucesso.")

    def click_login(self) -> None:
        self.logger.info("Clicando no botão LOGIN por imagem.")
        self._click_configured_image_or_fail("login_button", timeout=15)
        self.logger.info("Clique no botão LOGIN realizado com sucesso por imagem.")

    def open_materials_screen(self) -> None:
        self.logger.info("Abrindo Cadastro > Materiais > Materiais/Itens.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Cadastro", "Materiais", "Materiais/Itens"])
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def open_clients_screen(self) -> None:
        self.logger.info("Abrindo Cadastro > Cliente.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Cadastro"])
        keyboard.send_keys("{DOWN}")
        time.sleep(0.4)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def abrir_novo_orcamento(self) -> None:
        """Menu: Orçamento > Orçamento > Novo (F2)."""
        self.logger.info("Abrindo Orçamento > Orçamento - F2/novo.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Orçamento"])
        time.sleep(0.4)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(8)
        self._click_configured_image_or_fail("menu_orcamento_novo")
        time.sleep(2)
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def open_previous_orders_search(self) -> None:
        """Estrutura para: Orçamento > Orçamento > Pesquisar F5."""
        self.logger.info("Abrindo pesquisa de orçamentos anteriores.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Orçamento"])
        time.sleep(0.4)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(8)
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def _send_menu_sequence(self, labels: list[str]) -> None:
        for label in labels:
            image_key = self._menu_label_to_image_key(label)
            image_name = self._get_image_name(image_key)
            if image_name:
                self.logger.info("Clicando menu '%s' por imagem '%s'.", label, image_name)
                self._click_configured_image_or_fail(image_key, timeout=12)
                time.sleep(0.8)
                continue
            self.logger.info("Imagem do menu '%s' não configurada. Tentando por controle Windows.", label)
            self._click_menu_by_control(label)
            time.sleep(0.8)

    def _click_menu_by_control(self, label: str) -> None:
        desktop = Desktop(backend="uia")
        window = desktop.window(title_re=self.config.app.window_title_regex)
        window.set_focus()
        try:
            control = window.child_window(title=label, control_type="MenuItem")
            control.wait("exists enabled visible", timeout=8)
            control.click_input()
        except Exception as exc:
            self.logger.warning("Não consegui clicar no menu '%s' por controle: %s", label, exc)
            raise

    def press_search_f5(self) -> None:
        self.logger.info("Abrindo pesquisa com F5.")
        if self.config.runtime.dry_run:
            return
        if self._get_image_name("search_f5_button"):
            self._click_configured_image_or_fail("search_f5_button", timeout=10)
        else:
            keyboard.send_keys("{F5}")
        time.sleep(1)

    def close_current_screen(self) -> None:
        self.logger.info("Fechando tela atual.")
        if self.config.runtime.dry_run:
            return
        # Tenta fechar diálogos abertos (F5/busca). Se a imagem não for encontrada
        # usa ESC, que fecha qualquer diálogo sem errar se não houver nenhum aberto.
        self._try_close_dialog()
        self._try_close_dialog()
        self._click_configured_image_or_fail("btn_fechar_aba", timeout=10)
        time.sleep(1)

    def _try_close_dialog(self) -> None:
        image_name = self._get_image_name("btn_fechar_janela")
        if image_name:
            clicked = self.image.click(image_name=image_name, timeout=3, confidence=self._get_confidence())
            if clicked:
                time.sleep(0.8)
                return
        keyboard.send_keys("{ESC}")
        time.sleep(0.8)

    def search_material(self, code_or_reference: str) -> bool:
        return self.find_material(code_or_reference=code_or_reference) is not None

    def find_material(self, code_or_reference: str) -> dict[str, Any] | None:
        """Pesquisa material e valida o código exato via Excel exportado da grid."""
        self.press_search_f5()
        self._select_search_by_code_internal()
        time.sleep(1)
        self._set_material_status()
        time.sleep(1)
        self._type_search_text(code_or_reference)
        time.sleep(2)

        exported_file = self._export_grid_to_excel(code_or_reference)
        try:
            material = self.find_material_in_exported_excel(exported_file, code_or_reference)
            if material:
                self.logger.info("Material encontrado no Excel exportado: %s", material)
                return material
            self.logger.info("Material não encontrado no Excel exportado: %s", code_or_reference)
            return None
        finally:
            self._delete_file_safely(exported_file)

    def _select_search_by_code_internal(self) -> None:
        if self._get_image_name("search_by_codigo_interno"):
            self._click_configured_image_or_fail("search_by_codigo_interno", timeout=10)
            return
        keyboard.send_keys("{TAB}")
        keyboard.send_keys("{HOME}")
        keyboard.send_keys("{ENTER}")

    def _set_material_status(self) -> None:
        keyboard.send_keys("{TAB}{TAB}{DOWN}{DOWN}")
        time.sleep(0.3)

    def _type_search_text(self, text: str) -> None:
        self.logger.info("Digitando texto da pesquisa: %s", text)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(2)
        pyperclip.copy(text)
        time.sleep(2)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(2)
        self._click_search_button()

    def _click_search_button(self) -> None:
        if self._get_image_name("search_button"):
            try:
                self._click_configured_image_or_fail("search_button", timeout=5)
                return
            except Exception as exc:
                self.logger.info("Não consegui clicar pesquisar por imagem; usando ENTER: %s", exc)
        keyboard.send_keys("{ENTER}")

    def _export_grid_to_excel(self, expected_code: str) -> Path:
        self.logger.info("Exportando resultado da grid para Excel.")
        self._click_export_excel_button()
        export_path = self._save_exported_excel_dialog(expected_code)
        self._wait_until_file_is_ready(export_path, timeout=self.config.export.wait_timeout_seconds)
        self.logger.info("Arquivo exportado pronto em: %s", export_path)
        return export_path

    def _click_export_excel_button(self) -> None:
        self.logger.info("Clicando no botão de exportar Excel inferior.")
        image_name = self._get_image_name("export_excel_button")
        if not image_name:
            raise RuntimeError("Imagem 'export_excel_button' não configurada.")
        clicked = self.image.click_bottommost(image_name=image_name, timeout=10, confidence=self._get_confidence())
        if not clicked:
            raise RuntimeError("Não consegui clicar no botão Excel inferior.")
        time.sleep(1)

    def _save_exported_excel_dialog(self, expected_code: str, timeout: int = 15) -> Path:
        download_dir = Path(self.config.export.download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        safe_code = self._sanitize_filename(expected_code)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = download_dir / f"{self.config.export.exported_file_prefix}_{safe_code}_{timestamp}.xlsx"
        self.logger.info("Salvando Excel exportado em: %s", file_path)

        # A janela Salvar como costuma vir com o campo Nome selecionado.
        # Colar caminho completo define pasta + nome em uma única ação.
        pyperclip.copy(str(file_path))
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(0.5)
        keyboard.send_keys("{ENTER}")

        self._handle_save_confirmation_if_exists()
        return file_path

    def _handle_save_confirmation_if_exists(self) -> None:
        time.sleep(0.8)
        if not self._get_image_name("modal_duplicado") or not self._get_image_name("button_ok_duplicad"):
            return
        try:
            if self.image.exists(self._get_required_image_name("modal_duplicado"), timeout=2, confidence=self._get_confidence()):
                self._click_configured_image_or_fail("button_ok_duplicad", timeout=5)
        except Exception as exc:
            self.logger.info("Sem confirmação de substituição ou não consegui validar: %s", exc)

    def _wait_until_file_is_ready(self, file_path: Path, timeout: int = 90) -> None:
        self.logger.info("Aguardando arquivo ficar pronto: %s", file_path)
        deadline = time.time() + timeout
        last_size = -1
        stable_count = 0
        while time.time() < deadline:
            if file_path.exists():
                current_size = file_path.stat().st_size
                if current_size > 0 and current_size == last_size:
                    stable_count += 1
                else:
                    stable_count = 0
                last_size = current_size
                if stable_count >= 2:
                    try:
                        with file_path.open("rb"):
                            pass
                        return
                    except PermissionError:
                        self.logger.info("Arquivo ainda em uso. Aguardando...")
            time.sleep(1)
        raise TimeoutError(f"O arquivo exportado não ficou pronto dentro de {timeout} segundos: {file_path}")

    def find_material_in_exported_excel(self, excel_path: str | Path, expected_code: str) -> dict[str, Any] | None:
        path = Path(excel_path)
        workbook = load_workbook(path, data_only=True)
        sheet = workbook.active
        headers = {str(cell.value).strip(): cell.column for cell in sheet[1] if cell.value}
        code_col = headers.get("*Código Interno")
        item_col = headers.get("*Item")
        family_col = headers.get("*Família")
        group_col = headers.get("*Grupo")
        if not code_col:
            raise RuntimeError("Coluna '*Código Interno' não encontrada no Excel exportado.")

        expected = str(expected_code).strip()
        for row in range(2, sheet.max_row + 1):
            code = str(sheet.cell(row=row, column=code_col).value or "").strip()
            if code == expected:
                return {
                    "row": row,
                    "codigo_interno": code,
                    "item": sheet.cell(row=row, column=item_col).value if item_col else None,
                    "familia": sheet.cell(row=row, column=family_col).value if family_col else None,
                    "grupo": sheet.cell(row=row, column=group_col).value if group_col else None,
                }
        return None

    # ================================
    # Estrutura do fluxo de orçamento
    # ================================

    def criar_orcamento(
        self,
        company_code: str | None,
        items: list[Any],
        margins_by_code: dict[str, str] | None = None,
        carrier_code: str | None = None,
    ) -> str | None:
        self.logger.info("Iniciando criação de orçamento para empresa=%s | itens=%s", company_code, len(items))
        if self.config.runtime.dry_run:
            return None

        self._click_configured_image_or_fail("btn_fechar_aba", timeout=10)
        time.sleep(3)

        self.abrir_novo_orcamento()

        time.sleep(5)
        self._clicar_campo_codigo_grade()
        time.sleep(2)

        total_items = len(items)
        for index, item in enumerate(items, start=1):
            code = getattr(item, "code_or_reference", None) or item.get("code_or_reference")
            quantity = getattr(item, "quantity", None) or item.get("quantity")
            margin = (margins_by_code or {}).get(str(code), self.config.workflow.default_margin)

            self.logger.info("Adicionando item no orçamento: código=%s | quantidade=%s | margem=%s", code, quantity, margin)
            self._digitar_codigo_item(str(code))
            self._digitar_quantidade_item(str(quantity))
            if margin:
                self._digitar_margem_item(str(margin))
            if index < total_items:
                self._ir_proxima_linha_grade(index=index)

        return self._preencher_dados_e_observacao(carrier_code=carrier_code)

    def _clicar_campo_codigo_grade(self) -> None:
        self._click_configured_image_or_fail("campo_codigo_grade_orcamento", timeout=10)
        time.sleep(3)
        try:
            self._click_configured_image_or_fail("lupa_dentro_selecao", timeout=10)
        except Exception as exc:
            self._click_configured_image_or_fail("lupa_fora_selecao", timeout=10)
        time.sleep(2)
        keyboard.send_keys("{ESC}")
        time.sleep(2)
        self.logger.warning("Clicado na coluna de código de grade")

    def _digitar_codigo_item(self, code: str) -> None:
        self.logger.warning("Digitando código do item: %s", code)
        pyautogui.write(code, interval=0.05)
        time.sleep(0.3)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.5)
        self.handle_optional_message_modal()

    def _digitar_quantidade_item(self, quantity: str) -> None:
        self.logger.warning("Digitando quantidade do item: %s", quantity)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        pyperclip.copy(str(quantity))
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)

    def _digitar_margem_item(self, margin: str) -> None:
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        time.sleep(0.5)
        keyboard.send_keys("{TAB}")
        pyperclip.copy(str(margin))
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)

    def _ir_proxima_linha_grade(self, index: int) -> None:
        self.logger.info("Indo para próxima linha do orçamento. Linha atual=%s", index)
        keyboard.send_keys("{DOWN}")
        time.sleep(0.4)

    def _preencher_dados_e_observacao(self, carrier_code: str | None = None) -> str | None:
        self.logger.info("Preenchendo dados finais do orçamento e observação.")

        self._click_configured_image_or_fail("aba_dados_orcamento", timeout=8)

        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        pyperclip.copy(self.config.workflow.observation_placeholder)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(2)
        self._click_configured_image_or_fail("aba_observacao_orcamento", timeout=8)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        
        self._click_configured_image_or_fail("area_texto_observacao", timeout=5)
        observation = self._montar_texto_observacao(carrier_code=carrier_code)
        keyboard.send_keys("{TAB}")
        time.sleep(1)
        pyperclip.copy(observation)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        return None

    def _montar_texto_observacao(self, carrier_code: str | None) -> str:
        if not carrier_code:
            return self.config.workflow.observation_placeholder
        return f"{self.config.workflow.observation_placeholder}\nTransportadora: {carrier_code}"

    def buscar_margens_pedidos_anteriores(
        self,
        company_code: str | None,
        material_codes: list[str],
        company_name: str | None = None,
    ) -> tuple[dict[str, str], str | None]:
        """Busca margens e código de transportadora em orçamentos anteriores do cliente.

        Retorna (margins_by_code, carrier_code). O carrier_code vem do pedido mais recente
        que contenha essa informação; se não encontrado em nenhum pedido, retorna None.
        """
        self.logger.info("Buscando margens anteriores para empresa=%s | nome=%s | códigos=%s", company_code, company_name, material_codes)
        if not company_code or self.config.runtime.dry_run:
            return {}, None

        self.open_previous_orders_search()
        self.press_search_f5()
        search_term = company_name or company_code
        self._filtrar_pedidos_anteriores_por_cliente(search_term)

        exported_list = self._export_grid_to_excel(company_code)
        try:
            order_count = self._contar_linhas_excel(exported_list)
        finally:
            self._delete_file_safely(exported_list)

        if order_count == 0:
            self.logger.info("Nenhum pedido anterior encontrado para o cliente %s.", company_code)
            self._fechar_tela_pedidos_anteriores()
            return {}, None

        margins: dict[str, str] = {}
        carrier_code: str | None = None
        target_codes = {str(c) for c in material_codes}
        max_orders = self.config.workflow.previous_orders_max_to_check

        keyboard.send_keys("{HOME}")
        time.sleep(0.3)

        for order_idx in range(min(order_count, max_orders)):
            if len(margins) == len(target_codes) and carrier_code:
                break

            self.logger.info("Abrindo pedido %s/%s para buscar margens.", order_idx + 1, min(order_count, max_orders))
            keyboard.send_keys("{ENTER}")
            time.sleep(1.5)

            exported_items = self._export_grid_to_excel(f"{company_code}_pedido_{order_idx}")
            try:
                order_margins, order_carrier = self._ler_margens_do_excel_de_itens(exported_items, target_codes)
            finally:
                self._delete_file_safely(exported_items)

            for code, margin in order_margins.items():
                if code not in margins:
                    margins[code] = margin
                    self.logger.info("Margem encontrada: código=%s | margem=%s", code, margin)

            # Usa o carrier do pedido mais recente (primeiro encontrado)
            if not carrier_code and order_carrier:
                carrier_code = order_carrier
                self.logger.info("Código de transportadora encontrado no pedido %s: %s", order_idx + 1, carrier_code)

            self._try_close_dialog()
            self._click_configured_image_or_fail("btn_fechar_aba", timeout=10)
            time.sleep(0.8)
            keyboard.send_keys("{DOWN}")
            time.sleep(0.3)

        self._fechar_tela_pedidos_anteriores()
        return margins, carrier_code

    def _filtrar_pedidos_anteriores_por_cliente(self, search_term: str) -> None:
        # search_term é o Nome Fantasia (preferido) ou código numérico do cliente como fallback.
        self._click_configured_image_or_fail("filtro_por_cliente", timeout=8)
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        pyperclip.copy(search_term)
        time.sleep(0.4)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(0.3)

        # MAPEAR: previous_orders_date_range_field — campo de data inicial do filtro (formato DD/MM/AAAA).
        # Preenche com a data de X meses atrás (configurado em workflow.previous_orders_months_back).
        if self._get_image_name("previous_orders_date_range_field"):
            self._click_configured_image_or_fail("previous_orders_date_range_field", timeout=8)
            pyperclip.copy(self._calcular_data_inicio_pesquisa())
            keyboard.send_keys("^a")
            keyboard.send_keys("^v")
            time.sleep(0.3)

        # Dispara a pesquisa
        keyboard.send_keys("{ENTER}")
        time.sleep(2)

    def _calcular_data_inicio_pesquisa(self) -> str:
        from datetime import date
        months_back = self.config.workflow.previous_orders_months_back
        today = date.today()
        month = today.month - (months_back % 12)
        year = today.year - (months_back // 12)
        if month <= 0:
            month += 12
            year -= 1
        return f"{today.day:02d}/{month:02d}/{year}"

    def _contar_linhas_excel(self, excel_path: Path) -> int:
        workbook = load_workbook(excel_path, data_only=True)
        sheet = workbook.active
        count = max(0, sheet.max_row - 1)  # -1 para ignorar o cabeçalho
        workbook.close()
        return count

    def _ler_margens_do_excel_de_itens(self, excel_path: Path, target_codes: set[str]) -> dict[str, str]:
        workbook = load_workbook(excel_path, data_only=True)
        sheet = workbook.active
        headers = {str(cell.value or "").strip(): cell.column for cell in sheet[1] if cell.value}

        # Tenta localizar a coluna do código do material (padrão GRV com asterisco)
        code_col = (
            headers.get("*Código Interno")
            or headers.get("*Código")
            or headers.get("Código Interno")
            or headers.get("Código")
        )
        # Tenta localizar a coluna de margem
        margin_col = (
            headers.get("*Margem")
            or headers.get("*% Margem")
            or headers.get("Margem")
            or headers.get("% Margem")
        )

        carrier_col = (
            headers.get("*Transportadora")
            or headers.get("Transportadora")
            or headers.get("*Cód. Transportadora")
            or headers.get("Cód. Transportadora")
            or headers.get("*Cod. Transportadora")
            or headers.get("Cod. Transportadora")
        )

        if not code_col or not margin_col:
            self.logger.warning(
                "Colunas de código/margem não encontradas no Excel de itens. Disponíveis: %s",
                list(headers.keys()),
            )
            workbook.close()
            return {}, None

        result: dict[str, str] = {}
        carrier_code: str | None = None
        for row in range(2, sheet.max_row + 1):
            code = str(sheet.cell(row=row, column=code_col).value or "").strip()
            if carrier_col and not carrier_code:
                cv = str(sheet.cell(row=row, column=carrier_col).value or "").strip()
                if cv:
                    carrier_code = cv
            if code not in target_codes:
                continue
            margin_value = sheet.cell(row=row, column=margin_col).value
            if margin_value is not None and str(margin_value).strip():
                result[code] = str(margin_value).strip()

        workbook.close()
        return result, carrier_code

    def _fechar_tela_pedidos_anteriores(self) -> None:
        self._try_close_dialog()
        self._click_configured_image_or_fail("btn_fechar_aba", timeout=10)
        time.sleep(0.8)

    def buscar_codigo_transportadora(self, company_code: str | None) -> str | None:
        """Busca o código da transportadora do último pedido ou aba PADRÕES do cadastro do cliente."""
        self.logger.info("Buscando código da transportadora para empresa=%s", company_code)
        if not company_code or self.config.runtime.dry_run:
            return None
        # TODO: Implementar após capturar telas de pedidos anteriores ou aba PADRÕES do cliente.
        return None

    def gravar_orcamento(self) -> None:
        self.logger.info("Gravando orçamento.")
        self._click_configured_image_or_fail("botao_gravar_f3", timeout=10)
        time.sleep(1)
        self._tratar_erro_gravacao()

    def _tratar_erro_gravacao(self) -> None:
        for attempt in range(1, self.config.workflow.save_retry_attempts + 1):
            self.logger.info("Verificando erro de gravação. Tentativa %s", attempt)
            if not self._get_image_name("save_error_modal_ok_button"):
                return
            clicked = self.image.click_if_exists(
                self._get_required_image_name("save_error_modal_ok_button"),
                timeout=2,
                confidence=self._get_confidence(),
            )
            if not clicked:
                return
            time.sleep(0.5)
            self.gravar_orcamento()

    def gerar_pdf_orcamento(self) -> None:
        self.logger.info("Gerando PDF do orçamento.")
        if not self.config.workflow.generate_pdf or self.config.runtime.dry_run:
            return
        # Envia pelo menu: Imprimir > Imprimir Orçamento Padrão.
        self._send_menu_sequence(["Imprimir", "Imprimir Orçamento Padrão"])
        if self._get_image_name("print_ok_button"):
            self.image.click_if_exists(self._get_required_image_name("print_ok_button"), timeout=5, confidence=self._get_confidence())

    # ================================
    # Cliente
    # ================================

    def open_fallback_site(self) -> None:
        self.logger.info("Abrindo site fallback: %s", self.config.search.fallback_site)
        if not self.config.runtime.dry_run:
            webbrowser.open(self.config.search.fallback_site)

    def search_client_and_get_code(self, cpf_or_cnpj: str) -> tuple[str | None, str | None]:
        """Retorna (client_code, carrier_code). Carrier lido da aba PADRÕES do cadastro do cliente."""
        self.logger.info("Pesquisando cliente por CPF/CNPJ: %s", cpf_or_cnpj)
        if self.config.runtime.dry_run:
            return None, None
        self.press_search_f5()
        self._select_search_by_cpf_cnpj()
        self._garantir_radio_todos()
        self._type_search_text(cpf_or_cnpj)
        time.sleep(2)
        code = self._extract_first_client_code(cpf_or_cnpj)
        carrier_code = None
        if code:
            self._fechar_confirmacao_exportacao()
            carrier_code = self._ler_codigo_transportadora_aba_padrao()
        self._click_configured_image_or_fail("btn_fechar_aba", timeout=5)
        return code, carrier_code

    def _fechar_confirmacao_exportacao(self) -> None:
        """Fecha o diálogo de confirmação pós-exportação, mantendo o modal de pesquisa aberto."""
        self._click_configured_image_or_fail("btn_fechar_janela", timeout=5)
        time.sleep(5)
        if self._get_image_name("btn_ok_exportacao"):
            self._click_configured_image_or_fail("btn_ok_exportacao", timeout=5)
        else:
            keyboard.send_keys("{ENTER}")
        time.sleep(0.5)

    def _ler_codigo_transportadora_aba_padrao(self) -> str | None:
        """Clica na aba PADRÕES do cadastro do cliente, navega até o campo de transportadora e copia."""
        self._click_configured_image_or_fail("aba_padrao_cliente", timeout=8)
        time.sleep(0.5)
        self._click_configured_image_or_fail("interrogacao_aba_padrao", timeout=8)
        time.sleep(0.5)
        keyboard.send_keys("{ESC}")
        time.sleep(0.5)
        for _ in range(17):
            keyboard.send_keys("{TAB}")
            time.sleep(0.1)
        time.sleep(0.5)
        keyboard.send_keys("^a")
        keyboard.send_keys("^c")
        time.sleep(0.3)
        value = pyperclip.paste().strip()
        self.logger.info("Código de transportadora da aba PADRÕES: %s", value or "(vazio)")
        return value or None

    def _select_search_by_cpf_cnpj(self) -> None:
        self._click_configured_image_or_fail("search_by_cnpj_cpf", timeout=10)
        time.sleep(0.5)

    def _garantir_radio_todos(self) -> None:
        """Garante que o filtro 'Todos' está selecionado na tela de pesquisa.

        O GRV às vezes abre com 'Ativo', às vezes com 'Inativo', às vezes com 'Todos'.
        Clicar em 'Todos' quando já está selecionado não tem efeito, então é seguro
        chamar sempre. Se a imagem não for encontrada, apenas loga e segue em frente.
        """
        if self._get_image_name("radio_todos"):
            self._click_configured_image_or_fail("radio_todos", timeout=5)
            self.logger.info("Filtro 'Todos' selecionado.")
            time.sleep(0.3)
        else:
            self.logger.warning("Imagem 'radio_todos' não encontrada — verifique se está mapeada. Seguindo sem alterar o filtro.")

    def _extract_first_client_code(self, cpf_or_cnpj: str) -> str | None:
        self.logger.info("Exportando grid de clientes para Excel.")
        exported_file = self._export_grid_to_excel(cpf_or_cnpj)
        try:
            code = self._find_client_code_in_exported_excel(exported_file)
            if code:
                self.logger.info("Código do cliente extraído: %s", code)
            else:
                self.logger.info("Nenhum código de cliente encontrado no Excel exportado.")
            return code
        finally:
            self._delete_file_safely(exported_file)

    def _find_client_code_in_exported_excel(self, excel_path: Path) -> str | None:
        workbook = load_workbook(excel_path, data_only=True)
        sheet = workbook.active
        headers = {str(cell.value or "").strip(): cell.column for cell in sheet[1] if cell.value}
        code_col = headers.get("*Código") or headers.get("Código") or headers.get("*Codigo") or headers.get("Codigo")
        if code_col is None:
            raise RuntimeError(
                f"Coluna '*Código' não encontrada no Excel de clientes exportado. "
                f"Colunas disponíveis: {list(headers.keys())}"
            )
        for row in range(2, sheet.max_row + 1):
            value = sheet.cell(row=row, column=code_col).value
            if value is not None and str(value).strip():
                workbook.close()
                return str(value).strip()
        workbook.close()
        return None

    # ================================
    # Controle do ciclo de vida da app
    # ================================

    def close_app(self) -> None:
        """Fecha a janela do GRV para liberar o foco antes de abrir o navegador."""
        self.logger.info("Fechando aplicação GRV.")
        self._click_configured_image_or_fail("btn_fechar_janela", timeout=10)
        time.sleep(1)
        self._click_configured_image_or_fail("btn_fechar_janela", timeout=10)
        time.sleep(1)
        self._click_configured_image_or_fail("btn_fechar_aba", timeout=10)
        time.sleep(3)
        self._click_configured_image_or_fail("btn_sair_grv", timeout=10)
        time.sleep(1)
        self._click_configured_image_or_fail("btn_sair_do_sistema", timeout=10)
        time.sleep(3)
        self.app = None

    def reopen(self) -> None:
        """Reabre e faz login no GRV após ter fechado para ir ao site."""
        self.logger.info("Reabrindo aplicação GRV.")
        self.start()
        self.login()

    # ================================
    # Utilitários
    # ================================

    def handle_optional_message_modal(self) -> None:
        self.logger.info("Verificando se apareceu modal de mensagem.")
        time.sleep(0.5)
        modal_image = self._get_image_name("message_modal")
        ok_image = self._get_image_name("message_modal_ok_button")
        if not modal_image or not ok_image:
            self.logger.info("Imagens do modal não configuradas. Seguindo fluxo normal.")
            return
        modal_appeared = self.image.exists(image_name=modal_image, timeout=3, confidence=self._get_confidence())
        if not modal_appeared:
            self.logger.info("Modal de mensagem não apareceu. Seguindo fluxo normal.")
            return
        self.logger.info("Modal de mensagem encontrado. Clicando no OK.")
        clicked_ok = self.image.click(image_name=ok_image, timeout=5, confidence=self._get_confidence())
        if not clicked_ok:
            raise RuntimeError("Modal apareceu, mas não consegui clicar no botão OK.")
        time.sleep(0.5)

    def _click_configured_image_or_fail(self, image_key: str, timeout: int = 10, confidence: float | None = None) -> None:
        image_name = self._get_image_name(image_key)
        if not image_name:
            raise RuntimeError(f"Imagem '{image_key}' não configurada em config/config.yaml na seção images.")
        clicked = self.image.click(image_name=image_name, timeout=timeout, confidence=confidence or self._get_confidence())
        if clicked:
            return
        assets_dir = self.image_config.get("assets_dir", self.config.images.assets_dir)
        raise RuntimeError(
            f"Não foi possível localizar/clicar na imagem '{image_key}' ({image_name}). "
            f"Verifique se o arquivo existe em '{assets_dir}', se o recorte está correto "
            "e se a tela está na mesma escala/resolução."
        )

    def _get_image_name(self, image_key: str) -> str | None:
        value = self.image_config.get(image_key)
        if value is None or str(value).strip() == "":
            return None
        return str(value).strip()

    def _get_required_image_name(self, image_key: str) -> str:
        image_name = self._get_image_name(image_key)
        if not image_name:
            raise RuntimeError(f"Imagem obrigatória '{image_key}' não configurada em config/config.yaml.")
        return image_name

    def _get_confidence(self) -> float:
        return float(self.image_config.get("confidence", self.config.images.confidence))

    def _load_image_config(self) -> dict[str, Any]:
        yaml_images: dict[str, Any] = {}
        config_path = Path("config/config.yaml")
        try:
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as file:
                    raw = yaml.safe_load(file) or {}
                yaml_images = raw.get("images") or {}
        except Exception as exc:
            self.logger.warning("Não consegui ler seção images do config.yaml: %s", exc)
        images = {
            "assets_dir": getattr(self.config.images, "assets_dir", "assets/images"),
            "confidence": getattr(self.config.images, "confidence", 0.85),
            "login_button": getattr(self.config.images, "login_button", "login_button.png"),
        }
        images.update(yaml_images)
        return images

    @staticmethod
    def _menu_label_to_image_key(label: str) -> str:
        normalized = (
            label.lower()
            .replace("/", "_")
            .replace(" ", "_")
            .replace("-", "_")
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("ã", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )
        mapping = {
            "cadastro": "menu_cadastro",
            "cliente": "menu_cliente",
            "materiais": "menu_materiais",
            "materiais_itens": "menu_materiais_itens",
            "orcamento": "menu_orcamento",
            "orcamento_submenu": "menu_orcamento_submenu",
            "orcamento_novo": "menu_orcamento_novo",
            "orcamento_pesquisar": "menu_orcamento_pesquisar",
            "imprimir": "menu_imprimir",
            "imprimir_orcamento_padrao": "menu_imprimir_orcamento_padrao",
        }
        return mapping.get(normalized, f"menu_{normalized}")

    @staticmethod
    def _sanitize_filename(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip()) or "sem_codigo"

    def _delete_file_safely(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
            self.logger.info("Arquivo temporário removido: %s", path)
        except Exception as exc:
            self.logger.warning("Não consegui remover arquivo temporário %s: %s", path, exc)
