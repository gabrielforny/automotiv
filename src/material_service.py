from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.desktop_automation import AutomotivApp
from src.excel_reader import BudgetItem


@dataclass
class MaterialProcessResult:
    item: BudgetItem
    status: str
    material: dict[str, Any] | None = None
    message: str = ""

    @property
    def found(self) -> bool:
        return self.material is not None


class MaterialService:
    def __init__(self, app: AutomotivApp, logger: Any):
        self.app = app
        self.logger = logger

    def process_items(self, items: list[BudgetItem]) -> list[MaterialProcessResult]:
        self.app.open_materials_screen()
        results: list[MaterialProcessResult] = []

        for item in items:
            self.logger.info(
                "Processando material da linha %s | código/referência=%s | quantidade=%s",
                item.row_number,
                item.code_or_reference,
                item.quantity,
            )

            material = self.app.find_material(item.code_or_reference, inactive=False)

            if not material and self.app.config.search.try_inactive_when_not_found:
                self.logger.info("Não encontrou em Ativo/Todos. Tentando Inativo: %s", item.code_or_reference)
                material = self.app.find_material(item.code_or_reference, inactive=True)

            if material:
                results.append(
                    MaterialProcessResult(
                        item=item,
                        status="ENCONTRADO",
                        material=material,
                        message="Material localizado no GRV.",
                    )
                )
            else:
                self.logger.warning("Material não encontrado: %s. Abrindo site fallback.", item.code_or_reference)
                self.app.open_fallback_site()
                results.append(
                    MaterialProcessResult(
                        item=item,
                        status="NAO_ENCONTRADO",
                        material=None,
                        message="Material não localizado no GRV. Site oficial aberto para consulta manual.",
                    )
                )

            self.app.close_current_screen()
            self.app.open_materials_screen()

        return results
