from __future__ import annotations

import time
import webbrowser
from typing import Any

import pyperclip
from pywinauto import keyboard

from src.config import BotConfig
from src.formatters import code_search_variations
from src.image_automation import ImageAutomation


class SiteSearchService:
    """Pesquisa peça no site automotivdobrasil.com.br quando não encontrada no GRV.

    Fluxo:
      1. Abre o site no navegador padrão.
      2. Tenta cada variação do código (com -, espaço, ponto, sem separador).
      3. Se encontrar → retorna dict com dados da peça (mesmo formato do GRV).
      4. Fecha o navegador ao final (encontrou ou não).
    """

    def __init__(self, config: BotConfig, logger: Any) -> None:
        self.config = config
        self.logger = logger
        self.image = ImageAutomation(
            assets_dir=config.images.assets_dir,
            confidence=float(config.images.confidence),
            logger=logger,
        )

    def search(self, code_or_reference: str) -> dict[str, Any] | None:
        variations = code_search_variations(code_or_reference)
        self.logger.info(
            "Pesquisando no site '%s' | variações: %s",
            self.config.search.fallback_site,
            variations,
        )

        if self.config.runtime.dry_run:
            self.logger.info("DRY RUN: não vou acessar o site.")
            return None

        webbrowser.open(self.config.search.fallback_site)
        time.sleep(self.config.site_search.wait_after_open_seconds)

        try:
            for variation in variations:
                self.logger.info("Tentando variação no site: '%s'", variation)
                result = self._try_search_variation(variation)
                if result:
                    self.logger.info("Peça encontrada no site com variação '%s': %s", variation, result)
                    return result
            self.logger.info("Peça não encontrada no site para: %s", code_or_reference)
            return None
        finally:
            self._close_browser()

    def _try_search_variation(self, code: str) -> dict[str, Any] | None:
        """Digita o código no campo de busca do site e verifica o resultado.

        TODO: recortar as imagens abaixo do navegador real e ajustar a lógica
        de extração do código encontrado conforme o layout do site.
        """
        search_field_image = self.config.images.site_search_field
        search_button_image = self.config.images.site_search_button
        result_found_image = self.config.images.site_result_found

        # Clicar no campo de busca
        clicked = self.image.click(image_name=search_field_image, timeout=10)
        if not clicked:
            self.logger.warning("Campo de busca do site não encontrado por imagem (%s).", search_field_image)
            return None

        # Limpar campo e digitar código
        keyboard.send_keys("^a")
        pyperclip.copy(code)
        keyboard.send_keys("^v")
        time.sleep(0.3)

        # Clicar no botão de pesquisa (ou Enter se não tiver imagem)
        search_clicked = self.image.click(image_name=search_button_image, timeout=5)
        if not search_clicked:
            keyboard.send_keys("{ENTER}")

        time.sleep(self.config.site_search.wait_after_search_seconds)

        # Verificar se resultado apareceu
        found = self.image.exists(image_name=result_found_image, timeout=5)
        if not found:
            return None

        # TODO: extrair o código interno da área de resultados do site.
        # Por enquanto retorna o próprio código pesquisado como referência.
        internal_code = self._extract_code_from_result(code)
        return {
            "codigo_interno": internal_code,
            "item": None,
            "familia": None,
            "grupo": None,
            "origem": "site",
        }

    def _extract_code_from_result(self, searched_code: str) -> str:
        """Extrai o código interno da tela de resultados do site.

        TODO: implementar via imagem + OCR ou captura de clipboard após
        clicar no código na grid de resultados.
        """
        return searched_code

    def _close_browser(self) -> None:
        self.logger.info("Fechando navegador.")
        try:
            keyboard.send_keys("%{F4}")
            time.sleep(1)
        except Exception as exc:
            self.logger.warning("Não consegui fechar o navegador com Alt+F4: %s", exc)
