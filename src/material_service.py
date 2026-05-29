from __future__ import annotations

from typing import Any

from src.desktop_automation import AutomotivApp
from src.excel_reader import BudgetItem


class MaterialService:
    def __init__(self, app: AutomotivApp, logger: Any):
        self.app = app
        self.logger = logger


    def process_items(self, items: list[BudgetItem]) -> None:
        self.app.open_materials_screen()
        # self.app.handle_optional_message_modal()

        for item in items:
            self.logger.info(
                "Processando material da linha %s | código/referência=%s | quantidade=%s",
                item.row_number,
                item.code_or_reference,
                item.quantity,
            )
            
            found = self.app.search_material(item.code_or_reference, inactive=False)

            if not found:
                self.logger.warning(
                    "Material não encontrado em Ativo/Inativo: %s. Abrindo site fallback.",
                    item.code_or_reference,
                )
                self.app.open_fallback_site()

            self.app.close_current_screen()
