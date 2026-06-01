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
        last_idx = len(items) - 1

        for idx, item in enumerate(items):
            is_last = idx == last_idx
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
                # Fecha a tela de resultado. Se houver próximo item, reabre materiais.
                self.app.close_current_screen()
                if not is_last:
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

                # Sempre reabre o GRV após o site. Se houver próximo item, abre materiais.
                self.app.reopen()
                if not is_last:
                    self.logger.info("Abrindo materiais para próximo item.")
                    self.app.open_materials_screen()

        # Ao sair do loop o GRV está aberto na tela principal, pronto para
        # o fluxo de cliente e orçamento sem nenhuma sub-tela aberta.
        return results
