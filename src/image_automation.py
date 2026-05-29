from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pyautogui



class ImageAutomation:
    """
    Classe utilitária para automação por imagem usando PyAutoGUI.

    Todas as imagens devem ficar dentro da pasta configurada em assets_dir,
    por exemplo: assets/images/login_button.png
    """

    def __init__(self, assets_dir: str | Path, confidence: float = 0.85, logger=None) -> None:
        self.assets_dir = Path(assets_dir)
        self.confidence = confidence
        self.logger = logger

    def _resolve_image_path(self, image_name: str | Path) -> Path:
        image_path = Path(image_name)

        if image_path.is_absolute():
            return image_path

        return self.assets_dir / image_path

    def locate_center(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
    ):
        """
        Procura uma imagem na tela e retorna o centro dela.
        Retorna None caso não encontre dentro do timeout.
        """
        image_path = self._resolve_image_path(image_name)

        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        final_confidence = confidence if confidence is not None else self.default_confidence
        deadline = time.time() + timeout
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                center = pyautogui.locateCenterOnScreen(
                    str(image_path),
                    confidence=final_confidence,
                )

                if center:
                    return center

            except Exception as error:
                # Em alguns ambientes o OpenCV/confidence pode gerar erro.
                # Guardamos o erro para facilitar debug caso nunca encontre.
                last_error = error

            time.sleep(0.5)

        if last_error:
            print(f"[ImageAutomation] Último erro ao buscar imagem {image_path}: {last_error}")

        return None

    def click(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        clicks: int = 1,
        interval: float = 0.05,
        button: str = "left",
    ) -> bool:
        """
        Clica no centro da imagem localizada na tela.
        Retorna True se clicou, False se não encontrou.
        """
        center = self.locate_center(
            image_name=image_name,
            timeout=timeout,
            confidence=confidence,
        )

        if not center:
            return False

        pyautogui.click(
            x=center.x,
            y=center.y,
            clicks=clicks,
            interval=interval,
            button=button,
        )
        return True

    def double_click(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
    ) -> bool:
        return self.click(
            image_name=image_name,
            timeout=timeout,
            confidence=confidence,
            clicks=2,
        )

    def wait_until_visible(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
    ) -> bool:
        """
        Apenas espera a imagem aparecer na tela.
        """
        return self.locate_center(
            image_name=image_name,
            timeout=timeout,
            confidence=confidence,
        ) is not None

    def click_or_raise(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        error_message: str | None = None,
    ) -> None:
        """
        Clica na imagem ou dispara erro explicativo.
        Útil para fluxos obrigatórios, como botão LOGIN.
        """
        clicked = self.click(
            image_name=image_name,
            timeout=timeout,
            confidence=confidence,
        )

        if not clicked:
            image_path = self._resolve_image_path(image_name)
            raise RuntimeError(
                error_message
                or f"Não foi possível localizar/clicar na imagem: {image_path}"
            )

    def exists(self, image_name: str, timeout: int = 3, confidence: float | None = None) -> bool:
        """Verifica se uma imagem existe na tela sem clicar."""
        return self.locate(image_name, timeout=timeout, confidence=confidence) is not None


    def click_if_exists(self, image_name: str, timeout: int = 3, confidence: float | None = None) -> bool:
        """Clica na imagem somente se ela existir na tela."""
        location = self.locate(image_name, timeout=timeout, confidence=confidence)

        if not location:
            return False

        pyautogui.click(location.x, location.y)
        return True
    
    def locate(self, image_name: str, timeout: int = 10, confidence: float | None = None):
        image_path = self.assets_dir / image_name

        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        final_confidence = confidence if confidence is not None else self.confidence
        end_time = time.time() + timeout

        while time.time() < end_time:
            location = pyautogui.locateCenterOnScreen(
                str(image_path),
                confidence=final_confidence,
            )

            if location:
                return location

            time.sleep(0.5)

        return None
    
    def click_bottommost(
        self,
        image_name: str,
        timeout: int = 10,
        confidence: float | None = None,
    ) -> bool:
        image_path = self._resolve_image_path(image_name)
        final_confidence = confidence if confidence is not None else self.default_confidence
        deadline = time.time() + timeout

        while time.time() < deadline:
            matches = list(pyautogui.locateAllOnScreen(str(image_path), confidence=final_confidence))

            if matches:
                bottom_match = max(matches, key=lambda box: box.top)

                center_x = bottom_match.left + bottom_match.width // 2
                center_y = bottom_match.top + bottom_match.height // 2

                pyautogui.click(center_x, center_y)
                return True

            time.sleep(0.5)

        return False