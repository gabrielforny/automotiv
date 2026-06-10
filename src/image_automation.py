from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pyautogui


class ImageAutomation:
    """Utilitário de automação por imagem usando PyAutoGUI."""

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
        image_path = self._resolve_image_path(image_name)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        final_confidence = confidence if confidence is not None else self.confidence
        deadline = time.time() + timeout
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                center = pyautogui.locateCenterOnScreen(str(image_path), confidence=final_confidence)
                if center:
                    return center
            except Exception as error:
                last_error = error
            time.sleep(0.5)

        if last_error and self.logger:
            self.logger.debug("Último erro ao buscar imagem %s: %s", image_path, last_error)
        return None

    def locate(self, image_name: str | Path, timeout: int = 10, confidence: float | None = None):
        return self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)

    def exists(self, image_name: str | Path, timeout: int = 3, confidence: float | None = None) -> bool:
        return self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence) is not None

    def click(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        clicks: int = 1,
        interval: float = 0.05,
        button: str = "left",
    ) -> bool:
        center = self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)
        if not center:
            return False
        pyautogui.click(x=center.x, y=center.y, clicks=clicks, interval=interval, button=button)
        return True

    def double_click(self, image_name: str | Path, timeout: int = 10, confidence: Optional[float] = None) -> bool:
        return self.click(image_name=image_name, timeout=timeout, confidence=confidence, clicks=2)

    def click_if_exists(self, image_name: str | Path, timeout: int = 3, confidence: float | None = None) -> bool:
        return self.click(image_name=image_name, timeout=timeout, confidence=confidence)

    def click_bottommost(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: float | None = None,
    ) -> bool:
        image_path = self._resolve_image_path(image_name)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        final_confidence = confidence if confidence is not None else self.confidence
        deadline = time.time() + timeout
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                matches = list(pyautogui.locateAllOnScreen(str(image_path), confidence=final_confidence))
                if matches:
                    bottom_match = max(matches, key=lambda box: box.top)
                    center_x = bottom_match.left + bottom_match.width // 2
                    center_y = bottom_match.top + bottom_match.height // 2
                    pyautogui.click(center_x, center_y)
                    return True
            except Exception as error:
                last_error = error
            time.sleep(0.5)

        if last_error and self.logger:
            self.logger.debug("Último erro ao clicar imagem inferior %s: %s", image_path, last_error)
        return False

    def wait_until_visible(self, image_name: str | Path, timeout: int = 10, confidence: Optional[float] = None) -> bool:
        return self.exists(image_name=image_name, timeout=timeout, confidence=confidence)

    def click_with_offset(
        self,
        image_name: str | Path,
        offset_x: int = 0,
        offset_y: int = 0,
        timeout: int = 10,
        confidence: float | None = None,
    ) -> bool:
        """Localiza a imagem e clica com deslocamento em pixels a partir do centro."""
        center = self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)
        if not center:
            return False
        pyautogui.click(x=center.x + offset_x, y=center.y + offset_y)
        return True

    def click_or_raise(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        error_message: str | None = None,
    ) -> None:
        if self.click(image_name=image_name, timeout=timeout, confidence=confidence):
            return
        image_path = self._resolve_image_path(image_name)
        raise RuntimeError(error_message or f"Não foi possível localizar/clicar na imagem: {image_path}")
