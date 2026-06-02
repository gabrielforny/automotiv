from __future__ import annotations

from typing import Any

from src.desktop_automation import AutomotivApp
from src.material_service import MaterialProcessResult


class OrcamentoService:
    """Estrutura do restante do fluxo desenhado no Miro.

    Ainda depende das imagens reais das telas de orçamento/pedidos anteriores.
    Os métodos já existem para você ir preenchendo/ajustando conforme for recortando as imagens.
    """

    def __init__(self, app: AutomotivApp, logger: Any):
        self.app = app
        self.logger = logger

    def create_from_material_results(
        self,
        results: list[MaterialProcessResult],
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str | None:
        found_results = [result for result in results if result.found]

        if not found_results:
            self.logger.warning("Nenhum material encontrado. Não vou iniciar orçamento.")
            return None

        material_codes = [result.item.code_or_reference for result in found_results]
        # margins_by_code = self.app.buscar_margens_pedidos_anteriores(
        #     company_code=company_code,
        #     material_codes=material_codes,
        #     company_name=company_name,
        # )
        margins_by_code = {}  # TODO: implementar busca de margens em pedidos anteriores (GRV) e usar aqui.

        budget_number = self.app.criar_orcamento(
            company_code=company_code,
            items=[result.item for result in found_results],
            margins_by_code=margins_by_code,
        )

        self.app.gravar_orcamento()
        self.app.gerar_pdf_orcamento()

        return budget_number
