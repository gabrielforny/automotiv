from __future__ import annotations

import time
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.config import BotConfig
from src.formatters import code_search_variations

# XPaths do site automotivdobrasil.com.br
_XPATH_SEARCH_INPUT = "//form[contains(@class,'searchFormMenu')]//input[@name='s']"
_XPATH_RESULT_BLOCK = "//div[contains(@class,'rowProdutos')]//div[contains(@class,'blockPdtList')]"
_XPATH_CODE_LABEL = ".//p[contains(@class,'codeProduto')]"
_XPATH_TITLE_LABEL = ".//h4[contains(@class,'titleProduto')]"


class SiteSearchService:
    """Pesquisa peça no site automotivdobrasil.com.br via Selenium quando não encontrada no GRV.

    Fluxo:
      1. Abre o Chrome via Selenium.
      2. Tenta cada variação do código (com -, espaço, ponto, sem separador).
      3. Se encontrar resultado → retorna dict com dados da peça.
      4. Fecha o browser ao final.
    """

    def __init__(self, config: BotConfig, logger: Any) -> None:
        self.config = config
        self.logger = logger
        self._driver: webdriver.Chrome | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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

        self._open_browser()
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

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _open_browser(self) -> None:
        opts = Options()
        opts.add_argument("--start-maximized")
        service = Service(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=opts)
        self._driver.get(self.config.search.fallback_site)
        time.sleep(self.config.site_search.wait_after_open_seconds)

    def _try_search_variation(self, code: str) -> dict[str, Any] | None:
        driver = self._driver
        if driver is None:
            return None

        # Navega de volta à home antes de cada tentativa para limpar estado
        driver.get(self.config.search.fallback_site)
        time.sleep(1)

        try:
            wait = WebDriverWait(driver, 10)
            search_input = wait.until(EC.presence_of_element_located((By.XPATH, _XPATH_SEARCH_INPUT)))
        except Exception:
            self.logger.warning("Campo de busca não encontrado no site (XPath: %s).", _XPATH_SEARCH_INPUT)
            return None

        search_input.clear()
        search_input.send_keys(code)
        search_input.submit()

        time.sleep(self.config.site_search.wait_after_search_seconds)

        # Verifica se há pelo menos 1 bloco de produto na página de resultados
        try:
            first_block = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, _XPATH_RESULT_BLOCK))
            )
        except Exception:
            self.logger.info("Sem resultados para '%s'.", code)
            return None

        # Extrai código e título do primeiro resultado
        raw_code = self._extract_text(first_block, _XPATH_CODE_LABEL)
        title = self._extract_text(first_block, _XPATH_TITLE_LABEL)

        # O código vem como "#AE1390EP" — remove o '#'
        internal_code = raw_code.lstrip("#").strip() if raw_code else code

        return {
            "codigo_interno": internal_code,
            "item": title or None,
            "familia": None,
            "grupo": None,
            "origem": "site",
        }

    def _extract_text(self, parent: Any, xpath: str) -> str:
        try:
            return parent.find_element(By.XPATH, xpath).text.strip()
        except Exception:
            return ""

    def _close_browser(self) -> None:
        if self._driver is not None:
            self.logger.info("Fechando browser Selenium.")
            try:
                self._driver.quit()
            except Exception as exc:
                self.logger.warning("Erro ao fechar browser: %s", exc)
            finally:
                self._driver = None
