from __future__ import annotations

from typing import Any

from src.desktop_automation import AutomotivApp
from src.formatters import cpf_cnpj_search_variations


class ClienteService:
    def __init__(self, app: AutomotivApp, logger: Any):
        self.app = app
        self.logger = logger

    def find_client_code(self, cpf_or_cnpj: str) -> tuple[str | None, str | None, str | None]:
        """Retorna (client_code, carrier_code, company_name). Carrier e nome vêm do cadastro GRV."""
        self.app.open_clients_screen()

        code: str | None = None
        carrier_code: str | None = None
        company_name: str | None = None
        for value in cpf_cnpj_search_variations(cpf_or_cnpj):
            self.logger.info("Tentando buscar cliente com: %s", value)
            code, carrier_code, company_name = self.app.search_client_and_get_code(value)
            if code:
                self.logger.info(
                    "Cliente encontrado. Código: %s | Transportadora: %s | Nome: %s",
                    code, carrier_code, company_name,
                )
                break

        if not code:
            self.logger.warning("Cliente não encontrado para CPF/CNPJ informado: %s", cpf_or_cnpj)

        self.app.close_current_screen()
        return code, carrier_code, company_name
