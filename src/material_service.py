from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.desktop_automation import AutomotivApp
from src.excel_reader import BudgetItem

if TYPE_CHECKING:
    from src.site_search_service import SiteSearchService


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
    def __init__(self, app: AutomotivApp, site_service: SiteSearchService, logger: Any):
        self.app = app
        self.site_service = site_service
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

            material = self.app.find_material(item.code_or_reference)

            if material:
                results.append(
                    MaterialProcessResult(
                        item=item,
                        status="ENCONTRADO",
                        material=material,
                        message="Material localizado no GRV.",
                    )
                )
                self.app.close_current_screen()
                self.app.open_materials_screen()
            else:
                self.logger.warning(
                    "Material não encontrado no GRV: %s. Fechando app e pesquisando no site.",
                    item.code_or_reference,
                )
                self.app.close_app()
                site_material = self.site_service.search(item.code_or_reference)

                if site_material:
                    results.append(
                        MaterialProcessResult(
                            item=item,
                            status="ENCONTRADO_SITE",
                            material=site_material,
                            message="Material localizado no site automotivdobrasil.com.br.",
                        )
                    )
                else:
                    results.append(
                        MaterialProcessResult(
                            item=item,
                            status="NAO_ENCONTRADO",
                            material=None,
                            message="Material não localizado no GRV nem no site.",
                        )
                    )

                self.logger.info("Reabrindo GRV para próximo item.")
                self.app.reopen()
                self.app.open_materials_screen()

        return results
