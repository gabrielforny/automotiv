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
from pywinauto.findwindows import ElementNotFoundError

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
        self._send_menu_sequence(["Cadastro", "Cliente"])
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def open_budget_new_screen(self) -> None:
        """Estrutura para: Orçamento > Orçamento - F2 (novo)."""
        self.logger.info("Abrindo Orçamento > Orçamento - F2/novo.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Orçamento", "Orçamento Novo"])
        time.sleep(self.config.app.wait_after_open_screen_seconds)

    def open_previous_orders_search(self) -> None:
        """Estrutura para: Orçamento > Orçamento > Pesquisar F5."""
        self.logger.info("Abrindo pesquisa de orçamentos anteriores.")
        if self.config.runtime.dry_run:
            return
        self._send_menu_sequence(["Orçamento", "Orçamento Pesquisar"])
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
        if self._get_image_name("btn_fechar_janela"):
            self._click_configured_image_or_fail("btn_fechar_janela", timeout=10)
        else:
            keyboard.send_keys("{F10}")
        time.sleep(1)

    def search_material(self, code_or_reference: str, inactive: bool = False) -> bool:
        return self.find_material(code_or_reference=code_or_reference, inactive=inactive) is not None

    def find_material(self, code_or_reference: str, inactive: bool = False) -> dict[str, Any] | None:
        """Pesquisa material e valida o código exato via Excel exportado da grid."""
        status = "Inativo" if inactive else "Ativo/Todos"
        self.logger.info("Pesquisando material '%s' em status %s.", code_or_reference, status)
        if self.config.runtime.dry_run:
            return None

        self.press_search_f5()
        self._select_search_by_code_internal()
        time.sleep(1)
        self._set_material_status(inactive=inactive)
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

    def _set_material_status(self, inactive: bool) -> None:
        image_key = "radio_inativo" if inactive else "radio_todos"
        if self._get_image_name(image_key):
            try:
                self._click_configured_image_or_fail(image_key, timeout=4, confidence=0.75)
                return
            except Exception as exc:
                self.logger.info("Não consegui selecionar status por imagem (%s): %s", image_key, exc)
        if inactive:
            keyboard.send_keys("{TAB}{TAB}{DOWN}{DOWN}")
        else:
            keyboard.send_keys("{TAB}{TAB}{DOWN}{DOWN}")
        time.sleep(0.3)

    def _type_search_text(self, text: str) -> None:
        self.logger.info("Digitando texto da pesquisa: %s", text)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        keyboard.send_keys("{TAB}")
        time.sleep(0.4)
        pyperclip.copy(text)
        time.sleep(0.3)
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        time.sleep(0.5)
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

    def create_budget_for_items(
        self,
        company_code: str | None,
        items: list[Any],
        margins_by_code: dict[str, str] | None = None,
    ) -> str | None:
        """Estrutura inicial para criar orçamento com os itens já validados.

        As imagens ainda precisam ser recortadas/configuradas. A função já deixa os pontos
        certos para você ir habilitando no Windows real.
        """
        self.logger.info("Iniciando criação de orçamento para empresa=%s | itens=%s", company_code, len(items))
        if self.config.runtime.dry_run:
            return None

        self.open_budget_new_screen()
        self._click_budget_blank_area()

        for index, item in enumerate(items, start=1):
            code = getattr(item, "code_or_reference", None) or item.get("code_or_reference")
            quantity = getattr(item, "quantity", None) or item.get("quantity")
            margin = (margins_by_code or {}).get(str(code), self.config.workflow.default_margin)

            self.logger.info("Adicionando item no orçamento: código=%s | quantidade=%s | margem=%s", code, quantity, margin)
            self._type_budget_item_code(str(code))
            self._type_budget_item_quantity(str(quantity))
            if margin:
                self._type_budget_item_margin(str(margin))
            self._go_to_next_budget_item_line(index=index)

        return self._fill_budget_data_and_observation(company_code=company_code)

    def _click_budget_blank_area(self) -> None:
        if self._get_image_name("budget_blank_area"):
            self._click_configured_image_or_fail("budget_blank_area", timeout=10)
        else:
            self.logger.warning("Imagem budget_blank_area não configurada. Clique manual/teclado ainda precisa ser ajustado.")

    def _type_budget_item_code(self, code: str) -> None:
        pyperclip.copy(code)
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(0.5)
        self.handle_optional_message_modal()

    def _type_budget_item_quantity(self, quantity: str) -> None:
        if self._get_image_name("budget_quantity_field"):
            self._click_configured_image_or_fail("budget_quantity_field", timeout=5)
        pyperclip.copy(str(quantity))
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)

    def _type_budget_item_margin(self, margin: str) -> None:
        if self._get_image_name("budget_margin_field"):
            self._click_configured_image_or_fail("budget_margin_field", timeout=5)
        pyperclip.copy(str(margin))
        keyboard.send_keys("^a")
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)

    def _go_to_next_budget_item_line(self, index: int) -> None:
        self.logger.info("Indo para próxima linha do orçamento. Linha atual=%s", index)
        if self._get_image_name("budget_add_next_line_area"):
            self._click_configured_image_or_fail("budget_add_next_line_area", timeout=5)
        else:
            keyboard.send_keys("{DOWN}")
        time.sleep(0.4)

    def _fill_budget_data_and_observation(self, company_code: str | None) -> str | None:
        self.logger.info("Preenchendo dados finais do orçamento e observação.")
        if self._get_image_name("budget_tab_data"):
            self._click_configured_image_or_fail("budget_tab_data", timeout=8)
        if self._get_image_name("budget_order_number_field"):
            self._click_configured_image_or_fail("budget_order_number_field", timeout=5)
            pyperclip.copy(self.config.workflow.observation_placeholder)
            keyboard.send_keys("^a")
            keyboard.send_keys("^v")

        if self._get_image_name("budget_tab_observation"):
            self._click_configured_image_or_fail("budget_tab_observation", timeout=8)
        if self._get_image_name("budget_observation_text_area"):
            self._click_configured_image_or_fail("budget_observation_text_area", timeout=5)
            observation = self._build_observation_text(company_code=company_code)
            pyperclip.copy(observation)
            keyboard.send_keys("^a")
            keyboard.send_keys("^v")
        return None

    def _build_observation_text(self, company_code: str | None) -> str:
        carrier_code = self.find_carrier_code(company_code=company_code)
        if not carrier_code:
            return self.config.workflow.observation_placeholder
        return f"{self.config.workflow.observation_placeholder}\nTransportadora: {carrier_code}"

    def find_previous_order_margins(self, company_code: str | None, material_codes: list[str]) -> dict[str, str]:
        """Estrutura para buscar margens nos pedidos/orçamentos anteriores."""
        self.logger.info("Buscando margens anteriores para empresa=%s | códigos=%s", company_code, material_codes)
        if not company_code or self.config.runtime.dry_run:
            return {}
        # TODO: Recortar imagens e implementar: Orçamento > pesquisar F5 > todos > código cliente > range.
        return {}

    def find_carrier_code(self, company_code: str | None) -> str | None:
        """Estrutura para pegar código da transportadora do último pedido ou cadastro do cliente."""
        self.logger.info("Buscando código da transportadora para empresa=%s", company_code)
        if not company_code or self.config.runtime.dry_run:
            return None
        # TODO: Implementar após capturar as telas/imagens de pedidos anteriores ou aba PADRÕES do cliente.
        return None

    def save_budget(self) -> None:
        self.logger.info("Gravando orçamento.")
        if self.config.runtime.dry_run:
            return
        if self._get_image_name("budget_save_f3_button"):
            self._click_configured_image_or_fail("budget_save_f3_button", timeout=10)
        else:
            keyboard.send_keys("{F3}")
        time.sleep(1)
        self._handle_save_error_until_success()

    def _handle_save_error_until_success(self) -> None:
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
            self.save_budget()

    def generate_budget_pdf(self) -> None:
        self.logger.info("Gerando PDF do orçamento.")
        if not self.config.workflow.generate_pdf or self.config.runtime.dry_run:
            return
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

    def search_client_and_get_code(self, cpf_or_cnpj: str) -> str | None:
        self.logger.info("Pesquisando cliente por CPF/CNPJ: %s", cpf_or_cnpj)
        if self.config.runtime.dry_run:
            return None
        self.press_search_f5()
        self._select_search_by_cpf_cnpj()
        self._type_search_text(cpf_or_cnpj)
        time.sleep(2)
        return self._extract_first_client_code()

    def _select_search_by_cpf_cnpj(self) -> None:
        if self._get_image_name("search_by_cnpj_cpf"):
            self._click_configured_image_or_fail("search_by_cnpj_cpf", timeout=10)
            return
        keyboard.send_keys("{TAB}")
        keyboard.send_keys("{END}")
        keyboard.send_keys("{ENTER}")

    def _extract_first_client_code(self) -> str | None:
        try:
            desktop = Desktop(backend="uia")
            window = desktop.window(title_re=self.config.app.window_title_regex)
            texts = [t.strip() for t in window.texts() if t and t.strip()]
            self.logger.debug("Textos capturados na tela de cliente: %s", texts)
            # TODO: Quando a grid de cliente estiver definida, trocar por exportação Excel ou clipboard.
            return None
        except ElementNotFoundError:
            return None

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
