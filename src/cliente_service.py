from __future__ import annotations

from typing import Any

from src.desktop_automation import AutomotivApp
from src.formatters import cpf_cnpj_search_variations


class ClienteService:
    def __init__(self, app: AutomotivApp, logger: Any):
        self.app = app
        self.logger = logger

    def find_client_code(self, cpf_or_cnpj: str) -> str | None:
        self.app.open_clients_screen()

        for value in cpf_cnpj_search_variations(cpf_or_cnpj):
            self.logger.info("Tentando buscar cliente com: %s", value)
            code = self.app.search_client_and_get_code(value)
            if code:
                self.logger.info("Cliente encontrado. Código: %s", code)
                return code

        self.logger.warning("Cliente não encontrado para CPF/CNPJ informado: %s", cpf_or_cnpj)
        return None
